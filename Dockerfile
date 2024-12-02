# Use Ubuntu 20.04 as the base image, specifically targeting amd64 architecture
FROM --platform=linux/amd64 ubuntu:20.04

# Set non-interactive mode for APT
ENV DEBIAN_FRONTEND=noninteractive

# Update package list and install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3 \
        python3-pip \
        libopencv-dev \
        libgl1-mesa-glx \
        libglu1-mesa \
        freeglut3-dev \
        mesa-common-dev \
        nano \
        tree \
        && rm -rf /var/lib/apt/lists/*
        
# Install Python packages without caching
RUN python3 -m pip install --no-cache-dir numpy open3d flask

# Set LD_LIBRARY_PATH environment variable to point to the SDK library
ENV LD_LIBRARY_PATH=/workspace/python/Software_ShapeDriveG4_SDK_Linux/Sensor3D/lib:$LD_LIBRARY_PATH

# Set the working directory to the root of the repository
WORKDIR /workspace

# Copy all files from the host to the container
COPY . /workspace

# Expose port 5001 for the Flask app
EXPOSE 5001

# Command to run when the container starts, specifying the full path to the app.py file
CMD ["python3", "-m", "scanner_interface.app"]
