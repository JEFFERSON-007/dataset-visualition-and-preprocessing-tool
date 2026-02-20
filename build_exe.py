import PyInstaller.__main__
import os
import shutil

# Ensure we are in the right directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

print("Building DataLyze.exe for Windows...")

# PyInstaller arguments
args = [
    'app.py',                           # Main script
    '--name=DataLyze',                  # Executable name
    '--onefile',                        # Single exe file
    '--clean',                          # Clean cache
    '--add-data=static;static',         # Include static files
    
    # Hidden imports for engine
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=uvicorn',
    '--hidden-import=fastapi',
    
    # Aggressively exclude unnecessary modules to reduce size
    '--exclude-module=tkinter',
    '--exclude-module=tcl',
    '--exclude-module=tk',
    '--exclude-module=matplotlib',
    '--exclude-module=notebook',
    '--exclude-module=ipython',
    '--exclude-module=jupyter',
    '--exclude-module=unittest',
    '--exclude-module=test',
    '--exclude-module=pydoc',
    '--exclude-module=pdb',
    '--exclude-module=sklearn',
    '--exclude-module=scipy',
    
    # Optimization
    '--log-level=INFO',
]

# Run PyInstaller
try:
    PyInstaller.__main__.run(args)
    print("\n✅ Build Successful!")
    print(f"📁 Executable located at: {os.path.join(BASE_DIR, 'dist', 'DataLyze.exe')}")
    print("\n👉 To test: Double-click dist/DataLyze.exe")
except Exception as e:
    print(f"\n❌ Build Failed: {e}")
