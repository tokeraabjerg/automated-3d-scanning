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

@scan_bp.route('/manual_capture', methods=['POST'])
def manual_capture():
    """
    Start a manual capture scan.
    """
    data = request.json
    scan_interval = data.get('scanInterval')
    project_name = data.get('selectedProject')

    if not scan_interval or not project_name:
        return jsonify({'status': 'error', 'message': 'Scan interval and project name are required'}), 400

    try:
        # Start the scan thread
        executor = current_app.config['executor']
        stop_event = current_app.config['stop_event']
        scan_lock = current_app.config['scan_lock']
        scan_in_progress = current_app.config['scan_in_progress']

        with scan_lock:
            if scan_in_progress:
                return jsonify({'status': 'error', 'message': 'A scan is already in progress'}), 400
            current_app.config['scan_in_progress'] = True

        future = executor.submit(scan_thread, scan_interval, project_name, stop_event)
        future.add_done_callback(lambda x: current_app.config.update(scan_in_progress=False))

        return jsonify({'status': 'success', 'project': project_name}), 200
    except Exception as e:
        current_app.logger.error(f"Error starting manual capture: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def scan_thread(app, scan_interval, project_name):
    """
    Thread function to handle the scanning process.
    """
    logger.info("Scan thread started.")
    
    with app.app_context():
        try:
            scan_lock = current_app.config.get('scan_lock')
            if scan_lock is None:
                logger.error("scan_lock is None. Exiting scan thread.")
                return

            scanner = current_app.config.get('scanner')
            if scanner is None:
                logger.error("scanner is None. Exiting scan thread.")
                return

            output_directory = current_app.config.get('output_directory')

            pcd = scanner.perform_scan(scan_interval=scan_interval, stop_event=current_app.config.get('stop_event'))
            if pcd is None:
                logger.error("Failed to perform scan. Exiting scan thread.")
                return

            # Replace direct saving with ProjectManager's save_point_cloud method
            project_manager = current_app.config.get('project_manager')
            project_manager.save_point_cloud(pcd, project_name)

            #call icp function
            
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
    logger.info("Starting stop scan request.")
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

@scan_bp.route('/auto_scan', methods=['POST'])
def auto_scan():
    """
    Start an auto scan that loops through positions in positions.json.
    """
    data = request.json
    scan_interval = data.get('scanInterval')
    project_name = data.get('selectedProject')

    if not scan_interval or not project_name:
        return jsonify({'status': 'error', 'message': 'Scan interval and project name are required'}), 400

    # Check if the scanner is connected
    scanner = current_app.config.get('scanner')
    if not scanner or not scanner.connected:
        return jsonify({'status': 'error', 'message': 'Scanner is not connected'}), 400

    try:
        # Access project_manager through current_app
        project_manager = current_app.config['project_manager']
        positions = project_manager.get_positions(project_name)
        if positions is None:
            return jsonify({'status': 'error', 'message': 'positions.json not found or empty'}), 404

        # Start the auto scan thread
        executor = current_app.config['executor']
        stop_event = current_app.config['stop_event']
        scan_lock = current_app.config['scan_lock']
        scan_in_progress = current_app.config['scan_in_progress']

        with scan_lock:
            if scan_in_progress:
                return jsonify({'status': 'error', 'message': 'A scan is already in progress'}), 400
            current_app.config['scan_in_progress'] = True

        future = executor.submit(auto_scan_thread, scan_interval, project_name, positions, stop_event)
        future.add_done_callback(lambda x: current_app.config.update(scan_in_progress=False))

        return jsonify({'status': 'success', 'project': project_name}), 200
    except Exception as e:
        current_app.logger.error(f"Error starting auto scan: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def auto_scan_thread(scan_interval, project_name, positions, stop_event):
    """
    Thread function to perform auto scan.
    """
    scans = []  # Array to store scans
    try:
        for position in positions:
            if stop_event.is_set():
                break

            # Perform movement to the position (add actual movement code here)
            # move_to_position(position)

            # Start scan
            pcd = scan_thread(scan_interval, project_name, stop_event)
            if pcd is None:
                continue

            # Append the scan to the array
            scans.append(pcd)

            # Post-process the scan (add actual post-processing code here)
            # post_process_scan(pcd)

    except Exception as e:
        current_app.logger.error(f"Error in auto scan thread: {e}")
    finally:
        current_app.config['scan_in_progress'] = False

        # Print the total amount of scans and the number of points in each scan
        total_scans = len(scans)
        current_app.logger.info(f"Total scans completed: {total_scans}")
        for i, scan in enumerate(scans):
            num_points = len(scan.points)
            current_app.logger.info(f"Scan {i + 1}: {num_points} points")