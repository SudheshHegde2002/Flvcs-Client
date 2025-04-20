import os
import shutil
import json
import hashlib
from datetime import datetime
from pathlib import Path
import wave
import struct
import click
import uuid

class DAWVCS:
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.vcs_dir = self.project_path.parent / '.flvcs'
        self.commits_dir = self.vcs_dir / 'commits'
        self.commit_log_path = self.vcs_dir / 'commit_log.json'
        self.metadata_path = self.vcs_dir / 'metadata.json'
        
        # Initialize VCS directory structure if it doesn't exist
        self._init_vcs_structure()
        
    def _init_vcs_structure(self):
        """Create necessary directories and files for version control"""
        if not self.vcs_dir.exists():
            self.vcs_dir.mkdir()
            self.commits_dir.mkdir()
            self._save_commit_log({})
            self._save_metadata({
                'project_name': self.project_path.stem,
                'created_at': datetime.now().isoformat(),
                'total_commits': 0,
                'branches': ['main'],
                'current_branch': 'main',
                'branch_history': {},  # Track branch creation history
                'last_modified': datetime.now().isoformat(),
                'audio_stats': {},
                'project_stats': {
                    'size_history': []
                }
            })
    
    def _save_metadata(self, metadata):
        """Save project metadata to JSON file"""
        with open(self.metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _load_metadata(self):
        """Load project metadata from JSON file"""
        if self.metadata_path.exists():
            with open(self.metadata_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _update_metadata(self):
        """Update project metadata with current statistics"""
        metadata = self._load_metadata()
        
        # Update basic stats
        metadata['last_modified'] = datetime.now().isoformat()
        metadata['total_commits'] += 1
        
        # Update file size history
        size_stats = {
            'timestamp': datetime.now().isoformat(),
            'size_bytes': os.path.getsize(self.project_path)
        }
        metadata['project_stats']['size_history'].append(size_stats)
        
        # Update audio statistics if there are exported audio files
        audio_dir = self.project_path.parent / 'Rendered'
        if audio_dir.exists():
            audio_stats = self._analyze_audio_files(audio_dir)
            metadata['audio_stats'] = audio_stats
        
        self._save_metadata(metadata)
    
    def _analyze_audio_files(self, audio_dir):
        """Analyze audio files in the project directory"""
        audio_stats = {
            'total_audio_files': 0,
            'total_duration': 0,
            'formats': {},
            'sample_rates': {},
            'channels': {}
        }
        
        for audio_file in audio_dir.glob('*.wav'):
            try:
                with wave.open(str(audio_file), 'rb') as wav:
                    params = wav.getparams()
                    duration = params.nframes / params.framerate
                    
                    audio_stats['total_audio_files'] += 1
                    audio_stats['total_duration'] += duration
                    
                    # Track format statistics
                    format_key = f"{params.sampwidth * 8}bit"
                    audio_stats['formats'][format_key] = audio_stats['formats'].get(format_key, 0) + 1
                    
                    # Track sample rate statistics
                    sr_key = f"{params.framerate}Hz"
                    audio_stats['sample_rates'][sr_key] = audio_stats['sample_rates'].get(sr_key, 0) + 1
                    
                    # Track channel statistics
                    ch_key = 'mono' if params.nchannels == 1 else 'stereo'
                    audio_stats['channels'][ch_key] = audio_stats['channels'].get(ch_key, 0) + 1
            except:
                continue
        
        return audio_stats

    def _save_commit_log(self, log_data):
        """Save commit log to JSON file"""
        with open(self.commit_log_path, 'w') as f:
            json.dump(log_data, f, indent=2)
            
    def _load_commit_log(self):
        """Load commit log from JSON file"""
        if self.commit_log_path.exists():
            with open(self.commit_log_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _generate_commit_hash(self):
        """Generate a unique hash for the commit based on file content and timestamp"""
        timestamp = datetime.now().isoformat()
        with open(self.project_path, 'rb') as f:
            content = f.read()
        return hashlib.sha256(content + timestamp.encode()).hexdigest()[:8]
    
    def commit(self, message):
        """Create a new commit with the current state of the FL Studio project"""
        if not self.project_path.exists():
            raise FileNotFoundError("FL Studio project file not found")
            
        commit_hash = self._generate_commit_hash()
        commit_dir = self.commits_dir / commit_hash
        commit_dir.mkdir()
        
        # Copy project file to commit directory
        shutil.copy2(self.project_path, commit_dir / self.project_path.name)
        
        # Get current branch
        metadata = self._load_metadata()
        current_branch = metadata['current_branch']
        
        # Update commit log
        commit_log = self._load_commit_log()
        commit_log[commit_hash] = {
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'file': self.project_path.name,
            'branch': current_branch
        }
        self._save_commit_log(commit_log)
        
        # Update metadata
        metadata = self._load_metadata()
        metadata['total_commits'] += 1
        metadata['last_modified'] = datetime.now().isoformat()
        
        # Initialize branch_history if it doesn't exist
        if 'branch_history' not in metadata:
            metadata['branch_history'] = {}
        
        # Make sure current branch exists in branch_history
        if current_branch not in metadata['branch_history']:
            metadata['branch_history'][current_branch] = {
                'parent': 'main',
                'timestamp': datetime.now().isoformat(),
                'commits': []
            }
        
        # Make sure the branch_history has the correct structure
        if isinstance(metadata['branch_history'][current_branch], list):
            # Convert from old format to new format
            old_commits = metadata['branch_history'][current_branch]
            metadata['branch_history'][current_branch] = {
                'parent': 'main',
                'timestamp': datetime.now().isoformat(),
                'commits': old_commits
            }
        
        # Make sure there's a commits list
        if 'commits' not in metadata['branch_history'][current_branch]:
            metadata['branch_history'][current_branch]['commits'] = []
        
        # Add the commit hash to the branch's commit list
        if commit_hash not in metadata['branch_history'][current_branch]['commits']:
            metadata['branch_history'][current_branch]['commits'].append(commit_hash)
        
        # Update file size history
        if 'project_stats' not in metadata:
            metadata['project_stats'] = {'size_history': []}
            
        size_stats = {
            'timestamp': datetime.now().isoformat(),
            'size_bytes': os.path.getsize(self.project_path)
        }
        metadata['project_stats']['size_history'].append(size_stats)
        
        # Update audio statistics if there are exported audio files
        audio_dir = self.project_path.parent / 'Rendered'
        if audio_dir.exists():
            audio_stats = self._analyze_audio_files(audio_dir)
            metadata['audio_stats'] = audio_stats
        
        self._save_metadata(metadata)
        
        return commit_hash
    
    def get_metadata(self):
        """Get project metadata and statistics"""
        return self._load_metadata()
    
    def get_project_growth(self):
        """Get project size growth over time"""
        metadata = self._load_metadata()
        return metadata['project_stats']['size_history']
    
    def get_audio_stats(self):
        """Get statistics about rendered audio files"""
        metadata = self._load_metadata()
        return metadata['audio_stats']
    
    def list_commits(self):
        """List all commits with their messages and timestamps for the current branch including inherited commits"""
        commit_log = self._load_commit_log()
        metadata = self._load_metadata()
        current_branch = metadata['current_branch']
        
        # Initialize branch history if it doesn't exist (for backward compatibility)
        if 'branch_history' not in metadata:
            metadata['branch_history'] = {}
            self._save_metadata(metadata)
        
        # Initialize branch exclusions if it doesn't exist
        if 'branch_exclusions' not in metadata:
            metadata['branch_exclusions'] = {}
        
        # Get exclusion list for current branch
        branch_exclusions = metadata['branch_exclusions'].get(current_branch, [])
        
        # Store all branch creation points to determine commit inheritance
        branch_history = metadata.get('branch_history', {})
        
        # Get all commits
        all_commits = []
        for commit_hash, info in commit_log.items():
            # Skip excluded commits
            if commit_hash in branch_exclusions:
                continue
                
            # Add branch info if not present in older commits
            if 'branch' not in info:
                info['branch'] = 'main'
            
            # We need to include commits that:
            # 1. Belong to the current branch directly
            # 2. Are from parent branches and created before the branch point
            
            # Get branch and timestamp
            commit_branch = info['branch']
            commit_timestamp = info['timestamp']
            
            # If commit is from current branch, include it
            if commit_branch == current_branch:
                all_commits.append({
                    'hash': commit_hash,
                    'message': info['message'],
                    'timestamp': info['timestamp'],
                    'branch': info['branch']
                })
            else:
                # If current branch is 'main', only show main commits
                if current_branch == 'main':
                    if commit_branch == 'main':
                        all_commits.append({
                            'hash': commit_hash,
                            'message': info['message'],
                            'timestamp': info['timestamp'],
                            'branch': info['branch']
                        })
                # For other branches, check if commit is from a parent branch and created before branch point
                elif current_branch in branch_history:
                    # If the commit's branch is a parent of the current branch
                    # and the commit was created before the branch point
                    branch_info = branch_history[current_branch]
                    if isinstance(branch_info, dict) and 'parent' in branch_info:
                        parent_branch = branch_info['parent']
                        branch_point = branch_info['timestamp']
                        
                        # Check if commit is from parent or earlier in the branch hierarchy
                        parent_hierarchy = self._get_branch_hierarchy(parent_branch, branch_history)
                        
                        if commit_branch in parent_hierarchy and commit_timestamp < branch_point:
                            all_commits.append({
                                'hash': commit_hash,
                                'message': info['message'],
                                'timestamp': info['timestamp'],
                                'branch': info['branch']
                            })
                
        return sorted(all_commits, key=lambda x: x['timestamp'], reverse=True)
    
    def _get_branch_hierarchy(self, branch, branch_history):
        """Get a list of parent branches for the given branch"""
        hierarchy = [branch]
        current = branch
        
        while current in branch_history:
            branch_info = branch_history[current]
            # Skip if branch info is a list (old format) or doesn't have parent info
            if not isinstance(branch_info, dict) or 'parent' not in branch_info:
                break
                
            parent = branch_info['parent']
            # Avoid infinite loops if a branch is its own parent
            if parent == current:
                break
                
            hierarchy.append(parent)
            current = parent
            
            # Avoid infinite loops in the branch hierarchy
            if current in hierarchy[:-1]:
                break
                
        return hierarchy
        
    def list_all_commits(self):
        """List all commits from all branches with their messages and timestamps"""
        commit_log = self._load_commit_log()
        commits = []
        for commit_hash, info in commit_log.items():
            # Add branch info if not present in older commits
            if 'branch' not in info:
                info['branch'] = 'main'
                
            commits.append({
                'hash': commit_hash,
                'message': info['message'],
                'timestamp': info['timestamp'],
                'branch': info['branch']
            })
                
        return sorted(commits, key=lambda x: x['timestamp'], reverse=True)
    
    def create_branch(self, branch_name):
        """Create a new branch and make it the current branch"""
        metadata = self._load_metadata()
        
        # Check if branch already exists
        if branch_name in metadata['branches']:
            raise ValueError(f"Branch '{branch_name}' already exists")
        
        # Get the latest commit hash from current branch
        latest_commit = None
        commits = self.list_commits()
        if commits:
            latest_commit = commits[0]['hash']
        
        # Get current branch before switching
        current_branch = metadata['current_branch']
        
        # Initialize branch_history if it doesn't exist
        if 'branch_history' not in metadata:
            metadata['branch_history'] = {}
            
        # Record branch creation history
        metadata['branch_history'][branch_name] = {
            'parent': current_branch,
            'timestamp': datetime.now().isoformat(),
            'commits': []
        }
        
        # Add new branch to metadata
        metadata['branches'].append(branch_name)
        metadata['current_branch'] = branch_name
        self._save_metadata(metadata)
        
        # If we have a commit, let's create an initial branch commit
        if latest_commit:
            # Copy the latest commit file to the new branch commit
            latest_commit_file = self.commits_dir / latest_commit / self.project_path.name
            self.checkout(latest_commit)  # First checkout the latest commit
            
            # Then create a new commit for the branch
            self.commit(f"Initial commit for branch '{branch_name}'")
        
        return branch_name
    
    def list_branches(self):
        """List all branches"""
        metadata = self._load_metadata()
        return metadata['branches']
    
    def get_current_branch(self):
        """Get the current branch name"""
        metadata = self._load_metadata()
        return metadata['current_branch']
    
    def switch_branch(self, branch_name):
        """Switch to a different branch"""
        metadata = self._load_metadata()
        
        # Validate branch exists
        if branch_name not in metadata['branches']:
            raise ValueError(f"Branch '{branch_name}' does not exist")
        
        # Update current branch
        metadata['current_branch'] = branch_name
        self._save_metadata(metadata)
        
        # Get latest commit from the branch and checkout
        branch_commits = [c for c in self.list_all_commits() if c['branch'] == branch_name]
        if branch_commits:
            latest_commit = branch_commits[0]['hash']
            self.checkout(latest_commit)
            return latest_commit
        
        return None
    
    def checkout(self, commit_hash):
        """Restore project to a specific commit state"""
        commit_log = self._load_commit_log()
        if commit_hash not in commit_log:
            raise ValueError(f"Commit {commit_hash} not found")
            
        # Restore from commit by replacing the original file
        commit_file = self.commits_dir / commit_hash / self.project_path.name
        shutil.copy2(commit_file, self.project_path)
        
        return commit_hash
    
    def get_commit_details(self, commit_hash):
        """Get detailed information about a specific commit"""
        commit_log = self._load_commit_log()
        if commit_hash not in commit_log:
            raise ValueError(f"Commit {commit_hash} not found")
        return commit_log[commit_hash]
    
    def delete_commit(self, commit_hash):
        """
        Delete a specific commit from the current branch
        
        If the commit is from a parent branch, it will only be hidden from the current branch's history
        but will remain available to other branches. If it's a direct commit to the current branch,
        the commit will be fully removed if not used by any other branch.
        """
        commit_log = self._load_commit_log()
        metadata = self._load_metadata()
        current_branch = metadata['current_branch']
        
        # Check if commit exists
        if commit_hash not in commit_log:
            raise ValueError(f"Commit {commit_hash} not found")
        
        commit_info = commit_log[commit_hash]
        commit_branch = commit_info.get('branch', 'main')
        
        # Set up branch exclusion list if it doesn't exist
        if 'branch_exclusions' not in metadata:
            metadata['branch_exclusions'] = {}
        
        if current_branch not in metadata['branch_exclusions']:
            metadata['branch_exclusions'][current_branch] = []
        
        # If the commit is from a parent branch, just add it to exclusions for current branch
        if commit_branch != current_branch:
            # Add to exclusion list for the current branch
            if commit_hash not in metadata['branch_exclusions'][current_branch]:
                metadata['branch_exclusions'][current_branch].append(commit_hash)
                self._save_metadata(metadata)
            return commit_hash
        
        # If it's a direct commit to the current branch, check if it's used by other branches
        # first add it to current branch exclusions
        if commit_hash not in metadata['branch_exclusions'][current_branch]:
            metadata['branch_exclusions'][current_branch].append(commit_hash)
        
        # Check if any other branch depends on this commit
        is_used_by_other_branches = False
        for branch_name in metadata['branches']:
            if branch_name == current_branch:
                continue
                
            # Check if this commit is in the branch's history and not excluded
            branch_exclusions = metadata['branch_exclusions'].get(branch_name, [])
            if commit_hash not in branch_exclusions:
                # For other branches, we need to check if they inherit this commit
                if branch_name in metadata.get('branch_history', {}):
                    parent_branch = metadata['branch_history'][branch_name]['parent']
                    branch_point = metadata['branch_history'][branch_name]['timestamp']
                    commit_timestamp = commit_info['timestamp']
                    
                    # Check if commit is from a parent branch and before branch creation
                    parent_hierarchy = self._get_branch_hierarchy(parent_branch, metadata.get('branch_history', {}))
                    
                    if commit_branch in parent_hierarchy and commit_timestamp < branch_point:
                        is_used_by_other_branches = True
                        break
                
                # Check if this commit directly belongs to another branch
                if commit_branch == branch_name:
                    is_used_by_other_branches = True
                    break
        
        # If not used by other branches, physically remove the commit
        if not is_used_by_other_branches:
            # Remove the commit directory
            commit_dir = self.commits_dir / commit_hash
            if commit_dir.exists():
                shutil.rmtree(commit_dir)
            
            # Remove from commit log
            del commit_log[commit_hash]
            self._save_commit_log(commit_log)
        
        self._save_metadata(metadata)
        return commit_hash
    
    def delete_branch(self, branch_name):
        """
        Delete a branch and all its unique commits
        
        This will only delete commits that are specific to this branch and not inherited by
        or shared with other branches.
        """
        metadata = self._load_metadata()
        
        # Check if branch exists
        if branch_name not in metadata['branches']:
            raise ValueError(f"Branch '{branch_name}' does not exist")
        
        # Cannot delete the current branch or 'main' branch
        current_branch = metadata['current_branch']
        if branch_name == current_branch:
            raise ValueError(f"Cannot delete the current branch. Switch to another branch first.")
        
        if branch_name == 'main':
            raise ValueError(f"Cannot delete the 'main' branch.")
        
        # Get all commits specific to this branch
        commit_log = self._load_commit_log()
        branch_specific_commits = []
        
        for commit_hash, info in commit_log.items():
            commit_branch = info.get('branch', 'main')
            
            # If commit directly belongs to this branch
            if commit_branch == branch_name:
                branch_specific_commits.append(commit_hash)
        
        # Delete each commit unique to this branch
        for commit_hash in branch_specific_commits:
            # Check if commit is used by other branches
            is_used_by_other_branches = False
            for other_branch in metadata['branches']:
                if other_branch == branch_name:
                    continue
                    
                # Check if other branch inherits from this branch
                if other_branch in metadata.get('branch_history', {}):
                    other_parent = metadata['branch_history'][other_branch]['parent']
                    if other_parent == branch_name:
                        is_used_by_other_branches = True
                        break
            
            # If not used by other branches, remove it
            if not is_used_by_other_branches:
                # Remove the commit directory
                commit_dir = self.commits_dir / commit_hash
                if commit_dir.exists():
                    shutil.rmtree(commit_dir)
                
                # Remove from commit log
                if commit_hash in commit_log:
                    del commit_log[commit_hash]
        
        # Remove branch from branches list
        metadata['branches'].remove(branch_name)
        
        # Remove branch exclusions
        if 'branch_exclusions' in metadata and branch_name in metadata['branch_exclusions']:
            del metadata['branch_exclusions'][branch_name]
            
        # Remove branch history
        if 'branch_history' in metadata and branch_name in metadata['branch_history']:
            del metadata['branch_history'][branch_name]
            
        # Save changes
        self._save_commit_log(commit_log)
        self._save_metadata(metadata)
        
        return branch_name