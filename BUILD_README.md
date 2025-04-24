# Building FLVCS Executable

This document explains how to create a standalone executable (.exe) file for the FLVCS client application.

## Prerequisites

1. Python 3.6 or higher installed
2. FLVCS client code installed and working correctly
3. Internet connection (to download PyInstaller if needed)

## Building the Executable

### Option 1: Using the build script

1. Run the build script:
   ```
   python build_exe.py
   ```

2. Wait for the build process to complete. This may take a few minutes.

3. Once complete, you'll find the executable in the `dist` folder:
   ```
   dist/FLVCS.exe
   ```

### Option 2: Manual PyInstaller command

If you prefer to run PyInstaller directly:

1. Install PyInstaller if you haven't already:
   ```
   pip install pyinstaller
   ```

2. Run the following command:
   ```
   pyinstaller --name=FLVCS --onefile --icon=flvcs/Icon.png --windowed --noconsole --add-data "flvcs/Icon.png;flvcs" run_gui.py
   ```

## Using the Executable

Simply double-click the `FLVCS.exe` file in the `dist` folder to run the application. The executable is standalone and includes all necessary dependencies.

## Troubleshooting

If you encounter issues:

1. Ensure all required Python packages are installed:
   ```
   pip install -r requirements.txt
   ```
   
2. Try building with console output for debugging:
   ```
   pyinstaller --name=FLVCS --onefile --icon=flvcs/Icon.png run_gui.py
   ```

3. Check that the Icon.png file exists in the flvcs directory

## Distribution

You can distribute the standalone .exe file to users who don't have Python installed. They will be able to run the application directly without any additional setup. 