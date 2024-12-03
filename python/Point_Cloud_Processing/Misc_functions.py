import open3d as o3d
import numpy as np

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

    # Beregn Euler-vinkler fra rotationsmatrixen (roll, pitch, yaw)
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

    return {
        "translation": tuple(translation),
        "rotation": (roll, pitch, yaw),
    }

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


if __name__ == "__main__":
    steps, true_angle= compute_nearest_degree(15)
    print(f"number of steps to reach 15 degrees: {steps}")
    print(f"true angle: {true_angle}")