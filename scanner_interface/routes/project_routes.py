#---------------------------------------------------------------------------
#  ?                                ABOUT
#  @author         :  Toke Raabjerg
#  @repo           :  https://github.com/Tokeraabjerg/automated-3d-scanning
#  @description    :  This module defines the routes for handling project management operations.
#                     It includes routes for creating, renaming, and deleting projects.
#---------------------------------------------------------------------------
# routes/project_routes.py

from flask import Blueprint, request, jsonify, current_app  # Import current_app instead of project_manager directly
import logging
import threading
import open3d as o3d
import numpy as np
import os  # Import os module
# Use relative import instead of absolute import
from ..project_manager import ProjectManager  # Updated to relative import
from scanner_interface.arduino_coms import interpret_command  # Import the interpret_command function
from scanner_interface.routes.scan_routes import post_process_thread  # Import post_process_thread

# Initialize Blueprint with URL prefix
project_bp = Blueprint('project_bp', __name__, url_prefix='/project')  # Added url_prefix='/project'

# Initialize logger
logger = logging.getLogger(__name__)

__all__ = ['project_bp']

@project_bp.route('/rename_project', methods=['POST'])
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
        # Access project_manager through current_app
        project_manager: ProjectManager = current_app.config['project_manager']
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

@project_bp.route('/create_project', methods=['POST'])
def create_project():
    """
    Handle the create project action.
    Expects JSON data with 'projectName' (optional).
    """
    data = request.get_json()
    project_name = data.get('projectName')

    logger.info(f"Received request to create project: {project_name}")

    try:
        # Access project_manager through current_app
        project_manager: ProjectManager = current_app.config['project_manager']
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

@project_bp.route('/delete_project', methods=['POST'])
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
        # Access project_manager through current_app
        project_manager: ProjectManager = current_app.config['project_manager']
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

@project_bp.route('/delete_scan_files', methods=['POST'])
def delete_scan_files():
    """
    Handle the delete scan files action.
    Expects JSON data with 'projectName'.
    """
    data = request.get_json()
    project_name = data.get('projectName')

    if not project_name:
        return jsonify({'status': 'error', 'message': 'Project name not provided.'}), 400

    try:
        # Access project_manager through current_app
        project_manager: ProjectManager = current_app.config['project_manager']
        project_manager.delete_scan_files(project_name)
        logger.info(f"Deleted scan files in project: {project_name}")
        return jsonify({'status': 'success'}), 200
    except FileNotFoundError as e:
        logger.error(e)
        return jsonify({'status': 'error', 'message': str(e)}), 404
    except Exception as e:
        logger.error(f"Error deleting scan files in project '{project_name}': {e}")
        return jsonify({'status': 'error', 'message': 'Failed to delete scan files.'}), 500

