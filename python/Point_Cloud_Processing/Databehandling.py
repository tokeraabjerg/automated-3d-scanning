import open3d as o3d
import numpy as np
import json
import os
import pandas as pd  # Add pandas import
import time
import matplotlib.pyplot as plt  # Add matplotlib import

from Comparison import compare_point_clouds, compare_point_clouds_bounding_box, compare_point_clouds_log
from ICP import Point_to_Plane, legacy_icp_with_logging
from Misc_functions import remove_points_within_distance_of_pointcloud
from Calibration_by_fixture import remove_points_in_box

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

import open3d as o3d
import numpy as np

def loop_compute_cloud_to_cloud_distance_with_bins(pcd_tree, pcd2, max_distance=1.0, bin_size=0.05):
    """
    Compute cloud-to-cloud distance, identify outliers, and bin the distances.
    
    Args:
        pcd_tree (o3d.geometry.KDTreeFlann): KDTree of the reference point cloud.
        pcd2 (o3d.geometry.PointCloud): The point cloud to compare.
        max_distance (float): The maximum distance beyond which a point is considered an outlier.
        bin_size (float): The size of each bin for distance intervals.
    
    Returns:
        np.ndarray: Distances between corresponding points.
        list: Indices of outlier points.
        dict: Binned distance counts.
    """
    print("Computing Cloud-to-Cloud distance...")
    distances = []
    outlier_indices = []
    time_start = time.time()
    for i, point in enumerate(pcd2.points):
        [_, idx, dist] = pcd_tree.search_knn_vector_3d(point, 1)
        distance = np.sqrt(dist[0])
        distances.append(distance)
        if distance > max_distance:
            outlier_indices.append(i)
    time_elapsed = time.time() - time_start
    print(f"Time elapsed for finding distances: {time_elapsed:.2f} seconds")
    distances = np.array(distances)
    
    time_start = time.time()
    # Bin the distances
    max_bin = int(np.ceil(np.max(distances) / bin_size))
    bins = np.arange(0, (max_bin + 1) * bin_size, bin_size)
    binned_counts, _ = np.histogram(distances, bins=bins)
    
    # Create a dictionary to store the bin counts
    bin_counts = {f"{bins[i]:.2f}-{bins[i+1]:.2f}": int(binned_counts[i]) for i in range(len(binned_counts))}

    print(f"Mean Distance: {np.mean(distances):.6f}")
    print(f"Max Distance: {np.max(distances):.6f}")
    print(f"Min Distance: {np.min(distances):.6f}")
    print(f"Standard Deviation: {np.std(distances):.6f}")
    print(f"25th Percentile: {np.percentile(distances, 25)::.6f}")
    print(f"50th Percentile (Median): {np.percentile(distances, 50)::.6f}")
    print(f"75th Percentile: {np.percentile(distances, 75)::.6f}")
    #print("Distance Bins and Counts:")
    #for bin_range, count in bin_counts.items():
    #    print(f"{bin_range}: {count}")
    time_elapsed = time.time() - time_start
    print(f"Time elapsed for binning distances: {time_elapsed:.2f} seconds")

    return distances, outlier_indices, bin_counts

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
    print(f"Min Distance: {np.min(distances)::.6f}")
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
    distances, outlier_indices, bin_counts = loop_compute_cloud_to_cloud_distance_with_bins(pcd_tree, scanned_pc)
    return distances, outlier_indices, bin_counts

def process_ply_files(folder_path, design_pc, pcd_tree_design):
    cloud_results = []
    bin_data = {}  # Dictionary to store bin data for each point cloud
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.ply') and file_name.count('_') >= 5:
            # Start time:
            start_time = time.time()
            file_path = os.path.join(folder_path, file_name)
            print(f"Processing {file_path}...")
            scanned_pc = o3d.io.read_point_cloud(file_path)
            scanned_pc = remove_points_in_box(scanned_pc, (-100, -50, -50), (100, 50, 50))
            distances, outlier_indices, bin_counts = Auto_analyse(design_pc, scanned_pc, pcd_tree_design)
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
                "25th Percentile": np.percentile(distances, 25),
                "50th Percentile (Median)": np.percentile(distances, 50),
                "75th Percentile": np.percentile(distances, 75),
                "Total Points": total_points,
                "Number of Outliers": num_outliers,
                "Percentage of Outliers": percentage_outliers
            })
            bin_data[file_name] = bin_counts  # Store bin data
            time_elapsed = time.time() - start_time
            print(f"Time elapsed for ply-processing: {time_elapsed:.2f} seconds")
            del scanned_pc  # Remove from memory
    return cloud_results, bin_data

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
                    "25th Percentile": matching_cloud_result["25th Percentile"],
                    "50th Percentile (Median)": matching_cloud_result["50th Percentile (Median)"],
                    "75th Percentile": matching_cloud_result["75th Percentile"],
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

