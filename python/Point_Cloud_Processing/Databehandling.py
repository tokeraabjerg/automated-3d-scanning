import open3d as o3d
import numpy as np
import json
import os
import pandas as pd  # Add pandas import
import time

from Comparison import compare_point_clouds
from ICP import Point_to_Plane, legacy_icp_with_logging

def calculate_norms(icp_file):
    with open(icp_file, 'r') as f:
        data = json.load(f)
        icp_transformations = data["icp_transformations"]
        norms = [np.linalg.norm(np.array(transformation)) for transformation in icp_transformations]
        average_norm = np.mean(norms)
        highest_norm = np.max(norms)
        return average_norm, highest_norm

def extract_file_info(file_path):
    # Extract method, std, voxel_size, mcd from the file name
    base_name = os.path.basename(file_path)
    parts = base_name.split('_')
    if file_path.endswith('.json'):
        method = parts[2]
        std = float(parts[3])
        stdnn = float(parts[4])
        voxel_size = float(parts[5])
        mcd = float(parts[6])
    elif file_path.endswith('.ply'):
        method = parts[1]
        std = float(parts[2])
        stdnn = float(parts[3])
        voxel_size = float(parts[4])
        mcd = float(parts[5])
    else:
        raise ValueError("Unsupported file extension")
    return method, std, stdnn, voxel_size, mcd

def loop_compute_cloud_to_cloud_distance(pcd_tree, pcd2, max_distance=1.0):
    print("Computing Cloud-to-Cloud distance...")
    distances = []
    outlier_indices = []

    for i, point in enumerate(pcd2.points):
        [_, idx, dist] = pcd_tree.search_knn_vector_3d(point, 1)
        distance = np.sqrt(dist[0])
        distances.append(distance)
        if distance > max_distance:
            outlier_indices.append(i)

    distances = np.array(distances)
    print(f"Mean Distance: {np.mean(distances):.6f}")
    print(f"Max Distance: {np.max(distances):.6f}")
    print(f"Min Distance: {np.min(distances):.6f}")
    print(f"Standard Deviation: {np.std(distances):.6f}")
    return distances, outlier_indices

from Misc_functions import create_arrow

arrows = [
    create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
    ]
combined_geometry = o3d.geometry.TriangleMesh()
for arrow in arrows:
    combined_geometry += arrow

def Auto_analyse(aligned_design, scanned_pc, pcd_tree):
    print("Running point to plane on pointclouds.")
    legacy_icp_with_logging(aligned_design, scanned_pc, max_correspondence_distance=1)
    print("Point to plane done.")
    #o3d.visualization.draw_geometries([scanned_pc, aligned_design], window_name="Aligned Point Clouds")
    distances, outlier_indices = loop_compute_cloud_to_cloud_distance(pcd_tree, scanned_pc)
    
    return distances, outlier_indices

def process_ply_files(folder_path, design_pc, pcd_tree_design):
    cloud_results = []
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.ply') and file_name.count('_') >= 5:
            # Start time:
            start_time = time.time()
            file_path = os.path.join(folder_path, file_name)
            print(f"Processing {file_path}...")
            scanned_pc = o3d.io.read_point_cloud(file_path)
            distances, outlier_indices = Auto_analyse(design_pc, scanned_pc, pcd_tree_design)
            method, std, stdnn, voxel_size, mcd = extract_file_info(file_path)
            total_points = len(scanned_pc.points)
            num_outliers = len(outlier_indices)
            percentage_outliers = (num_outliers / total_points) * 100 if total_points > 0 else 0
            cloud_results.append({
                "Method": method, 
                "STD ratio": std, 
                "Outlier number of neighbors": stdnn, 
                "Voxel size [mm]": voxel_size, 
                "Maximum Correspondence Distance [mm]": mcd, 
                "Mean Distance": np.mean(distances), 
                "Max Distance": np.max(distances), 
                "Min Distance": np.min(distances), 
                "Standard Deviation": np.std(distances), 
                "Total Points": total_points,
                "Number of Outliers": num_outliers,
                "Percentage of Outliers": percentage_outliers
            })
            time_elapsed = time.time() - start_time
            print(f"Time elapsed for ply-processing: {time_elapsed:.2f} seconds")
            del scanned_pc  # Remove from memory
    return cloud_results

