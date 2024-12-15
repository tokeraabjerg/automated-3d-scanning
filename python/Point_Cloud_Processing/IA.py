import open3d as o3d
import numpy as np
import itertools
import getpass
import copy  # Import the copy module

# Define your username
your_username = "mikke"

# Check if the current user is you
if getpass.getuser() == your_username:
    print("The code is being without modules")
    from ICP import Point_to_Plane
else:
    # print("The code is not being run with modules")
    from .ICP import Point_to_Plane


def RANSAC_initial_alignment(source, target):
    # Simple initial alignment using downsampling and FPFH (Fast Point Feature Histograms)

    # Estimating normals for source and target point clouds
    radius_normal = 0.1  # Radius til normal estimering
    source.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=50))  # Øget max_nn for at få tilstrækkelige naboer
    target.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=50))

    # Calculate FPFH feature for both source and target
    source_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        source, o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=100))  # Juster max_nn hvis nødvendigt
    target_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        target, o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=100))

    # Use RANSAC to find a rough initial alignment
    # RANSAC-konvergenskriterier og estimation method
    Criteria = o3d.pipelines.registration.RANSACConvergenceCriteria(max_iteration=100, confidence=0.99)

    result = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        target, source, target_fpfh, source_fpfh,
        mutual_filter=True, max_correspondence_distance=0.10,
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        ransac_n=4,  # Antal punkter for at beregne transformationen
        criteria=Criteria)  # Brug RANSAC-konvergenskriterier


    return result.transformation


def rotate_point_cloud(target, rotation_vectors, index):
    """
    Behandler en point cloud ved at anvende en rotation fra en liste af rotationsvektorer
    baseret på et givet indeks. Hvis ingen rotation findes for indekset, udføres ingen rotation.

    Args:
        target (o3d.geometry.PointCloud): Den target point cloud, der skal behandles.
        rotation_vectors (list[tuple]): Liste over rotationsvektorer (x, y, z) i grader.
        index (int): Indeks i rotationslisten, der skal bruges.

    Returns:
        o3d.geometry.PointCloud: Den behandlede point cloud.
    """
    
    if index < len(rotation_vectors):
        # Hent rotationsvektoren ved det givne indeks
        rotation_vector = rotation_vectors[index]

        # Beregn længden af rotationsvektoren (rotationens størrelse)
        rotation_magnitude = np.linalg.norm(rotation_vector)

        if rotation_magnitude == 0:
            print(f"Rotation {index}: Ingen rotation påkrævet.")
            return target

        # Normaliser rotationsvektoren
        rotation_axis = np.array(rotation_vector) / rotation_magnitude

        # Konverter rotationsmagnitude til radianer
        theta = np.radians(rotation_magnitude)

        # Rodrigues' rotation formel: Skab en rotationsmatrix
        K = np.array([
            [0, -rotation_axis[2], rotation_axis[1]],
            [rotation_axis[2], 0, -rotation_axis[0]],
            [-rotation_axis[1], rotation_axis[0], 0]
        ])
        I = np.eye(3)
        R = I + np.sin(theta) * K + (1 - np.cos(theta)) * np.dot(K, K)

        # Roter point cloud
        target.rotate(R, center=(0, 0, 0))
        
        R_4x4 = np.eye(4)
        R_4x4[:3, :3] = R

        print(f"Point cloud rotated by vector {rotation_vector} (magnitude {rotation_magnitude} degrees) at index {index}.")
    else:
        print(f"No rotation applied for index {index} (Out of bounds).")

    return target, R_4x4


