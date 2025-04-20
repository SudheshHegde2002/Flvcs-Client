import sys
import os
from pathlib import Path
from datetime import datetime
import json

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QTabWidget, 
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QComboBox, QMessageBox, QSplitter, QFrame, QTreeWidget, 
    QTreeWidgetItem, QGroupBox, QFormLayout, QStatusBar, QInputDialog,
    QDialog
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon

from flvcs.main import DAWVCS
from flvcs.data_utils import upload_data, download_data, ensure_authenticated, load_user_auth, delete_user_auth, reset_upload_tracking

# Define theme colors
COLORS = {
    'primary': '#7B68EE',  # Medium slate blue
    'secondary': '#9370DB',  # Medium purple
    'background': '#2D2D30',  # Dark background
    'text': '#E0E0E0',  # Light text
    'accent': '#B39DDB',  # Light purple
    'success': '#81C784',  # Light green
    'hover': '#8A75F5',  # Slightly lighter primary
    'border': '#4A4A4D',  # Darker border
    'commit_bg': '#352F59',  # Dark purplish background
}

class StyleHelper:
    @staticmethod
    def get_stylesheet():
        return f"""
            QWidget {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                font-size: 10pt;
            }}
            
            QMainWindow {{
                background-color: {COLORS['background']};
            }}
            
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background-color: {COLORS['hover']};
            }}
            
            QPushButton:pressed {{
                background-color: {COLORS['secondary']};
            }}
            
            QLineEdit, QTextEdit, QComboBox {{
                background-color: {COLORS['border']};
                border: 1px solid {COLORS['secondary']};
                border-radius: 4px;
                padding: 5px;
                color: {COLORS['text']};
            }}
            
            QTableWidget, QTreeWidget {{
                background-color: {COLORS['background']};
                alternate-background-color: {COLORS['border']};
                border: 1px solid {COLORS['border']};
                gridline-color: {COLORS['border']};
            }}
            
            QTableWidget::item, QTreeWidget::item {{
                padding: 4px;
            }}
            
            QHeaderView::section {{
                background-color: {COLORS['primary']};
                color: white;
                padding: 5px;
                border: none;
            }}
            
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
            
            QTabBar::tab {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {COLORS['primary']};
                color: white;
            }}
            
            QGroupBox {{
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                margin-top: 10px;
                font-weight: bold;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
            
            QSplitter::handle {{
                background-color: {COLORS['border']};
            }}
        """


class CommitDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Commit")
        self.setFixedSize(400, 250)
        
        self.layout = QVBoxLayout(self)
        
        # Commit message label and field
        self.layout.addWidget(QLabel("Commit Message:"))
        self.commit_message = QTextEdit()
        self.commit_message.setPlaceholderText("Enter a description of your changes...")
        self.layout.addWidget(self.commit_message)
        
        # Buttons
        self.button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel")
        self.commit_button = QPushButton("Commit")
        self.commit_button.setObjectName("primary-button")
        
        self.button_layout.addWidget(self.cancel_button)
        self.button_layout.addWidget(self.commit_button)
        self.layout.addLayout(self.button_layout)
        
        # Connect signals
        self.cancel_button.clicked.connect(self.close)


class AuthDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FLVCS Authentication")
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout(self)
        
        # Information label
        info_label = QLabel(
            "Please log in using your browser.\n"
            "After logging in, you will receive a UID.\n"
            "Enter that UID below:"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # UID field
        uid_layout = QHBoxLayout()
        uid_layout.addWidget(QLabel("UID:"))
        self.uid_field = QLineEdit()
        self.uid_field.setEchoMode(QLineEdit.Password)  # Mask the input for security
        uid_layout.addWidget(self.uid_field)
        layout.addLayout(uid_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel")
        self.ok_button = QPushButton("OK")
        self.ok_button.setDefault(True)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)
        
        # Connect signals
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button.clicked.connect(self.accept)


class FLVCSMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.vcs = None
        self.project_file = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("FLVCS")
        self.setMinimumSize(900, 600)
        
        # Apply stylesheet
        self.setStyleSheet(StyleHelper.get_stylesheet())
        
        # Create central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # Create the top section with project info and main actions
        self.create_top_section()
        
        # Create the tab widget for different views
        self.tabs = QTabWidget()
        self.main_layout.addWidget(self.tabs)
        
        # Create tabs
        self.create_commits_tab()
        self.create_branches_tab()
        self.create_stats_tab()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Open or initialize a project with FLVCS to begin.")
        
        # Check if we're already in a VCS project
        self.check_current_directory()
    
    def create_top_section(self):
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        
        # Project info section
        project_group = QGroupBox("Project")
        project_layout = QFormLayout(project_group)
        
        self.project_name_label = QLabel("No project loaded")
        self.branch_label = QLabel("No branch")
        
        project_layout.addRow("Project:", self.project_name_label)
        project_layout.addRow("Branch:", self.branch_label)
        
        top_layout.addWidget(project_group, 3)
        
        # Actions section
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        actions_row1 = QHBoxLayout()
        self.init_button = QPushButton("Initialize")
        self.open_button = QPushButton("Open Project")
        self.refresh_button = QPushButton("Refresh")
        actions_row1.addWidget(self.init_button)
        actions_row1.addWidget(self.open_button)
        actions_row1.addWidget(self.refresh_button)
        
        actions_row2 = QHBoxLayout()
        self.commit_button = QPushButton("Create Commit")
        self.commit_button.setStyleSheet(f"background-color: {COLORS['success']};")
        self.commit_message = QLineEdit()
        self.commit_message.setPlaceholderText("Commit message...")
        actions_row2.addWidget(self.commit_message, 7)
        actions_row2.addWidget(self.commit_button, 3)
        
        # Add sync buttons
        actions_row3 = QHBoxLayout()
        self.upload_button = QPushButton("Upload")
        self.upload_button.setStyleSheet(f"background-color: #3F51B5; color: white;")  # Indigo
        self.download_button = QPushButton("Download")
        self.download_button.setStyleSheet(f"background-color: #3F51B5; color: white;")  # Indigo
        self.reset_tracking_button = QPushButton("Reset Tracking")
        self.reset_tracking_button.setStyleSheet(f"background-color: #FF9800; color: white;")  # Orange
        actions_row3.addWidget(self.upload_button)
        actions_row3.addWidget(self.download_button)
        actions_row3.addWidget(self.reset_tracking_button)
        
        # Add credentials management
        actions_row4 = QHBoxLayout()
        self.delete_cred_button = QPushButton("Delete Credentials")
        self.delete_cred_button.setStyleSheet(f"background-color: #E57373; color: white;")  # Red button
        actions_row4.addWidget(self.delete_cred_button)
        
        actions_layout.addLayout(actions_row1)
        actions_layout.addLayout(actions_row2)
        actions_layout.addLayout(actions_row3)
        actions_layout.addLayout(actions_row4)
        
        top_layout.addWidget(actions_group, 7)
        
        self.main_layout.addWidget(top_widget)
        
        # Connect signals
        self.init_button.clicked.connect(self.initialize_vcs)
        self.open_button.clicked.connect(self.open_project)
        self.refresh_button.clicked.connect(self.refresh_ui)
        self.commit_button.clicked.connect(self.create_commit)
        self.upload_button.clicked.connect(self.upload_branch)
        self.download_button.clicked.connect(self.download_branch)
        self.delete_cred_button.clicked.connect(self.delete_credentials)
        self.reset_tracking_button.clicked.connect(self.reset_upload_tracking)
    
    def create_commits_tab(self):
        commits_widget = QWidget()
        commits_layout = QVBoxLayout(commits_widget)
        
        # Commits table
        self.commits_table = QTableWidget()
        self.commits_table.setColumnCount(4)
        self.commits_table.setHorizontalHeaderLabels(["Commit", "Date", "Branch", "Message"])
        self.commits_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.commits_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.commits_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.commits_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        
        # Action buttons row
        action_layout = QHBoxLayout()
        
        # Checkout section
        checkout_layout = QHBoxLayout()
        checkout_layout.addWidget(QLabel("Checkout commit:"))
        self.checkout_combo = QComboBox()
        self.checkout_combo.setMinimumWidth(300)
        self.checkout_button = QPushButton("Checkout")
        
        checkout_layout.addWidget(self.checkout_combo)
        checkout_layout.addWidget(self.checkout_button)
        
        # Delete commit section
        delete_layout = QHBoxLayout()
        self.delete_commit_button = QPushButton("Delete Commit")
        self.delete_commit_button.setStyleSheet(f"background-color: #E57373; color: white;")  # Red delete button
        delete_layout.addWidget(self.delete_commit_button)
        
        action_layout.addLayout(checkout_layout, 7)
        action_layout.addLayout(delete_layout, 3)
        
        commits_layout.addWidget(self.commits_table)
        commits_layout.addLayout(action_layout)
        
        self.tabs.addTab(commits_widget, "Commits")
        
        # Connect signals
        self.checkout_button.clicked.connect(self.checkout_commit)
        self.delete_commit_button.clicked.connect(self.delete_commit)
        self.commits_table.itemSelectionChanged.connect(self.on_commit_selected)
    
    def create_branches_tab(self):
        branches_widget = QWidget()
        branches_layout = QVBoxLayout(branches_widget)
        
        # Branch management
        create_branch_layout = QHBoxLayout()
        create_branch_layout.addWidget(QLabel("Create new branch:"))
        self.new_branch_name = QLineEdit()
        self.new_branch_name.setPlaceholderText("New branch name...")
        self.create_branch_button = QPushButton("Create Branch")
        
        create_branch_layout.addWidget(self.new_branch_name, 7)
        create_branch_layout.addWidget(self.create_branch_button, 3)
        
        branches_layout.addLayout(create_branch_layout)
        
        # Branches table
        self.branches_table = QTableWidget()
        self.branches_table.setColumnCount(2)
        self.branches_table.setHorizontalHeaderLabels(["Branch", "Status"])
        self.branches_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.branches_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        
        # Branch actions section
        actions_layout = QHBoxLayout()
        
        # Switch branch section
        switch_layout = QHBoxLayout()
        switch_layout.addWidget(QLabel("Switch to:"))
        self.branch_combo = QComboBox()
        self.switch_branch_button = QPushButton("Switch Branch")
        
        switch_layout.addWidget(self.branch_combo)
        switch_layout.addWidget(self.switch_branch_button)
        
        # Delete branch section
        delete_layout = QHBoxLayout()
        self.delete_branch_button = QPushButton("Delete Branch")
        self.delete_branch_button.setStyleSheet(f"background-color: #E57373; color: white;")  # Red delete button
        delete_layout.addWidget(self.delete_branch_button)
        
        actions_layout.addLayout(switch_layout, 7)
        actions_layout.addLayout(delete_layout, 3)
        
        branches_layout.addWidget(self.branches_table)
        branches_layout.addLayout(actions_layout)
        
        self.tabs.addTab(branches_widget, "Branches")
        
        # Connect signals
        self.create_branch_button.clicked.connect(self.create_branch)
        self.switch_branch_button.clicked.connect(self.switch_branch)
        self.delete_branch_button.clicked.connect(self.delete_branch)
        self.branches_table.itemSelectionChanged.connect(self.on_branch_selected)
    
    def create_stats_tab(self):
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        
        # Project statistics
        self.stats_group = QGroupBox("Project Statistics")
        stats_form = QFormLayout(self.stats_group)
        
        self.created_at_label = QLabel("--")
        self.last_modified_label = QLabel("--")
        self.total_commits_label = QLabel("--")
        self.current_size_label = QLabel("--")
        
        stats_form.addRow("Created:", self.created_at_label)
        stats_form.addRow("Last Modified:", self.last_modified_label)
        stats_form.addRow("Total Commits:", self.total_commits_label)
        stats_form.addRow("Current Size:", self.current_size_label)
        
        # Audio statistics
        self.audio_group = QGroupBox("Audio Statistics")
        audio_form = QFormLayout(self.audio_group)
        
        self.audio_files_label = QLabel("--")
        self.audio_duration_label = QLabel("--")
        
        audio_form.addRow("Total Audio Files:", self.audio_files_label)
        audio_form.addRow("Total Duration:", self.audio_duration_label)
        
        stats_layout.addWidget(self.stats_group)
        stats_layout.addWidget(self.audio_group)
        stats_layout.addStretch()
        
        self.tabs.addTab(stats_widget, "Statistics")
    
    def check_current_directory(self):
        """Check if the current directory is part of a VCS project"""
        try:
            current_dir = Path.cwd()
            vcs_dir = current_dir / '.flvcs'
            
            if vcs_dir.exists():
                # We found a FLVCS project, now find a file to track
                all_files = [f for f in current_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
                
                # Try to find the project file from metadata first
                metadata_path = vcs_dir / 'metadata.json'
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        project_name = metadata.get('project_name', '')
                        if project_name:
                            # Look for files matching the project name
                            for file in current_dir.glob(f"{project_name}.*"):
                                if file.is_file():
                                    self.project_file = file
                                    self.vcs = DAWVCS(self.project_file)
                                    self.load_project()
                                    self.status_bar.showMessage(f"Loaded FLVCS project: {self.project_file.name}")
                                    return
                
                # If we couldn't find a file from metadata, use any file
                if all_files:
                    self.project_file = all_files[0]
                    self.vcs = DAWVCS(self.project_file)
                    self.load_project()
                    self.status_bar.showMessage(f"Loaded FLVCS project: {self.project_file.name}")
                else:
                    # No suitable files found, create a placeholder file
                    placeholder_file = current_dir / "placeholder.flvcs"
                    if not placeholder_file.exists():
                        with open(placeholder_file, "w") as f:
                            f.write("FLVCS placeholder file")
                    self.project_file = placeholder_file
                    self.vcs = DAWVCS(self.project_file)
                    self.load_project()
                    self.status_bar.showMessage(f"Loaded FLVCS project with placeholder file")
                
        except Exception as e:
            self.status_bar.showMessage(f"Error: {str(e)}")
    
    def initialize_vcs(self):
        """Initialize version control for a project"""
        try:
            # Let user select which directory to initialize FLVCS in
            dir_dialog = QFileDialog()
            dir_dialog.setFileMode(QFileDialog.DirectoryOnly)
            directory = dir_dialog.getExistingDirectory(
                self, "Select Directory to Initialize FLVCS", "", QFileDialog.ShowDirsOnly)
            
            if not directory:
                return
                
            # Change to the selected directory
            os.chdir(directory)
            current_dir = Path.cwd()
            vcs_dir = current_dir / '.flvcs'
            
            # Check if already initialized
            if vcs_dir.exists():
                QMessageBox.information(self, "Already Initialized", 
                                       "FLVCS is already initialized in this directory.")
                
                # If project is not loaded yet, try to load it
                if not self.vcs:
                    self.check_current_directory()
                return
            
            # Get a placeholder file if none exists
            all_files = [f for f in current_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
            
            if all_files:
                # Use first existing file
                self.project_file = all_files[0]
            else:
                # Create an empty placeholder file
                placeholder_file = current_dir / "placeholder.flvcs"
                with open(placeholder_file, "w") as f:
                    f.write("FLVCS placeholder file")
                self.project_file = placeholder_file
            
            self.vcs = DAWVCS(self.project_file)
            
            # Create initial commit
            commit_hash = self.vcs.commit("Initial commit")
            
            QMessageBox.information(self, "Success", 
                                   f"Initialized FLVCS in {current_dir}\n"
                                   f"Created initial commit: {commit_hash}")
            
            self.load_project()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error initializing project: {str(e)}")
    
    def open_project(self):
        """Open an existing FLVCS repository"""
        try:
            # Let user select either a directory or a file
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            
            dialog = QFileDialog()
            dialog.setOptions(options)
            dialog.setFileMode(QFileDialog.Directory)
            dialog.setOption(QFileDialog.ShowDirsOnly, False)  # Allow file selection too
            dialog.setWindowTitle("Open FLVCS Project or Directory")
            
            if dialog.exec_():
                selected_paths = dialog.selectedFiles()
                if not selected_paths:
                    return
                    
                selected_path = Path(selected_paths[0])
                
                # Check if it's a directory or file
                if selected_path.is_dir():
                    # Change to the directory
                    os.chdir(selected_path)
                    
                    # Check if it has FLVCS initialized
                    if not (selected_path / '.flvcs').exists():
                        response = QMessageBox.question(
                            self, "Initialize FLVCS", 
                            f"This directory doesn't have FLVCS initialized. Initialize it?",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        
                        if response == QMessageBox.Yes:
                            self.initialize_vcs()  # Use the initialize method
                        return
                    
                    # Find a suitable project file
                    all_files = [f for f in selected_path.iterdir() if f.is_file() and not f.name.startswith('.')]
                    if all_files:
                        self.project_file = all_files[0]
                    else:
                        # No files found
                        QMessageBox.warning(self, "No Files", "No files found in this directory.")
                        return
                else:
                    # It's a file, use it as project file
                    self.project_file = selected_path
                    
                    # Make sure its directory has FLVCS
                    if not (self.project_file.parent / '.flvcs').exists():
                        response = QMessageBox.question(
                            self, "Initialize FLVCS", 
                            f"This directory doesn't have FLVCS initialized. Initialize it?",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        
                        if response == QMessageBox.Yes:
                            os.chdir(self.project_file.parent)
                            self.vcs = DAWVCS(self.project_file)
                            commit_hash = self.vcs.commit("Initial commit")
                            QMessageBox.information(
                                self, "Success", 
                                f"Initialized FLVCS in {self.project_file.parent}\n"
                                f"Created initial commit: {commit_hash}"
                            )
                        else:
                            return
                
                # Initialize VCS with the project file
                self.vcs = DAWVCS(self.project_file)
                self.load_project()
                self.status_bar.showMessage(f"Opened FLVCS project with {self.project_file.name}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error opening project: {str(e)}")
    
    def load_project(self):
        """Load project data into the UI"""
        if not self.vcs:
            return
            
        metadata = self.vcs.get_metadata()
        
        # Update project info
        self.project_name_label.setText(f"{metadata['project_name']}.flp")
        self.branch_label.setText(metadata['current_branch'])
        
        # Update commits table
        self.load_commits()
        
        # Update branches table
        self.load_branches()
        
        # Update statistics
        self.load_statistics()
    
    def load_commits(self):
        """Load commit history into the table"""
        if not self.vcs:
            return
            
        commits = self.vcs.list_commits()
        
        # Clear table and checkout combo
        self.commits_table.setRowCount(0)
        self.checkout_combo.clear()
        
        # Populate table
        self.commits_table.setRowCount(len(commits))
        for i, commit in enumerate(commits):
            hash_item = QTableWidgetItem(commit['hash'])
            date = datetime.fromisoformat(commit['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            date_item = QTableWidgetItem(date)
            branch_item = QTableWidgetItem(commit['branch'])
            message_item = QTableWidgetItem(commit['message'])
            
            self.commits_table.setItem(i, 0, hash_item)
            self.commits_table.setItem(i, 1, date_item)
            self.commits_table.setItem(i, 2, branch_item)
            self.commits_table.setItem(i, 3, message_item)
            
            # Add to checkout combo
            self.checkout_combo.addItem(f"{commit['hash']} - {commit['message']}", commit['hash'])
    
    def load_branches(self):
        """Load branches into the table"""
        if not self.vcs:
            return
            
        branches = self.vcs.list_branches()
        current_branch = self.vcs.get_current_branch()
        
        # Clear table and branch combo
        self.branches_table.setRowCount(0)
        self.branch_combo.clear()
        
        # Populate table
        self.branches_table.setRowCount(len(branches))
        for i, branch in enumerate(branches):
            branch_item = QTableWidgetItem(branch)
            
            status = "Current" if branch == current_branch else ""
            status_item = QTableWidgetItem(status)
            
            self.branches_table.setItem(i, 0, branch_item)
            self.branches_table.setItem(i, 1, status_item)
            
            # Add to branch combo if not current branch
            if branch != current_branch:
                self.branch_combo.addItem(branch)
    
    def load_statistics(self):
        """Load project statistics"""
        if not self.vcs:
            return
            
        metadata = self.vcs.get_metadata()
        
        # Update project stats
        created_date = datetime.fromisoformat(metadata['created_at']).strftime('%Y-%m-%d %H:%M:%S')
        modified_date = datetime.fromisoformat(metadata['last_modified']).strftime('%Y-%m-%d %H:%M:%S')
        
        self.created_at_label.setText(created_date)
        self.last_modified_label.setText(modified_date)
        self.total_commits_label.setText(str(metadata['total_commits']))
        
        # Size history
        size_history = metadata['project_stats']['size_history']
        if size_history:
            latest_size = size_history[-1]['size_bytes']
            self.current_size_label.setText(f"{latest_size / 1024:.2f} KB")
        
        # Audio statistics
        audio_stats = metadata['audio_stats']
        if audio_stats and audio_stats.get('total_audio_files', 0) > 0:
            self.audio_files_label.setText(str(audio_stats['total_audio_files']))
            self.audio_duration_label.setText(f"{audio_stats['total_duration']:.2f} seconds")
        else:
            self.audio_files_label.setText("No audio files")
            self.audio_duration_label.setText("--")
    
    def create_commit(self):
        """Create a new commit"""
        if not self.vcs:
            QMessageBox.warning(self, "No Project", "No project loaded.")
            return
            
        message = self.commit_message.text().strip()
        if not message:
            QMessageBox.warning(self, "Empty Message", "Please enter a commit message.")
            return
            
        try:
            commit_hash = self.vcs.commit(message)
            QMessageBox.information(self, "Success", f"Created commit: {commit_hash}")
            self.commit_message.clear()
            self.refresh_ui()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error creating commit: {str(e)}")
    
    def checkout_commit(self):
        """Checkout to selected commit"""
        if not self.vcs:
            return
            
        selected_index = self.checkout_combo.currentIndex()
        if selected_index < 0:
            return
            
        commit_hash = self.checkout_combo.itemData(selected_index)
        
        try:
            self.vcs.checkout(commit_hash)
            QMessageBox.information(self, "Success", f"Restored project to commit {commit_hash}")
            self.refresh_ui()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error checking out commit: {str(e)}")
    
    def create_branch(self):
        """Create a new branch"""
        if not self.vcs:
            return
            
        branch_name = self.new_branch_name.text().strip()
        if not branch_name:
            QMessageBox.warning(self, "Empty Name", "Please enter a branch name.")
            return
            
        try:
            current_branch = self.vcs.get_current_branch()
            self.vcs.create_branch(branch_name)
            QMessageBox.information(self, "Success", 
                                   f"Created new branch '{branch_name}' from '{current_branch}'\n"
                                   f"Switched to branch '{branch_name}'")
            self.new_branch_name.clear()
            self.refresh_ui()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error creating branch: {str(e)}")
    
    def switch_branch(self):
        """Switch to selected branch"""
        if not self.vcs:
            return
            
        selected_index = self.branch_combo.currentIndex()
        if selected_index < 0:
            return
            
        branch_name = self.branch_combo.itemText(selected_index)
        
        try:
            current_branch = self.vcs.get_current_branch()
            commit_hash = self.vcs.switch_branch(branch_name)
            QMessageBox.information(self, "Success", 
                                   f"Switched from branch '{current_branch}' to '{branch_name}'")
            self.refresh_ui()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error switching branch: {str(e)}")
    
    def on_commit_selected(self):
        """Update checkout combo when a commit is selected in the table"""
        selected_items = self.commits_table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        commit_hash = self.commits_table.item(row, 0).text()
        
        # Find and select this commit in the combo
        index = self.checkout_combo.findData(commit_hash)
        if index >= 0:
            self.checkout_combo.setCurrentIndex(index)
    
    def on_branch_selected(self):
        """Update branch combo when a branch is selected in the table"""
        selected_items = self.branches_table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        branch_name = self.branches_table.item(row, 0).text()
        
        # Find and select this branch in the combo
        index = self.branch_combo.findText(branch_name)
        if index >= 0:
            self.branch_combo.setCurrentIndex(index)
    
    def refresh_ui(self):
        """Refresh all UI elements"""
        self.load_project()
        self.status_bar.showMessage("UI refreshed")
    
    def delete_commit(self):
        """Delete selected commit"""
        if not self.vcs:
            return
            
        selected_items = self.commits_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Commit Selected", "Please select a commit to delete.")
            return
            
        row = selected_items[0].row()
        commit_hash = self.commits_table.item(row, 0).text()
        commit_message = self.commits_table.item(row, 3).text()
        
        # Confirm deletion
        response = QMessageBox.question(
            self, "Confirm Deletion", 
            f"Are you sure you want to delete commit {commit_hash} ({commit_message})?\n\n"
            f"This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # Default is No to prevent accidental deletion
        )
        
        if response != QMessageBox.Yes:
            return
            
        try:
            self.vcs.delete_commit(commit_hash)
            QMessageBox.information(self, "Success", f"Deleted commit {commit_hash} from the current branch")
            self.refresh_ui()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error deleting commit: {str(e)}")
    
    def delete_branch(self):
        """Delete selected branch"""
        if not self.vcs:
            return
            
        selected_items = self.branches_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Branch Selected", "Please select a branch to delete.")
            return
            
        row = selected_items[0].row()
        branch_name = self.branches_table.item(row, 0).text()
        
        # Check if trying to delete current branch or main
        current_branch = self.vcs.get_current_branch()
        if branch_name == current_branch:
            QMessageBox.warning(self, "Cannot Delete", "Cannot delete the current branch. Switch to another branch first.")
            return
            
        if branch_name == 'main':
            QMessageBox.warning(self, "Cannot Delete", "Cannot delete the 'main' branch.")
            return
            
        # Confirm deletion
        response = QMessageBox.question(
            self, "Confirm Deletion", 
            f"Are you sure you want to delete branch '{branch_name}' and all its unique commits?\n\n"
            f"This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # Default is No to prevent accidental deletion
        )
        
        if response != QMessageBox.Yes:
            return
            
        try:
            self.vcs.delete_branch(branch_name)
            QMessageBox.information(self, "Success", f"Deleted branch '{branch_name}' and its unique commits")
            self.refresh_ui()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error deleting branch: {str(e)}")
    
    def upload_branch(self):
        """Upload current branch to server"""
        if not self.vcs:
            QMessageBox.warning(self, "No Project", "No project loaded.")
            return
            
        try:
            # Check if user is already authenticated
            auth_data = load_user_auth()
            
            if auth_data is None or "uid" not in auth_data:
                # Import webbrowser here to avoid importing at module level
                import webbrowser
                from flvcs.data_utils import API_ENDPOINTS, save_user_auth
                
                # Open the login page in browser
                webbrowser.open(API_ENDPOINTS['login'])
                
                # Show dialog to get UID
                auth_dialog = AuthDialog(self)
                if auth_dialog.exec_() != QDialog.Accepted:
                    return  # User cancelled
                    
                uid = auth_dialog.uid_field.text().strip()
                if not uid:
                    QMessageBox.warning(self, "Authentication Failed", "No UID provided.")
                    return
                    
                # Save the UID
                save_user_auth(uid)
                auth_data = {"uid": uid}
                
            current_branch = self.vcs.get_current_branch()
            
            # Get the project root
            project_root = Path.cwd()
            
            # First attempt a non-forced upload
            force = False
            
            # Show a loading message
            self.status_bar.showMessage(f"Uploading branch '{current_branch}' to server...")
            
            # Perform the upload with the auth_data we already have
            success = upload_data(project_root, current_branch, auth_data, force)
            
            # If the upload failed due to no new commits, offer to force upload
            if not success:
                # Check if there are any commits at all - if not, don't offer force
                flvcs_dir = project_root / '.flvcs'
                commit_log_path = flvcs_dir / 'commit_log.json'
                metadata_path = flvcs_dir / 'metadata.json'
                
                if not commit_log_path.exists() or not metadata_path.exists():
                    QMessageBox.warning(self, "Upload Failed", 
                                      "No commits found for this branch. Cannot upload.")
                    self.status_bar.showMessage(f"Upload failed - no commits")
                    return
                    
                # Load the metadata to check if the branch has commits
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    branch_history = metadata.get('branch_history', {})
                    branch_commits = branch_history.get(current_branch, [])
                    
                if not branch_commits:
                    QMessageBox.warning(self, "Upload Failed", 
                                      "No commits found for this branch. Cannot upload.")
                    self.status_bar.showMessage(f"Upload failed - no commits")
                    return
                    
                # We have commits but they haven't changed - ask to force upload
                result = QMessageBox.question(
                    self, "No New Commits", 
                    "No new commits since last upload. Do you want to force upload anyway?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if result == QMessageBox.Yes:
                    force = True
                    self.status_bar.showMessage(f"Force uploading branch '{current_branch}' to server...")
                    success = upload_data(project_root, current_branch, auth_data, force)
                else:
                    self.status_bar.showMessage(f"Upload cancelled")
                    return
            
            if success:
                QMessageBox.information(self, "Upload Successful", 
                                        f"Successfully uploaded branch '{current_branch}' to server.")
                self.status_bar.showMessage(f"Upload successful")
            else:
                QMessageBox.warning(self, "Upload Failed", 
                                  f"Failed to upload branch '{current_branch}' to server.")
                self.status_bar.showMessage(f"Upload failed")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error uploading branch: {str(e)}")
            self.status_bar.showMessage("Upload error")
    
    def download_branch(self):
        """Download branch from server"""
        if not self.vcs:
            QMessageBox.warning(self, "No Project", "No project loaded.")
            return
            
        try:
            # Check if user is already authenticated
            auth_data = load_user_auth()
            
            if auth_data is None or "uid" not in auth_data:
                # Import webbrowser here to avoid importing at module level
                import webbrowser
                from flvcs.data_utils import API_ENDPOINTS, save_user_auth
                
                # Open the login page in browser
                webbrowser.open(API_ENDPOINTS['login'])
                
                # Show dialog to get UID
                auth_dialog = AuthDialog(self)
                if auth_dialog.exec_() != QDialog.Accepted:
                    return  # User cancelled
                    
                uid = auth_dialog.uid_field.text().strip()
                if not uid:
                    QMessageBox.warning(self, "Authentication Failed", "No UID provided.")
                    return
                    
                # Save the UID
                save_user_auth(uid)
                auth_data = {"uid": uid}
                
            current_branch = self.vcs.get_current_branch()
            branches = self.vcs.list_branches()
            
            # Let the user choose which branch to download
            branch_name, ok = QInputDialog.getItem(
                self, "Select Branch", 
                "Select which branch to download:", 
                branches, 
                branches.index(current_branch) if current_branch in branches else 0,
                False
            )
            
            if not ok or not branch_name:
                return
                
            # Get the project root
            project_root = Path.cwd()
            
            # Show a loading message
            self.status_bar.showMessage(f"Downloading branch '{branch_name}' from server...")
            
            # Perform the download with the auth_data we already have
            success = download_data(project_root, branch_name, auth_data)
            
            if success:
                QMessageBox.information(self, "Download Successful", 
                                        f"Successfully downloaded branch '{branch_name}' from server.")
                
                # If the downloaded branch is the current branch, update the project file
                if branch_name == current_branch:
                    # Get the latest commit for this branch to checkout
                    commits = self.vcs.list_commits()
                    if commits:
                        latest_commit = commits[0]['hash']
                        self.vcs.checkout(latest_commit)
                
                # Refresh the UI to reflect changes
                self.refresh_ui()
                self.status_bar.showMessage(f"Download successful")
            else:
                QMessageBox.warning(self, "Download Failed", 
                                    f"Failed to download branch '{branch_name}' from server.")
                self.status_bar.showMessage(f"Download failed")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error downloading branch: {str(e)}")
            self.status_bar.showMessage("Download error")

    def delete_credentials(self):
        """Delete stored authentication credentials"""
        try:
            result = QMessageBox.question(
                self, "Delete Credentials", 
                "Are you sure you want to delete your authentication credentials?\n\n"
                "You will need to re-authenticate on your next upload or download.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No  # Default is No to prevent accidental deletion
            )
            
            if result != QMessageBox.Yes:
                return
                
            if delete_user_auth():
                QMessageBox.information(self, "Success", "Authentication credentials deleted successfully.")
                self.status_bar.showMessage("Authentication credentials deleted")
            else:
                QMessageBox.information(self, "No Credentials", "No authentication credentials were found.")
                self.status_bar.showMessage("No authentication credentials found")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error deleting credentials: {str(e)}")
            self.status_bar.showMessage("Error deleting credentials")

    def reset_upload_tracking(self):
        """Reset upload tracking for the current branch or all branches"""
        if not self.vcs:
            QMessageBox.warning(self, "No Project", "No project loaded.")
            return
        
        try:
            current_branch = self.vcs.get_current_branch()
            branches = self.vcs.list_branches()
            
            # Let the user choose which branch to reset or all branches
            options = branches + ["All Branches"]
            branch_name, ok = QInputDialog.getItem(
                self, "Reset Upload Tracking", 
                "Select which branch tracking to reset:", 
                options, 
                branches.index(current_branch) if current_branch in branches else 0,
                False
            )
            
            if not ok or not branch_name:
                return
            
            # Get the project root
            project_root = Path.cwd()
            
            if branch_name == "All Branches":
                branch_param = None
                message = "Are you sure you want to reset upload tracking for all branches?\n\n" \
                         "This will allow re-uploading all branches even without new commits."
            else:
                branch_param = branch_name
                message = f"Are you sure you want to reset upload tracking for branch '{branch_name}'?\n\n" \
                          f"This will allow re-uploading this branch even without new commits."
            
            # Confirm action
            result = QMessageBox.question(
                self, "Confirm Reset", 
                message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if result != QMessageBox.Yes:
                return
            
            success = reset_upload_tracking(project_root, branch_param)
            
            if success:
                if branch_param:
                    QMessageBox.information(self, "Success", 
                                          f"Successfully reset upload tracking for branch '{branch_param}'.\n\n"
                                          f"You can now upload this branch again.")
                else:
                    QMessageBox.information(self, "Success", 
                                          "Successfully reset upload tracking for all branches.\n\n"
                                          "You can now upload any branch again.")
                self.status_bar.showMessage("Upload tracking reset successful")
            else:
                QMessageBox.warning(self, "Failed", "Failed to reset upload tracking.")
                self.status_bar.showMessage("Upload tracking reset failed")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error resetting upload tracking: {str(e)}")
            self.status_bar.showMessage("Error resetting upload tracking")


def run_gui():
    app = QApplication(sys.argv)
    window = FLVCSMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    run_gui() 