import open3d as o3d
import numpy as np
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def global_imports(modulename,shortname = None, asfunction = False):
    if shortname is None: 
        shortname = modulename
    if asfunction is False:
        globals()[shortname] = __import__(modulename)
    else:        
        globals()[shortname] = eval(modulename + "." + shortname)

def compute_nearest_degree(target_angle, motor):
    """
    Compute the nearest possible angle that a stepper motor can achieve.
    
    Args:
        target_angle (float): The target angle in degrees. 
        motor (str): The motor type (either "pan" or "tilt").
    
    Returns:
        float: The closest possible angle in degrees.
    
    Home-ish
        {
        "pos_a": 2716,  min 0 max ca 5800
        "pos_b": 619    min 0 max ca 2000
    }
    """
    
    # Convert the target angle to steps
    steps_per_degree = 19.5
    steps = target_angle * steps_per_degree
    
    # Round to the nearest integer step
    nearest_steps = round(steps)
    
    # Convert back to degrees
    nearest_angle = nearest_steps / steps_per_degree
    
    # TODO: check zero steps!
    if motor == "pan":
        zero_steps = 2716
    elif motor == "tilt":
        zero_steps = 619
    else:
        raise ValueError("Invalid motor type. Must be 'pan' or 'tilt'.")
    
    abs_steps = nearest_steps + zero_steps

    return nearest_steps, abs_steps, nearest_angle

def compute_bounding_box(point_cloud):
    """
    Beregn bounding box for en point cloud.

    Args:
        point_cloud (o3d.geometry.PointCloud): Point cloud, hvor bounding box skal beregnes.

    Returns:
        tuple: Min- og max-koordinater (x_min, y_min, z_min, x_max, y_max, z_max).
    """
    # Beregn bounding box
    bbox = point_cloud.get_axis_aligned_bounding_box()
    
    # Hent min og max koordinater
    min_bound = np.asarray(bbox.min_bound)
    max_bound = np.asarray(bbox.max_bound)
    
    print(f"Bounding box min: {min_bound}")
    print(f"Bounding box max: {max_bound}")
    
    return min_bound, max_bound

def compute_rotation_axis(pcd1, pcd2, angle):
    """
    Finds the axis of rotation given two point clouds and a known rotation angle.

    Args:
        pcd1 (o3d.geometry.PointCloud): First point cloud.
        pcd2 (o3d.geometry.PointCloud): Second point cloud (rotated version of pcd1).
        angle (float): Known rotation angle (in radians).

    Returns:
        np.ndarray: Unit vector representing the axis of rotation.
    """
    # Translate point clouds to center at the origin
    pcd1_centered = np.asarray(pcd1.points) - np.mean(np.asarray(pcd1.points), axis=0)
    pcd2_centered = np.asarray(pcd2.points) - np.mean(np.asarray(pcd2.points), axis=0)
    
    # Compute the cross-covariance matrix
    H = np.dot(pcd1_centered.T, pcd2_centered)
    
    # Singular Value Decomposition
    U, _, Vt = np.linalg.svd(H)
    R = np.dot(Vt.T, U.T)
    
    # Ensure R is a valid rotation matrix (det(R) should be 1)
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = np.dot(Vt.T, U.T)
    
    # Extract the axis of rotation from the rotation matrix
    axis = np.array([R[2, 1] - R[1, 2],
                     R[0, 2] - R[2, 0],
                     R[1, 0] - R[0, 1]])
    axis = axis / np.linalg.norm(axis)  # Normalize the axis
    
    return axis


def remove_small_clusters(point_cloud, min_cluster_size, eps):
    """
    Fjerner små grupper af punkter fra en point cloud.

    Args:
        point_cloud (o3d.geometry.PointCloud): Point cloud der skal renses.
        min_cluster_size (int): Minimum antal punkter i en gruppe for at blive bevaret.

    Returns:
        o3d.geometry.PointCloud: Filtreret point cloud uden små grupper.
    """
    # Brug DBSCAN til clustering
    labels = np.array(point_cloud.cluster_dbscan(eps, min_cluster_size, print_progress=True)
    )
    
    # Find størrelsen af hver gruppe
    unique_labels, counts = np.unique(labels, return_counts=True)
    print(f"Antal grupper fundet: {len(unique_labels)}")

    # Find den største gruppe
    largest_cluster = unique_labels[np.argmax(counts)]
    print(f"Største gruppe størrelse: {counts.max()}")

    # Bevar kun punkter fra grupper, der opfylder minimumsstørrelsen
    filtered_indices = [i for i, label in enumerate(labels) if counts[label] >= min_cluster_size]
    filtered_point_cloud = point_cloud.select_by_index(filtered_indices)

    return filtered_point_cloud

