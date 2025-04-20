import click
import os
from pathlib import Path
import json
from flvcs.main import DAWVCS
from flvcs.data_utils import upload_data, download_data, ensure_authenticated, delete_user_auth
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
    """Find a suitable project file in the current directory or return the first file"""
    # Common DAW project file extensions
    daw_extensions = ['.flp', '.als', '.ptx', '.cpr', '.rpp', '.logic', '.aup', '.aup3', '.sfl', '.sesx', '.reason']
    
    # First, look for DAW project files
    for ext in daw_extensions:
        project_files = list(Path.cwd().glob(f'*{ext}'))
        if project_files:
            if len(project_files) > 1:
                # If multiple files of the same type, give a warning but return the first one
                click.echo(f"Warning: Multiple{ext} files found. Using {project_files[0].name}")
            return project_files[0]
    
    # If an existing VCS folder exists, try to find the tracked file from metadata
    vcs_dir = Path.cwd() / '.flvcs'
    if vcs_dir.exists():
        metadata_path = vcs_dir / 'metadata.json'
        if metadata_path.exists():
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    project_name = metadata.get('project_name', '')
                    if project_name:
                        # Try to find files matching that name
                        for file in Path.cwd().glob(f"{project_name}.*"):
                            return file
            except:
                pass
    
    # If no DAW project files, ask the user which file to track
    all_files = [f for f in Path.cwd().iterdir() if f.is_file() and not f.name.startswith('.')]
    if not all_files:
        raise click.ClickException("No files found in current directory to track")
    
    if len(all_files) == 1:
        return all_files[0]
    
    # If multiple files, let user select
    click.echo("Multiple files found. Please specify which file to track with the --file option")
    for i, file in enumerate(all_files):
        click.echo(f"{i+1}. {file.name}")
    
    choice = click.prompt("Select a file number to track", type=int, default=1)
    if 1 <= choice <= len(all_files):
        return all_files[choice-1]
    else:
        return all_files[0]

def ensure_in_project():
    """Ensure we're in a version control project directory"""
    root = find_project_root()
    if not root:
        raise click.ClickException("Not in an FLVCS project directory. Run 'flvcs init' first.")
    return root

@click.group()
def cli():
    """FLVCS - Version Control System for Digital Audio Workstations"""
    pass

