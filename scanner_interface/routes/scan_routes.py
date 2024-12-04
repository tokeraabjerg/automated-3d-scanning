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
import json
import numpy as np
from scanner_interface.arduino_coms import interpret_command  # Import the interpret_command function
from python.Point_Cloud_Processing.PCP_main import Point_Cloud_Processing  # Import the Point_Cloud_Processing function
from python.Point_Cloud_Processing.PP import preprocess_point_cloud
from python.Point_Cloud_Processing.Calibration_by_fixture import Calibration_by_fixture

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
            project_manager.save_point_cloud(pcd, project_name, save_as_main=False)

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
    auto_scan_stop_event = current_app.config.get('auto_scan_stop_event')
    scanner = current_app.config.get('scanner')

    if scanner is not None:
        try:
            stop_event.set()  # Signal the scanning thread to stop
            auto_scan_stop_event.set()  # Signal the auto scan thread to stop
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

# Ensure the stop events are reset after the scan is stopped
def reset_stop_events():
    stop_event = current_app.config.get('stop_event')
    auto_scan_stop_event = current_app.config.get('auto_scan_stop_event')
    if stop_event:
        stop_event.clear()
    if auto_scan_stop_event:
        auto_scan_stop_event.clear()
    logger.info("Stop events reset.")

# Call reset_stop_events after the scan is stopped
@scan_bp.route('/is_processing', methods=['GET'])
def is_processing():
    """
    Check if a scan is currently in progress.
    """
    scan_in_progress = current_app.config.get('scan_in_progress', False)
    if not scan_in_progress:
        reset_stop_events()
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

        # Check for existing scans in the project directory
        existing_scans = project_manager.get_scan_count(project_name)
        if existing_scans > 0:
            return jsonify({
                'status': 'warning',
                'message': 'Existing scans found. Do you want to overwrite them? You can run post-processing without capturing new scans by running manual PCP.'
            }), 200

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

# Add a flag to track the post-processing thread status
post_processing_thread_running = False

def auto_scan_thread(app, scan_interval, project_name, positions, stop_event):
    """
    Thread function to perform auto scan.
    """
    pcd_dict = {}  # Dictionary to store individual point clouds and their rotation information
    auto_scan_stop_event = current_app.config.get('auto_scan_stop_event')

    try:
        with app.app_context():
            # Update positions with relative angles
            project_manager = current_app.config.get('project_manager')
            positions = project_manager.update_positions_with_relative_angles(project_name)
            if not positions:
                logger.error(f"No positions found for the project '{project_name}'.")
                return None

            for index, position in enumerate(positions):
                if stop_event.is_set() or auto_scan_stop_event.is_set():
                    logger.info("Scan stopped by stop event.")
                    break

                # Ensure position is a dictionary
                if not isinstance(position, dict):
                    logger.error(f"Invalid position data at index {index}: {position}")
                    continue

                # Perform movement to the position
                logger.info(f"Moving to position {index + 1}/{len(positions)}: {position}")
                response = interpret_command(position)  # Call the interpret_command function with the current position

                # Log the response from the motor movement
                logger.info(f"Motor movement response: {response}")

                # Check if the movement was successful
                if "success" not in response.lower():
                    logger.error(f"Error moving to position {index + 1}. Aborting auto scan.")
                    break

                # Wait for the motor to stop before starting the scan
                logger.info(f"Waiting for motor to stop before starting scan {index + 1}/{len(positions)}.")
                time.sleep(0.5)  # Aust the sleep duration as needed

                # Start scan
                logger.info(f"Attempting to start scan {index + 1}/{len(positions)}.")
                scanner = current_app.config.get('scanner')
                new_pcd = scanner.perform_scan(scan_interval=scan_interval, stop_event=stop_event)
                if new_pcd is None:
                    logger.warning(f"Scan {index + 1} failed or was stopped.")
                    continue

                # Add the new point cloud and its rotation information to the dictionary
                rotation = [position['deg_a'], position['deg_b']]
                pcd_dict[f"scan_{index + 1}"] = {
                    "pcd": new_pcd,
                    "rotation": rotation,
                    "icp_transformation": position.get('icp_transformation', [])
                }

                logger.info(f"We currently got {len(pcd_dict)} scans")

                # Save the combined point cloud
                project_manager.save_point_cloud(new_pcd, project_name)
                logger.info("Point cloud saved.")

                # If there are 2 or more point clouds and no post-processing thread is running, start post-processing in a new thread
                global post_processing_thread_running
                if len(pcd_dict) >= 2 and not post_processing_thread_running:
                    logger.info(f"Starting post-processing thread for {len(pcd_dict)} point clouds.")
                    post_processing_thread_running = True
                    post_processing_thread = threading.Thread(target=post_process_thread, args=(app, pcd_dict, project_name, len(positions)))
                    post_processing_thread.start()

            # Send success message after completing all scans
            logger.info(f"Auto scan completed successfully for project: {project_name}")
            return jsonify({'status': 'success', 'message': 'Auto scan completed successfully', 'project': project_name}), 200

    except Exception as e:
        current_app.logger.error(f"Error in auto scan thread: {e}")
    finally:
        with app.app_context():
            current_app.config['scan_in_progress'] = False

            # Print the total amount of scans and the number of points in each scan
            total_scans = len(positions)
            current_app.logger.info(f"Total scans completed: {total_scans}, expected {len(positions)}")
            if "scan_main" in pcd_dict:
                num_points = len(pcd_dict["scan_main"]["pcd"].points)
                current_app.logger.info(f"Combined scan: {num_points} points")

