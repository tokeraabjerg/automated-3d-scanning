import open3d as o3d
import numpy as np
from Comparison import compare_point_clouds
import sys
import os

# Dynamically add the parent of the current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)

from Diverse_scripts.STLtoPC import stl_to_point_cloud



def complete_comparison(design_STL, scanned_pc):

    # Constants
    num_points = 100000

    print("Converting STL-file to a pointcloud with " + num_points + " points.")





x=1
y=1



stl_file = r"C:\Users\ovikd\Documents\Punktskyer\DesignUdenTap.STL"
complete_comparison(x,y)





