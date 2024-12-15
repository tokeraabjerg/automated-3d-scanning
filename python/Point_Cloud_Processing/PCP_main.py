import open3d as o3d
import numpy as np
import logging  # Add logging import
import time
import getpass
import json  # Add json import
import os  # Add os import

# Define your username
your_username = "mikke"

# Check if the current user is you
if getpass.getuser() == your_username:
    print("The code is being without modules")
    from ICP import Point_to_Plane, legacy_icp_with_logging, Point_to_Plane_with_Normal_Check
    from Misc_functions import create_arrow, decompose_transformation, remove_points_within_distance_of_pointcloud, sample_adjacent_point_pairs
    from PP import preprocess_point_cloud, Preproces_pipeline, Preproces_normal_pipeline, Preproces_early_outliers_pipeline, Preproces_normal_late_pipeline
    from Calibration_by_fixture import Calibration_by_fixture, remove_points_in_box
else:
    print("The code is being run with modules")
    from .ICP import Point_to_Plane, legacy_icp_with_logging, Point_to_Plane_with_Normal_Check
    from .Misc_functions import create_arrow, decompose_transformation, remove_points_within_distance_of_pointcloud, sample_adjacent_point_pairs
    from .PP import preprocess_point_cloud, Preproces_pipeline, Preproces_normal_pipeline, Preproces_early_outliers_pipeline
    from .Calibration_by_fixture import Calibration_by_fixture, remove_points_in_box

#define global variables in global scope, tsk tsk.
ShowMe = True
legacyMode = False
doInitial_alignment = True
doICP = True
Preprocessing_pipeline = "NSS"
# options = "Standard", "Early-outliers-NSS" and "NSS"

# Initialize logger
logger = logging.getLogger(__name__)


def Point_Cloud_Processing(combined_cloud, target_cloud, theta_pan, theta_tilt, Calibration_transformation, voxel_size=0.1, max_correspondence_distance=1, std=1,preprocessing_method="Standard", stdnn=20, Fikstur=None):
    logger.info("Starting Point_Cloud_Processing")

    if Fikstur is None:
        Fikstur = o3d.io.read_point_cloud(r"calibration\ref.ply")

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

    # Print the parameters:
    print(f"Parameters received in Point_Cloud_Processing: voxel_size={voxel_size}, max_correspondence_distance={max_correspondence_distance}, std={std}, preprocessing_method={preprocessing_method}")

    # Paint the target cloud
    # target_cloud.paint_uniform_color([1, 0.706, 0])
    # logger.debug("Target cloud painted")

    # Apply Calibration transformation to the target cloud
    target_cloud.transform(Calibration_transformation)
    logger.info("Applied calibration transformation to target cloud")
    
    
    # Preproces: Downsize, Find normals, downsample in normal space, remove outliers:
    if preprocessing_method == "Standard":
        logger.debug("Selecting Preproces_pipeline")
        def Preproces(target_cloud, voxel_size, std_ratio, stdnn):
            target_cloud = Preproces_pipeline(target_cloud, voxel_size, std_ratio, stdnn)
            return target_cloud
    elif preprocessing_method == "Early-outliers-NSS":
        logger.debug("Selecting Early-outliers-NSS")
        def Preproces(target_cloud, voxel_size, std_ratio, stdnn):
            target_cloud = Preproces_early_outliers_pipeline(target_cloud, voxel_size, std_ratio, stdnn)
            return target_cloud
    elif preprocessing_method == "NSS":
        logger.debug("Starting Preproces_normal_pipeline")
        def Preproces(target_cloud, voxel_size, std_ratio, stdnn):
            target_cloud = Preproces_normal_pipeline(target_cloud, voxel_size, std_ratio, stdnn)
            return target_cloud
    elif preprocessing_method == "NSS-late":
        logger.debug("Starting Preproces_normal_late_pipeline")
        def Preproces(target_cloud, voxel_size, std_ratio, stdnn):
            target_cloud = Preproces_normal_late_pipeline(target_cloud, voxel_size, std_ratio, stdnn)
            return target_cloud 
    else:
        raise ValueError("Invalid Preprocessing_pipeline option")



    logger.debug("Starting Preproces")
    target_cloud_normal_sample = Preproces(target_cloud, voxel_size, std_ratio=std, stdnn=stdnn)
    if not target_cloud_normal_sample.has_normals():
        logger.info("Target lost normals after preprocessing")
    
    # Ensure normals are computed for the combined cloud (Toke)
    if not combined_cloud.has_normals():
        if ShowMe is True:
            o3d.visualization.draw_geometries([current_cloud, AxisArrow, Fikstur], window_name="First Point Cloud")
        logger.info("Estimating normals for combined_cloud and applying calibration transformation")
        combined_cloud.transform(Calibration_transformation)
        combined_cloud = Preproces(combined_cloud, voxel_size, std_ratio=std, stdnn=stdnn)
        # TODO: Test white dataset without fikstur!
        # TODO: Add a step to perform initial alignment of the combined cloud, if applicable.
        combined_cloud += Fikstur
        if ShowMe is True:
                o3d.visualization.draw_geometries([combined_cloud, AxisArrow, Fikstur], window_name="First Point Cloud post calibration")

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
    
    logger.info("voxeldownsampling the combined cloud post registration")
    combined_cloud = combined_cloud.voxel_down_sample(voxel_size=voxel_size)
    # Optional: Visualize the current merged cloud
    if ShowMe is True:
        o3d.visualization.draw_geometries([combined_cloud, AxisArrow], window_name="Current cloud merged")

    logger.info("Point_Cloud_Processing completed")

    return combined_cloud, icp_transformation


