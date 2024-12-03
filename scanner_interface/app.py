#---------------------------------------------------------------------------
#  ?                                ABOUT
#  @author         :  Toke Raabjerg
#  @repo           :  https://github.com/Tokeraabjerg/automated-3d-scanning
#  @description    :  This is the main Flask application file for the 3D scanner control panel.
#                     It initializes the application, sets up logging, and registers routes.
#---------------------------------------------------------------------------

from flask import Flask, render_template, request, redirect, url_for, Response, jsonify, current_app
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import threading
from scanner_interface import ScannerInterface
from .configurations import Configurations
from concurrent.futures import ThreadPoolExecutor
import time
from .project_manager import ProjectManager  # Ensure ProjectManager is imported
import open3d as o3d
import numpy as np
import psutil  # Add psutil import
import subprocess  # Add this import

from scanner_interface.routes.project_routes import project_bp
from scanner_interface.routes.scan_routes import scan_bp
from scanner_interface.routes.config_routes import config_bp
from scanner_interface.routes.interface_routes import interface_bp
from scanner_interface.routes.calibration_routes import calibration_bp

app = Flask(__name__)

# Determine the base directory where app.py is located
base_dir = os.path.dirname(os.path.abspath(__file__))
app.config['base_dir'] = base_dir  # Add base_dir to app config

# Set up the output directory relative to base_dir
output_directory = os.path.join(base_dir, "output")

# Ensure the output directory exists
os.makedirs(output_directory, exist_ok=True)

# Initialize ProjectManager and store it in app config
project_manager = ProjectManager(output_directory)
app.config['project_manager'] = project_manager  
app.config['output_directory'] = output_directory 

