""""
This document is an attempt at doing edge outlier removal.
May god have mercy on my soul.

New idea! Density based artefakt removal? 
Just use DBscan?

"""

import open3d as o3d
import numpy as np
import logging


def remove_noise_based_on_normals(point_cloud, radius_est=2, max_nn=50, radius_remove=0.5, min_neighbors=10, consistency_threshold=0.9):
    """
    Remove noisy points from a point cloud based on the consistency of normals in local neighborhoods.

    Args:
        point_cloud (o3d.geometry.PointCloud): The input point cloud.
        radius (float, optional): The radius for the neighborhood search. Defaults to 0.05.
        min_neighbors (int, optional): The minimum number of neighbors required to compute a normal. Defaults to 10.
        consistency_threshold (float, optional): The threshold for normal consistency (0 to 1). Defaults to 0.9.

    Returns:
        o3d.geometry.PointCloud: The filtered point cloud with noise removed.
    """
    # Ensure the point cloud has normals
    if not point_cloud.has_normals():
        logger.info("Computing normals for the point cloud...")
        point_cloud.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=radius_est, max_nn=max_nn))
        point_cloud.normalize_normals()

    # Build a KD-tree for neighborhood search
    kd_tree = o3d.geometry.KDTreeFlann(point_cloud)

    # Initialize a list to keep track of points to keep
    points_to_keep = []

    logger.info("Starting noise removal based on normal consistency...")

    for i, normal in enumerate(point_cloud.normals):
        # Search for neighbors within the radius
        [_, idx, _] = kd_tree.search_radius_vector_3d(point_cloud.points[i], radius_remove)

        # Ignore points with insufficient neighbors
        if len(idx) < min_neighbors:
            continue

        # Calculate the average normal of the neighbors
        neighbor_normals = np.asarray(point_cloud.normals)[idx]
        avg_normal = neighbor_normals.mean(axis=0)
        avg_normal /= np.linalg.norm(avg_normal)

        # Compute the cosine of the angle between the current normal and the average normal
        cosine_angle = np.dot(normal, avg_normal)

        # Check if the consistency is above the threshold
        if (cosine_angle >= consistency_threshold):
            points_to_keep.append(i)

    logger.info(f"Filtered out {len(point_cloud.points) - len(points_to_keep)} noisy points.")

    # Select the points to keep
    filtered_pcd = point_cloud.select_by_index(points_to_keep)
    filtered_pcd.remove_non_finite_points()

    return filtered_pcd

