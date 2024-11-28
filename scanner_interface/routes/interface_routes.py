from flask import Blueprint, jsonify, current_app
import logging

interface_bp = Blueprint('interface_bp', __name__, url_prefix='/interface')
logger = logging.getLogger(__name__)

# Route to check scanner status
@interface_bp.route('/scanner_status', methods=['GET'])
def scanner_status():
    """
    Return the current scanner connection status.
    """
    scanner = current_app.config.get('scanner')
    connecting_attempt = current_app.config.get('connecting_attempt', False)
    
    if scanner:
        connected = scanner.ping_sensor()
    else:
        connected = False

    status = {
        'connected': connected,
        'connecting': connecting_attempt
    }
    return jsonify(status)

# Route to attempt reconnecting to the scanner
@interface_bp.route('/attempt_reconnect', methods=['POST'])
def attempt_reconnect():
    logger.info("Attempting to reconnect to the scanner.")
    """
    Attempt to reconnect to the scanner.
    """
    scanner = current_app.config.get('scanner')
    config_manager = current_app.config.get('config_manager')
    sensor_lock = current_app.config.get('sensor_lock')
    connecting_attempt = current_app.config.get('connecting_attempt', False)

    if not scanner:
        logger.error("Scanner instance is None.")
        return jsonify({"status": "error", "message": "Scanner instance is None."}), 500

    if not config_manager:
        logger.error("Config manager instance is None.")
        return jsonify({"status": "error", "message": "Config manager instance is None."}), 500

    if not sensor_lock:
        logger.error("Sensor lock instance is None.")
        return jsonify({"status": "error", "message": "Sensor lock instance is None."}), 500

    with sensor_lock:
        if not scanner.connected and not connecting_attempt:
            logger.info("Attempting to reconnect to the scanner...")
            current_app.config['connecting_attempt'] = True
            try:
                if scanner.connect():
                    logger.info("Scanner reconnected successfully.")
                    try:
                        config_manager.read_all_configurations()
                        logger.info("Configurations reloaded after reconnection.")
                        current_app.config['connecting_attempt'] = False
                        return jsonify({"status": "success", "message": "Reconnected successfully."}), 200
                    except Exception as e:
                        logger.error(f"Failed to read configurations after reconnection: {e}")
                        current_app.config['connecting_attempt'] = False
                        return jsonify({"status": "error", "message": "Reconnected but failed to read configurations."}), 500
                else:
                    logger.warning("Failed to reconnect to the scanner.")
                    current_app.config['connecting_attempt'] = False
                    return jsonify({"status": "error", "message": "Failed to reconnect."}), 500
            except Exception as e:
                logger.exception(f"Exception during reconnection attempt: {e}")
                current_app.config['connecting_attempt'] = False
                return jsonify({"status": "error", "message": "Exception occurred during reconnection attempt."}), 500
        else:
            logger.warning("Scanner is already connected or reconnection is in progress.")
            return jsonify({"status": "error", "message": "Scanner is already connected or reconnection is in progress."}), 400