def extract_rotation_axis_and_angle(R):
    """
    Extracts the rotation axis and angle from a rotation matrix.

    #OBS! FUNCTION NOT TESTED
    Args:
        R (np.ndarray): 3x3 rotation matrix.

    Returns:
        tuple: (axis, angle), where `axis` is the rotation axis (normalized)
               and `angle` is the rotation angle in radians.
    """
    # Ensure the matrix is valid (orthogonal and determinant close to 1)
    if not np.allclose(np.dot(R.T, R), np.eye(3)) or not np.isclose(np.linalg.det(R), 1):
        raise ValueError("Input is not a valid rotation matrix.")

    # Compute the rotation angle
    angle = np.arccos((np.trace(R) - 1) / 2)

    # Handle numerical precision issues for small angles
    if np.isclose(angle, 0):
        # No rotation, arbitrary axis
        return np.array([1, 0, 0]), 0

    # Compute the rotation axis using the antisymmetric part of R
    axis = np.array([
        R[2, 1] - R[1, 2],
        R[0, 2] - R[2, 0],
        R[1, 0] - R[0, 1]
    ]) / (2 * np.sin(angle))

    return axis, angle

def create_arrow(origin, direction, color, shaft_radius=1, head_radius=2, head_length=10, length=100):
    """
    Creates a colored arrow starting at a given origin and pointing in a specified direction.

    Args:
        origin (tuple): Starting point of the arrow (x, y, z).
        direction (tuple): Direction vector of the arrow (x, y, z).
        color (tuple): Color of the arrow in RGB format (r, g, b).
        shaft_radius (float): Radius of the arrow's shaft.
        head_radius (float): Radius of the arrow's head.
        head_length (float): Length of the arrow's head.
        length (float): Total length of the arrow.

    Returns:
        open3d.geometry.TriangleMesh: Arrow mesh.
    """
    # Normalize direction
    direction = np.array(direction)
    direction = direction / np.linalg.norm(direction) * length

    # Create arrow mesh
    arrow = o3d.geometry.TriangleMesh.create_arrow(
        cylinder_radius=shaft_radius,
        cone_radius=head_radius,
        cylinder_height=length - head_length,
        cone_height=head_length
    )
    arrow.paint_uniform_color(color)

    # Align arrow direction
    z_axis = np.array([0, 0, 1])  # Default arrow direction
    rotation_axis = np.cross(z_axis, direction)
    if np.linalg.norm(rotation_axis) < 1e-6:
        rotation_matrix = np.eye(3)  # No rotation needed
    else:
        rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)
        angle = np.arccos(np.dot(z_axis, direction) / np.linalg.norm(direction))
        rotation_matrix = o3d.geometry.get_rotation_matrix_from_axis_angle(rotation_axis * angle)

    arrow.rotate(rotation_matrix, center=(0, 0, 0))

    # Translate arrow to its origin
    arrow.translate(origin)
    return arrow

def create_circle_mesh(diameter, z_value=0, color=(1, 0, 0)):
    """
    Create a 3D mesh of a circle with the given diameter.

    Args:
        diameter (float): The diameter of the circle.
        z_value (float): The z-coordinate where the circle lies.
        color (tuple): The color of the circle in RGB format (r, g, b).

    Returns:
        open3d.geometry.TriangleMesh: Circle mesh.
    """
    radius = diameter / 2
    circle = o3d.geometry.TriangleMesh.create_sphere(radius=radius, resolution=20)
    circle.paint_uniform_color(color)
    
    # Scale the sphere to make it a flat circle
    scale_matrix = np.diag([1, 1, 0.01, 1])
    circle.transform(scale_matrix)
    
    # Translate the circle to the specified z_value
    circle.translate((0, 0, z_value))
    
    return circle

# example usage
# Define arrows
arrows = [
    create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
]

# Combine arrows into a single geometry
combined_geometry = o3d.geometry.TriangleMesh()
for arrow in arrows:
    combined_geometry += arrow

# Visualize
#o3d.visualization.draw_geometries([combined_geometry])

