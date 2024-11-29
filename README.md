# automated-3d-scanning

# 3D Scanner Control Panel

## Overview

The **3D Scanner Control Panel** is a web-based interface designed to manage and configure a 3D scanning sensor. It provides functionalities to start and stop scans, manage projects, view logs, and visualize point cloud data through an interactive 3D viewer.

## Features

### 3D Scanner Control Panel Interface

- Create a web-based control panel for a 3D scanner using Flask as the backend and HTML/JavaScript for the frontend.
- The control panel allows users to start and stop scans, manage projects, and view logs.

### Project Management

- Implement functionality to create, rename, and delete projects.
- Each project can contain multiple scans, and scans are saved with incremental filenames.

### 3D Point Cloud Preview

- Implement functionality to fetch and display 3D point clouds using Three.js.
- Provide a preview of the point cloud in a SweetAlert2 popup when a button is clicked.

### Scanner Configuration

- Manage scanner configurations using a `Configurations` class.
- Allow users to update configurations through the web interface.

### Logging and Error Handling

- Set up logging to capture and display logs in the web interface.
- Handle errors gracefully and provide feedback to the user.

### Backend Routes

- Define Flask routes to handle various operations such as fetching logs, starting/stopping scans, and managing projects.
- Implement routes to process and return point cloud data.

### Concurrency and Thread Safety

- Use threading and locks to ensure thread safety during scanner operations.
- Use a `ThreadPoolExecutor` to manage concurrent tasks.

### Scanner SDK Integration

- Integrate with the scanner's SDK to perform operations such as connecting to the scanner, configuring it, and acquiring point clouds.
- Handle SDK-specific error codes and provide meaningful error messages.

## Key Files and Their Roles

### app.py

- Main Flask application file that initializes the app, sets up logging, and registers routes.

### project_manager.py

- Manages project-related operations such as creating, renaming, deleting projects, and saving scans.

### scanner_interface.py

- Provides an interface to interact with the 3D scanner using its SDK.
- Includes functionality to connect to the scanner, configure it, perform scans, and handle point cloud data.

### configurations.py

- Manages scanner configurations, including reading, validating, and updating configuration parameters.

### config_routes.py

- Defines routes for handling configuration management operations.

### index.html

- Main HTML file for the control panel interface.
- Includes sections for scan controls, project management, configurations, and logs.

### scripts.js

- Contains JavaScript functions for handling the control panel interface, including starting/stopping scans, managing projects, and updating configurations.

### preview.js

- Contains JavaScript functions for loading and displaying 3D point clouds using Three.js.

## Getting Started

### Prerequisites

- Python 3.x
- Flask
- Open3D
- Three.js and other JavaScript dependencies