def process_json_files(folder_path, cloud_results):
    icp_results = []
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.json') and file_name.count('_') >= 5:
            file_path = os.path.join(folder_path, file_name)
            average_norm, highest_norm = calculate_norms(file_path)
            method, std, stdnn, voxel_size, mcd = extract_file_info(file_path)
            with open(file_path, 'r') as f:
                data = json.load(f)
                elapsed_timePCP = data["elapsed_timePCP"]
            
            matching_cloud_result = next((item for item in cloud_results if item["Method"] == method and item["STD ratio"] == std and item["Outlier number of neighbors"] == stdnn and item["Voxel size [mm]"] == voxel_size and item["Maximum Correspondence Distance [mm]"] == mcd), None)
            
            if matching_cloud_result:
                icp_result = {
                    "Method": method, 
                    "STD ratio": std, 
                    "Outlier number of neighbors": stdnn, 
                    "Voxel size [mm]": voxel_size, 
                    "Maximum Correspondence Distance [mm]": mcd, 
                    "average norm": average_norm, 
                    "highest norm": highest_norm, 
                    "PCP time [s]": elapsed_timePCP,
                    "Mean Distance": matching_cloud_result["Mean Distance"], 
                    "Max Distance": matching_cloud_result["Max Distance"], 
                    "Min Distance": matching_cloud_result["Min Distance"], 
                    "Standard Deviation": matching_cloud_result["Standard Deviation"], 
                    "Total Points": matching_cloud_result["Total Points"],
                    "Number of Outliers": matching_cloud_result["Number of Outliers"],
                    "Percentage of Outliers": matching_cloud_result["Percentage of Outliers"]
                }
            else:
                icp_result = {
                    "Method": method, 
                    "STD ratio": std, 
                    "Outlier number of neighbors": stdnn, 
                    "Voxel size [mm]": voxel_size, 
                    "Maximum Correspondence Distance [mm]": mcd, 
                    "average norm": average_norm, 
                    "highest norm": highest_norm, 
                    "PCP time [s]": elapsed_timePCP
                }
            
            icp_results.append(icp_result)
            del data  # Remove from memory
    return icp_results

if __name__ == "__main__":
    """
    Start of point cloud analysis
    """
    folder_paths = [
        r"scanner_interface\output\sort-fikstur-0.5-contrast-filter"
        #r"scanner_interface\output\hvidt-fikstur-0.5-contrast-filter",
        #r"scanner_interface\output\sort-fikstur-0.5-contrast-filter"
    ]
    
    design_pc = o3d.io.read_point_cloud(r"calibration\ProduceretEmne.ply")
    aligned_design = design_pc.rotate(o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(0), np.radians(90), np.radians(-90))), center=(0,0,0))
    aligned_design.translate((78, 49.5,-15))
    pcd_tree_design = o3d.geometry.KDTreeFlann(aligned_design)

    for folder_path in folder_paths:
        folder_name = os.path.basename(folder_path)
        print(f"Processing folder: {folder_name}")
        cloud_results = process_ply_files(folder_path, aligned_design, pcd_tree_design)

        # Print cloud_results for debugging
        # print("Cloud Results:")
        # for result in cloud_results:
        #     print(result)

        icp_results = process_json_files(folder_path, cloud_results)

        # Convert ICP results to a DataFrame and save to Excel
        output_file = f"Analysis_{folder_name}.xlsx"
        df_icp = pd.DataFrame(icp_results)
        df_icp.to_excel(output_file, index=False)
        print(f"ICP results saved to {output_file}")


