import open3d as o3d
import numpy as np
import sys
from Comparison import compare_point_clouds
from PCP import process_point_clouds
from STP import STL_to_pointcloud

# File paths
stl_file = r"C:\Users\ovikd\Downloads\DesignPC_rotated.ply"
ply_file = r"C:\Users\ovikd\Downloads\cropped_est.ply"
voxel_size = 0.5 # Set the desired voxel size

# Load and downsample the PLY file
print("Loading and downsampling PLY file...")
ply_pcd = o3d.io.read_point_cloud(ply_file)
if ply_pcd.is_empty():
    print("Failed to load the PLY file.")
    sys.exit()

print(f"Original PLY point cloud has {len(ply_pcd.points)} points.")
ply_pcd_downsampled = ply_pcd.voxel_down_sample(voxel_size=voxel_size)
print(f"Downsampled PLY point cloud has {len(ply_pcd_downsampled.points)} points.")

# Save the downsampled PLY point cloud to a temporary file for further processing
downsampled_ply_file = r"C:\Users\ovikd\Downloads\downsampled_cropped_est.ply"
o3d.io.write_point_cloud(downsampled_ply_file, ply_pcd_downsampled)
print(f"Downsampled PLY point cloud saved to {downsampled_ply_file}")

# Process and compare point clouds

rotation_vectors = [
    (None),    # Tom første indgang
    (0, 1, 0)     # Rotation omkring en vilkårlig akse
    #(0, 0, 0)    # 90 grader omkring y-aksen
    ]


print("Processing point clouds")
output_file = process_point_clouds(ply_file, rotation_vectors, voxel_size=1.5, mcd=4)

# Call the function to compare point clouds
print("Comparing point clouds.")
compare_point_clouds(output_file, downsampled_ply_file, 0.001)
