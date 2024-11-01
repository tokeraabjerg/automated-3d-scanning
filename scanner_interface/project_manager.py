# project_manager.py

import os
from datetime import datetime

class ProjectManager:
    def __init__(self, output_dir):
        """
        Initialize the ProjectManager with the specified output directory.
        """
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

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
        new_project_path = os.path.join(self.output_dir, name)
        if os.path.exists(new_project_path):
            raise FileExistsError(f"Project '{name}' already exists.")
        os.makedirs(new_project_path)
        return name

    def rename_project(self, old_name, new_name):
        """
        Rename an existing project directory from old_name to new_name.
        """
        old_path = os.path.join(self.output_dir, old_name)
        new_path = os.path.join(self.output_dir, new_name)
        if not os.path.exists(old_path):
            raise FileNotFoundError(f"Project '{old_name}' does not exist.")
        if os.path.exists(new_path):
            raise FileExistsError(f"Project '{new_name}' already exists.")
        os.rename(old_path, new_path)
