import open3d as o3d
import numpy as np
from IA import RANSAC_initial_alignment
from ICP import point_association
from EE import calculate_error

def process_point_clouds(source_path, target_path, voxel_size=0.001, max_correspondence_distance=0.02):
    """
    Main function to process point clouds. It performs the following steps:
    - Loads source and target point clouds.
    - Runs initial alignment (ICP or feature matching).
    - Performs point association (ICP).
    - Visualizes the aligned point clouds.
    - Calculates registration error.

    Parameters:
    - source_path: Path to the source point cloud file.
    - target_path: Path to the target point cloud file.
    - voxel_size: Voxel size for downsampling.
    - max_correspondence_distance: Max distance for point correspondence during ICP.

    Returns:
    - transformation: The final transformation matrix after ICP.
    - aligned_source: The aligned source point cloud.
    """
    
    # Step 1: Load point clouds
    source_leg = o3d.io.read_point_cloud(source_path)
    target_leg = o3d.io.read_point_cloud(target_path)
    
    # Save legacy clouds prior to registration
    source=source_leg
    target=target_leg

    target.paint_uniform_color([1, 0.706, 0])
    # o3d.visualization.draw_geometries([source, target])
    
    # Step 2: Downsample the point clouds
    source = source.voxel_down_sample(voxel_size)
    target = target.voxel_down_sample(voxel_size)
    
    # Step 3: Initial alignment (can be feature matching or ICP with coarse alignment) 
    # Currently RANSAC, shall be updated to consider alignment from joints
    print("Performing initial alignment...")
    initial_transformation = RANSAC_initial_alignment(source, target)
    print("Initial alignment transformation applied:")
    print(initial_transformation)
    target.transform(initial_transformation)
    o3d.visualization.draw_geometries([source, target])

    # Step 4: Point-to-Plane
    print("Performing Point-to-Plane")
    transformation_ICP, aligned_target = point_association(source, target)
    o3d.visualization.draw_geometries([source, target])
    
    # Step 5: Compare transformed target, if pass inspection, merge into source
    rmse_rating=calculate_error(source,target)
    print('rmse rating is:')
    print(rmse_rating)

    if rmse_rating < 0.005:
        
        combined = source + target
        # Potentially, downsize:
        # combined = combined.voxel_down_sample(voxel_size)
        print('merge succesful')
        o3d.visualization.draw_geometries([combined])

    else:
        print('merge failed')

    return combined




    
# Example of how to call the function
if __name__ == "__main__":
    source_file = r"C:\Users\mikke\Desktop\bunny\data\bun000.ply"
    target_file = r"C:\Users\mikke\Desktop\bunny\data\bun045.ply"
    
    # Call the function with appropriate arguments
    transformation, aligned_source = process_point_clouds(source_file, target_file)




# Brug funktionen med en liste af .ply-filer
    ply_files = [r"C:\Users\mikke\Desktop\bunny\data\bun000.ply", r"C:\Users\mikke\Desktop\bunny\data\bun045.ply"]
ply_files = [r"C:\Users\mikke\Desktop\bunny\data\bun000.ply", r"C:\Users\mikke\Desktop\bunny\data\bun045.ply", r"C:\Users\mikke\Desktop\bunny\data\bun090.ply"]
output_file = "merged_point_cloud.ply"

# process_point_clouds(r"C:\Users\mikke\Desktop\bunny\data\bun000.ply", r"C:\Users\mikke\Desktop\bunny\data\bun090.ply", voxel_size=0.01, max_correspondence_distance=0.02)
