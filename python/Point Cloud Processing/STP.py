import open3d as o3d

# Omgør en STL-fil til en punktsky

def STL_to_pointcloud(stl_path,number_of_points):

    mesh = o3d.io.read_triangle_mesh(stl_path)
    mesh.compute_vertex_normals()
    pcd = mesh.sample_points_uniformly(number_of_points)
    pcd = mesh.sample_points_poisson_disk(number_of_points=500, pcl=pcd)
    o3d.visualization.draw_geometries([pcd])

    return pcd