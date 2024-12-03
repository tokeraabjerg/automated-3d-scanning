import getpass
import open3d as o3d
import numpy as np
import time
import logging

# Define your username
your_username = "mikke"

# Check if the current user is you
if getpass.getuser() == your_username:
    print("The code is being without modules")
    from Misc_functions import create_arrow
    from Calibration_by_fixture import inverse_center_and_filter_point_cloud
else:
    print("The code is not being run with Toke modules")
    from python.Point_Cloud_Processing.Misc_functions import create_arrow
    from python.Point_Cloud_Processing.Calibration_by_fixture import inverse_center_and_filter_point_cloud



def compute_point_cloud_density(pcd, radius):
    """
    Computes the density of points in a point cloud based on the number of neighbors within a specified radius.
    
    Args:
        pcd (o3d.geometry.PointCloud): The input point cloud.
        radius (float): The radius to use for density estimation.
    
    Returns:
        np.ndarray: An array of densities for each point in the point cloud.
    """
    kdtree = o3d.geometry.KDTreeFlann(pcd)
    densities = np.zeros(len(pcd.points))

    for i in range(len(pcd.points)):
        [_, idx, _] = kdtree.search_radius_vector_3d(pcd.points[i], radius)
        densities[i] = len(idx) - 1  # Subtract 1 to exclude the point itself

    return densities

def color_points_by_density(pcd, radius):
    """
    Colors points in a point cloud based on their density.
    
    Args:
        pcd (o3d.geometry.PointCloud): The input point cloud.
        radius (float): The radius to use for density estimation.
    
    Returns:
        o3d.geometry.PointCloud: The colored point cloud.
    """
    # Compute point cloud density
    densities = compute_point_cloud_density(pcd, radius)

    # Normalize densities to the range [0, 1]
    densities = (densities - densities.min()) / (densities.max() - densities.min())

    # Map densities to colors (e.g., blue to red)
    colors = np.zeros((len(densities), 3))
    colors[:, 0] = densities  # Red channel
    colors[:, 2] = 1 - densities  # Blue channel

    # Assign colors to the point cloud
    pcd.colors = o3d.utility.Vector3dVector(colors)

    return pcd

