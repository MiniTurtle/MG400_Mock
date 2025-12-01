#!/bin/bash

# autostart.sh

# Ensure the script exits on errors
set -e

# Catch both SIGINT (Ctrl+C) and SIGTERM (task close)
cleanup() {
    echo "Stopping Docker containers..."
    sudo docker compose -f docker/docker-compose.yml down -v
    exit 0
}

trap cleanup SIGINT SIGTERM

sudo docker compose -f docker/docker-compose.yml up