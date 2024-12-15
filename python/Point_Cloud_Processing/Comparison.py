import open3d as o3d
import numpy as np
import matplotlib.pyplot as plt
import multiprocessing
import json
import os
from Translatory_crutch import align_centroids
from Calibration_by_fixture import remove_points_in_box
from Misc_functions import remove_points_within_distance_of_pointcloud, create_arrow


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

def paint_point_cloud_by_log_distance(pcd, distances):
    log_distances = np.log1p(distances)  # Apply logarithmic scale
    normalized_log_distances = (log_distances - np.min(log_distances)) / (np.max(log_distances) - np.min(log_distances))

    # Use jet colormap for coloring the points
    colors = plt.cm.jet(normalized_log_distances)[:, :3]
    pcd.colors = o3d.utility.Vector3dVector(colors)

def plot_legend(distances):
    min_dist = np.min(distances)
    max_dist = np.max(distances)

    fig, ax = plt.subplots(figsize=(7.5, 1.5))  # Adjust the height here
    fig.subplots_adjust(bottom=0.7)

    cmap = plt.cm.jet
    norm = plt.Normalize(vmin=min_dist, vmax=max_dist)
    cbar = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=ax, orientation='horizontal')
    cbar.set_label('Distance to Design Point Cloud [mm]', fontsize=14)  # Increase text size
    cbar.ax.tick_params(labelsize=14)  # Make the numbers on the colorbar the same size

    plt.show()

def plot_log_legend(distances):
    min_dist = np.min(distances)
    max_dist = np.max(distances)
    log_distances = np.log1p(distances)  # Apply logarithmic scale

    fig, ax = plt.subplots(figsize=(7.5, 1.5))  # Adjust the height here
    fig.subplots_adjust(bottom=0.7)

    cmap = plt.cm.jet
    norm = plt.Normalize(vmin=np.min(log_distances), vmax=np.max(log_distances))
    cbar = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=ax, orientation='horizontal')
    cbar.set_label('Distance to Design Point Cloud [mm]', fontsize=14, labelpad=4)  # Increase text size and add padding
    cbar.ax.tick_params(labelsize=14, rotation=90)  # Make the numbers on the colorbar the same size and tilt them 90 degrees back

    # Set logarithmic ticks with specified density
    tick_locs = np.log1p(np.concatenate([
        np.linspace(0, 1, num=5, endpoint=False),
        np.arange(1, 11, 1)
    ]))
    if np.log1p(19.99) <= np.log1p(max_dist):
        tick_locs = np.append(tick_locs, np.log1p(19.99))
    tick_locs = tick_locs[tick_locs <= np.log1p(max_dist)]  # Ensure ticks do not extend beyond max distance
    cbar.set_ticks(tick_locs)
    cbar.set_ticklabels([f"{np.expm1(tick):.1f}" for tick in tick_locs])

    plt.show()

def set_camera_view(vis, intrinsic):
    parameters = o3d.io.read_pinhole_camera_parameters("calibration\Orientation.json")
    ctr = vis.get_view_control()
    ctr.convert_from_pinhole_camera_parameters(parameters)

def compare_point_clouds(design_pc, scanned_pc):

    print("Computing distances between the point clouds...")
    distances = compute_cloud_to_cloud_distance(design_pc, scanned_pc)

    print("Painting scanned point cloud based on distances as a heatmap...")
    paint_point_cloud_by_distance(scanned_pc, distances)


    # Start multiprocessing for both Open3D visualization and the legend plot
    p1 = multiprocessing.Process(target=plot_legend, args=(distances,))
    p1.start()

    # Visualize with interactive point picking
    parameters = o3d.io.read_pinhole_camera_parameters("calibration\Orientation.json")
    intrinsic = parameters.intrinsic
    vis = o3d.visualization.VisualizerWithEditing()
    vis.create_window(window_name="Point Cloud Comparison with Distance Heatmap", width=intrinsic.width, height=intrinsic.height)
    vis.add_geometry(scanned_pc)
    
    # Set the camera view
    # set_camera_view(vis, intrinsic)

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

def compare_point_clouds_log(design_pc, scanned_pc):
    # Get the enlarged bounding box
    enlarged_bbox = get_enlarged_bounding_box(design_pc)

    # Crop the scanned point cloud to the enlarged bounding box
    scanned_pc = scanned_pc.crop(enlarged_bbox)

    print("Computing distances between the point clouds...")
    distances = compute_cloud_to_cloud_distance(design_pc, scanned_pc)

    print("Painting scanned point cloud based on log distances as a heatmap...")
    paint_point_cloud_by_log_distance(scanned_pc, distances)

    # Start multiprocessing for both Open3D visualization and the legend plot
    p1 = multiprocessing.Process(target=plot_log_legend, args=(distances,))
    p1.start()

    # Visualize with interactive point picking
    parameters = o3d.io.read_pinhole_camera_parameters("calibration\Orientation.json")
    intrinsic = parameters.intrinsic
    vis = o3d.visualization.VisualizerWithEditing()
    vis.create_window(window_name="Point Cloud Comparison with Log Distance Heatmap", width=intrinsic.width, height=intrinsic.height)
    vis.add_geometry(scanned_pc)
    
    # Set the camera view
    # set_camera_view(vis, intrinsic)

    # Run the visualizer to allow point picking
    vis.run()
    vis.destroy_window()

    # Get picked points
    picked_points = vis.get_picked_points()

    if len(picked_points) < 6:
        print("Not enough points were picked. Please select at least 6 points.")
    else:
        point1 = np.asarray(scanned_pc.points)[picked_points[0]]
        for i in range(1, 4):
            point = np.asarray(scanned_pc.points)[picked_points[i]]
            distance = np.linalg.norm(point1 - point)
            print(f"Distance between point 1 and point {i + 1}: {distance:.2f} mm")
        
        point5 = np.asarray(scanned_pc.points)[picked_points[4]]
        point6 = np.asarray(scanned_pc.points)[picked_points[5]]
        distance = np.linalg.norm(point5 - point6)
        print(f"Distance between point 5 and point 6: {distance:.2f} mm")

    p1.join()

