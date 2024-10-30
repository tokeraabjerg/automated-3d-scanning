# Docker Container Setup Using Docker Desktop UI

This guide will help you set up a Docker image and container using Docker Desktop UI, starting from a Dockerfile. The process includes building the image, configuring binds, mapping ports, and starting the container to run a Flask web application.

### Prerequisites
- Docker Desktop is installed and running on your Mac.
- You have the Dockerfile and all necessary files in the project directory.

### Step 1: Prepare Your Project Directory

1. **Place the Dockerfile in the Project Directory**:
   - Ensure the Dockerfile is saved in the root of your project directory, which contains all necessary files such as `app.py`.

   Example of your project directory structure:
   ```
   /Users/tokeraabjerg/Dropbox/Skole/Universitet/5. Semester/MP5 Projekt/automation-3d-scanning/automated-3d-scanning
   ├── Dockerfile
   ├── python
   │   ├── app.py
   │   └── (other project files)
   └── (other files)
   ```

### Step 2: Build a Docker Image Using Docker Desktop

1. **Open Docker Desktop**:
   - Start Docker Desktop and navigate to the **Dashboard**.

2. **Create a New Image**:
   - Click on the **Images** tab.
   - On the top right, click the **Add** button and select **Build** from the dropdown.

3. **Specify Build Context and Dockerfile**:
   - **Context Directory**: Enter the path to your project directory where the Dockerfile is located. Example:
     ```
     /Users/tokeraabjerg/Dropbox/Skole/Universitet/5. Semester/MP5 Projekt/automation-3d-scanning/automated-3d-scanning
     ```
   - **Dockerfile Path**: Docker Desktop should automatically detect `Dockerfile` if it's in the specified context directory.

4. **Set Image Name and Tags**:
   - **Image Name**: Set a descriptive name, for example, `automated-scanner`.
   - **Tag**: Use a version tag such as `latest` or `v1`.

5. **Click "Build"**:
   - Click the **Build** button to create the Docker image.
   - Docker will use the provided Dockerfile to create an image. The progress will be displayed in Docker Desktop.

### Step 3: Verify the Built Image

- After the build completes, navigate to the **Images** tab.
- You should see the new image (e.g., `automated-scanner:latest`) listed.

### Step 4: Create a Container from the Docker Image

1. **Click on "Run"**:
   - In the **Images** tab, click the **Run** button next to the `automated-scanner` image to create a new container.

2. **Configure Container Settings**:

   - **Container Name**: Optionally set a name for your container, e.g., `automated-scanner-container`.
   - **Port Configuration**:
     - Add a port mapping to access the Flask app.
     - Set **Host Port** to `5001` and **Container Port** to `5001` to allow access to the web application.
   - **Volume Bind Configuration**:
     - Add a **bind mount** to link a directory on your computer to a directory inside the container. This will allow you to share files between the local machine and the container.
     - **Host Path**: Enter the absolute path to your project directory:
       ```
       /Users/tokeraabjerg/Dropbox/Skole/Universitet/5. Semester/MP5 Projekt/automation-3d-scanning/automated-3d-scanning
       ```
     - **Container Path**: Set it as `/workspace` so that the files are accessible inside the container at this location.
   - **Platform Compatibility**:
     - Make sure to set the platform to `linux/amd64` in the advanced settings to match the Dockerfile specification.

3. **Start the Container**:
   - After configuring all settings, click **Run** to start the container.

### Step 5: Verify Container Status and Access Flask Application

- **Check Container Status**:
  - Go to the **Containers** tab to verify that your container is running. It should show the container with a green indicator for running.
  
- **Access the Flask Web Application**:
  - Open a web browser and navigate to `http://localhost:5001`.
  - If everything is configured correctly, you should see the Flask application running.

### Troubleshooting Tips

- **Port Issues**:
  - Ensure the port `5001` is available and not in use by another service.
  
- **Volume Permissions**:
  - Make sure Docker Desktop has permissions to access the specified local directory, particularly if you're running on macOS. You may need to grant Docker access in the **Settings** > **Resources** > **File Sharing** section of Docker Desktop.

### Summary of Steps

1. **Open Docker Desktop** and navigate to the **Images** tab.
2. **Build a new image** from the Dockerfile by specifying the project directory as the build context.
3. **Run the image** to create a container, ensuring proper **port mapping** (`5001:5001`) and **volume bind** (`/workspace`).
4. **Access the web app** at `http://localhost:5001`.

This process will allow you to set up and run your containerized Flask application using Docker Desktop UI from scratch.

