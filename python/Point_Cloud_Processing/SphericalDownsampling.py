import open3d as o3d
import numpy as np
from scipy.spatial import KDTree

#===========================================================================
#  *                                 INFO
#    Downsampler en given punktsky ved hjælp af et k-d træ, samt sfæriske
#    "voxels". Tager cirka 8 sekunder at downsample for en rå punktsky.
#    
#    Bruger en ny modul scipy: python3 -m pip install scipy
#===========================================================================


def downsample_with_spherical_voxels(input_file, output_file, radius):
    """
    Downsample a point cloud using spherical voxels efficiently with KD-Tree.

    :param input_file: Path to the input point cloud file.
    :param output_file: Path to save the downsampled point cloud.
    :param radius: Radius of the spherical voxel.
    """
    # Load the point cloud from the file
    print(f"Loading point cloud from {input_file}...")
    point_cloud = o3d.io.read_point_cloud(input_file)
    if point_cloud.is_empty():
        print("Error: The point cloud is empty. Check the input file.")
        return

    # Get the number of points in the input file
    input_points_count = len(point_cloud.points)
    print(f"Number of points in input point cloud: {input_points_count}")

    # Visualize the input point cloud
    print("Visualizing the input point cloud...")
    o3d.visualization.draw_geometries([point_cloud], window_name="Input Point Cloud")

    print(f"Downsampling point cloud with spherical voxels (radius: {radius})...")
    points = np.asarray(point_cloud.points)

    # Use KDTree for efficient neighbor searching
    tree = KDTree(points)
    processed = np.zeros(len(points), dtype=bool)
    downsampled_points = []

    for i in range(len(points)):
        if not processed[i]:
            # Find neighbors within the spherical radius
            neighbors = tree.query_ball_point(points[i], radius)
            
            # Mark neighbors as processed
            processed[neighbors] = True

            # Select a representative point (e.g., centroid of neighbors)
            cluster_points = points[neighbors]
            centroid = cluster_points.mean(axis=0)
            downsampled_points.append(centroid)

    # Create new point cloud with downsampled points
    downsampled_pcd = o3d.geometry.PointCloud()
    downsampled_pcd.points = o3d.utility.Vector3dVector(np.array(downsampled_points))

    # Get the number of points in the downsampled file
    output_points_count = len(downsampled_points)
    print(f"Number of points in downsampled point cloud: {output_points_count}")

    # Save the downsampled point cloud
    print(f"Saving downsampled point cloud to {output_file}...")
    o3d.io.write_point_cloud(output_file, downsampled_pcd)
    print(f"Downsampling complete. Downsampled point cloud saved to {output_file}")

    # Visualize the downsampled point cloud
    print("Visualizing the downsampled point cloud...")
    o3d.visualization.draw_geometries([downsampled_pcd], window_name="Downsampled Point Cloud")

# File paths
input_pcd_file = r"C:\Users\ovikd\Documents\Punktskyer\Scanned45.ply"  # Input file path
output_pcd_file = r"C:\Users\ovikd\Documents\Punktskyer\downsampletest.ply"  # Output file path
spherical_radius = 1.5  # Adjust the radius as needed

downsample_with_spherical_voxels(input_pcd_file, output_pcd_file, spherical_radius)
