@echo off
setlocal
echo ==================================================
echo   DataLyze Installer
echo ==================================================
echo.

:: 1. Define Paths
set "SOURCE_EXE=%~dp0dist\DataLyze.exe"
set "INSTALL_DIR=%LOCALAPPDATA%\DataLyze"
set "TARGET_EXE=%INSTALL_DIR%\DataLyze.exe"
set "SHORTCUT_NAME=DataLyze.lnk"

:: 2. Check if source exists
if not exist "%SOURCE_EXE%" (
    echo [ERROR] Could not find dist\DataLyze.exe
    echo Please run 'datalyze.bat build' first!
    pause
    exit /b 1
)

:: 3. Create Install Directory
echo [1/4] Creating installation directory...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: 4. Copy Executable
echo [2/4] Copying files...
copy /Y "%SOURCE_EXE%" "%TARGET_EXE%" >nul
if errorlevel 1 (
    echo [ERROR] Failed to copy files.
    pause
    exit /b 1
)

:: 5. Create Start Menu Shortcut (using PowerShell)
echo [3/4] Creating Start Menu shortcut...
set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "PS_SCRIPT=%TEMP%\CreateShortcut.ps1"
echo $WshShell = New-Object -comObject WScript.Shell > "%PS_SCRIPT%"
echo $Shortcut = $WshShell.CreateShortcut("%START_MENU%\%SHORTCUT_NAME%") >> "%PS_SCRIPT%"
echo $Shortcut.TargetPath = "%TARGET_EXE%" >> "%PS_SCRIPT%"
echo $Shortcut.WorkingDirectory = "%INSTALL_DIR%" >> "%PS_SCRIPT%"
echo $Shortcut.Description = "DataLyze - Premium EDA Tool" >> "%PS_SCRIPT%"
echo $Shortcut.Save() >> "%PS_SCRIPT%"
powershell -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

:: 6. Create Desktop Shortcut
echo [4/4] Creating Desktop shortcut...
set "DESKTOP=%USERPROFILE%\Desktop"
echo $WshShell = New-Object -comObject WScript.Shell > "%PS_SCRIPT%"
echo $Shortcut = $WshShell.CreateShortcut("%DESKTOP%\%SHORTCUT_NAME%") >> "%PS_SCRIPT%"
echo $Shortcut.TargetPath = "%TARGET_EXE%" >> "%PS_SCRIPT%"
echo $Shortcut.WorkingDirectory = "%INSTALL_DIR%" >> "%PS_SCRIPT%"
echo $Shortcut.Description = "DataLyze - Premium EDA Tool" >> "%PS_SCRIPT%"
echo $Shortcut.Save() >> "%PS_SCRIPT%"
powershell -ExecutionPolicy Bypass -File "%PS_SCRIPT%"

:: Cleanup
del "%PS_SCRIPT%"

echo.
echo ==================================================
echo   Installation Complete! 🚀
echo ==================================================
echo.
echo You can now find DataLyze in your Start Menu and Desktop.
echo.
pause
