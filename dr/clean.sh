#!/bin/bash

# Use this to free up disk space

# Remove all existing docker images
docker rmi $(docker images -q)

# Remove all cache and build artifacts
sudo docker system prune -a
