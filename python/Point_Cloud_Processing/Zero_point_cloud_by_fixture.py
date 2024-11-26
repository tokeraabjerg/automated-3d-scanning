# This program takes a scan of a fixture, in which a part may or may not be present.
# Then, based on an stl of the fixture, it find the transformation which aligns the fixture with the global axis.
# This transformation than may be applied to all subsequent scans, such that initial rotation of future scans are correctly rotated.
# Scan assumes that the fixture is at a set position (Vertical, with the flat side)

import open3d as o3d
import numpy as np
from ICP import Point_to_Plane

def Zero_point_cloud_by_fixture(point_cloud, Fikstur_fil):
    """
    Align a point cloud with a fixture using  ICP.
    
    Parameters:
    - ply_file: Path to the point cloud file.
    - fixture_reference: Path to the ply file of the fixture.
    
    Returns:
    - Zeroing transformation: The aligning transformation.
    """
    

    # Load the and prepare the fixture
    Fikstur = o3d.io.read_point_cloud(Fikstur_fil)
    Fikstur.rotate(o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(90), np.radians(90), np.radians(0))), center=(0,0,0))
    Fikstur.translate((0,-100,-15))

    # Create the axis arrows
    arrows = [
    create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
    ]
    combined_geometry = o3d.geometry.TriangleMesh()
    for arrow in arrows:
        combined_geometry += arrow
    
    # Visualize current setup
    # o3d.visualization.draw_geometries([Fikstur, combined_geometry, Fikstur_forskudt])    
    
    # Remove excess points from the fixture
    min_bound = (-120.0, -120.0, -14.0)  # Replace with your box's minimum x, y, and z coordinates
    max_bound = (120.0, 120.0, 30.0) 
    Fikstur_Reduced = remove_points_in_box(Fikstur, min_bound, max_bound)

    # o3d.visualization.draw_geometries([Fikstur_Reduced, combined_geometry])
    Fikstur_Reduced, density_vector_fiks = center_and_filter_point_cloud(Fikstur_Reduced, radius=60)
    point_cloud, density_vector_pc = center_and_filter_point_cloud(Fikstur_forskudt, radius=60)
        # TODO: When testing with the real scans, uncomment the following line and test the alignment. 
        # Will need to be added to zero trans.
    # centroid = np.mean(np.asarray(point_cloud.points), axis=0)
    # point_cloud.translate(-centroid)
    # o3d.visualization.draw_geometries([Fikstur_Reduced, point_cloud, combined_geometry], window_name="reduced and centered") 
    
    radius_normal = 2*1.5  # Radius til normal estimering
    point_cloud.estimate_normals(
    search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=50)) 
    Fikstur_Reduced.estimate_normals(
    search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=50))
    Fikstur_Reduced.paint_uniform_color([1, 0.706, 0])
    Transformation, point_cloud=Point_to_Plane(Fikstur_Reduced, point_cloud, 5)
    # o3d.visualization.draw_geometries([Fikstur_Reduced, point_cloud, combined_geometry], window_name="applied ICP") 

    translation_matrix = np.eye(4)
    translation_matrix[:3, 3] = -density_vector_pc 
    Zero_transformation=np.dot(Transformation, translation_matrix)

    translation_matrix = np.eye(4)
    translation_matrix[:3, 3] = density_vector_fiks 
    Zero_transformation=np.dot(translation_matrix, Zero_transformation)
    print(Zero_transformation)

    # Lastly, translate the fixture out by the distance to the center of tilt
    tilt_vec=(32.77, 0, 0)
    Fikstur.translate(tilt_vec)
    translation_matrix = np.eye(4)
    translation_matrix[:3, 3] = tilt_vec
    Zero_transformation=np.dot(translation_matrix, Zero_transformation)
    print(Zero_transformation)
    return Zero_transformation, Fikstur
    
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


