import open3d as o3d
import numpy as np
from IA import RANSAC_initial_alignment, rotate_point_cloud, execute_global_registration
from ICP import Point_to_Plane, legacy_icp_with_logging
from EE import calculate_error
from DT import decompose_transformation
from DB import remove_small_clusters
from Misc_functions import compute_bounding_box, create_arrow
from PP import preprocess_point_cloud
from Bin import extract_rotation_axis_and_angle

def process_point_clouds(ply_files, rotation_vectors, voxel_size, mcd):
    """
    Process a list of point clouds by registering and merging them iteratively.
    
    Parameters:
    - ply_files: List of paths to the point cloud files.
    - voxel_size: Voxel size for downsampling.
    - max_correspondence_distance: Max distance for point correspondence during ICP.

    Returns:
    - combined_cloud: The final merged point cloud.
    """
    if len(ply_files) < 2:
        raise ValueError("At least two point cloud files are required for registration.")
    
    # Load the first point cloud as the initial source
    combined_cloud = o3d.io.read_point_cloud(ply_files[0])

    arrows = [
    create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
    ]
    AxisArrow = o3d.geometry.TriangleMesh()
    for arrow in arrows:
        AxisArrow += arrow

    # Visualize
    # o3d.visualization.draw_geometries([AxisArrow])

    # Preproces: Downsize, Remove outliers, Find normals, Find features:
    # combined_cloud = combined_cloud.voxel_down_sample(voxel_size)
    combined_cloud.translate(x_axis)
    combined_cloud, combined_voxel = preprocess_point_cloud(combined_cloud, voxel_size)

    # Downsample using normal space sampling (now part of preprocess)
    # downsampled_pcd = downsample_normal_space(combined_cloud, num_samples=int(30000/voxel_size), voxel_size=voxel_size)

    # Visualize the downsampled point cloud
    
    o3d.visualization.draw_geometries([combined_voxel, AxisArrow], window_name="Preproccesed Point Cloud")
    # Beregn bounding box, størrelse af pooint cloud
    
    # min_bound, max_bound = compute_bounding_box(combined_cloud)

    # # Beregn størrelse af bounding box
    # bbox_size = max_bound - min_bound
    # print(f"Størrelse af bounding box: {bbox_size}")

#    combined_cloud = remove_small_clusters(combined_cloud, 1000/voxel_size, eps=0.1e-100)
#    o3d.visualization.draw_geometries([combined_cloud], window_name="Clusters removed")

    for i in range(1, len(ply_files)):
        print(f"Processing point cloud {i + 1}/{len(ply_files)}...")
        
        # Load the next point cloud
        target_cloud = o3d.io.read_point_cloud(ply_files[i])
        target_cloud.translate(x_axis)
        target_cloud, target_voxel = preprocess_point_cloud(target_cloud, voxel_size)
        

        target_cloud.paint_uniform_color([1, 0.706, 0])

        # Step 1: Initial alignment (RANSAC or other coarse alignment)
        # initial_transformation = [None] * len(ply_files) For storing initial transformations.
        if rotation_vectors[i] == (None):
            print("Performing RANSAC initial alignment...")
            initial_transformation = RANSAC_initial_alignment(combined_cloud, target_cloud)
            print("Initial alignment transformation applied:")
            print(initial_transformation)
            target_cloud.transform(initial_transformation)
            o3d.visualization.draw_geometries([combined_cloud, target_cloud], window_name="RANSAC'ed Point Cloud")
        else:
            unrotated_target_center = np.mean(np.asarray(target_cloud.points), axis=0)
            o3d.visualization.draw_geometries([combined_cloud, target_cloud, AxisArrow], window_name="Unrotated Point Cloud")
            initial_rotation=o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(x_rot[i]), 0, 0))
            print(initial_rotation)
            target_cloud.rotate(initial_rotation, center=(0,0,0))
            o3d.visualization.draw_geometries([combined_cloud, target_cloud, AxisArrow], window_name="Rotated Point Cloud")
            target_center = np.mean(np.asarray(target_cloud.points), axis=0)
            # translation_vector=combined_center-target_center
            translation_vector=unrotated_target_center-target_center
            translation_vector=(0,0,0)
            target_cloud.translate(translation_vector)
            #o3d.visualization.draw_geometries([combined_cloud, target_cloud], window_name="Translated Point Cloud")
            
            int_rot_4x4=np.eye(4)
            int_rot_4x4[:3, :3] = initial_rotation 
            translation_matrix = np.eye(4)
            translation_matrix[:3, 3] = translation_vector 
            initial_transformation=np.dot(translation_matrix, int_rot_4x4)    
            # result=execute_global_registration(combined_cloud, target_cloud, combined_fpfh, target_fpfh, voxel_size)
            # target_cloud.transform(result.transformation)
            # o3d.visualization.draw_geometries([combined_cloud, target_cloud], window_name="New RANSAC")
            # source_down, target_down, source_fpfh, target_fpfh, voxel_size


        result=decompose_transformation(initial_transformation)
        print("Translation (x, y, z):", result["translation"])
        print("Rotation (roll, pitch, yaw) in degrees:", result["rotation"])

        # Step 2: Point-to-Plane ICP
        # Estimating normals for source and target point clouds, som brugt i point to plane
        radius_normal = 2*voxel_size  # Radius til normal estimering
        combined_cloud.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=50)) 
        target_cloud.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=50))

        print("Performing ICP registration...")
        # Initialize the array containing all ICP transformaitons
        # icp_transformation = [None] * len(ply_files)
        icp_transformation, aligned_target=legacy_icp_with_logging(combined_cloud, target_cloud, mcd)
        # aligned_target=target_cloud.transform(icp_transformation)
        # icp_transformation[i], aligned_target = Point_to_Plane(combined_cloud, target_cloud, mcd)
        
        # Indsæt translationen i den sidste kolonne
        # Initialize combined_transformation as a list of independent identity matrices

        # Initialize combined_transformation as a list of independent identity matrices
        combined_transformation = [np.eye(4) for _ in range(len(ply_files))]

        # Combine transformations for the i-th transformation
        combined_transformation[i] = np.dot(icp_transformation, initial_transformation)
        # Decompose the transformation and print results
        result = decompose_transformation(combined_transformation[i])
        print(f"PC nr {i} was transformed by:")
        print("Translation (x, y, z):", result["translation"])
        print("Rotation (roll, pitch, yaw) in degrees:", result["rotation"])


        # Step 3: Calculate RMSE 
        # rmse_rating = calculate_error(combined_cloud, aligned_target)
        # print(f"RMSE rating: {rmse_rating}")

        # Step 4: Merge if RMSE is acceptable !! This needs to be updated in some way. 
        # I have yet to find an intelligent solution. 
        # Technically, I guess it should'nt be here, since the ICP script should have rejected it.
        #if rmse_rating < 50:
        combined_cloud += aligned_target
  #          combined_voxel += aligned_voxel
