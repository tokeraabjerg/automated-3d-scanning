# project_manager.py

import os
from datetime import datetime
import shutil  # Import shutil for deleting directories
import logging
import re
import open3d as o3d
import numpy as np
import json
from typing import Optional

class ProjectManager:
    def __init__(self, output_dir, config_manager):
        """
        Initialize the ProjectManager with the specified output directory and configuration manager.
        """
        self.output_dir = output_dir
        self.config_manager = config_manager  # Store the injected config_manager
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"ProjectManager initialized with output directory: {self.output_dir}")

    def is_valid_project_name(self, name):
        """
        Validate the project name to prevent path traversal and invalid characters.
        Allow only alphanumeric characters, underscores, and hyphens.
        """
        pattern = re.compile(r'^[A-Za-z0-9_-]+$')
        return bool(pattern.match(name))

    def load_projects(self):
        """
        Load and return a list of current projects (directories) in the output directory.
        """
        projects = [
            d for d in os.listdir(self.output_dir)
            if os.path.isdir(os.path.join(self.output_dir, d))
        ]
        return projects

    def create_project(self, name=None):
        """
        Create a new project directory.
        If no name is provided, use the current timestamp as the project name.
        Returns the name of the created project.
        """
        if not name:
            name = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.logger.info(f"No project name provided. Generated name: {name}")
        if not self.is_valid_project_name(name):
            self.logger.error(f"Invalid project name: {name}")
            raise ValueError("Invalid project name. Only letters, numbers, underscores, and hyphens are allowed.")
        new_project_path = os.path.join(self.output_dir, name)
        if os.path.exists(new_project_path):
            self.logger.error(f"Project '{name}' already exists.")
            raise FileExistsError(f"Project '{name}' already exists.")
        try:
            os.makedirs(new_project_path)
            self.logger.info(f"Successfully created project directory: {new_project_path}")
            return name
        except Exception as e:
            self.logger.error(f"Exception occurred while creating project '{name}': {e}")
            raise e

    def rename_project(self, old_name, new_name):
        """
        Rename an existing project directory from old_name to new_name.
        """
        if not self.is_valid_project_name(new_name):
            self.logger.error(f"Invalid new project name: {new_name}")
            raise ValueError("Invalid new project name. Only letters, numbers, underscores, and hyphens are allowed.")
        old_path = os.path.join(self.output_dir, old_name)
        new_path = os.path.join(self.output_dir, new_name)
        if not os.path.exists(old_path):
            self.logger.error(f"Project '{old_name}' does not exist.")
            raise FileNotFoundError(f"Project '{old_name}' does not exist.")
        if os.path.exists(new_path):
            self.logger.error(f"Project '{new_name}' already exists.")
            raise FileExistsError(f"Project '{new_name}' already exists.")
        try:
            os.rename(old_path, new_path)
            self.logger.info(f"Successfully renamed project from '{old_name}' to '{new_name}'.")
        except Exception as e:
            self.logger.error(f"Exception occurred while renaming project '{old_name}' to '{new_name}': {e}")
            raise e

    def delete_project(self, project_name):
        """
        Delete an existing project directory.
        """
        if not self.is_valid_project_name(project_name):
            self.logger.error(f"Invalid project name: {project_name}")
            raise ValueError("Invalid project name.")
        project_path = os.path.join(self.output_dir, project_name)
        if not os.path.exists(project_path):
            self.logger.error(f"Project '{project_name}' does not exist.")
            raise FileNotFoundError(f"Project '{project_name}' does not exist.")
        if not os.path.isdir(project_path):
            self.logger.error(f"Path '{project_path}' is not a directory.")
            raise NotADirectoryError(f"Path '{project_path}' is not a directory.")
        try:
            shutil.rmtree(project_path)
            self.logger.info(f"Successfully deleted project: {project_name}")
        except Exception as e:
            self.logger.error(f"Error deleting project '{project_name}': {e}")
            raise e

    def get_next_scan_number(self, project_name):
        """
        Determine the next scan number for the given project.
        Scans are named as 'scan_1', 'scan_2', etc.
        """
        project_path = os.path.join(self.output_dir, project_name)
        if not os.path.exists(project_path):
            self.logger.error(f"Project '{project_name}' does not exist.")
            raise FileNotFoundError(f"Project '{project_name}' does not exist.")
        existing_scans = [
            d for d in os.listdir(project_path)
            if os.path.isdir(os.path.join(project_path, d)) and d.startswith('scan_')
        ]
        scan_numbers = []
        for scan in existing_scans:
            try:
                num = int(scan.split('_')[1])
                scan_numbers.append(num)
            except (IndexError, ValueError):
                continue  # Ignore folders that don't follow the naming convention
        next_scan_number = max(scan_numbers, default=0) + 1
        self.logger.info(f"Next scan number for project '{project_name}': {next_scan_number}")
        return next_scan_number

    def create_scan_folder(self, project_name):
        """
        Create a new scan folder within the specified project.
        Returns the path to the new scan folder.
        """
        next_scan_number = self.get_next_scan_number(project_name)
        scan_folder_name = f"scan_{next_scan_number}"
        scan_folder_path = os.path.join(self.output_dir, project_name, scan_folder_name)
        try:
            os.makedirs(scan_folder_path)
            self.logger.info(f"Created scan folder: {scan_folder_path}")
            return scan_folder_path
        except Exception as e:
            self.logger.error(f"Failed to create scan folder '{scan_folder_path}': {e}")
            raise e

    def save_scan(self, scan_folder_path: str, point_cloud: o3d.geometry.PointCloud) -> str:
        """
        Save the provided point cloud into the specified scan folder with proper enumeration.
        Additionally, save a reduced point cloud for previewing.

        :param scan_folder_path: Path to the scan folder where the point cloud will be saved.
        :param point_cloud: Open3D PointCloud object to be saved.
        :return: Path to the saved full point cloud file.
        """
        try:
            # Determine the scan number from the scan folder name
            scan_folder_name = os.path.basename(scan_folder_path)
            match = re.match(r'scan_(\d+)', scan_folder_name)
            if not match:
                self.logger.error(f"Scan folder '{scan_folder_name}' does not follow the naming convention 'scan_n'.")
                raise ValueError(f"Invalid scan folder name: {scan_folder_name}")
            scan_number = match.group(1)

            # Define the full point cloud filename
            full_pcd_filename = f"scan_{scan_number}.ply"
            full_pcd_path = os.path.join(scan_folder_path, full_pcd_filename)

            # Save the full point cloud using Open3D
            o3d.io.write_point_cloud(full_pcd_path, point_cloud)
            self.logger.info(f"Full point cloud saved at {full_pcd_path}.")

            # Create and save the reduced point cloud
            reduced_pcd = self.reduce_point_cloud(point_cloud)
            reduced_pcd_filename = f"scan_{scan_number}_reduced.ply"
            reduced_pcd_path = os.path.join(scan_folder_path, reduced_pcd_filename)
            o3d.io.write_point_cloud(reduced_pcd_path, reduced_pcd)
            self.logger.info(f"Reduced point cloud saved at {reduced_pcd_path}.")

            return full_pcd_path
        except Exception as e:
            self.logger.error(f"Failed to save point cloud: {e}")
            raise e

    def reduce_point_cloud(self, point_cloud: o3d.geometry.PointCloud, target_points: int = 100000) -> o3d.geometry.PointCloud:
        """
        Reduce the point cloud to have approximately target_points using voxel downsampling.

        :param point_cloud: The original Open3D PointCloud.
        :param target_points: The desired number of points after reduction.
        :return: The reduced Open3D PointCloud.
        """
        try:
            num_points = len(point_cloud.points)

            if num_points <= target_points:
                return point_cloud

            # Estimate voxel size by scaling based on the ratio of target_points to current points
            ratio = (num_points / target_points) ** (1/3)  # Assuming uniform scaling
            voxel_size = 0.1 * ratio  # Base voxel size is 0.1, adjust as needed
            voxel_size = max(voxel_size, 0.01)  # Set a minimum voxel size

            reduced_pcd = point_cloud.voxel_down_sample(voxel_size=voxel_size)

            # If the downsampled point cloud is still larger than target_points, apply another round of downsampling
            while len(reduced_pcd.points) > target_points:
                voxel_size *= 1.1  # Increase voxel size slightly
                reduced_pcd = reduced_pcd.voxel_down_sample(voxel_size=voxel_size)

            return reduced_pcd
        except Exception as e:
            self.logger.error(f"Error reducing point cloud: {e}")
            raise e
    
    def save_point_cloud(self, pcd: o3d.geometry.PointCloud, project_name: str, save_as_main: bool = False):
        """
        Save the point cloud to the specified project's folder with an incremental filename.
        If save_as_main is True, save the point cloud as scan_main.ply.
        
        :param pcd: The Open3D point cloud to save.
        :param project_name: The name of the current project.
        :param save_as_main: Boolean indicating whether to save the point cloud as scan_main.ply.
        """
        project_path = os.path.join(self.output_dir, project_name)
        os.makedirs(project_path, exist_ok=True)
        
        if save_as_main:
            output_filename = os.path.join(project_path, "scan_main.ply")
        else:
            # Determine the next scan number
            scan_files = [
                f for f in os.listdir(project_path)
                if os.path.isfile(os.path.join(project_path, f)) and f.startswith('scan_') and f.endswith('.ply')
            ]
            scan_numbers = [int(f.split('_')[1].split('.')[0]) for f in scan_files if f.split('_')[1].split('.')[0].isdigit()]
            next_scan_number = max(scan_numbers, default=0) + 1
            output_filename = os.path.join(project_path, f"scan_{next_scan_number}.ply")
        
        try:
            # Save the point cloud
            o3d.io.write_point_cloud(output_filename, pcd)
            self.logger.info(f"Saved point cloud to {output_filename}")
        except Exception as e:
            self.logger.error(f"Failed to save point cloud: {e}")

    def get_scan_count(self, project_name):
        """
        Get the number of scans in the specified project.
        """
        project_path = os.path.join(self.output_dir, project_name)
        if not os.path.exists(project_path):
            self.logger.error(f"Project '{project_name}' does not exist.")
            raise FileNotFoundError(f"Project '{project_name}' does not exist.")
        
        scan_files = [
            f for f in os.listdir(project_path)
            if os.path.isfile(os.path.join(project_path, f)) and f.startswith('scan_') and f.endswith('.ply')
        ]
        return len(scan_files)

    def get_scan_preview(self, project_name, scan_file):
        """
        Get a downsampled preview of the specified scan in the project.
        """
        project_path = os.path.join(self.output_dir, project_name)
        if not os.path.exists(project_path):
            self.logger.error(f"Project '{project_name}' does not exist.")
            raise FileNotFoundError(f"Project '{project_name}' does not exist.")

        scan_filepath = os.path.join(project_path, f"{scan_file}.ply")
        if not os.path.exists(scan_filepath):
            self.logger.warning(f"Scan file '{scan_file}.ply' does not exist in project '{project_name}'.")
            return None  # Return None instead of raising an error

        try:
            # Load the point cloud
            point_cloud = o3d.io.read_point_cloud(scan_filepath)
            # Downsample the point cloud for preview
            downsampled_pcd = self.reduce_point_cloud(point_cloud, target_points=100000)  # Adjust target points
            # Convert the downsampled point cloud to a format suitable for JSON response
            downsampled_points = np.asarray(downsampled_pcd.points).tolist()
            downsampled_intensities = np.asarray(downsampled_pcd.colors)[:, 0].tolist()  # Assuming intensity is stored in colors
            self.logger.info(f"Returning reduced point cloud for scan '{scan_file}.ply' with {len(downsampled_points)} points.")
            return {'points': downsampled_points, 'intensities': downsampled_intensities}
        except Exception as e:
            self.logger.error(f"Error getting scan preview for '{scan_file}.ply': {e}")
            raise e

    def get_full_size_point_cloud(self, project_name, scan_index, downsample=False, target_points=100000):
        """
        Get the full-size point cloud for the specified scan in the project.
        Optionally downsample the point cloud to reduce its size.
        """
        project_path = os.path.join(self.output_dir, project_name)
        if not os.path.exists(project_path):
            self.logger.error(f"Project '{project_name}' does not exist.")
            raise FileNotFoundError(f"Project '{project_name}' does not exist.")

        # Handle scan_main for index 0
        scan_filename = "scan_main.ply" if scan_index == 0 else f"scan_{scan_index}.ply"
        scan_filepath = os.path.join(project_path, scan_filename)
        if not os.path.exists(scan_filepath):
            self.logger.error(f"Scan file '{scan_filename}' does not exist in project '{project_name}'.")
            raise FileNotFoundError(f"Scan file '{scan_filename}' does not exist in project '{project_name}'.")

        try:
            # Load the full-size point cloud
            point_cloud = o3d.io.read_point_cloud(scan_filepath)
            self.logger.info(f"Returning full-size point cloud for scan '{scan_filename}' with {len(point_cloud.points)} points.")
            
            if downsample:
                point_cloud = self.reduce_point_cloud(point_cloud, target_points)
                self.logger.info(f"Downsampled point cloud to {len(point_cloud.points)} points.")

            points = np.asarray(point_cloud.points).tolist()
            intensities = np.asarray(point_cloud.colors)[:, 0].tolist()  # Assuming intensity is stored in colors

            return {'points': points, 'intensities': intensities}
        except Exception as e:
            self.logger.error(f"Error getting full-size point cloud for '{scan_filename}': {e}")
            raise e

    def get_positions(self, project_name):
        """
        Retrieve the contents of positions.json for the specified project.
        """
        self.logger.debug(f"get_positions called for project: {project_name}")
        project_path = os.path.join(self.output_dir, project_name)
        positions_file = os.path.join(project_path, 'positions.json')

        if not os.path.exists(positions_file):
            self.logger.warning(f"positions.json not found for project '{project_name}'.")
            return None

        try:
            with open(positions_file, 'r') as file:
                positions = json.load(file)
                self.logger.info(f"Retrieved {len(positions)} positions for project '{project_name}'.")
                return positions
        except Exception as e:
            self.logger.error(f"Error reading positions.json for project '{project_name}': {e}")
            return None

    def delete_scan_files(self, project_name):
        """
        Delete only scan files (scan_main and scan_i) in the specified project directory.
        """
        project_path = os.path.join(self.output_dir, project_name)
        if not os.path.exists(project_path):
            self.logger.error(f"Project '{project_name}' does not exist.")
            raise FileNotFoundError(f"Project '{project_name}' does not exist.")

        try:
            for file_name in os.listdir(project_path):
                if file_name.startswith("scan_") and file_name.endswith(".ply"):
                    file_path = os.path.join(project_path, file_name)
                    os.remove(file_path)
                    self.logger.info(f"Deleted scan file: {file_path}")
        except Exception as e:
            self.logger.error(f"Error deleting scan files in project '{project_name}': {e}")
            raise e

    def update_positions_with_relative_angles(self, project_name):
        """
        Update positions.json with relative angle changes for each entry compared to the first entry.
        Append the values under each entry as deg_a and deg_b.
        """
        positions_file = os.path.join(self.output_dir, project_name, 'positions.json')
        if not os.path.exists(positions_file):
            self.logger.error(f"positions.json not found for project '{project_name}'.")
            raise FileNotFoundError(f"positions.json not found for project '{project_name}'.")

        try:
            with open(positions_file, 'r') as file:
                positions = json.load(file)

            if not positions:
                self.logger.error(f"No positions found in positions.json for project '{project_name}'.")
                raise ValueError(f"No positions found in positions.json for project '{project_name}'.")

            # Determine the base positions
            base_pos_a = None
            base_pos_b = None
            for position in positions:
                if position.get("home"):
                    base_pos_a = position.get('pos_a', 2716)
                    base_pos_b = position.get('pos_b', 619)
                    break

            if base_pos_a is None or base_pos_b is None:
                self.logger.error(f"No home position found in positions.json for project '{project_name}'.")
                raise ValueError(f"No home position found in positions.json for project '{project_name}'.")

            steps_per_degree = 19.5

            for position in positions:
                if position.get("home"):
                    position['deg_a'] = 0
                    position['deg_b'] = 0
                elif 'pos_a' in position and 'pos_b' in position:
                    relative_deg_a = (position['pos_a'] - base_pos_a) / steps_per_degree
                    relative_deg_b = (position['pos_b'] - base_pos_b) / steps_per_degree
                    position['deg_a'] = relative_deg_a
                    position['deg_b'] = relative_deg_b

            # Save the updated positions back to positions.json
            with open(positions_file, 'w') as file:
                json.dump(positions, file, indent=4)

            self.logger.info(f"Updated positions.json with relative angles for project '{project_name}'.")

            return positions  # Ensure this returns the updated positions list
        except Exception as e:
            self.logger.error(f"Error updating positions.json for project '{project_name}': {e}")
            raise e

    def save_current_configurations(self, project_name: str):
        """
        Retrieve current scanner configurations and save them to the specified project as configurations.json.

        :param project_name: The name of the project where configurations will be saved.
        """
        try:
            if not self.config_manager:
                self.logger.error("Configuration manager is not available.")
                return False

            # Read all configurations
            configurations = self.config_manager.read_all_configurations()

            # Define the path to save the configurations.json
            project_path = os.path.join(self.output_dir, project_name)
            if not os.path.exists(project_path):
                self.logger.error(f"Project '{project_name}' does not exist.")
                return False

            configurations_path = os.path.join(project_path, 'configurations.json')
            with open(configurations_path, 'w') as config_file:
                json.dump(self.config_manager.configurations, config_file, indent=4)

            self.logger.info(f"Configurations saved successfully at {configurations_path}.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save configurations: {e}")
            return False

