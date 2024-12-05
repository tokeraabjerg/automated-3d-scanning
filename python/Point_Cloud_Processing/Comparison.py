import open3d as o3d
import numpy as np
import matplotlib.pyplot as plt
import multiprocessing
from Translatory_crutch import align_centroids

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

# TODO: Fjern denne funktion og opdater variabelnavn i compare_point_clouds
# TODO: når det ikke længere er relevant at downsample.
"""
def downsample_point_cloud(pcd, voxel_size):
    print(f"Downsampling point cloud with voxel size {voxel_size}...")
    downsampled_pcd = pcd.voxel_down_sample(voxel_size)
    print(f"Downsampled point cloud has {len(downsampled_pcd.points)} points.")
    return downsampled_pcd
"""
    
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

if __name__ == "__main__":
    # Enable multiprocessing on Windows
    multiprocessing.set_start_method('spawn', force=True)

    # File paths
    design_pc_path1 = r"C:\Users\ovikd\Documents\Punktskyer\DesignUdenTapPC_rotated.ply"  # Replace with your design point cloud path
    scanned_pc_path1 = r"C:\Users\ovikd\Documents\Punktskyer\ScannedMerged.ply"  # Replace with your scanned point cloud path

    # Voxel size for downsampling
    voxel_size = 0.5

    # Align the centroids of the point clouds
    pcd1, pcd2_translated = align_centroids(design_pc_path1, scanned_pc_path1)

    # Compare the point clouds and paint scanned PC based on distances
    compare_point_clouds(pcd1, pcd2_translated)
