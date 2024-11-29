#---------------------------------------------------------------------------
#  ?                                ABOUT
#  @author         :  Toke Raabjerg
#  @repo           :  https://github.com/Tokeraabjerg/automated-3d-scanning
#  @description    :  This module defines the routes for handling configuration management operations.
#                     It includes routes for retrieving and updating scanner configurations.
#---------------------------------------------------------------------------

from flask import Blueprint, request, jsonify, current_app, redirect, url_for
import logging

config_bp = Blueprint('config_bp', __name__, url_prefix='/config') 
logger = logging.getLogger(__name__)

@config_bp.route('/get_configurations', methods=['GET'])
def get_configurations():
    """
    Return the current configurations as JSON.
    This can be used by the frontend to dynamically update the configurations after initial load.
    """
    config_manager = current_app.config.get('config_manager')
    if config_manager:
        return jsonify(config_manager.configurations)
    else:
        logger.error("Configurations manager is not available.")
        return jsonify({}), 500

@config_bp.route('/update_configurations', methods=['POST'])
def update_configurations():
    """
    Update scanner configurations based on form data.
    If the scanner is not connected, update configurations locally with default values.
    """
    config_manager = current_app.config.get('config_manager')
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
    return redirect(url_for('index'))  # Redirect to the main interface page