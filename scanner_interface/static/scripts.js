// static/scripts.js

// Configure Toastr options
toastr.options = {
    "closeButton": true,                // Show a close button on the notifications
    "debug": false,                     // Enable debug mode
    "newestOnTop": false,               // Newest notifications appear at the bottom
    "progressBar": true,                // Show a progress bar
    "positionClass": "toast-top-right", // Position of the notifications
    "preventDuplicates": false,         // Prevent duplicate notifications
    "onclick": null,                    // Callback on click
    "showDuration": "300",              // How long it takes to show the notification
    "hideDuration": "1000",             // How long it takes to hide the notification
    "timeOut": "5000",                  // How long the notification stays visible
    "extendedTimeOut": "1000",          // How long the notification stays after hover
    "showEasing": "swing",              // Easing function to show
    "hideEasing": "linear",             // Easing function to hide
    "showMethod": "fadeIn",             // Show method
    "hideMethod": "fadeOut"             // Hide method
};

// Helper functions for Toastr notifications
function showSuccess(message, title = 'Success') {
    toastr.success(message, title);
}

function showError(message, title = 'Error') {
    toastr.error(message, title);
}

function showInfo(message, title = 'Info') {
    toastr.info(message, title);
}

function showWarning(message, title = 'Warning') {
    toastr.warning(message, title);
}

// Function to replace native confirm with SweetAlert2 for shutdown confirmation
function confirmShutdown(event) {
    event.preventDefault(); // Prevent default form submission

    Swal.fire({
        title: 'Are you sure?',
        text: "Are you sure you want to shutdown the server?",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Yes, shutdown!'
    }).then((result) => {
        if (result.isConfirmed) {
            // Proceed with form submission
            event.target.submit();
        }
    });

    return false; // Prevent form submission until confirmed
}

let scannerConnected = false;
let connectingNotificationShown = false;

// Function to check scanner connection status
function checkScannerStatus() {
    fetch('/scanner_status')
        .then(response => response.json())
        .then(data => {
            if (data.connected) {
                if (!scannerConnected) {
                    scannerConnected = true;
                    if (connectingNotificationShown) {
                        toastr.clear(); // Remove all toasts
                        connectingNotificationShown = false;
                    }
                    showSuccess('Scanner connected successfully.', 'Scanner Status');
                }
            } else {
                if (scannerConnected) {
                    scannerConnected = false;
                    showError('Scanner disconnected.', 'Scanner Status');
                }
                if (!connectingNotificationShown) {
                    showInfo('Attempting to connect to the scanner...', 'Scanner Status');
                    connectingNotificationShown = true;
                }
            }
        })
        .catch(error => {
            console.error('Error checking scanner status:', error);
            // Optionally, handle the error by showing a notification
            if (scannerConnected) {
                scannerConnected = false;
                showError('Error checking scanner status.', 'Scanner Status');
            }
            if (!connectingNotificationShown) {
                showInfo('Attempting to connect to the scanner...', 'Scanner Status');
                connectingNotificationShown = true;
            }
        });
}

// Function to fetch and display logs every 2 seconds
function fetchLogs() {
    fetch('/get_logs')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.text();
        })
        .then(data => {
            const logOutput = document.getElementById('log-output');
            // Split the log data into lines, reverse the order, and join back into a string
            let reversedLogs = data.split('\n').reverse().join('\n');
            logOutput.textContent = reversedLogs;
            // Scroll to the top to show the newest logs
            logOutput.scrollTop = 0;
        })
        .catch(error => {
            console.error('Error fetching logs:', error);
            showError('Failed to fetch logs.');
        });
}

// Initial fetch and set interval for logs
window.onload = function() {
    fetchLogs();
    load3DPreviewSetting();
    loadScanInterval(); // Load scan interval from localStorage

    // Attach event listeners for Start and Stop Scan
    const startScanForm = document.getElementById('start-scan-form');
    const stopScanForm = document.getElementById('stop-scan-form');
    const newProjectForm = document.getElementById('new-project-form');

    startScanForm.addEventListener('submit', function(event) {
        handleStartScan(event);
    });

    stopScanForm.addEventListener('submit', function(event) {
        handleStopScan(event);
    });

    newProjectForm.addEventListener('submit', function(event) {
        createNewProject(event);
    });

    // Initially disable the Stop button since no scan is active
    const stopButton = document.getElementById('stop-scan-button');
    stopButton.disabled = true;

    // Start polling for logs every 2 seconds
    setInterval(fetchLogs, 2000);

    // Check scanner status immediately
    checkScannerStatus();

    // Start polling for scanner status every 10 seconds
    setInterval(checkScannerStatus, 10000); // every 10 seconds
};

