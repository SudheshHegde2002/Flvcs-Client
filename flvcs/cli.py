import click
import os
from pathlib import Path
import json
from flvcs.main import FLStudioVCS
from tabulate import tabulate
from datetime import datetime

def find_project_root():
    """Find the nearest parent directory containing .flvcs"""
    current = Path.cwd()
    while current != current.parent:
        if (current / '.flvcs').exists():
            return current
        current = current.parent
    return None

def get_project_file():
    """Find the FL Studio project file in the current directory"""
    flp_files = list(Path.cwd().glob('*.flp'))
    if not flp_files:
        raise click.ClickException("No .flp file found in current directory")
    if len(flp_files) > 1:
        raise click.ClickException("Multiple .flp files found. Please specify which one to track.")
    return flp_files[0]

def ensure_in_project():
    """Ensure we're in a FLVCS project directory"""
    root = find_project_root()
    if not root:
        raise click.ClickException("Not in a FLVCS project directory. Run 'flvcs init' first.")
    return root

@click.group()
def cli():
    """FL Studio Version Control System"""
    pass

@cli.command()
def init():
    """Initialize version control in current directory"""
    try:
        project_file = get_project_file()
        vcs = FLStudioVCS(project_file)
        click.echo(f"Initialized version control for {project_file.name}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.argument('message')
def commit(message):
    """Create a new commit with the current project state"""
    try:
        ensure_in_project()
        project_file = get_project_file()
        vcs = FLStudioVCS(project_file)
        commit_hash = vcs.commit(message)
        click.echo(f"Created commit {commit_hash}: {message}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
def log():
    """Show commit history"""
    try:
        ensure_in_project()
        project_file = get_project_file()
        vcs = FLStudioVCS(project_file)
        commits = vcs.list_commits()
        
        if not commits:
            click.echo("No commits yet")
            return
            
        table_data = []
        for commit in commits:
            date = datetime.fromisoformat(commit['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            table_data.append([
                commit['hash'],
                date,
                commit['message']
            ])
            
        click.echo(tabulate(
            table_data,
            headers=['Commit', 'Date', 'Message'],
            tablefmt='grid'
        ))
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.argument('commit_hash')
def checkout(commit_hash):
    """Restore project to a specific commit"""
    try:
        ensure_in_project()
        project_file = get_project_file()
        vcs = FLStudioVCS(project_file)
        backup_path = vcs.checkout(commit_hash)
        click.echo(f"Restored to commit {commit_hash}")
        click.echo(f"Backup saved at: {backup_path}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
def status():
    """Show project status and metadata"""
    try:
        ensure_in_project()
        project_file = get_project_file()
        vcs = FLStudioVCS(project_file)
        metadata = vcs.get_metadata()
        
        click.echo("\nProject Status:")
        click.echo(f"Project: {metadata['project_name']}.flp")
        click.echo(f"Created: {metadata['created_at']}")
        click.echo(f"Last Modified: {metadata['last_modified']}")
        click.echo(f"Total Commits: {metadata['total_commits']}")
        click.echo(f"Current Branch: {metadata['current_branch']}")
        
        # Show size history
        size_history = metadata['project_stats']['size_history']
        if size_history:
            latest_size = size_history[-1]['size_bytes']
            click.echo(f"\nCurrent Size: {latest_size / 1024:.2f} KB")
        
        # Show audio statistics
        audio_stats = metadata['audio_stats']
        if audio_stats and audio_stats['total_audio_files'] > 0:
            click.echo("\nAudio Statistics:")
            click.echo(f"Total Audio Files: {audio_stats['total_audio_files']}")
            click.echo(f"Total Duration: {audio_stats['total_duration']:.2f} seconds")
            click.echo("\nFormats:")
            for format_name, count in audio_stats['formats'].items():
                click.echo(f"  {format_name}: {count}")
            click.echo("\nSample Rates:")
            for rate, count in audio_stats['sample_rates'].items():
                click.echo(f"  {rate}: {count}")
            
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
@cli.command()
def backups():
    """List all backup files"""
    try:
        ensure_in_project()
        project_file = get_project_file()
        vcs = FLStudioVCS(project_file)
        
        backup_files = vcs.list_backups()
        
        if not backup_files:
            click.echo("No backup files found")
            return
        
        click.echo("Backup Files:")
        for backup in backup_files:
            click.echo(f"  {backup}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.argument('backup_filename')
def restore(backup_filename):
    """Restore project from a specific backup file"""
    try:
        ensure_in_project()
        project_file = get_project_file()
        vcs = FLStudioVCS(project_file)
        
        new_backup_path = vcs.restore_backup(backup_filename)
        click.echo(f"Restored from backup {backup_filename}")
        click.echo(f"Current state backed up at: {new_backup_path}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

if __name__ == '__main__':
    cli()