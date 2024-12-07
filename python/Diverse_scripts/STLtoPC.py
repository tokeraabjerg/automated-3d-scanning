import open3d as o3d
import numpy as np
import os

#================================================
#  *                    INFO
#    Omgør en STL-fil til en punktsky med et
#    bestemt antal punkter. Filen bliver gemt til
#    en path der bestemmes i bunden. Scriptet
#    kan måske kaldes fra et andet script, men
#    ikke regn med det. Det burde uanset bare
#    blive kørt en gang per STL-fil.
#================================================ 

import open3d as o3d
import numpy as np

def stl_to_point_cloud(stl_file, output_file, num_points=100000):
    """
    Convert an STL file to a point cloud and save it as a PLY file.
    :param stl_file: Path to the STL file.
    :param output_file: Path to save the resulting PLY file.
    :param num_points: Number of points to sample from the mesh.
    """
    # Load the STL file as a triangle mesh
    print(f"Loading STL file from {stl_file}...")
    mesh = o3d.io.read_triangle_mesh(stl_file)
    if mesh.is_empty():
        print("Failed to load the STL file. Please check the path.")
        return

    # Sample points on the mesh using Poisson disk sampling
    print(f"Sampling approximately {num_points} points from the mesh using Poisson disk sampling...")
    point_cloud = mesh.sample_points_poisson_disk(number_of_points=num_points, init_factor=5)

    # Save the point cloud as a PLY file
    print(f"Saving point cloud to {output_file}...")
    o3d.io.write_point_cloud(output_file, point_cloud)
    print(f"Point cloud successfully saved to {output_file}")
    
    return point_cloud

if __name__ == "__main__":
    # File paths
    stl_file = r"C:\Users\mikke\automated-3d-scanning\calibration\CalibrationCylinder.STL"  # Replace with your STL file path
    output_ply_file = r"C:\Users\mikke\automated-3d-scanning\calibration\CalibrationCylinder2.ply"  # Output PLY file

    # Convert and save the point cloud
    stl_to_point_cloud(stl_file, output_ply_file, num_points=200000)