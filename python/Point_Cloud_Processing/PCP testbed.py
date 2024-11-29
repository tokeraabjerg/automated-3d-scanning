import open3d as o3d
import numpy as np
from IA import RANSAC_initial_alignment, rotate_point_cloud, execute_global_registration
from ICP import Point_to_Plane, legacy_icp_with_logging, Point_to_Plane_with_Normal_Check
from Misc_functions import compute_bounding_box, create_arrow, extract_rotation_axis_and_angle, decompose_transformation, remove_small_clusters, remove_points_within_distance_of_pointcloud
from PP import preprocess_point_cloud
from Calibration_by_fixture import Calibration_by_fixture

def Point_Cloud_Processing(combined_cloud, target_cloud, theta_pan, theta_tilt, Calibration_transformation, voxel_size, mcd=4):
    """
    Process a list of point clouds by registering and merging them iteratively.
    
    Parameters:
    - Combined_cloud: The initial point cloud, and the point cloud to which the other point clouds are registered.
    - target_cloud: The point cloud to be registered to the combined_cloud.
    - theta_pan: The pan angle of the target_cloud.
    - theta_tilt: The tilt angle of the target_cloud.
    - zero_transform: The transformation matrix to zero the point clouds.
    - voxel_size: Voxel size for downsampling.
    - max_correspondence_distance: Max distance for point correspondence during ICP.

    Returns:
    - combined_cloud: The final merged point cloud.
    """

    # Visual aide for the axis of rotation

    arrows = [
    create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
    ]
    AxisArrow = o3d.geometry.TriangleMesh()
    for arrow in arrows:
        AxisArrow += arrow


    # Preproces: Downsize, Remove outliers, Find normals
    combined_cloud, combined_voxel = preprocess_point_cloud(combined_cloud, voxel_size)
    combined_cloud.transform(Calibration_transformation)

    # downsampled_pcd = downsample_normal_space(combined_cloud, num_samples=int(30000/voxel_size), voxel_size=voxel_size)

    # Visualize the downsampled point cloud
    
    o3d.visualization.draw_geometries([combined_voxel, AxisArrow], window_name="Preproccesed Point Cloud")
    # Beregn bounding box, størrelse af pooint cloud

    #    combined_cloud = remove_small_clusters(combined_cloud, 1000/voxel_size, eps=0.1e-100)
    #    o3d.visualization.draw_geometries([combined_cloud], window_name="Clusters removed")

    
        target_cloud, target_voxel = preprocess_point_cloud(target_cloud, voxel_size)
        

        target_cloud.paint_uniform_color([1, 0.706, 0])

        if theta_pan == 0 and theta_tilt == 0:
            print("Nice job idiot, you forgot to turn on the motor")
        else:
            # unrotated_target_center = np.mean(np.asarray(target_cloud.points), axis=0)
            o3d.visualization.draw_geometries([combined_cloud, target_cloud, AxisArrow], window_name="Unrotated Point Cloud")
            initial_rotation = o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(theta_pan), np.radians(theta_tilt), np.radians(rotation_vectors[i][2])))
            print(initial_rotation)
            target_cloud.rotate(initial_rotation, center=(0,0,0))
            o3d.visualization.draw_geometries([combined_cloud, target_cloud, AxisArrow], window_name="Rotated Point Cloud")
            # target_center = np.mean(np.asarray(target_cloud.points), axis=0)
            # For now, translation by densitity alignment is not implimented
            # translation_vector=combined_center-target_center
            # translation_vector=unrotated_target_center-target_center
            translation_vector=(0,0,0)
            target_cloud.translate(translation_vector)
            #o3d.visualization.draw_geometries([combined_cloud, target_cloud], window_name="Translated Point Cloud")
            
            int_rot_4x4=np.eye(4)
            int_rot_4x4[:3, :3] = initial_rotation 
            translation_matrix = np.eye(4)
            translation_matrix[:3, 3] = translation_vector 
            initial_transformation=np.dot(translation_matrix, int_rot_4x4)    


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
        # Initialize the array containing all ICP transformaitons - outdated, no need when only the combined transformation is stored.
        # icp_transformation = [None] * len(ply_files)

        icp_transformation, aligned_target=legacy_icp_with_logging(combined_cloud, target_cloud, mcd)
        # aligned_target=target_cloud.transform(icp_transformation)
        # icp_transformation[i], aligned_target = Point_to_Plane(combined_cloud, target_cloud, mcd)

        # Initialize combined_transformation as a list of independent identity matrices
        combined_transformation = [np.eye(4) for _ in range(len(ply_files))]

        # Combine transformations for the i-th transformation
        # TODO: Add zero transformation to the combined transformation
        combined_transformation[i] = np.dot(icp_transformation, initial_transformation)
        # Decompose the transformation and print results
        result = decompose_transformation(combined_transformation[i])
        print(f"PC nr {i} was transformed by:")
        print("Translation (x, y, z):", result["translation"])
        print("Rotation (roll, pitch, yaw) in degrees:", result["rotation"])


        combined_cloud += aligned_target

        # Anvend den samlede transformation på den højere opløsnings punktsky
        aligned_voxel = target_voxel.transform(combined_transformation[i])
        combined_voxel += aligned_voxel
        
        # R=combined_transformation[i][:3, :3]
        # print('LOOK HERE')
        # print(R)
        # axis, angle = extract_rotation_axis_and_angle(R)
        # print("Rotation Axis:", axis)
        # print("Rotation Angle (degrees):", np.degrees(angle))

        # Optional: Visualize the current merged cloud
        o3d.visualization.draw_geometries([combined_cloud], window_name="Merged Point Cloud")
        o3d.visualization.draw_geometries([combined_voxel], window_name="Merged Point Cloud voxel")

    return combined_voxel, combined_transformation