@project_bp.route('/get_scan_count', methods=['GET'])
def get_scan_count():
    """
    Get the number of scans in the specified project.
    Expects a query parameter 'projectName'.
    """
    project_name = request.args.get('projectName')
    if not project_name:
        return jsonify({'status': 'error', 'message': 'Project name not provided.'}), 400

    try:
        # Access project_manager through current_app
        project_manager: ProjectManager = current_app.config['project_manager']
        scan_count = project_manager.get_scan_count(project_name)
        return jsonify({'status': 'success', 'scanCount': scan_count}), 200
    except FileNotFoundError as e:
        logger.error(e)
        return jsonify({'status': 'error', 'message': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting scan count: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to get scan count.'}), 500

@project_bp.route('/get_scan_preview', methods=['GET'])
def get_scan_preview():
    """
    Get a downsampled preview of the specified scan in the project.
    Expects query parameters 'projectName' and 'scanFile'.
    """
    project_name = request.args.get('projectName')
    scan_file = request.args.get('scanFile')

    if not project_name or not scan_file:
        return jsonify({'status': 'error', 'message': 'Project name or scan file not provided.'}), 400

    try:
        # Access project_manager through current_app
        project_manager: ProjectManager = current_app.config['project_manager']
        scan_preview = project_manager.get_scan_preview(project_name, scan_file)
        if scan_preview is None:
            return jsonify({'status': 'success', 'scanPreview': None}), 200  # Return success with None if no scan files exist
        return jsonify({'status': 'success', 'scanPreview': scan_preview}), 200
    except FileNotFoundError as e:
        logger.error(e)
        return jsonify({'status': 'error', 'message': str(e)}), 404
    except Exception as e:
        logger.error(f"Error getting scan preview: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to get scan preview.'}), 500

@project_bp.route('/get_positions', methods=['GET'])
def get_positions():
    """
    Retrieve the contents of positions.json for the specified project.
    """
    project_name = request.args.get('projectName')
    if not project_name:
        return jsonify({'status': 'error', 'message': 'Project name is required'}), 400

    project_manager = current_app.config.get('project_manager')
    if not project_manager:
        logger.error("Project manager is not available.")
        return jsonify({'status': 'error', 'message': 'Project manager is not available'}), 500

    positions = project_manager.get_positions(project_name)
    if positions is None:
        return jsonify({'status': 'error', 'message': 'positions.json not found or empty'}), 404

    return jsonify({'status': 'success', 'positions': positions})

@project_bp.route('/preview_scan', methods=['POST'])
def preview_scan():
    """
    Preview the movement path by sending all positions to the Arduino.
    Expects JSON data with 'projectName'.
    """
    data = request.json
    project_name = data.get('projectName')

    if not project_name:
        return jsonify({'status': 'error', 'message': 'Project name is required'}), 400

    try:
        project_manager = current_app.config.get('project_manager')
        if not project_manager:
            logger.error("Project manager is not available.")
            return jsonify({'status': 'error', 'message': 'Project manager is not available'}), 500

        positions = project_manager.get_positions(project_name)
        if not positions:
            return jsonify({'status': 'error', 'message': 'No positions found for the project.'}), 404

        # Send positions to Arduino for preview
        response = interpret_command(positions)
        if response.lower() == "success":
            logger.debug(f"Preview scan for '{project_name}' completed successfully.")
            return jsonify({'status': 'success', 'project': project_name, 'message': 'Preview scan completed successfully.'}), 200
        else:
            logger.error(f"Preview scan failed: {response}")
            return jsonify({'status': 'error', 'message': f'Preview scan failed: {response}'}), 500

    except Exception as e:
        logger.error(f"Error during preview scan for '{project_name}': {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@project_bp.route('/manual_pcp', methods=['POST'])
def manual_pcp():
    """
    Manually process point clouds for the specified project.
    Expects JSON data with 'projectName'.
    """
    data = request.json
    project_name = data.get('projectName')
    preprocessing_method = data.get('preprocessingMethod', 'Standard')
    voxel_size = data.get('voxelSize', 0.01)
    max_correspondence_distance = data.get('maxCorrespondenceDistance', 2)

    if not project_name:
        return jsonify({'status': 'error', 'message': 'Project name is required'}), 400

    try:
        project_manager = current_app.config.get('project_manager')
        if not project_manager:
            logger.error("Project manager is not available.")
            return jsonify({'status': 'error', 'message': 'Project manager is not available'}), 500

        # Update positions with relative angles
        positions = project_manager.update_positions_with_relative_angles(project_name)
        if not positions:
            return jsonify({'status': 'error', 'message': 'No positions found for the project.'}), 404

        # Fetch full-size point clouds
        pcd_dict = {}
        for index, position in enumerate(positions):
            scan_index = index + 1
            scan_filename = f"scan_{scan_index}.ply"
            scan_filepath = os.path.join(project_manager.output_dir, project_name, scan_filename)
            if os.path.exists(scan_filepath):
                pcd = o3d.io.read_point_cloud(scan_filepath)
                rotation = [position['deg_a'], position['deg_b']]
                logger.info(f"Angles for scan_{scan_index}: theta_pan={rotation[0]}, theta_tilt={rotation[1]}")
                pcd_dict[f"scan_{scan_index}"] = {
                    "pcd": pcd,
                    "rotation": rotation  # Rotation determined from positions.json
                }

        if not pcd_dict:
            return jsonify({'status': 'error', 'message': 'No point clouds found for the project.'}), 404

        # Start post-processing thread
        app = current_app._get_current_object()
        post_processing_thread = threading.Thread(target=post_process_thread, args=(app, pcd_dict, project_name, len(positions), preprocessing_method, voxel_size, max_correspondence_distance))
        post_processing_thread.start()

        return jsonify({'status': 'success', 'message': 'Manual point cloud processing started.'}), 200

    except Exception as e:
        logger.error(f"Error during manual point cloud processing for '{project_name}': {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@project_bp.route('/save_configurations', methods=['POST'])
def save_configurations():
    """
    Save the current scanner configurations to the specified project as configurations.json.
    """
    try:
        data = request.get_json()
        project_name = data.get('projectName')

        if not project_name:
            return jsonify({'status': 'error', 'message': 'Project name is required.'}), 400

        project_manager = current_app.config.get('project_manager')
        if not project_manager:
            return jsonify({'status': 'error', 'message': 'Project manager is not available.'}), 500

        success = project_manager.save_current_configurations(project_name)

        if success:
            return jsonify({'status': 'success', 'message': 'Configurations saved successfully.'}), 200
        else:
            return jsonify({'status': 'error', 'message': 'Failed to save configurations.'}), 500
    except Exception as e:
        current_app.logger.error(f"Error in save_configurations: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


