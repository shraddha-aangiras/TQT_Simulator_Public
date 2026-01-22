#!/bin/bash

# 1. Create the venv (if it doesn't exist yet)
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 2. Activate the venv
echo "Activating virtual environment..."
source venv/bin/activate
echo "Downloading requirements"
pip install -r requirements.txt
