from flask import Blueprint, request, jsonify, current_app
import logging
import open3d as o3d
from python.Point_Cloud_Processing.PP import preprocess_point_cloud
from python.Point_Cloud_Processing.Calibration_by_fixture import Calibration_by_fixture
import os
import json
import time

# Update blueprint definition with explicit name and url_prefix
calibration_bp = Blueprint('calibration_bp', __name__, url_prefix='/calibration')
logger = logging.getLogger(__name__)


@calibration_bp.route('/get_saved_calibration', methods=['GET'])
def get_saved_calibration():
    """
    Retrieve the saved calibration matrix from calibration.json.
    If it doesn't exist, inform the user to run calibration.
    """
    try:
        # Get base directory from app config
        base_dir = current_app.config.get('base_dir')
        calibration_dir = os.path.join(base_dir, '..', 'calibration')
        config_json_path = os.path.join(calibration_dir, 'calibration.json')

        if not os.path.exists(config_json_path):
            return jsonify({'status': 'error', 'message': 'Calibration file not found. Please run calibration.'}), 404

        with open(config_json_path, 'r') as f:
            calibration_data = json.load(f)
            if 'calibration_transformation' in calibration_data:
                return jsonify({'status': 'success', 'calibrationTransformation': calibration_data['calibration_transformation']}), 200
            else:
                return jsonify({'status': 'error', 'message': 'Calibration data is missing. Please run calibration.'}), 500

    except Exception as e:
        logger.error(f"Error retrieving saved calibration: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