def extract_bin_data(json_file, file_name):
    """
    Extract bin data from a JSON file according to the specified file name.
    
    Args:
        json_file (str): Path to the JSON file.
        file_name (str): Name of the file to extract bin data for.
    
    Returns:
        dict: Extracted bin data.
    """
    with open(json_file, 'r') as f:
        bin_data = json.load(f)
    
    return bin_data.get(file_name, {})

def create_histogram(datasets, labels, title="Histogram of Distances from reference", group_size=4, max_value=None):
    """
    Create a histogram from multiple datasets with adjacent bars.
    
    Args:
        datasets (list of dict): List of bin data dictionaries to create the histogram from.
        labels (list of str): List of labels for each dataset.
        title (str): Title of the histogram.
        group_size (int): Number of bins to group together for readability.
        max_value (float): Maximum value for the range of the histogram.
    """
    grouped_bins = []
    grouped_counts_list = [[] for _ in datasets]
    
    for dataset in datasets:
        bins = list(dataset.keys())
        counts = list(dataset.values())
        
        # Filter bins and counts based on max_value
        if max_value is not None:
            filtered_bins = []
            filtered_counts = []
            for bin_label, count in zip(bins, counts):
                end_bin = float(bin_label.split('-')[1])
                if end_bin <= max_value:
                    filtered_bins.append(bin_label)
                    filtered_counts.append(count)
            bins = filtered_bins
            counts = filtered_counts
        
        # Group bins and counts
        grouped_counts = []
        for i in range(0, len(bins), group_size):
            start_bin = float(bins[i].split('-')[0])
            end_bin = float(bins[min(i + group_size - 1, len(bins) - 1)].split('-')[1])
            group_bin = f"{start_bin:.2f}-{end_bin:.2f}"
            group_count = sum(counts[i:i + group_size])
            if len(grouped_bins) <= i // group_size:
                grouped_bins.append(group_bin)
            grouped_counts.append(group_count)
        total_points = sum(grouped_counts)
        grouped_counts_list[datasets.index(dataset)] = [count / total_points * 100 for count in grouped_counts]
    
    bar_width = 0.8 / len(datasets)
    x = np.arange(len(grouped_bins))
    
    plt.figure(figsize=(9, 4))
    for i, (grouped_counts, label) in enumerate(zip(grouped_counts_list, labels)):
        plt.bar(x + i * bar_width, grouped_counts, width=bar_width, label=label, alpha=0.7)
    
    plt.xlabel('Distance from reference [mm]')
    plt.ylabel('Percentage of points [%]')
    plt.title(title)
    plt.xticks(x + bar_width * (len(datasets) - 1) / 2, grouped_bins, rotation=75, ha='right')
    plt.xlim(left=-0.5)  # Remove unused space before zero
    plt.legend()
    plt.tight_layout()
    plt.show()

