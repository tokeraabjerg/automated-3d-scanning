import open3d as o3d
import numpy as np
from IA import RANSAC_initial_alignment, rotate_point_cloud
from ICP import Point_to_Plane
from EE import calculate_error
from DT import decompose_transformation
from DB import remove_small_clusters
from BB import compute_bounding_box

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
    combined_cloud = combined_cloud.voxel_down_sample(voxel_size)

    # Beregn bounding box
    min_bound, max_bound = compute_bounding_box(combined_cloud)

    # Beregn størrelse af bounding box
    bbox_size = max_bound - min_bound
    print(f"Størrelse af bounding box: {bbox_size}")

    o3d.visualization.draw_geometries([combined_cloud])
    print("Statistical oulier removal")
    combined_cloud, ind = combined_cloud.remove_statistical_outlier(nb_neighbors=100, std_ratio=0.5)
    o3d.visualization.draw_geometries([combined_cloud], window_name="Statistical outliers removed")
#    combined_cloud = remove_small_clusters(combined_cloud, 1000/voxel_size, eps=0.1e-100)
#    o3d.visualization.draw_geometries([combined_cloud], window_name="Clusters removed")

    for i in range(1, len(ply_files)):
        print(f"Processing point cloud {i + 1}/{len(ply_files)}...")
        
        # Load the next point cloud
        target_cloud = o3d.io.read_point_cloud(ply_files[i])
        target_cloud = target_cloud.voxel_down_sample(voxel_size)
        target_cloud, ind = target_cloud.remove_statistical_outlier(nb_neighbors=100, std_ratio=0.5)
        target_cloud.paint_uniform_color([1, 0.706, 0])

        # Step 1: Initial alignment (RANSAC or other coarse alignment)
        initial_transformation = [None] * len(ply_files)
        if rotation_vectors[i] == (None):
            print("Performing RANSAC initial alignment...")
            initial_transformation[i] = RANSAC_initial_alignment(combined_cloud, target_cloud)
            print("Initial alignment transformation applied:")
            print(initial_transformation[i])
            target_cloud.transform(initial_transformation[i])
            o3d.visualization.draw_geometries([combined_cloud, target_cloud], window_name="RANSAC'ed Point Cloud")
        else:
            target_cloud, initial_transformation[i]=rotate_point_cloud(target_cloud, rotation_vectors, i)
            print(initial_transformation[i])
            o3d.visualization.draw_geometries([combined_cloud, target_cloud], window_name="Rotated Point Cloud")
        result=decompose_transformation(initial_transformation[i])
        print("Translation (x, y, z):", result["translation"])
        print("Rotation (roll, pitch, yaw) in degrees:", result["rotation"])
        # Estimating normals for source and target point clouds
        radius_normal = 0.1  # Radius til normal estimering
        combined_cloud.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=50))  # Øget max_nn for at få tilstrækkelige naboer
        target_cloud.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=50))

        # Step 2: Point-to-Plane ICP
        print("Performing ICP registration...")
        # Initialize the array containing all ICP transformaitons
        transformation_ICP = [None] * len(ply_files)
        transformation_ICP[i], aligned_target = Point_to_Plane(combined_cloud, target_cloud, mcd)
        
        combined_transformation = np.dot(transformation_ICP[i], initial_transformation[i])
        result=decompose_transformation(combined_transformation)
        print("Translation (x, y, z):", result["translation"])
        print("Rotation (roll, pitch, yaw) in degrees:", result["rotation"])

        # Step 3: Calculate RMSE
        rmse_rating = calculate_error(combined_cloud, aligned_target)
        print(f"RMSE rating: {rmse_rating}")

        # Step 4: Merge if RMSE is acceptable !! This needs to be updated in some way. 
        # I have yet to find an intelligent solution. 
        # Technically, I guess it should'nt be here, since the ICP script should have rejected it.
        if rmse_rating < 50:
            combined_cloud += aligned_target
#            combined_cloud = combined_cloud.voxel_down_sample(voxel_size)
#            combined_cloud.paint_uniform_color([1, 0.706, 0])
            print("Merge successful.")
        else:
            print("Merge failed. Skipping this cloud.")
        
        # Optional: Visualize the current merged cloud
        o3d.visualization.draw_geometries([combined_cloud], window_name="Merged Point Cloud")

    return combined_cloud


# Example of how to call the function
# if __name__ == "__main__":
#     # List of .ply files to process
#     ply_files = [
#         r"C:\Users\mikke\Desktop\bunny\data\bun000.ply",
#         r"C:\Users\mikke\Desktop\bunny\data\bun045.ply",
#         r"C:\Users\mikke\Desktop\bunny\data\bun090.ply"
#         #r"C:\Users\mikke\Desktop\bunny\data\bun315.ply"
#         #r"C:\Users\mikke\Desktop\bunny\data\bun270.ply"
#     ]

#     #rotation_degrees = [0, 45, 90, 315, 270]   
#     rotation_vectors = [
#     (0, 0, 0),    # Tom første indgang
#     (0, 0, 0),   # Rotation omkring en vilkårlig akse
#     (0, 90, 0)    # 90 grader omkring y-aksen
#     ]
if __name__ == "__main__":
    # List of .ply files to process
    ply_files = [
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\0 grader test 2.ply",
        r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\15 grader test 2.ply"
       # r"C:\Users\mikke\Desktop\0, 15, 45 (test 2 til Mikkel)\45 grader test 2.ply"
    ]

    rotation_vectors = [
    (None),    # Tom første indgang
    (15, 0, 0)     # Rotation omkring en vilkårlig akse
    #(0, 0, 0)    # 90 grader omkring y-aksen
    ]


    # Process the point clouds
    print("Starting point cloud processing...")
    final_cloud = process_point_clouds(ply_files, rotation_vectors, voxel_size=1.5, mcd=10)

    # Save the final merged point cloud
    output_file = "merged_point_cloud.ply"
    o3d.io.write_point_cloud(output_file, final_cloud)
    print(f"Final merged point cloud saved to: {output_file}")

    # Visualize the final result
    o3d.visualization.draw_geometries([final_cloud], window_name="Final Merged Point Cloud")
