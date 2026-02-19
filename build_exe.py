import PyInstaller.__main__
import os
import shutil

# Ensure we are in the right directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

print("🚀 Building DataLyze.exe for Windows...")

# PyInstaller arguments
args = [
    'app.py',                           # Main script
    '--name=DataLyze',                  # Executable name
    '--onefile',                        # Single exe file
    '--clean',                          # Clean cache
    '--add-data=static;static',         # Include static files
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=uvicorn',
    '--hidden-import=fastapi',
    '--hidden-import=sklearn',          # For ML features
    '--hidden-import=sklearn.impute',
    '--hidden-import=sklearn.preprocessing',
    '--hidden-import=sklearn.pipeline',
    '--hidden-import=sklearn.compose',
]

# Run PyInstaller
try:
    PyInstaller.__main__.run(args)
    print("\n✅ Build Successful!")
    print(f"📁 Executable located at: {os.path.join(BASE_DIR, 'dist', 'DataLyze.exe')}")
except Exception as e:
    print(f"\n❌ Build Failed: {e}")
