# configurations_data.py
# This is .py is ONLY for documentation purposes. It is never called nor edited 

configurations_info = {
    'Current Acquisition Time (µs)': {
        'get_command': 'GetAcquisitionTime',
        'set_command': 'SetAcquisitionTime',
        'description': 'Determines the interval of acquiring point cloud or 2D camera images.',
        'type': 'int',
        'default': 220000,
        'min': 220000,
        'max': 500000,
    },
    'Current Exposure Time Limit (µs)': {
        'get_command': 'GetExposureTimeLimit',
        'set_command': 'SetExposureTimeLimit',
        'description': 'Sets the exposure time limit. The LED projector frequency will be adjusted accordingly.',
        'type': 'int',
        'default': 30000,
        'min': 10000,
        'max': 30000,
    },
    'Current Exposure Time (µs)': {
        'get_command': 'GetExposureTime',
        'set_command': 'SetExposureTime',
        'description': 'Sets the exposure time of the built-in camera chip.',
        'type': 'int',
        'default': 30000,
        'min': 10000,
        'max': 30000,
    },
    'Z Start (mm)': {
        'get_command': 'GetZmin',
        'set_command': 'SetZmin',
        'description': 'Sets the minimum measuring range in Z.',
        'type': 'float',
        'default': 270.0,
        'min': 220.0,
        'max': 470.0,
    },
    'Z End (mm)': {
        'get_command': 'GetZmax',
        'set_command': 'SetZmax',
        'description': 'Sets the maximum measuring range in Z.',
        'type': 'float',
        'default': 470.0,
        'min': 270.0,
        'max': 600.0,
    },
    'Contrast Comparison Filter': {
        'get_command': 'GetContrastComparisonFilterMinPhase',
        'set_command': 'SetContrastComparisonFilterMinPhase',
        'description': 'Sets the filter threshold of the contrast comparison filter where 1 is the highest possible contrast and 0 is no contrast at all.',
        'type': 'float',
        'default': 0.10,
        'min': 0.0,
        'max': 1.0,
    },
    'SDK Queue Size': {
        'get_command': 'GetSDKQueueSize',
        'set_command': 'SetSDKQueueSize',
        'description': 'Sets the maximum number of point clouds buffered in SDK.',
        'type': 'int',
        'default': 5,
        'min': 1,
        'max': 100,
    },
    'Trigger Source': {
        'get_command': 'GetTriggerSource',
        'set_command': 'SetTriggerSource',
        'description': 'Sets the trigger source of the 3D sensor.',
        'type': 'enum',
        'options': {
            '0': 'Internal trigger',
            '1': 'Software trigger',
            '2': 'Hardware trigger (I/O1)',
            '3': 'Hardware trigger (I/O2)',
            '4': 'Hardware trigger (I/O3)',
            '5': 'Hardware trigger (I/O4)',
        },
        'default': '0'
    },
    'Sensor Enable': {
        'get_command': 'GetSensorEnable',
        'set_command': 'SetSensorEnable',
        'description': 'Activates the I/O data acquisition of the 3D sensor.',
        'type': 'enum',
        'options': {
            '0': 'Off',
            '1': 'I/O Line 1',
            '2': 'I/O Line 2',
            '3': 'I/O Line 3',
            '4': 'I/O Line 4',
        },
        'default': '0'
    },
    'Sensor Mode': {
        'get_command': 'GetSensorMode',
        'set_command': 'SetSensorMode',
        'description': 'Configures the 3D sensor to generate point cloud or 2D images.',
        'type': 'enum',
        'options': {
            '4': '3D Point Cloud',
            '5': '2D Camera Images',
        },
        'default': '4'
    },
    'Gain': {
        'get_command': 'GetGain',
        'set_command': 'SetGain',
        'description': 'Sets the gain of the built-in camera chip.',
        'type': 'int',
        'default': 0,
        'min': 0,
        'max': 100,
    },
    'Subsampling': {
        'get_command': 'GetSubSampling',
        'set_command': 'SetSubSampling',
        'description': 'Activates the subsampling in the built-in camera chip.',
        'type': 'enum',
        'options': {
            '0': 'Disabled',
            '1': 'Enabled',
        },
        'default': '0'
    },
    'LED Power (%)': {
        'get_command': 'GetLEDPower',
        'set_command': 'SetLEDPower',
        'description': 'Sets the brightness of the sensor’s LED projector.',
        'type': 'int',
        'default': 10,
        'min': 0,
        'max': 100,
    },
    'User LED': {
        'get_command': 'GetUserLED',
        'set_command': 'SetUserLED',
        'description': 'Sets User LED color.',
        'type': 'enum',
        'options': {
            '0': 'Off',
            '1': 'Green',
            '2': 'Red',
            '3': 'Orange',
        },
        'default': '0'
    },
    'LED Activate': {
        'get_command': 'GetLEDActivate',
        'set_command': 'SetLEDActivate',
        'description': 'Activates/deactivates the built-in LED projector.',
        'type': 'enum',
        'options': {
            '0': 'Deactivate',
            '1': 'Activate',
        },
        'default': '1'
    },
    'Extended Measuring Range': {
        'get_command': 'GetEnableExtendedMeasuringRange',
        'set_command': 'SetEnableExtendedMeasuringRange',
        'description': 'Activates/deactivates the extended working area.',
        'type': 'enum',
        'options': {
            '0': 'Deactivate',
            '1': 'Activate',
        },
        'default': '0'
    },
    # Remove 'Acquisition Start' and 'Acquisition Stop' from configurations_info
    # These are commands, not parameters, and should not be read as parameters.
}
