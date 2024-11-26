#---------------------------------------------------------------------------
#  ?                                ABOUT
#  @author         :  Toke Raabjerg
#  @repo           :  https://github.com/Tokeraabjerg/automated-3d-scanning
#  @description    :  This module defines the routes for handling scan operations.
#                     It includes routes for starting, stopping, and checking the status of scans.
#---------------------------------------------------------------------------

from flask import Blueprint, request, jsonify, current_app
import logging
import threading
import os
from concurrent.futures import ThreadPoolExecutor
import open3d as o3d

scan_bp = Blueprint('scan_bp', __name__, url_prefix='/scan')  # Added url_prefix='/scan'
logger = logging.getLogger(__name__)

@scan_bp.route('/start_scan', methods=['POST'])
def start_scan():
    """
    Handle scan initiation request from the user.
    Initiates a single scan.
    """
    scan_in_progress = current_app.config.get('scan_in_progress', False)
    scan_lock = current_app.config.get('scan_lock')
    stop_event = current_app.config.get('stop_event')
    executor = current_app.config.get('executor')

    scanner = current_app.config.get('scanner')
    project_manager = current_app.config.get('project_manager')
    output_directory = current_app.config.get('output_directory')

    if scanner is None or not scanner.sensorHandle:
        logger.error("Scanner is not connected.")
        return jsonify({"status": "error", "message": "Scanner is not connected."}), 400

    with scan_lock:
        if scan_in_progress:
            logger.warning("Attempted to start a scan while another scan is in progress.")
            return jsonify({"status": "error", "message": "Scan is already in progress."}), 400
        try:
            data = request.get_json()
            scan_interval = int(data.get('scanInterval', 3))  # Default to 3 seconds
            selected_project = data.get('selectedProject')  # Optional
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

        current_app.config['scan_in_progress'] = True
        stop_event.clear()  # Reset the stop_event before starting a new scan
        logger.info(f"Starting scan, interval of {scan_interval} seconds, project '{selected_project}'.")
        executor.submit(scan_thread, scan_interval, selected_project)
    return jsonify({"status": "success", "message": "Scan started.", "project": selected_project}), 200

def scan_thread(scan_interval, project_name):
    """
    Thread function to handle the scanning process.
    """
    scan_lock = current_app.config.get('scan_lock')
    scan_in_progress = current_app.config.get('scan_in_progress')
    stop_event = current_app.config.get('stop_event')
    scanner = current_app.config.get('scanner')
    output_directory = current_app.config.get('output_directory')

    try:
        # Corrected perform_scan call
        pcds = scanner.perform_scan(scan_interval=scan_interval, stop_event=stop_event)

        for idx, pcd in enumerate(pcds, start=1):
            # Save the point cloud as a .ply file
            output_filename = os.path.join(output_directory, f"{project_name}_point_cloud_{idx}.ply")
            o3d.io.write_point_cloud(output_filename, pcd)
            logger.info(f"Saved point cloud to {output_filename}")
    except Exception as e:
        logger.exception(f"An error occurred during scanning: {e}")
    finally:
        with scan_lock:
            current_app.config['scan_in_progress'] = False
        logger.info("Scan process completed and scan_in_progress flag reset.")

@scan_bp.route('/stop_scan', methods=['POST'])
def stop_scan():
    """
    Handle scan termination request from the user by setting the stop_event.
    This signals the scanning thread to stop the scan gracefully.
    """
    scan_in_progress = current_app.config.get('scan_in_progress', False)
    stop_event = current_app.config.get('stop_event')
    scanner = current_app.config.get('scanner')

    if scanner is not None:
        try:
            stop_event.set()  # Signal the scanning thread to stop
            with current_app.config['scan_lock']:
                current_app.config['scan_in_progress'] = False
            logger.info("Scan stopped successfully.")
            return jsonify({"status": "success", "message": "Scan stopped."}), 200
        except Exception as e:
            logger.error(f"Failed to send stop command to the scanner: {e}")
            return jsonify({"status": "error", "message": "Exception occurred while stopping scan."}), 500
    else:
        logger.warning("Attempted to stop scan, but scanner instance is None.")
        return jsonify({"status": "error", "message": "Scanner is not connected."}), 400

@scan_bp.route('/is_processing', methods=['GET'])
def is_processing():
    """
    Check if a scan is currently in progress.
    """
    scan_in_progress = current_app.config.get('scan_in_progress', False)
    return jsonify({'processing': scan_in_progress})