def compare_point_clouds_bounding_box(design_pc, scanned_pc):
    # Get the enlarged bounding box
    enlarged_bbox = get_enlarged_bounding_box(design_pc)

    # Crop the scanned point cloud to the enlarged bounding box
    scanned_pc = scanned_pc.crop(enlarged_bbox)

    print("Computing distances between the point clouds...")
    distances = compute_cloud_to_cloud_distance(design_pc, scanned_pc)

    print("Painting scanned point cloud based on distances as a heatmap...")
    paint_point_cloud_by_distance(scanned_pc, distances)

    # Start multiprocessing for both Open3D visualization and the legend plot
    p1 = multiprocessing.Process(target=plot_legend, args=(distances,))
    p1.start()

    # Visualize with interactive point picking
    parameters = o3d.io.read_pinhole_camera_parameters("calibration\Orientation.json")
    intrinsic = parameters.intrinsic
    vis = o3d.visualization.VisualizerWithEditing()
    vis.create_window(window_name="Point Cloud Comparison with Distance Heatmap", width=intrinsic.width, height=intrinsic.height)
    vis.add_geometry(scanned_pc)
    
    # Set the camera view
    # set_camera_view(vis, intrinsic)

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
    for folder_num in range(12, num_folders + 1):
        folder_path = os.path.join(base_path, str(folder_num))
        scan_path = os.path.join(folder_path, "scan_1.ply")

        # Load point cloud
        pcd = load_point_cloud(scan_path)
        print("Loaded ply from " + str(scan_path))

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
        pcd = remove_points_in_box(pcd, min_bound, max_bound)

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
def compute_distance(point_cloud, index1, index2):
    """
    Compute the distance between two points in a point cloud given their indices.

    Parameters:
    - point_cloud: The point cloud containing the points.
    - index1: The index of the first point.
    - index2: The index of the second point.

    Returns:
    - distance: The Euclidean distance between the two points.
    """
    point1 = np.asarray(point_cloud.points[index1])
    point2 = np.asarray(point_cloud.points[index2])
    distance = np.linalg.norm(point1 - point2)
    return distance

def get_enlarged_bounding_box(pcd, enlargement=20):
    bbox = pcd.get_axis_aligned_bounding_box()
    min_bound = bbox.min_bound - enlargement
    max_bound = bbox.max_bound + enlargement
    enlarged_bbox = o3d.geometry.AxisAlignedBoundingBox(min_bound, max_bound)
    return enlarged_bbox

if __name__ == "__main__":
    # Enable multiprocessing on Windows
    multiprocessing.set_start_method('spawn', force=True)

    stl_file = r"calibration\CalibrationCylinder.ply"
    scanned_pc_path1 = r"scanner_interface\output\hvidt-fikstur-0.5-contrast-filter\scan_1.ply"  # Replace with your scanned point cloud path
    # compare_point_clouds(load_point_cloud(stl_file), load_point_cloud(scanned_pc_path1))
    dist =  compute_distance(load_point_cloud(scanned_pc_path1), 69769, 71494)
    print(dist)

    """"
    [Open3D INFO] Picked point #700115 (-25., 44., 3.6e+02) to add in queue.
    [Open3D INFO] No point has been picked.
    [Open3D INFO] No point has been picked.
    [Open3D INFO] Picked point #68763 (-25., -56., 3.6e+02) to add in queue.
    """ 
    
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

    # Save the camera parameters to a JSON file
    camera_params = {
        "class_name": "PinholeCameraParameters",
        "extrinsic": [
            -0.5317827803127757, 0.46781625108626318, -0.70594265332419792, 0.0,
            0.089816055488240371, -0.79772416909884658, -0.59629625708374878, 0.0,
            -0.84210459608017085, -0.38050506600457934, 0.38219856620021903, 0.0,
            84.752610037172346, -101.31738821983899, 312.88177547609172, 1.0
        ],
        "intrinsic": {
            "height": 754,
            "intrinsic_matrix": [
                652.9831544534668, 0.0, 0.0,
                0.0, 652.9831544534668, 0.0,
                331.5, 376.5, 1.0
            ],
            "width": 664
        },
        "version_major": 1,
        "version_minor": 0
    }
    with open("camera_params.json", "w") as f:
        json.dump(camera_params, f)

    # ...existing code...

