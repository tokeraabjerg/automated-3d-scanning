import open3d as o3d
import numpy as np

def load_point_cloud(file_path):
    """
    Load a point cloud from a file.
    :param file_path: Path to the point cloud file.
    :return: Open3D point cloud object.
    """
    pcd = o3d.io.read_point_cloud(file_path)
    if pcd.is_empty():
        raise ValueError(f"Failed to load point cloud from {file_path}")
    print(f"Loaded point cloud '{file_path}' with {len(pcd.points)} points.")
    return pcd

def compute_centroid(file_path):
    """
    Compute the centroid of a point cloud.
    :param file_path: Path to the point cloud file.
    :return: Numpy array of the centroid coordinates.
    """
    #pcd = load_point_cloud(file_path)
    pcd = file_path
    points = np.asarray(pcd.points)
    centroid = points.mean(axis=0)
    print(f"Centroid of point cloud '{file_path}': {centroid}")
    return centroid

def align_centroids(design_file_path, scanned_file_path):
    """
    Align the centroids of two point clouds.
    :param file_path1: File path of the first point cloud (reference).
    :param file_path2: File path of the second point cloud (to be aligned).
    :return: Aligned point cloud (from file_path2) translated to match the centroid of file_path1.
    """

    designPC = design_file_path
    scannedPC = scanned_file_path
    
    centroid_design = compute_centroid(design_file_path)
    centroid_scanned = compute_centroid(scanned_file_path)
    print(f"Translation vector: {centroid_scanned - centroid_design}")

    # Translate the second point cloud to align centroids
    designPC_translated = designPC.translate(centroid_scanned - centroid_design)
    return designPC_translated, scannedPC

def visualize_aligned_point_clouds(file_path1, file_path2):
    """
    Visualize two point clouds after aligning their centroids.
    :param file_path1: File path of the first point cloud (reference).
    :param file_path2: File path of the second point cloud (to be aligned).
    """
    pcd1, pcd2_aligned = align_centroids(file_path1, file_path2)

    # Set colors for visualization
    pcd1.paint_uniform_color([1, 0, 0])  # Red for reference
    pcd2_aligned.paint_uniform_color([0, 1, 0])  # Green for aligned

    # Visualize
    o3d.visualization.draw_geometries([pcd1, pcd2_aligned], window_name="Aligned Point Clouds")

if __name__ == "__main__":
    # File paths for the two point clouds
    pc1_path = r"C:\Users\ovikd\Documents\Punktskyer\DesignUdenTapPC_rotated.ply"
    pc2_path = r"C:\Users\ovikd\Documents\Punktskyer\ScannedMerged.ply"

    # Visualize the aligned point clouds
    visualize_aligned_point_clouds(pc1_path, pc2_path)