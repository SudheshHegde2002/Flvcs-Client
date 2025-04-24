#!/usr/bin/env python
import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_macos_app():
    print("Building FLVCS macOS application...")
    
    # Check that we're running on macOS
    if sys.platform != 'darwin':
        print("Error: This script must be run on macOS.")
        sys.exit(1)
    
    # Get the current directory and ensure paths are correct
    current_dir = os.path.abspath(os.path.dirname(__file__))
    icon_path = os.path.join(current_dir, "flvcs", "Icon.png")
    
    # Convert PNG icon to ICNS format (required for macOS)
    icns_path = os.path.join(current_dir, "flvcs.icns")
    try:
        # Check if iconutil is available on this system
        if not os.path.exists(icns_path):
            print("Converting icon to macOS format...")
            
            # Create temporary iconset directory
            iconset_path = os.path.join(current_dir, "flvcs.iconset")
            os.makedirs(iconset_path, exist_ok=True)
            
            # Generate various icon sizes using sips
            icon_sizes = [16, 32, 64, 128, 256, 512, 1024]
            for size in icon_sizes:
                output_icon = os.path.join(iconset_path, f"icon_{size}x{size}.png")
                subprocess.run(["sips", "-z", str(size), str(size), icon_path, "--out", output_icon], 
                              check=True, capture_output=True)
                
                # Create retina (2x) versions
                if size <= 512:
                    output_icon_2x = os.path.join(iconset_path, f"icon_{size}x{size}@2x.png")
                    size_2x = size * 2
                    subprocess.run(["sips", "-z", str(size_2x), str(size_2x), icon_path, "--out", output_icon_2x],
                                 check=True, capture_output=True)
            
            # Convert iconset to icns
            subprocess.run(["iconutil", "-c", "icns", iconset_path], check=True)
            
            # Clean up
            shutil.rmtree(iconset_path)
            print(f"Created macOS icon at: {icns_path}")
    except Exception as e:
        print(f"Warning: Could not create macOS icon: {e}")
        print("Continuing with default icon...")
        icns_path = ""
    
    # Build command
    cmd = [
        "pyinstaller",
        "--name=FLVCS",
        "--windowed",  # Create a .app bundle
        "--onedir",    # Use a directory structure for the app
        "--clean",     # Clean PyInstaller cache
    ]
    
    # Add icon if available
    if os.path.exists(icns_path):
        cmd.append(f"--icon={icns_path}")
    
    # Add data files
    if os.path.exists(icon_path):
        cmd.extend(["--add-data", f"{icon_path}:flvcs"])
    
    # Add required Qt imports
    cmd.extend([
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        os.path.join(current_dir, "run_gui.py")  # Script to run
    ])
    
    print("Executing command:", " ".join(cmd))
    
    # Execute the build command
    try:
        result = subprocess.run(cmd, check=True)
        
        print("\nApplication bundle created successfully!")
        app_path = os.path.abspath(os.path.join(current_dir, "dist", "FLVCS.app"))
        print(f"Application bundle created at: {app_path}")
        
        # Now create a DMG file for easy distribution
        dmg_path = os.path.join(current_dir, "dist", "FLVCS-Installer.dmg")
        print("\nCreating DMG installer...")
        
        # Create temporary folder for DMG contents
        dmg_build_dir = os.path.join(current_dir, "dist", "dmg_build")
        os.makedirs(dmg_build_dir, exist_ok=True)
        
        # Copy the .app bundle to the build directory
        app_dest = os.path.join(dmg_build_dir, "FLVCS.app")
        if os.path.exists(app_dest):
            shutil.rmtree(app_dest)
        shutil.copytree(app_path, app_dest)
        
        # Create a symbolic link to /Applications
        applications_link = os.path.join(dmg_build_dir, "Applications")
        if os.path.exists(applications_link):
            os.unlink(applications_link)
        os.symlink("/Applications", applications_link)
        
        # Create a README file for the DMG
        with open(os.path.join(dmg_build_dir, "README.txt"), "w") as f:
            f.write("FLVCS - File Version Control System\n\n")
            f.write("To install, drag the FLVCS.app icon to the Applications folder.\n")
            f.write("After installation, you can eject this disk image.\n")
        
        # Create the DMG
        try:
            # Remove existing DMG if it exists
            if os.path.exists(dmg_path):
                os.unlink(dmg_path)
                
            # Create the DMG using hdiutil
            subprocess.run([
                "hdiutil", "create", 
                "-volname", "FLVCS Installer",
                "-srcfolder", dmg_build_dir,
                "-ov", "-format", "UDZO",
                dmg_path
            ], check=True)
            
            print(f"\nDMG installer created successfully at: {dmg_path}")
            
        except Exception as e:
            print(f"Error creating DMG: {e}")
            print("The .app bundle was created successfully, but the DMG packaging failed.")
            
        # Clean up
        shutil.rmtree(dmg_build_dir)
            
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
    
    print("\nBuild process completed.")
    print("To distribute the application:")
    print(f"1. Use the DMG installer at: {dmg_path}")
    print("2. Users can drag FLVCS.app to their Applications folder")
    print("3. No additional installation required")

if __name__ == "__main__":
    build_macos_app() 