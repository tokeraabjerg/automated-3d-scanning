import open3d as o3d
import numpy as np

# Load the point clouds
def load_point_clouds(pcd_path_1, pcd_path_2):
    pcd1 = o3d.io.read_point_cloud(pcd_path_1)
    pcd2 = o3d.io.read_point_cloud(pcd_path_2)
    return pcd1, pcd2

# Preprocess point clouds: downsample them for faster processing (optional)
def preprocess_point_cloud(pcd, voxel_size):
    pcd_down = pcd.voxel_down_sample(voxel_size=voxel_size)
    radius_normal = voxel_size * 2
    pcd_down.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=30))
    return pcd_down

# Perform ICP registration
def icp_registration(source, target, voxel_size):
    # Use a transformation threshold (smaller than the size of the scene objects)
    threshold = voxel_size * 1.5
    # Initialize a rough initial transformation matrix if needed
    initial_transform = np.identity(4)

    # Run the ICP registration
    icp_result = o3d.pipelines.registration.registration_icp(
        source, target, threshold, initial_transform,
        o3d.pipelines.registration.TransformationEstimationPointToPoint())

    return icp_result

# Paths to your point clouds
pcd_path_1 = "path/to/first_point_cloud.ply"  # replace with your first file path
pcd_path_2 = "path/to/second_point_cloud.ply"  # replace with your second file path

# Set the voxel size for downsampling
voxel_size = 0.05  # Adjust based on your point cloud size

# Load and preprocess
pcd1, pcd2 = load_point_clouds(pcd_path_1, pcd_path_2)
pcd1_down = preprocess_point_cloud(pcd1, voxel_size)
pcd2_down = preprocess_point_cloud(pcd2, voxel_size)

# Perform ICP
icp_result = icp_registration(pcd1_down, pcd2_down, voxel_size)
print("ICP transformation matrix:\n", icp_result.transformation)

# Visualize the aligned point clouds
# Apply the ICP transformation to the original point cloud
pcd1.transform(icp_result.transformation)
o3d.visualization.draw_geometries([pcd1, pcd2], window_name="ICP Registration Result")
