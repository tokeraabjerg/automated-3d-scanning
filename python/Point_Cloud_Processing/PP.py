import open3d as o3d
from Normal_space_downsampling import downsample_normal_space

    # Preproces: Downsize, Remove outliers, Find normals, Find features:
def preprocess_point_cloud(pcd, voxel_size):
    print(":: Downsample with a voxel size %.3f." % voxel_size)
    # Downsize...
    pcd_voxel = pcd.voxel_down_sample(voxel_size)
    
    # Remove Clusters
    # pcd_voxel=remove_small_clusters(pcd_voxel, int(10//voxel_size), 3*voxel_size)
    # Remove statistical outliers
    pcd_voxel, ind = pcd_voxel.remove_statistical_outlier(nb_neighbors=int(150//voxel_size), std_ratio=0.5)

    # Estimate normal
    radius_normal = voxel_size * 2
    print(":: Estimate normal with search radius %.3f." % radius_normal)
    pcd_voxel.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=30))
    
    # Downsample using normal space sampling
    pcd_normal = downsample_normal_space(pcd_voxel, num_samples=int(50000/voxel_size), voxel_size=voxel_size)

    return pcd_normal, pcd_voxel

#TENSOR SWITCH

import open3d as o3d
import numpy as np

def dbscan_tensor(pcd, eps, min_points):
    """
    DBSCAN clustering for a Tensor point cloud using Open3D KD-Tree.

    Args:
        pcd (open3d.t.geometry.PointCloud): Input tensor point cloud.
        eps (float): Distance to neighbors in a cluster.
        min_points (int): Minimum number of points to form a cluster.

    Returns:
        open3d.t.geometry.PointCloud: Filtered tensor point cloud.
    """
    # Extract points as tensor
    points = pcd.point.positions

    # Build KD-Tree using Open3D's Tensor API
    kdtree = o3d.t.geometry.KDTreeFlann(pcd)

    # Initialize cluster labels (-1 means noise)
    labels = np.full(points.shape[0], -1, dtype=int)
    cluster_id = 0

    for i in range(points.shape[0]):
        if labels[i] != -1:  # Skip already processed points
            continue

        # Find neighbors within `eps`
        indices, _ = kdtree.search_radius_vector_3d(points[i], eps)
        if len(indices) < min_points:
            continue  # Mark as noise

        # Expand cluster
        labels[indices] = cluster_id
        cluster_queue = list(indices)

        while cluster_queue:
            current = cluster_queue.pop()
            neighbors, _ = kdtree.search_radius_vector_3d(points[current], eps)
            if len(neighbors) >= min_points:
                for neighbor in neighbors:
                    if labels[neighbor] == -1:
                        labels[neighbor] = cluster_id
                        cluster_queue.append(neighbor)

        cluster_id += 1

    # Keep only the largest cluster
    largest_cluster_label = np.argmax(np.bincount(labels[labels >= 0]))
    mask = labels == largest_cluster_label
    filtered_points = points[mask]

    # Update the point cloud
    filtered_pcd = o3d.t.geometry.PointCloud()
    filtered_pcd.point.positions = o3d.core.Tensor(filtered_points, dtype=o3d.core.Dtype.Float32)
    return filtered_pcd



def t_preprocess_point_cloud(pcd, voxel_size):
    print(":: Downsample with a voxel size %.3f." % voxel_size)
    # Downsize...
    pcd_voxel = pcd.voxel_down_sample(voxel_size)
    
    # Remove outliers with custom dbscan
    # size = pcd_voxel.point["positions"].shape[0]
    pcd_voxel=dbscan_tensor(pcd_voxel, 2*voxel_size, 10*voxel_size)

    # Estimate normal
    radius_normal = voxel_size * 2
    print(":: Estimate normal with search radius %.3f." % radius_normal)
    pcd_voxel.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=30))

    # Find Features
    radius_feature = voxel_size * 5
    print(":: Compute FPFH feature with search radius %.3f." % radius_feature)
    pcd_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        pcd_voxel,
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_feature, max_nn=100))
    
    # Downsample using normal space sampling
    pcd_down = downsample_normal_space(pcd_voxel, num_samples=int(30000/voxel_size), voxel_size=voxel_size)

    return pcd_down, pcd_fpfh, pcd_voxel