#!/bin/bash

#cd "$(dirname "$0")/.." || exit

# Create the venv (if it doesn't exist yet)
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the venv
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Downloading requirements..."
pip install -r requirements.txt

echo "Setup complete."