def decompose_transformation(transformation):
    """
    Udtrækker translation og rotation fra en 4x4 transformationsmatrix.
    TODO: Appears bugged!
    Args:
        transformation (np.ndarray): 4x4 transformationsmatrix.

    Returns:
        dict: En dictionary med 'translation' (x, y, z) og 'rotation' (roll, pitch, yaw i grader).
    """

    # Kontroller input
    if transformation.shape != (4, 4):
        raise ValueError("Transformationsmatrixen skal være 4x4.")

    # Udtræk translation (de sidste tre elementer i den fjerde kolonne)
    translation = transformation[:3, 3]

    # Udtræk rotationsdelen (de første tre rækker og kolonner)
    rotation_matrix = transformation[:3, :3]

    # Beregn Euler-vinkler fra rotationsmatrixen (roll, pitch, yaw) assuming fixed angles XYZ order
    sy = np.sqrt(rotation_matrix[0, 0]**2 + rotation_matrix[1, 0]**2)

    singular = sy < 1e-6  # Tjek for singularitet

    if not singular:
        roll = np.arctan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
        pitch = np.arctan2(-rotation_matrix[2, 0], sy)
        yaw = np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
    else:
        roll = np.arctan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
        pitch = np.arctan2(-rotation_matrix[2, 0], sy)
        yaw = 0

    # Konverter rotation fra radianer til grader
    roll = np.degrees(roll)
    pitch = np.degrees(pitch)
    yaw = np.degrees(yaw)

    return rotation_matrix, translation, roll, pitch, yaw

def calculate_error(source, target):
    # Compute the point-to-point distance (RMSE)
    distances = source.compute_point_cloud_distance(target)
    rmse = np.sqrt(np.mean(np.array(distances) ** 2))

    return rmse

def remove_points_within_distance_of_pointcloud(source_pcd, target_pcd, distance_threshold):
    """
    Input: Source_pcd, Target_pcd, distance_threshold
    Output: Target_pcd - [every point within distance_threshold of Source_pcd]
    """
    
    # Convert point clouds to numpy arrays
    source_points = np.asarray(source_pcd.points)
    target_points = np.asarray(target_pcd.points)

    # Create a KDTree for the target point cloud
    target_kdtree = o3d.geometry.KDTreeFlann(target_pcd)

    # Initialize a mask to keep track of points to keep
    mask = np.ones(len(source_points), dtype=bool)

    # Iterate over each point in the source point cloud
    for i, point in enumerate(source_points):
        # Find the nearest neighbors within the distance threshold
        [k, idx, _] = target_kdtree.search_radius_vector_3d(point, distance_threshold)
        if k > 0:
            mask[i] = False

    # Filter the points
    filtered_points = source_points[mask]

    # Create a new point cloud with the filtered points
    filtered_pcd = o3d.geometry.PointCloud()
    filtered_pcd.points = o3d.utility.Vector3dVector(filtered_points)

    return filtered_pcd

def sample_adjacent_point_pairs(pcd, n, max_distance):
    points = np.asarray(pcd.points)
    num_points = points.shape[0]

    if num_points < 2:
        raise ValueError("Point cloud must contain at least 2 points.")

    if n >= num_points - 1:
        raise ValueError("Number of samples must be less than the number of adjacent point pairs.")

    # Randomly sample n indices from the range [0, num_points - 2]
    sampled_indices = np.random.choice(num_points - 1, n, replace=False)

    # Calculate distances between adjacent point pairs
    distances = np.linalg.norm(points[sampled_indices + 1] - points[sampled_indices], axis=1)

    # Filter out distances greater than max_distance
    valid_distances = distances[distances <= max_distance]

    if len(valid_distances) == 0:
        raise ValueError("No valid distances found within the specified max_distance.")

    # Calculate the average distance
    average_distance = np.mean(valid_distances)

    return average_distance

def average_distance_to_nearest_point(pcd):
    points = np.asarray(pcd.points)
    num_points = points.shape[0]

    if num_points < 2:
        raise ValueError("Point cloud must contain at least 2 points.")

    # Create a KD-tree for the point cloud
    kdtree = o3d.geometry.KDTreeFlann(pcd)

    # Initialize a list to store the distances to the nearest point
    distances = []

    # Iterate over each point in the point cloud
    for i in range(num_points):
        # Find the nearest neighbor (excluding the point itself)
        [_, idx, dists] = kdtree.search_knn_vector_3d(points[i], 2)
        distances.append(dists[1])  # The first distance is 0 (the point itself), so take the second

    # Calculate the average distance
    average_distance = np.mean(distances)

    return average_distance

