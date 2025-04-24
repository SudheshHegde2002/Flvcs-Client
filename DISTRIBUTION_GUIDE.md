# FLVCS Distribution Guide

This guide explains how to distribute and use the FLVCS client executable.

## Contents

1. **FLVCS.exe** - The main executable file that runs the application
2. **create_shortcut.bat** - A batch script to create a desktop shortcut (optional)

## For Users

### Installation

No installation is required! The FLVCS.exe is a standalone executable that contains all the necessary dependencies.

1. Download and extract the provided files to any location on your computer
2. Double-click **FLVCS.exe** to run the application
3. (Optional) Run **create_shortcut.bat** to create a desktop shortcut

### Requirements

- Windows operating system (Windows 7 or newer)
- No Python installation required
- No additional libraries required

### First Run

When you first run the application:

1. The FLVCS GUI will open
2. You may need to authenticate if accessing remote repositories
3. Follow the on-screen instructions to work with your version control repositories

## For Distributors

### What to Include

When distributing FLVCS to users, include:

1. **FLVCS.exe** from the dist/ folder
2. **create_shortcut.bat** (modify if needed for your deployment scenario)
3. This guide or a simplified version for end-users

### Distribution Methods

1. **Direct Download**: Provide the files via a download link
2. **Shared Folder**: Place in a network share for multiple users
3. **USB Drive**: Copy to USB drives for offline distribution

### Troubleshooting

If users encounter issues:

1. Ensure antivirus software isn't blocking the application
2. Verify all required files are in the distribution package
3. Check for Windows permissions issues (may need to run as administrator)

## Additional Information

- File size: ~46 MB
- The executable contains all Python dependencies and libraries
- No registry changes are made during execution
- The application can be removed by simply deleting the files 