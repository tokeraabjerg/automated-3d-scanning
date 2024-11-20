
import open3d as o3d
import numpy as np

def downsample_normal_space(point_cloud, num_samples, voxel_size):
    """
    Downsamples a point cloud using normal space sampling.
    
    Args:
        point_cloud (o3d.geometry.PointCloud): The input point cloud.
        num_samples (int): The number of points to sample.
    
    Returns:
        o3d.geometry.PointCloud: The downsampled point cloud.
    """
    # Compute normals for the point cloud
    point_cloud.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=2*voxel_size, max_nn=30))
    normals = np.asarray(point_cloud.normals)

    # Convert normals to spherical coordinates (theta, phi)
    theta = np.arccos(normals[:, 2])  # Angle from z-axis
    phi = np.arctan2(normals[:, 1], normals[:, 0])  # Angle in xy-plane

    # Bin normals into uniform bins in the normal space
    num_theta_bins = int(np.sqrt(num_samples))  # Divide angular space evenly
    num_phi_bins = int(np.sqrt(num_samples))
    theta_bins = np.linspace(0, np.pi, num_theta_bins + 1)
    phi_bins = np.linspace(-np.pi, np.pi, num_phi_bins + 1)

    # Map each normal to a bin
    bin_indices = np.vstack([
        np.digitize(theta, theta_bins) - 1,
        np.digitize(phi, phi_bins) - 1
    ]).T

    # Group points by bin and sample
    sampled_indices = []
    for theta_idx in range(num_theta_bins):
        for phi_idx in range(num_phi_bins):
            in_bin = np.where((bin_indices[:, 0] == theta_idx) & (bin_indices[:, 1] == phi_idx))[0]
            if len(in_bin) > 0:
                # Randomly sample one point from the bin
                sampled_indices.append(np.random.choice(in_bin))

    # Create the downsampled point cloud
    sampled_indices = np.array(sampled_indices[:num_samples])  # Ensure exact number of samples
    downsampled_cloud = point_cloud.select_by_index(sampled_indices)

    return downsampled_cloud

# Example Usage
if __name__ == "__main__":
    # Load a point cloud
    pcd = o3d.io.read_point_cloud("point_cloud.ply")

    # Downsample using normal space sampling
    downsampled_pcd = downsample_normal_space(pcd, num_samples=500)

    # Visualize the downsampled point cloud
    o3d.visualization.draw_geometries([downsampled_pcd], window_name="Downsampled Point Cloud")

    