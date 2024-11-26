import open3d as o3d
import numpy as np

def load_point_cloud(file_path):
    """
    Load a point cloud from a file.
    :param file_path: Path to the point cloud file.
    :return: Loaded Open3D point cloud object.
    """
    pcd = o3d.io.read_point_cloud(file_path)
    if pcd.is_empty():
        print(f"Failed to load point cloud from {file_path}")
        return None
    print(f"Loaded point cloud with {len(pcd.points)} points.")
    return pcd

def downsample_point_cloud(pcd, voxel_size):
    """
    Downsample a point cloud using voxel grid filtering.
    :param pcd: The Open3D point cloud object.
    :param voxel_size: Voxel size for downsampling.
    :return: Downsampled point cloud object.
    """
    print(f"Downsampling point cloud with voxel size {voxel_size}...")
    downsampled_pcd = pcd.voxel_down_sample(voxel_size)
    print(f"Downsampled point cloud has {len(downsampled_pcd.points)} points.")
    return downsampled_pcd

def compute_cloud_to_cloud_distance(pcd1, pcd2):
    """
    Compute the Cloud-to-Cloud (C2C) distance between two point clouds.
    :param pcd1: The first point cloud.
    :param pcd2: The second point cloud.
    :return: Array of distances between each point in pcd1 and its nearest neighbor in pcd2.
    """
    print("Computing Cloud-to-Cloud distance...")
    pcd_tree = o3d.geometry.KDTreeFlann(pcd2)
    distances = []

    for point in pcd1.points:
        [_, idx, dist] = pcd_tree.search_knn_vector_3d(point, 1)
        distances.append(np.sqrt(dist[0]))

    distances = np.array(distances)
    print(f"Mean Distance: {np.mean(distances):.6f}")
    print(f"Max Distance: {np.max(distances):.6f}")
    print(f"Min Distance: {np.min(distances):.6f}")
    print(f"Standard Deviation: {np.std(distances):.6f}")
    return distances

def compare_point_clouds(design_pc_path, scanned_pc_path, voxel_size):
    """
    Compare two point clouds by downsampling the scanned point cloud and computing distances.
    :param design_pc_path: Path to the design point cloud.
    :param scanned_pc_path: Path to the scanned point cloud.
    :param voxel_size: Voxel size for downsampling the scanned point cloud.
    """
    print("Loading design point cloud...")
    design_pc = load_point_cloud(design_pc_path)
    if design_pc is None:
        return

    print("Loading scanned point cloud...")
    scanned_pc = load_point_cloud(scanned_pc_path)
    if scanned_pc is None:
        return

    print("Downsampling scanned point cloud...")
    scanned_pc_downsampled = downsample_point_cloud(scanned_pc, voxel_size)

    print("Comparing the point clouds...")
    distances = compute_cloud_to_cloud_distance(design_pc, scanned_pc_downsampled)

    print("Visualizing the point clouds...")
    design_pc.paint_uniform_color([1, 0, 0])  # Design PC in red
    scanned_pc_downsampled.paint_uniform_color([0, 1, 0])  # Scanned PC in green
    o3d.visualization.draw_geometries([design_pc, scanned_pc_downsampled], window_name="Point Cloud Comparison")

# File paths
design_pc_path = r"C:\Users\ovikd\Downloads\DesignPC_rotated.ply"  # Replace with your design point cloud path
scanned_pc_path = r"C:\Users\ovikd\Downloads\ScannedCroppedPC0.ply"  # Replace with your scanned point cloud path

# Voxel size for downsampling
voxel_size = 0.5

# Compare the point clouds
compare_point_clouds(design_pc_path, scanned_pc_path, voxel_size)
