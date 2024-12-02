/**------------------------------------------------------------------------
 * ?                                ABOUT
 * @author         :  Toke Raabjerg
 * @repo           :  https://github.com/Tokeraabjerg/automated-3d-scanning
 * @description    :  This JavaScript file contains functions for handling the 3D scanner 
 *                    control panel interface.
 *------------------------------------------------------------------------**/

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

// Function to replace native confirm with SweetAlert2 for restart confirmation
function confirmRestart(event) {
    event.preventDefault(); // Prevent default form submission

    Swal.fire({
        title: 'Are you sure?',
        text: "Are you sure you want to restart the server?",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#3085d6',
        cancelButtonColor: '#d33',
        confirmButtonText: 'Yes, restart!'
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

// Function to show/hide connection status icons
function updateConnectionStatus(connected, connecting) {
    const connectedIcon = document.getElementById('connected-icon');
    const connectingIcon = document.getElementById('connecting-icon');
    const disconnectedIcon = document.getElementById('disconnected-icon');

    if (connected) {
        connectedIcon.style.display = 'inline-block';
        connectingIcon.style.display = 'none';
        disconnectedIcon.style.display = 'none';
    } else if (connecting) {
        connectedIcon.style.display = 'none';
        connectingIcon.style.display = 'inline-block';
        disconnectedIcon.style.display = 'none';
    } else {
        connectedIcon.style.display = 'none';
        connectingIcon.style.display = 'none';
        disconnectedIcon.style.display = 'inline-block';
    }

    console.log(`Connection Status Updated - Connected: ${connected}, Connecting: ${connecting}`);
}

function updateConnectionStatus(isConnected) {
    if (isConnected) {
        document.getElementById('connected-icon').style.display = 'block';
        document.getElementById('connecting-icon').style.display = 'none';
        document.getElementById('disconnected-icon').style.display = 'none';
    } else {
        document.getElementById('connected-icon').style.display = 'none';
        document.getElementById('connecting-icon').style.display = 'none';
        document.getElementById('disconnected-icon').style.display = 'block';
    }
}

let lastLogTime = 0;

// Function to check scanner connection status
function checkScannerStatus(logInterval = 30000) {
    fetch('/interface/scanner_status')
        .then(response => response.json())
        .then(data => {
            console.log('Scanner Status:', data);
            if (data.connected) {
                updateConnectionStatus(true, false);
                if (!scannerConnected) {
                    scannerConnected = true;
                    if (connectingNotificationShown) {
                        toastr.clear(); // Remove all toasts
                        connectingNotificationShown = false;
                    }
                    showSuccess('Scanner connected successfully.', 'Scanner Status');
                }
            } else {
                if (data.connecting) {
                    updateConnectionStatus(false, true);
                    if (!connectingNotificationShown) {
                        showInfo('Attempting to connect to the scanner...', 'Scanner Status');
                        connectingNotificationShown = true;
                    }
                } else {
                    updateConnectionStatus(false, false);
                    if (scannerConnected) {
                        scannerConnected = false;
                        showError('Scanner disconnected.', 'Scanner Status');
                    }
                    if (!connectingNotificationShown) {
                        showInfo('Scanner is disconnected.', 'Scanner Status');
                        connectingNotificationShown = true;
                    }
                }
            }

            // Log a message every logInterval milliseconds
            const currentTime = Date.now();
            if (currentTime - lastLogTime >= logInterval) {
                lastLogTime = currentTime;
            }
        })
        .catch(error => {
            console.error('Error checking scanner status:', error);
            // Optionally, handle the error by showing a notification
            updateConnectionStatus(false, false);
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
let errorDisplayed = false;
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
            const isScrolledToTop = logOutput.scrollTop === 0;
            // Split the log data into lines, reverse the order, and join back into a string
            let reversedLogs = data.split('\n').reverse().join('\n');
            logOutput.textContent = reversedLogs;
            // Scroll to the top to show the newest logs only if the user is not scrolling
            if (isScrolledToTop) {
                logOutput.scrollTop = 0;
            }
            errorDisplayed = false; // Reset error display flag on successful fetch
        })
        .catch(error => {
            console.error('Error fetching logs:', error);
            if (!errorDisplayed) {
                showError('Failed to fetch logs.');
                errorDisplayed = true;
                setTimeout(() => {
                    errorDisplayed = false;
                }, 30000); // Reset error display flag after 30 seconds
            }
        });
}

// 3D Previewer Settings

// Remove the manual refresh function
// function manualRefresh() {
//     // Trigger preview.js to reload the point cloud
//     loadPointCloud();
// }

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

function hideLoadingIndicator() {
    const loadingIndicator = document.getElementById('header-loading-indicator');
    loadingIndicator.style.display = 'none';
}

function showViewerLoadingIndicator() {
    const loadingIndicator = document.getElementById('viewer-loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'flex';
    } else {
        console.error('viewer-loading-indicator element not found.');
    }
}

function hideViewerLoadingIndicator() {
    const loadingIndicator = document.getElementById('viewer-loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'none';
    } else {
        console.error('viewer-loading-indicator element not found.');
    }
}

// Function to handle Manual Capture form submission
function handleManualCapture(event) {
    event.preventDefault(); // Prevent default form submission

    // Check if the scanner is connected
    if (!scannerConnected) {
        showError('Scanner is not connected. Please connect the scanner before starting a scan.', 'Scan Validation');
        return;
    }

    const scanInterval = parseInt(document.getElementById('scanInterval').value);
    const selectedProject = document.querySelector('input[name="selected-project"]:checked');

    let project = null;
    if (selectedProject) {
        project = selectedProject.value;
    } else {
        showWarning('Please select or create a project before starting a scan.', 'Scan Validation');
        return;
    }

    // Input Validation
    if (scanInterval < 1) {
        showWarning('Scan interval must be at least 1.', 'Scan Validation');
        return;
    }

    // Show loading indicator with "Starting scan..."
    showLoadingIndicator('Starting scan...');

    // Disable the Start button and Stop button to prevent multiple clicks
    const startButton = document.getElementById('start-scan-button');
    const stopButton = document.getElementById('stop-scan-button');
    startButton.disabled = true;
    stopButton.disabled = true;

    fetch('/scan/start_scan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
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

// Function to handle Manual Capture form submission
function handleManualCapture(event) {
    event.preventDefault(); // Prevent default form submission

    // Check if the scanner is connected
    if (!scannerConnected) {
        showError('Scanner is not connected. Please connect the scanner before starting a scan.', 'Scan Validation');
        return;
    }

    const scanInterval = parseInt(document.getElementById('scanInterval').value);
    const selectedProject = document.querySelector('input[name="selected-project"]:checked');

    let project = null;
    if (selectedProject) {
        project = selectedProject.value;
    } else {
        showWarning('Please select or create a project before starting a scan.', 'Scan Validation');
        return;
    }

    // Input Validation
    if (scanInterval < 1) {
        showWarning('Scan interval must be at least 1.', 'Scan Validation');
        return;
    }

    // Show loading indicator with "Starting scan..."
    showLoadingIndicator('Starting scan...');

    // Disable the Manual Capture button and Stop button to prevent multiple clicks
    const manualCaptureButton = document.getElementById('manual-capture-button');
    const stopButton = document.getElementById('stop-scan-button');
    manualCaptureButton.disabled = true;
    stopButton.disabled = true;

    fetch('/scan/manual_capture', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            scanInterval: scanInterval,
            selectedProject: project
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showSuccess(`Manual capture started for project: ${data.project}`, 'Scan Status');
            // Update loading indicator to "Scanning..."
            showLoadingIndicator('Scanning...');
            // Enable the Stop button
            stopButton.disabled = false;
            // Start polling for scan status
            pollScanStatus();
        } else {
            showError(`Error: ${data.message}`, 'Scan Status');
            hideLoadingIndicator();
            manualCaptureButton.disabled = false;
            stopButton.disabled = true;
        }
    })
    .catch(error => {
        console.error('Error starting manual capture:', error);
        showError('An error occurred while starting the manual capture.', 'Scan Status');
        hideLoadingIndicator();
        manualCaptureButton.disabled = false;
        stopButton.disabled = true;
    });
}

// Function to handle Auto Scan form submission
function handleAutoScan(event) {
    event.preventDefault(); // Prevent default form submission

    // Check if the scanner is connected
    if (!scannerConnected) {
        showError('Scanner is not connected. Please connect the scanner before starting a scan.', 'Scan Validation');
        return;
    }

    const scanInterval = parseInt(document.getElementById('scanInterval').value);
    const selectedProject = document.querySelector('input[name="selected-project"]:checked');

    let project = null;
    if (selectedProject) {
        project = selectedProject.value;
    } else {
        showWarning('Please select or create a project before starting a scan.', 'Scan Validation');
        return;
    }

    // Input Validation
    if (scanInterval < 1) {
        showWarning('Scan interval must be at least 1.', 'Scan Validation');
        return;
    }

    // Show loading indicator with "Starting auto scan..."
    showLoadingIndicator('Starting auto scan...');

    // Disable the Auto Scan button and Stop button to prevent multiple clicks
    const autoScanButton = document.getElementById('auto-scan-button');
    const stopButton = document.getElementById('stop-scan-button');
    autoScanButton.disabled = true;
    stopButton.disabled = true;

    fetch('/scan/auto_scan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            scanInterval: scanInterval,
            selectedProject: project
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showSuccess(`Auto scan started for project: ${data.project}`, 'Scan Status');
            // Update loading indicator to "Scanning..."
            showLoadingIndicator('Scanning...');
            // Enable the Stop button
            stopButton.disabled = false;
            // Start polling for scan status
            pollScanStatus();
        } else {
            showError(`Error: ${data.message}`, 'Scan Status');
            hideLoadingIndicator();
            autoScanButton.disabled = false;
            stopButton.disabled = true;
        }
    })
    .catch(error => {
        console.error('Error starting auto scan:', error);
        showError('An error occurred while starting the auto scan.', 'Scan Status');
        hideLoadingIndicator();
        autoScanButton.disabled = false;
        stopButton.disabled = true;
    });
}

// Function to handle Stop Scan form submission
function handleStopScan(event) {
    event.preventDefault(); // Prevent default form submission

    console.log('Stop scan button clicked'); // Debugging log

    // Show loading indicator with "Stopping scan..."
    showLoadingIndicator('Stopping scan...');

    // Disable the Stop button to prevent multiple clicks
    const stopButton = document.getElementById('stop-scan-button');
    const startButton = document.getElementById('start-scan-button');
    stopButton.disabled = true;
    startButton.disabled = true;

    fetch('/scan/stop_scan', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
    })
    .then(response => {
        console.log('Response received from stop_scan:', response); // Debugging log
        return response.json();
    })
    .then(data => {
        console.log('Data received from stop_scan:', data); // Debugging log
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
        fetch('/scan/is_processing')
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
            return fetch('/project/rename_project', {
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
                    showSuccess('Project renamed successfully.', 'scanner is not  Management');
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
            fetch('/project/delete_project', {
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
    fetch('/project/create_project', {
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

function highlightSelectedProject(radio) {
    // Remove highlight from all project items
    const projectItems = document.querySelectorAll('.project-item');
    projectItems.forEach(item => {
        item.classList.remove('highlighted');
    });

    // Add highlight to the selected project item
    const selectedProjectItem = radio.closest('.project-item');
    if (selectedProjectItem) {
        selectedProjectItem.classList.add('highlighted');
    }

    // Fetch and display planned scan count
    const projectName = radio.value;
    fetch(`/project/get_positions?projectName=${projectName}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const plannedScanCount = data.positions.length;
                document.getElementById('planned-scan-count').textContent = `Planned Scans: ${plannedScanCount}`;
            } else {
                document.getElementById('planned-scan-count').textContent = 'Planned Scans: NaN';
                showWarning('positions.json not found or empty for the selected project.', 'Project Selection');
            }
        })
        .catch(error => {
            console.error('Error fetching positions:', error);
            document.getElementById('planned-scan-count').textContent = 'Planned Scans: NaN';
            showWarning('positions.json not found or empty for the selected project.', 'Project Selection');
        });
}

function attemptReconnect() {
    fetch('/interface/attempt_reconnect', { method: 'POST' })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === "success") {
                toastr.success(data.message);
                updateConnectionStatus(true);
            } else {
                toastr.error(data.message);
                updateConnectionStatus(false);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            toastr.error('Reconnection attempt failed.');
            updateConnectionStatus(false);
        });
}


function nextScan() {
    const selectedProject = document.querySelector('input[name="selected-project"]:checked');
    if (!selectedProject) {
        showWarning('No project selected.', 'Scan Selector');
        return;
    }
    if (currentScanIndex < totalScans) {
        currentScanIndex++;
        updateScanSelector();
        console.log(`Current scan index: ${currentScanIndex}`);
    }
}

function previousScan() {
    const selectedProject = document.querySelector('input[name="selected-project"]:checked');
    if (!selectedProject) {
        showWarning('No project selected.', 'Scan Selector');
        return;
    }
    if (currentScanIndex > 1) {
        currentScanIndex--;
        updateScanSelector();
        console.log(`Current scan index: ${currentScanIndex}`);
    }
}

function firstScan() {
    const selectedProject = document.querySelector('input[name="selected-project"]:checked');
    if (!selectedProject) {
        showWarning('No project selected.', 'Scan Selector');
        return;
    }
    if (totalScans > 0) {
        currentScanIndex = 1;
        updateScanSelector();
        console.log(`Current scan index: ${currentScanIndex}`);
    }
}

function lastScan() {
    const selectedProject = document.querySelector('input[name="selected-project"]:checked');
    if (!selectedProject) {
        showWarning('No project selected.', 'Scan Selector');
        return;
    }
    if (totalScans > 0) {
        currentScanIndex = totalScans;
        updateScanSelector();
        console.log(`Current scan index: ${currentScanIndex}`);
    }
}

function requestAndDisplayPointCloudForIndex(scanIndex) {
    const selectedProject = document.querySelector('input[name="selected-project"]:checked');
    if (!selectedProject) {
        showError('Please select a project first.', 'Project Selection');
        return;
    }

    const projectName = selectedProject.value;
    console.log(`Requesting point cloud for project: ${projectName}, scan index: ${scanIndex}`);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 seconds timeout

    fetch(`/project/get_full_size_point_cloud?projectName=${projectName}&scanIndex=${scanIndex}&downsample=true&targetPoints=100000`, { signal: controller.signal })
        .then(response => {
            clearTimeout(timeoutId);
            console.log('Fetch response received:', response);
            return response.json();
        })
        .then(data => {
            console.log('Fetch data received:', data);
            if (data.status === 'success') {
                const pointCloud = data.point_cloud;
                displayPointCloudOverlay(pointCloud);
            } else {
                showError(`Error: ${data.message}`, 'Point Cloud Retrieval');
            }
        })
        .catch(error => {
            if (error.name === 'AbortError') {
                console.error('Fetch request timed out');
                showError('Request timed out. Please try again.', 'Point Cloud Retrieval');
            } else {
                console.error('Error fetching point cloud:', error);
                showError('An unexpected error occurred while fetching the point cloud.', 'Point Cloud Retrieval');
            }
        });
}

// Optionally, periodically check scanner status and update UI
setInterval(function() {
    fetch('/interface/scanner_status')
        .then(response => response.json())
        .then(data => {
            updateConnectionStatus(data.connected);
        })
        .catch(error => {
            console.error('Error:', error);
            updateConnectionStatus(false);
        });
}, 5000); // Every 5 seconds

let autoRefresh = localStorage.getItem('autoRefresh') !== 'false'; // Default to true if not set

function toggleAutoRefresh() {
    autoRefresh = !autoRefresh;
    localStorage.setItem('autoRefresh', autoRefresh);
}

let currentScanIndex = 1;
let totalScans = 0;
let lastRequestedScanIndex = null;

function runPreviewScan() {
    const selectedProject = document.querySelector('input[name="selected-project"]:checked');
    if (!selectedProject) {
        showWarning('Please select a project first.', 'Project Selection');
        return;
    }

    const projectName = selectedProject.value;

    // Show loading indicator with "Running preview scan..."
    showLoadingIndicator('Running preview scan...');

    fetch('/project/preview_scan', {
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
            showSuccess(`Preview scan completed for project: ${data.project}`, 'Preview Scan');
        } else {
            showError(`Error: ${data.message}`, 'Preview Scan');
        }
        hideLoadingIndicator();
    })
    .catch(error => {
        console.error('Error running preview scan:', error);
        showError('An error occurred while running the preview scan.', 'Preview Scan');
        hideLoadingIndicator();
    });
}

document.addEventListener('DOMContentLoaded', function() {
    let autoRefresh = localStorage.getItem('autoRefresh') !== 'false'; // Default to true if not set
    const autoRefreshCheckbox = document.getElementById('auto-refresh-checkbox');
    if (autoRefreshCheckbox) {
        autoRefreshCheckbox.checked = autoRefresh;
    }

    function updateScanSelector() {
        const selectedProject = document.querySelector('input[name="selected-project"]:checked');
        if (!selectedProject) {
            document.getElementById('scan-selector').textContent = 'No project selected';
            return;
        }

        const projectName = selectedProject.value;
        fetch(`/project/get_scan_count?projectName=${projectName}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const previousTotalScans = totalScans;
                    totalScans = data.scanCount;
                    document.getElementById('scan-selector').textContent = `${currentScanIndex}/${totalScans}`;
                    // If auto-refresh is enabled and the total scans have increased, jump to the last scan
                    if (autoRefresh && totalScans > previousTotalScans) {
                        currentScanIndex = totalScans;
                    }
                    // Request and display the scan preview only if the scan index has changed
                    if (currentScanIndex !== lastRequestedScanIndex) {
                        showViewerLoadingIndicator();
                        requestScanPreview(projectName, currentScanIndex);
                        lastRequestedScanIndex = currentScanIndex;
                    }
                } else {
                    showError(`Error: ${data.message}`, 'Scan Selector');
                }
            })
            .catch(error => {
                console.error('Error fetching scan count:', error);
                showError('An unexpected error occurred while fetching scan count.', 'Scan Selector');
            });
    }

    // Attach the function to the window object to make it globally accessible
    window.updateScanSelector = updateScanSelector;

    window.onload = function() {
        fetchLogs();
        loadScanInterval(); // Load scan interval from localStorage

        // Initially disable the Stop button since no scan is active
        const stopButton = document.getElementById('stop-scan-button');
        if (stopButton) {
            stopButton.disabled = true;
        }

        // Start polling for logs every 2 seconds
        setInterval(fetchLogs, 2000);

        // Check scanner status immediately
        checkScannerStatus();

        // Start polling for scanner status every 10 seconds
        setInterval(() => checkScannerStatus(30000), 10000); // every 10 seconds

        // Update scan selector every 5 seconds
        setInterval(updateScanSelector, 5000);

        // Initialize auto-refresh checkbox
        let autoRefresh = localStorage.getItem('autoRefresh') !== 'false'; // Default to true if not set
        const autoRefreshCheckbox = document.getElementById('auto-refresh-checkbox');
        if (autoRefreshCheckbox) {
            autoRefreshCheckbox.checked = autoRefresh;
        }
    };
});
