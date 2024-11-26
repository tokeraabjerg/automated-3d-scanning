// static/preview.js

// Function to load the point cloud
function loadPointCloud() {
    const viewer = document.getElementById('viewer');

    // Clear any existing content
    while (viewer.firstChild) {
        viewer.removeChild(viewer.firstChild);
    }

    // Fetch the reduced point cloud from the backend
    fetch('/get_reduced_point_cloud')
        .then(response => {
            if (!response.ok) {
                throw new Error('No reduced point cloud available.');
            }
            return response.arrayBuffer();
        })
        .then(buffer => {
            // Initialize three.js scene and render the point cloud
            initThreeJS(buffer);
        })
        .catch(error => {
            console.error('Error loading point cloud:', error);
            showError('Failed to load point cloud. Please ensure a scan has been completed.');
        });
}

// Initialize three.js scene
function initThreeJS(buffer) {
    const container = document.getElementById('viewer');

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

    // Load point cloud using PLYLoader
    const loader = new THREE.PLYLoader();
    const geometry = loader.parse(buffer);
    
    // Assume that the PLY file contains color information
    geometry.computeVertexNormals(); // Compute normals if not present

    const material = new THREE.PointsMaterial({ size: 0.5, vertexColors: true });
    const points = new THREE.Points(geometry, material);
    scene.add(points);

    // Fit camera to point cloud
    const boundingBox = new THREE.Box3().setFromObject(points);
    const center = boundingBox.getCenter(new THREE.Vector3());
    const size = boundingBox.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = camera.fov * (Math.PI / 180);
    let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
    camera.position.z = cameraZ * 1.5;
    camera.lookAt(center);

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
}

// Export the loadPointCloud function to be accessible from scripts.js
window.loadPointCloud = loadPointCloud;