def get_xyz_euler(roll, pitch, yaw):
    """
    Rotate a point cloud using Euler angles (roll, pitch, yaw) at a specified index.
    If no Euler angles exist for the index, no rotation is applied.

    Args:
        target (o3d.geometry.PointCloud): The target point cloud to process.
        euler_angles (list[tuple]): List of Euler angles (roll, pitch, yaw) in degrees.
        index (int): Index in the Euler angles list to use for rotation.

    Returns:
        o3d.geometry.PointCloud: The rotated point cloud.
        np.ndarray: The 4x4 transformation matrix used for the rotation.
    """

    # Retrieve the Euler angles at the specified index
    roll, pitch, yaw

    # Convert angles from degrees to radians
    roll = np.radians(roll)
    pitch = np.radians(pitch)
    yaw = np.radians(yaw)

    # Rotation matrices for each axis
    R_x = np.array([
        [1, 0, 0],
        [0, np.cos(roll), -np.sin(roll)],
        [0, np.sin(roll), np.cos(roll)]
    ])

    R_y = np.array([
        [np.cos(pitch), 0, np.sin(pitch)],
        [0, 1, 0],
        [-np.sin(pitch), 0, np.cos(pitch)]
    ])

    R_z = np.array([
        [np.cos(yaw), -np.sin(yaw), 0],
        [np.sin(yaw), np.cos(yaw), 0],
        [0, 0, 1]
    ])

    # Combine the rotations (R = Rz * Ry * Rx)
    R = R_x @ R_y @ R_z

    # Create a 4x4 transformation matrix
    R_4x4 = np.eye(4)
    R_4x4[:3, :3] = R

    print(f"Point cloud rotated by Euler angles (roll={np.degrees(roll):.2f}°, pitch={np.degrees(pitch):.2f}°, yaw={np.degrees(yaw):.2f}°).")

    return R

def remove_outliers_dbscan(point_cloud, eps=0.02, min_points=10):
    """
    Remove outliers from a point cloud using DBSCAN clustering.

    Args:
        point_cloud (o3d.geometry.PointCloud): The input point cloud.
        eps (float): The maximum distance between two samples for them to be considered as in the same neighborhood.
        min_points (int): The number of samples in a neighborhood for a point to be considered as a core point.

    Returns:
        o3d.geometry.PointCloud: The filtered point cloud with outliers removed.
    """
    labels = np.array(point_cloud.cluster_dbscan(eps=eps, min_points=min_points, print_progress=True))
    max_label = labels.max()
    inlier_indices = np.where(labels >= 0)[0]
    filtered_point_cloud = point_cloud.select_by_index(inlier_indices)
    return filtered_point_cloud

def show_clusters_dbscan(point_cloud, eps=0.02, min_points=10, min_cluster_size=100):
    """
    Show clusters from a point cloud using DBSCAN clustering that are above a certain size.

    Args:
        point_cloud (o3d.geometry.PointCloud): The input point cloud.
        eps (float): The maximum distance between two samples for them to be considered as in the same neighborhood.
        min_points (int): The number of samples in a neighborhood for a point to be considered as a core point.
        min_cluster_size (int): The minimum size of clusters to be shown.

    Returns:
        o3d.geometry.PointCloud: The filtered point cloud with clusters above the specified size.
    """
    labels = np.array(point_cloud.cluster_dbscan(eps=eps, min_points=min_points, print_progress=True))
    unique_labels, counts = np.unique(labels, return_counts=True)
    large_clusters_indices = [i for i, label in enumerate(labels) if counts[label] >= min_cluster_size and label >= 0]
    filtered_point_cloud = point_cloud.select_by_index(large_clusters_indices)
    return filtered_point_cloud

def inverse_radius_filter_point_cloud(point_cloud, radius):
    """
    Centers the point cloud to the global zero point and removes points beyond the specified radius around the x-axis.
    
    Args:
        point_cloud (o3d.geometry.PointCloud): The input point cloud.
        radius (float): The radius to use for filtering points.
    
    Returns:
        o3d.geometry.PointCloud: The filtered point cloud.
        np.ndarray: The centroid of the original point cloud.
    """

    # Filter points within the specified radius around the x-axis
    def filter_function(point):
        x, y, z = point
        distance = np.sqrt(y**2 + z**2)
        return distance <= radius

    filtered_points = np.asarray(point_cloud.points)[np.apply_along_axis(filter_function, 1, np.asarray(point_cloud.points))]
    filtered_point_cloud = o3d.geometry.PointCloud()
    filtered_point_cloud.points = o3d.utility.Vector3dVector(filtered_points)

    return filtered_point_cloud

