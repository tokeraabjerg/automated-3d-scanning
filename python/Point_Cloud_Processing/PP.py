import open3d as o3d
import numpy as np
from Normal_space_downsampling import downsample_normal_space



    # Preproces: Downsize, Remove outliers, Find normals, Find features:
def preprocess_point_cloud(pcd, resolution):
    #print(":: Rand Downsample with a resolution %.3f." % resolution)
    #pcd_rand=pcd.random_down_sample(0.005*resolution)
    #print(len(pcd_rand.points))
    #o3d.visualization.draw_geometries([pcd_rand], window_name="rand Cloud")
    print(":: Voxel Downsample with a resolution %.3f." % resolution)
    pcd_voxel=pcd.voxel_down_sample(1/resolution)
    print(f"PCD vox has {len(pcd_voxel.points)} points")
    # o3d.visualization.draw_geometries([pcd_voxel], window_name="Vox Cloud")
    
    
    # Remove statistical outliers
    print(":: Statistically remove outliers.")
    pcd_voxel, ind = pcd_voxel.remove_statistical_outlier(nb_neighbors=int(100*resolution), std_ratio=0.5, print_progress=True)
    #o3d.visualization.draw_geometries([pcd_voxel], window_name="vox Cloud")
    
    #pcd_voxel.estimate_normals(
    #    o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=30))

    # Downsample using normal space sampling
    pcd_normal = downsample_normal_space(pcd_voxel, num_samples=int(40000), resolution=resolution)
    # print(pcd_normal.has_normals()) True
    #o3d.visualization.draw_geometries([pcd_normal], window_name="Normal Cloud")
    return pcd_normal, pcd_voxel

