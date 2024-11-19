# Error Evaluation

# EE.py
import open3d as o3d
import numpy as np

def calculate_error(source, target):
    # Compute the point-to-point distance (RMSE)
    distances = source.compute_point_cloud_distance(target)
    rmse = np.sqrt(np.mean(np.array(distances) ** 2))

    return rmse