def Point_to_Point(source, target, max_correspondence_distance):
    # Point Association using ICP for Open3D v0.18.0
    print("Running ICP...")

    # Initializing convergence criteria (using ICPConvergenceCriteria)
    criteria = o3d.pipelines.registration.ICPConvergenceCriteria(
        relative_fitness=1e-12, 
        relative_rmse=1e-12, 
        max_iteration=200  # Increase the number of iterations
    )

    # Perform ICP with scaling
    icp_result = o3d.pipelines.registration.registration_icp(
        target, source, max_correspondence_distance=max_correspondence_distance, 
        init=np.eye(4),  # Initial transformation (identity matrix)
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(with_scaling=True),
        criteria=criteria
    )

    print("Fitness: ", icp_result.fitness)
    print("Inlier RMSE: ", icp_result.inlier_rmse)

    # Apply the transformation to the target point cloud
    target.transform(icp_result.transformation)

    # Return the transformed target point cloud for further use (or visualization)
    return icp_result.transformation, target

def find_smallest_circle_diameter(point_cloud):
    """
    Find the diameter of the smallest circle in a cylindrical point cloud along the z-axis using RANSAC.

    Args:
        point_cloud (o3d.geometry.PointCloud): The input cylindrical point cloud.

    Returns:
        float: The diameter of the smallest circle.
    """
    points = np.asarray(point_cloud.points)
    
    # Project points onto the XY plane
    xy_points = points[:, :2]
    
    # Use RANSAC to fit a circle to the points
    def fit_circle(points):
        A = np.hstack([points, np.ones((points.shape[0], 1))])
        b = np.sum(points**2, axis=1)
        x = np.linalg.lstsq(A, b, rcond=None)[0]
        center = x[:2] / 2
        radius = np.sqrt(x[2] + np.sum(center**2))
        return center, radius

    best_radius = float('inf')
    best_center = None
    num_iterations = 1000
    threshold = 0.01

    for _ in range(num_iterations):
        sample_indices = np.random.choice(xy_points.shape[0], 3, replace=False)
        sample_points = xy_points[sample_indices]
        try:
            center, radius = fit_circle(sample_points)
            distances = np.linalg.norm(xy_points - center, axis=1)
            inliers = np.abs(distances - radius) < threshold
            if np.sum(inliers) > 3 and radius < best_radius:
                best_radius = radius
                best_center = center
        except np.linalg.LinAlgError:
            continue
    
    min_diameter = 2 * best_radius if best_radius != float('inf') else None
    
    return min_diameter

def highlight_smallest_circle_points(point_cloud, diameter):
    """
    Highlight the points used to create the smallest circle from the point cloud.

    Args:
        point_cloud (o3d.geometry.PointCloud): The input cylindrical point cloud.
        diameter (float): The diameter of the smallest circle.

    Returns:
        o3d.geometry.PointCloud: Point cloud with highlighted points.
        open3d.geometry.TriangleMesh: Circle mesh.
    """
    points = np.asarray(point_cloud.points)
    
    # Project points onto the XY plane
    xy_points = points[:, :2]
    
    # Calculate the distance of each point from the origin
    distances = np.linalg.norm(xy_points, axis=1)
    
    # Find the minimum distance (radius of the smallest circle)
    min_radius = diameter / 2
    
    # Find points that are within a small threshold of the minimum radius
    threshold = 0.01  # Adjust this threshold as needed
    circle_points_indices = np.where(np.abs(distances - min_radius) < threshold)[0]
    circle_points = points[circle_points_indices]
    
    # Create a point cloud for the circle points
    circle_points_pcd = o3d.geometry.PointCloud()
    circle_points_pcd.points = o3d.utility.Vector3dVector(circle_points)
    circle_points_pcd.paint_uniform_color([1, 0, 0])  # Red color for highlighted points
    
    # Create the circle mesh
    circle_mesh = create_circle_mesh(diameter)
    
    return circle_points_pcd, circle_mesh

