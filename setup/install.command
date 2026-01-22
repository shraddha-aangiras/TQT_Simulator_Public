#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$PROJECT_ROOT/venv"
fi

echo "Activating virtual environment..."
source "$PROJECT_ROOT/venv/bin/activate"

pip install -r "$PROJECT_ROOT/requirements.txt"
echo "Setup complete."