def remove_noise_based_on_planes(point_cloud, distance_threshold=0.2, ransac_n=4, num_iterations=1000, min_inliers=20, plane_distance_threshold=1):
    """
    Remove points that exist outside of planes.
    Modified to rely on distance between planes instead of normal uniqueness. 

    Args:
        point_cloud (o3d.geometry.PointCloud): The input point cloud.
        distance_threshold (float): Maximum distance a point can be from the plane to be considered an inlier.
        ransac_n (int): Number of points to sample for plane fitting.
        num_iterations (int): Number of iterations for RANSAC.
        min_inliers (int): Minimum number of inliers required to accept a plane.
        plane_distance_threshold (float): Maximum distance between two planes to consider them as overlapping.

    Returns:
        o3d.geometry.PointCloud: The filtered point cloud with noise removed.
        o3d.geometry.PointCloud: The point cloud containing all points in detected planes.
    """
    # Ensure the point cloud has normals
    if not point_cloud.has_normals():
        logger.info("Computing normals for the point cloud...")
        point_cloud.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
        point_cloud.normalize_normals()

    planes = []
    remaining_pcd = point_cloud
    plane_geometries = []

    while True:
        plane_model, inliers = remaining_pcd.segment_plane(distance_threshold=distance_threshold,
                                                           ransac_n=ransac_n,
                                                           num_iterations=num_iterations)
        if len(inliers) < min_inliers:
            break

        new_plane_normal = plane_model[:3]
        new_plane_d = plane_model[3]
        new_plane_inliers = set(inliers)
        keep_plane = True

        for plane in planes:
            existing_normal = plane['normal']
            existing_d = plane['d']
            distance = abs(new_plane_d - existing_d) / np.linalg.norm(existing_normal)
            if distance < plane_distance_threshold:
                if len(inliers) > len(plane['inliers']):
                    plane['normal'] = new_plane_normal
                    plane['d'] = new_plane_d
                    plane['inliers'] = inliers
                else:
                    plane['inliers'].extend(inliers)
                keep_plane = False
                break

        if keep_plane:
            planes.append({'normal': new_plane_normal, 'd': new_plane_d, 'inliers': inliers})
            plane_cloud = remaining_pcd.select_by_index(inliers)
            plane_cloud.paint_uniform_color(np.random.rand(3))
            plane_geometries.append(plane_cloud)
        
        remaining_pcd = remaining_pcd.select_by_index(inliers, invert=True)
    
    # Collect all inlier indices from all planes
    all_inliers = []
    for plane in planes:
        all_inliers.extend(plane['inliers'])

    # Visualize the planes
    o3d.visualization.draw_geometries(plane_geometries, window_name="Detected Planes")

    # Filter points based on plane inliers
    points_to_keep = []
    for plane in planes:
        inlier_indices = point_cloud.segment_plane(distance_threshold=distance_threshold,
                                                   ransac_n=ransac_n,
                                                   num_iterations=num_iterations)[1]
        points_to_keep.extend(inlier_indices)

    logger.info(f"Detected {len(planes)} unique planes with minimum {min_inliers} inliers each.")

    # Select the points to keep
    filtered_pcd = point_cloud.select_by_index(points_to_keep)
    filtered_pcd.remove_non_finite_points()

    # Create a point cloud with all points in detected planes
    plane_points_pcd = point_cloud.select_by_index(all_inliers)
    plane_points_pcd.remove_non_finite_points()

    return filtered_pcd, plane_points_pcd

