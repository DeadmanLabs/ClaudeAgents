#!/bin/bash

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker and try again."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Start the dashboard
echo "Starting Claude Agents Dashboard..."
docker-compose up --build

# Handle Ctrl+C gracefully
trap 'docker-compose down' INT TERM

echo "Claude Agents Dashboard is now running at http://localhost:5173"