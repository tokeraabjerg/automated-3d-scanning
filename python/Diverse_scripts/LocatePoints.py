import open3d as o3d
import numpy as np


#===================================================
#  *                    INFO
#    Åbner en visualisering af en punktsky. Et
#    valgfrit antal punkter kan vælges med
#    Shift-click. Når vinduet bliver lukket bliver
#    punkternes koordinater printet til terminalen.
#===================================================



class PointPickerVisualizer:
    def __init__(self, point_cloud, window_name):
        """
        Initialize the point picker visualizer.
        :param point_cloud: The Open3D point cloud object.
        :param window_name: Name of the visualization window.
        """
        self.point_cloud = point_cloud
        self.vis = o3d.visualization.VisualizerWithEditing()
        self.vis.create_window(window_name=window_name)

        # Add the point cloud to the visualizer
        self.vis.add_geometry(self.point_cloud)

        # Calculate bounding box size and center
        bbox = self.point_cloud.get_axis_aligned_bounding_box()
        center = bbox.get_center()
        extent = bbox.get_extent()
        max_extent = max(extent)

        print("Bounding Box Details:")
        print(f" - Center: {center}")
        print(f" - Extent: {extent}")
        print(f" - Max Extent: {max_extent}")

        # Add a coordinate frame centered at the point cloud
        coord_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(
            size=max_extent * 0.1 if max_extent > 0 else 1.0,  # Fallback to size 1.0 if max_extent is invalid
            origin=center
        )
        self.vis.add_geometry(coord_frame)
        print("Coordinate frame added to the visualizer.")
        
        # Set larger point size for easier clicking
        render_option = self.vis.get_render_option()
        render_option.point_size = 5.0  # Increase this value for larger points

        # Set background color to a subtler light baby blue
        render_option.background_color = np.array([0.789, 0.9, 0.94])  # RGB for light baby blue

    
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
    print(f"Loaded point cloud with {len(pcd.points)} points.")
    return pcd

# File path to the point cloud
file_path = r"C:\Users\ovikd\Downloads\Bolger_ved_distancer\scan_dist520close.ply"

# Load the point cloud
point_cloud = load_point_cloud(file_path)

if point_cloud:
    # Create and run the point picker visualizer
    picker = PointPickerVisualizer(point_cloud, window_name=file_path)
    picker.pick_points()
