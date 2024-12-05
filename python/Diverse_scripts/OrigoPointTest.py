import open3d as o3d
import numpy as np


def remove_origin_points(input_file, output_file):
    # Load the point cloud
    print(f"Loading point cloud from {input_file}...")
    point_cloud = o3d.io.read_point_cloud(input_file)
    
    if not point_cloud.has_points():
        print("Point cloud is empty or not loaded properly.")
        return

    # Convert point cloud to numpy array
    points = np.asarray(point_cloud.points)
    print(f"Original point cloud has {points.shape[0]} points.")

    # Remove points with coordinates [0, 0, 0]
    mask = ~np.all(points == [0, 0, -1], axis=1)
    filtered_points = points[mask]

    if len(filtered_points) == 0:
        print("All points have been removed. The filtered point cloud is empty.")
        return

    # Update the point cloud with the filtered points
    filtered_point_cloud = o3d.geometry.PointCloud()
    filtered_point_cloud.points = o3d.utility.Vector3dVector(filtered_points)

    # Copy colors if available
    if point_cloud.has_colors():
        colors = np.asarray(point_cloud.colors)
        filtered_point_cloud.colors = o3d.utility.Vector3dVector(colors[mask])

    # Copy normals if available
    if point_cloud.has_normals():
        normals = np.asarray(point_cloud.normals)
        filtered_point_cloud.normals = o3d.utility.Vector3dVector(normals[mask])

    # Save the cleaned point cloud
    print(f"Saving cleaned point cloud to {output_file}...")
    o3d.io.write_point_cloud(output_file, filtered_point_cloud)
    print(f"Cleaned point cloud saved successfully with {len(filtered_points)} points.")

# Run the function

if __name__ == "__main__":
    # File paths
    input_file = r"C:\Users\ovikd\Documents\GitHub\automated-3d-scanning\scanner_interface\output\Calibrationverification\scan_8.ply"
    output_file = r"C:\Users\ovikd\Documents\Punktskyer\OrigoPointTest.ply"
    remove_origin_points(input_file, input_file)
