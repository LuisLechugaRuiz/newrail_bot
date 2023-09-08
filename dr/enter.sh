#!/bin/bash

# Store the current directory
CURRENT_DIR=$(pwd)

# Change to the current directory
cd "$(dirname "$0")"

# Set your container name
CONTAINER_NAME="newrail"

# Check if the container is running
CONTAINER_STATUS=$(docker container inspect -f '{{.State.Status}}' $CONTAINER_NAME 2>/dev/null)

if [ "$CONTAINER_STATUS" != "running" ]; then
  # Container is not running, start Docker Compose
  echo "Container is not running. Starting Docker Compose..."
  docker-compose up -d
  echo "Docker Compose started. Entering the container..."
fi

# Enter the container with poetry venv loaded - small hack
docker exec -it $CONTAINER_NAME /bin/bash -c "poetry run /bin/bash"

# Restore the original directory
cd "$CURRENT_DIR"
