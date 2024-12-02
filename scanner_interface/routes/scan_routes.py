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
import time
from scanner_interface.arduino_coms import perform_scan  # Import the perform_scan function
from python.Point_Cloud_Processing.PCP_main import Point_Cloud_Processing as PCP # Import the Point_Cloud_Processing function


scan_bp = Blueprint('scan_bp', __name__, url_prefix='/scan')  # Added url_prefix='/scan'
logger = logging.getLogger(__name__)

@scan_bp.route('/manual_capture', methods=['POST'])
def manual_capture():
    """
    Start a manual capture scan.
    """
    logger.debug("manual_capture route called.")
    data = request.json
    scan_interval = data.get('scanInterval')
    project_name = data.get('selectedProject')

    if not scan_interval or not project_name:
        logger.debug("Invalid data provided for manual capture.")
        return jsonify({'status': 'error', 'message': 'Scan interval and project name are required'}), 400

    try:
        # Start the scan thread
        executor = current_app.config['executor']
        stop_event = current_app.config['stop_event']
        scan_lock = current_app.config['scan_lock']
        scan_in_progress = current_app.config['scan_in_progress']

        with scan_lock:
            if scan_in_progress:
                logger.debug("A scan is already in progress.")
                return jsonify({'status': 'error', 'message': 'A scan is already in progress'}), 400
            current_app.config['scan_in_progress'] = True

        app = current_app._get_current_object()
        future = executor.submit(scan_thread, app, scan_interval, project_name, stop_event)
        future.add_done_callback(lambda x: app.app_context().push() or app.config.update(scan_in_progress=False))

        logger.debug("Manual capture scan started successfully.")
        return jsonify({'status': 'success', 'project': project_name}), 200
    except Exception as e:
        current_app.logger.error(f"Error starting manual capture: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def scan_thread(app, scan_interval, project_name, stop_event):
    """
    Thread function to handle the scanning process.
    """
    logger.debug("scan_thread function called.")
    logger.info("Scan thread started.")
    
    with app.app_context():
        try:
            scan_lock = current_app.config.get('scan_lock')
            if scan_lock is None:
                logger.error("scan_lock is None. Exiting scan thread.")
                return None

            scanner = current_app.config.get('scanner')
            if scanner is None:
                logger.error("scanner is None. Exiting scan thread.")
                return None

            output_directory = current_app.config.get('output_directory')

            pcd = scanner.perform_scan(scan_interval=scan_interval, stop_event=current_app.config.get('stop_event'))
            if pcd is None:
                logger.error("Failed to perform scan. Exiting scan thread.")
                return None

            # Replace direct saving with ProjectManager's save_point_cloud method
            project_manager = current_app.config.get('project_manager')
            project_manager.save_point_cloud(pcd, project_name)

            #call icp function
            
            return pcd
            
        except Exception as e:
            logger.exception(f"An error occurred during scanning: {e}")
            return None
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

        app = current_app._get_current_object()
        future = executor.submit(auto_scan_thread, app, scan_interval, project_name, positions, stop_event)
        future.add_done_callback(lambda x: app.app_context().push() or app.config.update(scan_in_progress=False))

        return jsonify({'status': 'success', 'project': project_name}), 200
    except Exception as e:
        current_app.logger.error(f"Error starting auto scan: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def post_process_thread(app, combined_pcd, new_pcd, project_name, result_container):
    """
    Thread function to handle post-processing of point clouds.
    """
    with app.app_context():
        try:
            # Call the Point_Cloud_Processing function
            processed_pcd = PCP(combined_pcd, new_pcd)
            # Save the processed point cloud
            project_manager = current_app.config.get('project_manager')
            project_manager.save_point_cloud(processed_pcd, project_name, pcd_secondary=new_pcd)
            # Store the result in the container
            result_container['processed_pcd'] = processed_pcd
        except Exception as e:
            current_app.logger.error(f"Error in post-processing thread: {e}")

def auto_scan_thread(app, scan_interval, project_name, positions, stop_event):
    """
    Thread function to perform auto scan.
    """
    combined_pcd = None  # Initialize combined point cloud
    result_container = {}  # Container to store the result from the post-processing thread

    try:
        with app.app_context():
            for index, position in enumerate(positions):
                if stop_event.is_set():
                    logger.info("Scan stopped by stop event.")
                    break

                # Perform movement to the position
                logger.info(f"Moving to position {index + 1}/{len(positions)}: {position}")
                response = perform_scan(position)  # Call the perform_scan function with the current position

                # Log the response from the motor movement
                logger.info(f"Motor movement response: {response}")

                # Check if the movement was successful
                if "success" not in response.lower():
                    logger.error(f"Error moving to position {index + 1}. Aborting auto scan.")
                    break

                # Wait for the motor to stop before starting the scan
                logger.info(f"Waiting for motor to stop before starting scan {index + 1}/{len(positions)}.")
                time.sleep(2)  # Adjust the sleep duration as needed

                # Start scan
                logger.info(f"Attempting to start scan {index + 1}/{len(positions)}.")
                scanner = current_app.config.get('scanner')
                new_pcd = scanner.perform_scan(scan_interval=scan_interval, stop_event=stop_event)
                if new_pcd is None:
                    logger.warning(f"Scan {index + 1} failed or was stopped.")
                    continue

                # If combined_pcd is None, initialize it with the first scan
                if combined_pcd is None:
                    combined_pcd = new_pcd
                    project_manager = current_app.config.get('project_manager')
                    project_manager.save_point_cloud(combined_pcd, project_name)
                else:
                    # Wait for the previous post-processing to complete before starting a new one
                    if post_processing_future:
                        post_processing_future.result()
                        # Update combined_pcd with the processed point cloud from the previous post-processing
                        if 'processed_pcd' in result_container:
                            combined_pcd = result_container['processed_pcd']

                    # Submit post-processing task to the executor
                    post_processing_future = executor.submit(post_process_thread, app, combined_pcd, new_pcd, project_name, result_container)

    except Exception as e:
        current_app.logger.error(f"Error in auto scan thread: {e}")
    finally:
        with app.app_context():
            current_app.config['scan_in_progress'] = False

            # Print the total amount of scans and the number of points in each scan
            total_scans = len(positions)
            current_app.logger.info(f"Total scans completed: {total_scans}, expected {len(positions)}")
            if combined_pcd:
                num_points = len(combined_pcd.points)
                current_app.logger.info(f"Combined scan: {num_points} points")