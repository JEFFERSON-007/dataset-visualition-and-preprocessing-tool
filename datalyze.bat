@echo off
REM DataLyze CLI Wrapper for Windows

if "%1"=="" (
    echo DataLyze CLI
    echo Usage: datalyze {start|install|build}
    exit /b 1
)

if "%1"=="start" (
    call start.bat
)

if "%1"=="install" (
    call install.bat
)

if "%1"=="build" (
    echo Building DataLyze Executable...
    call venv\Scripts\activate.bat
    python build_exe.py
    echo Build complete. Check dist/ folder.
)
