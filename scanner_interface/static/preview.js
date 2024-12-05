// static/preview.js

// Function to load the point cloud from data
function loadPointCloudFromData(data, containerId = 'viewer') {
    console.log('Loading point cloud data into container:', containerId);
    const viewer = document.getElementById(containerId);

    // Show the loading indicator
    const container = viewer.parentElement;
    const loadingIndicator = container.querySelector('#viewer-loading-indicator');
    if (loadingIndicator) {
        loadingIndicator.style.display = 'flex';
    }

    // Clear any existing content
    while (viewer.firstChild) {
        viewer.removeChild(viewer.firstChild);
    }

    // Separate points and intensities
    const points = new Float32Array(data.points.flat());
    const intensities = new Float32Array(data.intensities);

    console.log('Points and intensities separated:', points.length, intensities.length);

    // Create a buffer geometry and set the attributes
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(points, 3));

    // Normalize intensities to [0, 1] range
    const maxIntensity = Math.max(...intensities);
    const normalizedIntensities = intensities.map(i => i / maxIntensity);

    console.log('Intensities normalized:', normalizedIntensities.length);

    // Create colors based on intensities
    const colors = new Float32Array(normalizedIntensities.length * 3);
    for (let i = 0; i < normalizedIntensities.length; i++) {
        const intensity = normalizedIntensities[i];
        colors[i * 3] = intensity; // R
        colors[i * 3 + 1] = intensity; // G
        colors[i * 3 + 2] = intensity; // B
    }
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    console.log('Colors created:', colors.length);

    // Create a material and points object
    const material = new THREE.PointsMaterial({ size: 0.5, vertexColors: true });
    const pointCloud = new THREE.Points(geometry, material);

    console.log('Point cloud created, initializing three.js scene...');
    // Initialize three.js scene and render the point cloud
    initThreeJS(pointCloud, containerId).then(() => {
        // Hide the loading indicator after the scene is initialized
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
            console.log('Loading indicator hidden.');
        }
    }).catch(error => {
        console.error('Error initializing Three.js scene:', error);
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
        showError('An error occurred while loading the 3D preview.', 'Loading Error');
    });
}

// Initialize three.js scene
function initThreeJS(pointCloud, containerId = 'viewer') {
    return new Promise((resolve, reject) => {
        try {
            const container = document.getElementById(containerId);

            // Create scene, camera, renderer
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 1, 100000);
            camera.position.set(0, 0, 100);

            const renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(container.clientWidth, container.clientHeight);
            
            // Set the background color to white
            renderer.setClearColor(0xffffff, 1); // white background

            container.appendChild(renderer.domElement);

            // Add controls
            const controls = new THREE.OrbitControls(camera, renderer.domElement);

            // Add the point cloud to the scene
            scene.add(pointCloud);

            // Fit camera to point cloud
            const boundingBox = new THREE.Box3().setFromObject(pointCloud);
            const center = boundingBox.getCenter(new THREE.Vector3());
            const size = boundingBox.getSize(new THREE.Vector3());
            const maxDim = Math.max(size.x, size.y, size.z);
            const fov = camera.fov * (Math.PI / 180);
            let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
            camera.position.z = cameraZ * 1.5;
            camera.lookAt(center);

            // Set the OrbitControls' target to the center of the point cloud
            controls.target.copy(center);
            controls.update();

            // Handle window resize
            window.addEventListener('resize', function() {
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            });

            // Animate the scene
            function animate() {
                requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }
            animate();

            console.log('Three.js scene initialized successfully.');
            resolve();
        } catch (error) {
            reject(error);
        }
    });
}

function requestScanPreview(projectName, scanIndex) {
    let scanFile = scanIndex === 0 ? 'scan_main' : `scan_${scanIndex}`;
    fetch(`/project/get_scan_preview?projectName=${projectName}&scanFile=${scanFile}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                displayScanPreview(data.scanPreview);
            } else {
                showError(`Error: ${data.message}`, 'Scan Preview');
            }
        })
        .catch(error => {
            console.error('Error fetching scan preview:', error);
            showError('An unexpected error occurred while fetching scan preview.', 'Scan Preview');
        });
}

function displayScanPreview(scanPreview) {
    // Use the preview.js to load the point cloud
    loadPointCloudFromData(scanPreview);
}

function requestAndDisplayPointCloud(pointCloud) {
    fetch('/process_point_cloud', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ point_cloud: pointCloud })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            const processedPointCloud = data.point_cloud;
            displayPointCloudOverlay(processedPointCloud);
        } else {
            showError(`Error: ${data.message}`, 'Point Cloud Processing');
        }
    })
    .catch(error => {
        console.error('Error processing point cloud:', error);
        showError('An unexpected error occurred while processing the point cloud.', 'Point Cloud Processing');
    });
}

function displayPointCloudOverlay(pointCloud) {
    console.log('Displaying point cloud overlay with data:', pointCloud);
    Swal.fire({
        title: 'Point Cloud Preview',
        html: '<div id="point-cloud-viewer" style="width: 100%; height: 600px;"></div>', // Increase height to 600px
        width: '90%', // Increase width to 90%
        showCloseButton: true,
        didOpen: () => {
            console.log('Popup opened, loading point cloud data...');
            loadPointCloudFromData(pointCloud, 'point-cloud-viewer');
        }
    });
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

// // WebSocket listener for receiving point clouds
// function setupWebSocket() {
//     const socket = new WebSocket('ws://localhost:5001/point_cloud');

//     socket.onopen = function(event) {
//         console.log('WebSocket connection opened:', event);
//     };

//     socket.onmessage = function(event) {
//         console.log('WebSocket message received:', event);
//         const pointCloud = JSON.parse(event.data);
//         displayPointCloudOverlay(pointCloud);
//     };

//     socket.onclose = function(event) {
//         console.log('WebSocket connection closed:', event);
//     };

//     socket.onerror = function(error) {
//         console.error('WebSocket error:', error);
//     };
// }

// // Initialize WebSocket listener when the document is ready
// document.addEventListener('DOMContentLoaded', function() {
//     setupWebSocket();
// });

// Export the functions to be accessible from other scripts
window.loadPointCloudFromData = loadPointCloudFromData;
window.requestScanPreview = requestScanPreview;
window.displayScanPreview = displayScanPreview;
window.requestAndDisplayPointCloud = requestAndDisplayPointCloud;
