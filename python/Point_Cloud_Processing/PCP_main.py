import open3d as o3d
import numpy as np
import logging  # Add logging import
import time
import getpass

# Define your username
your_username = "not" #"mikke"

# Check if the current user is you
if getpass.getuser() == your_username:
    print("The code is being without modules")
    from IA import RANSAC_initial_alignment
    from ICP import Point_to_Plane, legacy_icp_with_logging, Point_to_Plane_with_Normal_Check
    from Misc_functions import create_arrow, decompose_transformation, remove_points_within_distance_of_pointcloud, sample_adjacent_point_pairs
    from PP import preprocess_point_cloud, Preproces_pipeline, Preproces_normal_pipeline, Preproces_early_outliers_pipeline
    from Calibration_by_fixture import Calibration_by_fixture, remove_points_in_box
else:
    print("The code is being run with modules")
    from .IA import RANSAC_initial_alignment
    from .ICP import Point_to_Plane, legacy_icp_with_logging, Point_to_Plane_with_Normal_Check
    from .Misc_functions import create_arrow, decompose_transformation, remove_points_within_distance_of_pointcloud, sample_adjacent_point_pairs
    from .PP import preprocess_point_cloud, Preproces_pipeline, Preproces_normal_pipeline, Preproces_early_outliers_pipeline
    from .Calibration_by_fixture import Calibration_by_fixture, remove_points_in_box

#define global variables in global scope, tsk tsk.
ShowMe = False
legacyMode = False
doInitial_alignment = True
doICP = False
Preprocessing_pipeline = "Standard"
# options = "Standard", "Early_outliers_NSS" and "NSS"

# Initialize logger
logger = logging.getLogger(__name__)


def Point_Cloud_Processing(combined_cloud, target_cloud, theta_pan, theta_tilt, Calibration_transformation, voxel_size=0.01, max_correspondence_distance=2, preprocessing_method="Standard"):
    logger.info("Starting Point_Cloud_Processing")

    """
    Process a list of point clouds by registering and merging them iteratively.
    
    Parameters:
    - Combined_cloud: The initial point cloud, and the point cloud to which the other point clouds are registered.
    - target_cloud: The point cloud to be registered to the combined_cloud.
    - theta_pan: The pan angle of the target_cloud (motor A?).
    - theta_tilt: The tilt angle of the target_cloud. (motor B?).
    - zero_transform: The transformation matrix to zero the point clouds.
    - voxel_size: Voxel size for downsampling.
    - max_correspondence_distance: Max distance for point correspondence during ICP.

    Returns:
    - combined_cloud: The final merged point cloud.
    """

    # Visual aide for the axis of rotation
    """
    arrows = [
    create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
    ]
    AxisArrow = o3d.geometry.TriangleMesh()
    for arrow in arrows:
        AxisArrow += arrow
    """
    # Paint the target cloud
    # target_cloud.paint_uniform_color([1, 0.706, 0])
    # logger.debug("Target cloud painted")

    # Apply Calibration transformation to the target cloud
    target_cloud.transform(Calibration_transformation)
    logger.info("Applied calibration transformation to target cloud")
    
    
    # Preproces: Downsize, Find normals, downsample in normal space, remove outliers:
    if preprocessing_method == "Standard":
        logger.debug("Selecting Preproces_pipeline")
        def Preproces(target_cloud, voxel_size, std_ratio):
            target_cloud = Preproces_pipeline(target_cloud, voxel_size, std_ratio)
            return target_cloud
    elif preprocessing_method == "Early_outliers_NSS":
        logger.debug("Selecting Early_outliers_NSS")
        def Preproces(target_cloud, voxel_size, std_ratio):
            target_cloud = Preproces_early_outliers_pipeline(target_cloud, voxel_size, std_ratio)
            return target_cloud
    elif preprocessing_method == "NSS":
        logger.debug("Starting Preproces_normal_pipeline")
        def Preproces(target_cloud, voxel_size, std_ratio):
            target_cloud = Preproces_normal_pipeline(target_cloud, voxel_size, std_ratio)
            return target_cloud
    else:
        raise ValueError("Invalid Preprocessing_pipeline option")


    logger.debug("Starting Preproces")
    target_cloud_normal_sample = Preproces(target_cloud, voxel_size, std_ratio=2.0)
    if not target_cloud_normal_sample.has_normals():
        logger.info("Target lost normals after preprocessing")
    
    # Ensure normals are computed for the combined cloud (Toke)
    if not combined_cloud.has_normals():
        logger.info("Estimating normals for combined_cloud and applying calibration transformation")
        combined_cloud.transform(Calibration_transformation)
        combined_cloud = Preproces(combined_cloud, voxel_size, std_ratio=2.0) 

    if not target_cloud_normal_sample.has_normals():
        logger.info("Target lost normals COMBINED preprocessing")
    if not combined_cloud.has_normals():
        logger.info("Combined lost normals after preprocessing")
    
    logger.debug("Normals estimated for combined_cloud_normal_sample")

    logger.debug(f"Angles received in Point_Cloud_Processing: theta_pan_diff={theta_pan}, theta_tilt_diff={theta_tilt}")

    if doInitial_alignment is False:
        logger.info("Skipping alignment")
    else:
        if ShowMe is True:
            o3d.visualization.draw_geometries([combined_cloud, target_cloud_normal_sample, AxisArrow], window_name="Unrotated Point Cloud")
        initial_rotation = o3d.geometry.PointCloud.get_rotation_matrix_from_yxz((np.radians(theta_tilt), np.radians(theta_pan), np.radians(0)))
        logger.debug(f"Initial rotation matrix: {initial_rotation}")
        target_cloud_normal_sample.rotate(initial_rotation, center=(0, 0, 0))
        logger.debug("Rotated target cloud")
        if ShowMe is True:
            o3d.visualization.draw_geometries([combined_cloud, target_cloud_normal_sample, AxisArrow], window_name="Rotated Point Cloud")
        
    # Step 2: Point-to-Plane ICP
    if doICP is False:
        logger.info("Skipping ICP")
        icp_transformation = np.eye(4)
        aligned_target = target_cloud_normal_sample
    else:
        logger.debug("Performing ICP registration...")
        icp_transformation, aligned_target = Point_to_Plane(combined_cloud, target_cloud_normal_sample, max_correspondence_distance)
        logger.info(f"ICP transformation matrix: {icp_transformation}")

    combined_cloud += aligned_target
    logger.debug("ICP registration completed")

    # Optional: Visualize the current merged cloud
    if ShowMe is True:
        o3d.visualization.draw_geometries([combined_cloud, AxisArrow], window_name="Current cloud merged")

    logger.info("Point_Cloud_Processing completed")

    return combined_cloud, icp_transformation

