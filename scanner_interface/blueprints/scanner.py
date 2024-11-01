# blueprints/scanner.py

from flask import Blueprint, jsonify, request
import logging
import threading
import time

logger = logging.getLogger(__name__)
scanner_bp = Blueprint('scanner', __name__)

# Assume 'scanner' and 'config_manager' are accessible via app context or other means
# You might need to adjust based on your actual implementation

@scanner_bp.route('/scanner_status')
def scanner_status():
    """
    Return the current scanner connection status.
    """
    # Replace with actual scanner status check
    connected = scanner.sensorHandle if scanner else False
    return jsonify({'connected': bool(connected)})

# Add more scanner-related routes if needed
