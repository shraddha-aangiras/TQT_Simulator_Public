#!/bin/bash

# Navigate to the project root
cd "$(dirname "$0")/.." || exit

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Error: 'venv' not found."
    echo "Please run the setup script first to create the environment."
    exit 1
fi

# Activate and Run
source venv/bin/activate

# Start app
echo "Starting application..."
python interface.py