# Eksempel på brug af funktionen:
if __name__ == "__main__":
    from Misc_functions import create_arrow

    Fikstur = o3d.io.read_point_cloud(r"C:\Users\mikke\OneDrive - Aalborg Universitet\CAD\Fiktur.ply")
    Fikstur_forskudt = o3d.io.read_point_cloud(r"C:\Users\mikke\automated-3d-scanning\Fiktur_Forskudt.ply")
    
    Fikstur_fil=r"C:\Users\mikke\OneDrive - Aalborg Universitet\CAD\Fiktur.ply"
    Zero_transformation, Fikstur=Zero_point_cloud_by_fixture(Fikstur_forskudt, Fikstur_fil)
    
    Fikstur_forskudt = o3d.io.read_point_cloud(r"C:\Users\mikke\automated-3d-scanning\Fiktur_Forskudt.ply")
    Fikstur_forskudt_uden_trans = o3d.io.read_point_cloud(r"C:\Users\mikke\automated-3d-scanning\Fiktur_Forskudt.ply")
    Fikstur_forskudt.transform(Zero_transformation)

    arrows = [
    create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
    ]
    combined_geometry = o3d.geometry.TriangleMesh()
    for arrow in arrows:
        combined_geometry += arrow
    Fikstur_forskudt.paint_uniform_color([1, 0.706, 1])
    o3d.visualization.draw_geometries([Fikstur_forskudt_uden_trans, Fikstur_forskudt, combined_geometry], window_name="Applied zero transform")
    
"""
    #Align the fixture with the global axis
    Fikstur.rotate(o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(90), np.radians(90), np.radians(0))), center=(0,0,0))
    Fikstur.translate((0,-100,-15))

    # Create the axis arrows
    arrows = [
    create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
    create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
    ]
    combined_geometry = o3d.geometry.TriangleMesh()
    for arrow in arrows:
        combined_geometry += arrow
    
    # Visualize current setup
    o3d.visualization.draw_geometries([Fikstur, combined_geometry, Fikstur_forskudt])    
    
    # Remove excess points from the fixture
    min_bound = (-120.0, -120.0, -14.5)  # Replace with your box's minimum x, y, and z coordinates
    max_bound = (120.0, 120.0, 30.0) 
    Fikstur_Reduced = remove_points_in_box(Fikstur, min_bound, max_bound)

    point_cloud, translation_vector = center_and_filter_point_cloud(Fikstur_forskudt, radius=60)
    # TODO: When testing with the real scans, uncomment the following line and test the alignment
    # centroid = np.mean(np.asarray(point_cloud.points), axis=0)
    # point_cloud.translate(-centroid)

    o3d.visualization.draw_geometries([Fikstur_Reduced, combined_geometry])
    Fikstur_Reduced, return_vector = center_and_filter_point_cloud(Fikstur_Reduced, radius=60)
    o3d.visualization.draw_geometries([Fikstur_Reduced, point_cloud, combined_geometry], window_name="reduced and centered") 
    
    #ToDo: find the transformation, and apply it to the point cloud. Then, return vector.
    radius_normal = 2*1.5  # Radius til normal estimering
    point_cloud.estimate_normals(
    search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=50)) 
    Fikstur_Reduced.estimate_normals(
    search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius_normal, max_nn=50))
    Fikstur_Reduced.paint_uniform_color([1, 0.706, 0])
    Transformation, point_cloud=Point_to_Plane(Fikstur_Reduced, point_cloud, 5)
    print(Transformation)
    o3d.visualization.draw_geometries([Fikstur_Reduced, point_cloud, combined_geometry], window_name="applied ICP") 
    

    

    translation_matrix = np.eye(4)
    translation_matrix[:3, 3] = -translation_vector 

    Zero_transformation=np.dot(Transformation, translation_matrix)
    translation_matrix = np.eye(4)
    translation_matrix[:3, 3] = return_vector 
    Zero_transformation=np.dot(translation_matrix, Zero_transformation)
    print(Zero_transformation)

    #Fikstur_forskudt.translate(-translation_vector)
    #Fikstur_forskudt.transform(Transformation)
    #Fikstur_forskudt.translate(return_vector)
    Fikstur_Reduced.translate(return_vector)
    Fikstur_forskudt.transform(Zero_transformation)

    o3d.visualization.draw_geometries([Fikstur_Reduced, Fikstur_forskudt, combined_geometry], window_name="applied zero transform")


#    FiksturReduced.rotate(o3d.geometry.PointCloud.get_rotation_matrix_from_xyz((np.radians(-3), np.radians(2), np.radians(0))), center=(0,0,0))
#    FiksturReduced.translate((50,30,300))


"""
