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