def rotate_point_cloud_euler(target, euler_angles, index):
    """
    Rotate a point cloud using Euler angles (roll, pitch, yaw) at a specified index.
    If no Euler angles exist for the index, no rotation is applied.

    Args:
        target (o3d.geometry.PointCloud): The target point cloud to process.
        euler_angles (list[tuple]): List of Euler angles (roll, pitch, yaw) in degrees.
        index (int): Index in the Euler angles list to use for rotation.

    Returns:
        o3d.geometry.PointCloud: The rotated point cloud.
        np.ndarray: The 4x4 transformation matrix used for the rotation.
    """
    if index < len(euler_angles):
        # Retrieve the Euler angles at the specified index
        roll, pitch, yaw = euler_angles[index]

        # Convert angles from degrees to radians
        roll = np.radians(roll)
        pitch = np.radians(pitch)
        yaw = np.radians(yaw)

        # Rotation matrices for each axis
        R_x = np.array([
            [1, 0, 0],
            [0, np.cos(roll), -np.sin(roll)],
            [0, np.sin(roll), np.cos(roll)]
        ])

        R_y = np.array([
            [np.cos(pitch), 0, np.sin(pitch)],
            [0, 1, 0],
            [-np.sin(pitch), 0, np.cos(pitch)]
        ])

        R_z = np.array([
            [np.cos(yaw), -np.sin(yaw), 0],
            [np.sin(yaw), np.cos(yaw), 0],
            [0, 0, 1]
        ])

        # Combine the rotations (R = Rz * Ry * Rx)
        R = R_z @ R_y @ R_x

        # Apply the rotation to the point cloud
        target.rotate(R, center=(0, 0, 0))

        # Create a 4x4 transformation matrix
        R_4x4 = np.eye(4)
        R_4x4[:3, :3] = R

        print(f"Point cloud rotated by Euler angles (roll={np.degrees(roll):.2f}°, pitch={np.degrees(pitch):.2f}°, yaw={np.degrees(yaw):.2f}°) at index {index}.")
    else:
        print(f"No rotation applied for index {index} (Out of bounds).")
        R_4x4 = np.eye(4)

    return target, R_4x4


def execute_global_registration(source_down, target_down, source_fpfh,
                                target_fpfh, voxel_size):
    distance_threshold = voxel_size * 1.5
    print(":: RANSAC registration on downsampled point clouds.")
    print("   Since the downsampling voxel size is %.3f," % voxel_size)
    print("   we use a liberal distance threshold %.3f." % distance_threshold)
    result = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        source_down, target_down, source_fpfh, target_fpfh, True,
        distance_threshold,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(False),
        3, [
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnNormal(
                0.25),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(
                distance_threshold)
        ], o3d.pipelines.registration.RANSACConvergenceCriteria(1000, 0.99))
    return result


def align_point_clouds(scan, stl_point_cloud):
    """
    Align the point cloud generated from an STL file with the final scan.
    
    Args:
        scan (o3d.geometry.PointCloud): The scanned point cloud.
        stl_point_cloud (o3d.geometry.PointCloud): The point cloud generated from the STL file.
    
    Returns:
        o3d.geometry.PointCloud: The aligned scanned point cloud.
    """
    # Center both point clouds by density
    scan_center = np.mean(np.asarray(scan.points), axis=0)
    stl_center = np.mean(np.asarray(stl_point_cloud.points), axis=0)
    scan.translate(-scan_center)
    stl_point_cloud.translate(-stl_center)

    # Define all possible 90 degree rotations
    rotations = [
        (0, 0, 0), (90, 0, 0), (180, 0, 0), (270, 0, 0),
        (0, 90, 0), (0, 180, 0), (0, 270, 0),
        (0, 0, 90), (0, 0, 180), (0, 0, 270),
        (90, 90, 0), (90, 180, 0), (90, 270, 0),
        (180, 90, 0), (180, 180, 0), (180, 270, 0),
        (270, 90, 0), (270, 180, 0), (270, 270, 0)
    ]

    best_fitness = float('inf')
    best_transformation = None

    for rotation in rotations:
        # Apply rotation
        rotated_scan = copy.deepcopy(scan)  # Use deepcopy instead of copy() or clone()
        R = o3d.geometry.PointCloud.get_rotation_matrix_from_xyz(np.radians(rotation))
        rotated_scan.rotate(R, center=(0, 0, 0))

        # Run Point-To-Plane ICP
        result = o3d.pipelines.registration.registration_icp(
            rotated_scan, stl_point_cloud, max_correspondence_distance=0.05,
            estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPlane()
        )

        if result.fitness < best_fitness:
            best_fitness = result.fitness
            best_transformation = result.transformation

    # Apply the best transformation to the original scan
    aligned_scan = copy.deepcopy(scan)  # Use deepcopy instead of copy() or clone()
    aligned_scan.transform(best_transformation)

    return aligned_scan, stl_point_cloud