def remove_points_beyond_plane_intersections(point_cloud, distance_threshold=0.2, ransac_n=4, num_iterations=1000, min_inliers=20, plane_distance_threshold=1):
    """
    Find the intersection between planes, visualize the intersections, and remove points further away than the most distant intersection line.

    Args:
        point_cloud (o3d.geometry.PointCloud): The input point cloud.
        distance_threshold (float): Maximum distance a point can be from the plane to be considered an inlier.
        ransac_n (int): Number of points to sample for plane fitting.
        num_iterations (int): Number of iterations for RANSAC.
        min_inliers (int): Minimum number of inliers required to accept a plane.
        plane_distance_threshold (float): Maximum distance between two planes to consider them as overlapping.

    Returns:
        o3d.geometry.PointCloud: The filtered point cloud with points beyond the most distant intersection line removed.
    """
    logger.info("Starting plane intersection removal process...")

    # Ensure the point cloud has normals
    if not point_cloud.has_normals():
        logger.info("Computing normals for the point cloud...")
        point_cloud.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
        point_cloud.normalize_normals()

    planes = []
    remaining_pcd = point_cloud
    plane_geometries = []

    while True:
        plane_model, inliers = remaining_pcd.segment_plane(distance_threshold=distance_threshold,
                                                           ransac_n=ransac_n,
                                                           num_iterations=num_iterations)
        if len(inliers) < min_inliers:
            break

        new_plane_normal = plane_model[:3]
        new_plane_d = plane_model[3]
        new_plane_inliers = set(inliers)
        keep_plane = True

        for plane in planes:
            existing_normal = plane['normal']
            existing_d = plane['d']
            distance = abs(new_plane_d - existing_d) / np.linalg.norm(existing_normal)
            if distance < plane_distance_threshold:
                if len(inliers) > len(plane['inliers']):
                    plane['normal'] = new_plane_normal
                    plane['d'] = new_plane_d
                    plane['inliers'] = inliers
                else:
                    plane['inliers'].extend(inliers)
                keep_plane = False
                break

        if keep_plane:
            planes.append({'normal': new_plane_normal, 'd': new_plane_d, 'inliers': inliers})
            plane_cloud = remaining_pcd.select_by_index(inliers)
            plane_cloud.paint_uniform_color(np.random.rand(3))
            plane_geometries.append(plane_cloud)
        
        remaining_pcd = remaining_pcd.select_by_index(inliers, invert=True)
    
    logger.info(f"Detected {len(planes)} planes.")

    # Visualize all detected planes
    o3d.visualization.draw_geometries(plane_geometries, window_name="Detected Planes")

    # Calculate the density center of the point cloud
    density_center = np.mean(np.asarray(point_cloud.points), axis=0)

    # Find the most distant intersection line
    max_distance = 0
    intersection_lines = []
    for i, plane1 in enumerate(planes):
        for j, plane2 in enumerate(planes):
            if i >= j:
                continue
            # Calculate the intersection line of the two planes
            normal1 = plane1['normal']
            d1 = plane1['d']
            normal2 = plane2['normal']
            d2 = plane2['d']
            line_direction = np.cross(normal1, normal2)
            if np.linalg.norm(line_direction) < 1e-6:
                continue  # Planes are parallel or coincident

            # Find a point on the intersection line
            A = np.array([normal1, normal2, line_direction])
            b = np.array([-d1, -d2, 0])
            intersection_point = np.linalg.solve(A, b)

            # Calculate the distance from the density center to the intersection line
            distance = np.linalg.norm(density_center - intersection_point)
            if distance > max_distance:
                max_distance = distance

            intersection_lines.append((intersection_point, line_direction))

    logger.info(f"Most distant intersection line distance: {max_distance}")

    # Visualize the intersection lines
    intersection_geometries = []
    for intersection_point, line_direction in intersection_lines:
        line_mesh = o3d.geometry.TriangleMesh.create_arrow(
            cylinder_radius=2,
            cone_radius=2,
            cylinder_height=10.0,
            cone_height=3
        )
        line_mesh.paint_uniform_color([1, 0, 0])  # Red color for intersection lines
        line_mesh.rotate(o3d.geometry.get_rotation_matrix_from_axis_angle(line_direction), center=(0, 0, 0))
        line_mesh.translate(intersection_point)
        intersection_geometries.append(line_mesh)

    # Combine intersection geometries and plane geometries into a single list
    all_geometries = intersection_geometries + plane_geometries

    o3d.visualization.draw_geometries(all_geometries, window_name="Intersection Lines")

    # Remove points beyond the most distant intersection line
    points_to_keep = []
    for point in np.asarray(point_cloud.points):
        if np.linalg.norm(density_center - point) <= max_distance:
            points_to_keep.append(point)

    # Create a new point cloud with the filtered points
    filtered_pcd = o3d.geometry.PointCloud()
    filtered_pcd.points = o3d.utility.Vector3dVector(points_to_keep)

    logger.info("Plane intersection removal process completed.")

    return filtered_pcd

def detect_surface_boundaries(point_cloud, plane_model, distance_threshold=0.01, boundary_distance=0.05):
    """
    Detect the boundaries of a surface defined by a plane model within a point cloud.

    Args:
        point_cloud (o3d.geometry.PointCloud): The input point cloud.
        plane_model (list or np.ndarray): The plane model coefficients [a, b, c, d] from RANSAC.
        distance_threshold (float): Distance threshold to consider a point as inlier.
        boundary_distance (float): Distance to consider for boundary detection.

    Returns:
        o3d.geometry.PointCloud: Point cloud consisting of boundary points.
    """
    # Find inliers of the plane
    inlier_indices = point_cloud.segment_plane(distance_threshold=distance_threshold,
                                              ransac_n=3,
                                              num_iterations=1000)[1]
    plane_pcd = point_cloud.select_by_index(inlier_indices)

    # Build KDTree for the entire point cloud
    kdtree = o3d.geometry.KDTreeFlann(point_cloud)

    boundary_indices = []
    plane_set = set(inlier_indices)

    for idx in inlier_indices:
        point = point_cloud.points[idx]
        [_, neighbor_idx, _] = kdtree.search_radius_vector_3d(point, boundary_distance)
        # Check if any neighbor is not part of the plane
        has_non_plane_neighbor = any(n not in plane_set for n in neighbor_idx)
        if has_non_plane_neighbor:
            boundary_indices.append(idx)

    boundary_pcd = point_cloud.select_by_index(boundary_indices)
    boundary_pcd.paint_uniform_color([1, 1, 0])  # Yellow color for boundaries

    logger.info(f"Detected {len(boundary_indices)} boundary points.")

    # Visualize the boundaries
    o3d.visualization.draw_geometries([boundary_pcd], window_name="Surface Boundaries")

    return boundary_pcd

