# app.py

from flask import Flask, render_template, request, redirect, url_for, Response, jsonify
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import threading
from scanner_interface import ScannerInterface
from configurations import Configurations
from concurrent.futures import ThreadPoolExecutor
import time
from project_manager import ProjectManager  # Import ProjectManager

app = Flask(__name__)

# Determine the base directory where app.py is located
base_dir = os.path.dirname(os.path.abspath(__file__))

# Set up the output directory relative to base_dir
output_directory = os.path.join(base_dir, "output")

# Ensure the output directory exists
os.makedirs(output_directory, exist_ok=True)

# Initialize ProjectManager
project_manager = ProjectManager(output_directory)

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
sensor_lock = threading.Lock()  # Lock for sensor handle access
executor = ThreadPoolExecutor(max_workers=5)  # Thread pool executor with a maximum of 5 workers
connecting_attempt = False  # Flag to track if a connection attempt is in progress

def initialize():
    global scanner, config_manager, connecting_attempt
    time.sleep(2)  # Wait for 2 seconds to ensure network is up
    # Determine the SDK library path based on the operating system
    if sys.platform.startswith('win'):
        lib_relative_path = os.path.join("Software_ShapeDriveG4_SDK_Windows", "Sensor3D", "Sensor3d.dll")
    else:
        lib_relative_path = os.path.join("Software_ShapeDriveG4_SDK_Linux", "Sensor3D", "lib", "libSensor3D.so")
    
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
    global scanner
    with sensor_lock:
        if scanner is not None:
            scanner.disconnect()
            logger.info("Scanner disconnected.")
        else:
            logger.warning("Attempted to disconnect scanner, but scanner instance is None.")

# Initialize scanner and configurations
initialize()

def background_ping():
    """
    Background thread to ping the sensor and update connection status periodically.
    """
    global scanner
    while True:
        with sensor_lock:
            if scanner:
                connected = scanner.ping_sensor()
                # Update connection status in a way that can be accessed by the frontend
                with app.app_context():
                    app.config['CONNECTED'] = connected
        time.sleep(10)  # Ping every 10 seconds

# Start the background thread for pinging the sensor
ping_thread = threading.Thread(target=background_ping, daemon=True)
ping_thread.start()

# Route for the home page
@app.route('/')
def index():
    """
    Render the index page without attempting to reconnect.
    """
    logger.info("Rendering the index page.")
    
    # Read the logs from the log file
    try:
        with open(log_file_path, 'r') as log_file:
            logs = log_file.read()
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        logs = "Error reading logs."

    # Load projects
    projects = project_manager.load_projects()

    # Render the index.html template with configurations, projects, and logs
    return render_template(
        'index.html',
        configurations=config_manager.configurations if config_manager else {},
        output_directory=output_directory,
        logs=logs,
        projects=projects
    )

