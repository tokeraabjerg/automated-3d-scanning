import open3d as o3d

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

import numpy as np

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

import open3d as o3d
import numpy as np

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


if __name__ == "__main__":
    from Misc_functions import create_arrow
    from PP import preprocess_point_cloud

    voxel_size=1.5
    # List of .ply files to process
    ply_files = [
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\0 grader test 2.ply",
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\15 grader test 2.ply",
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\45 grader test 2.ply"
    ]

    rotation_vectors = [
    (None),    # Tom første indgang
    (25, 0, 0),     # Rotation omkring en vilkårlig akse
    (45, 0, 0)    # 90 grader omkring y-aksen
    ]
    if len(ply_files) < 2:
        raise ValueError("At least two point cloud files are required for registration.")
    
    # Load the first point cloud as the initial source
    combined_cloud = o3d.io.read_point_cloud(ply_files[0])

    arrows = [
    create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
    ]
    combined_geometry = o3d.geometry.TriangleMesh()
    for arrow in arrows:
        combined_geometry += arrow

    # Preproces: Downsize, Remove outliers, Find normals, Find features:
    # combined_cloud = combined_cloud.voxel_down_sample(voxel_size)
    combined_cloud_normal, combined_cloud = preprocess_point_cloud(combined_cloud, voxel_size)

    target_cloud = o3d.io.read_point_cloud(ply_files[1])

    target_cloud_normal, target_cloud = preprocess_point_cloud(target_cloud, voxel_size)
        #target_cloud = target_cloud.voxel_down_sample(voxel_size)
        #target_cloud, ind = target_cloud.remove_statistical_outlier(nb_neighbors=150/voxel_size, std_ratio=0.5)
    target_cloud.paint_uniform_color([1, 0.706, 0])
    o3d.visualization.draw_geometries([combined_cloud, target_cloud, combined_geometry], window_name="Point Clouds")
    target_cloud, initial_transformation=rotate_point_cloud(target_cloud, rotation_vectors, 1)
    print(initial_transformation)
    o3d.visualization.draw_geometries([combined_cloud, target_cloud, combined_geometry], window_name="Rotated Point Cloud")

    combined_center = np.mean(np.asarray(combined_cloud.points), axis=0)
    target_center = np.mean(np.asarray(target_cloud.points), axis=0)
    translation_vector=combined_center-target_center
    print(translation_vector)
    target_cloud.translate(translation_vector)
    o3d.visualization.draw_geometries([combined_cloud, target_cloud, combined_geometry], window_name="Translated Point Cloud")

