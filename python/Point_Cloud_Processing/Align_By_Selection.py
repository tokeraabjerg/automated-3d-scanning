import open3d as o3d
import numpy as np
from IA import RANSAC_initial_alignment, rotate_point_cloud, execute_global_registration

def center_and_filter_point_cloud(point_cloud, radius):
    # Move the center of the point cloud to the global zero point
    centroid = np.mean(np.asarray(point_cloud.points), axis=0)
    point_cloud.translate(-centroid)

    # Filter points within the specified radius around the x-axis
    def filter_function(point):
        x, y, z = point
        distance = np.sqrt(y**2 + z**2)
        return distance > radius

    filtered_points = np.asarray(point_cloud.points)[np.apply_along_axis(filter_function, 1, np.asarray(point_cloud.points))]
    filtered_point_cloud = o3d.geometry.PointCloud()
    filtered_point_cloud.points = o3d.utility.Vector3dVector(filtered_points)

    return filtered_point_cloud, centroid

def extract_plane(point_cloud, distance_threshold=0.01, ransac_n=3, num_iterations=1000):
    plane_model, inliers = point_cloud.segment_plane(distance_threshold=distance_threshold,
                                                     ransac_n=ransac_n,
                                                     num_iterations=num_iterations)
    plane_points = point_cloud.select_by_index(inliers)
    return plane_model, plane_points

def calculate_alignment_transformation(plane_model):
    # Extract the normal vector of the plane
    normal = np.array(plane_model[:3])

    # Calculate the rotation matrix to align the normal with the z-axis
    z_axis = np.array([0, 0, 1])
    v = np.cross(normal, z_axis)
    c = np.dot(normal, z_axis)
    k = 1 / (1 + c)

    rotation_matrix = np.array([
        [v[0] * v[0] * k + c, v[0] * v[1] * k - v[2], v[0] * v[2] * k + v[1]],
        [v[1] * v[0] * k + v[2], v[1] * v[1] * k + c, v[1] * v[2] * k - v[0]],
        [v[2] * v[0] * k - v[1], v[2] * v[1] * k + v[0], v[2] * v[2] * k + c]
    ])

    # Create the 4x4 transformation matrix
    transformation_matrix = np.eye(4)
    transformation_matrix[:3, :3] = rotation_matrix

    return transformation_matrix

def align_plane_to_axes(point_cloud, plane_model):
    # Calculate the transformation matrix
    transformation_matrix = calculate_alignment_transformation(plane_model)

    # Apply the transformation to the point cloud
    point_cloud.transform(transformation_matrix)

    return point_cloud


def select_edges(point_cloud):
    print("Please select 2 edges in the point cloud.")
    vis = o3d.visualization.VisualizerWithEditing()
    vis.create_window()
    vis.add_geometry(point_cloud)
    vis.run()  # user picks points
    vis.destroy_window()
    picked_points = vis.get_picked_points()
    assert len(picked_points) == 4, "Exactly 4 points must be selected to define 2 edges."
    return picked_points

def calculate_edge_alignment_transformation(points):
    assert len(points) == 4, "Exactly 4 points must be provided to define 2 edges."

    # Convert points to numpy array
    points = np.array(points)

    # Calculate vectors for the edges
    edge1 = points[1] - points[0]
    edge2 = points[3] - points[2]

    # Calculate the Euclidean distance between points 0 and 1
    calculated_distance = np.linalg.norm(edge1)
    known_distance = 60  # Known distance between the two points
    # Compute the scaling factor
    scaling_factor = known_distance / calculated_distance

    # Normalize the edges
    edge1 /= np.linalg.norm(edge1)
    edge2 /= np.linalg.norm(edge2)

    # Create rotation matrix
    R = np.eye(4)
    R[:3, :3] = np.vstack([edge1, edge2, np.cross(edge1, edge2)]).T

    # Create translation matrix
    T = np.eye(4)
    T[:3, 3] = -points[0]

    # Combine rotation and translation
    transformation_matrix = np.dot(R, T)

    return transformation_matrix, scaling_factor

def align_edges_to_axes(point_cloud):
    centroid = np.mean(np.asarray(point_cloud.points), axis=0)
    point_cloud.translate(-centroid)
    # Select 2 edges (4 points)
    picked_points_indices = select_edges(point_cloud)
    picked_points = np.asarray(point_cloud.points)[picked_points_indices]

    # Calculate transformation matrix
    transformation_matrix, scaling_factor = calculate_edge_alignment_transformation(picked_points)

    # Apply transformation
    point_cloud.transform(transformation_matrix)

    # Assuming the same corner is chosen every time..
    print(f"Scaling factor: {scaling_factor}")
    Trans_vec=(60,70,15)# (110*scaling_factor, -70*scaling_factor, -15*scaling_factor)
    point_cloud.translate(Trans_vec)

    translation_matrix = np.eye(4)
    translation_matrix[:3, 3] = Trans_vec 
    Center_and_align_trans=np.dot(translation_matrix, transformation_matrix) 
    
    return point_cloud, scaling_factor, Center_and_align_trans

