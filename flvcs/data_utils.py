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
from datetime import datetime

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

def upload_data(project_root, branch_name, auth_data=None, force=False, debug=False):
    """Upload FLVCS data for a branch to the server
    
    Args:
        project_root: Path to the project root
        branch_name: Name of the branch to upload
        auth_data: Optional authentication data. If provided, authentication step is skipped
        force: If True, upload even if no new commits since last upload
        debug: If True, print debug information
        
    Returns:
        bool: True if upload was successful, False otherwise
    """
    # Ensure authentication if not provided
    if auth_data is None:
        auth_data = ensure_authenticated()
    
    # Force upload if requested
    if force:
        if debug: print(f"Force upload requested. Will upload branch '{branch_name}' regardless of commit status.")
        
    # Check if there are new commits since last upload
    flvcs_dir = project_root / '.flvcs'
    last_upload_path = flvcs_dir / 'last_upload.json'
    
    # Load commit log
    commit_log_path = flvcs_dir / 'commit_log.json'
    if not commit_log_path.exists():
        print("No commits found. Nothing to upload.")
        return False
        
    with open(commit_log_path, 'r') as f:
        commit_log = json.load(f)
        if debug: print(f"DEBUG: Loaded commit log with {len(commit_log)} commits")
    
    # Load metadata to get branch history
    metadata_path = flvcs_dir / 'metadata.json'
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    else:
        print("ERROR: metadata.json not found")
        return False

    # Get commits for the branch - first check branch_history for a list of commits
    branch_history = metadata.get('branch_history', {})
    branch_commits = []
    
    # Check if branch exists in branch_history and has a 'commits' field
    if branch_name in branch_history:
        branch_info = branch_history[branch_name]
        if isinstance(branch_info, dict) and 'commits' in branch_info:
            branch_commits = branch_info['commits']
            if debug: print(f"DEBUG: Found {len(branch_commits)} commits for branch '{branch_name}' in branch_history.commits")
        elif isinstance(branch_info, list):
            # For backwards compatibility with older format
            branch_commits = branch_info
            if debug: print(f"DEBUG: Found {len(branch_commits)} commits for branch '{branch_name}' in old-style branch_history")
    
    # If no commits found in branch_history, look for commits with matching branch in commit_log
    if not branch_commits:
        for commit_hash, info in commit_log.items():
            if info.get('branch') == branch_name:
                branch_commits.append(commit_hash)
        if debug: print(f"DEBUG: Found {len(branch_commits)} commits for branch '{branch_name}' by searching commit_log")
    
    if not branch_commits:
        print(f"No commits found for branch '{branch_name}'. Nothing to upload.")
        return False
    
    # Get the latest commit time for the branch
    latest_commit_time = None
    valid_timestamps = 0
    
    # Find the latest commit time (as ISO string)
    for i, commit_hash in enumerate(branch_commits):
        if debug: print(f"DEBUG: Processing commit {i+1}/{len(branch_commits)}: {commit_hash}")
        
        if commit_hash in commit_log:
            commit_info = commit_log[commit_hash]
            commit_time_str = commit_info.get('timestamp', '')
            
            if debug: print(f"DEBUG: Commit timestamp string: '{commit_time_str}'")
            
            try:
                # Try parsing as ISO format
                commit_time = datetime.fromisoformat(commit_time_str)
                valid_timestamps += 1
                if debug: print(f"DEBUG: Valid timestamp: {commit_time}")
                
                if latest_commit_time is None or commit_time > latest_commit_time:
                    latest_commit_time = commit_time
                    if debug: print(f"DEBUG: New latest timestamp: {latest_commit_time}")
            except (ValueError, TypeError) as e:
                if debug: print(f"DEBUG: Invalid timestamp format: {e}")
                
                # For compatibility with older versions that might have used different formats
                try:
                    # Try standard ISO format without microseconds
                    if 'T' in commit_time_str and '+' in commit_time_str:
                        # Try removing timezone part if causing issues
                        commit_time_str = commit_time_str.split('+')[0]
                        commit_time = datetime.fromisoformat(commit_time_str)
                        valid_timestamps += 1
                        if debug: print(f"DEBUG: Fixed timestamp (removed tz): {commit_time}")
                    # Try common date format without time
                    elif len(commit_time_str) == 10 and commit_time_str.count('-') == 2:
                        commit_time_str += "T00:00:00"
                        commit_time = datetime.fromisoformat(commit_time_str)
                        valid_timestamps += 1
                        if debug: print(f"DEBUG: Fixed timestamp (added time): {commit_time}")
                    # Try numeric timestamp (old versions)
                    elif commit_time_str.isdigit():
                        commit_time = datetime.fromtimestamp(float(commit_time_str))
                        valid_timestamps += 1
                        if debug: print(f"DEBUG: Fixed numeric timestamp: {commit_time}")
                    
                    if latest_commit_time is None or commit_time > latest_commit_time:
                        latest_commit_time = commit_time
                        if debug: print(f"DEBUG: New latest timestamp from fixed format: {latest_commit_time}")
                except Exception as e2:
                    if debug: print(f"DEBUG: Could not fix timestamp '{commit_time_str}': {e2}")
                    continue
        else:
            if debug: print(f"DEBUG: Commit {commit_hash} not found in commit log")
    
    if debug: print(f"DEBUG: Found {valid_timestamps} valid timestamps out of {len(branch_commits)} commits")
    
    if latest_commit_time is None:
        if force:
            print("No valid commit timestamps found, but force upload requested. Proceeding with upload.")
            # Use current time as latest commit time for force uploads
            latest_commit_time = datetime.now()
        else:
            print(f"No valid commit timestamps found for branch '{branch_name}'. Nothing to upload.")
            print("Use --force option to upload anyway.")
            return False
    
    # Convert to ISO string for storage
    latest_commit_time_str = latest_commit_time.isoformat()
    if debug: print(f"DEBUG: Latest commit time: {latest_commit_time_str}")
    
    # Check if we've uploaded since the latest commit
    last_upload_time_str = None
    if last_upload_path.exists():
        try:
            with open(last_upload_path, 'r') as f:
                upload_data = json.load(f)
                last_upload_time_str = upload_data.get(branch_name)
                if debug: print(f"DEBUG: Last upload time string: '{last_upload_time_str}'")
        except (json.JSONDecodeError, FileNotFoundError) as e:
            if debug: print(f"DEBUG: Error reading last_upload.json: {e}")
            pass
    else:
        if debug: print("DEBUG: No previous upload record found")
    
    # Compare timestamps if we have a previous upload and not forcing
    if last_upload_time_str and not force:
        try:
            last_upload_time = datetime.fromisoformat(last_upload_time_str)
            if debug: 
                print(f"DEBUG: Last upload time: {last_upload_time}")
                print(f"DEBUG: Latest commit time: {latest_commit_time}")
            
            # If last upload is newer or same as latest commit, abort
            if last_upload_time >= latest_commit_time:
                print(f"No new commits on branch '{branch_name}' since last upload. Nothing to upload.")
                print("Use --force option to upload anyway.")
                return False
            else:
                if debug: print(f"DEBUG: New commits found since last upload")
        except (ValueError, TypeError) as e:
            if debug: print(f"DEBUG: Invalid last upload timestamp format: {e}")
            # If timestamp is invalid, continue with upload
            pass
    
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
                
                # Save the upload time for this branch
                upload_data = {}
                if last_upload_path.exists():
                    try:
                        with open(last_upload_path, 'r') as f:
                            upload_data = json.load(f)
                    except json.JSONDecodeError:
                        pass
                
                # Store latest commit time as ISO string
                upload_data[branch_name] = latest_commit_time_str
                
                with open(last_upload_path, 'w') as f:
                    json.dump(upload_data, f, indent=2)
                    
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

