# configurations.py

import logging
from typing import Optional  # Add this import
from configurations_data import configurations_info
import threading

logger = logging.getLogger(__name__)

class Configurations:
    def __init__(self, scanner_interface=None):
        self.scanner_interface = scanner_interface
        self.configurations = configurations_info.copy()

    def read_all_configurations(self):
        """
        Read all configurations from the sensor.
        """
        for key, config in self.configurations.items():
            if config['get_command']:
                value = self.read_configuration(config['get_command'])
                if value is not None:
                    config['value'] = value
                else:
                    logger.warning(f"Failed to read '{key}'. Using default value: {config['default']}.")
                    config['value'] = config['default']

    def read_configuration(self, command: str) -> Optional[str]:
        """
        Read a configuration value from the sensor.

        :param command: The command string to send to the sensor.
        :return: The configuration value if successful, None otherwise.
        """
        if self.scanner_interface:
            return self.scanner_interface.read_sensor_parameter(command)
        return None

    def update_configuration(self, key: str, value: str) -> bool:
        """
        Update a configuration value on the sensor.

        :param key: The configuration key.
        :param value: The new value to set.
        :return: True if the configuration was updated successfully, False otherwise.
        """
        config = self.configurations.get(key)
        if not config:
            logger.error(f"Configuration '{key}' not found.")
            return False

        if config['set_command']:
            command = f"{config['set_command']}={value}"
            if self.scanner_interface and self.scanner_interface.write_sensor_command(command):
                config['value'] = value
                logger.info(f"Configuration '{key}' updated successfully to {value}.")
                return True
            else:
                logger.error(f"Failed to set configuration '{key}' to {value}.")
                return False
        else:
            logger.error(f"No set command for configuration '{key}'.")
            return False