def create_histogram_with_median(datasets, labels, medians, title="Histogram of Distances from reference", group_size=4, max_value=None):
    """
    Create a histogram from multiple datasets with adjacent bars and overlay upper quartile values.
    
    Args:
        datasets (list of dict): List of bin data dictionaries to create the histogram from.
        labels (list of str): List of labels for each dataset.
        medians (list of float): List of upper quartile values for each dataset.
        title (str): Title of the histogram.
        group_size (int): Number of bins to group together for readability.
        max_value (float): Maximum value for the range of the histogram.
    """
    grouped_bins = []
    grouped_counts_list = [[] for _ in datasets]

    for dataset in datasets:
        bins = list(dataset.keys())
        counts = list(dataset.values())
        
        # Filter bins and counts based on max_value
        if max_value is not None:
            filtered_bins = []
            filtered_counts = []
            for bin_label, count in zip(bins, counts):
                end_bin = float(bin_label.split('-')[1])
                if end_bin <= max_value:
                    filtered_bins.append(bin_label)
                    filtered_counts.append(count)
            bins = filtered_bins
            counts = filtered_counts
        
        # Group bins and counts
        grouped_counts = []
        for i in range(0, len(bins), group_size):
            start_bin = float(bins[i].split('-')[0])
            end_bin = float(bins[min(i + group_size - 1, len(bins) - 1)].split('-')[1])
            group_bin = f"{start_bin:.2f}-{end_bin:.2f}"
            group_count = sum(counts[i:i + group_size])
            if len(grouped_bins) <= i // group_size:
                grouped_bins.append(group_bin)
            grouped_counts.append(group_count)
        total_points = sum(grouped_counts)
        grouped_counts_list[datasets.index(dataset)] = [count / total_points * 100 for count in grouped_counts]
    
    bar_width = 0.8 / len(datasets)
    x = np.arange(len(grouped_bins))
    
    fig, ax = plt.subplots(figsize=(9, 4))
    for i, (grouped_counts, label) in enumerate(zip(grouped_counts_list, labels)):
        ax.bar(x + i * bar_width, grouped_counts, width=bar_width, label=label, alpha=0.7)
        ax.axvline(x=(medians[i] / (max_value if max_value else 1)) * len(grouped_bins), color=plt.cm.tab10(i), linestyle='--', label=f'{label} upper quartile')
    
    ax.set_xlabel('Distance from reference [mm]')
    ax.set_ylabel('Percentage of points [%]')
    ax.set_title(title)
    ax.set_xticks(x + bar_width * (len(datasets) - 1) / 2)
    ax.set_xticklabels(grouped_bins, rotation=75, ha='right')
    ax.set_xlim(left=-0.5)  # Remove unused space before zero
    ax.legend()
    
    # Add ticks at the upper quartile values at the bottom without labels
    median_positions = [(medians[i] / (max_value if max_value else 1)) * len(grouped_bins) for i in range(len(medians))]
    all_ticks = list(ax.get_xticks()) + median_positions
    all_labels = [label.get_text() for label in ax.get_xticklabels()] + [''] * len(median_positions)
    ax.set_xticks(all_ticks)
    ax.set_xticklabels(all_labels, rotation=75, ha='right')
    
    plt.tight_layout()
    plt.show()

def analyze_factorial_experiment(excel_files):
    """
    Analyze the factorial experiment data and present the effects of each variable on the upper quartile of distances.
    
    Args:
        excel_files (list of str): List of paths to the Excel files containing the data.
    """
    # Read data from Excel files
    data_frames = [pd.read_excel(file) for file in excel_files]
    combined_data = pd.concat(data_frames, ignore_index=True)
    
    # Calculate the upper quartile (75th percentile) of distances
    combined_data['Upper Quartile Distance'] = combined_data.groupby(['Dataset', 'Method', 'STD ratio', 'Outlier number of neighbors', 'Voxel size [mm]', 'Maximum Correspondence Distance [mm]'])['75th Percentile'].transform('max')
    
    # Analyze the effects of each variable
    factors = ['Dataset', 'Method', 'STD ratio', 'Outlier number of neighbors', 'Voxel size [mm]', 'Maximum Correspondence Distance [mm]']
    effects = combined_data.groupby(factors)['Upper Quartile Distance'].mean().reset_index()
    
    # Print the effects
    print("Effects of each variable on the upper quartile of distances:")
    print(effects)
    
    # Save the effects to an Excel file
    output_file = "Factorial_Experiment_Analysis.xlsx"
    effects.to_excel(output_file, index=False)
    print(f"Analysis results saved to {output_file}")

