import os
import json
import requests
import webbrowser
import time
from pathlib import Path
import platform
import subprocess
import tempfile
import zipfile
import shutil
import getpass  # Add getpass module for secure input

# API endpoints - centralized for easier updates when moving to production
API_ENDPOINTS = {
    "login": "http://localhost:3000/login-from-client",
    "upload": "http://localhost:5000/upload",
    "download": "http://localhost:5000/download"
}

# Local storage for user credentials
def get_user_data_dir():
    """Get the directory to store user data based on platform"""
    if platform.system() == "Windows":
        return Path(os.path.expandvars("%APPDATA%/flvcs"))
    elif platform.system() == "Darwin":  # macOS
        return Path("~/Library/Application Support/flvcs").expanduser()
    else:  # Linux and others
        return Path("~/.config/flvcs").expanduser()

def get_auth_file():
    """Get the path to the authentication file"""
    data_dir = get_user_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "auth.json"

def save_user_auth(uid):
    """Save user authentication data"""
    auth_file = get_auth_file()
    with open(auth_file, 'w') as f:
        json.dump({"uid": uid}, f)

def load_user_auth():
    """Load user authentication data if it exists"""
    auth_file = get_auth_file()
    if auth_file.exists():
        try:
            with open(auth_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None
    return None

def delete_user_auth():
    """Delete the authentication file if it exists"""
    auth_file = get_auth_file()
    if auth_file.exists():
        os.remove(auth_file)
        return True
    return False

def ensure_authenticated():
    """Make sure the user is authenticated, start auth flow if not"""
    auth_data = load_user_auth()
    
    if auth_data is None or "uid" not in auth_data:
        print("You need to authenticate first.")
        print(f"Opening browser to {API_ENDPOINTS['login']}...")
        
        # Open the login page in the browser
        webbrowser.open(API_ENDPOINTS['login'])
        
        # Wait for the user to complete authentication
        print("Please complete the authentication in your browser.")
        print("After authenticating, enter the UID provided (input will be hidden):")
        
        # Use getpass to hide the input
        uid = getpass.getpass("UID: ").strip()
        
        if not uid:
            raise Exception("Authentication failed. No UID provided.")
            
        # Save the UID for future use
        save_user_auth(uid)
        auth_data = {"uid": uid}
        
        print("Authentication successful!")
    
    return auth_data

def create_archive(project_root, branch_name):
    """Create a zip archive of the complete FLVCS project for sharing
    
    This archives the entire .flvcs directory and the project file for
    a complete backup that can be restored on another machine.
    """
    flvcs_dir = project_root / '.flvcs'
    
    # Create a temporary directory to store the files to be uploaded
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a nested directory structure
        project_temp_dir = temp_path / project_root.name
        os.makedirs(project_temp_dir, exist_ok=True)
        
        # Create .flvcs subdirectory
        temp_flvcs_dir = project_temp_dir / '.flvcs'
        os.makedirs(temp_flvcs_dir, exist_ok=True)
        
        # Copy the entire .flvcs directory structure
        shutil.copytree(flvcs_dir, temp_flvcs_dir, dirs_exist_ok=True)
        
        # Find and copy the project file
        metadata_path = flvcs_dir / 'metadata.json'
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                project_name = metadata.get('project_name', '')
                
                # Try to find the project file by name
                if project_name:
                    # Look for any file matching the project name with any extension
                    for file_path in project_root.glob(f"{project_name}.*"):
                        if file_path.is_file() and not file_path.name.startswith('.'):
                            shutil.copy2(file_path, project_temp_dir / file_path.name)
                            break
        
        # If we couldn't find a project file by name, copy any likely project file
        if not any(project_temp_dir.glob("*.*")):
            # Get any file in the current directory that might be a project file
            for file_path in project_root.glob("*.*"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    shutil.copy2(file_path, project_temp_dir / file_path.name)
                    break
        
        # Create the archive with just the project name (no branch or UID)
        archive_path = temp_path.parent / f"{project_root.name}.zip"
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_path):
                for file in files:
                    file_path = Path(root) / file
                    # Set arcname to be relative to temp_path
                    arcname = file_path.relative_to(temp_path)
                    zipf.write(file_path, arcname)
        
        return archive_path

def extract_archive(archive_path, project_root):
    """Extract a zip archive with FLVCS data and update the local repository"""
    flvcs_dir = project_root / '.flvcs'
    
    # Create a temporary directory to extract the files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Extract the archive
        with zipfile.ZipFile(archive_path, 'r') as zipf:
            zipf.extractall(temp_path)
        
        # Check for the new structure where files are in project/... and project/.flvcs/...
        temp_project_dir = None
        for item in os.listdir(temp_path):
            if os.path.isdir(temp_path / item) and (temp_path / item / '.flvcs').exists():
                temp_project_dir = temp_path / item
                break
        
        # If we found the project directory with the new structure
        if temp_project_dir:
            # Use the new structure
            temp_flvcs_dir = temp_project_dir / '.flvcs'
        else:
            # Fall back to the old structure where files are directly in the root
            temp_flvcs_dir = temp_path
        
        # Load the existing metadata and commit log to merge
        local_metadata_path = flvcs_dir / 'metadata.json'
        local_commit_log_path = flvcs_dir / 'commit_log.json'
        
        local_metadata = {}
        if local_metadata_path.exists():
            with open(local_metadata_path, 'r') as f:
                local_metadata = json.load(f)
        
        local_commit_log = {}
        if local_commit_log_path.exists():
            with open(local_commit_log_path, 'r') as f:
                local_commit_log = json.load(f)
        
        # Load the downloaded metadata and commit log
        downloaded_metadata_path = temp_flvcs_dir / 'metadata.json'
        downloaded_commit_log_path = temp_flvcs_dir / 'commit_log.json'
        
        downloaded_metadata = {}
        if downloaded_metadata_path.exists():
            with open(downloaded_metadata_path, 'r') as f:
                downloaded_metadata = json.load(f)
        
        downloaded_commit_log = {}
        if downloaded_commit_log_path.exists():
            with open(downloaded_commit_log_path, 'r') as f:
                downloaded_commit_log = json.load(f)
        
        # Merge the metadata (keeping local settings but updating branch info)
        if 'branches' in downloaded_metadata:
            # Add any new branches
            for branch in downloaded_metadata['branches']:
                if branch not in local_metadata.get('branches', []):
                    if 'branches' not in local_metadata:
                        local_metadata['branches'] = []
                    local_metadata['branches'].append(branch)
        
        # Merge branch history
        if 'branch_history' in downloaded_metadata:
            if 'branch_history' not in local_metadata:
                local_metadata['branch_history'] = {}
            
            for branch, history in downloaded_metadata['branch_history'].items():
                local_metadata['branch_history'][branch] = history
        
        # Merge branch exclusions
        if 'branch_exclusions' in downloaded_metadata:
            if 'branch_exclusions' not in local_metadata:
                local_metadata['branch_exclusions'] = {}
            
            for branch, exclusions in downloaded_metadata['branch_exclusions'].items():
                local_metadata['branch_exclusions'][branch] = exclusions
        
        # Merge the commit logs
        local_commit_log.update(downloaded_commit_log)
        
        # Save the merged metadata and commit log
        os.makedirs(flvcs_dir, exist_ok=True)
        with open(local_metadata_path, 'w') as f:
            json.dump(local_metadata, f, indent=2)
        
        with open(local_commit_log_path, 'w') as f:
            json.dump(local_commit_log, f, indent=2)
        
        # Copy the commit directories
        os.makedirs(flvcs_dir / 'commits', exist_ok=True)
        for commit_hash in downloaded_commit_log.keys():
            src_commit_dir = temp_flvcs_dir / 'commits' / commit_hash
            dest_commit_dir = flvcs_dir / 'commits' / commit_hash
            
            if src_commit_dir.exists() and not dest_commit_dir.exists():
                shutil.copytree(src_commit_dir, dest_commit_dir)
        
        # Copy any project files from the downloaded archive if present
        if temp_project_dir:
            for item in os.listdir(temp_project_dir):
                if item != '.flvcs':  # Skip the .flvcs directory
                    src_path = temp_project_dir / item
                    dest_path = project_root / item
                    
                    if src_path.is_file() and not dest_path.exists():
                        shutil.copy2(src_path, dest_path)
                        print(f"Restored project file: {item}")

def upload_data(project_root, branch_name, auth_data=None):
    """Upload FLVCS data for a branch to the server
    
    Args:
        project_root: Path to the project root
        branch_name: Name of the branch to upload
        auth_data: Optional authentication data. If provided, authentication step is skipped
    """
    # Ensure authentication if not provided
    if auth_data is None:
        auth_data = ensure_authenticated()
    
    # Create an archive of the data
    print(f"Preparing data for branch '{branch_name}'...")
    archive_path = create_archive(project_root, branch_name)
    
    # Send the archive to the server
    print(f"Uploading to {API_ENDPOINTS['upload']}...")
    
    try:
        with open(archive_path, 'rb') as f:
            # Send only the project name (no branch) in the filename
            filename = f"{project_root.name}.zip"
            files = {'file': (filename, f)}
            data = {
                'uid': auth_data['uid'],
                'branch': branch_name,
                'project': project_root.name
            }
            
            # Include the User-ID header
            headers = {
                'User-ID': auth_data['uid']
            }
            
            response = requests.post(API_ENDPOINTS['upload'], files=files, data=data, headers=headers)
            
            # Check if response status is 200 or 201 (both indicate success)
            if response.status_code in [200, 201]:
                result = response.json()
                print(f"Upload successful! {result.get('message', '')}")
                return True
            else:
                print(f"Upload failed with status code {response.status_code}.")
                if response.text:
                    print(f"Server message: {response.text}")
                return False
    except Exception as e:
        print(f"Error during upload: {str(e)}")
        return False
    finally:
        # Clean up
        if archive_path.exists():
            os.unlink(archive_path)

def download_data(project_root, branch_name, auth_data=None):
    """Download FLVCS data for a branch from the server
    
    Args:
        project_root: Path to the project root
        branch_name: Name of the branch to download
        auth_data: Optional authentication data. If provided, authentication step is skipped
    """
    # Ensure authentication if not provided
    if auth_data is None:
        auth_data = ensure_authenticated()
    
    # Request the data from the server
    print(f"Downloading data for branch '{branch_name}' from {API_ENDPOINTS['download']}...")
    
    try:
        params = {
            'uid': auth_data['uid'],
            'branch': branch_name,
            'project': project_root.name
        }
        
        # Include the User-ID header
        headers = {
            'User-ID': auth_data['uid']
        }
        
        response = requests.get(API_ENDPOINTS['download'], params=params, headers=headers, stream=True)
        
        if response.status_code == 200:
            # Save the downloaded file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        temp_file.write(chunk)
                
                temp_file_path = temp_file.name
                
            # Extract the archive
            print("Extracting data...")
            extract_archive(temp_file_path, project_root)
            
            # Clean up
            os.unlink(temp_file_path)
            
            print("Download and update successful!")
            return True
        else:
            print(f"Download failed with status code {response.status_code}.")
            if response.text:
                print(f"Server message: {response.text}")
            return False
    except Exception as e:
        print(f"Error during download: {str(e)}")
        return False 