// 3D Previewer Settings
function load3DPreviewSetting() {
    const checkbox = document.getElementById('3d-preview-checkbox');
    // Check if the setting exists in localStorage
    const storedSetting = localStorage.getItem('show3DPreviewer');
    if (storedSetting !== null) {
        checkbox.checked = (storedSetting === 'true');
    } else {
        // Default to enabled if not set
        checkbox.checked = true;
        localStorage.setItem('show3DPreviewer', 'true');
    }
    updateViewerVisibility();
}

function save3DPreviewSetting() {
    const checkbox = document.getElementById('3d-preview-checkbox');
    const isEnabled = checkbox.checked;
    localStorage.setItem('show3DPreviewer', isEnabled.toString());
    updateViewerVisibility();
}

function updateViewerVisibility() {
    const checkbox = document.getElementById('3d-preview-checkbox');
    const container = document.getElementById('viewer-container');
    if (checkbox.checked) {
        container.style.display = 'block';
        // Trigger preview.js to load the point cloud
        loadPointCloud();
    } else {
        container.style.display = 'none';
    }
}

function toggleViewer() {
    const checkbox = document.getElementById('3d-preview-checkbox');
    checkbox.checked = !checkbox.checked;
    save3DPreviewSetting();
}

function manualRefresh() {
    // Trigger preview.js to reload the point cloud
    loadPointCloud();
}

// Scan Interval Settings
function loadScanInterval() {
    const scanIntervalInput = document.getElementById('scanInterval');
    const storedInterval = localStorage.getItem('scanInterval');
    if (storedInterval !== null) {
        scanIntervalInput.value = storedInterval;
    } else {
        // Default to 1 second if not set
        scanIntervalInput.value = 1;
        localStorage.setItem('scanInterval', 1);
    }

    // Add event listener to update localStorage when value changes
    scanIntervalInput.addEventListener('input', function() {
        const value = scanIntervalInput.value;
        if (value && value >= 1) {
            localStorage.setItem('scanInterval', value);
        }
    });
}

// Function to show loading indicator in header with specific text
function showLoadingIndicator(message) {
    const loadingIndicator = document.getElementById('header-loading-indicator');
    const loadingText = document.getElementById('header-loading-text');
    loadingText.textContent = message;
    loadingIndicator.style.display = 'flex';
}

// Function to hide loading indicator in header
function hideLoadingIndicator() {
    const loadingIndicator = document.getElementById('header-loading-indicator');
    loadingIndicator.style.display = 'none';
}

// Function to handle Start Scan form submission
function handleStartScan(event) {
    event.preventDefault(); // Prevent default form submission

    const nrScans = document.getElementById('nrScans').value;
    const scanInterval = document.getElementById('scanInterval').value;
    const selectedProject = document.querySelector('input[name="selected-project"]:checked');

    let project = null;
    if (selectedProject) {
        project = selectedProject.value;
    }

    // Input Validation
    if (nrScans < 1 || scanInterval < 1) {
        showWarning('Number of scans and scan interval must be at least 1.', 'Scan Validation');
        return;
    }

    // Show loading indicator with "Starting scan..."
    showLoadingIndicator('Starting scan...');

    // Disable the Start button and Stop button to prevent multiple clicks
    const startButton = document.getElementById('start-scan-button');
    const stopButton = document.getElementById('stop-scan-button');
    startButton.disabled = true;
    stopButton.disabled = true;

    fetch('/start_scan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            nrScans: nrScans,
            scanInterval: scanInterval,
            selectedProject: project
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showSuccess(`Scan started for project: ${data.project}`, 'Scan Status');
            // Update loading indicator to "Scanning..."
            showLoadingIndicator('Scanning...');
            // Enable the Stop button
            stopButton.disabled = false;
            // Start polling for scan status
            pollScanStatus();
        } else {
            showError(`Error: ${data.message}`, 'Scan Status');
            hideLoadingIndicator();
            startButton.disabled = false;
            stopButton.disabled = true;
        }
    })
    .catch(error => {
        console.error('Error starting scan:', error);
        showError('An error occurred while starting the scan.', 'Scan Status');
        hideLoadingIndicator();
        startButton.disabled = false;
        stopButton.disabled = true;
    });
}

