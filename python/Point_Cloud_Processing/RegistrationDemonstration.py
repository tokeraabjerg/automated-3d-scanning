import numpy as np
import open3d as o3d
import matplotlib.pyplot as plt

def load_bunny_point_cloud():
    """
    Load the Stanford Bunny point cloud and project it to 2D.
    Returns:
        reference_points (numpy.ndarray): The original 2D point cloud.
        target_points (numpy.ndarray): Transformed point cloud (used as target).
    """
    # Load the Stanford Bunny
    bunny = o3d.data.BunnyMesh().path
    bunny_mesh = o3d.io.read_triangle_mesh(bunny)
    bunny_pc = bunny_mesh.sample_points_poisson_disk(number_of_points=500)

    # Project to 2D by dropping the z-axis
    bunny_points = np.asarray(bunny_pc.points)
    reference_points = bunny_points[:, :2]

    # Apply a rigid transformation to create the target point cloud
    theta = np.radians(30)  # Rotation angle
    rotation_matrix = np.array([[np.cos(theta), -np.sin(theta)], 
                                 [np.sin(theta), np.cos(theta)]])
    translation = np.array([0.1, 0.2])
    target_points = (rotation_matrix @ reference_points.T).T + translation

    return reference_points, target_points

def numpy_to_open3d(points):
    """
    Convert a numpy array of points to an Open3D point cloud.
    Args:
        points (numpy.ndarray): Array of 2D points.
    Returns:
        open3d.geometry.PointCloud: Open3D point cloud.
    """
    pc = o3d.geometry.PointCloud()
    pc.points = o3d.utility.Vector3dVector(np.hstack((points, np.zeros((points.shape[0], 1)))))
    return pc

def visualize_registration(reference, target, intermediate=None, result=None, step=None):
    """
    Visualize the registration results.
    """
    plt.figure(figsize=(8, 6))
    plt.scatter(reference[:, 0], reference[:, 1], label="Target", alpha=0.7)
    plt.scatter(target[:, 0], target[:, 1], label="Reference", alpha=0.7)
    if intermediate is not None:
        plt.scatter(intermediate[:, 0], intermediate[:, 1], label="Intermediate", alpha=0.7, marker="x")
    if result is not None:
        plt.scatter(result[:, 0], result[:, 1], label="Registered", alpha=0.7, marker="x")
        if step == "before_icp":
            plt.title("Before ICP Registration")
        elif step == "intermediate":
            plt.title("Intermediate Transformation")
        else:
            plt.title("After ICP Registration")
    else:
        plt.title("Point Clouds")
    plt.legend()
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.grid()
    plt.axis("equal")
    plt.show()

def main():
    # Load reference and target point clouds
    target_points, reference_points = load_bunny_point_cloud()

    # Convert to Open3D point clouds
    reference_pc = numpy_to_open3d(reference_points)
    target_pc = numpy_to_open3d(target_points)

    # Visualize before registration
    visualize_registration(reference_points, target_points, step="before_icp")

    # Apply an intermediate transformation for demonstration
    intermediate_transform = np.eye(4)
    theta = np.radians(7)  # -10 degrees rotation
    rotation_matrix = np.array([[np.cos(theta), -np.sin(theta)], 
                                 [np.sin(theta), np.cos(theta)]])
    intermediate_transform[:2, :2] = rotation_matrix
    intermediate_transform[:2, 3] = [0.05, 0.04]  # Move -0.05 in x-axis and -0.12 in y-axis
    intermediate_pc = intermediate_transform[:2, :2] @ target_points.T + intermediate_transform[:2, 3].reshape(2, 1)
    intermediate_points = intermediate_pc.T

    # Visualize intermediate transformation
    visualize_registration(reference_points, target_points, intermediate=intermediate_points, step="intermediate")

    # Perform registration using ICP
    threshold = 0.02  # Distance threshold
    result = o3d.pipelines.registration.registration_icp(
        target_pc, reference_pc, threshold, np.eye(4),
        o3d.pipelines.registration.TransformationEstimationPointToPoint())

    # Extract registered points
    registered_pc = result.transformation[:2, :2] @ target_points.T + result.transformation[:2, 3].reshape(2, 1)
    registered_points = registered_pc.T

    # Visualize after registration
    visualize_registration(reference_points, target_points, result=registered_points, step="after_icp")

if __name__ == "__main__":
    main()
