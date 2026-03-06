#!/bin/bash

# Support Assistant Runner Script
# Activates the virtual environment and starts the assistant

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running setup first..."
    ./setup.sh
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and configure your credentials."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Run the assistant
echo "Starting Support Assistant..."
python main.py
