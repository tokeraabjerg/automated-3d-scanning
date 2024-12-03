import ctypes
import os

# Set the path to the SDK library
lib_path = "/workspace/scanner_interface/Software_ShapeDriveG4_SDK_Linux/Sensor3D/lib/libSensor3D.so"

# Load the SDK library
sdk = ctypes.CDLL(lib_path)

# Call a function from the SDK (replace with an actual function from the SDK)
try:
    version = ctypes.create_string_buffer(256)
    result = sdk.Sensor3D_GetVersion(version, 256)
    if result == 0:  # Assuming 0 is the success code
        print(f"SDK Version: {version.value.decode()}")
    else:
        print(f"Failed to get SDK version, error code: {result}")
except Exception as e:
    print(f"Error calling SDK function: {e}")