# Example Usage, as in Tokes code
if __name__ == "__main__":
    # List of .ply files to process
    
    # Todo: Scaling of the point clouds
    # Play with the resulting cloud:

    # test_cloud = o3d.io.read_point_cloud(r"C:\Users\mikke\automated-3d-scanning\merged_point_cloud_tester1.ply")
    #test_cloud, ind = test_cloud.remove_statistical_outlier(nb_neighbors=10, std_ratio=0.1)
    #test_cloud, ind = test_cloud.remove_statistical_outlier(nb_neighbors=60, std_ratio=0.5)
    #o3d.visualization.draw_geometries([test_cloud], window_name="Test Cloud")
    

    Calibration_known = False
    arrows = [
    create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
    ]
    AxisArrow = o3d.geometry.TriangleMesh()
    for arrow in arrows:
        AxisArrow += arrow
    ply_files = [
        r"C:\Users\mikke\Desktop\40pct_15scans\40pct_15scans\scan_1.ply",
        r"C:\Users\mikke\Desktop\40pct_15scans\40pct_15scans\scan_2.ply",
        r"C:\Users\mikke\Desktop\40pct_15scans\40pct_15scans\scan_3.ply",
        r"C:\Users\mikke\Desktop\40pct_15scans\40pct_15scans\scan_4.ply"
        #r"C:\Users\mikke\Desktop\40pct_15scans\40pct_15scans\scan_5.ply",
        #r"C:\Users\mikke\Desktop\40pct_15scans\40pct_15scans\scan_6.ply",
        #r"C:\Users\mikke\Desktop\40pct_15scans\40pct_15scans\scan_7.ply",
        #r"C:\Users\mikke\Desktop\40pct_15scans\40pct_15scans\scan_8.ply",
        #r"C:\Users\mikke\Desktop\mikkel\mikkel\motor_b_+15.ply",
        #r"C:\Users\mikke\Desktop\mikkel\mikkel\motor_b_-15.ply" # Appears to be 0, 0
    ]
    
    theta_pan = [0, 20, 40, 60, 0]
    theta_tilt = [0, 0, 0, 0, 0]

    # #illustrate the first cloud:
    # cloud = o3d.io.read_point_cloud(ply_files[0])
    # o3d.visualization.draw_geometries([cloud, AxisArrow], window_name="First Point Cloud")
    # cloud = remove_points_in_box(cloud, (-1000.0, -1000, -10), (1000, 1000, 10))
    # #TODO: Implement this function or a version of it at scan level - maybe next to origen points?
    # o3d.visualization.draw_geometries([cloud, AxisArrow], window_name="First Point Cloud")
    

    ShowMe = True
    legacyMode = False
    

    
    # Initialize combined_transformation as a list of independent identity matrices
    # combined_transformation = [np.eye(4) for _ in range(len(ply_files))]
    
    # Initialize the combined point cloud
    combined_cloud = None

    start_timePCP = time.time()

    for i in range(0, len(ply_files)):
        print(f"Processing point cloud {i+1}/{len(ply_files)}...")
        
        current_cloud = o3d.io.read_point_cloud(ply_files[i])
        if Calibration_known is False:
            if theta_pan[i] == 0 and theta_tilt[i] == 0:
                print("Finding calibration by fixture-based method")
                Alignment_point_cloud = current_cloud
                Morm, Alignment_point_cloud = preprocess_point_cloud(current_cloud, resolution=1, std_ratio=0.5) 
                Fikstur_fil=r"C:\Users\mikke\OneDrive - Aalborg Universitet\CAD\Fiktur.ply"
                Calibration_transformation, Fikstur = Calibration_by_fixture(Alignment_point_cloud, Fikstur_fil)  
                print("Calibration transformation found:")
                print(Calibration_transformation)
                Calibration_known = True
            else:
                raise ValueError("lacking calibration point cloud")
        
        logger.info("Removing points around the scanner")
        current_cloud = remove_points_in_box(current_cloud, (-1000.0, -1000, -10), (1000, 1000, 10))
        # TODO: Implement this function or a version of it at scan level - maybe next to origen points?
        

        if legacyMode is True:
            combined_cloud, combined_transformation = Legacy_process_point_clouds(ply_files, theta_pan, theta_tilt, Calibration_transformation, voxel_size=0.5, max_correspondence_distance=4)
        
        elif combined_cloud == None:
            o3d.visualization.draw_geometries([current_cloud, AxisArrow, Fikstur], window_name="First Point Cloud")
            current_cloud.transform(Calibration_transformation)
            combined_cloud = Preproces_normal_pipeline(current_cloud, voxel_size=0.5, std_ratio=2)
            if ShowMe is True:
                o3d.visualization.draw_geometries([combined_cloud, AxisArrow, Fikstur], window_name="First Point Cloud post calibration")
        else:
            o3d.visualization.draw_geometries([combined_cloud, current_cloud, AxisArrow, Fikstur], window_name="Current Point Cloud, before processing and calibration")
            combined_cloud, ICP_transform = Point_Cloud_Processing(combined_cloud, current_cloud, theta_pan[i], theta_tilt[i], Calibration_transformation, voxel_size=0.01, max_correspondence_distance=1)
    
    combined_cloud = remove_points_within_distance_of_pointcloud(combined_cloud, Fikstur, 2) 
    min_bound = (-120.0, -200.0, -100)  # Replace with your box's minimum x, y, and z coordinates
    max_bound = (50, 200, 100) 
    combined_cloud = remove_points_in_box(combined_cloud, min_bound, max_bound)
    
    end_timePCP = time.time()
    elapsed_timePCP = end_timePCP - start_timePCP
    print(f"Time taken by PCP: {elapsed_timePCP:.2f} seconds")   

    o3d.visualization.draw_geometries([combined_cloud, AxisArrow], window_name="Proccesed Point Clouds")
    # Save the final merged point cloud
    output_ply = "merged_point_cloud_tester1.ply"
    #     output_trans = "combined_transformation.json"
    o3d.io.write_point_cloud(output_ply, combined_cloud)
    #print(f"Final merged point cloud saved to: {output_file}")
