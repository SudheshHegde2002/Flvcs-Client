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

class FLStudioVCS:
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
        
        # Update commit log
        commit_log = self._load_commit_log()
        commit_log[commit_hash] = {
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'file': self.project_path.name
        }
        self._save_commit_log(commit_log)
        
        # Update metadata
        self._update_metadata()
        
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
    
    # Previous methods remain the same
    def list_commits(self):
        """List all commits with their messages and timestamps"""
        commit_log = self._load_commit_log()
        commits = []
        for commit_hash, info in commit_log.items():
            commits.append({
                'hash': commit_hash,
                'message': info['message'],
                'timestamp': info['timestamp']
            })
        return sorted(commits, key=lambda x: x['timestamp'], reverse=True)
    
  
    def checkout(self, commit_hash):
        """Restore project to a specific commit state"""
        commit_log = self._load_commit_log()
        if commit_hash not in commit_log:
            raise ValueError(f"Commit {commit_hash} not found")
            
        # Generate a unique backup filename
        backup_filename = (
            f"{self.project_path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{self.project_path.suffix}"
        )
        backup_path = self.project_path.parent / backup_filename
        
        # Copy current project file to backup
        shutil.copy2(self.project_path, backup_path)
        click.echo(f"Backup created: {backup_filename}")
        
        # Restore from commit
        commit_file = self.commits_dir / commit_hash / self.project_path.name
        shutil.copy2(commit_file, self.project_path)
        
        return backup_path
    
    def list_backups(self):
        """List all backup files in the project directory"""
        backup_files = list(self.project_path.parent.glob(f"{self.project_path.stem}_backup_*{self.project_path.suffix}"))
        return [backup.name for backup in backup_files]

    def restore_backup(self, backup_filename):
        """Restore from a specific backup file"""
        backup_path = self.project_path.parent / backup_filename
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file {backup_filename} not found")
        
        # Create a new backup of current state
        new_backup_filename = (
            f"{self.project_path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{self.project_path.suffix}"
        )
        new_backup_path = self.project_path.parent / new_backup_filename
        shutil.copy2(self.project_path, new_backup_path)
        
        # Restore from backup
        shutil.copy2(backup_path, self.project_path)
        
        return new_backup_path
    
    def get_commit_details(self, commit_hash):
        """Get detailed information about a specific commit"""
        commit_log = self._load_commit_log()
        if commit_hash not in commit_log:
            raise ValueError(f"Commit {commit_hash} not found")
        return commit_log[commit_hash]