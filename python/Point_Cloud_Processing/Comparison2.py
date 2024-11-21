import open3d as o3d
import numpy as np

def load_stl_as_point_cloud(stl_file):
    """
    Load an STL file and convert it to a point cloud.
    :param stl_file: Path to the STL file.
    :return: Point cloud object generated from the STL file.
    """
    mesh = o3d.io.read_triangle_mesh(stl_file)
    if mesh.is_empty():
        print(f"Failed to load mesh from {stl_file}")
        return None

    # Sample points on the mesh to create a point cloud
    pcd = mesh.sample_points_uniformly(number_of_points=100000)
    return pcd

def load_and_downsample_ply_point_cloud(ply_file, voxel_size):
    """
    Load a point cloud from a PLY file and downsample it using a voxel grid.
    :param ply_file: Path to the PLY file.
    :param voxel_size: Voxel size for downsampling.
    :return: Downsampled point cloud object.
    """
    pcd = o3d.io.read_point_cloud(ply_file)
    if pcd.is_empty():
        print(f"Failed to load point cloud from {ply_file}")
        return None

    print(f"Original point cloud has {len(pcd.points)} points.")
    print(f"Downsampling with voxel size: {voxel_size}...")
    downsampled_pcd = pcd.voxel_down_sample(voxel_size=voxel_size)
    print(f"Downsampled point cloud has {len(downsampled_pcd.points)} points.")
    return downsampled_pcd

def compute_cloud_to_cloud_distance(pcd1, pcd2):
    """
    Compute the Cloud-to-Cloud (C2C) distance between two point clouds.
    :param pcd1: The first point cloud.
    :param pcd2: The second point cloud.
    :return: Array of distances between each point in pcd1 and its nearest neighbor in pcd2.
    """
    # Use KDTree for efficient nearest neighbor search
    pcd_tree = o3d.geometry.KDTreeFlann(pcd2)
    distances = []

    for point in pcd1.points:
        [_, idx, dist] = pcd_tree.search_knn_vector_3d(point, 1)
        distances.append(np.sqrt(dist[0]))

    return np.array(distances)

def compare_point_clouds(stl_file, ply_file, voxel_size):
    """
    Compare a point cloud generated from an STL file with a point cloud from a PLY file.
    The PLY point cloud is downsampled using the specified voxel size.
    :param stl_file: Path to the STL file.
    :param ply_file: Path to the PLY file.
    :param voxel_size: Voxel size for downsampling the PLY file.
    """
    print("Loading point cloud from STL file...")
    stl_pcd = load_stl_as_point_cloud(stl_file)
    if stl_pcd is None:
        return

    print("Loading and downsampling point cloud from PLY file...")
    ply_pcd = load_and_downsample_ply_point_cloud(ply_file, voxel_size)
    if ply_pcd is None:
        return

    print("Computing Cloud-to-Cloud distance...")
    distances = compute_cloud_to_cloud_distance(stl_pcd, ply_pcd)

    # Analyze the distances
    print("Cloud-to-Cloud Distance Analysis:")
    print(f"Mean Distance: {np.mean(distances):.6f}")
    print(f"Max Distance: {np.max(distances):.6f}")
    print(f"Min Distance: {np.min(distances):.6f}")
    print(f"Standard Deviation: {np.std(distances):.6f}")

    # Visualize the two point clouds together
    print("Visualizing the point clouds...")
    stl_pcd.paint_uniform_color([1, 0, 0])  # Red
    ply_pcd.paint_uniform_color([0, 1, 0])  # Green
    o3d.visualization.draw_geometries([stl_pcd, ply_pcd], window_name="Point Cloud Comparison")

# Example usage
if __name__ == "__main__":
    # File paths
    stl_file = r"C:\Users\ovikd\Downloads\example_model.stl"
    ply_file = r"C:\Users\ovikd\Downloads\example_pointcloud.ply"
    voxel_size = 0.001  # Set the desired voxel size

    # Call the function to compare point clouds
    compare_point_clouds(stl_file, ply_file, voxel_size)
