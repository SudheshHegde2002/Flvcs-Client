#!/usr/bin/env python
import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_exe():
    print("Building FLVCS executable...")
    
    # Get the current directory and ensure paths are correct
    current_dir = os.path.abspath(os.path.dirname(__file__))
    icon_path = os.path.join(current_dir, "flvcs", "Icon.png")
    
    # Verify the icon file exists
    if not os.path.exists(icon_path):
        print(f"Warning: Icon file not found at {icon_path}")
        icon_option = []
    else:
        print(f"Using icon: {icon_path}")
        icon_option = [f"--icon={icon_path}"]
    
    # Include necessary data files
    add_data = []
    if os.path.exists(icon_path):
        add_data.extend(["--add-data", f"{icon_path};flvcs"])
    
    # Build command
    cmd = [
        "pyinstaller",
        "--name=FLVCS",
        "--onefile",  # Create a single executable
        "--windowed",  # Don't show console window
        "--clean",    # Clean PyInstaller cache
        *icon_option,
        *add_data,
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        os.path.join(current_dir, "run_gui.py")  # Script to run
    ]
    
    print("Executing command:", " ".join(cmd))
    
    # Execute the build command
    try:
        result = subprocess.run(cmd, check=True)
        
        print("\nBuild completed successfully!")
        exe_path = os.path.abspath(os.path.join(current_dir, "dist", "FLVCS.exe"))
        print(f"Executable created at: {exe_path}")
        
        # Create a batch file that creates a shortcut (Windows-only)
        try:
            if sys.platform == 'win32':
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                if os.path.exists(desktop_path) and os.path.exists(exe_path):
                    # Create a batch file to make the shortcut
                    batch_path = os.path.join(current_dir, "create_shortcut.bat")
                    with open(batch_path, 'w') as f:
                        f.write('@echo off\n')
                        f.write('echo Creating shortcut...\n')
                        f.write('powershell "$ws = New-Object -ComObject WScript.Shell; ')
                        f.write(f'$s = $ws.CreateShortcut(\'{desktop_path}\\FLVCS.lnk\'); ')
                        f.write(f'$s.TargetPath = \'{exe_path}\'; ')
                        f.write(f'$s.WorkingDirectory = \'{os.path.dirname(exe_path)}\'; ')
                        f.write(f'$s.IconLocation = \'{exe_path}\'; ')
                        f.write('$s.Save()"\n')
                        f.write('echo Shortcut created on desktop.\n')
                        f.write('pause\n')
                    
                    print(f"Created batch file to make desktop shortcut: {batch_path}")
                    print("Run this file to create a desktop shortcut.")
        except Exception as e:
            print(f"Could not create shortcut batch file: {e}")
    
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
    
    print("\nYou can now run the FLVCS application by double-clicking on the executable file.")

if __name__ == "__main__":
    build_exe() 