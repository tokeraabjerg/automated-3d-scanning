from flask import Flask, render_template, request, redirect, url_for, Response, jsonify, send_from_directory
import numpy as np
import os
import threading
import logging
from logging.handlers import RotatingFileHandler
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

# Set up logging with RotatingFileHandler
log_file_path = os.path.join(base_dir, 'app.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

rotating_handler = RotatingFileHandler(log_file_path, maxBytes=10*1024*1024, backupCount=5)
rotating_handler.setLevel(logging.INFO)
rotating_handler.setFormatter(formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.handlers = []  # Remove existing handlers
root_logger.addHandler(rotating_handler)
root_logger.setLevel(logging.INFO)

# Configure Flask app's logger
app.logger.handlers = []
app.logger.addHandler(rotating_handler)
app.logger.setLevel(logging.INFO)

# Disable Werkzeug logging to reduce clutter
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Initialize the logger
logger = logging.getLogger(__name__)

logger.info("Flask application has started.")

# Global variables
scanner = None
config_manager = None
scan_in_progress = False
scan_lock = threading.Lock()  # Lock for scan_in_progress
executor = ThreadPoolExecutor(max_workers=5)  # Thread pool executor with a maximum of 5 workers


def initialize():
    global scanner, config_manager
    # Determine the SDK library path based on the operating system
    if sys.platform.startswith('win'):
        # Corrected DLL filename to 'Sensor3d.dll' (with a lowercase 'd')
        lib_relative_path = os.path.join("Software_ShapeDriveG4_SDK_Windows", "Sensor3D", "Sensor3d.dll")
    else:
        lib_relative_path = os.path.join("Software_ShapeDriveG4_SDK_Linux_x86_64_1.3.0", "Sensor3D", "lib", "libSensor3D.so")
    
    lib_path = os.path.join(base_dir, lib_relative_path)
    
    try:
        if not os.path.exists(lib_path):
            logger.error(f"SDK library not found at {lib_path}")
            config_manager = Configurations()  # Initialize with default configurations
            return

        scanner = ScannerInterface(lib_path, output_directory=output_directory)  # Pass output_directory
        if scanner.connect():
            config_manager = Configurations(scanner)
            try:
                config_manager.read_all_configurations()
                logger.info("Configuration Manager initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to read configurations: {e}")
                # Proceed with default configurations
        else:
            logger.warning("Failed to connect to the sensor. Proceeding with default configurations.")
            config_manager = Configurations()  # Initialize with default configurations
    except Exception as e:
        logger.error(f"Error initializing scanner or configuration manager: {e}")
        config_manager = Configurations()  # Initialize with default configurations


def disconnect_scanner():
    """
    Disconnect the scanner if it is connected.
    """
    if scanner is not None:
        scanner.disconnect()
        logger.info("Scanner disconnected.")
    else:
        logger.warning("Attempted to disconnect scanner, but scanner instance is None.")


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
        if scanner.connect():
            try:
                config_manager.read_all_configurations()
                logger.info("Configuration Manager re-initialized after successful connection.")
            except Exception as e:
                logger.error(f"Failed to read configurations: {e}")
        else:
            logger.warning("Scanner not connected. Proceeding without sensor data.")
    
    elif scanner is not None:
        # Attempt to read configurations if the scanner is already connected
        try:
            config_manager.read_all_configurations()
            logger.info("Configurations read successfully.")
        except Exception as e:
            logger.error(f"Failed to read configurations: {e}")

    # Read the logs from the log file
    try:
        with open(log_file_path, 'r') as log_file:
            logs = log_file.read()
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        logs = "Error reading logs."

    # Render the index.html template with configurations and logs
    return render_template(
        'index.html',
        configurations=config_manager.configurations if config_manager else {},
        output_directory=output_directory,
        logs=logs
    )

@app.route('/get_configurations', methods=['GET'])
def get_configurations():
    """
    Return the current configurations as JSON.
    This can be used by the frontend to dynamically update the configurations after initial load.
    """
    if config_manager:
        return jsonify(config_manager.configurations)
    else:
        logger.error("Configurations manager is not available.")
        return jsonify({}), 500

@app.route('/update_configurations', methods=['POST'])
def update_configurations():
    """
    Update scanner configurations based on form data.
    """
    global config_manager
    if config_manager is None:
        logger.error("Configurations manager is not available.")
        return "Configurations manager is not available.", 400
    # Iterate through each configuration key and update its value
    for key in list(config_manager.configurations.keys()):
        value = request.form.get(key)
        if value is not None:
            if not config_manager.update_configuration(key, value):
                logger.error(f"Failed to set configuration: {key} to value: {value}")
                return f"Failed to set {key}", 400
    logger.info("All configurations updated successfully.")
    return redirect(url_for('index'))

@app.route('/start_scan', methods=['POST'])
def start_scan():
    global scan_in_progress
    if scanner is None or not scanner.sensorHandle:
        logger.error("Scanner is not connected.")
        return "Scanner is not connected.", 400
    with scan_lock:
        if scan_in_progress:
            logger.warning("Attempted to start a scan while another scan is in progress.")
            return "Scan is already in progress.", 400
        try:
            nrScans = int(request.form.get('nrScans', 1))
            if nrScans < 1:
                raise ValueError("Number of scans must be at least 1.")
        except ValueError as ve:
            logger.error(f"Invalid number of scans provided: {ve}")
            return "Invalid number of scans.", 400

        scan_in_progress = True
        logger.info(f"Starting scan with {nrScans} scan(s).")
        executor.submit(scan_thread, nrScans)
    return redirect(url_for('index'))

def scan_thread(nrScans):
    global scan_in_progress
    try:
        scanner.perform_scan(nrScans)
    except Exception as e:
        logger.exception(f"An error occurred during scanning: {e}")
    finally:
        with scan_lock:
            scan_in_progress = False
        logger.info("Scan process completed and scan_in_progress flag reset.")

@app.route('/stop_scan', methods=['POST'])
def stop_scan():
    global scan_in_progress
    if scanner is not None:
        try:
            if scanner.write_sensor_command("SetAcquisitionStop\r"):
                with scan_lock:
                    scan_in_progress = False
                logger.info("Scan stopped successfully.")
            else:
                logger.error("Failed to send stop command to the scanner.")
        except Exception as e:
            logger.error(f"Failed to send stop command to the scanner: {e}")
    else:
        logger.warning("Attempted to stop scan, but scanner instance is None.")
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
        try:
            os.makedirs(new_directory, exist_ok=True)
            output_directory = new_directory
            if scanner:
                scanner.output_directory = output_directory  # Update scanner's output_directory
            logger.info(f"Output directory changed to {output_directory}")
        except Exception as e:
            logger.error(f"Failed to change output directory to {new_directory}: {e}")
            return "Failed to change output directory.", 400
    else:
        logger.warning("No output directory provided in the request.")
    return redirect(url_for('index'))

@app.route('/get_logs')
def get_logs():
    """
    Get the application logs.
    """
    try:
        with open(log_file_path, 'r') as log_file:
            logs = log_file.read()
        # Optional: Sanitize logs by removing null bytes
        sanitized_logs = logs.replace('\x00', '')
        response = Response(sanitized_logs, mimetype='text/plain; charset=utf-8')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return "Error reading logs.", 500

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """
    Shutdown the Flask application.
    """
    disconnect_scanner()
    logger.info("Application shutdown initiated.")
    func = request.environ.get('werkzeug.server.shutdown')
    if func:
        func()
        logger.info("Server shutdown successfully.")
        return 'Server shutting down...'
    else:
        logger.error("Shutdown function not found. Unable to shut down the server.")
        return 'Server shutdown failed.', 500

@app.route('/get_reduced_point_cloud')
def get_reduced_point_cloud():
    reduced_point_cloud_path = os.path.join(output_directory, 'reduced_point_cloud.ply')
    if not os.path.exists(reduced_point_cloud_path):
        logger.warning(f"Reduced point cloud not found at {reduced_point_cloud_path}")
        return "No reduced point cloud available.", 404
    return send_from_directory(output_directory, 'reduced_point_cloud.ply')

@app.route('/is_processing')
def is_processing():
    return jsonify({'processing': scan_in_progress})


if __name__ == '__main__':
    try:
        # Run the Flask application
        app.run(host='0.0.0.0', port=5001, debug=True)
    finally:
        # Ensure the scanner is disconnected on application shutdown
        disconnect_scanner()
        logger.info("Scanner disconnected on application shutdown.")
