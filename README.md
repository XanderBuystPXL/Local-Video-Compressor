# Local Video Compressor

This is a fun little side project created to locally compress any video to a desired filesize while dynamically preserving the highest perceived quality.

## Features

- Drag and drop interface for easy video selection.
- Set a target filesize limit to perfectly match constraints like email attachments.
- Intelligently downscales video resolution and adjusts bitrates using ffprobe and a 2-pass libx264 encode.
- Fully containerized with Docker for easy local execution.

## Getting Started

### Prerequisites

- Docker Desktop or Docker Engine installed on your system.

### Running the Application

1. Clone this repository or download the source code.
2. Open a terminal or PowerShell in the project directory.
3. Run the following command to build and start the Docker container:
   `docker-compose up --build -d`
4. Open your web browser and navigate to `http://localhost:8000`.
5. Drag, drop, and compress your videos locally.

## Built With

- Python
- FastAPI
- FFmpeg
- Docker
