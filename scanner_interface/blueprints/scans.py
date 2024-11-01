# blueprints/scans.py

from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)
scans_bp = Blueprint('scans', __name__)

@scans_bp.route('/start_scan', methods=['POST'])
def start_scan():
    """
    Handle scan initiation request from the user.
    Expects JSON data with 'nrScans', 'scanInterval', and optionally 'selectedProject'.
    """
    global scan_in_progress
    if scanner is None or not scanner.sensorHandle:
        logger.error("Scanner is not connected.")
        return jsonify({"status": "error", "message": "Scanner is not connected."}), 400
    with scan_lock:
        if scan_in_progress:
            logger.warning("Attempted to start a scan while another scan is in progress.")
            return jsonify({"status": "error", "message": "Scan is already in progress."}), 400
        try:
            data = request.get_json()
            nrScans = int(data.get('nrScans', 1))
            scan_interval = int(data.get('scanInterval', 1))  # Default to 1 second
            selected_project = data.get('selectedProject')  # Optional
            if nrScans < 1:
                raise ValueError("Number of scans must be at least 1.")
            if scan_interval < 1:
                raise ValueError("Scan interval must be at least 1 second.")
        except (ValueError, TypeError) as ve:
            logger.error(f"Invalid input provided: {ve}")
            return jsonify({"status": "error", "message": f"Invalid input: {ve}"}), 400

        # If no project is selected, create a new one with the current timestamp
        if not selected_project:
            try:
                selected_project = project_manager.create_project()
                logger.info(f"Created new project: {selected_project}")
            except Exception as e:
                logger.error(f"Error creating project: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500
        else:
            # Verify that the selected project exists
            if selected_project not in project_manager.load_projects():
                logger.error(f"Selected project '{selected_project}' does not exist.")
                return jsonify({"status": "error", "message": "Selected project does not exist."}), 400

        scan_in_progress = True
        logger.info(f"Starting scan with {nrScans} scan(s), interval of {scan_interval} seconds, project '{selected_project}'.")
        executor.submit(scan_thread, nrScans, scan_interval, selected_project)
    return jsonify({"status": "success", "message": "Scan started.", "project": selected_project}), 200

@scans_bp.route('/stop_scan', methods=['POST'])
def stop_scan():
    """
    Handle scan termination request from the user.
    """
    global scan_in_progress
    if scanner is not None:
        try:
            if scanner.stop_scan():
                with scan_lock:
                    scan_in_progress = False
                logger.info("Scan stopped successfully.")
                return jsonify({"status": "success", "message": "Scan stopped."}), 200
            else:
                logger.error("Failed to send stop command to the scanner.")
                return jsonify({"status": "error", "message": "Failed to stop scan."}), 500
        except Exception as e:
            logger.error(f"Failed to send stop command to the scanner: {e}")
            return jsonify({"status": "error", "message": "Exception occurred while stopping scan."}), 500
    else:
        logger.warning("Attempted to stop scan, but scanner instance is None.")
        return jsonify({"status": "error", "message": "Scanner is not connected."}), 400
