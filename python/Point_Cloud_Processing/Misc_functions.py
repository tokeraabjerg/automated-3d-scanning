import open3d as o3d
import numpy as np

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
