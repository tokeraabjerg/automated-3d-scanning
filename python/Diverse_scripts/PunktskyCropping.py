import open3d as o3d
import numpy as np

#================================================
#  *                    INFO
#    Åbner en visualisering af en punktsky. To
#    punkter kan vælges med Shift-click for at
#    definere en boks. Alle punkter udenfor denne
#    kasse bliver fjernet.
#    
#    Filen bliver gemt til output_file på
#    linje 81.
#================================================


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
        render_option.point_size = 5.0  # Adjust as needed for visibility
    
    def pick_points(self):
        """
        Launch the visualizer and let the user pick points.
        Returns the indices of the picked points.
        """
        print("Use [Shift + Left Click] to pick points.")
        print("Pick exactly 2 points for cropping. Close the window after selection.")
        self.vis.run()  # User selects points
        self.vis.destroy_window()

        # Get the picked point indices
        picked_points = self.vis.get_picked_points()
        return picked_points

def crop_point_cloud(point_cloud, point_indices, output_file):
    if len(point_indices) != 2:
        print("Error: You must pick exactly 2 points for cropping.")
        return None

    # Get the coordinates of the selected points
    points = np.asarray(point_cloud.points)
    point1 = points[point_indices[0]]
    point2 = points[point_indices[1]]

    # Add a small tolerance to avoid zero-size bounding box
    tolerance = 1e-5
    min_bound = np.minimum(point1, point2) - tolerance
    max_bound = np.maximum(point1, point2) + tolerance

    # Define the bounding box
    bounding_box = o3d.geometry.AxisAlignedBoundingBox(min_bound=min_bound, max_bound=max_bound)

    # Visualize the bounding box before cropping
    point_cloud.paint_uniform_color([0.5, 0.5, 0.5])  # Set point cloud to a neutral color
    bounding_box.color = (1, 0, 0)  # Make the bounding box red for better visibility
    o3d.visualization.draw_geometries([point_cloud, bounding_box], window_name="Bounding Box Verification")

    # Crop the point cloud
    cropped_pcd = point_cloud.crop(bounding_box)
    if cropped_pcd.is_empty():
        print("Error: Cropped point cloud is empty. Please check the selected points.")
        return None

    print(f"Cropped point cloud has {len(cropped_pcd.points)} points.")
    
    # Save the cropped point cloud
    o3d.io.write_point_cloud(output_file, cropped_pcd)
    print(f"Cropped point cloud saved to {output_file}")

    # Visualize the cropped point cloud
    o3d.visualization.draw_geometries([cropped_pcd], window_name="Cropped Point Cloud")
    return cropped_pcd

def main():
    # File path to the input and output point clouds
    input_file = r"C:\Users\ovikd\Documents\Punktskyer\Scanned0.ply"
    output_file = r"C:\Users\ovikd\Documents\Punktskyer\Croptest.ply"

    # Load the point cloud
    point_cloud = o3d.io.read_point_cloud(input_file)
    if point_cloud.is_empty():
        print(f"Failed to load point cloud from {input_file}")
        return

    print(f"Loaded point cloud with {len(point_cloud.points)} points.")

    # Initialize the point picker visualizer
    picker = PointPickerVisualizer(point_cloud)

    # Pick two points
    picked_indices = picker.pick_points()
    if len(picked_indices) != 2:
        print("You must pick exactly 2 points. Please try again.")
        return
    
    print(f"Picked point indices: {picked_indices}")
    picked_coords = [np.asarray(point_cloud.points)[i] for i in picked_indices]
    print(f"Picked point coordinates: {picked_coords}")

    # Crop the point cloud using the picked points
    crop_point_cloud(point_cloud, picked_indices, output_file)

if __name__ == "__main__":
    main()