if __name__ == "__main__":
    """
    Start of point cloud analysis
    """

    # Paths to the Excel files containing the data
    # excel_files = [
    #     r"scanner_interface\output\sort-fikstur-0.5-contrast-filter\Analysis_sort-fikstur-0.5-contrast-filter-k.xlsx",
    #     r"scanner_interface\output\sort-fikstur-0.1-contrast-filter\Analysis_sort-fikstur-0.1-contrast-filter-k.xlsx",
    #     r"scanner_interface\output\hvidt-fikstur-0.5-contrast-filter\Analysis_hvidt-fikstur-0.5-contrast-filter-k.xlsx"
    # ]
    
    # Golden baby (Lowest outlier, lowest median dist): Black05	Standard	1	20	0,1	1
    # Best Early-outliers: Black05	Early-outliers-NSS	1	20	0,1	1
    # Best NSS: Black05	NSS	0,5	20	0,1	1

    # Worst black outliers: Black05	Standard	2	20	0,5	1
    # Worst outliers : White05	Early-outliers-NSS	0,5	20	0,1	1
    # Worst highnorm: Black05	Standard	1	200	0,1	2 (17)
    # Worst avgnorm: Black05	Early-outliers-NSS	0,5	200	0,1	1 (close follow up to highest norm, 16)
    # Example usage of extract_bin_data function
    design_pc = o3d.io.read_point_cloud(r"calibration\ProduceretEmne.ply")
    aligned_design = design_pc.rotate(o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(0), np.radians(90), np.radians(-90))), center=(0,0,0))
    aligned_design.translate((78, 49.5,-15))
    pcd_tree_design = o3d.geometry.KDTreeFlann(aligned_design)

    
    # read_path = r"scanner_interface\output\optimal_path\Bin_Data_optimal_path.json"

    Considered = o3d.io.read_point_cloud(r"scanner_interface\output\sort-fikstur-0.5-contrast-filter\Black05_Standard_1_20_0.1_1_1.ply")
    
    Considered = remove_points_in_box(Considered, (-100, -50, -50), (100, 50, 50))
    o3d.visualization.draw_geometries([Considered], window_name="Considered pcd") 
    print("number of points in considered: ", len(Considered.points))

    print("Running point to plane on pointclouds.")
    legacy_icp_with_logging(aligned_design, Considered, max_correspondence_distance=1)  
    print("Point to plane done.")
    # o3d.visualization.draw_geometries([Considered, aligned_design], window_name="Aligned Point Clouds")
    
    compare_point_clouds_log(aligned_design, Considered)
    compare_point_clouds_log(aligned_design, Considered)
    compare_point_clouds_log(aligned_design, Considered)
    compare_point_clouds_log(aligned_design, Considered)
    compare_point_clouds_log(aligned_design, Considered)
    br
    # compare_point_clouds(aligned_design, Considered)
    # Extract bin data   
    bin_data_file1 = r"scanner_interface\output\sort-fikstur-0.5-contrast-filter\Bin_Data_sort-fikstur-0.5-contrast-filter.json"
    example_bin_data1 = extract_bin_data(bin_data_file1, "Black05_Standard_0.5_20_0.1_1_1.ply")
    #example_bin_data2 = extract_bin_data(bin_data_file1, "Black05_Standard_1_20_0.5_1_1.ply")
    #example_bin_data3 = extract_bin_data(bin_data_file1, "Black05_Standard_2_20_0.1_1_1.ply")
    #example_bin_data4 = extract_bin_data(bin_data_file1, "Black05_Standard_1_20_0.1_1_1.ply")
    
    bin_data_file4 = r"scanner_interface\output\hvidt-fikstur-0.5-contrast-filter\Bin_Data_hvidt-fikstur-0.5-contrast-filter.json"
    bin_data_file3 = r"scanner_interface\output\sort-fikstur-0.1-contrast-filter\Bin_Data_sort-fikstur-0.1-contrast-filter.json"
    
    example_bin_data2 = extract_bin_data(bin_data_file3, "Black01_Standard_0.5_20_0.1_1_1.ply")
    example_bin_data3 = extract_bin_data(bin_data_file4, "White05_Standard_0.5_20_0.1_1_1.ply")
    # Create a histogram from the extracted bin data
    # create_histogram([example_bin_data1, example_bin_data2, example_bin_data4], labels=["No. 63","No. 135", "No. 209"], title="Histogram of Distances", group_size=1, max_value=1)
    Medians=[0.1759, 0.2617, 0.3589]
    create_histogram_with_median([example_bin_data1, example_bin_data2, example_bin_data3], medians=Medians, labels=["No. 47","No. 119","No. 193"], title="Histogram of Distances", group_size=1, max_value=1)  
    """

    folder_paths = [
        #r"scanner_interface\output\Legacy_Data\optimal_path"
        r"scanner_interface\output\hvidt-fikstur-0.5-contrast-filter",
        r"scanner_interface\output\sort-fikstur-0.5-contrast-filter",
        r"scanner_interface\output\sort-fikstur-0.1-contrast-filter"
    ]
    
    design_pc = o3d.io.read_point_cloud(r"calibration\ProduceretEmne.ply")
    aligned_design = design_pc.rotate(o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(0), np.radians(90), np.radians(-90))), center=(0,0,0))
    aligned_design.translate((78, 49.5,-15))
    pcd_tree_design = o3d.geometry.KDTreeFlann(aligned_design)
    
    
    for folder_path in folder_paths:
        folder_name = os.path.basename(folder_path)
        print(f"Processing folder: {folder_name}")
        cloud_results, bin_data = process_ply_files(folder_path, aligned_design, pcd_tree_design)

        # Save bin data to a JSON file in the same folder
        bin_data_file = os.path.join(folder_path, f"Bin_Data_{folder_name}.json")
        with open(bin_data_file, 'w') as f:
            json.dump(bin_data, f, indent=4)
        print(f"Bin data saved to {bin_data_file}")
        del bin_data

        icp_results = process_json_files(folder_path, cloud_results)

        # Convert ICP results to a DataFrame and save to Excel
        output_file = os.path.join(folder_path, f"Analysis_{folder_name}.xlsx")
        df_icp = pd.DataFrame(icp_results)
        df_icp.to_excel(output_file, index=False)
        print(f"ICP results saved to {output_file}")
        
    # Paths to the Excel files containing the data
    #excel_files = [
    #    "path/to/Black05.xlsx",
    #    "path/to/Black01.xlsx",
    #    "path/to/White05.xlsx"
    #]
    
    # Analyze the factorial experiment data
    # analyze_factorial_experiment(excel_files)

"""



