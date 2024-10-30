from ctypes import *
import logging
import threading
import time
import numpy as np
import open3d as o3d
import os
import requests

logger = logging.getLogger(__name__)

# Define constants
SENSOR3D_OK = 0
SENSOR_CONNECTED = 0x00000001

# Define structures
class POINT3D(Structure):
    _fields_ = [("x", c_double), ("y", c_double), ("z", c_double)]

class POINT_CLOUD(Structure):
    _fields_ = [("point", POINTER(POINT3D)), ("intensity", POINTER(c_ushort))]

class ROI(Structure):
    _fields_ = [("start_x", c_int), ("start_y", c_int), ("width", c_int), ("height", c_int)]

class ScannerInterface:
    def __init__(self, lib_path, ip_address=b"192.168.100.1", timeout=5000, output_directory="/workspace/output"):
        try:
            self.lib = cdll.LoadLibrary(lib_path)
        except OSError as e:
            logger.error(f"Failed to load library at {lib_path}: {e}")
            raise
        
        self.sensorHandle = None
        self.ip_address = ip_address
        self.timeout = timeout
        self.output_directory = output_directory
        self._configure_library_functions()
        self.lock = threading.Lock()

    def _configure_library_functions(self):
        # Map functions
        self.lib.Sensor3D_Connect.argtypes = [c_char_p, c_int]
        self.lib.Sensor3D_Connect.restype = c_void_p

        self.lib.Sensor3D_GetSensorStatus.argtypes = [c_void_p, POINTER(c_int)]
        self.lib.Sensor3D_GetSensorStatus.restype = c_int

        self.lib.Sensor3D_ReadData.argtypes = [c_void_p, c_char_p, c_char_p, c_int, c_int]
        self.lib.Sensor3D_ReadData.restype = c_int

        self.lib.Sensor3D_WriteData.argtypes = [c_void_p, c_char_p]
        self.lib.Sensor3D_WriteData.restype = c_int

        self.lib.Sensor3D_GetPointCloud.argtypes = [
            c_void_p,
            POINTER(POINT_CLOUD),
            c_int,
            POINTER(c_int),
            POINTER(ROI),
            c_int
        ]
        self.lib.Sensor3D_GetPointCloud.restype = c_int

        self.lib.Sensor3D_Disconnect.argtypes = [c_void_p]
        self.lib.Sensor3D_Disconnect.restype = None

    def connect(self, max_retries=3):
        with self.lock:
            logger.info("Attempting to connect to the sensor.")
            for attempt in range(max_retries):
                self.sensorHandle = self.lib.Sensor3D_Connect(self.ip_address, self.timeout)
                if self.sensorHandle:
                    logger.info("Connected to the sensor.")
                    return True
                else:
                    logger.error(f"Failed to connect on attempt {attempt + 1}/{max_retries}. Retrying...")
                    time.sleep(1)  # Wait before retrying

            # Final check if all attempts fail
            if not self.sensorHandle:
                logger.error("All connection attempts failed. Unable to connect to the sensor.")
                return False
            return True

    def disconnect(self):
        with self.lock:
            if self.sensorHandle:
                self.lib.Sensor3D_Disconnect(self.sensorHandle)
                logger.info("Disconnected from the sensor.")
                self.sensorHandle = None

    def read_sensor_parameter(self, command):
        with self.lock:
            readBuffer = create_string_buffer(1024)
            result = self.lib.Sensor3D_ReadData(
                self.sensorHandle, command.encode(), readBuffer, 1024, 1000
            )
            if result != SENSOR3D_OK:
                error_message = f"Error reading {command}, result code: {result}"
                logger.error(error_message)
                return None
            value = readBuffer.value.decode().strip()
            return value

    def write_sensor_command(self, command):
        with self.lock:
            result = self.lib.Sensor3D_WriteData(self.sensorHandle, command.encode())
            if result != SENSOR3D_OK:
                logger.error(f"Error writing {command}, result code: {result}")
                return False
            logger.info(f"Executed command: {command}")
            return True

    def perform_scan(self, nrScans):
        try:
            # Try to read camera dimensions
            camera_width_str = self.read_sensor_parameter("GetPixelXMax")
            if camera_width_str is None:
                camera_width_str = self.read_sensor_parameter("GetROI1WidthX")
            camera_height_str = self.read_sensor_parameter("GetPixelYMax")
            if camera_height_str is None:
                camera_height_str = self.read_sensor_parameter("GetROI1HeightY")

            if camera_width_str is None or camera_height_str is None:
                logger.error("Failed to obtain camera dimensions. Aborting scan.")
                return

            camera_width = int(camera_width_str)
            camera_height = int(camera_height_str)
            nrPixels = camera_width * camera_height
            pc_size = (sizeof(POINT3D) + sizeof(c_ushort)) * nrPixels

            # Initialize buffers
            PointArrayType = POINT3D * nrPixels
            IntensityArrayType = c_ushort * nrPixels

            scanBuffer = POINT_CLOUD()
            scanBuffer.point = PointArrayType()
            scanBuffer.intensity = IntensityArrayType()

            # Configure sensor for scanning
            if not self.write_sensor_command("SetSensorMode=4\r"):
                logger.error("Failed to set sensor mode.")
                return
            if not self.write_sensor_command("SetTriggerSource=0\r"):
                logger.error("Failed to set trigger source.")
                return
            if not self.write_sensor_command("SetLEDPattern=28\r"):
                logger.error("Failed to set LED pattern.")
                return
            if not self.write_sensor_command("SetAcquisitionStart\r"):
                logger.error("Failed to start acquisition.")
                return
 
            logger.info("Acquisition started successfully.")

            number_of_points = c_int()
            roi = ROI()
            timeout = 30000

            for i in range(nrScans):
                logger.info(f"Attempting to acquire scan {i + 1}/{nrScans}.")
                result = self.lib.Sensor3D_GetPointCloud(
                    self.sensorHandle,
                    byref(scanBuffer),
                    pc_size,
                    byref(number_of_points),
                    byref(roi),
                    timeout
                )

                if result != SENSOR3D_OK:
                    logger.error(f"Error acquiring point cloud, result: {result}")
                else:
                    logger.info(f"Scan {i + 1}/{nrScans}: Number of points: {number_of_points.value}")
                    if number_of_points.value == 0:
                        logger.error("No points acquired. Skipping this scan.")
                        continue

                    # Convert to numpy arrays
                    points_np = np.zeros((number_of_points.value, 3), dtype=np.float64)
                    intensities_np = np.zeros((number_of_points.value,), dtype=np.uint16)

                    for idx in range(number_of_points.value):
                        point = scanBuffer.point[idx]
                        points_np[idx, :] = [point.x, point.y, point.z]
                        intensities_np[idx] = scanBuffer.intensity[idx]

                    # Create Open3D point cloud
                    pcd = o3d.geometry.PointCloud()
                    pcd.points = o3d.utility.Vector3dVector(points_np)
                    intensities_normalized = (intensities_np / 65535).astype(np.float64)
                    pcd.colors = o3d.utility.Vector3dVector(np.tile(intensities_normalized[:, None], (1, 3)))

                    # Save the full point cloud as a .ply file
                    if not os.path.exists(self.output_directory):
                        os.makedirs(self.output_directory)
                    output_filename = os.path.join(self.output_directory, f"point_cloud_{i+1}.ply")
                    o3d.io.write_point_cloud(output_filename, pcd)
                    logger.info(f"Saved point cloud to {output_filename}")

                    # Check if 3D preview is enabled before reducing the point cloud
                    if self.is_3d_preview_enabled():
                        self.reduce_and_save_point_cloud(pcd)

            # Stop acquisition
            if not self.write_sensor_command("SetAcquisitionStop\r"):
                logger.error("Failed to stop acquisition.")
            else:
                logger.info("Scan completed successfully.")

        except Exception as e:
            logger.exception(f"An error occurred during scanning: {e}")

    def reduce_and_save_point_cloud(self, pcd):
        # Reduce the point cloud to less than 100,000 points
        num_points = len(pcd.points)
        if num_points > 100000:
            # Calculate voxel size to reduce to approximately 100,000 points
            pcd_reduced = pcd.voxel_down_sample(voxel_size=0.1)
        else:
            pcd_reduced = pcd

        # Save the reduced point cloud to a fixed filename, overwriting previous
        reduced_pcd_filename = os.path.join(self.output_directory, "reduced_point_cloud.ply")
        o3d.io.write_point_cloud(reduced_pcd_filename, pcd_reduced)
        logger.info(f"Saved reduced point cloud to {reduced_pcd_filename}")

    def is_3d_preview_enabled(self):
        try:
            # Make a GET request to the Flask endpoint to get the current 3D preview setting
            response = requests.get("http://localhost:5001/get_3d_preview_setting")
            if response.status_code == 200:
                # Parse the response to get the preview enabled status
                data = response.json()
                return data.get('3DPreviewEnabled', True)
            else:
                logger.error(f"Failed to get 3D preview setting, status code: {response.status_code}")
                return True  # Default to True if there is an error
        except Exception as e:
            logger.error(f"Exception occurred while getting 3D preview setting: {e}")
            return True  # Default to True in case of exception