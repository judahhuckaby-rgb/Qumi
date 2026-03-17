"""
QEMU GUI - EXE Builder
Just run this file to build the exe!
"""

import subprocess
import sys
import os

def build_exe():
    print("=" * 60)
    print("QEMU Virtual Machine Manager - Building .exe file...")
    print("=" * 60)
    print()
    
    # Check if PyInstaller is installed
    print("Step 1: Checking for PyInstaller...")
    try:
        import PyInstaller
        print("  PyInstaller found!")
    except ImportError:
        print("  PyInstaller not found. Installing now...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("  PyInstaller installed!")
    
    print()
    
    # Check if PySide6 is installed
    print("Step 2: Checking for PySide6...")
    try:
        import PySide6
        print("  PySide6 found!")
    except ImportError:
        print("  PySide6 not found. Installing now...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PySide6"])
        print("  PySide6 installed!")
    
    print()
    
    # Build the exe
    print("Step 3: Building QEMU-GUI.exe...")
    print("This may take 1-2 minutes, please wait...")
    print()
    
    result = subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "QEMU-GUI",
        "qemu_gui.py"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print()
        print("=" * 60)
        print("  BUILD SUCCESSFUL!")
        print("=" * 60)
        print()
        print("Your exe is located at:")
        print(f"  {os.path.abspath('dist/QEMU-GUI.exe')}")
        print()
        print("VM profiles are stored in:")
        print(f"  {os.path.expanduser('~/.qemu-gui/machines/')}")
        print()
        print("You can now:")
        print("  1. Copy QEMU-GUI.exe anywhere you want")
        print("  2. Delete all these Python files")
        print("  3. Just double-click QEMU-GUI.exe to run!")
        print()
    else:
        print()
        print("=" * 60)
        print("  BUILD FAILED")
        print("=" * 60)
        print()
        print("FULL ERROR OUTPUT:")
        print("-" * 60)
        print(result.stdout)
        print(result.stderr)
        print("-" * 60)
        print()
        print("Please copy ALL the text above and send it to me!")
    
    input("Press Enter to exit...")

if __name__ == "__main__":
    build_exe()
