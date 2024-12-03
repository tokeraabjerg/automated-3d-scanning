import sys
import os
import open3d as o3d
import numpy as np

from ICP import Point_to_Plane
from IA import align_point_clouds

# Dynamically add the parent of the current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)

from Diverse_scripts.STLtoPC import stl_to_point_cloud
from Comparison import compare_point_clouds
from Translatory_crutch import align_centroids



def complete_comparison(design_STL, scanned_pc, rotation_manual = False):

    # Constants
    num_points = 10000

    print("Initializing STL to point cloud conversion.")
    design_pointcloud = stl_to_point_cloud(design_STL,0,num_points)
    print("STL converted to point cloud.")
    
    print("Aligning centroids of point clouds.")
    pcd1, pcd2 = align_centroids(design_pointcloud,scanned_pc)

    o3d.visualization.draw_geometries([pcd1,pcd2],window_name="Aligned by centroids")
    if rotation_manual is True:
        print("Manually rotate the pointclouds to align them.")
        pcd1.rotate(o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(0), np.radians(90), np.radians(-90))))
    else:
        print("Non-manually rotate the pointclouds to align them.")
        print("Aligning point clouds using optimal initial alignment and ICP.")
        aligned_scan = align_point_clouds(scanned_pc, design_pointcloud)
    
    o3d.visualization.draw_geometries([pcd1,pcd2],window_name="Rotated manually")
    print("Running point to plane on pointclouds.")
    Point_to_Plane(pcd1, pcd2, mcd=4)
    print("Point to plane done.")

    print("Visualizing aligned point clouds.")
    o3d.visualization.draw_geometries([design_pointcloud, aligned_scan], window_name="Aligned Point Clouds")

    print("Initializing point cloud comparison script.")
    compare_point_clouds(design_pointcloud, aligned_scan, 0)
    return


if __name__ == "__main__":
    stl_file = r"C:\Users\ovikd\Documents\Punktskyer\DesignUdenTap.STL"
    scanned_pc_path1 = r"C:\Users\ovikd\Documents\Punktskyer\ScannedMerged.ply"  # Replace with your scanned point cloud path

    scanned_pointcloud = o3d.io.read_point_cloud(scanned_pc_path1)

    complete_comparison(stl_file, scanned_pointcloud, rotation_manual=False)





