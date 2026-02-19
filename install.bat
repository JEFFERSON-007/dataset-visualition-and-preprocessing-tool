@echo off
echo ========================================
echo DataLyze - Installer
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.8+ from python.org
    echo.
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment...
python -m venv venv

echo [2/3] Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [3/3] Setup complete!
echo.
echo ========================================
echo DataLyze installation successful!
echo ========================================
echo.
echo To run the application:
echo   1. Double-click: start.bat
echo   2. Open browser to: http://localhost:8081
echo.
pause