#            combined_cloud = combined_cloud.voxel_down_sample(voxel_size)
#            combined_cloud.paint_uniform_color([1, 0.706, 0])
       #print("Merge successful.")
        #else:
       #print("Merge failed. Skipping this cloud.")
            
        # Anvend den samlede transformation på punkt skyen
        aligned_voxel = target_voxel.transform(combined_transformation[i])
        combined_voxel += aligned_voxel
        
        R=combined_transformation[i][:3, :3]
        print('LOOK HERE')
        print(R)
        axis, angle = extract_rotation_axis_and_angle(R)
        print("Rotation Axis:", axis)
        print("Rotation Angle (degrees):", np.degrees(angle))
        # Optional: Visualize the current merged cloud
        o3d.visualization.draw_geometries([combined_cloud], window_name="Merged Point Cloud")
        o3d.visualization.draw_geometries([combined_voxel], window_name="Merged Point Cloud voxel")

    return combined_voxel



#     ply_files = [
#         r"C:\Users\mikke\Desktop\bunny\data\bun000.ply",
#         r"C:\Users\mikke\Desktop\bunny\data\bun045.ply",
#         r"C:\Users\mikke\Desktop\bunny\data\bun090.ply"
#         #r"C:\Users\mikke\Desktop\bunny\data\bun315.ply"
#         #r"C:\Users\mikke\Desktop\bunny\data\bun270.ply"
#     ]

if __name__ == "__main__":
    # List of .ply files to process
    ply_files = [
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\0 grader test 2.ply",
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\15 grader test 2.ply",
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\45 grader test 2.ply"
    ]

    rotation_vectors = [
    (None),    # Tom første indgang, "none" er eq. til ikke at kende rotationen.
    (15, 0, 0),     # Rotation omkring en vilkårlig akse
    (45, 0, 0)    # 90 grader omkring y-aksen
    ]
    x_rot = [
        None,
        15,
        45
    ]

    # Translation vectors to move from global to local coords. Must find a method of locating the motors axis of rotation.
    # Hard coded translation for the first axis of rotation (Not perfect, since data appears inconsistent)
    # x_axis=(143.31,24.85,-318.16)
    x_axis=(143.31, 15,-340.16)
    # Process the point clouds
    print("Starting point cloud processing...")
    final_cloud = process_point_clouds(ply_files, rotation_vectors, voxel_size=1.5, mcd=4)

    # Save the final merged point cloud
    output_file = "merged_point_cloud.ply"
    #o3d.io.write_point_cloud(output_file, final_cloud)
    #print(f"Final merged point cloud saved to: {output_file}")

    # Visualize the final result
    #o3d.visualization.draw_geometries([final_cloud], window_name="Final Merged Point Cloud")
