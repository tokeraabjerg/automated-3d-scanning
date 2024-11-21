import open3d as o3d
import numpy as np

class PointPickerVisualizer:
    def __init__(self, point_cloud):
        """
        Initialize the point picker visualizer.
        :param point_cloud: The Open3D point cloud object.
        """
        self.point_cloud = point_cloud
        self.vis = o3d.visualization.VisualizerWithEditing()
        self.vis.create_window()
        self.vis.add_geometry(self.point_cloud)
        
        # Set larger point size for easier clicking
        render_option = self.vis.get_render_option()
        render_option.point_size = 10.0  # Increase this value for larger points
    
    def pick_points(self):
        """
        Launch the visualizer and let the user pick points.
        After picking points, the coordinates are printed.
        """
        print("Use [Shift + Left Click] to pick points.")
        print("Close the window after picking points to view their coordinates.")
        self.vis.run()  # User can pick points in this interactive window
        self.vis.destroy_window()

        # Get the picked point indices
        picked_points = self.vis.get_picked_points()
        if not picked_points:
            print("No points were picked.")
            return
        
        print("Picked Points Coordinates:")
        for idx in picked_points:
            coord = np.asarray(self.point_cloud.points)[idx]
            print(f"Point Index: {idx}, Coordinates: {coord}")

def load_point_cloud(file_path):
    """
    Load a point cloud from a file.
    :param file_path: Path to the point cloud file.
    :return: Loaded Open3D point cloud object.
    """
    pcd = o3d.io.read_point_cloud(file_path)
    if pcd.is_empty():
        print(f"Failed to load point cloud from {file_path}")
        return None
    return pcd

# File path to the point cloud
#file_path = r"C:\Users\ovikd\Downloads\bunny\bunny\data\bun000.ply"
file_path = r"C:\Users\ovikd\Downloads\testemne45.ply"

# Load the point cloud
point_cloud = load_point_cloud(file_path)
if point_cloud:
    # Create and run the point picker visualizer
    picker = PointPickerVisualizer(point_cloud)
    picker.pick_points()
