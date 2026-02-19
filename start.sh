#!/bin/bash

echo "========================================"
echo "Dataset Visualization Tool"
echo "========================================"
echo
echo "Starting server..."
echo "Server will be available at: http://localhost:8081"
echo
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo

source venv/bin/activate
python app.py
