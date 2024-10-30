from flask import Flask, render_template, request, redirect, url_for, Response, jsonify, send_from_directory
import numpy as np
import os
import threading
import logging
import io
import sys
from scanner_interface import ScannerInterface
from configurations import Configurations
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Determine the base directory where app.py is located
base_dir = os.path.dirname(os.path.abspath(__file__))

# Set up the output directory relative to base_dir
output_directory = os.path.join(base_dir, "output")

# Ensure the output directory exists
os.makedirs(output_directory, exist_ok=True)

# Set up logging
log_stream = io.StringIO()

# Create a handler that writes to the StringIO object
stream_handler = logging.StreamHandler(log_stream)
stream_handler.setLevel(logging.INFO)

# Set a formatter (optional, but recommended)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(formatter)

# Get the root logger and clear any existing handlers
root_logger = logging.getLogger()
root_logger.handlers = []  # Remove any existing handlers
root_logger.addHandler(stream_handler)
root_logger.setLevel(logging.INFO)

# Optionally, configure the Flask app's logger
app.logger.handlers = []  # Remove any existing handlers
app.logger.addHandler(stream_handler)
app.logger.setLevel(logging.INFO)

# Disable Werkzeug logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)  # Set Werkzeug logging to ERROR

# Now, use the root logger or app.logger in your code
logger = logging.getLogger(__name__)

logger.info("Flask application has started.")

# Global variables
scanner = None
config_manager = None
scan_in_progress = False
executor = ThreadPoolExecutor(max_workers=5)  # Thread pool executor with a maximum of 5 workers


def initialize():
    global scanner, config_manager
    # Determine the SDK library path based on the operating system
    if sys.platform.startswith('win'):
        lib_relative_path = os.path.join("Software_ShapeDriveG4_SDK_Windows", "Sensor3D", "Sensor3d.dll")
    else:
        lib_relative_path = os.path.join("Software_ShapeDriveG4_SDK_Linux_x86_64_1.3.0", "Sensor3D", "lib", "libSensor3D.so")
    
    lib_path = os.path.join(base_dir, lib_relative_path)
    
    try:
        if not os.path.exists(lib_path):
            logger.error(f"SDK library not found at {lib_path}")
            return

        scanner = ScannerInterface(lib_path, output_directory=output_directory)  # Pass output_directory
        config_manager = Configurations(scanner)
        if not scanner.connect():
            logger.error("Failed to connect to the sensor.")
        else:
            config_manager.read_all_configurations()
    except Exception as e:
        logger.error(f"Error initializing scanner: {e}")


def disconnect_scanner():
    """
    Disconnect the scanner if it is connected.
    """
    if scanner is not None:
        scanner.disconnect()


# Initialize scanner and configurations
initialize()

# Route for the home page
@app.route('/')
def index():
    """
    Render the index page.
    If the scanner is not connected, attempt to reconnect.
    """
    logger.info("Rendering the index page.")
    global config_manager
    if scanner is not None and not scanner.sensorHandle:
        # Attempt to connect if the scanner handle is not available
        if not scanner.connect():
            logger.warning("Scanner not connected. Proceeding without sensor data.")
        else:
            # Read configurations if the scanner connects successfully
            config_manager.read_all_configurations()
    elif scanner is not None:
        # Read configurations if the scanner is already connected
        config_manager.read_all_configurations()

    # Get the log contents
    logs = log_stream.getvalue()

    # Render the index.html template with configurations and logs
    return render_template(
        'index.html',
        configurations=config_manager.configurations if config_manager else {},
        output_directory=output_directory,
        logs=logs
    )

@app.route('/update_configurations', methods=['POST'])
def update_configurations():
    """
    Update scanner configurations based on form data.
    """
    global config_manager
    if config_manager is None:
        return "Configurations manager is not available.", 400
    # Iterate through each configuration key and update its value
    for key in list(config_manager.configurations.keys()):
        value = request.form.get(key)
        if value is not None:
            if not config_manager.update_configuration(key, value):
                return f"Failed to set {key}", 400
    return redirect(url_for('index'))

@app.route('/start_scan', methods=['POST'])
def start_scan():
    global scan_in_progress
    if scanner is None or not scanner.sensorHandle:
        return "Scanner is not connected.", 400
    if scan_in_progress:
        return "Scan is already in progress.", 400
    try:
        nrScans = int(request.form.get('nrScans', 1))
    except ValueError:
        return "Invalid number of scans.", 400

    scan_in_progress = True
    executor.submit(scan_thread, nrScans)
    return redirect(url_for('index'))

