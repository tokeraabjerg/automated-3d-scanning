import sys
import os
import open3d as o3d
from ICP import Point_to_Plane
import numpy as np


# Dynamically add the parent of the current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)

from Diverse_scripts.STLtoPC import stl_to_point_cloud
from Comparison import compare_point_clouds
from Translatory_crutch import align_centroids



def complete_comparison(design_STL, scanned_pc):

    # Constants
    num_points = 10000

    print("Initializing STL to point cloud conversion.")
    design_pointcloud = stl_to_point_cloud(design_STL,0,num_points)
    print("STL converted to point cloud.")
    
    print("Aligning centroids of point clouds.")
    pcd1, pcd2 = align_centroids(design_pointcloud,scanned_pc)

    o3d.visualization.draw_geometries([pcd1,pcd2],window_name="Aligned by centroids")
    pcd1.rotate(o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(0), np.radians(90), np.radians(-90))))
    o3d.visualization.draw_geometries([pcd1,pcd2],window_name="Rotated manually")
    print("Running ICP on pointclouds.")
    Point_to_Plane(pcd1, pcd2, mcd=4)

    print("Visualizing aligned point clouds.")
    o3d.visualization.draw_geometries([pcd1,pcd2],window_name="Aligned with ICP")

    print("Initializing point cloud comparison script.")
    compare_point_clouds(pcd1, pcd2, 0)
    return


if __name__ == "__main__":
    stl_file = r"C:\Users\ovikd\Documents\Punktskyer\DesignUdenTap.STL"
    scanned_pc_path1 = r"C:\Users\ovikd\Documents\Punktskyer\ScannedMerged.ply"  # Replace with your scanned point cloud path

    scanned_pointcloud = o3d.io.read_point_cloud(scanned_pc_path1)

    complete_comparison(stl_file,scanned_pointcloud)