# Set up logging with RotatingFileHandler
log_file_path = os.path.join(base_dir, 'app.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

rotating_handler = RotatingFileHandler(log_file_path, maxBytes=10*1024*1024, backupCount=5)
rotating_handler.setLevel(logging.DEBUG)  # Set to DEBUG level
rotating_handler.setFormatter(formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.handlers = []  # Remove existing handlers
root_logger.addHandler(rotating_handler)
root_logger.setLevel(logging.INFO)  # Set to DEBUG level

# Configure Flask app's logger
app.logger.handlers = []
app.logger.addHandler(rotating_handler)
app.logger.setLevel(logging.INFO)  # Set to DEBUG level

# Disable Werkzeug logging to reduce clutter
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# Initialize the logger
logger = logging.getLogger(__name__)

logger.info("Flask application has started.")

# Log memory information
memory_info = psutil.virtual_memory()
logger.info(f"Total memory: {memory_info.total / (1024 ** 3):.2f} GB")
logger.info(f"Available memory: {memory_info.available / (1024 ** 3):.2f} GB")

# Global variables
scanner = None
config_manager = None
scan_in_progress = False
scan_lock = threading.Lock()  # Lock for scan_in_progress
sensor_lock = threading.Lock()  # Lock for sensor handle access
connecting_attempt = False  # New flag to track connection attempts
stop_event = threading.Event()  # New event to signal scan stop

# Add these variables to app.config
app.config['scan_in_progress'] = scan_in_progress
app.config['scan_lock'] = scan_lock
app.config['sensor_lock'] = sensor_lock 
app.config['stop_event'] = stop_event

def initialize():
    global scanner, config_manager, connecting_attempt
    logger.info("Initializing application.")

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
            app.config['config_manager'] = config_manager  # Add this line
            return

        scanner = ScannerInterface(lib_path, output_directory=output_directory)  # Pass output_directory
        app.config['scanner'] = scanner  # Add this line
        connecting_attempt = True  # Start connection attempt
        if scanner.connect():
            connecting_attempt = False  # Connection successful
            config_manager = Configurations(scanner)
            app.config['config_manager'] = config_manager  # Add this line
            try:
                config_manager.read_all_configurations()
                logger.info("Configuration Manager initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to read configurations: {e}")
                # Proceed with default configurations
        else:
            connecting_attempt = False  # Connection failed
            logger.warning("Failed to connect to the sensor. Proceeding with default configurations.")
            config_manager = Configurations()  # Initialize with default configurations
            app.config['config_manager'] = config_manager  # Add this line
    except Exception as e:
        connecting_attempt = False  # Reset flag on exception
        logger.error(f"Error initializing scanner or configuration manager: {e}")
        config_manager = Configurations()  # Initialize with default configurations
        app.config['config_manager'] = config_manager  # Add this line

    # Initialize ProjectManager and store it in app config
    project_manager = ProjectManager(output_directory)
    app.config['project_manager'] = project_manager

    # Initialize scan-related configurations
    scan_lock = threading.Lock()
    app.config['scan_lock'] = scan_lock
    scan_in_progress = False
    app.config['scan_in_progress'] = scan_in_progress
    stop_event = threading.Event()
    app.config['stop_event'] = stop_event

    # Initialize ThreadPoolExecutor and store it in app config
    executor = ThreadPoolExecutor(max_workers=10)
    app.config['executor'] = executor

    logger.info("Initialization completed.")

def log_resource_usage(context: str):
    """
    Log the current CPU and memory usage.
    """
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    logger.info(f"{context} - CPU usage: {cpu_usage}%, Memory usage: {memory_info.percent}%")

def disconnect_scanner():
    """
    Disconnect the scanner if it is connected.
    """
    global scanner
    if scanner is not None:
        scanner.disconnect()
        logger.info("Scanner disconnected.")
    else:
        logger.warning("Attempted to disconnect scanner, but scanner instance is None.")

# Initialize scanner and configurations
initialize()

# Register Blueprints
app.register_blueprint(project_bp)
app.register_blueprint(scan_bp)
app.register_blueprint(config_bp)
app.register_blueprint(interface_bp)
app.register_blueprint(calibration_bp)

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

@app.route('/get_logs')
def get_logs():
    """
    Get the application logs.
    """
    try:
        with open(log_file_path, 'rb') as log_file:
            logs = log_file.read()
        # Sanitize logs by removing null bytes and decoding to utf-8
        sanitized_logs = logs.replace(b'\x00', b'').decode('utf-8', errors='ignore')
        response = Response(sanitized_logs, mimetype='text/plain; charset=utf-8')
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return "Error reading logs.", 500

@app.route('/get_reduced_point_cloud')
def get_reduced_point_cloud():
    """
    Retrieve the latest reduced point cloud file.
    """
    # Since scanner_interface.py does not save point clouds,
    # return 404 to prevent the frontend from attempting to load non-existent files.
    logger.warning("Requested reduced point cloud, but no point cloud is saved.")
    return "No reduced point cloud available.", 404

@app.route('/is_processing')
def is_processing():
    """
    Check if a scan is currently in progress.
    """
    return jsonify({'processing': scan_in_progress})

@app.route('/process_point_cloud', methods=['POST'])
def process_point_cloud():
    try:
        # Assume point cloud data is sent as a JSON array of points
        point_cloud_data = request.json.get('point_cloud')
        if not point_cloud_data:
            return jsonify({'status': 'error', 'message': 'No point cloud data provided'}), 400

        # Convert to Open3D point cloud
        points = np.array(point_cloud_data, dtype=np.float64)
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)

        # Downsample if more than 100,000 points
        if len(pcd.points) > 100000:
            pcd = pcd.uniform_down_sample(every_k_points=int(len(pcd.points) / 100000))

        # Convert back to list for JSON response
        downsampled_points = np.asarray(pcd.points).tolist()

        return jsonify({'status': 'success', 'point_cloud': downsampled_points})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/project/get_full_size_point_cloud', methods=['GET'])
def get_full_size_point_cloud():
    """
    Get the full-size point cloud for the specified project and scan index.
    Optionally downsample the point cloud to reduce its size.
    """
    project_name = request.args.get('projectName')
    scan_index = request.args.get('scanIndex')
    downsample = request.args.get('downsample', 'false').lower() == 'true'
    target_points = int(request.args.get('targetPoints', 100000))  # Set target_points to 100,000

    if not project_name or not scan_index:
        return jsonify({'status': 'error', 'message': 'Project name and scan index are required'}), 400

    try:
        scan_index = int(scan_index)
        project_manager = current_app.config['project_manager']
        logger.info(f"Fetching full-size point cloud for project: {project_name}, scan index: {scan_index}, downsample: {downsample}, target_points: {target_points}")
        point_cloud = project_manager.get_full_size_point_cloud(project_name, scan_index, downsample, target_points)
        logger.info(f"Successfully fetched point cloud with {len(point_cloud['points'])} points.")
        return jsonify({'status': 'success', 'point_cloud': point_cloud})
    except Exception as e:
        current_app.logger.error(f"Error fetching point cloud: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/restart_app', methods=['POST'])
def restart_app():
    """
    Restart the Flask application.
    """
    logger.info("Flask application restart initiated.")
    try:
        # Restart the application as a module
        os.execv(sys.executable, ['python3', '-m', 'scanner_interface.app'])
    except Exception as e:
        logger.error(f"Exception occurred while restarting Flask application: {e}")
        return jsonify({'status': 'error', 'message': f"Exception occurred while restarting Flask application: {e}"}), 500

def process_point_cloud_o3d(pcd: o3d.geometry.PointCloud) -> o3d.geometry.PointCloud:
    """
    Process an Open3D point cloud by downsampling it if it has more than 100,000 points.

    :param pcd: The original Open3D point cloud.
    :return: The processed (downsampled) Open3D point cloud.
    """
    try:
        # Downsample if more than 100,000 points
        if len(pcd.points) > 100000:
            pcd = pcd.uniform_down_sample(every_k_points=int(len(pcd.points) / 100000))
        return pcd
    except Exception as e:
        logger.error(f"Error processing point cloud: {e}")
        return None

if __name__ == '__main__':
    try:
        logger.info("Starting Flask application.")
        app.run(host='0.0.0.0', port=5001, debug=True)
    finally:
        disconnect_scanner()
        logger.info("Scanner disconnected on application shutdown.")