def find_smallest_circle_diameter_general(point_cloud, min_distance=24, max_distance=27):
    """
    Find the diameter of the smallest circle in a cylindrical point cloud along the z-axis without constraining to a specific center point.

    Args:
        point_cloud (o3d.geometry.PointCloud): The input cylindrical point cloud.
        min_distance (float): The minimum distance from the z-axis to consider.
        max_distance (float): The maximum distance from the z-axis to consider.

    Returns:
        float: The diameter of the smallest circle.
    """
    points = np.asarray(point_cloud.points)
    
    # Filter points within the specified distance range from the z-axis
    distances_from_z = np.linalg.norm(points[:, :2], axis=1)
    filtered_points = points[(distances_from_z >= min_distance) & (distances_from_z <= max_distance)]
    
    # Project points onto the XY plane
    xy_points = filtered_points[:, :2]
    
    # Use RANSAC to fit a circle to the points
    def fit_circle(points):
        A = np.hstack([points, np.ones((points.shape[0], 1))])
        b = np.sum(points**2, axis=1)
        x = np.linalg.lstsq(A, b, rcond=None)[0]
        center = x[:2] / 2
        radius = np.sqrt(x[2] + np.sum(center**2))
        return center, radius

    best_radius = 30
    best_center = (0,0,0)
    num_iterations = 1000
    threshold = 1

    for _ in range(num_iterations):
        sample_indices = np.random.choice(xy_points.shape[0], 3, replace=False)
        sample_points = xy_points[sample_indices]
        try:
            center, radius = fit_circle(sample_points)
            distances = np.linalg.norm(xy_points - center, axis=1)
            inliers = np.abs(distances - radius) < threshold
            if np.sum(inliers) > 3 and radius < best_radius:
                best_radius = radius
                best_center = center
        except np.linalg.LinAlgError:
            continue
    
    min_diameter = 2 * best_radius if best_radius != float('inf') else None
    
    return min_diameter

def remove_points_in_hollow_cylinder(point_cloud, center, inner_radius, outer_radius, height):
    """
    Remove points within a specified hollow cylindrical region from the point cloud.

    Args:
        point_cloud (o3d.geometry.PointCloud): The input point cloud.
        center (tuple): The center of the base of the cylinder (x, y).
        inner_radius (float): The inner radius of the hollow cylinder.
        outer_radius (float): The outer radius of the hollow cylinder.
        height (float): The height of the cylinder (can be negative for subtraction in the negative z direction).

    Returns:
        o3d.geometry.PointCloud: The filtered point cloud with points inside the hollow cylinder removed.
    """
    points = np.asarray(point_cloud.points)
    
    # Calculate the distance of each point from the center of the cylinder base
    distances_from_center = np.linalg.norm(points[:, :2] - np.array(center), axis=1)
    
    # Determine the z-range based on the height
    if height >= 0:
        z_min, z_max = 0, height
    else:
        z_min, z_max = height, 0
    
    # Filter points that are within the hollow cylindrical region
    mask = ~((distances_from_center >= inner_radius) & (distances_from_center <= outer_radius) & (points[:, 2] >= z_min) & (points[:, 2] <= z_max))
    filtered_points = points[mask]
    
    # Create a new point cloud with the filtered points
    filtered_point_cloud = o3d.geometry.PointCloud()
    filtered_point_cloud.points = o3d.utility.Vector3dVector(filtered_points)
    
    return filtered_point_cloud

def find_optimal_scaling_factor(source, target, max_correspondence_distance, scaling_range=(0.95, 1.15), scaling_step=0.05):
    """
    Find the optimal scaling factor to align two point clouds.
    #TODO Test with full scan of scaling part.
    Args:
        source (o3d.geometry.PointCloud): The source point cloud.
        target (o3d.geometry.PointCloud): The target point cloud.
        max_correspondence_distance (float): The maximum correspondence distance for ICP.
        scaling_range (tuple): The range of scaling factors to test (min, max).
        scaling_step (float): The step size for scaling factors.

    Returns:
        float: The optimal scaling factor.
        float: The fitness score of the optimal scaling factor.
    """
    best_scaling_factor = 1.0
    best_fitness = 0.0
    print("Finding optimal scaling factor...")
    for scale in np.arange(scaling_range[0], scaling_range[1], scaling_step):
        # Apply scaling to a copy of the original target
        scaled_target = o3d.geometry.PointCloud(target)
        scaled_target.scale(scale, center=(0, 0, 0))
        icp_result = o3d.pipelines.registration.registration_icp(
            source, scaled_target, max_correspondence_distance,
            np.eye(4),
            o3d.pipelines.registration.TransformationEstimationPointToPoint()
        )
        o3d.visualization.draw_geometries([source, scaled_target])
        if icp_result.fitness > best_fitness:
            best_fitness = icp_result.fitness
            best_scaling_factor = scale

    return best_scaling_factor, best_fitness

