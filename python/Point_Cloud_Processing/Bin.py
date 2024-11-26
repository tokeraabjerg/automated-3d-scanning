import numpy as np
import open3d as o3d

def compute_rotation_axis(pcd1, pcd2, angle):
    """
    Finds the axis of rotation given two point clouds and a known rotation angle.

    Args:
        pcd1 (o3d.geometry.PointCloud): First point cloud.
        pcd2 (o3d.geometry.PointCloud): Second point cloud (rotated version of pcd1).
        angle (float): Known rotation angle (in radians).

    Returns:
        np.ndarray: Unit vector representing the axis of rotation.
    """
    # Translate point clouds to center at the origin
    pcd1_centered = np.asarray(pcd1.points) - np.mean(np.asarray(pcd1.points), axis=0)
    pcd2_centered = np.asarray(pcd2.points) - np.mean(np.asarray(pcd2.points), axis=0)
    
    # Compute the cross-covariance matrix
    H = np.dot(pcd1_centered.T, pcd2_centered)
    
    # Singular Value Decomposition
    U, _, Vt = np.linalg.svd(H)
    R = np.dot(Vt.T, U.T)
    
    # Ensure R is a valid rotation matrix (det(R) should be 1)
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = np.dot(Vt.T, U.T)
    
    # Extract the axis of rotation from the rotation matrix
    axis = np.array([R[2, 1] - R[1, 2],
                     R[0, 2] - R[2, 0],
                     R[1, 0] - R[0, 1]])
    axis = axis / np.linalg.norm(axis)  # Normalize the axis
    
    return axis

def extract_rotation_axis_and_angle(R):
    """
    Extracts the rotation axis and angle from a rotation matrix.

    Args:
        R (np.ndarray): 3x3 rotation matrix.

    Returns:
        tuple: (axis, angle), where `axis` is the rotation axis (normalized)
               and `angle` is the rotation angle in radians.
    """
    # Ensure the matrix is valid (orthogonal and determinant close to 1)
    if not np.allclose(np.dot(R.T, R), np.eye(3)) or not np.isclose(np.linalg.det(R), 1):
        raise ValueError("Input is not a valid rotation matrix.")

    # Compute the rotation angle
    angle = np.arccos((np.trace(R) - 1) / 2)

    # Handle numerical precision issues for small angles
    if np.isclose(angle, 0):
        # No rotation, arbitrary axis
        return np.array([1, 0, 0]), 0

    # Compute the rotation axis using the antisymmetric part of R
    axis = np.array([
        R[2, 1] - R[1, 2],
        R[0, 2] - R[2, 0],
        R[1, 0] - R[0, 1]
    ]) / (2 * np.sin(angle))

    return axis, angle

# Example Usage
# Load two point clouds (e.g., "source.pcd" and "target.pcd")
# if __name__ == "__main__":


#     R = np.array([
#     [0, -1, 0],
#     [1,  0, 0],
#     [0,  0, 1]
#     ])

#     axis, angle = extract_rotation_axis_and_angle(R)
#     print("Rotation Axis:", axis)
#     print("Rotation Angle (degrees):", np.degrees(angle))

    # from PP import preprocess_point_cloud
    # from Misc_functions import create_arrow

    # voxel_size=1.5
    # # List of .ply files to process
    # ply_files = [
    #     r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\0 grader test 2.ply",
    #     r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\15 grader test 2.ply",
    #     r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\45 grader test 2.ply"
    # ]

    # rotation_vectors = [
    # (None),    # Tom første indgang
    # (25, 0, 0),     # Rotation omkring en vilkårlig akse
    # (45, 0, 0)    # 90 grader omkring y-aksen
    # ]
    # if len(ply_files) < 2:
    #     raise ValueError("At least two point cloud files are required for registration.")
    
    # # Load the first point cloud as the initial source
    # combined_cloud = o3d.io.read_point_cloud(ply_files[0])

    # arrows = [
    # create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
    # create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
    # create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
    # ]
    # combined_geometry = o3d.geometry.TriangleMesh()
    # for arrow in arrows:
    #     combined_geometry += arrow

    # # Preproces: Downsize, Remove outliers, Find normals, Find features:
    # # combined_cloud = combined_cloud.voxel_down_sample(voxel_size)
    # combined_cloud_normal, combined_cloud = preprocess_point_cloud(combined_cloud, voxel_size)

    # target_cloud = o3d.io.read_point_cloud(ply_files[2])

    # target_cloud_normal, target_cloud = preprocess_point_cloud(target_cloud, voxel_size)
    #     #target_cloud = target_cloud.voxel_down_sample(voxel_size)
    #     #target_cloud, ind = target_cloud.remove_statistical_outlier(nb_neighbors=150/voxel_size, std_ratio=0.5)
    # target_cloud.paint_uniform_color([1, 0.706, 0])

    # # Known angle in radians (e.g., 45 degrees)
    # angle = np.pi / 4

    # # Compute the rotation axis
    # rotation_axis = compute_rotation_axis(combined_cloud, target_cloud, angle)
    # print("Rotation Axis:", rotation_axis)

    # # Visualize the axis of rotation (optional)
    # origin = np.mean(np.asarray(combined_cloud.points), axis=0)  # Compute the center
    # arrow = o3d.geometry.TriangleMesh.create_arrow(
    #     cone_radius=0.02, cone_height=0.1, cylinder_radius=0.01, cylinder_height=0.5
    # )
    # arrow.paint_uniform_color([1, 0, 0])  # Red for visibility
    # arrow.translate(origin)
    # arrow.rotate(o3d.geometry.get_rotation_matrix_from_axis_angle(rotation_axis * angle))
    # o3d.visualization.draw_geometries([combined_cloud, target_cloud, arrow])