def create_reference_plane(size=1.0, color=[0.5, 0.5, 0.5]):
    # Define the vertices of the plane
    vertices = np.array([
        [-size, -size, 0],
        [size, -size, 0],
        [size, size, 0],
        [-size, size, 0]
    ])

    # Define the triangles of the plane
    triangles = np.array([
        [0, 1, 2],
        [2, 3, 0]
    ])

    # Create the mesh
    plane = o3d.geometry.TriangleMesh()
    plane.vertices = o3d.utility.Vector3dVector(vertices)
    plane.triangles = o3d.utility.Vector3iVector(triangles)
    plane.paint_uniform_color(color)

    return plane

def remove_points_in_box(point_cloud, min_bound, max_bound):
    # Convert point cloud to numpy array
    points = np.asarray(point_cloud.points)

    # Define the box bounds
    x_min, y_min, z_min = min_bound
    x_max, y_max, z_max = max_bound

    # Filter points within the box
    mask = np.logical_or.reduce((
        points[:, 0] < x_min,
        points[:, 0] > x_max,
        points[:, 1] < y_min,
        points[:, 1] > y_max,
        points[:, 2] < z_min,
        points[:, 2] > z_max
    ))

    filtered_points = points[mask]

    # Create a new point cloud with the filtered points
    filtered_point_cloud = o3d.geometry.PointCloud()
    filtered_point_cloud.points = o3d.utility.Vector3dVector(filtered_points)

    return filtered_point_cloud

# Unrelated example code
if __name__ == "__main__":
    from Misc_functions import create_arrow
    from PP import preprocess_point_cloud

    voxel_size=1.5
    # List of .ply files to process
    ply_files = [
        r"C:\Users\mikke\automated-3d-scanning\Fiktur_Forskudt.ply"
    ]

    Fikstur = o3d.io.read_point_cloud(r"C:\Users\mikke\OneDrive - Aalborg Universitet\CAD\Fiktur.ply")
    Fikstur_forskudt = o3d.io.read_point_cloud(ply_files[0])
    
    Fikstur.rotate(o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(90), np.radians(90), np.radians(0))), center=(0,0,0))
    Fikstur.translate((0,-100,-15))
    arrows = [
    create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
    ]
    combined_geometry = o3d.geometry.TriangleMesh()
    for arrow in arrows:
        combined_geometry += arrow
    

    # Preproces: Downsize, Remove outliers, Find normals, Find features:
    # combined_cloud = combined_cloud.voxel_down_sample(voxel_size)
    Fikstur.translate((32.77,0,0))
    Fikstur.rotate(o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(45), np.radians(20), np.radians(0))), center=(0,0,0))
    o3d.visualization.draw_geometries([Fikstur, combined_geometry])    
    
#    FiksturReduced.rotate(o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(-3), np.radians(2), np.radians(0))), center=(0,0,0))
#    FiksturReduced.translate((50,30,300))



    # print("Performing RANSAC initial alignment...")
    # initial_transformation = RANSAC_initial_alignment(FiksturReduced, Filt_combined_cloud)
    # print("Initial alignment transformation applied:")
    # print(initial_transformation)
    # Filt_combined_cloud.transform(initial_transformation)
    
    
    # o3d.visualization.draw_geometries([FiksturReduced, Filt_combined_cloud, combined_geometry])
    



# Plane and edge based alignment methods
    # plane_model, inliers = Filt_combined_cloud.segment_plane(distance_threshold=0.01,
    #                                      ransac_n=3,
    #                                      num_iterations=1000)
    # [a, b, c, d] = plane_model
    # print(f"Plane equation: {a:.2f}x + {b:.2f}y + {c:.2f}z + {d:.2f} = 0")

    # inlier_cloud = Filt_combined_cloud.select_by_index(inliers)
    # inlier_cloud.paint_uniform_color([1.0, 0, 0])
    # outlier_cloud = Filt_combined_cloud.select_by_index(inliers, invert=True)
    # o3d.visualization.draw_geometries([inlier_cloud, outlier_cloud])
    # Alignplane=calculate_alignment_transformation(plane_model)
    # print(Alignplane)
    # Filt_combined_cloud.transform(Alignplane)
    # o3d.visualization.draw_geometries([Filt_combined_cloud, combined_geometry])
    # aligned_point_cloud, scaling_factor, transformation_matrix = align_edges_to_axes(combined_cloud)

    # # Visualize the result
    # o3d.visualization.draw_geometries([aligned_point_cloud, combined_geometry])

