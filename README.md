# Automated 3D Scanning Control Panel

## Overview

This project provides a web-based control panel for automating 3D scanning using the Wenglor MLAS214 sensor. It allows users to manage scan projects, configure settings, and visualize point cloud data through an intuitive interface.

See it in action:

https://www.youtube.com/watch?v=JDepGS2HYEw

## Features

- **Project Management**: Create, rename, and delete scanning projects.
- **Scan Control**: Initiate scans, preview results, and perform manual post-processing.
- **Configuration Management**: Adjust scanning parameters and save configurations.
- **Visualization**: View and interact with 3D point cloud data directly in the browser.
- **Logging**: Real-time logs for monitoring and troubleshooting.

## Installation

### Prerequisites

- Python 3.x
- Flask
- Open3D
- Docker (optional)

## Usage

1. **Start the Application**:
    ```bash
    pytho -m scanner_interface.app
    ```
2. **Access the Control Panel**:
    - Open a web browser and navigate to `http://localhost:5001`.
    
## Folder Structure

- `scanner_interface/`: Main application code.
  - `app.py`: Initializes the Flask application.
  - `routes/`: Contains route definitions for different functionalities.
  - `static/`: Static assets like JavaScript files and CSS stylesheets.
  - `templates/`: HTML templates for rendering the web interface.
- `docker-setup.md`: Detailed instructions for setting up the application using Docker.
- `overview.md`: Additional documentation and workflow details.
- `python/`: Contains postprocessing scripts to combine point clouds and refine them.


## License

This project is licensed under the MIT License.