def contains_non_greyscale_colors(point_cloud):
    """
    Detect if a point cloud contains colors outside greyscale/black and white.

    Args:
        point_cloud (o3d.geometry.PointCloud): The input point cloud.

    Returns:
        bool: True if the point cloud contains non-greyscale colors, False otherwise.
    """
    if not point_cloud.has_colors():
        return False

    colors = np.asarray(point_cloud.colors)
    avg_color = np.mean(colors, axis=0)
    if not np.allclose(avg_color[0], avg_color[1]) or not np.allclose(avg_color[1], avg_color[2]):
        print("Non-greyscale color detected:", avg_color)
        return True
    return False

def rename_files_in_folder(folder_path):
    """
    Rename all .json and .ply files in the specified folder by inserting "_20" after the {std} part of the file name.

    Args:
        folder_path (str): The path to the folder containing the files to rename.
    """
    for filename in os.listdir(folder_path):
        if filename.endswith(".json") or filename.endswith(".ply"):
            name, ext = os.path.splitext(filename)
            parts = name.split('_')
            if len(parts) >= 5 and filename.endswith(".json"):
                parts[3] += "_20"
            elif len(parts) >= 4 and filename.endswith(".ply"):
                parts[2] += "_20"
            new_name = '_'.join(parts) + ext
            os.rename(os.path.join(folder_path, filename), os.path.join(folder_path, new_name))
            print(f"Renamed: {filename} to {new_name}")

# Example usage:
# rename_files_in_folder("/path/to/folder")