def download_data(project_root, branch_name, auth_data=None, debug=False):
    """Download FLVCS data for a branch from the server
    
    Args:
        project_root: Path to the project root
        branch_name: Name of the branch to download
        auth_data: Optional authentication data. If provided, authentication step is skipped
        debug: If True, print debug information
        
    Returns:
        bool: True if download was successful, False otherwise
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
            
            # After successful download, update the last upload time for this branch
            # This prevents unnecessary uploads of the same data
            flvcs_dir = project_root / '.flvcs'
            last_upload_path = flvcs_dir / 'last_upload.json'
            
            # Get the latest commit time for the branch after download
            commit_log_path = flvcs_dir / 'commit_log.json'
            if commit_log_path.exists():
                with open(commit_log_path, 'r') as f:
                    commit_log = json.load(f)
                
                # Load metadata to get branch history
                metadata_path = flvcs_dir / 'metadata.json'
                latest_commit_time = None
                
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        branch_history = metadata.get('branch_history', {})
                        
                        # Get commits for the branch
                        branch_commits = []
                        if branch_name in branch_history:
                            branch_info = branch_history[branch_name]
                            if isinstance(branch_info, dict) and 'commits' in branch_info:
                                branch_commits = branch_info['commits']
                            elif isinstance(branch_info, list):
                                branch_commits = branch_info
                        
                        if not branch_commits:
                            # Fallback to searching commit log
                            for commit_hash, info in commit_log.items():
                                if info.get('branch') == branch_name:
                                    branch_commits.append(commit_hash)
                        
                        # Find the latest commit time
                        for commit_hash in branch_commits:
                            if commit_hash in commit_log:
                                commit_time_str = commit_log[commit_hash].get('timestamp', '')
                                try:
                                    # Try parsing as ISO format
                                    commit_time = datetime.fromisoformat(commit_time_str)
                                    if latest_commit_time is None or commit_time > latest_commit_time:
                                        latest_commit_time = commit_time
                                except (ValueError, TypeError):
                                    # Try alternative formats
                                    try:
                                        # Try standard ISO format without microseconds
                                        if 'T' in commit_time_str and '+' in commit_time_str:
                                            # Try removing timezone part if causing issues
                                            commit_time_str = commit_time_str.split('+')[0]
                                            commit_time = datetime.fromisoformat(commit_time_str)
                                        # Try common date format without time
                                        elif len(commit_time_str) == 10 and commit_time_str.count('-') == 2:
                                            commit_time_str += "T00:00:00"
                                            commit_time = datetime.fromisoformat(commit_time_str)
                                        # Try numeric timestamp (old versions)
                                        elif commit_time_str.isdigit():
                                            commit_time = datetime.fromtimestamp(float(commit_time_str))
                                        
                                        if latest_commit_time is None or commit_time > latest_commit_time:
                                            latest_commit_time = commit_time
                                    except Exception:
                                        # If all parsing fails, continue to next commit
                                        continue
                        
                        if latest_commit_time is not None:
                            # Convert to ISO string for storage
                            latest_commit_time_str = latest_commit_time.isoformat()
                            
                            # Update the last upload time
                            upload_data = {}
                            if last_upload_path.exists():
                                try:
                                    with open(last_upload_path, 'r') as f:
                                        upload_data = json.load(f)
                                except json.JSONDecodeError:
                                    pass
                            
                            upload_data[branch_name] = latest_commit_time_str
                            
                            with open(last_upload_path, 'w') as f:
                                json.dump(upload_data, f, indent=2)
            
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

def reset_upload_tracking(project_root, branch_name=None):
    """Reset the upload timestamp tracking for one or all branches.
    
    This can be used to force the system to recognize commits as new after errors.
    
    Args:
        project_root: Path to the project root
        branch_name: Name of the branch to reset. If None, all branches are reset.
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        flvcs_dir = project_root / '.flvcs'
        last_upload_path = flvcs_dir / 'last_upload.json'
        
        if not last_upload_path.exists():
            print("No upload tracking file found. Nothing to reset.")
            return True
            
        if branch_name is None:
            # Reset all branches by deleting the file
            os.unlink(last_upload_path)
            print("Reset upload tracking for all branches.")
            return True
        else:
            # Reset specific branch
            upload_data = {}
            try:
                with open(last_upload_path, 'r') as f:
                    upload_data = json.load(f)
            except json.JSONDecodeError:
                # Invalid JSON, just reset the file
                os.unlink(last_upload_path)
                print(f"Reset upload tracking for branch '{branch_name}' (and all others due to file corruption).")
                return True
                
            if branch_name in upload_data:
                del upload_data[branch_name]
                with open(last_upload_path, 'w') as f:
                    json.dump(upload_data, f, indent=2)
                print(f"Reset upload tracking for branch '{branch_name}'.")
            else:
                print(f"No upload tracking found for branch '{branch_name}'. Nothing to reset.")
                
            return True
    except Exception as e:
        print(f"Error resetting upload tracking: {str(e)}")
        return False 