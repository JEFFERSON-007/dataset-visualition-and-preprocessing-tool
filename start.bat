@echo off
echo ========================================
echo Dataset Visualization Tool
echo ========================================
echo.
echo Starting server...
echo Server will be available at: http://localhost:8081
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

call venv\Scripts\activate.bat
python app.py

pause
