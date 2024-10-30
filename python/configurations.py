import logging
from configurations_data import configurations_info
import threading

logger = logging.getLogger(__name__)

class Configurations:
    def __init__(self, scanner_interface=None):
        # Initialize the Configurations class with a scanner interface and configuration information
        self.scanner = scanner_interface
        self.configurations_info = configurations_info
        self.configurations = {}
        self.lock = threading.Lock()  # Use a lock to ensure thread safety during operations

    def read_parameter(self, command):
        # Read a parameter value from the sensor using the provided command
        try:
            if command and self.scanner:
                return self.scanner.read_sensor_parameter(command)
        except Exception as e:
            logger.error(f"Failed to read parameter {command}: {e}")
        return None

    def read_default_parameter(self, default_command):
        # Read the default value of a parameter from the sensor using the provided default command
        try:
            if default_command and self.scanner:
                return self.scanner.read_sensor_parameter(default_command)
        except Exception as e:
            logger.error(f"Failed to read default parameter {default_command}: {e}")
        return None

    def read_all_configurations(self):
        # Read all configurations from the sensor and store them in the configurations dictionary
        with self.lock:
            for key, info in self.configurations_info.items():
                # Read the current value of the configuration
                value = self.read_parameter(info.get('get_command'))
                if value is None:
                    value = info.get('default')  # Set to default if reading fails

                # Read the minimum value of the configuration (if available)
                min_value = self.read_parameter(info.get('min_command'))

                # Read the maximum value of the configuration (if available)
                max_value = self.read_parameter(info.get('max_command'))

                # Read the default value of the configuration (if available)
                default_value = info.get('default')
                if default_value is None and 'default_command' in info:
                    default_value = self.read_default_parameter(info.get('default_command'))

                # Ensure min and max values are not None, set sensible defaults if they are
                min_value = float(min_value) if min_value is not None else float('-inf')
                max_value = float(max_value) if max_value is not None else float('inf')

                # Store the read values in the configurations_info dictionary
                info['value'] = value if value is not None else default_value
                info['min'] = min_value
                info['max'] = max_value
                info['default'] = default_value

                # Update the configurations dictionary with the read values
                self.configurations[key] = {
                    'value': value if value is not None else default_value,
                    'description': info.get('description'),
                    'type': info.get('type'),
                    'options': info.get('options'),
                    'min': min_value,
                    'max': max_value,
                    'default': default_value,
                }
                #logger.info(f"Loaded configuration '{key}': {self.configurations[key]}")

    def validate_value(self, info, value):
        # Validate the provided value based on the configuration type and range (if applicable)
        try:
            if info['type'] == 'int':
                int_value = int(value)
                # Check if the value is within the specified min and max range
                if info['min'] != float('-inf') and info['max'] != float('inf'):
                    min_value = int(info['min'])
                    max_value = int(info['max'])
                    if not (min_value <= int_value <= max_value):
                        logger.error(f"Value for {info['get_command']} out of range ({min_value} - {max_value})")
                        return False
            elif info['type'] == 'float':
                float_value = float(value)
                # Check if the value is within the specified min and max range
                if info['min'] != float('-inf') and info['max'] != float('inf'):
                    min_value = float(info['min'])
                    max_value = float(info['max'])
                    if not (min_value <= float_value <= max_value):
                        logger.error(f"Value for {info['get_command']} out of range ({min_value} - {max_value})")
                        return False
            elif info['type'] == 'enum':
                # Ensure the provided value is one of the valid options
                if value not in info['options'].keys():
                    logger.error(f"Invalid option for {info['get_command']}")
                    return False
            return True
        except ValueError:
            # Log an error if the value cannot be converted to the expected type
            logger.error(f"Invalid value for {info['get_command']}: {value}")
            return False

    def update_configuration(self, key, value):
        # Update the configuration value on the scanner
        with self.lock:
            # Get the configuration information for the provided key
            info = self.configurations_info.get(key)
            if not info:
                logger.error(f"Configuration {key} not found.")
                return False

            # Only update if the value is different from the current value
            current_value = info.get('value')
            if current_value == value:
                logger.info(f"No update needed for {key}, value is already set to {value}.")
                return True

            set_command = info.get('set_command')
            # Validate the input based on the type
            if not self.validate_value(info, value):
                return False

            # Send the command to the scanner to update the configuration
            logger.info(f"Writing value {value} to {key} using command {set_command}.")
            if not self.scanner.write_sensor_command(f"{set_command}={value}\r"):
                logger.error(f"Failed to set {key}, reverting to default value.")
                return False

            # Log after writing the command
            logger.info(f"Command executed successfully for {key}, written value: {value}")

            # Read back the value to verify
            logger.info(f"Verifying updated value for {key}.")
            updated_value = self.read_parameter(info.get('get_command'))
            logger.info(f"Verification read-back for {key}: expected {value}, got {updated_value}")
            if updated_value is None or updated_value != value:
                logger.warning(f"Verification failed for {key}, expected {value} but got {updated_value}.")
                return False

            # Update the local configuration if verification is successful
            info['value'] = value
            self.configurations[key]['value'] = value
            logger.info(f"Configuration for {key} updated successfully to {value}.")
            return True
