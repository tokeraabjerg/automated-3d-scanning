# Docker Container Setup Using Command Line and Docker Desktop UI

**NOTE! This is only required if you wish to run the repository on macOS; it is Apple Silicon compatible!**

This guide will help you set up a Docker image and container by building the image using the command line and then running it using the Docker Desktop UI. The process includes building the image via the command line, configuring binds, mapping ports, and starting the container to run a Flask web application.

## Prerequisites

- Docker Desktop is installed and running on your Mac.
- You have the Dockerfile and all necessary files in the project directory.
- Access to the command line (Terminal) on your Mac.

## Step 1: Prepare Your Project Directory

1. **Place the Dockerfile in the Project Directory**:

   - Ensure the Dockerfile is saved in the root of your project directory, which contains all necessary files such as `app.py`.

   Example of your project directory structure:

   ```
   /Users/yourusername/path/to/your/project
   ├── Dockerfile
   ├── scanner_interface
   │   ├── app.py
   │   └── (other project files)
   └── (other files)
   ```

## Step 2: Build the Docker Image Using Command Line

1. **Open Terminal**:

   - Open the Terminal application on your Mac.

2. **Navigate to Your Project Directory**:

   - Use the `cd` command to navigate to the directory where your Dockerfile is located. For example:

     ```bash
     cd /Users/yourusername/path/to/your/project
     ```

3. **Build the Docker Image**:

   - Run the `docker build` command to build your image. Replace `yourimagename` with a descriptive name for your image, such as `automated-scanner`.

     ```bash
     docker build -t yourimagename:tag .
     ```

     For example:

     ```bash
     docker build -t automated-scanner:latest .
     ```

     - The `.` at the end specifies the current directory as the build context.
     - `-t` specifies the name and tag for the image (`imagename:tag`).

4. **Wait for the Build to Complete**:

   - Docker will process the Dockerfile and build the image. You will see the progress in the Terminal.

## Step 3: Verify the Built Image

- After the build completes, you can verify that the image was created successfully.

1. **List Docker Images via Command Line**:

   ```bash
   docker images
   ```

   - You should see your image (`automated-scanner:latest`) listed among the images.

2. **Alternatively, Check in Docker Desktop**:

   - Open Docker Desktop and navigate to the **Images** tab.
   - You should see the new image (`automated-scanner:latest`) listed there.

## Step 4: Create a Container from the Docker Image Using Docker Desktop

1. **Open Docker Desktop**:

   - Start Docker Desktop and navigate to the **Images** tab.

2. **Run the Image**:

   - Find your image (`automated-scanner:latest`) in the list.
   - Click the **Run** button next to the image to create a new container.

3. **Configure Container Settings**:

   - **Container Name**: Optionally set a name for your container, e.g., `automated-scanner-container`.
   - **Port Configuration**:
     - Add a port mapping to access the Flask app.
     - Set **Host Port** to `5001` and **Container Port** to `5001` to allow access to the web application.
   - **Volume Bind Configuration**:
     - Add a **bind mount** to link a directory on your computer to a directory inside the container. This will allow you to share files between the local machine and the container.
     - **Host Path**: Enter the absolute path to your project directory:

       ```
       /Users/yourusername/path/to/your/project
       ```

     - **Container Path**: Set it as `/workspace` so that the files are accessible inside the container at this location.
   - **Platform Compatibility**:
     - In the advanced settings, ensure that the platform is set appropriately, e.g., `linux/amd64`, if necessary, to match the Dockerfile specification.

4. **Start the Container**:

   - After configuring all settings, click **Run** to start the container.

## Step 5: Verify Container Status and Access Flask Application

- **Check Container Status**:

  - Go to the **Containers** tab in Docker Desktop to verify that your container is running. It should show the container with a green indicator for running.

- **Access the Flask Web Application**:

  - Open a web browser and navigate to `http://localhost:5001`.
  - If everything is configured correctly, you should see the Flask application running.

## Troubleshooting Tips

- **Port Issues**:

  - Ensure the port `5001` is available and not in use by another service.

- **Volume Permissions**:

  - Make sure Docker Desktop has permissions to access the specified local directory, particularly if you're running on macOS. You may need to grant Docker access in the **Settings** > **Resources** > **File Sharing** section of Docker Desktop.

- **Platform Compatibility**:

  - If you're using an Apple Silicon (M1/M2) Mac, and your image requires `linux/amd64` architecture, ensure that the platform is specified correctly when building and running the image.

## Summary of Steps

1. **Build the Docker Image via Command Line**:

   - Navigate to your project directory in Terminal.
   - Run `docker build -t imagename:tag .` to build the image.

2. **Open Docker Desktop** and navigate to the **Images** tab.

3. **Run the image** to create a container, ensuring proper **port mapping** (`5001:5001`) and **volume bind** (`/workspace`).

4. **Access the web app** at `http://localhost:5001`.

This process will allow you to set up and run your containerized Flask application by building the Docker image via command line and running it using Docker Desktop UI.

