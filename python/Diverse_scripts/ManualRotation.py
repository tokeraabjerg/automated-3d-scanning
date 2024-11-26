import open3d as o3d
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QWidget
import threading


class PointCloudVisualizer(QMainWindow):
    def __init__(self, design_pc_path, scanned_pc_path):
        super().__init__()

        # Load point clouds
        self.design_pc_path = design_pc_path
        self.design_pc = o3d.io.read_point_cloud(design_pc_path)
        self.scanned_pc = o3d.io.read_point_cloud(scanned_pc_path)

        if self.design_pc.is_empty() or self.scanned_pc.is_empty():
            raise ValueError("One or both point clouds failed to load.")

        # Compute centroid of DesignPC
        self.design_centroid = np.mean(np.asarray(self.design_pc.points), axis=0)
        print(f"Centroid of DesignPC: {self.design_centroid}")

        # Layout for buttons
        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)

        # Add rotation buttons
        self.add_rotation_buttons()

        self.setCentralWidget(self.widget)

        # Start the Open3D viewer in a separate thread
        self.viewer_thread = threading.Thread(target=self.start_open3d_viewer, daemon=True)
        self.viewer_thread.start()

    def add_rotation_buttons(self):
        """
        Add buttons for rotating the DesignPC point cloud.
        """
        self.rotate_x_plus_button = QPushButton("Rotate Design +X")
        self.rotate_x_plus_button.clicked.connect(lambda: self.rotate_design(axis="x", angle=5))
        self.layout.addWidget(self.rotate_x_plus_button)

        self.rotate_x_minus_button = QPushButton("Rotate Design -X")
        self.rotate_x_minus_button.clicked.connect(lambda: self.rotate_design(axis="x", angle=-5))
        self.layout.addWidget(self.rotate_x_minus_button)

        self.rotate_y_plus_button = QPushButton("Rotate Design +Y")
        self.rotate_y_plus_button.clicked.connect(lambda: self.rotate_design(axis="y", angle=5))
        self.layout.addWidget(self.rotate_y_plus_button)

        self.rotate_y_minus_button = QPushButton("Rotate Design -Y")
        self.rotate_y_minus_button.clicked.connect(lambda: self.rotate_design(axis="y", angle=-5))
        self.layout.addWidget(self.rotate_y_minus_button)

        self.rotate_z_plus_button = QPushButton("Rotate Design +Z")
        self.rotate_z_plus_button.clicked.connect(lambda: self.rotate_design(axis="z", angle=5))
        self.layout.addWidget(self.rotate_z_plus_button)

        self.rotate_z_minus_button = QPushButton("Rotate Design -Z")
        self.rotate_z_minus_button.clicked.connect(lambda: self.rotate_design(axis="z", angle=-5))
        self.layout.addWidget(self.rotate_z_minus_button)

        self.reset_button = QPushButton("Reset Design Rotation")
        self.reset_button.clicked.connect(self.reset_design)
        self.layout.addWidget(self.reset_button)

    def rotate_design(self, axis, angle):
        """
        Rotate the DesignPC point cloud around the specified axis by the given angle.
        Rotation is performed around its own centroid.
        """
        angle = np.radians(angle)

        if axis == "x":
            R = np.array([
                [1, 0, 0],
                [0, np.cos(angle), -np.sin(angle)],
                [0, np.sin(angle), np.cos(angle)]
            ])
        elif axis == "y":
            R = np.array([
                [np.cos(angle), 0, np.sin(angle)],
                [0, 1, 0],
                [-np.sin(angle), 0, np.cos(angle)]
            ])
        elif axis == "z":
            R = np.array([
                [np.cos(angle), -np.sin(angle), 0],
                [np.sin(angle), np.cos(angle), 0],
                [0, 0, 1]
            ])
        else:
            print("Invalid axis. Choose 'x', 'y', or 'z'.")
            return

        # Rotate the design point cloud around its centroid
        self.design_pc.translate(-self.design_centroid)
        self.design_pc.rotate(R, center=(0, 0, 0))
        self.design_pc.translate(self.design_centroid)

    def reset_design(self):
        """
        Reset the DesignPC point cloud to its original state.
        """
        self.design_pc = o3d.io.read_point_cloud(self.design_pc_path)
        self.design_pc.paint_uniform_color([1, 0, 0])  # Red

    def save_design_pc(self):
        """
        Save the rotated DesignPC to a file.
        """
        output_file = self.design_pc_path.replace(".ply", "_rotated.ply")
        o3d.io.write_point_cloud(output_file, self.design_pc)
        print(f"Rotated DesignPC saved to {output_file}")

    def start_open3d_viewer(self):
        """
        Start the Open3D visualizer in a standalone window.
        """
        vis = o3d.visualization.Visualizer()
        vis.create_window(window_name="Open3D Viewer", width=800, height=600)

        # Add geometries
        self.design_pc.paint_uniform_color([1, 0, 0])  # Red
        self.scanned_pc.paint_uniform_color([0, 1, 0])  # Green
        vis.add_geometry(self.design_pc)
        vis.add_geometry(self.scanned_pc)

        while True:
            vis.update_geometry(self.design_pc)
            vis.update_geometry(self.scanned_pc)
            vis.poll_events()
            vis.update_renderer()

    def closeEvent(self, event):
        """
        Save the rotated DesignPC and close the viewer.
        """
        self.save_design_pc()
        print("Application closed. Rotated DesignPC saved.")
        super().closeEvent(event)


if __name__ == "__main__":
    import sys

    # File paths for point clouds
    design_pc_path = r"C:\Users\ovikd\Documents\Punktskyer\DesignPC_rotated.ply"
    scanned_pc_path = r"C:\Users\ovikd\Documents\Punktskyer\ScannedCropped0.ply"

    # Create the application and main window
    app = QApplication(sys.argv)
    viewer = PointCloudVisualizer(design_pc_path, scanned_pc_path)
    viewer.show()

    # Run the application
    sys.exit(app.exec_())