#     ply_files = [
#         r"C:\Users\mikke\Desktop\bunny\data\bun000.ply",
#         r"C:\Users\mikke\Desktop\bunny\data\bun045.ply",
#         r"C:\Users\mikke\Desktop\bunny\data\bun090.ply"
#         #r"C:\Users\mikke\Desktop\bunny\data\bun315.ply"
#         #r"C:\Users\mikke\Desktop\bunny\data\bun270.ply"
#     ]

# Example Usage, as in Tokes code
if __name__ == "__main__":
    # List of .ply files to process
    ply_files = [
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\0 grader test 2.ply",
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\15 grader test 2.ply",
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\45 grader test 2.ply"
    ]
    Calibration_known = False
    for i in range(1, len(ply_files)):
        print(f"Processing point cloud {i + 1}/{len(ply_files)}...")
        
        current_cloud = o3d.io.read_point_cloud(ply_files[i])
        theta_pan = 0
        theta_tilt = 0


        if Calibration_known is False:
            if theta_pan == 0 and theta_tilt == 0:
                print("Finding calibration by fixture-based method")
                Alignment_point_cloud = current_cloud
                Fikstur_fil=r"C:\Users\mikke\OneDrive - Aalborg Universitet\CAD\Fiktur.ply"
                Calibration_transformation = Calibration_by_fixture(Alignment_point_cloud, Fikstur_fil)  
                Calibration_known = True
            else:
                raise ValueError("lacking calibration point cloud")
            

        try:
            combined_cloud
        except NameError:
            combined_cloud = preprocess_point_cloud(current_cloud, resolution=1, std_ratio=0.5)
        else:
            combined_cloud, combined_transformation = Point_Cloud_Processing(combined_cloud, current_cloud, theta_pan, theta_tilt, Calibration_transformation, resolution=1, mcd=4)

    
"""
if __name__ == "__main__":
    # List of .ply files to process
    ply_files = [
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\0 grader test 2.ply",
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\15 grader test 2.ply",
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\45 grader test 2.ply"
    ]

    # Input vectors for inital rotation. Rotate a point cloud using Euler angles (roll, pitch, yaw) at a specified index.
    rotation_vectors = [
    #(None),    # Tom første indgang, "none" er eq. til ikke at kende rotationen.
    (0, 0, 0),     # Ingen rotation identificere en point cloud som værende velegnet til zeroing.
    (15, 0, 0),     # Rotation omkring en vilkårlig akse
    (45, 0, 0)    # 90 grader omkring y-aksen
    ]

    # Translation vectors to move from global to local coords. Must find a method of locating the motors axis of rotation.
    # Hard coded translation for the first axis of rotation (Not perfect, since data appears inconsistent)
    # Calculated x_axis=(143.31,24.85,-318.16)
    
    # Working x_axis=(143.31, 15,-340.16)
    # x_axis=(143.31, 15,-345)

    # Obtain zeroing transformation
    Fikstur_fil=r"C:\Users\mikke\OneDrive - Aalborg Universitet\CAD\Fiktur.ply"

    if rotation_vectors[0] == (0,0,0):
        print("Zeroing point clouds by fixture-based method")
        Alignment_point_cloud = o3d.io.read_point_cloud(ply_files[0])
    else:
        raise ValueError("lacking zeroing point cloud")
    
    Calibration_transformation, Fikstur=Zero_point_cloud_by_fixture(Alignment_point_cloud, Fikstur_fil)
    Calibration_transformation = np.eye(4)
    # Process the point clouds
    print("Starting point cloud processing...")
    final_cloud, combined_transformation = process_point_clouds(ply_files, rotation_vectors, Calibration_transformation, voxel_size=1.5, mcd=4)
    print(combined_transformation.shape)
    final_cloud_minus_fixture = remove_points_within_distance_of_pointcloud(Fikstur, final_cloud, 10)

    # Save the final merged point cloud
    output_ply = "merged_point_cloud.ply"
    output_trans = "combined_transformation.json"
    #o3d.io.write_point_cloud(output_file, final_cloud)
    #print(f"Final merged point cloud saved to: {output_file}")

    # Visualize the final result
    #o3d.visualization.draw_geometries([final_cloud], window_name="Final Merged Point Cloud")
"""