// Function to handle Stop Scan form submission
function handleStopScan(event) {
    event.preventDefault(); // Prevent default form submission

    // Show loading indicator with "Stopping scan..."
    showLoadingIndicator('Stopping scan...');

    // Disable the Stop button to prevent multiple clicks
    const stopButton = document.getElementById('stop-scan-button');
    const startButton = document.getElementById('start-scan-button');
    stopButton.disabled = true;
    startButton.disabled = true;

    fetch('/stop_scan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showInfo('Scan stopping...', 'Scan Status');
            // Update loading indicator to "Stopping scan..."
            showLoadingIndicator('Stopping scan...');
            // Start polling for scan status to confirm stop
            pollScanStatus();
        } else {
            showError(`Error: ${data.message}`, 'Scan Status');
            hideLoadingIndicator();
            stopButton.disabled = false;
            startButton.disabled = false;
        }
    })
    .catch(error => {
        console.error('Error stopping scan:', error);
        showError('An error occurred while stopping the scan.', 'Scan Status');
        hideLoadingIndicator();
        stopButton.disabled = false;
        startButton.disabled = true;
    });
}

// Function to poll scan status
function pollScanStatus() {
    const intervalId = setInterval(() => {
        fetch('/is_processing')
            .then(response => response.json())
            .then(data => {
                if (!data.processing) {
                    // Scan has completed or been stopped
                    clearInterval(intervalId);
                    hideLoadingIndicator();
                    showSuccess('Scan operation completed.', 'Scan Status');
                    // Re-enable the Start button and disable the Stop button
                    const startButton = document.getElementById('start-scan-button');
                    const stopButton = document.getElementById('stop-scan-button');
                    startButton.disabled = false;
                    stopButton.disabled = true;
                    // Trigger preview.js to load the point cloud
                    loadPointCloud();
                } else {
                    // Scan is still in progress
                    // Optionally, update the loading text
                    const loadingText = document.getElementById('header-loading-text');
                    if (loadingText.textContent !== 'Scanning...') {
                        loadingText.textContent = 'Scanning...';
                    }
                }
            })
            .catch(error => {
                console.error('Error polling scan status:', error);
                clearInterval(intervalId);
                hideLoadingIndicator();
                showError('An error occurred while polling scan status.', 'Scan Status');
                // Re-enable the Start button and disable the Stop button
                const startButton = document.getElementById('start-scan-button');
                const stopButton = document.getElementById('stop-scan-button');
                startButton.disabled = false;
                stopButton.disabled = true;
            });
    }, 1000); // Poll every 1 second
}

// Function to rename a project using SweetAlert2
function renameProject(projectName) {
    Swal.fire({
        title: 'Rename Project',
        input: 'text',
        inputLabel: 'New project name',
        inputValue: projectName,
        showCancelButton: true,
        confirmButtonText: 'Rename',
        showLoaderOnConfirm: true,
        preConfirm: (newName) => {
            if (!newName) {
                Swal.showValidationMessage('Project name cannot be empty.');
                return false;
            }
            // Implement AJAX request to rename the project
            return fetch('/rename_project', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    oldName: projectName,
                    newName: newName
                })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => { throw new Error(data.message); });
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    showSuccess('Project renamed successfully.', 'Project Management');
                    // Reload the page or update the DOM
                    location.reload();
                } else {
                    throw new Error(data.message);
                }
            })
            .catch(error => {
                Swal.showValidationMessage(`Request failed: ${error}`);
            });
        },
        allowOutsideClick: () => !Swal.isLoading()
    });
}

// Function to delete a project using SweetAlert2
function deleteProject(projectName) {
    Swal.fire({
        title: 'Delete Project',
        text: `Are you sure you want to delete the project "${projectName}"? This action cannot be undone.`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, delete it!'
    }).then((result) => {
        if (result.isConfirmed) {
            // Proceed with deletion
            fetch('/delete_project', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    projectName: projectName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showSuccess(`Project "${projectName}" has been deleted.`, 'Project Management');
                    // Reload the page or update the DOM
                    location.reload();
                } else {
                    showError(`Error: ${data.message}`, 'Project Management');
                }
            })
            .catch(error => {
                console.error('Error deleting project:', error);
                showError('An unexpected error occurred while deleting the project.', 'Project Management');
            });
        }
    });
}

// Function to create a new project
function createNewProject(event) {
    event.preventDefault(); // Prevent default form submission

    const newProjectName = document.getElementById('newProjectName').value.trim();

    if (!newProjectName) {
        showWarning('Project name cannot be empty.', 'Project Management');
        return false; // Prevent form submission
    }

    // Implement AJAX request to create a new project
    fetch('/create_project', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            projectName: newProjectName
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showSuccess(`Project '${data.project}' created successfully.`, 'Project Management');
            // Reload the page or update the DOM
            location.reload();
        } else {
            showError(`Error: ${data.message}`, 'Project Management');
        }
    })
    .catch(error => {
        console.error('Error creating project:', error);
        showError('An unexpected error occurred while creating the project.', 'Project Management');
    });

    return false; // Prevent form submission
}
