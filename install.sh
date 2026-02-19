#!/bin/bash

echo "========================================"
echo "Dataset Visualization Tool - Installer"
echo "========================================"
echo

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found!"
    echo "Please install Python 3.8+ from python.org"
    echo
    exit 1
fi

echo "[1/3] Creating virtual environment..."
python3 -m venv venv

echo "[2/3] Installing dependencies..."
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "[3/3] Setup complete!"
echo
echo "========================================"
echo "Installation successful!"
echo "========================================"
echo
echo "To run the application:"
echo "  1. Run: ./start.sh"
echo "  2. Open browser to: http://localhost:8081"
echo
