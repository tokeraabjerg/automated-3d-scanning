#---------------------------------------------------------------------------
#  ?                                ABOUT
#  @author         :  Toke Raabjerg
#  @repo           :  https://github.com/Tokeraabjerg/automated-3d-scanning
#  @description    :  This module provides an interface to interact with a 3D scanner using its SDK library. 
#                     It includes functionality to connect to the scanner, configure it, perform scans, 
#                     and handle point cloud data.
#---------------------------------------------------------------------------

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

# Define additional error code constants
SENSOR3D_INVALIDSENSORHANDLE = -1
SENSOR3D_SENSORNOTCONNECTED = -2
SENSOR3D_TIMEOUT = -3
SENSOR3D_CONFIGURATIONERROR = -4
SENSOR3D_ARGUMENTNULLPOINTER = -101
SENSOR3D_ARGUMENTOUTOFRANGE = -102
SENSOR3D_RETURNBUFFERTOOSMALL = -103
SENSOR3D_COMMANDNOTFOUND = -104
SENSOR3D_SOCKETCOMMUNICATIONERROR = -106
SENSOR3D_BUSY = -201
SENSOR3D_DATASTREAMERROR = -301

# Create a dictionary to map error codes to descriptions
ERROR_CODES = {
    SENSOR3D_OK: "No error.",
    SENSOR3D_INVALIDSENSORHANDLE: "Sensor handle doesn’t exist in the list of opened 3D sensors.",
    SENSOR3D_SENSORNOTCONNECTED: "Sensor is disconnected.",
    SENSOR3D_TIMEOUT: "Operation timeout.",
    SENSOR3D_CONFIGURATIONERROR: "Failed to read the configurations from the 3D sensor.",
    SENSOR3D_ARGUMENTNULLPOINTER: "Argument used in SDK function is null.",
    SENSOR3D_ARGUMENTOUTOFRANGE: "Argument used in SDK function is out of the possible range.",
    SENSOR3D_RETURNBUFFERTOOSMALL: "The size of the SDK result is bigger than the size of the buffer used as an argument.",
    SENSOR3D_COMMANDNOTFOUND: "The ASCII command could not be found.",
    SENSOR3D_SOCKETCOMMUNICATIONERROR: "Error in socket communication.",
    SENSOR3D_BUSY: "The command cannot be processed. The device is in the Acquisition state.",
    SENSOR3D_DATASTREAMERROR: "Failed to read data stream format from the sensor."
}

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
        self.last_ping_failed_log_time = 0  # Initialize the last log time for ping failure
        self.ping_log_interval = 60  # Set the log interval to 60 seconds
        self.last_ping_success_log_time = 0  # Initialize the last log time for ping success
        self.ping_log_interval = 60  # Set the log interval to 60 seconds

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

    def interpret_error(self, error_code: int) -> str:
        """
        Interpret the error code and return its description.

        :param error_code: The error code returned by an SDK function.
        :return: Description of the error.
        """
        return ERROR_CODES.get(error_code, f"Unknown error code: {error_code}")

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
                            error_message = self.interpret_error(result)
                            logger.warning(f"Connection attempt {attempt}/{max_retries} failed: {error_message}, status value {status.value}.")
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
                error_message = self.interpret_error(result)
                logger.error(f"Sensor3D_GetSensorStatus failed with error code {result} - {error_message}.")
                self.connected = False  # Update connection status
                return {'connected': False, 'error_code': result, 'error_message': error_message}

            # Interpret the status value based on SDK documentation
            is_connected = bool(status.value & SENSOR_CONNECTED)  # Adjust based on actual bitmask
            error_code = (status.value & ~SENSOR_CONNECTED)  # Adjust extraction as per SDK

            logger.info(f"Sensor Status - Connected: {is_connected}, Error Code: {error_code}")

            self.connected = is_connected  # Update connection status
            return {
                'connected': is_connected,
                'error_code': error_code
            }

    def perform_scan(self, stop_event: Optional[threading.Event] = None) -> Optional[o3d.geometry.PointCloud]:
        logger.info("Starting perform_scan method.")

        # Clear the stop_event before starting the scan
        if stop_event:
            stop_event.clear()

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
                return None

            # Set trigger source to software
            if not self.write_sensor_command("SetTriggerSource=1"):
                logger.error("Failed to set trigger source to software.")
                return None

            if not self.write_sensor_command(f"SetLEDPattern={led_pattern}"):
                logger.error("Failed to set LED pattern.")
                return None

            if not self.write_sensor_command("SetAcquisitionStart"):
                logger.error("Failed to start acquisition.")
                return None
            
             # Trigger the scan
            if not self.write_sensor_command("SetTriggerSoftware"):
                logger.error("Failed to trigger the software scan.")
                return None

            # Try to read camera dimensions
            camera_width_str = self.read_sensor_parameter("GetPixelXMax")
            if camera_width_str is None:
                camera_width_str = self.read_sensor_parameter("GetROI1WidthX")
            camera_height_str = self.read_sensor_parameter("GetPixelYMax")
            if camera_height_str is None:
                camera_height_str = self.read_sensor_parameter("GetROI1HeightY")

            if camera_width_str is None or camera_height_str is None:
                logger.error("Failed to obtain camera dimensions. Aborting scan.")
                return None

            try:
                camera_width = int(camera_width_str)
                camera_height = int(camera_height_str)
                logger.info(f"Camera dimensions: width={camera_width}, height={camera_height}")
            except ValueError as ve:
                logger.error(f"Invalid camera dimensions received: width='{camera_width_str}', height='{camera_height_str}'")
                return None

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

            if stop_event and stop_event.is_set():
                logger.info("Scan stopped by user before starting scan.")
                return None

            logger.info("Attempting to acquire scan.")

            # Perform the scan
            result = self.lib.Sensor3D_GetPointCloud(
                self.sensorHandle,
                byref(scanBuffer),
                pc_size,
                byref(number_of_points),
                byref(roi),
                timeout
            )

            if stop_event and stop_event.is_set():
                logger.info("Scan stopped by user during acquisition.")
                return None

            if result != SENSOR3D_OK:
                logger.error(f"Error acquiring point cloud, result: {result}")
                return None

            logger.info(f"Scan: Number of points: {number_of_points.value}")
            if number_of_points.value == 0:
                logger.error("No points acquired. Skipping this scan.")
                return None

            ## optimized approach using numpy's vectorized operations, needs testing ##
            # Extract all points and intensities into numpy arrays
            all_points = np.array([(scanBuffer.point[idx].x, scanBuffer.point[idx].y, scanBuffer.point[idx].z) for idx in range(number_of_points.value)], dtype=np.float64)
            all_intensities = np.array([scanBuffer.intensity[idx] for idx in range(number_of_points.value)], dtype=np.uint32)  # Use uint32 to avoid clipping

            # Create a boolean mask for points with z >= 1
            valid_mask = all_points[:, 2] >= 1

            # Filter out invalid points using the mask
            points_np = all_points[valid_mask]
            intensities_np = all_intensities[valid_mask]

            logger.info(f"After filtering origin points, remaining points: {len(points_np)}")

            # Create Open3D point cloud
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(points_np)
            intensities_normalized = (intensities_np / 65535).astype(np.float64)
            pcd.colors = o3d.utility.Vector3dVector(np.tile(intensities_normalized[:, None], (1, 3)))

            # pcd is the Open3D point cloud
            logger.info("Scan completed successfully.")
            return pcd

        except Exception as e:
            logger.exception(f"An error occurred during scanning: {e}")
            return None

        finally:
            # Stop acquisition to reset the sensor
            self.write_sensor_command("SetAcquisitionStop")

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
                    error_message = self.interpret_error(result)
                    logger.error(f"Error writing {full_command.strip()}, result code: {result} - {error_message}")
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
                    error_message = self.interpret_error(result)
                    logger.error(f"Error reading {command}, result code: {result} - {error_message}")
                    return None
                value = readBuffer.value.decode().strip()
                logger.debug(f"Read parameter {command}: {value}")
                return value
            except Exception as e:
                logger.error(f"Exception while reading parameter {command}: {e}")
                return None

    def stop_scan(self):
        """
        Send the SetAcquisitionStop command to the sensor.
        """
        if self.write_sensor_command("SetAcquisitionStop"):
            logger.debug("Acquisition stopped successfully.")
            # Optionally, set the stop_event here if it's being used
            # if stop_event:
            #     stop_event.set()
        else:
            logger.error("Failed to stop acquisition.")

    def ping_sensor(self) -> bool:
        """
        Ping the sensor to check connectivity.

        :return: True if the sensor is connected, False otherwise.
        """
        with self.lock:
            if not self.sensorHandle:
                current_time = time.time()
                if current_time - self.last_ping_failed_log_time > self.ping_log_interval:
                    logger.warning("Ping failed: sensorHandle is None.")
                    self.last_ping_failed_log_time = current_time
                self.connected = False  # Update connection status
                return False

            status = c_int()
            result = self.lib.Sensor3D_GetSensorStatus(self.sensorHandle, byref(status))

            if result == SENSOR3D_OK:
                current_time = time.time()
                if current_time - self.last_ping_success_log_time > self.ping_log_interval:
                    logger.info("Ping successful: Sensor is connected.")
                    self.last_ping_success_log_time = current_time
                self.connected = True  # Update connection status
                return True
            else:
                current_time = time.time()
                if current_time - self.last_ping_failed_log_time > self.ping_log_interval:
                    logger.warning(f"Ping failed: Sensor status result code {result}, status value {status.value}.")
                    self.last_ping_failed_log_time = current_time
                self.connected = False  # Update connection status
                return False
