
import open3d as o3d
import numpy as np
import json
import os
from Translatory_crutch import align_centroids
from Calibration_by_fixture import remove_points_in_box, inverse_center_and_filter_point_cloud
from Misc_functions import remove_points_within_distance_of_pointcloud

def load_point_cloud(file_path):
    pcd = o3d.io.read_point_cloud(file_path)
    if pcd.is_empty():
        print(f"Failed to load point cloud from {file_path}")
        return None
    print(f"Loaded point cloud with {len(pcd.points)} points.")
    return pcd

def apply_calibration(pcd, calibration_path):
    with open(calibration_path, 'r') as f:
        calibration_data = json.load(f)
    
    transformation_matrix = np.array(calibration_data['calibration_transformation'])
    pcd.transform(transformation_matrix)
    return pcd

def process_and_visualize_merged_point_clouds(merged_pcs, calibration_path, remove_outliers=False):
    for idx, pc_path in enumerate(merged_pcs):
        print(f"Processing point cloud {idx + 1}/{len(merged_pcs)}: {pc_path}")

        # Load point cloud
        pcd = load_point_cloud(pc_path)
        if pcd is None:
            continue

        # Apply calibration
        # pcd = apply_calibration(pcd, calibration_path)

        # Remove fixture and motor points
        min_bound_fixture = (-120.0, -200.0, -200)  # Replace with your box's minimum x, y, and z coordinates
        max_bound_fixture = (100, 200, 200)
        pcd = remove_points_in_box(pcd, min_bound_fixture, max_bound_fixture)

        pcd = inverse_center_and_filter_point_cloud(pcd, 300, 0.5)
        
        # Remove points within a certain distance of the fixture

        # min_bound_motor = (-1000.0, -2000.0, -10)  # Replace with your box's minimum x, y, and z coordinates
        # max_bound_motor = (1000, 2000, 10)
        # pcd = remove_points_in_box(pcd, min_bound_motor, max_bound_motor)

        # Optional: Perform statistical outlier removal
        if remove_outliers:
            cl, ind = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=1.0)
            outlier_count = len(pcd.points) - len(ind)
            print(f"Outliers removed: {outlier_count}")

            # Save the number of points removed to a JSON file
            json_path = os.path.join(os.path.dirname(pc_path), "outliers_removed.json")
            with open(json_path, 'w') as f:
                json.dump({"outliers_removed": outlier_count}, f)

            # Visualize the point cloud after outlier removal
            pcd = pcd.select_by_index(ind)

        # Visualize the processed point cloud
        o3d.visualization.draw_geometries([pcd], window_name=f"Processed Point Cloud - {os.path.basename(pc_path)}")

if __name__ == "__main__":
    # File paths
    merged_pcs = [
        r"path\to\merged_point_cloud1.ply",
        r"path\to\merged_point_cloud2.ply",
        # Add more paths as needed
    ]
    calibration_path = r"path\to\calibration.json"

    # Process and visualize merged point clouds
    process_and_visualize_merged_point_clouds(merged_pcs, calibration_path, remove_outliers=True)