def normal_space_sampling_with_bin_control(point_cloud, num_samples, radius=3, max_nn=50, bin_size=360):
    """
    Downsamples a point cloud using normal space sampling.
    
    Args:
        point_cloud (o3d.geometry.PointCloud): The input point cloud.
        num_samples (int): The number of points to sample.
        radius (float): The radius for normal estimation.
        Bin size (int): The number of bins to use for normal space sampling. 
            Fewer bins will preferentially sample from areas with the greatest geometric change
            More bins will sample more uniformly across the surface.
    
    Returns:
        o3d.geometry.PointCloud: The downsampled point cloud.
    """
    print("num_samples:", num_samples)
    print("bin_size:", bin_size)
    # Compute normals for the point cloud
    if not point_cloud.has_normals():
        print("Estimating normals...")
        start_time = time.time()
        point_cloud.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius, max_nn), fast_normal_computation=True)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Time taken to estimate normals: {elapsed_time:.2f} seconds")
        # Orient normals towards the negative z-axis, improves sampling. (normals pointing away from the camera are inverted) 
        point_cloud.orient_normals_to_align_with_direction(orientation_reference=([0., 0., -1.]))

    
    normals = np.asarray(point_cloud.normals)
    print("Picking normals...")
    start_time = time.time()
    # Normalize the normal vectors
    normals = normals / np.linalg.norm(normals, axis=1, keepdims=True)

    # Convert normals to spherical coordinates (theta, phi)
    theta = np.arccos(normals[:, 2])  # Angle from z-axis
    phi = np.arctan2(normals[:, 1], normals[:, 0])  # Angle in xy-plane
    
    # Bin normals into uniform bins in the normal space
    num_theta_bins = bin_size #int(np.sqrt(num_samples)*bin_size)  # Divide angular space evenly
    num_phi_bins = bin_size #int(np.sqrt(num_samples)*bin_size)
    theta_bins = np.linspace(0, np.pi, num_theta_bins + 1)
    phi_bins = np.linspace(-np.pi, np.pi, num_phi_bins + 1) 
    #TODO: Normally, phi is -pi to pi, but since we flip towards the camera, we can optimize as we have done here
    #ERROR: Some point clouds REALLY dont like this.
    
    # Map each normal to a bin
    bin_indices = np.vstack([
        np.digitize(theta, theta_bins) - 1,
        np.digitize(phi, phi_bins) - 1
    ]).T

    """
    OG scheme - This is SLOW for large sets of points
    # Group points by bin and sample
    sampled_indices = []
    for theta_idx in range(num_theta_bins):
        for phi_idx in range(num_phi_bins):
            in_bin = np.where((bin_indices[:, 0] == theta_idx) & (bin_indices[:, 1] == phi_idx))[0]
            if len(in_bin) > 0:
                # Randomly sample one point from the bin
                sampled_indices.append(np.random.choice(in_bin))
    """
   
    # Group points by bin using a dictionary
    bin_dict = {}
    for idx, bin_index in enumerate(bin_indices):
        bin_tuple = tuple(bin_index)
        if bin_tuple not in bin_dict:
            bin_dict[bin_tuple] = []
        bin_dict[bin_tuple].append(idx)

    print("Randomly sampling points from each bin...")
    # Random scheme:
    sampled_indices = set()
    bin_keys = list(bin_dict.keys())  # Ensure bin_keys is a 1-dimensional list
    while len(sampled_indices) < num_samples:
        random_bin = bin_keys[np.random.randint(len(bin_keys))]
        random_point = np.random.choice(bin_dict[random_bin])
        if random_point not in sampled_indices:
            sampled_indices.add(random_point)
    sampled_indices = list(sampled_indices)
    print("Number of bins:", len(bin_dict))
    print("Number of sampled points:", len(sampled_indices))
    
    """
    # Uniform scheme:
    # The scheme below can run faster, yet does not actually randomly sample.

    # Sample one point from each bin
    sampled_indices = []
    for bin_points in bin_dict.values():
        sampled_indices.append(np.random.choice(bin_points))
    print("Number of bins:", len(bin_dict))
    print("Number of sampled points:", len(sampled_indices))
    
    num_samples=int(len(bin_dict))
    print("Number of points to sample:", num_samples)
    # Ensure we have exactly num_samples points
    sampled_indices = np.array(sampled_indices)
    if len(sampled_indices) > num_samples:
        sampled_indices = np.random.choice(sampled_indices, num_samples, replace=False)
    elif len(sampled_indices) < num_samples:
        additional_indices = np.random.choice(sampled_indices, num_samples - len(sampled_indices), replace=True)
        sampled_indices = np.concatenate([sampled_indices, additional_indices])
    print("Number of sampled points after check:", len(sampled_indices))
    """

    # Create the downsampled point cloud
    downsampled_cloud = point_cloud.select_by_index(sampled_indices)
    end_time = time.time()

    elapsed_time = end_time - start_time
    print(f"Time taken to bin and pick normals: {elapsed_time:.2f} seconds")
    
    return downsampled_cloud