def scan_thread(nrScans):
    global scan_in_progress
    try:
        scanner.perform_scan(nrScans)
    finally:
        scan_in_progress = False

@app.route('/stop_scan', methods=['POST'])
def stop_scan():
    global scan_in_progress
    if scanner is not None:
        try:
            scanner.write_sensor_command("SetAcquisitionStop\r")
            scan_in_progress = False
            logger.info("Scan stopped successfully.")
        except Exception as e:
            logger.error(f"Failed to send stop command to the scanner: {e}")
    return redirect(url_for('index'))

@app.route('/change_output_directory', methods=['POST'])
def change_output_directory():
    global output_directory
    new_directory = request.form.get('output_directory')
    if new_directory:
        # Make the new directory path relative to base_dir if it's not absolute
        if not os.path.isabs(new_directory):
            new_directory = os.path.join(base_dir, new_directory)
        # Ensure the new output directory exists
        os.makedirs(new_directory, exist_ok=True)
        output_directory = new_directory
        scanner.output_directory = output_directory  # Update scanner's output_directory
        logger.info(f"Output directory changed to {output_directory}")
    return redirect(url_for('index'))

@app.route('/get_logs')
def get_logs():
    """
    Get the application logs.
    """
    logs = log_stream.getvalue()
    response = Response(logs, mimetype='text/plain; charset=utf-8')
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """
    Shutdown the Flask application.
    """
    disconnect_scanner()
    logger.info("Application shutdown.")
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()
    return 'Server shutting down...'

@app.route('/get_reduced_point_cloud')
def get_reduced_point_cloud():
    reduced_point_cloud_path = os.path.join(output_directory, 'reduced_point_cloud.ply')
    if not os.path.exists(reduced_point_cloud_path):
        return "No reduced point cloud available.", 404
    return send_from_directory(output_directory, 'reduced_point_cloud.ply')

@app.route('/is_processing')
def is_processing():
    return jsonify({'processing': scan_in_progress})

# Modified Route: Get 3D Preview Setting
@app.route('/get_3d_preview_setting', methods=['GET'])
def get_3d_preview_setting():
    """
    Get the current setting of the 3D preview from the server.
    """
    if config_manager:
        # Retrieve the current value of '3D Preview Enabled'
        is_enabled = config_manager.configurations.get('3D Preview Enabled', {}).get('value', True)
        # Convert the value to a boolean
        is_enabled_bool = True if is_enabled in ['1', 'True', 'true'] else False
        return jsonify({'3DPreviewEnabled': is_enabled_bool})
    else:
        logger.error("Configurations manager is not available.")
        # Default to True if configurations are unavailable
        return jsonify({'3DPreviewEnabled': True}), 500

# New Route: Set 3D Preview Setting
@app.route('/set_3d_preview_setting', methods=['POST'])
def set_3d_preview_setting():
    """
    Set the 3D preview setting based on user input.
    Expects a form parameter '3DPreviewEnabled' with value '1' or '0'.
    """
    global config_manager
    if config_manager is None:
        logger.error("Configurations manager is not available.")
        return jsonify({'status': 'failure', 'message': 'Configurations manager is not available.'}), 400

    # Retrieve the '3DPreviewEnabled' value from the form data
    is_enabled = request.form.get('3DPreviewEnabled')
    if is_enabled is None:
        logger.error("3DPreviewEnabled parameter is missing in the request.")
        return jsonify({'status': 'failure', 'message': '3DPreviewEnabled parameter is missing.'}), 400

    # Validate and convert the input to '1' or '0'
    if is_enabled in ['1', 'True', 'true', 'yes', 'on']:
        value = '1'
    else:
        value = '0'

    # Update the configuration using the Configurations class
    success = config_manager.update_configuration('3D Preview Enabled', value)

    if success:
        logger.info(f"3D Preview Enabled set to {value}")
        # Return the updated status
        return jsonify({'status': 'success', '3DPreviewEnabled': value == '1'}), 200
    else:
        logger.error("Failed to update 3D Preview Enabled configuration.")
        return jsonify({'status': 'failure', 'message': 'Failed to update configuration.'}), 500


if __name__ == '__main__':
    try:
        # Run the Flask application
        app.run(host='0.0.0.0', port=5001, debug=True)
    finally:
        # Ensure the scanner is disconnected on application shutdown
        disconnect_scanner()
