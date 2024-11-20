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

