#!/bin/bash

# Store the current directory
CURRENT_DIR=$(pwd)

# Change to the root directory
cd "$(dirname "$0")/.."

# Pull all dependent Docker images
DEPENDENT_IMAGES=(
    "semitechnologies/weaviate:1.18.3"
    # Add more images here if needed...
)

echo "Pulling dependent Docker images..."
for image in "${DEPENDENT_IMAGES[@]}"; do
    echo "Pulling $image..."
    docker pull $image
done

echo "Building the Docker image for the Python application..."
docker-compose -f dr/docker-compose.yml build --no-cache

# Restore the original directory
cd "$CURRENT_DIR"