def detect_and_visualize_outlying_planes(point_cloud, distance_threshold=0., ransac_n=4, num_iterations=1000, min_inliers=20):
    """
    Detect and visualize outlying planes in a point cloud. Outlying planes are those which, in a given direction,
    are furthest away from the center of density.

    Args:
        point_cloud (o3d.geometry.PointCloud): The input point cloud.
        distance_threshold (float): Maximum distance a point can be from the plane to be considered an inlier.
        ransac_n (int): Number of points to sample for plane fitting.
        num_iterations (int): Number of iterations for RANSAC.
        min_inliers (int): Minimum number of inliers required to accept a plane.

    Returns:
        o3d.geometry.PointCloud: The point cloud containing all points in detected outlying planes.
    """
    logger.info("Starting outlying plane detection process...")

    # Ensure the point cloud has normals
    if not point_cloud.has_normals():
        logger.info("Computing normals for the point cloud...")
        point_cloud.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
        point_cloud.normalize_normals()

    planes = []
    remaining_pcd = point_cloud
    plane_geometries = []

    while True:
        plane_model, inliers = remaining_pcd.segment_plane(distance_threshold=distance_threshold,
                                                           ransac_n=ransac_n,
                                                           num_iterations=num_iterations)
        if len(inliers) < min_inliers:
            break

        new_plane_normal = plane_model[:3]
        new_plane_d = plane_model[3]
        new_plane_inliers = set(inliers)
        keep_plane = True

        for plane in planes:
            existing_normal = plane['normal']
            existing_d = plane['d']
            if np.allclose(new_plane_normal, existing_normal) or np.allclose(new_plane_normal, -existing_normal):
                if abs(new_plane_d) > abs(existing_d):
                    plane['normal'] = new_plane_normal
                    plane['d'] = new_plane_d
                    plane['inliers'] = inliers
                keep_plane = False
                break

        if keep_plane:
            planes.append({'normal': new_plane_normal, 'd': new_plane_d, 'inliers': inliers})
            plane_cloud = remaining_pcd.select_by_index(inliers)
            plane_cloud.paint_uniform_color(np.random.rand(3))
            plane_geometries.append(plane_cloud)
        
        remaining_pcd = remaining_pcd.select_by_index(inliers, invert=True)
    
    logger.info(f"Detected {len(planes)} outlying planes.")

    # Visualize all detected planes
    o3d.visualization.draw_geometries(plane_geometries, window_name="Outlying Planes")

    # Collect all inlier indices from all planes
    all_inliers = []
    for plane in planes:
        all_inliers.extend(plane['inliers'])

    # Create a point cloud with all points in detected planes
    outlying_planes_pcd = point_cloud.select_by_index(all_inliers)
    outlying_planes_pcd.remove_non_finite_points()

    return outlying_planes_pcd

def create_axis_arrows(length=1.0, radius=0.01):
    """
    Create a point cloud representing axis arrows from the origin (0,0,0).

    Args:
        length (float): The length of each axis arrow. Defaults to 1.0.
        radius (float): The radius of each axis arrow. Defaults to 0.01.

    Returns:
        o3d.geometry.PointCloud: The point cloud representing the axis arrows.
    """
    mesh_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=length, origin=[0, 0, 0])
    axis_arrows_pcd = mesh_frame.sample_points_uniformly(number_of_points=int(length / radius * 1000))
    return axis_arrows_pcd

if __name__ == "__main__":
    # Create axis arrows point cloud
    axis_arrows_pcd = create_axis_arrows(length=100.0, radius=5)
    
    # Save the point cloud to a file
    o3d.io.write_point_cloud("axis_arrows.ply", axis_arrows_pcd)
    
    # Visualize the point cloud
    o3d.visualization.draw_geometries([axis_arrows_pcd], window_name="Axis Arrows")