@app.route('/scanner_status')
def scanner_status():
    """
    Return the current scanner connection status.
    """
    status = {
        'connected': scanner.sensorHandle is not None if scanner else False,
        'connecting': connecting_attempt
    }
    return jsonify(status)

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
    If the scanner is not connected, update configurations locally with default values.
    """
    global config_manager
    if config_manager is None:
        logger.error("Configurations manager is not available.")
        return "Configurations manager is not available.", 400

    # Iterate through each configuration key and update its value
    for key in list(config_manager.configurations.keys()):
        value = request.form.get(key)
        if value is not None:
            success = config_manager.update_configuration(key, value)
            if not success:
                logger.error(f"Failed to set configuration: {key} to value: {value}")
                return f"Failed to set {key}", 400

    logger.info("All configurations updated successfully.")
    return redirect(url_for('index'))

@app.route('/start_scan', methods=['POST'])
def start_scan():
    """
    Handle scan initiation request from the user.
    Expects JSON data with 'nrScans', 'scanInterval', and optionally 'selectedProject'.
    """
    global scan_in_progress
    if scanner is None or not scanner.sensorHandle:
        logger.error("Scanner is not connected.")
        return jsonify({"status": "error", "message": "Scanner is not connected."}), 400
    with scan_lock:
        if scan_in_progress:
            logger.warning("Attempted to start a scan while another scan is in progress.")
            return jsonify({"status": "error", "message": "Scan is already in progress."}), 400
        try:
            data = request.get_json()
            nrScans = int(data.get('nrScans', 1))
            scan_interval = int(data.get('scanInterval', 1))  # Default to 1 second
            selected_project = data.get('selectedProject')  # Optional
            if nrScans < 1:
                raise ValueError("Number of scans must be at least 1.")
            if scan_interval < 1:
                raise ValueError("Scan interval must be at least 1 second.")
        except (ValueError, TypeError) as ve:
            logger.error(f"Invalid input provided: {ve}")
            return jsonify({"status": "error", "message": f"Invalid input: {ve}"}), 400

        # If no project is selected, create a new one with the current timestamp
        if not selected_project:
            try:
                selected_project = project_manager.create_project()
                logger.info(f"Created new project: {selected_project}")
            except Exception as e:
                logger.error(f"Error creating project: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500
        else:
            # Verify that the selected project exists
            if selected_project not in project_manager.load_projects():
                logger.error(f"Selected project '{selected_project}' does not exist.")
                return jsonify({"status": "error", "message": "Selected project does not exist."}), 400

        scan_in_progress = True
        logger.info(f"Starting scan with {nrScans} scan(s), interval of {scan_interval} seconds, project '{selected_project}'.")
        executor.submit(scan_thread, nrScans, scan_interval, selected_project)
    return jsonify({"status": "success", "message": "Scan started.", "project": selected_project}), 200

def scan_thread(nrScans, scan_interval, project_name):
    """
    Thread function to handle the scanning process.
    """
    global scan_in_progress
    try:
        for scan_num in range(1, nrScans + 1):
            if not scan_in_progress:
                logger.info("Scan process was interrupted.")
                break

            logger.info(f"Initiating scan {scan_num} for project '{project_name}'.")

            # Create a new scan folder
            scan_folder_path = project_manager.create_scan_folder(project_name)
            logger.debug(f"Scan folder path: {scan_folder_path}")

            # Initiate the scan
            if not scanner.perform_scan(nrScans=1):
                logger.error(f"Failed to initiate scan {scan_num} for project '{project_name}'.")
                continue

            # Wait for the user-defined interval
            logger.info(f"Scanning for {scan_interval} seconds (Scan {scan_num}/{nrScans}).")
            time.sleep(scan_interval)

            # Stop the scan
            if not scanner.stop_scan():
                logger.error(f"Failed to stop scan {scan_num} for project '{project_name}'.")
                continue

            # Note: Since perform_scan handles the scanning and saving, additional handling may not be necessary
            logger.info(f"Completed scan {scan_num} for project '{project_name}'.")

    except Exception as e:
        logger.exception(f"An error occurred during the scan thread: {e}")
    finally:
        with scan_lock:
            scan_in_progress = False
        logger.info("Scan thread completed and scan_in_progress flag reset.")

@app.route('/stop_scan', methods=['POST'])
def stop_scan():
    """
    Handle scan termination request from the user.
    """
    global scan_in_progress
    if scanner is not None:
        try:
            if scanner.stop_scan():
                with scan_lock:
                    scan_in_progress = False
                logger.info("Scan stopped successfully.")
                return jsonify({"status": "success", "message": "Scan stopped."}), 200
            else:
                logger.error("Failed to send stop command to the scanner.")
                return jsonify({"status": "error", "message": "Failed to stop scan."}), 500
        except Exception as e:
            logger.error(f"Failed to send stop command to the scanner: {e}")
            return jsonify({"status": "error", "message": "Exception occurred while stopping scan."}), 500
    else:
        logger.warning("Attempted to stop scan, but scanner instance is None.")
        return jsonify({"status": "error", "message": "Scanner is not connected."}), 400


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
    """
    Retrieve the latest reduced point cloud file.
    """
    # Since perform_scan saves the reduced point cloud, serve it if exists
    reduced_pcd_filename = os.path.join(output_directory, "reduced_point_cloud.ply")
    if os.path.exists(reduced_pcd_filename):
        try:
            with open(reduced_pcd_filename, 'rb') as f:
                data = f.read()
            response = Response(data, mimetype='application/octet-stream')
            response.headers['Content-Disposition'] = f'attachment; filename=reduced_point_cloud.ply'
            return response
        except Exception as e:
            logger.error(f"Error serving reduced point cloud: {e}")
            return "Error retrieving reduced point cloud.", 500
    else:
        logger.warning("Requested reduced point cloud, but no point cloud is saved.")
        return "No reduced point cloud available.", 404

@app.route('/is_processing')
def is_processing():
    """
    Check if a scan is currently in progress.
    """
    return jsonify({'processing': scan_in_progress})

# Project Management Routes

@app.route('/rename_project', methods=['POST'])
def rename_project():
    """
    Handle the rename project action.
    Expects JSON data with 'oldName' and 'newName'.
    """
    data = request.get_json()
    old_name = data.get('oldName')
    new_name = data.get('newName')

    if not old_name or not new_name:
        return jsonify({'status': 'error', 'message': 'Invalid data provided.'}), 400

    try:
        project_manager.rename_project(old_name, new_name)
        logger.info(f"Renamed project from '{old_name}' to '{new_name}'.")
        return jsonify({'status': 'success'}), 200
    except FileNotFoundError as e:
        logger.error(e)
        return jsonify({'status': 'error', 'message': str(e)}), 404
    except FileExistsError as e:
        logger.error(e)
        return jsonify({'status': 'error', 'message': str(e)}), 409
    except ValueError as e:
        logger.error(e)
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred.'}), 500

@app.route('/create_project', methods=['POST'])
def create_project():
    """
    Handle the create project action.
    Expects JSON data with 'projectName' (optional).
    """
    data = request.get_json()
    project_name = data.get('projectName')

    logger.info(f"Received request to create project: {project_name}")

    try:
        created_project = project_manager.create_project(name=project_name)
        logger.info(f"Created new project: {created_project}")
        return jsonify({'status': 'success', 'project': created_project}), 200
    except FileExistsError as e:
        logger.error(f"FileExistsError: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 409
    except ValueError as e:
        logger.error(f"ValueError: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.exception(f"Unexpected error while creating project: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to create project.'}), 500

@app.route('/delete_project', methods=['POST'])
def delete_project():
    """
    Handle the delete project action.
    Expects JSON data with 'projectName'.
    """
    data = request.get_json()
    project_name = data.get('projectName')

    if not project_name:
        return jsonify({'status': 'error', 'message': 'Project name not provided.'}), 400

    try:
        project_manager.delete_project(project_name)
        logger.info(f"Deleted project: {project_name}")
        return jsonify({'status': 'success'}), 200
    except FileNotFoundError as e:
        logger.error(e)
        return jsonify({'status': 'error', 'message': str(e)}), 404
    except ValueError as e:
        logger.error(e)
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to delete project.'}), 500

@app.route('/get_sensor_status', methods=['GET'])
def get_sensor_status():
    """
    Endpoint to retrieve the scanner's current sensor status.
    Usage:
        curl http://localhost:5001/get_sensor_status
    """
    if scanner is None:
        logger.error("Scanner instance is None.")
        return jsonify({'status': 'error', 'message': 'Scanner not initialized.'}), 500

    status = scanner.get_sensor_status()

    if status['connected']:
        return jsonify({
            'status': 'connected',
            'error_code': status['error_code']
        }), 200
    else:
        return jsonify({
            'status': 'disconnected',
            'error_code': status['error_code']
        }), 200

@app.route('/ping_status')
def ping_status():
    """
    Return the current ping status of the sensor.
    """
    connected = app.config.get('CONNECTED', False)
    return jsonify({'connected': connected})

@app.route('/attempt_reconnect', methods=['POST'])
def attempt_reconnect():
    """
    Attempt to reconnect to the scanner.

    Changes made:
    - Removed automatic reconnection attempts.
    - Added a manual reconnection button in the UI.
    - This function is called when the manual reconnect button is pressed.
    - It checks if the scanner is not connected and no reconnection attempt is in progress.
    - If conditions are met, it attempts to reconnect to the scanner.
    - Updates the connection status and reloads configurations if reconnection is successful.
    - Returns a JSON response indicating the result of the reconnection attempt.
    """
    global scanner, connecting_attempt
    with sensor_lock:
        if scanner and not scanner.connected and not connecting_attempt:
            logger.info("Attempting to reconnect to the scanner...")
            connecting_attempt = True
            if scanner.connect():
                logger.info("Scanner reconnected successfully.")
                try:
                    config_manager.read_all_configurations()
                    logger.info("Configurations reloaded after reconnection.")
                    connecting_attempt = False
                    return jsonify({"status": "success", "message": "Reconnected successfully."}), 200
                except Exception as e:
                    logger.error(f"Failed to read configurations after reconnection: {e}")
                    connecting_attempt = False
                    return jsonify({"status": "error", "message": "Reconnected but failed to read configurations."}), 500
            else:
                logger.warning("Failed to reconnect to the scanner.")
                connecting_attempt = False
                return jsonify({"status": "error", "message": "Failed to reconnect."}), 500
        else:
            return jsonify({"status": "error", "message": "Scanner is already connected or reconnection is in progress."}), 400

if __name__ == '__main__':
    try:
        # Run the Flask application
        app.run(host='0.0.0.0', port=5001, debug=True)
    finally:
        # Ensure the scanner is disconnected on application shutdown
        disconnect_scanner()
        logger.info("Scanner disconnected on application shutdown.")