def post_process_thread(app, pcd_dict, project_name, total_positions):
    """
    Thread function to handle post-processing of point clouds.
    """
    logger.info("Post-processing thread started.")

    with app.app_context():
        try:
            # Get saved calibration transformation
            response = current_app.test_client().get('/calibration/get_saved_calibration')
            calibration_data = response.get_json()

            if calibration_data['status'] != 'success':
                logger.error(f"Failed to get saved calibration: {calibration_data['message']}")
                return
            
            matrix = calibration_data['calibrationTransformation']
            logger.info(f"Using saved calibration transformation: {matrix}")

            while True:
                logger.info(f"Current pcd_dict length: {len(pcd_dict)}")
                if len(pcd_dict) >= 2:
                    logger.info(f"Post-processing {len(pcd_dict)} point clouds.")
                    if "scan_main" in pcd_dict:
                        logger.info("Combining scan_main with the lowest scan key.")
                        combined_pcd = pcd_dict["scan_main"]["pcd"]
                        lowest_scan_key = min((key for key in pcd_dict if key != "scan_main"), 
                                           key=lambda k: int(k.split('_')[1]))
                        target_pcd = pcd_dict[lowest_scan_key]["pcd"]
                        target_rotation = pcd_dict[lowest_scan_key]["rotation"]
                        main_rotation = pcd_dict["scan_main"]["rotation"]
                        
                        # # Calculate the difference in angles
                        # theta_pan_diff = target_rotation[0] - main_rotation[0]
                        # theta_tilt_diff = target_rotation[1] - main_rotation[1]
                        
                        logger.info(f"Combining scan_main with {lowest_scan_key}, using rotations {target_rotation[0]} and {target_rotation[1]}")
                        
                        combined_pcd, icp_transform = Point_Cloud_Processing(
                            combined_pcd,
                            target_pcd,
                            target_rotation[0], 
                            -target_rotation[1],  
                            matrix
                        )
                        logger.info(f"ICP transform: {icp_transform}")

                        pcd_dict.update({"scan_main": {"pcd": combined_pcd, "rotation": target_rotation}})
                        del pcd_dict[lowest_scan_key]
                    else:
                        logger.info("Combining the first two point clouds.")
                        pcd_list = [pcd_dict[key]["pcd"] for key in sorted(pcd_dict.keys())[:2]]
                        rotation_list = [pcd_dict[key]["rotation"] for key in sorted(pcd_dict.keys())[:2]]
                        
                        # # Calculate the difference in angles
                        # theta_pan_diff = rotation_list[1][0] - rotation_list[0][0]
                        # theta_tilt_diff = rotation_list[1][1] - rotation_list[0][1]
                        
                        logger.info(f"Combining {sorted(pcd_dict.keys())[:2]}")
                        logger.info(f"Angles sent to Point_Cloud_Processing: theta_pan_diff={rotation_list[1][0]}, theta_tilt_diff={ rotation_list[1][1]}")
                        combined_pcd, icp_transform = Point_Cloud_Processing(
                            pcd_list[0],
                            pcd_list[1],
                            rotation_list[1][0], #pan, motor a
                            -rotation_list[1][1],  #tilt, motor b
                            matrix
                        )
                        
                        logger.info(f"ICP transform: {icp_transform}")

                        pcd_dict = {
                            "scan_main": {
                                "pcd": combined_pcd,
                                "rotation": rotation_list[0] # I changed this to 0, it should be the first index which is 0,0. Right..?
                            }
                        }

                    # Save the combined point cloud as scan_main.ply
                    project_manager = current_app.config.get('project_manager')
                    project_manager.save_point_cloud(combined_pcd, project_name, save_as_main=True)
                    logger.info("Combined point cloud saved as scan_main.ply.")

                if len(pcd_dict) < 2:
                    if len(pcd_dict) < total_positions and total_positions > 2:
                        logger.info("Waiting for new scans to process.")
                        time.sleep(2)
                    else:
                        logger.info("No more scans to process. Exiting post-processing thread.")
                        break

            logger.info("Post-processing thread completed.")
        except Exception as e:
            logger.error(f"Error in post-processing thread: {e}")
        finally:
            global post_processing_thread_running
            post_processing_thread_running = False
            logger.info("Post-processing thread completed.")






