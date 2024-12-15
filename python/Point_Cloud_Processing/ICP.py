import open3d as o3d
import numpy as np
#Todo: Include the following metods in the ICP.py file, test them in the PCP.py file
#https://www.open3d.org/html/python_api/open3d.pipelines.registration.CorrespondenceCheckerBasedOnNormal.html#open3d-pipelines-registration-correspondencecheckerbasedonnormal

def Point_to_Plane(source, target, max_correspondence_distance):
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
        target, source, max_correspondence_distance=max_correspondence_distance, 
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

# Broken func. Normal checking is not available in this formulation of the function
def Point_to_Plane_with_Normal_Check(source, target, max_correspondence_distance, normal_threshold):
    # Point Association using ICP for Open3D v0.18.0
    print("Running ICP with normal check...")
    
    # Initializing convergence criteria (using ICPConvergenceCriteria)
    criteria = o3d.pipelines.registration.ICPConvergenceCriteria(
        relative_fitness=1e-10, 
        relative_rmse=1e-10, 
        max_iteration=50
    )

    # Correspondence checker based on normal
    correspondence_checker = o3d.pipelines.registration.CorrespondenceCheckerBasedOnNormal(
        normal_angle_threshold=np.deg2rad(normal_threshold)  # Adjust the angle threshold as needed
    )

    # Perform ICP
    icp_result = o3d.pipelines.registration.registration_icp(
        target, source, max_correspondence_distance=max_correspondence_distance, 
        init=np.eye(4),  # Initial transformation (identity matrix)
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        criteria=criteria,
        checkers=[correspondence_checker]
    )

        # Apply the transformation to the target point cloud
    target.transform(icp_result.transformation)
    return icp_result.transformation, target


def legacy_icp_with_logging(source, target, max_correspondence_distance):
    """
    Perform point-to-plane ICP using the legacy API with iteration logging.
    
    Args:
        source (o3d.geometry.PointCloud): The source point cloud.
        target (o3d.geometry.PointCloud): The target point cloud.
        max_correspondence_distance (float): Maximum correspondence distance for ICP.
        init_transformation (np.ndarray): Initial 4x4 transformation matrix.
        max_iterations (int): Number of ICP iterations.
    
    Returns:
        np.ndarray: Final transformation matrix.
    """
    # Copy source to avoid modifying the original
    init_transformation=np.eye(4)
    max_iterations=(15)
    transformation_log=np.eye(4)
    target_copy = target.transform(init_transformation)
    transformation = init_transformation

    # Logging header
    print(f"{'Iteration':<10}{'Fitness':<10}{'Inlier RMSE':<15}{'Change in Transform':<20}")
    print("-" * 55)

    # Perform manual ICP iterations
    for i in range(max_iterations):
        # Find correspondences and estimate transformation
        reg_result = o3d.pipelines.registration.registration_icp(
            target_copy, source, max_correspondence_distance, transformation,
            o3d.pipelines.registration.TransformationEstimationPointToPlane()
        )
        
        # Log metrics
        fitness = reg_result.fitness
        inlier_rmse = reg_result.inlier_rmse
        delta_transform = np.linalg.norm(transformation - reg_result.transformation)
        print(f"{i+1:<10}{fitness:<10.6f}{inlier_rmse:<15.6f}{delta_transform:<20.6f}")

        # Check for convergence (optional)
        if delta_transform < 1e-5:
            print("Converged!")
            break
        
        # Update transformation and apply it
        transformation_log=np.dot(reg_result.transformation, transformation_log)
        transformation = reg_result.transformation
        target_copy.transform(transformation)
    
    return transformation_log, target_copy


# TENSOR
# Callback function to log iteration progress
def icp_callback(iteration, fitness, inlier_rmse):
    print(f"Iteration: {iteration}, Fitness: {fitness:.6f}, Inlier RMSE: {inlier_rmse:.6f}")

def t_Point_to_Plane_Log(source, target, max_correspondence_distance):
    """
    Point-to-plane ICP implementation with iteration logging.
    
    Args:
        source (o3d.geometry.PointCloud): Source point cloud.
        target (o3d.geometry.PointCloud): Target point cloud.
        max_correspondence_distance (float): Maximum correspondence distance.

    Returns:
        np.ndarray: Final transformation matrix.
        o3d.geometry.PointCloud: Transformed target point cloud.
    """
    print("Running ICP...")

    # Initializing convergence criteria
    criteria = o3d.t.pipelines.registration.ICPConvergenceCriteria(
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
    result = o3d.t.pipelines.registration.registration_icp(
        target,
        source,
        max_correspondence_distance=max_correspondence_distance,
        init=np.eye(4),  # Initial transformation (identity matrix)
        estimation_method=o3d.t.pipelines.registration.TransformationEstimationPointToPlane(),
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