"""


Right

{
	"class_name" : "ViewTrajectory",
	"interval" : 29,
	"is_loop" : false,
	"trajectory" : 
	[
		{
			"boundingbox_max" : [ 225.83528804175376, 85.505207516629582, 10.675470344153076 ],
			"boundingbox_min" : [ 71.862335053692789, -52.142223020386822, -35.273779486537649 ],
			"field_of_view" : 60.0,
			"front" : [ 0.21699136208035213, 0.65333451369806428, -0.72530597818674258 ],
			"lookat" : [ 157.88396388832166, 10.959090319413106, -18.676430782755098 ],
			"up" : [ 0.9761475488631931, -0.15064462937014231, 0.15633988131731485 ],
			"zoom" : 0.59999999999999987
		}
	],
	"version_major" : 1,
	"version_minor" : 0
}

Better top:

{
	"class_name" : "ViewTrajectory",
	"interval" : 29,
	"is_loop" : false,
	"trajectory" : 
	[
		{
			"boundingbox_max" : [ 226.37439811568606, 50.056631569660134, 0.48473162262281078 ],
			"boundingbox_min" : [ 76.563746780587365, -51.297736545098502, -44.94171530893891 ],
			"field_of_view" : 60.0,
			"front" : [ 0.9551803297632121, -0.018827678237537095, 0.29542521247453701 ],
			"lookat" : [ 151.18090046720064, 0.48532321334380324, -21.430145090429662 ],
			"up" : [ -0.29556794223323213, -0.005248746729289145, 0.95530730248532303 ],
			"zoom" : 0.80000000000000004
		}
	],
	"version_major" : 1,
	"version_minor" : 0
}


Bottom:

{
	"class_name" : "ViewTrajectory",
	"interval" : 29,
	"is_loop" : false,
	"trajectory" : 
	[
		{
			"boundingbox_max" : [ 225.83528804175376, 85.505207516629582, 10.675470344153076 ],
			"boundingbox_min" : [ 71.862335053692789, -52.142223020386822, -35.273779486537649 ],
			"field_of_view" : 60.0,
			"front" : [ -0.96902969194334976, -0.042265702941516284, -0.24330036269400873 ],
			"lookat" : [ 147.77456578292194, 3.3057715673568628, -16.291574188671948 ],
			"up" : [ 0.2435077424802119, 0.00024905820759657266, -0.9698989211882858 ],
			"zoom" : 0.69999999999999996
		}
	],
	"version_major" : 1,
	"version_minor" : 0
}





Top:

{
	"class_name" : "ViewTrajectory",
	"interval" : 29,
	"is_loop" : false,
	"trajectory" : 
	[
		{
			"boundingbox_max" : [ 225.83528804175376, 85.505207516629582, 10.675470344153076 ],
			"boundingbox_min" : [ 71.862335053692789, -52.142223020386822, -35.273779486537649 ],
			"field_of_view" : 60.0,
			"front" : [ 0.96920034879406514, 0.0029622827588357816, -0.24625577917750341 ],
			"lookat" : [ 149.74680784618866, -2.6122133895330539, -10.674983283083019 ],
			"up" : [ 0.24626550445715867, -0.0035521307812667424, 0.96919589541091999 ],
			"zoom" : 0.80000000000000004
		}
	],
	"version_major" : 1,
	"version_minor" : 0
}"""