def calculate_average_intensity(pcd):
    """
    Calculate the average intensity of the point cloud.

    :param pcd: The Open3D point cloud object.
    :return: The average intensity value.
    """
    intensities = np.asarray(pcd.colors)[:, 0]  # Assuming intensity is stored in the colors attribute
    average_intensity = np.mean(intensities)
    return average_intensity

def increase_exposure_time(scanner, increment):
    """
    Increase the exposure time by a set value.

    :param scanner: The scanner interface instance.
    :param increment: The value to increase the exposure time by.
    :return: True if the exposure time was increased successfully, False otherwise.
    """
    try:
        # Read the current exposure time
        current_exposure_str = scanner.read_parameter("GetExposureTime")
        if current_exposure_str is None:
            logger.error("Failed to read current exposure time.")
            return False

        current_exposure = int(current_exposure_str)
        new_exposure = current_exposure + increment

        # Update the exposure time
        if scanner.update_configuration("ExposureTime", new_exposure):
            logger.info(f"Exposure time increased from {current_exposure} to {new_exposure}.")
            return True
        else:
            logger.error("Failed to update exposure time.")
            return False
    except Exception as e:
        logger.error(f"Exception while increasing exposure time: {e}")
        return False



def increase_led_power(scanner, increment):
    """
    Increase the LED power by a set value within the limits of 10 and 100.

    :param scanner: The scanner interface instance.
    :param increment: The value to increase the LED power by.
    :return: True if the LED power was increased successfully, False otherwise.
    """
    try:
        # Read the current LED power
        current_led_power_str = scanner.read_parameter("GetLEDPower")
        if current_led_power_str is None:
            logger.error("Failed to read current LED power.")
            return False

        current_led_power = int(current_led_power_str)
        new_led_power = current_led_power + increment

        # Ensure the new LED power is within the limits
        if new_led_power < 10:
            logger.info("Minimum LED power reached. Defaulting to 10.")
            new_led_power = 10
        elif new_led_power > 100:
            logger.info("Maximum LED power reached. Defaulting to 100.")
            new_led_power = 100

        # Update the LED power
        if scanner.update_configuration("LEDPower", new_led_power):
            logger.info(f"LED power increased from {current_led_power} to {new_led_power}.")
            return True
        else:
            logger.error("Failed to update LED power.")
            return False
    except Exception as e:
        logger.error(f"Exception while increasing LED power: {e}")
        return False




