import open3d as o3d
import numpy as np
from Normal_space_downsampling import normal_space_sampling_with_bin_control, downsample_normal_space
from Misc_functions import sample_adjacent_point_pairs, create_arrow


    # Preproces: Downsize, Remove outliers, Find normals, Find features:
def preprocess_point_cloud(pcd, resolution, std_ratio):

    print(":: Voxel Downsample with a resolution %.3f." % resolution)
    pcd_voxel=pcd.voxel_down_sample(1/resolution)
    print(f"Voxelization resulted in {len(pcd_voxel.points)} points")
    # o3d.visualization.draw_geometries([pcd_voxel], window_name="Vox Cloud")
    
    # Remove statistical outliers
    
    print(":: Statistically remove outliers.")
    pcd_voxel, ind = pcd_voxel.remove_statistical_outlier(nb_neighbors=int(100*resolution), std_ratio=std_ratio, print_progress=True)
    #o3d.visualization.draw_geometries([pcd_voxel], window_name="vox Cloud")
    

    # Downsample using normal space sampling
    vox_meandist=sample_adjacent_point_pairs(pcd_voxel, 100, 1)
    # print(f"Mean distance between points: {meandist}")
    pcd_normal = downsample_normal_space(pcd_voxel, num_samples=int(len(pcd_voxel.points)/12), radius=2)
    #pcd_normal = downsample_normal_space_with_bin_control(pcd_voxel, radius=2, bin_size=360)
    # print(pcd_normal.has_normals()) True
    #o3d.visualization.draw_geometries([pcd_normal], window_name="Normal Cloud")
    return pcd_normal, pcd_voxel

"""
We shall develop a more robust preproccesing method.
Firstly, we shall consider different downsampling methods.

Then, we shall consider removing outliers.
Finally, we shall consider finding normals for the Point to Plane algorithm.
"""

def Preproces_normal_pipeline(pcd, voxel_size, std_ratio):

    print(":: Voxel Downsample with voxel size %.3f." % voxel_size)
    pcd_voxel=pcd.voxel_down_sample(voxel_size)
    print(f"Voxelization resulted in {len(pcd_voxel.points)} points")
    # o3d.visualization.draw_geometries([pcd_voxel], window_name="Vox Cloud")
    numb_samples = int(len(pcd_voxel.points)/12)
    pcd_normal = normal_space_sampling_with_bin_control(pcd_voxel, numb_samples, radius=3, max_nn=100, bin_size=360)

    # Remove statistical outliers
    print(":: Statistically remove outliers.")
    pcd_normal, ind = pcd_normal.remove_statistical_outlier(nb_neighbors=int(100//voxel_size), std_ratio=std_ratio, print_progress=False)
    #o3d.visualization.draw_geometries([pcd_voxel], window_name="vox Cloud")
    
    return pcd_normal

def Preproces_early_outliers_pipeline(pcd, voxel_size, std_ratio):

    """
    This method cannot accept as many points/low voxel size as the Preproces_normal_pipeline method.
    """
    
    print(":: Voxel Downsample with voxel size %.3f." % voxel_size)
    pcd_voxel=pcd.voxel_down_sample(voxel_size)
    print(f"Voxelization resulted in {len(pcd_voxel.points)} points")
    # o3d.visualization.draw_geometries([pcd_voxel], window_name="Vox Cloud")
    numb_samples = int(len(pcd_voxel.points)/12)
    # Remove statistical outliers
    print(":: Statistically remove outliers.")
    pcd_voxel, ind = pcd_voxel.remove_statistical_outlier(nb_neighbors=int(100//voxel_size), std_ratio=std_ratio, print_progress=True)

    pcd_normal = normal_space_sampling_with_bin_control(pcd_voxel, numb_samples, radius=3, max_nn=100, bin_size=360)

    #o3d.visualization.draw_geometries([pcd_voxel], window_name="vox Cloud")
    return pcd_normal, pcd_voxel


def assign_colors(labels):
    # Define a set of colors
    colors = [
        [1, 0, 0],  # Red
        [0, 1, 0],  # Green
        [0, 0, 1],  # Blue
        [1, 1, 0],  # Yellow
        [1, 0, 1],  # Magenta
        [0, 1, 1],  # Cyan
        [0.5, 0.5, 0.5],  # Gray
        [1, 0.5, 0],  # Orange
        [0.5, 0, 0.5],  # Purple
        [0, 0.5, 0.5]   # Teal
    ]
    max_label = labels.max()
    assigned_colors = np.zeros((labels.size, 3))
    for i in range(max_label + 1):
        assigned_colors[labels == i] = colors[i % len(colors)]
    return assigned_colors

import time

if __name__ == "__main__":
    # List of .ply files to process
    ply_files = [
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\0 grader test 2.ply",
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\15 grader test 2.ply",
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\45 grader test 2.ply"
    ]

    # Load the point cloud
    combined_cloud = o3d.io.read_point_cloud(ply_files[0])
    start_timeb = time.time()
    pcd = preprocess_point_cloud(combined_cloud, 8, 0.5)
    end_timeb = time.time()
    elapsed_timeb = end_timeb - start_timeb
    print(f"Time taken to preprocess: {elapsed_timeb:.2f} seconds")
    
    # Create the axis arrows
    arrows = [
        create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
        create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
        create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
    ]
    AxisArrow = o3d.geometry.TriangleMesh()
    for arrow in arrows:
        AxisArrow += arrow
    o3d.visualization.draw_geometries([combined_cloud, AxisArrow], window_name="Piss Clustering")
    
    meandist = sample_adjacent_point_pairs(combined_cloud, 10, 1)
    print(f"Mean distance between points: {meandist}")
    resolution = 1
    print(":: Voxel Downsample with a resolution %.3f." % resolution)
    pcd_rand = combined_cloud.voxel_down_sample(1)
    print(f"PCD rand has {len(pcd_rand.points)} points")
    # o3d.visualization.draw_geometries([pcd_voxel], window_name="Vox Cloud")

    # Remove DBSCAN outliers
    print(":: DBSCAN clustering.")
    labels = np.array(pcd_rand.cluster_dbscan(eps=2.4, min_points=20, print_progress=True))

    # Select the largest cluster
    max_label = labels.max()
    print(f"point cloud has {max_label + 1} clusters")
    colors = assign_colors(labels)
    pcd_rand.colors = o3d.utility.Vector3dVector(colors)

    # Visualize the result
    o3d.visualization.draw_geometries([pcd_rand], window_name="DBSCAN Clustering")

    # Optionally, select the largest cluster
    largest_cluster_indices = np.where(labels == np.argmax(np.bincount(labels[labels >= 0])))[0]
    largest_cluster = pcd_rand.select_by_index(largest_cluster_indices)

    # Visualize the largest cluster
    o3d.visualization.draw_geometries([largest_cluster], window_name="Largest Cluster")