def Legacy_process_point_clouds(ply_files, rotation_vectors, zero_transform, voxel_size, mcd):
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
    # combined_cloud.translate(x_axis)
    combined_cloud, combined_voxel = preprocess_point_cloud(combined_cloud, voxel_size)
    combined_cloud.transform(Calibration_transformation)

    # downsampled_pcd = downsample_normal_space(combined_cloud, num_samples=int(30000/voxel_size), voxel_size=voxel_size)

    # Visualize the downsampled point cloud
    
    o3d.visualization.draw_geometries([combined_voxel, AxisArrow], window_name="Preproccesed Point Cloud")
    # Beregn bounding box, størrelse af pooint cloud

    #    combined_cloud = remove_small_clusters(combined_cloud, 1000/voxel_size, eps=0.1e-100)
    #    o3d.visualization.draw_geometries([combined_cloud], window_name="Clusters removed")

    for i in range(1, len(ply_files)):
        print(f"Processing point cloud {i + 1}/{len(ply_files)}...")

        # Load the next point cloud
        target_cloud = o3d.io.read_point_cloud(ply_files[i])
        target_cloud.transform(Calibration_transformation)
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
            # unrotated_target_center = np.mean(np.asarray(target_cloud.points), axis=0)
            o3d.visualization.draw_geometries([combined_cloud, target_cloud, AxisArrow], window_name="Unrotated Point Cloud")
            initial_rotation = o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(rotation_vectors[i][0]), np.radians(rotation_vectors[i][1]), np.radians(rotation_vectors[i][2])))
            print(initial_rotation)
            target_cloud.rotate(initial_rotation, center=(0,0,0))
            o3d.visualization.draw_geometries([combined_cloud, target_cloud, AxisArrow], window_name="Rotated Point Cloud")
            # target_center = np.mean(np.asarray(target_cloud.points), axis=0)
            # For now, translation by densitity alignment is not implimented
            # translation_vector=combined_center-target_center
            # translation_vector=unrotated_target_center-target_center
            translation_vector=(0,0,0)
            target_cloud.translate(translation_vector)
            #o3d.visualization.draw_geometries([combined_cloud, target_cloud], window_name="Translated Point Cloud")
            
            int_rot_4x4=np.eye(4)
            int_rot_4x4[:3, :3] = initial_rotation 
            translation_matrix = np.eye(4)
            translation_matrix[:3, 3] = translation_vector 
            initial_transformation=np.dot(translation_matrix, int_rot_4x4)    


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
        # Initialize the array containing all ICP transformaitons - outdated, no need when only the combined transformation is stored.
        # icp_transformation = [None] * len(ply_files)

        icp_transformation, aligned_target=legacy_icp_with_logging(combined_cloud, target_cloud, mcd)
        # aligned_target=target_cloud.transform(icp_transformation)
        # icp_transformation[i], aligned_target = Point_to_Plane(combined_cloud, target_cloud, mcd)

        # Initialize combined_transformation as a list of independent identity matrices
        combined_transformation = [np.eye(4) for _ in range(len(ply_files))]

        # Combine transformations for the i-th transformation
        # TODO: Add zero transformation to the combined transformation
        combined_transformation[i] = np.dot(icp_transformation, initial_transformation)
        # Decompose the transformation and print results
        result = decompose_transformation(combined_transformation[i])
        print(f"PC nr {i} was transformed by:")
        print("Translation (x, y, z):", result["translation"])
        print("Rotation (roll, pitch, yaw) in degrees:", result["rotation"])


        combined_cloud += aligned_target

        # Anvend den samlede transformation på den højere opløsnings punktsky
        aligned_voxel = target_voxel.transform(combined_transformation[i])
        combined_voxel += aligned_voxel
        
        # R=combined_transformation[i][:3, :3]
        # print('LOOK HERE')
        # print(R)
        # axis, angle = extract_rotation_axis_and_angle(R)
        # print("Rotation Axis:", axis)
        # print("Rotation Angle (degrees):", np.degrees(angle))

        # Optional: Visualize the current merged cloud
        o3d.visualization.draw_geometries([combined_cloud], window_name="Merged Point Cloud")
        o3d.visualization.draw_geometries([combined_voxel], window_name="Merged Point Cloud voxel")

    return combined_voxel, combined_transformation
