import open3d as o3d
import numpy as np
import matplotlib.pyplot as plt
import multiprocessing
import json
import os
from Translatory_crutch import align_centroids
from Calibration_by_fixture import remove_points_in_box
from Misc_functions import remove_points_within_distance_of_pointcloud


#===========================================================================
#  *                                 INFO
#    Bruges til at sammenligne to punktskyer (scannet og fra design-STL)
#    Lige nu bliver den scannede sky downsamplet, men det er en relic fra
#    at den tolket rå punktskyer fra scanneren. Fjernes når dette ikke 
#    længere skal ske.
#
#    Hvis et punkt Shift-klikkes i visualiseringen vil dets koordinater og
#    afstand til nærmeste punkt i design-punktskyen printes i terminalen
#    når visualiseringsvinduet lukkes.
#
#    Matplotlib skal installeres med pip:
#    pip install matplotlib
#===========================================================================



def load_point_cloud(file_path):
    pcd = o3d.io.read_point_cloud(file_path)
    if pcd.is_empty():
        print(f"Failed to load point cloud from {file_path}")
        return None
    print(f"Loaded point cloud with {len(pcd.points)} points.")
    return pcd

    
def compute_cloud_to_cloud_distance(pcd1, pcd2):
    print("Computing Cloud-to-Cloud distance...")
    pcd_tree = o3d.geometry.KDTreeFlann(pcd1)
    distances = []

    for point in pcd2.points:
        [_, idx, dist] = pcd_tree.search_knn_vector_3d(point, 1)
        distances.append(np.sqrt(dist[0]))

    distances = np.array(distances)
    print(f"Mean Distance: {np.mean(distances):.6f}")
    print(f"Max Distance: {np.max(distances):.6f}")
    print(f"Min Distance: {np.min(distances):.6f}")
    print(f"Standard Deviation: {np.std(distances):.6f}")
    return distances

def paint_point_cloud_by_distance(pcd, distances):
    min_dist, max_dist = np.min(distances), np.max(distances)
    normalized_distances = (distances - min_dist) / (max_dist - min_dist)

    # Use jet colormap for coloring the points
    colors = plt.cm.jet(normalized_distances)[:, :3]
    pcd.colors = o3d.utility.Vector3dVector(colors)

def plot_legend(distances):
    min_dist = np.min(distances)
    max_dist = np.max(distances)

    fig, ax = plt.subplots(figsize=(8, 1))
    fig.subplots_adjust(bottom=0.4)

    cmap = plt.cm.jet
    norm = plt.Normalize(vmin=min_dist, vmax=max_dist)
    cbar = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=ax, orientation='horizontal')
    cbar.set_label('Distance to Design Point Cloud')

    plt.show()

def compare_point_clouds(design_pc, scanned_pc):

    print("Computing distances between the point clouds...")
    distances = compute_cloud_to_cloud_distance(design_pc, scanned_pc)

    print("Painting scanned point cloud based on distances as a heatmap...")
    paint_point_cloud_by_distance(scanned_pc, distances)

    # Start multiprocessing for both Open3D visualization and the legend plot
    p1 = multiprocessing.Process(target=plot_legend, args=(distances,))
    p1.start()

    # Visualize with interactive point picking
    vis = o3d.visualization.VisualizerWithEditing()
    vis.create_window(window_name="Point Cloud Comparison with Distance Heatmap")
    #vis.add_geometry(design_pc)
    vis.add_geometry(scanned_pc)


    # Run the visualizer to allow point picking
    vis.run()
    vis.destroy_window()

    # Get picked points
    picked_points = vis.get_picked_points()
    if picked_points:
        print("Picked Points (Scanned Point Cloud):")
        for idx in picked_points:
            if idx < len(scanned_pc.points):
                coord = np.asarray(scanned_pc.points)[idx]
                distance = distances[idx]
                print(f"Point Index: {idx}, Coordinates: {coord}, Distance to Design: {distance:.6f}")
    else:
        print("No points were picked.")

    p1.join()

def apply_calibration(pcd, calibration_path):
    with open(calibration_path, 'r') as f:
        calibration_data = json.load(f)
    
    transformation_matrix = np.array(calibration_data['calibration_transformation'])
    
    pcd.transform(transformation_matrix)
    
    return pcd

def process_and_visualize_ply_files(base_path, num_folders, Fikstur):
    # Ændre det første tal i range for at bestemme startpunkt.
    for folder_num in range(1, num_folders + 1):
        folder_path = os.path.join(base_path, str(folder_num))
        scan_path = os.path.join(folder_path, "scan_1.ply")

        # Load point cloud
        pcd = load_point_cloud(scan_path)
        if pcd is None:
            print("Missing pcd, Continuing to next folder...")
            continue
        min_bound = (-1000.0, -2000.0, -10)  # Replace with your box's minimum x, y, and z coordinates
        max_bound = (1000, 2000, 10) 
        pcd = remove_points_in_box(pcd, min_bound, max_bound)

        # Apply calibration
        calibration_path = r"calibration\calibration.json"
        pcd = apply_calibration(pcd, calibration_path)

        min_bound = (-120.0, -200.0, -200)  # Replace with your box's minimum x, y, and z coordinates
        max_bound = (100, 200, 200) 
        #pcd = remove_points_in_box(pcd, min_bound, max_bound)

        #pcd = remove_points_within_distance_of_pointcloud(pcd, Fikstur, 2)

        # Initial visualization
        o3d.visualization.draw_geometries([pcd], window_name=f"Initial Point Cloud - Folder {folder_num}")


        # Perform statistical outlier removal
        cl, ind = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=1.0)
        outlier_count = len(pcd.points) - len(ind)
        print("Outliers removed: " + str(outlier_count))

        # Save the number of points removed to a JSON file
        json_path = os.path.join(folder_path, "outliers_removed.json")
        with open(json_path, 'w') as f:
            json.dump({"outliers_removed": outlier_count}, f)

        # Visualize the point cloud after outlier removal
        inlier_cloud = pcd.select_by_index(ind)
        o3d.visualization.draw_geometries([inlier_cloud], window_name=f"Filtered Point Cloud - Folder {folder_num}")

if __name__ == "__main__":
    # Enable multiprocessing on Windows
    multiprocessing.set_start_method('spawn', force=True)

    # File paths
    base_path = r"scanner_interface\output\Parameter_test"
    num_folders = 24
    
    Fikstur = o3d.io.read_point_cloud(r"calibration\ref.ply")
    Fikstur.rotate(o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(90), np.radians(90), np.radians(0))), center=(0,0,0))
    Fikstur.translate((0,-100,-15))
    tilt_vec=(32.77, 0, 0)
    Fikstur.translate(tilt_vec)
    # Process and visualize .ply files
    process_and_visualize_ply_files(base_path, num_folders, Fikstur)
    
    
    #* Ikke længere superrelevant. CompleteComparison er bedre.
    #* Lader det alligevel ligge for sikkerheds skyld.
    # Example usage til Comparison.py
    # # File paths
    # design_pc_path1 = r"C:\Users\ovikd\Documents\Punktskyer\DesignUdenTapPC_rotated.ply"  # Replace with your design point cloud path
    # scanned_pc_path1 = r"C:\Users\ovikd\Documents\Punktskyer\ScannedMerged.ply"  # Replace with your scanned point cloud path

    # # Align the centroids of the point clouds
    # pcd1, pcd2_translated = align_centroids(design_pc_path1, scanned_pc_path1)

    # # Compare the point clouds and paint scanned PC based on distances
    # compare_point_clouds(pcd1, pcd2_translated)

