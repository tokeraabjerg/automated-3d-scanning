import open3d as o3d
import numpy as np

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
    labels = np.array(
        point_cloud.cluster_dbscan(eps, min_points=10, print_progress=True)
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

