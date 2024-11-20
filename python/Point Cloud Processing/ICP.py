import open3d as o3d
import numpy as np


def Point_to_Plane(source, target, mcd):
    # Point Association using ICP for Open3D v0.18.0
    print("Running ICP...")

    # Initializing convergence criteria (using ICPConvergenceCriteria)
    criteria = o3d.pipelines.registration.ICPConvergenceCriteria(
        relative_fitness=1e-10, 
        relative_rmse=1e-10, 
        max_iteration=50
    )


    # Perform ICP
    icp_result = o3d.pipelines.registration.registration_icp(
        target, source, max_correspondence_distance=mcd, 
        init=np.eye(4),  # Initial transformation (identity matrix)
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        criteria=criteria
    )


    print("Fitness: ", icp_result.fitness)
    print("Inlier RMSE: ", icp_result.inlier_rmse)

    # Apply the transformation to the target point cloud
    target.transform(icp_result.transformation)

    # Return the transformed target point cloud for further use (or visualization)
    return icp_result.transformation, target
