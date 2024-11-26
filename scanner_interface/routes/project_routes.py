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

# Use relative import instead of absolute import
from ..project_manager import ProjectManager  # Updated to relative import

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