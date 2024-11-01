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
from datetime import datetime

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

class PointCloud:
    """
    A simple PointCloud class to store 3D points.
    Replace or extend this class based on your actual point cloud data structure.
    """
    def __init__(self, points):
        self.points = points

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
                        logger.info("Connected to the sensor.")
                        return True
                    else:
                        logger.warning(f"Connection attempt {attempt}/{max_retries} failed.")
                except Exception as e:
                    logger.error(f"Exception during connection attempt {attempt}/{max_retries}: {e}")

                time.sleep(1)  # Wait before retrying

            logger.error("All connection attempts failed. Unable to connect to the sensor.")
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
            else:
                logger.warning("Attempted to disconnect, but sensor was not connected.")

    def initiate_scan(self) -> bool:
        """
        Start the scanning process.

        :return: True if scan started successfully, False otherwise.
        """
        with self.lock:
            try:
                result = self.lib.Sensor3D_WriteData(self.sensorHandle, b"SetAcquisitionStart\r")
                if result == SENSOR3D_OK:
                    logger.info("Scan initiated successfully.")
                    return True
                else:
                    logger.error(f"Failed to initiate scan, result code: {result}")
                    return False
            except Exception as e:
                logger.error(f"Exception while initiating scan: {e}")
                return False

    def stop_scan(self) -> bool:
        """
        Stop the scanning process.

        :return: True if scan stopped successfully, False otherwise.
        """
        with self.lock:
            try:
                result = self.lib.Sensor3D_WriteData(self.sensorHandle, b"SetAcquisitionStop\r")
                if result == SENSOR3D_OK:
                    logger.info("Scan stopped successfully.")
                    return True
                else:
                    logger.error(f"Failed to stop scan, result code: {result}")
                    return False
            except Exception as e:
                logger.error(f"Exception while stopping scan: {e}")
                return False

    def handle_scan(self) -> Optional[o3d.geometry.PointCloud]:
        """
        Retrieve the scan data, converting it to an Open3D point cloud.

        :return: Open3D PointCloud object if successful, None otherwise.
        """
        with self.lock:
            try:
                logger.info("Retrieving point cloud data from scanner.")

                # Read camera dimensions
                camera_width_str = self.read_sensor_parameter("GetPixelXMax")
                if camera_width_str is None:
                    camera_width_str = self.read_sensor_parameter("GetROI1WidthX")
                camera_height_str = self.read_sensor_parameter("GetPixelYMax")
                if camera_height_str is None:
                    camera_height_str = self.read_sensor_parameter("GetROI1HeightY")

                if camera_width_str is None or camera_height_str is None:
                    logger.error("Failed to obtain camera dimensions. Cannot process scan data.")
                    return None

                camera_width = int(camera_width_str)
                camera_height = int(camera_height_str)
                logger.info(f"Camera dimensions: width={camera_width}, height={camera_height}")

                nrPixels = camera_width * camera_height
                pc_size = (sizeof(POINT3D) + sizeof(c_ushort)) * nrPixels

                PointArrayType = POINT3D * nrPixels
                IntensityArrayType = c_ushort * nrPixels

                scanBuffer = POINT_CLOUD()
                scanBuffer.point = PointArrayType()
                scanBuffer.intensity = IntensityArrayType()

                number_of_points = c_int()
                roi = ROI()
                timeout = 30000  # Timeout for point cloud acquisition in milliseconds

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
                    return None

                logger.info(f"Acquired point cloud with {number_of_points.value} points.")

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

                logger.info("Point cloud converted to Open3D format successfully.")
                return pcd

            except Exception as e:
                logger.exception(f"Exception while handling scan: {e}")
                return None

    def read_sensor_parameter(self, command: str) -> Optional[str]:
        """
        Read a parameter value from the sensor using the provided command.

        :param command: Command string to send to the sensor.
        :return: The parameter value as a string if successful, None otherwise.
        """
        with self.lock:
            try:
                readBuffer = create_string_buffer(1024)
                result = self.lib.Sensor3D_ReadData(
                    self.sensorHandle,
                    command.encode(),
                    readBuffer,
                    1024,
                    0
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
