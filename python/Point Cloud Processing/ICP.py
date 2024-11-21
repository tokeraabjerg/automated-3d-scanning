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


# Callback function to log iteration progress
def icp_callback(iteration, fitness, inlier_rmse):
    print(f"Iteration: {iteration}, Fitness: {fitness:.6f}, Inlier RMSE: {inlier_rmse:.6f}")

def t_Point_to_Plane_Lore(source, target, mcd):
    """
    Point-to-plane ICP implementation with iteration logging.
    
    Args:
        source (o3d.geometry.PointCloud): Source point cloud.
        target (o3d.geometry.PointCloud): Target point cloud.
        mcd (float): Maximum correspondence distance.

    Returns:
        np.ndarray: Final transformation matrix.
        o3d.geometry.PointCloud: Transformed target point cloud.
    """
    print("Running ICP...")

    # Initializing convergence criteria
    criteria = o3d.pipelines.registration.ICPConvergenceCriteria(
        relative_fitness=1e-10, 
        relative_rmse=1e-10, 
        max_iteration=50
    )

    # Wrapper function to include iteration logging
    iteration_log = []

    def callback_after_iteration(iteration, fitness, inlier_rmse):
        icp_callback(iteration, fitness, inlier_rmse)  # Log details
        iteration_log.append((iteration, fitness, inlier_rmse))

    # Perform ICP
    result = o3d.pipelines.registration.registration_icp(
        target,
        source,
        max_correspondence_distance=mcd,
        init=np.eye(4),  # Initial transformation (identity matrix)
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        criteria=criteria,
        callback_after_iteration=callback_after_iteration,  # Add callback
    )

    # Logging final results
    print(f"Final Fitness: {result.fitness:.6f}")
    print(f"Final Inlier RMSE: {result.inlier_rmse:.6f}")
    print("Transformation Matrix:")
    print(result.transformation)

    # Apply the transformation to the target point cloud
    target.transform(result.transformation)

    return result.transformation, target, iteration_log
