# project_manager.py

import os
from datetime import datetime
import shutil  # Import shutil for deleting directories
import logging
import re
import open3d as o3d

class ProjectManager:
    def __init__(self, output_dir):
        """
        Initialize the ProjectManager with the specified output directory.
        """
        self.output_dir = output_dir
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

        :param scan_folder_path: Path to the scan folder where the point cloud will be saved.
        :param point_cloud: Open3D PointCloud object to be saved.
        :return: Path to the saved point cloud file.
        """
        try:
            # Determine the scan number from the scan folder name
            scan_folder_name = os.path.basename(scan_folder_path)
            match = re.match(r'scan_(\d+)', scan_folder_name)
            if not match:
                self.logger.error(f"Scan folder '{scan_folder_name}' does not follow the naming convention 'scan_n'.")
                raise ValueError(f"Invalid scan folder name: {scan_folder_name}")
            scan_number = match.group(1)

            # Define the point cloud filename
            point_cloud_filename = f"scan_{scan_number}.ply"
            point_cloud_path = os.path.join(scan_folder_path, point_cloud_filename)

            # Save the point cloud using Open3D
            o3d.io.write_point_cloud(point_cloud_path, point_cloud)
            self.logger.info(f"Point cloud saved at {point_cloud_path}.")

            return point_cloud_path
        except Exception as e:
            self.logger.error(f"Failed to save point cloud: {e}")
            raise e
