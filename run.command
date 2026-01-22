#!/bin/bash

# Navigate to the exact folder where THIS file is located
cd "$(dirname "$0")" || exit

# Activate venv
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Error: 'venv' folder not found here."
    echo "Make sure the virtual environment is set up."
    read -p "Press Enter to exit..."
    exit 1
fi

# Run the Python program
echo "Starting application..."
python3 interface.py