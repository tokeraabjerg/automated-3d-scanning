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



def complete_comparison(Idesign_STL, Iscanned_pc, rotation_manual = False):

    # Constants
    num_points = 10000

    print("Initializing STL to point cloud conversion.")
    design_pointcloud = stl_to_point_cloud(Idesign_STL,0,num_points)
    print("STL converted to point cloud.")
    
    print("Aligning centroids of point clouds.")
    designPC_translated, scanned_pc = align_centroids(design_pointcloud,Iscanned_pc)
    print("Centroids aligned.")
    o3d.visualization.draw_geometries([designPC_translated,Iscanned_pc],window_name="Aligned by centroids")
    
    
    if rotation_manual is True:
        print("Manually rotate the pointcloud.")
        aligned_design = designPC_translated.rotate(o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(0), np.radians(90), np.radians(-90))))
        print("Rotating manually.")

#TODO: Figure this shit out
    else:
        print("i aint doin jack shit rn i got lotion on my shit rn")
        print("Automatically rotate the pointcloud.")
        print("Aligning point clouds using optimal initial alignment and ICP.")
        aligned_scan, stl_point_cloud  = align_point_clouds(Iscanned_pc, design_pointcloud)
    
    #Viser punktskyen fra scan, og punktskyen til designet der er (røft) flyttet og roteret
    o3d.visualization.draw_geometries([aligned_design,Iscanned_pc],window_name="Rotated.")
    
    # Forsøger at lave en så god transform (rotation og translation) som muligt.
    print("Running point to plane on pointclouds.")
    Point_to_Plane(aligned_design, Iscanned_pc, max_correspondence_distance=3)
    print("Point to plane done.")

    print("Visualizing aligned point clouds.")
    o3d.visualization.draw_geometries([Iscanned_pc, aligned_design], window_name="Aligned Point Clouds")
    
    print("Initializing point cloud comparison script.")
    compare_point_clouds(aligned_design, Iscanned_pc)
    return


if __name__ == "__main__":
    stl_file = r"C:\Users\ovikd\Downloads\AfskaarenTestemne.STL"
    scanned_pc_path1 = r"C:\Users\ovikd\Documents\GitHub\automated-3d-scanning\scanner_interface\output\test_project\scan_1.ply"  # Replace with your scanned point cloud path

    scanned_pointcloud = o3d.io.read_point_cloud(scanned_pc_path1)

    complete_comparison(stl_file, scanned_pointcloud, rotation_manual=True)





