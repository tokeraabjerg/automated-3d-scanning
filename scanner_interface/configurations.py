#---------------------------------------------------------------------------
#  ?                                ABOUT
#  @author         :  Toke Raabjerg
#  @repo           :  https://github.com/Tokeraabjerg/automated-3d-scanning
#  @description    :  This module manages the configurations for the 3D scanner.
#                     It reads, validates, and updates configuration parameters.
#---------------------------------------------------------------------------

# configurations.py

import logging
from .configurations_data import configurations_info
import threading

logger = logging.getLogger(__name__)

class Configurations:
    def __init__(self, scanner_interface=None):
        """
        Initialize the Configurations class with a scanner interface and configuration information.
        If the scanner is not connected, load default configurations.
        """
        self.scanner = scanner_interface
        self.configurations_info = configurations_info
        self.configurations = {}
        self.lock = threading.Lock()  # Use a lock to ensure thread safety during operations

        # Load configurations
        self.read_all_configurations()

    def read_parameter(self, command):
        """
        Read a parameter value from the sensor using the provided get_command.
        """
        try:
            if command and self.scanner:
                return self.scanner.read_sensor_parameter(command)
        except Exception as e:
            logger.error(f"Failed to read parameter {command}: {e}")
        return None

    def read_all_configurations(self):
        """
        Read all configurations from the sensor using get_commands and store them in the configurations dictionary.
        Uses hardcoded min, max, and default values.
        If the scanner is not connected or reading a parameter fails, use the default value.
        """
        with self.lock:
            for key, info in self.configurations_info.items():
                logger.debug(f"Reading configuration for '{key}'")

                # Retrieve the current value using get_command
                current_value = self.read_parameter(info.get('get_command'))
                min_value = self.read_parameter(info.get('get_command_min')) if 'get_command_min' in info else info.get('min')
                max_value = self.read_parameter(info.get('get_command_max')) if 'get_command_max' in info else info.get('max')
                default_value = self.read_parameter(info.get('get_command_default')) if 'get_command_default' in info else info.get('default')

                if current_value is None and info.get('get_command'):
                    logger.warning(f"Failed to read '{key}'. Using default value: {info.get('default')}.")
                    current_value = info.get('default')
                else:
                    # Convert value to appropriate type
                    try:
                        if info['type'] == 'int':
                            current_value = int(current_value)
                        elif info['type'] == 'float':
                            current_value = float(current_value)
                        elif info['type'] == 'enum':
                            current_value = str(current_value)
                    except ValueError:
                        logger.info(f"Invalid value format for '{key}': {current_value}. Using default value: {info.get('default')}.")
                        current_value = info.get('default')

                # Hardcode fix for LED Power max value
                if key == 'LED Power (%)':
                    max_value = 99

                # Store the configuration
                self.configurations[key] = {
                    'value': current_value,
                    'description': info.get('description'),
                    'type': info.get('type'),
                    'options': info.get('options'),
                    'min': min_value,
                    'max': max_value,
                    'default': default_value,
                }

            logger.debug(f"All configurations loaded successfully. {self.configurations}")

    def validate_value(self, info, value):
        """
        Validate the provided value based on the configuration type and range (if applicable).
        """
        try:
            if info['type'] == 'int':
                int_value = int(value)
                # Check if the value is within the specified min and max range
                if not (info['min'] <= int_value <= info['max']):
                    logger.error(f"Value for '{info['description']}' out of range ({info['min']} - {info['max']}). Provided value: {value}.")
                    return False
            elif info['type'] == 'float':
                float_value = float(value)
                # Check if the value is within the specified min and max range
                if not (info['min'] <= float_value <= info['max']):
                    logger.error(f"Value for '{info['description']}' out of range ({info['min']} - {info['max']}). Provided value: {value}.")
                    return False
            elif info['type'] == 'enum':
                # Ensure the provided value is one of the valid options
                if str(value) not in info['options'].keys():
                    logger.error(f"Invalid option for '{info['description']}': {value}. Valid options: {list(info['options'].keys())}.")
                    return False
            return True
        except ValueError:
            # Log an error if the value cannot be converted to the expected type
            logger.error(f"Invalid value type for '{info['description']}': {value}. Expected type: {info['type']}.")
            return False

    def update_configuration(self, key, value):
        """
        Update the configuration value on the scanner.
        If the scanner is not connected, update the local configuration only.
        """
        
        with self.lock:
            # Get the configuration information for the provided key
            info = self.configurations_info.get(key)
            if not info:
                logger.error(f"Configuration '{key}' not found.")
                return False

            # Only update if the value is different from the current value
            current_value = self.configurations[key]['value']
            if str(current_value) == str(value):
                #logger.debug(f"No update needed for '{key}', value is already set to {value}.")
                return True

            #Validate the input based on the type and range
            if not self.validate_value(info, value):
               return False

            # Prepare the set_command with the value
            set_command = f"{info['set_command']}={value}\r"
            logger.info(f"Sending command to set '{key}' to {value}: {set_command.strip()}")

            # Send the set_command to the sensor if connected
            if self.scanner and self.scanner.sensorHandle:
                if not self.scanner.write_sensor_command(set_command):
                    logger.error(f"Failed to set '{key}' to {value}.")
                    return False
            else:
                logger.warning(f"Scanner not connected. Updating '{key}' locally only.")

            # Update the local configuration
            try:
                if info['type'] == 'int':
                    updated_value = int(value)
                elif info['type'] == 'float':
                    updated_value = float(value)
                elif info['type'] == 'enum':
                    updated_value = str(value)
                else:
                    updated_value = value  # Fallback
            except ValueError:
                logger.error(f"Failed to convert '{value}' to the required type for '{key}'.")
                return False

            self.configurations[key]['value'] = updated_value
            logger.info(f"Configuration '{key}' updated successfully to {updated_value}.")

            return True

    def refresh_configurations(self):
        """
        Refresh configurations by re-reading all configurations from the sensor.
        """
        logger.info("Refreshing configurations from the scanner.")
        self.read_all_configurations()