# Function to get the next available filename
def get_next_filename(base_path, base_name, extension):
    index = 1
    while os.path.exists(f"{base_path}/{base_name}_{index}.{extension}"):
        index += 1
    return f"{base_path}/{base_name}_{index}.{extension}"

# Example Usage, as in Tokes code
if __name__ == "__main__":
    # List of .ply files to process

    Calibration_known = False
    arrows = [
    create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
    ]
    AxisArrow = o3d.geometry.TriangleMesh()
    for arrow in arrows:
        AxisArrow += arrow





    #test_cloud = o3d.io.read_point_cloud(r"merged_point_cloud_white.ply")
    #test_cloud, ind = test_cloud.remove_statistical_outlier(nb_neighbors=10, std_ratio=0.1)
    #test_cloud, ind = test_cloud.remove_statistical_outlier(nb_neighbors=60, std_ratio=0.5)
    #o3d.visualization.draw_geometries([test_cloud], window_name="Test Cloud")
    #min_bound = (-120.0, -200.0, -15)  # Replace with your box's minimum x, y, and z coordinates
    #max_bound = (100, 200, 100) 
    #test_cloud = remove_points_in_box(test_cloud, min_bound, max_bound)
    
    #test_cloud = test_cloud.voxel_down_sample(voxel_size=0.1)
    

    #ind = test_cloud.cluster_dbscan(eps=2, min_points=200, print_progress=True)
    #test_cloud = test_cloud.select_by_index([i for i, label in enumerate(ind) if label != -1])
    #test_cloud, ind = test_cloud.remove_statistical_outlier(nb_neighbors=10, std_ratio=1)
    #o3d.visualization.draw_geometries([test_cloud, AxisArrow], window_name="Test Cloud")
    


    ply_files = [
        r"scanner_interface\output\sort-fikstur-0.1-contrast-filter\scan_1.ply",
        r"scanner_interface\output\sort-fikstur-0.1-contrast-filter\scan_2.ply",
        r"scanner_interface\output\sort-fikstur-0.1-contrast-filter\scan_3.ply",
        r"scanner_interface\output\sort-fikstur-0.1-contrast-filter\editednr4.ply",
        r"scanner_interface\output\sort-fikstur-0.1-contrast-filter\scan_5.ply",
        r"scanner_interface\output\sort-fikstur-0.1-contrast-filter\scan_7.ply",
        r"scanner_interface\output\sort-fikstur-0.1-contrast-filter\scan_8reflectfree.ply",
        r"scanner_interface\output\sort-fikstur-0.1-contrast-filter\scan_6.ply"
        #r"C:\Users\mikke\Desktop\40pct_15scans\40pct_15scans\scan_5.ply",
        #r"C:\Users\mikke\Desktop\40pct_15scans\40pct_15scans\scan_6.ply",
        #r"C:\Users\mikke\Desktop\40pct_15scans\40pct_15scans\scan_7.ply",
        #r"C:\Users\mikke\Desktop\40pct_15scans\40pct_15scans\scan_8.ply",
        #r"C:\Users\mikke\Desktop\mikkel\mikkel\motor_b_+15.ply",
        #r"C:\Users\mikke\Desktop\mikkel\mikkel\motor_b_-15.ply" # Appears to be 0, 0
    ]

    theta_pan = [0, 0, 0, 0, 45, -45, -130, 145.03]
    theta_tilt = [0, -25.03, -14.97, 20, 0, 0, 0, 0]
    ShowMe = False
    legacyMode = False
    doInitial_alignment = True
    doICP = True

    
    input_values = [
        {"Method": "Standard", "std": 1, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
    ]
    
    for values in input_values:
        Method = values["Method"]
        std = values["std"]
        stdnn = values["stdnn"]
        voxel_size = values["voxel_size"]
        mcd = values["mcd"]

        # Initialize combined_transformation as a list of independent identity matrices
        # combined_transformation = [np.eye(4) for _ in range(len(ply_files))]

        # Initialize the combined point cloud
        combined_cloud = None

        # Initialize list to store ICP transformations
        icp_transformations = []

        start_timePCP = time.time()

        for i in range(0, len(ply_files)):
            print(f"Processing point cloud {i+1}/{len(ply_files)}...")

            current_cloud = o3d.io.read_point_cloud(ply_files[i])
            # current_cloud.scale(1, center=(0, 0, 0))
            if Calibration_known is False:
                if theta_pan[i] == 0 and theta_tilt[i] == 0:
                    print("Finding calibration by fixture-based method")
                    Alignment_point_cloud = current_cloud
                    Norm, Alignment_point_cloud = preprocess_point_cloud(current_cloud, resolution=1, std_ratio=0.5)
                    Fikstur_fil = r"C:\Users\mikke\OneDrive - Aalborg Universitet\CAD\Fiktur.ply"
                    Calibration_transformation, Fikstur = Calibration_by_fixture(Alignment_point_cloud, Fikstur_fil)
                    if ShowMe is True:
                        current_cloud = o3d.io.read_point_cloud(ply_files[i])
                        current_cloud.transform(Calibration_transformation)
                        o3d.visualization.draw_geometries([Alignment_point_cloud, Fikstur, AxisArrow], window_name="Alignment Point Cloud")
                    print("Calibration transformation found:")
                    print(Calibration_transformation)
                    Calibration_known = True
                else:
                    raise ValueError("lacking calibration point cloud")

            logger.info("Removing points around the scanner")
            current_cloud = remove_points_in_box(current_cloud, (-1000.0, -1000, -10), (1000, 1000, 10))
            # TODO: Implement this function or a version of it at scan level - maybe next to origen points?

            if legacyMode is True:
                combined_cloud, combined_transformation = Legacy_process_point_clouds(ply_files, theta_pan, theta_tilt, Calibration_transformation, voxel_size=voxel_size, max_correspondence_distance=4)
            elif combined_cloud == None:
                combined_cloud = current_cloud  # .transform(Calibration_transformation)
            else:
                if ShowMe is True:
                    o3d.visualization.draw_geometries([combined_cloud, current_cloud, AxisArrow, Fikstur], window_name="Current Point Cloud, before processing and calibration")
                combined_cloud, ICP_transform = Point_Cloud_Processing(combined_cloud, current_cloud, theta_pan[i], theta_tilt[i], Calibration_transformation, voxel_size=voxel_size, max_correspondence_distance=mcd, std=std, preprocessing_method=Method, stdnn=stdnn, Fikstur=Fikstur)
                icp_transformations.append(ICP_transform.tolist())  # Store the ICP transformation

        combined_cloud = remove_points_within_distance_of_pointcloud(combined_cloud, Fikstur, 2)
        min_bound = (-120.0, -200.0, -15)  # Replace with your box's minimum x, y, and z coordinates
        max_bound = (100, 200, 100)
        combined_cloud = remove_points_in_box(combined_cloud, min_bound, max_bound)
        min_bound = (-120.0, -200.0, -200)  # Replace with your box's minimum x, y, and z coordinates
        max_bound = (50, 200, 200)
        combined_cloud = remove_points_in_box(combined_cloud, min_bound, max_bound)

        # TODO. Implement this function in Standard? Test it.
        # if Method == "NSS-late":
        #     logger.debug("Starting outlier removal")
        #     combined_cloud, ind = combined_cloud.remove_statistical_outlier(nb_neighbors=stdnn, std_ratio=std)
        #     logger.info(f"Outlier removal completed, points count: {len(combined_cloud.points)}")
        # o3d.visualization.draw_geometries([combined_cloud, AxisArrow], window_name="Proccesed Point Clouds")
        
        end_timePCP = time.time()
        elapsed_timePCP = end_timePCP - start_timePCP
        print(f"Time taken by PCP: {elapsed_timePCP:.2f} seconds")

        # o3d.visualization.draw_geometries([combined_cloud, AxisArrow], window_name="Proccesed Point Clouds")
        # Save the final merged point cloud
        base_path = "scanner_interface/output/sort-fikstur-0.1-contrast-filter"
        output_ply_filename = get_next_filename(base_path, f"Black01_{Method}_{std}_{stdnn}_{voxel_size}_{mcd}", "ply")
        o3d.io.write_point_cloud(output_ply_filename, combined_cloud)
        print(f"Final merged point cloud saved to: {output_ply_filename}")

        # Save the ICP transformations to a JSON file
        icp_json_filename = get_next_filename(base_path, f"icp_transformations_{Method}_{std}_{stdnn}_{voxel_size}_{mcd}", "json")
        with open(icp_json_filename, 'w') as f:
            json.dump({"icp_transformations": icp_transformations, "elapsed_timePCP": elapsed_timePCP}, f, indent=4)
        print(f"ICP transformations saved to: {icp_json_filename}")
"""
    # Define the list of input values
    # redo these for black01, after removing the artefact/reaqureing scan 8:
    tested_input_values = [
        {"Method": "Standard", "std": 0.5, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
        {"Method": "NSS", "std": 0.5, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
        {"Method": "Standard", "std": 0.5, "voxel_size": 0.1, "mcd": 2, "stdnn": 20},
        {"Method": "NSS", "std": 0.5, "voxel_size": 0.1, "mcd": 2, "stdnn": 20},
        {"Method": "Standard", "std": 0.5, "voxel_size": 0.5, "mcd": 1, "stdnn": 20},
        {"Method": "NSS", "std": 0.5, "voxel_size": 0.5, "mcd": 1, "stdnn": 20},
        {"Method": "Standard", "std": 0.5, "voxel_size": 0.5, "mcd": 2, "stdnn": 20},
        {"Method": "NSS", "std": 0.5, "voxel_size": 0.5, "mcd": 2, "stdnn": 20},
        {"Method": "Standard", "std": 1, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
        {"Method": "NSS", "std": 1, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
        {"Method": "Standard", "std": 1, "voxel_size": 0.1, "mcd": 2, "stdnn": 20},
        {"Method": "NSS", "std": 1, "voxel_size": 0.1, "mcd": 2, "stdnn": 20},
        {"Method": "Standard", "std": 1, "voxel_size": 0.5, "mcd": 1, "stdnn": 20},
        {"Method": "NSS", "std": 1, "voxel_size": 0.5, "mcd": 1, "stdnn": 20},
        {"Method": "Standard", "std": 1, "voxel_size": 0.5, "mcd": 2, "stdnn": 20},
        {"Method": "NSS", "std": 1, "voxel_size": 0.5, "mcd": 2, "stdnn": 20},
        {"Method": "Standard", "std": 2, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
        {"Method": "NSS", "std": 2, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
        {"Method": "Standard", "std": 2, "voxel_size": 0.1, "mcd": 2, "stdnn": 20},
        {"Method": "NSS", "std": 2, "voxel_size": 0.1, "mcd": 2, "stdnn": 20},
        {"Method": "Standard", "std": 2, "voxel_size": 0.5, "mcd": 1, "stdnn": 20},
        {"Method": "NSS", "std": 2, "voxel_size": 0.5, "mcd": 1, "stdnn": 20},
        {"Method": "Standard", "std": 2, "voxel_size": 0.5, "mcd": 2, "stdnn": 20},
        {"Method": "NSS", "std": 2, "voxel_size": 0.5, "mcd": 2, "stdnn": 20},
    ]
    
    input_values = [
        {"Method": "Standard", "std": 0.5, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
        {"Method": "NSS", "std": 0.5, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
        {"Method": "Standard", "std": 0.5, "voxel_size": 0.1, "mcd": 2, "stdnn": 20},
        {"Method": "NSS", "std": 0.5, "voxel_size": 0.1, "mcd": 2, "stdnn": 20},
        {"Method": "Standard", "std": 0.5, "voxel_size": 0.5, "mcd": 1, "stdnn": 20},
        {"Method": "NSS", "std": 0.5, "voxel_size": 0.5, "mcd": 1, "stdnn": 20},
        {"Method": "Standard", "std": 0.5, "voxel_size": 0.5, "mcd": 2, "stdnn": 20},
        {"Method": "NSS", "std": 0.5, "voxel_size": 0.5, "mcd": 2, "stdnn": 20},
        {"Method": "Standard", "std": 1, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
        {"Method": "NSS", "std": 1, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
        {"Method": "Standard", "std": 1, "voxel_size": 0.1, "mcd": 2, "stdnn": 20},
        {"Method": "NSS", "std": 1, "voxel_size": 0.1, "mcd": 2, "stdnn": 20},
        {"Method": "Standard", "std": 1, "voxel_size": 0.5, "mcd": 1, "stdnn": 20},
        {"Method": "NSS", "std": 1, "voxel_size": 0.5, "mcd": 1, "stdnn": 20},
        {"Method": "Standard", "std": 1, "voxel_size": 0.5, "mcd": 2, "stdnn": 20},
        {"Method": "NSS", "std": 1, "voxel_size": 0.5, "mcd": 2, "stdnn": 20},
        {"Method": "Standard", "std": 2, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
        {"Method": "NSS", "std": 2, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
        {"Method": "Standard", "std": 2, "voxel_size": 0.1, "mcd": 2, "stdnn": 20},
        {"Method": "NSS", "std": 2, "voxel_size": 0.1, "mcd": 2, "stdnn": 20},
        {"Method": "Standard", "std": 2, "voxel_size": 0.5, "mcd": 1, "stdnn": 20},
        {"Method": "NSS", "std": 2, "voxel_size": 0.5, "mcd": 1, "stdnn": 20},
        {"Method": "Standard", "std": 2, "voxel_size": 0.5, "mcd": 2, "stdnn": 20},
        {"Method": "NSS", "std": 2, "voxel_size": 0.5, "mcd": 2, "stdnn": 20},
        {"Method": "Early-outliers-NSS", "std": 0.5, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
        {"Method": "Early-outliers-NSS", "std": 0.5, "voxel_size": 0.1, "mcd": 2, "stdnn": 20},
        {"Method": "Early-outliers-NSS", "std": 0.5, "voxel_size": 0.5, "mcd": 1, "stdnn": 20},
        {"Method": "Early-outliers-NSS", "std": 0.5, "voxel_size": 0.5, "mcd": 2, "stdnn": 20},
        {"Method": "Early-outliers-NSS", "std": 1, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
        {"Method": "Early-outliers-NSS", "std": 1, "voxel_size": 0.1, "mcd": 2, "stdnn": 20},
        {"Method": "Early-outliers-NSS", "std": 1, "voxel_size": 0.5, "mcd": 1, "stdnn": 20},
        {"Method": "Early-outliers-NSS", "std": 1, "voxel_size": 0.5, "mcd": 2, "stdnn": 20},
        {"Method": "Early-outliers-NSS", "std": 2, "voxel_size": 0.1, "mcd": 1, "stdnn": 20},
        {"Method": "Early-outliers-NSS", "std": 2, "voxel_size": 0.1, "mcd": 2, "stdnn": 20},
        {"Method": "Early-outliers-NSS", "std": 2, "voxel_size": 0.5, "mcd": 1, "stdnn": 20},
        {"Method": "Early-outliers-NSS", "std": 2, "voxel_size": 0.5, "mcd": 2, "stdnn": 20},
        {"Method": "Early-outliers-NSS", "std": 0.5, "voxel_size": 0.1, "mcd": 1, "stdnn": 200},
        {"Method": "Early-outliers-NSS", "std": 0.5, "voxel_size": 0.1, "mcd": 2, "stdnn": 200},
        {"Method": "Early-outliers-NSS", "std": 0.5, "voxel_size": 0.5, "mcd": 1, "stdnn": 200},
        {"Method": "Early-outliers-NSS", "std": 0.5, "voxel_size": 0.5, "mcd": 2, "stdnn": 200},
        {"Method": "Early-outliers-NSS", "std": 1, "voxel_size": 0.1, "mcd": 1, "stdnn": 200},
        {"Method": "Early-outliers-NSS", "std": 1, "voxel_size": 0.1, "mcd": 2, "stdnn": 200},
        {"Method": "Early-outliers-NSS", "std": 1, "voxel_size": 0.5, "mcd": 1, "stdnn": 200},
        {"Method": "Early-outliers-NSS", "std": 1, "voxel_size": 0.5, "mcd": 2, "stdnn": 200},
        {"Method": "Early-outliers-NSS", "std": 2, "voxel_size": 0.1, "mcd": 1, "stdnn": 200},
        {"Method": "Early-outliers-NSS", "std": 2, "voxel_size": 0.1, "mcd": 2, "stdnn": 200},
        {"Method": "Early-outliers-NSS", "std": 2, "voxel_size": 0.5, "mcd": 1, "stdnn": 200},
        {"Method": "Early-outliers-NSS", "std": 2, "voxel_size": 0.5, "mcd": 2, "stdnn": 200},
        {"Method": "Standard", "std": 0.5, "voxel_size": 0.1, "mcd": 1, "stdnn": 200},
        {"Method": "NSS", "std": 0.5, "voxel_size": 0.1, "mcd": 1, "stdnn": 200},
        {"Method": "Standard", "std": 0.5, "voxel_size": 0.1, "mcd": 2, "stdnn": 200},
        {"Method": "NSS", "std": 0.5, "voxel_size": 0.1, "mcd": 2, "stdnn": 200},
        {"Method": "Standard", "std": 0.5, "voxel_size": 0.5, "mcd": 1, "stdnn": 200},
        {"Method": "NSS", "std": 0.5, "voxel_size": 0.5, "mcd": 1, "stdnn": 200},
        {"Method": "Standard", "std": 0.5, "voxel_size": 0.5, "mcd": 2, "stdnn": 200},
        {"Method": "NSS", "std": 0.5, "voxel_size": 0.5, "mcd": 2, "stdnn": 200},
        {"Method": "Standard", "std": 1, "voxel_size": 0.1, "mcd": 1, "stdnn": 200},
        {"Method": "NSS", "std": 1, "voxel_size": 0.1, "mcd": 1, "stdnn": 200},
        {"Method": "Standard", "std": 1, "voxel_size": 0.1, "mcd": 2, "stdnn": 200},
        {"Method": "NSS", "std": 1, "voxel_size": 0.1, "mcd": 2, "stdnn": 200},
        {"Method": "Standard", "std": 1, "voxel_size": 0.5, "mcd": 1, "stdnn": 200},
        {"Method": "NSS", "std": 1, "voxel_size": 0.5, "mcd": 1, "stdnn": 200},
        {"Method": "Standard", "std": 1, "voxel_size": 0.5, "mcd": 2, "stdnn": 200},
        {"Method": "NSS", "std": 1, "voxel_size": 0.5, "mcd": 2, "stdnn": 200},
        {"Method": "Standard", "std": 2, "voxel_size": 0.1, "mcd": 1, "stdnn": 200},
        {"Method": "NSS", "std": 2, "voxel_size": 0.1, "mcd": 1, "stdnn": 200},
        {"Method": "Standard", "std": 2, "voxel_size": 0.1, "mcd": 2, "stdnn": 200},
        {"Method": "NSS", "std": 2, "voxel_size": 0.1, "mcd": 2, "stdnn": 200},
        {"Method": "Standard", "std": 2, "voxel_size": 0.5, "mcd": 1, "stdnn": 200},
        {"Method": "NSS", "std": 2, "voxel_size": 0.5, "mcd": 1, "stdnn": 200},
        {"Method": "Standard", "std": 2, "voxel_size": 0.5, "mcd": 2, "stdnn": 200},
        {"Method": "NSS", "std": 2, "voxel_size": 0.5, "mcd": 2, "stdnn": 200}
    ]
    """