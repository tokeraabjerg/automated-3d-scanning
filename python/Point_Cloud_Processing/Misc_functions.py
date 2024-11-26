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
