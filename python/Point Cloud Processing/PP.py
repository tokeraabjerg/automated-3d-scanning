import open3d as o3d
from Normal_space_downsampling import downsample_normal_space
    # Preproces: Downsize, Remove outliers, Find normals, Find features:
def preprocess_point_cloud(pcd, voxel_size):
    print(":: Downsample with a voxel size %.3f." % voxel_size)
    # Downsize...
    pcd_voxel = pcd.voxel_down_sample(voxel_size)
    
    # Remove statistical outliers
    pcd_voxel, ind = pcd_voxel.remove_statistical_outlier(nb_neighbors=int(150//voxel_size), std_ratio=0.5)

    # Estimate normal
    radius_normal = voxel_size * 2
    print(":: Estimate normal with search radius %.3f." % radius_normal)
    pcd_voxel.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=30))

    # Find Features
    radius_feature = voxel_size * 5
    print(":: Compute FPFH feature with search radius %.3f." % radius_feature)
    pcd_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        pcd_voxel,
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius_feature, max_nn=100))
    
    # Downsample using normal space sampling
    pcd_down = downsample_normal_space(pcd_voxel, num_samples=int(30000/voxel_size), voxel_size=voxel_size)

    return pcd_down, pcd_fpfh, pcd_voxel

