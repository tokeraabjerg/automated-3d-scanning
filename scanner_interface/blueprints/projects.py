# blueprints/projects.py

from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)
projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/rename_project', methods=['POST'])
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
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred.'}), 500

@projects_bp.route('/create_project', methods=['POST'])
def create_project():
    """
    Handle the create project action.
    Expects JSON data with 'projectName' (optional).
    """
    data = request.get_json()
    project_name = data.get('projectName')

    try:
        created_project = project_manager.create_project(name=project_name)
        logger.info(f"Created new project: {created_project}")
        return jsonify({'status': 'success', 'project': created_project}), 200
    except FileExistsError as e:
        logger.error(e)
        return jsonify({'status': 'error', 'message': str(e)}), 409
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to create project.'}), 500
