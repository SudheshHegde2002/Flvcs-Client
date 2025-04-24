# FLVCS Distribution Guide

This guide explains how to distribute and use the FLVCS client executable on Windows and macOS.

## Windows Distribution

### Contents

1. **FLVCS.exe** - The main executable file that runs the application
2. **create_shortcut.bat** - A batch script to create a desktop shortcut (optional)

### For Users (Windows)

#### Installation

No installation is required! The FLVCS.exe is a standalone executable that contains all the necessary dependencies.

1. Download and extract the provided files to any location on your computer
2. Double-click **FLVCS.exe** to run the application
3. (Optional) Run **create_shortcut.bat** to create a desktop shortcut

#### Requirements

- Windows operating system (Windows 7 or newer)
- No Python installation required
- No additional libraries required

## macOS Distribution

### Contents

1. **FLVCS-Installer.dmg** - A disk image containing the application bundle

### For Users (macOS)

#### Installation

1. Double-click the **FLVCS-Installer.dmg** file to mount the disk image
2. A window will open showing the FLVCS.app icon and the Applications folder
3. Drag the FLVCS.app icon to the Applications folder to install
4. Eject the disk image when finished
5. Open the app from your Applications folder

#### Requirements

- macOS 10.13 (High Sierra) or newer recommended
- No Python installation required
- No additional libraries required

## First Run

When you first run the application:

1. The FLVCS GUI will open
2. You may need to authenticate if accessing remote repositories
3. Follow the on-screen instructions to work with your version control repositories

## For Distributors

### What to Include

When distributing FLVCS to users, include:

#### For Windows Users
1. **FLVCS.exe** from the dist/ folder
2. **create_shortcut.bat** (modify if needed for your deployment scenario)

#### For macOS Users
1. **FLVCS-Installer.dmg** from the dist/ folder

### Distribution Methods

1. **Direct Download**: Provide the files via a download link
2. **Shared Folder**: Place in a network share for multiple users
3. **USB Drive**: Copy to USB drives for offline distribution

### Building the Installers

#### Windows
Run the build_exe.py script:
```
python build_exe.py
```

#### macOS
Run the build_macos.py script (must be run on a Mac):
```
python build_macos.py
```

### Troubleshooting

If users encounter issues:

#### Windows
1. Ensure antivirus software isn't blocking the application
2. Verify all required files are in the distribution package
3. Check for Windows permissions issues (may need to run as administrator)

#### macOS
1. If macOS blocks the app due to it being from an unidentified developer:
   - Right-click (or Control-click) the app icon and select "Open"
   - Click "Open" in the dialog that appears
2. If you see a "damaged app" message, ensure the DMG was properly downloaded

## Additional Information

- File sizes:
  - Windows: ~46 MB
  - macOS: ~50 MB (varies)
- The executables contain all Python dependencies and libraries
- No registry changes are made during execution
- The application can be removed by simply deleting the files (Windows) or moving to Trash (macOS) 