@cli.command()
@click.option('--file', help='Specific file to track')
def init(file):
    """Initialize version control in current directory"""
    try:
        # Check if already initialized
        vcs_dir = Path.cwd() / '.flvcs'
        if vcs_dir.exists():
            click.echo("Version control is already initialized in this directory")
            return
            
        # Get the file to track
        if file:
            project_file = Path(file)
            if not project_file.exists():
                raise click.ClickException(f"File {file} not found")
        else:
            try:
                project_file = get_project_file()
            except click.ClickException as e:
                click.echo(f"Error: {str(e)}", err=True)
                return
        
        vcs = DAWVCS(project_file)
        # Create an initial commit
        commit_hash = vcs.commit("Initial commit")
        click.echo(f"Initialized version control for {project_file.name}")
        click.echo(f"Created initial commit {commit_hash}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.argument('message')
def commit(message):
    """Create a new commit with the current project state"""
    try:
        ensure_in_project()
        project_file = get_project_file()
        vcs = DAWVCS(project_file)
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
        vcs = DAWVCS(project_file)
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
                commit['branch'],
                commit['message']
            ])
            
        click.echo(tabulate(
            table_data,
            headers=['Commit', 'Date', 'Branch', 'Message'],
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
        vcs = DAWVCS(project_file)
        vcs.checkout(commit_hash)
        click.echo(f"Restored project to commit {commit_hash}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
def status():
    """Show project status and metadata"""
    try:
        ensure_in_project()
        project_file = get_project_file()
        vcs = DAWVCS(project_file)
        metadata = vcs.get_metadata()
        
        click.echo("\nProject Status:")
        click.echo(f"Project: {metadata['project_name']}{project_file.suffix}")
        click.echo(f"Created: {metadata['created_at']}")
        click.echo(f"Last Modified: {metadata['last_modified']}")
        click.echo(f"Total Commits: {metadata['total_commits']}")
        click.echo(f"Current Branch: {metadata['current_branch']}")
        
        # Show available branches
        click.echo(f"\nBranches:")
        for branch in metadata['branches']:
            if branch == metadata['current_branch']:
                click.echo(f"  * {branch} (current)")
            else:
                click.echo(f"    {branch}")
        
        # Show size history
        size_history = metadata['project_stats']['size_history']
        if size_history:
            latest_size = size_history[-1]['size_bytes']
            click.echo(f"\nCurrent Size: {latest_size / 1024:.2f} KB")
        
        # Show audio statistics
        audio_stats = metadata['audio_stats']
        if audio_stats and audio_stats.get('total_audio_files', 0) > 0:
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

@cli.group()
def branch():
    """Branch management commands"""
    pass

@branch.command(name="create")
@click.argument('branch_name')
def branch_create(branch_name):
    """Create a new branch from the current branch"""
    try:
        ensure_in_project()
        project_file = get_project_file()
        vcs = DAWVCS(project_file)
        
        # Get current branch before switching
        current_branch = vcs.get_current_branch()
        
        vcs.create_branch(branch_name)
        click.echo(f"Created new branch '{branch_name}' from '{current_branch}'")
        click.echo(f"Switched to branch '{branch_name}'")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@branch.command(name="list")
def branch_list():
    """List all branches"""
    try:
        ensure_in_project()
        project_file = get_project_file()
        vcs = DAWVCS(project_file)
        
        branches = vcs.list_branches()
        current_branch = vcs.get_current_branch()
        
        click.echo("Branches:")
        for branch in branches:
            if branch == current_branch:
                click.echo(f"  * {branch} (current)")
            else:
                click.echo(f"    {branch}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@branch.command(name="switch")
@click.argument('branch_name')
def branch_switch(branch_name):
    """Switch to a different branch"""
    try:
        ensure_in_project()
        project_file = get_project_file()
        vcs = DAWVCS(project_file)
        
        # Get current branch before switching
        current_branch = vcs.get_current_branch()
        
        if current_branch == branch_name:
            click.echo(f"Already on branch '{branch_name}'")
            return
        
        commit_hash = vcs.switch_branch(branch_name)
        click.echo(f"Switched from branch '{current_branch}' to '{branch_name}'")
        if commit_hash:
            click.echo(f"Restored project to latest commit {commit_hash}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@branch.command(name="current")
def branch_current():
    """Show the current branch"""
    try:
        ensure_in_project()
        project_file = get_project_file()
        vcs = DAWVCS(project_file)
        
        current_branch = vcs.get_current_branch()
        click.echo(f"Current branch: {current_branch}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@branch.command(name="delete")
@click.argument('branch_name')
def branch_delete(branch_name):
    """Delete a branch and its unique commits"""
    try:
        ensure_in_project()
        project_file = get_project_file()
        vcs = DAWVCS(project_file)
        
        # Get current branch before deletion
        current_branch = vcs.get_current_branch()
        
        if branch_name == current_branch:
            click.echo(f"Cannot delete the current branch. Switch to another branch first.")
            return
        
        if branch_name == 'main':
            click.echo(f"Cannot delete the 'main' branch.")
            return
        
        # Confirm deletion
        if not click.confirm(f"Are you sure you want to delete branch '{branch_name}'? This cannot be undone."):
            click.echo("Branch deletion cancelled.")
            return
        
        vcs.delete_branch(branch_name)
        click.echo(f"Deleted branch '{branch_name}' and its unique commits")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.argument('commit_hash')
def delete(commit_hash):
    """Delete a specific commit from the current branch"""
    try:
        ensure_in_project()
        project_file = get_project_file()
        vcs = DAWVCS(project_file)
        
        # Get commit details before deletion
        try:
            commit_details = vcs.get_commit_details(commit_hash)
            commit_message = commit_details.get('message', 'Unknown commit')
        except:
            commit_message = 'Unknown commit'
        
        # Confirm deletion
        if not click.confirm(f"Are you sure you want to delete commit {commit_hash} ({commit_message})? This cannot be undone."):
            click.echo("Commit deletion cancelled.")
            return
        
        vcs.delete_commit(commit_hash)
        click.echo(f"Deleted commit {commit_hash} from the current branch")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
def upload():
    """Upload the current branch data to the server"""
    try:
        ensure_in_project()
        project_root = find_project_root()
        project_file = get_project_file()
        vcs = DAWVCS(project_file)
        
        # Get current branch
        current_branch = vcs.get_current_branch()
        
        click.echo(f"Uploading branch '{current_branch}' to server...")
        success = upload_data(project_root, current_branch)
        
        if success:
            click.echo(f"Successfully uploaded branch '{current_branch}'")
        else:
            click.echo(f"Failed to upload branch '{current_branch}'")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.option('--branch', help='Specific branch to download (defaults to current branch)')
def download(branch):
    """Download branch data from the server and update local files"""
    try:
        ensure_in_project()
        project_root = find_project_root()
        project_file = get_project_file()
        vcs = DAWVCS(project_file)
        
        # Use specified branch or current branch
        if branch:
            branch_name = branch
        else:
            branch_name = vcs.get_current_branch()
        
        click.echo(f"Downloading branch '{branch_name}' from server...")
        success = download_data(project_root, branch_name)
        
        if success:
            click.echo(f"Successfully downloaded branch '{branch_name}'")
            
            # If the download was for the current branch, reload the project file
            if branch_name == vcs.get_current_branch():
                click.echo("Updating local project file...")
                
                # Get the latest commit for this branch to checkout
                commits = vcs.list_commits()
                if commits:
                    latest_commit = commits[0]['hash']
                    vcs.checkout(latest_commit)
                    click.echo(f"Updated project file to latest commit ({latest_commit})")
        else:
            click.echo(f"Failed to download branch '{branch_name}'")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command(name="delete-cred")
def delete_cred():
    """Delete stored authentication credentials"""
    try:
        if delete_user_auth():
            click.echo("Authentication credentials successfully deleted.")
            click.echo("You will need to reauthenticate on your next upload or download.")
        else:
            click.echo("No authentication credentials found.")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

if __name__ == '__main__':
    cli()