if __name__ == "__main__":
    from Comparison import compare_point_clouds
    from Normal_space_downsampling import normal_space_sampling_with_bin_control
    from Calibration_by_fixture import remove_points_in_box
    import time
    arrows = [
    create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
    ]
    AxisArrow = o3d.geometry.TriangleMesh()
    for arrow in arrows:
        AxisArrow += arrow

    # rename_files_in_folder(r"scanner_interface\output\sort-fikstur-0.1-contrast-filter")
    

    pcd = o3d.io.read_point_cloud(r"scanner_interface\output\sort-fikstur-0.1-contrast-filter\scan_8.ply")

    pcd = remove_points_in_box(pcd, (-1000, -1000, -2000), (1000, 1000, 10))
    #time the function:
    # start = time.time()
    # contains_non_greyscale_colors(pcd)
    # end = time.time()
    # print(f"Time taken: {end - start} seconds")
    o3d.visualization.draw_geometries([pcd, AxisArrow], window_name="Scanned point cloud")
    #logger.debug("Starting voxel downsampling")
    #print("prior to downsampling len(pcd.points): ", len(pcd.points))
    #pcd = pcd.voxel_down_sample(0.5)
    #logger.info(f"Voxel downsampling completed, points count: {len(pcd.points)}")

    save_path = r"scanner_interface\output\sort-fikstur-0.1-contrast-filter\scan_8_noiseless.ply"
    o3d.io.write_point_cloud(save_path, pcd)

    brk
 #Test
  # Play with the resulting cloud:
    scanned_pointcloud = o3d.io.read_point_cloud(r"calibration\Smultring\scan_1.ply")
    Reference = o3d.io.read_point_cloud(r"calibration\CalibrationCylinder2.ply")
    scanned_pointcloud.translate((0,10,-290))
    scanned_pointcloud = inverse_radius_filter_point_cloud(scanned_pointcloud, 100)
    scanned_pointcloud = scanned_pointcloud.voxel_down_sample(voxel_size=0.1)
    print("Number of points in the point cloud: ", len(np.asarray(scanned_pointcloud.points)))
    scanned_pointcloud, ind = scanned_pointcloud.remove_statistical_outlier(nb_neighbors=35, std_ratio=0.3)
    
    

    #Visualize the pointcloud
    centroid=scanned_pointcloud.get_center()
    scanned_pointcloud.translate(-centroid)
    scanned_pointcloud.translate((8,0,0))
    centroid=Reference.get_center()
    Reference.translate(-centroid)
    Reference.rotate(o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(90), np.radians(90), np.radians(0))), center=(0,0,0))
    Reference.translate((0,0,-16))
    
    # Remove points within a specified hollow cylinder
    center = (0, 0)
    inner_radius = 28
    outer_radius = 47
    height = -100
    #Reference = remove_points_in_hollow_cylinder(Reference, center, inner_radius, outer_radius, height)
    Reference.paint_uniform_color((0,1,0))
    
    # Visualize the filtered point cloud
    # o3d.visualization.draw_geometries([AxisArrow, Reference], window_name="Filtered point cloud")
    
    scanned_pointcloud.translate((0,-1,-1))
    # eye = np.eye(4)
    # eye[4,4]=0.5

    # o3d.visualization.draw_geometries([scanned_pointcloud, AxisArrow, Reference], window_name="Scanned point cloud")
    
    scanned_pointcloud = remove_points_in_hollow_cylinder(scanned_pointcloud, center, inner_radius, outer_radius, height)
    #scanned_pointcloud.scale(0.9, center=(0,0,0))
    # normal_space_sampling_with_bin_control(scanned_pointcloud, num_samples=int(len(scanned_pointcloud.points)/12))
    best_fact, fitniss = find_optimal_scaling_factor(Reference, scanned_pointcloud, 1)
    print(f"Best scaling factor: {best_fact}")
    print(f"Best fitness: {fitniss}")
    o3d.visualization.draw_geometries([scanned_pointcloud, AxisArrow, Reference], window_name="Scanned point cloud")
    
    brk
    transform, scanned_pointcloud = Point_to_Point(Reference, scanned_pointcloud, 0.7)
    print(transform)
    #dia = find_smallest_circle_diameter_general(scanned_pointcloud)
    #print(f"Smallest circle diameter: {dia}")
    
    # Highlight the points and create the circle mesh
    # circle_points_pcd, circle_mesh = highlight_smallest_circle_points(scanned_pointcloud, dia)
    
    # Visualize the point cloud with highlighted points and the circle mesh
    # o3d.visualization.draw_geometries([scanned_pointcloud, AxisArrow, Reference, circle_points_pcd, circle_mesh], window_name="Scanned point cloud with Smallest Circle Points")

    o3d.visualization.draw_geometries([scanned_pointcloud, AxisArrow, Reference], window_name="ICP point cloud")
    brk
    compare_point_clouds(Reference, scanned_pointcloud)
    
    
    
    #
    dia = find_smallest_circle_diameter(scanned_pointcloud)
    print(f"Smallest circle diameter: {dia}")
    
    # Highlight the points and create the circle mesh
    circle_points_pcd, circle_mesh = highlight_smallest_circle_points(scanned_pointcloud, dia)
    
    # Visualize the point cloud with highlighted points and the circle mesh
    o3d.visualization.draw_geometries([scanned_pointcloud, AxisArrow, Reference, circle_points_pcd, circle_mesh], window_name="Scanned point cloud with Smallest Circle Points")
    brk
    Reference = o3d.io.read_point_cloud(r"calibration\CalibrationCylinder.ply")
    o3d.visualization.draw_geometries([test_cloud], window_name="Test Cloud")
    
    
    
    cl, ind = test_cloud.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
    statistical_filtered_pcd = test_cloud.select_by_index(ind)
    o3d.visualization.draw_geometries([cl], window_name="Statistical Outlier Removal")

    test_cloud = o3d.io.read_point_cloud(r"C:\Users\mikke\Desktop\40pct_15scans\40pct_15scans\scan_main.ply")
    # Show clusters using DBSCAN
    dbscan_filtered_pcd = show_clusters_dbscan(test_cloud, eps=1, min_points=5, min_cluster_size=10)
    o3d.visualization.draw_geometries([dbscan_filtered_pcd], window_name="DBSCAN Clusters")

    """
    x = 45
    y = 25
    z = 5
    #Fixed rotation:
    initial_rotation = o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(x), np.radians(y), np.radians(z)))
    translation_vector=(10,0,5)
    print(initial_rotation)

    #o3d.visualization.draw_geometries([combined_cloud, target_cloud], window_name="Translated Point Cloud")
    
    int_rot_4x4=np.eye(4)
    int_rot_4x4[:3, :3] = initial_rotation 
    translation_matrix = np.eye(4)
    translation_matrix[:3, 3] = translation_vector 
    initial_transformation=np.dot(translation_matrix, int_rot_4x4)  

    # Test the decompose_transformation function
    rotation_matrix, translation, roll, pitch, yaw = (decompose_transformation(initial_transformation))

    print(f"Rotation matrix:\n{rotation_matrix}")
    print(f"Translation vector: {translation}")
    print(f"Roll: {roll:.2f}°")
    print(f"Pitch: {pitch:.2f}°")
    print(f"Yaw: {yaw:.2f}°")
    """