# Example Usage
if __name__ == "__main__":
    
    arrows = [
        create_arrow(origin=(0, 0, 0), direction=(1, 0, 0), color=(1, 0, 0)),  # Red arrow along X-axis
        create_arrow(origin=(0, 0, 0), direction=(0, 1, 0), color=(0, 1, 0)),  # Green arrow along Y-axis
        create_arrow(origin=(0, 0, 0), direction=(0, 0, 1), color=(0, 0, 1))   # Blue arrow along Z-axis
    ]
    AxisArrow = o3d.geometry.TriangleMesh()
    for arrow in arrows:
        AxisArrow += arrow

    # Load a point cloud
    pcd = o3d.io.read_point_cloud(r"C:\Users\mikke\Desktop\mikkel\mikkel\motor_a_+15.ply")
    start_timer = time.time()
    print("Point cloud has", len(pcd.points), "points")

    pcd = pcd.voxel_down_sample(voxel_size=0.1)
    pcd = inverse_center_and_filter_point_cloud(pcd, 130)
    
    #densi_pcd = color_points_by_density(pcd, radius=2)
    o3d.visualization.draw_geometries([pcd], window_name="Downsampled Point Cloud")
    print("Point cloud Voxel has", len(pcd.points), "points")
    """
    # Downsample using normal space sampling
    if not pcd.has_normals():
        print("Estimating normals...")
        start_time = time.time()
        pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(3, max_nn=80), fast_normal_computation=False)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Time taken to estimate normals: {elapsed_time:.2f} seconds")
        # Orient normals towards the negative z-axis, improves sampling. (normals pointing away from the camera are inverted) 
        pcd.orient_normals_to_align_with_direction(orientation_reference=([0., 0., -1.]))

    o3d.visualization.draw_geometries([pcd], window_name="Downsampled Point Cloud", point_show_normal=True)
    
    
    start_time = time.time()
    downsampled_pcd=downsample_normal_space(pcd, num_samples=int(40000), radius=1)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Time taken by old scheme: {elapsed_time:.2f} seconds")   
    """

    # downsampled_pcd = Preprocessed_normal_pipeline(pcd, 0.1, 2.0)
    downsampled_pcd = normal_space_sampling_with_bin_control(pcd, num_samples=int(len(pcd.points)/12), radius=3, max_nn=100, bin_size=360)
    print("Downsampled point cloud has", len(downsampled_pcd.points), "points")
    # downsampled_pcd, ind = downsampled_pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2)
    # print("Outlier removed point cloud has", len(downsampled_pcd.points), "points")
    end_timer = time.time()
    elapsed_time = end_timer - start_timer
    print(f"Time taken by new scheme: {elapsed_time:.2f} seconds")   


    downsampled_pcd = color_points_by_density(downsampled_pcd, radius=3)
    # Measure the time to downsample using normal space sampling
    
    
    # o3d.visualization.draw_geometries([pcd], window_name=" Point Cloud", point_show_normal=True)
    # Visualize the downsampled point cloud
    o3d.visualization.draw_geometries([downsampled_pcd], window_name="Downsampled Point Cloud", point_show_normal=False)



def downsample_normal_space(point_cloud, num_samples, radius):
    """
    Downsamples a point cloud using normal space sampling.
        LEGACY FUNCTION
    Args:
        point_cloud (o3d.geometry.PointCloud): The input point cloud.
        num_samples (int): The number of points to sample.
    
    Returns:
        o3d.geometry.PointCloud: The downsampled point cloud.
    """
    # Compute normals for the point cloud
    print("Estimating normals...")
    if not point_cloud.has_normals():
        point_cloud.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius, max_nn=50), fast_normal_computation=False)
    normals = np.asarray(point_cloud.normals)
    print("picking normals...")
    # Convert normals to spherical coordinates (theta, phi)
    theta = np.arccos(normals[:, 2])  # Angle from z-axis
    phi = np.arctan2(normals[:, 1], normals[:, 0])  # Angle in xy-plane

    # Bin normals into uniform bins in the normal space
    num_theta_bins = int(np.sqrt(num_samples))  # Divide angular space evenly
    num_phi_bins = int(np.sqrt(num_samples))
    theta_bins = np.linspace(0, np.pi, num_theta_bins + 1)
    phi_bins = np.linspace(-np.pi, np.pi, num_phi_bins + 1)

    # Map each normal to a bin
    bin_indices = np.vstack([
        np.digitize(theta, theta_bins) - 1,
        np.digitize(phi, phi_bins) - 1
    ]).T

    # Group points by bin and sample
    sampled_indices = []
    for theta_idx in range(num_theta_bins):
        for phi_idx in range(num_phi_bins):
            in_bin = np.where((bin_indices[:, 0] == theta_idx) & (bin_indices[:, 1] == phi_idx))[0]
            if len(in_bin) > 0:
                # Randomly sample one point from the bin
                sampled_indices.append(np.random.choice(in_bin))

    # Create the downsampled point cloud
    sampled_indices = np.array(sampled_indices[:num_samples])  # Ensure exact number of samples
    downsampled_cloud = point_cloud.select_by_index(sampled_indices)

    return downsampled_cloud

