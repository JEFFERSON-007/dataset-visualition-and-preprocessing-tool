@echo off
echo ========================================
echo DataLyze
echo ========================================
echo.
echo Starting DataLyze server...
echo Server will be available at: http://localhost:8081
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

call venv\Scripts\activate.bat
python app.py

pause