@scan_bp.route('/Scanner_calibration_scan', methods=['POST'])
def Scanner_calibration_scan():
    """Start an scanner calibration scan at the zero position (0,0)."""
    try:
        logger.info("Starting Scanner calibration scan...")

        # Check if scanner is connected
        scanner = current_app.config.get('scanner')
        if not scanner or not scanner.connected:
            logger.error("Scanner not connected")
            return jsonify({'status': 'error', 'message': 'Scanner not connected'}), 400

        # Ensure we're at position (0,0)
        zero_position = {"home": True}
        response = interpret_command(zero_position)
        if "success" not in response.lower():
            logger.error("Failed to move to zero position")
            return jsonify({'status': 'error', 'message': 'Failed to move to zero position'}), 500

        logger.info("Moved to zero position successfully")
        time.sleep(1)  # Wait for motors to settle

        calibrated = False
        max_exposure_scans = 10
        n_scans = 0
        # Perform the calibration scan
        while calibrated == False and n_scans < max_exposure_scans:
            pcd = scanner.perform_scan(scan_interval=1, stop_event=current_app.config.get('stop_event'))
            if pcd is None:
                logger.error("Scan failed")
                return jsonify({'status': 'error', 'message': 'Scan failed'}), 500

            # Preprocess the point cloud
            logger.info("Preprocessing point cloud...")
            voxel_size = 1
            pcd_voxel=pcd.voxel_down_sample(voxel_size)
            # print(f"Voxelization resulted in {len(pcd_voxel.points)} points")
            
            # Remove statistical outliers
            # print(":: Statistically remove outliers.")
            pcd_voxel, ind = pcd_voxel.remove_statistical_outlier(nb_neighbors=int(100/voxel_size), std_ratio=1)

            # Check if intensity is too low
            average_intensity = calculate_average_intensity(pcd_voxel)
            logger.info(f"Average intensity of the point cloud: {average_intensity}")
            # TODO: Consider adding intensity check here/logic to adjust LED power

            # If the number of outliers is less than 10% of the total points, calibration is successful
            logger.info(f"Point cloud preprocessed successfully, removed {len(ind)} outliers")
            if len(ind) < 0.1*len(pcd_voxel.points):
                logger.info("Calibration completed successfully")
                calibrated = True
            else:
                logger.info("Calibration failed, reducing LED power")

                scanner = current_app.config.get('scanner')
                if scanner:
                    increase_led_power(scanner, -10)  # Decrease LED power by 10 units
                else:
                    logger.error("Scanner instance is None. Cannot decrease LED power.")

            n_scans += 1
        
        return jsonify({
            'status': 'success',
            'message': 'Calibration completed'
        }), 200

    except Exception as e:
        logger.error(f"Error in exposure calibration scan: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500




@scan_bp.route('/calibration_scan', methods=['POST'])
def calibration_scan():
    """Start a calibration scan at the zero position (0,0)."""
    try:
        logger.info("Starting calibration scan...")

        # Check if scanner is connected
        scanner = current_app.config.get('scanner')
        if not scanner or not scanner.connected:
            logger.error("Scanner not connected")
            return jsonify({'status': 'error', 'message': 'Scanner not connected'}), 400

        # Ensure we're at position (0,0)
        zero_position = {"home": True}
        response = interpret_command(zero_position)
        if "success" not in response.lower():
            logger.error("Failed to move to zero position")
            return jsonify({'status': 'error', 'message': 'Failed to move to zero position'}), 500

        logger.info("Moved to zero position successfully")
        time.sleep(1)  # Wait for motors to settle

        # Perform the calibration scan
        pcd = scanner.perform_scan(scan_interval=1, stop_event=current_app.config.get('stop_event'))
        if pcd is None:
            logger.error("Scan failed")
            return jsonify({'status': 'error', 'message': 'Scan failed'}), 500

        # Preprocess the point cloud
        logger.info("Preprocessing point cloud...")
        preprocessed_cloud_normal, preprocessed_cloud = preprocess_point_cloud(pcd, resolution=1, std_ratio=0.5)
        logger.info("Point cloud preprocessed successfully")

        # Get base directory from app config
        base_dir = current_app.config.get('base_dir')
        calibration_dir = os.path.join(base_dir, '..', 'calibration')
        fixture_path = os.path.join(calibration_dir, 'ref.ply')

        # Get fixture path and perform calibration
        if not os.path.exists(fixture_path):
            logger.error("Fixture file not found")
            return jsonify({'status': 'error', 'message': 'Reference file not found'}), 404

        logger.info("Fixture file found, performing calibration...")
        # Calculate calibration
        calibration_matrix, fixture = Calibration_by_fixture(preprocessed_cloud, fixture_path)
        logger.info("Calibration performed successfully")

        # Save calibration matrix
        os.makedirs(calibration_dir, exist_ok=True)
        config_json_path = os.path.join(calibration_dir, 'calibration.json')

        with open(config_json_path, 'w') as f:
            json.dump({'calibration_transformation': calibration_matrix.tolist()}, f)

        logger.info("Calibration completed and saved successfully")
        return jsonify({
            'status': 'success',
            'message': 'Calibration completed',
            'calibrationTransformation': calibration_matrix.tolist()
        }), 200

    except Exception as e:
        logger.error(f"Error in calibration scan: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
