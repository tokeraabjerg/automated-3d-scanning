# scanner_interface.py

from ctypes import *
import logging
import threading
import time
import numpy as np
import open3d as o3d
import os
import sys
from typing import Optional

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
    def __init__(self, lib_path: str, ip_address: str = "192.168.100.1", timeout: int = 5000, output_directory: Optional[str] = None):
        """
        Initialize the ScannerInterface.

        :param lib_path: Path to the scanner's SDK library (DLL or SO file).
        :param ip_address: IP address of the scanner.
        :param timeout: Timeout for sensor commands in milliseconds.
        :param output_directory: Directory where scan data will be stored.
        """
        if output_directory is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            output_directory = os.path.join(base_dir, "output")
        self.output_directory = output_directory

        try:
            self.lib = cdll.LoadLibrary(lib_path)
            logger.info(f"Successfully loaded library from {lib_path}")
        except OSError as e:
            logger.error(f"Failed to load library at {lib_path}: {e}")
            raise

        self.sensorHandle = None
        self.ip_address = ip_address
        self.timeout = timeout
        self.lock = threading.Lock()
        self.connected = False  # Initialize the connected attribute

        self._configure_library_functions()

    def _configure_library_functions(self):
        """
        Configure the argument and return types for the scanner SDK functions.
        """
        try:
            # Connect
            self.lib.Sensor3D_Connect.argtypes = [c_char_p, c_int]
            self.lib.Sensor3D_Connect.restype = c_void_p

            # GetSensorStatus
            self.lib.Sensor3D_GetSensorStatus.argtypes = [c_void_p, POINTER(c_int)]
            self.lib.Sensor3D_GetSensorStatus.restype = c_int

            # ReadData
            self.lib.Sensor3D_ReadData.argtypes = [c_void_p, c_char_p, c_char_p, c_int, c_int]
            self.lib.Sensor3D_ReadData.restype = c_int

            # WriteData
            self.lib.Sensor3D_WriteData.argtypes = [c_void_p, c_char_p]
            self.lib.Sensor3D_WriteData.restype = c_int

            # GetPointCloud
            self.lib.Sensor3D_GetPointCloud.argtypes = [
                c_void_p,
                POINTER(POINT_CLOUD),
                c_int,
                POINTER(c_int),
                POINTER(ROI),
                c_int
            ]
            self.lib.Sensor3D_GetPointCloud.restype = c_int

            # Disconnect
            self.lib.Sensor3D_Disconnect.argtypes = [c_void_p]
            self.lib.Sensor3D_Disconnect.restype = None

            logger.info("Configured library functions successfully.")
        except AttributeError as e:
            logger.error(f"Failed to configure library functions: {e}")
            raise

    def connect(self, max_retries: int = 3) -> bool:
        """
        Attempt to connect to the sensor.

        :param max_retries: Maximum number of connection attempts.
        :return: True if connected successfully, False otherwise.
        """
        with self.lock:
            logger.info("Attempting to connect to the sensor.")
            for attempt in range(1, max_retries + 1):
                try:
                    self.sensorHandle = self.lib.Sensor3D_Connect(self.ip_address.encode(), self.timeout)
                    if self.sensorHandle:
                        # Verify connection status
                        status = c_int()
                        result = self.lib.Sensor3D_GetSensorStatus(self.sensorHandle, byref(status))
                        if result == SENSOR3D_OK and (status.value & SENSOR_CONNECTED):
                            logger.info("Connected to the sensor.")
                            self.connected = True  # Update connection status
                            return True
                        else:
                            logger.warning(f"Connection attempt {attempt}/{max_retries} failed: Sensor status result code {result}, status value {status.value}.")
                            self.sensorHandle = None  # Reset sensorHandle if connection is not verified
                    else:
                        logger.warning(f"Connection attempt {attempt}/{max_retries} failed: Sensor handle is None.")
                except Exception as e:
                    logger.error(f"Exception during connection attempt {attempt}/{max_retries}: {e}")

                time.sleep(1)  # Wait before retrying

            logger.error("All connection attempts failed. Unable to connect to the sensor.")
            self.connected = False  # Update connection status
            return False

    def disconnect(self):
        """
        Disconnect from the sensor.
        """
        with self.lock:
            if self.sensorHandle:
                try:
                    self.lib.Sensor3D_Disconnect(self.sensorHandle)
                    logger.info("Disconnected from the sensor.")
                except Exception as e:
                    logger.error(f"Error during disconnection: {e}")
                finally:
                    self.sensorHandle = None
                    self.connected = False  # Update connection status
            else:
                logger.warning("Attempted to disconnect, but sensor was not connected.")

    def get_sensor_status(self) -> dict:
        """
        Retrieves the current status of the scanner.

        Returns:
            dict: Contains 'connected' (bool) and 'error_code' (int).
        """
        with self.lock:
            if not self.sensorHandle:
                logger.warning("Attempted to get status, but sensorHandle is None.")
                self.connected = False  # Update connection status
                return {'connected': False, 'error_code': -1}

            status = c_int()
            result = self.lib.Sensor3D_GetSensorStatus(self.sensorHandle, byref(status))

            if result != SENSOR3D_OK:
                logger.error(f"Sensor3D_GetSensorStatus failed with error code {result}.")
                self.connected = False  # Update connection status
                return {'connected': False, 'error_code': result}

            # Interpret the status value based on SDK documentation
            is_connected = bool(status.value & SENSOR_CONNECTED)  # Adjust based on actual bitmask
            error_code = (status.value & ~SENSOR_CONNECTED)  # Adjust extraction as per SDK

            logger.info(f"Sensor Status - Connected: {is_connected}, Error Code: {error_code}")

            self.connected = is_connected  # Update connection status
            return {
                'connected': is_connected,
                'error_code': error_code
            }

    def perform_scan(self, nrScans: int):
        """
        Perform a scan and save the point cloud data.

        :param nrScans: Number of scans to perform.
        """
        try:
            # Hardcoded configurations
            sensor_mode = "4"        # 4: 3D Point Cloud
            trigger_source = "0"     # 0: Internal trigger
            led_pattern = "28"       # 28: Predefined LED pattern

            # Ensure output directory exists
            os.makedirs(self.output_directory, exist_ok=True)

            # Configure sensor using hardcoded configurations
            if not self.write_sensor_command(f"SetSensorMode={sensor_mode}"):
                logger.error("Failed to set sensor mode.")
                return
            if not self.write_sensor_command(f"SetTriggerSource={trigger_source}"):
                logger.error("Failed to set trigger source.")
                return
            if not self.write_sensor_command(f"SetLEDPattern={led_pattern}"):
                logger.error("Failed to set LED pattern.")
                return
            if not self.write_sensor_command("SetAcquisitionStart"):
                logger.error("Failed to start acquisition.")
                return

            logger.info("Acquisition started successfully.")

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

            try:
                camera_width = int(camera_width_str)
                camera_height = int(camera_height_str)
                logger.info(f"Camera dimensions: width={camera_width}, height={camera_height}")
            except ValueError as ve:
                logger.error(f"Invalid camera dimensions received: width='{camera_width_str}', height='{camera_height_str}'")
                return

            nrPixels = camera_width * camera_height
            pc_size = (sizeof(POINT3D) + sizeof(c_ushort)) * nrPixels

            # Initialize buffers
            PointArrayType = POINT3D * nrPixels
            IntensityArrayType = c_ushort * nrPixels

            scanBuffer = POINT_CLOUD()
            scanBuffer.point = PointArrayType()
            scanBuffer.intensity = IntensityArrayType()

            number_of_points = c_int()
            roi = ROI()
            timeout = 30000  # Timeout for point cloud acquisition in milliseconds

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
                    continue

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
                output_filename = os.path.join(self.output_directory, f"point_cloud_{i+1}.ply")
                o3d.io.write_point_cloud(output_filename, pcd)
                logger.info(f"Saved point cloud to {output_filename}")

                # Always reduce and save the point cloud
                self.reduce_and_save_point_cloud(pcd, scan_number=i+1)

            # Stop acquisition
            if not self.write_sensor_command("SetAcquisitionStop"):
                logger.error("Failed to stop acquisition.")
            else:
                logger.info("Acquisition stopped successfully.")

        except Exception as e:
            logger.exception(f"An error occurred during scanning: {e}")

    def reduce_and_save_point_cloud(self, pcd: o3d.geometry.PointCloud, scan_number: int):
        """
        Reduce the point cloud to less than 100,000 points and save it.

        :param pcd: The original point cloud.
        :param scan_number: The scan number for naming purposes.
        """
        try:
            num_points = len(pcd.points)
            logger.info(f"Original point cloud has {num_points} points.")

            if num_points > 100000:
                # Calculate voxel size to reduce to approximately 100,000 points
                voxel_size = self.calculate_voxel_size(pcd, target_points=100000)
                pcd_reduced = pcd.voxel_down_sample(voxel_size=voxel_size)
                logger.info(f"Reduced point cloud to {len(pcd_reduced.points)} points using voxel size {voxel_size}.")
            else:
                pcd_reduced = pcd
                logger.info("Point cloud size is within the desired limit. No reduction needed.")

            # Save the reduced point cloud to a fixed filename, overwriting previous
            reduced_pcd_filename = os.path.join(self.output_directory, "reduced_point_cloud.ply")
            o3d.io.write_point_cloud(reduced_pcd_filename, pcd_reduced)
            logger.info(f"Saved reduced point cloud to {reduced_pcd_filename}")
        except Exception as e:
            logger.error(f"Error during point cloud reduction and saving: {e}")

    def calculate_voxel_size(self, pcd: o3d.geometry.PointCloud, target_points: int = 100000) -> float:
        """
        Calculate an appropriate voxel size to reduce the point cloud to approximately target_points.

        :param pcd: The original point cloud.
        :param target_points: The desired number of points after reduction.
        :return: The calculated voxel size.
        """
        try:
            # Estimate voxel size by scaling based on the ratio of target_points to current points
            num_points = len(pcd.points)
            if num_points <= target_points:
                return 0.0  # No reduction needed

            ratio = (num_points / target_points) ** (1/3)  # Assuming uniform scaling
            voxel_size = 0.1 * ratio  # Base voxel size is 0.1, adjust as needed
            voxel_size = max(voxel_size, 0.01)  # Set a minimum voxel size
            return voxel_size
        except Exception as e:
            logger.error(f"Error calculating voxel size: {e}")
            return 0.1  # Default voxel size

    def write_sensor_command(self, command: str) -> bool:
        """
        Send a command to the sensor, appending '\r' if not present.

        :param command: Command string to send to the sensor.
        :return: True if command executed successfully, False otherwise.
        """
        with self.lock:
            try:
                full_command = command if command.endswith('\r') else command + '\r'
                result = self.lib.Sensor3D_WriteData(self.sensorHandle, full_command.encode())
                if result != SENSOR3D_OK:
                    logger.error(f"Error writing {full_command.strip()}, result code: {result}")
                    return False
                logger.debug(f"Executed command: {full_command.strip()}")
                return True
            except Exception as e:
                logger.error(f"Exception while writing command {command}: {e}")
                return False

    def read_sensor_parameter(self, command: str) -> Optional[str]:
        """
        Read a parameter from the sensor.

        :param command: The command string to send to the sensor.
        :return: The response from the sensor if successful, None otherwise.
        """
        with self.lock:
            try:
                readBuffer = create_string_buffer(1024)
                result = self.lib.Sensor3D_ReadData(
                    self.sensorHandle,
                    command.encode(),
                    readBuffer,
                    1024,
                    0  # Corrected: Reserved should be 0
                )
                if result != SENSOR3D_OK:
                    logger.error(f"Error reading {command}, result code: {result}")
                    return None
                value = readBuffer.value.decode().strip()
                logger.debug(f"Read parameter {command}: {value}")
                return value
            except Exception as e:
                logger.error(f"Exception while reading parameter {command}: {e}")
                return None

    def stop_scan(self) -> bool:
        """
        Stop the ongoing scan process.

        :return: True if the scan was stopped successfully, False otherwise.
        """
        return self.write_sensor_command("SetAcquisitionStop")

    def ping_sensor(self) -> bool:
        """
        Ping the sensor to check connectivity.

        :return: True if the sensor is connected, False otherwise.
        """
        with self.lock:
            if not self.sensorHandle:
                logger.warning("Ping failed: sensorHandle is None.")
                self.connected = False  # Update connection status
                return False

            status = c_int()
            result = self.lib.Sensor3D_GetSensorStatus(self.sensorHandle, byref(status))

            if result == SENSOR3D_OK:
                logger.info("Ping successful: Sensor is connected.")
                self.connected = True  # Update connection status
                return True
            else:
                logger.warning(f"Ping failed: Sensor status result code {result}, status value {status.value}.")
                self.connected = False  # Update connection status
                return False