# def select_points(point_cloud):
#     print("Please select 3 points in the point cloud.")
#     vis = o3d.visualization.VisualizerWithEditing()
#     vis.create_window()
#     vis.add_geometry(point_cloud)
#     vis.run()  # user picks points
#     vis.destroy_window()
#     return vis.get_picked_points()

# def calculate_transformation_matrix(points):
#     assert len(points) == 3, "Exactly 3 points must be selected."

#     # Convert points to numpy array
#     points = np.array(points)

#     # Calculate vectors
#     v1 = points[1] - points[0]
#     v2 = points[2] - points[0]

#     # Calculate normal vector
#     normal = np.cross(v1, v2)
#     normal /= np.linalg.norm(normal)

#     # Create rotation matrix
#     R = np.eye(4)
#     R[:3, :3] = np.vstack([v1 / np.linalg.norm(v1), v2 / np.linalg.norm(v2), normal]).T

#     # Create translation matrix
#     T = np.eye(4)
#     T[:3, 3] = -points[0]

#     # Combine rotation and translation
#     transformation_matrix = np.dot(R, T)

#     return transformation_matrix

# def align_point_cloud_with_axis(point_cloud):
#     # Select 3 points
#     picked_points_indices = select_points(point_cloud)
#     picked_points = np.asarray(point_cloud.points)[picked_points_indices]

#     # Calculate transformation matrix
#     transformation_matrix = calculate_transformation_matrix(picked_points)

#     # Apply transformation
#     point_cloud.transform(transformation_matrix)

#     return point_cloud


# if __name__ == "__main__":
#     from Misc_functions import create_arrow
#     from PP import preprocess_point_cloud

#     voxel_size=1.5
#     # List of .ply files to process
#     ply_files = [
#         r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\0 grader test 2.ply",
#         r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\15 grader test 2.ply",
#         r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\45 grader test 2.ply"
#     ]

#     rotation_vectors = [
#     (None),    # Tom første indgang
#     (15, 0, 0),     # Rotation omkring en vilkårlig akse
#     (45, 0, 0)    # 90 grader omkring y-aksen
#     ]
#     if len(ply_files) < 2:
#         raise ValueError("At least two point cloud files are required for registration.")
    
#     # Load the first point cloud as the initial source
#     combined_cloud = o3d.io.read_point_cloud(ply_files[0])

#     arrows = [
#     create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
#     create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
#     create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
#     ]
#     combined_geometry = o3d.geometry.TriangleMesh()
#     for arrow in arrows:
#         combined_geometry += arrow

#     # Preproces: Downsize, Remove outliers, Find normals, Find features:
#     # combined_cloud = combined_cloud.voxel_down_sample(voxel_size)
#     combined_cloud_normal, combined_cloud = preprocess_point_cloud(combined_cloud, voxel_size)

#     select_points(combined_cloud)

#     target_cloud = o3d.io.read_point_cloud(ply_files[1])

#     target_cloud_normal, target_cloud = preprocess_point_cloud(target_cloud, voxel_size)
#         #target_cloud = target_cloud.voxel_down_sample(voxel_size)
#         #target_cloud, ind = target_cloud.remove_statistical_outlier(nb_neighbors=150/voxel_size, std_ratio=0.5)
#     target_cloud.paint_uniform_color([1, 0.706, 0])
#     o3d.visualization.draw_geometries([combined_cloud, target_cloud, combined_geometry], window_name="Point Clouds")
#     target_cloud, initial_transformation=rotate_point_cloud(target_cloud, rotation_vectors, 1)
#     print(initial_transformation)
#     o3d.visualization.draw_geometries([combined_cloud, target_cloud, combined_geometry], window_name="Rotated Point Cloud")

#     combined_center = np.mean(np.asarray(combined_cloud.points), axis=0)
#     target_center = np.mean(np.asarray(target_cloud.points), axis=0)
#     translation_vector=combined_center-target_center
#     print(translation_vector)
#     target_cloud.translate(translation_vector)
#     o3d.visualization.draw_geometries([combined_cloud, target_cloud, combined_geometry], window_name="Translated Point Cloud")
