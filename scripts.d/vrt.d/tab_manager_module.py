#!/usr/bin/env python3
"""
Tab manager for diff_review

This module contains the tab widget that manages multiple DiffViewer instances
with a sidebar for file selection.
"""
import sys
from PyQt6.QtWidgets import (QApplication, QTabWidget, QMainWindow, QHBoxLayout, 
                              QVBoxLayout, QWidget, QPushButton, QScrollArea, QSplitter,
                              QPlainTextEdit, QMenu, QMessageBox, QProgressDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont

from help_dialog import HelpDialog
from search_dialogs import SearchDialog, SearchResultDialog
from commit_msg_dialog import CommitMsgDialog


class FileButton(QPushButton):
    """Custom button for file selection in sidebar"""
    
    def __init__(self, file_class, parent=None):
        super().__init__(parent)
        self.file_class = file_class
        self.is_active = False
        self.setText(file_class.button_label())
        self.setCheckable(False)
        self.setStyleSheet(self._get_stylesheet())
    
    def set_active(self, active):
        """Set whether this button represents the active tab"""
        self.is_active = active
        self.setStyleSheet(self._get_stylesheet())
    
    def _get_stylesheet(self):
        """Generate stylesheet based on active state"""
        if self.is_active:
            return """
                QPushButton {
                    text-align: left;
                    padding: 8px 8px 8px 20px;
                    border: none;
                    background-color: #f0f0f0;
                    border-left: 4px solid #0066cc;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """
        else:
            return """
                QPushButton {
                    text-align: left;
                    padding: 8px 8px 8px 20px;
                    border: none;
                    background-color: white;
                    border-left: 4px solid transparent;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                }
            """


class DiffViewerTabWidget(QMainWindow):
    """Main window containing tabs of DiffViewer instances with file sidebar"""
    
    def __init__(self):
        if QApplication.instance() is None:
            self._app = QApplication(sys.argv)
        else:
            self._app = QApplication.instance()
        
        super().__init__()
        
        self.setWindowTitle("Diff Viewer")
        
        # Storage for file classes and their buttons
        self.file_classes = []
        self.file_buttons = []
        self.file_to_tab_index = {}  # Maps file_class to tab index
        self.current_file_class = None  # Track which file is being added
        self.sidebar_visible = True
        self._commit_msg_file = None  # Track commit message file (internal)
        self.commit_msg_button = None  # Track commit message button
        self.commit_msg_dialog = None  # Track commit message dialog
        
        # Create main layout
        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter for resizable sidebar
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create sidebar
        self.sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Scroll area for buttons
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.button_container = QWidget()
        self.button_layout = QVBoxLayout(self.button_container)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(0)
        
        # Add "Open All" button at the top
        self.open_all_button = QPushButton("Open All Files")
        self.open_all_button.clicked.connect(self.open_all_files)
        self.open_all_button.setStyleSheet("""
            QPushButton {
                text-align: center;
                padding: 10px;
                border: none;
                background-color: #e8f4f8;
                font-weight: bold;
                color: #0066cc;
            }
            QPushButton:hover {
                background-color: #d0e8f0;
            }
        """)
        self.button_layout.addWidget(self.open_all_button)
        
        self.button_layout.addStretch()
        
        scroll_area.setWidget(self.button_container)
        sidebar_layout.addWidget(scroll_area)
        
        # Add sidebar and tab widget to splitter
        self.splitter.addWidget(self.sidebar_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        self.splitter.addWidget(self.tab_widget)
        
        # Set initial splitter sizes (sidebar: 250px, main area: rest)
        self.splitter.setSizes([250, 1350])
        
        main_layout.addWidget(self.splitter)
        
        self.setCentralWidget(central)
        
        # Create menu bar
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        close_tab_action = QAction("Close Tab", self)
        close_tab_action.setShortcut("Ctrl+W")
        close_tab_action.triggered.connect(self.close_current_tab)
        file_menu.addAction(close_tab_action)
        
        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        toggle_sidebar_action = QAction("Toggle Sidebar", self)
        toggle_sidebar_action.setShortcut("Ctrl+B")
        toggle_sidebar_action.triggered.connect(self.toggle_sidebar)
        view_menu.addAction(toggle_sidebar_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        help_action = QAction("How to Use", self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        # Default window size
        # Measured: 1672px shows 73 chars per pane (146 total) with sidebar closed
        # Target: 80 chars per pane (160 total)
        # Scale: 1672 * (160/146) = ~1832px
        total_width = int(1672 * (160.0 / 146.0))
        
        self.resize(total_width, 900)
    
    def add_commit_msg(self, commit_msg_file):
        """
        Add commit message to the sidebar as the first item.
        
        Args:
            commit_msg_file: Path to the commit message file
        """
        # Check if file exists
        try:
            with open(commit_msg_file, 'r') as f:
                f.read()
        except Exception:
            return  # File doesn't exist or can't be read, don't add
        
        self._commit_msg_file = commit_msg_file
        
        # Create a special button for commit message
        self.commit_msg_button = QPushButton("📝 Commit Message")
        self.commit_msg_button.clicked.connect(self.on_commit_msg_clicked)
        self.commit_msg_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 8px 8px 20px;
                border: none;
                background-color: #fff4e6;
                border-left: 4px solid #ff9800;
                font-weight: bold;
                color: #e65100;
            }
            QPushButton:hover {
                background-color: #ffe0b2;
            }
        """)
        
        # Insert after "Open All" button (position 1)
        self.button_layout.insertWidget(1, self.commit_msg_button)
    
    def on_commit_msg_clicked(self):
        """Handle commit message button click"""
        # Check if tab already exists
        if 'commit_msg' in self.file_to_tab_index:
            tab_index = self.file_to_tab_index['commit_msg']
            if 0 <= tab_index < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(tab_index)
                return
            # Tab was closed, remove from mapping
            del self.file_to_tab_index['commit_msg']
        
        # Create new commit message tab
        self.create_commit_msg_tab()
    
    def create_commit_msg_tab(self):
        """Create a tab displaying the commit message"""
        try:
            with open(self._commit_msg_file, 'r') as f:
                commit_msg_text = f.read()
        except Exception as e:
            QMessageBox.warning(self, 'Error Reading Commit Message',
                              f'Could not read commit message file:\n{e}')
            return
        
        # Create text widget
        text_widget = QPlainTextEdit()
        text_widget.setReadOnly(True)
        text_widget.setPlainText(commit_msg_text)
        text_widget.setFont(QFont("Courier", 12, QFont.Weight.Bold))
        
        # Set up context menu
        text_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        text_widget.customContextMenuRequested.connect(
            lambda pos: self.show_commit_msg_context_menu(pos, text_widget))
        
        # Install event filter for keyboard shortcuts
        text_widget.installEventFilter(self)
        
        # Store reference to tab widget for later use
        text_widget.is_commit_msg = True
        
        # Add to tabs
        index = self.tab_widget.addTab(text_widget, "Commit Message")
        self.file_to_tab_index['commit_msg'] = index
        self.tab_widget.setCurrentIndex(index)
        
        # Update button state
        self.update_button_states()
    
    def show_search_dialog(self):
        """Show search dialog for current tab"""
        viewer = self.get_current_viewer()
        current_widget = self.tab_widget.currentWidget()
        
        # Determine if we have a commit message
        has_commit_msg = False
        if viewer and viewer.commit_msg_file:
            has_commit_msg = True
        elif hasattr(current_widget, 'is_commit_msg') and current_widget.is_commit_msg:
            has_commit_msg = True
        
        dialog = SearchDialog(self, has_commit_msg=has_commit_msg)
        if dialog.exec() == dialog.DialogCode.Accepted and dialog.search_text:
            # Pass self (tab widget) as parent so search results can navigate properly
            results_dialog = SearchResultDialog(
                search_text=dialog.search_text,
                parent=self,
                case_sensitive=dialog.case_sensitive,
                search_base=dialog.search_base,
                search_modi=dialog.search_modi,
                search_commit_msg=dialog.search_commit_msg,
                search_all_tabs=dialog.search_all_tabs,
                use_regex=dialog.use_regex
            )
            results_dialog.exec()
    
    def search_selected_text(self, text_widget):
        """Search for selected text from any text widget"""
        cursor = text_widget.textCursor()
        if not cursor.hasSelection():
            return
        
        search_text = cursor.selectedText()
        
        # Default to searching all tabs if multiple tabs are open
        search_all_tabs = self.tab_widget.count() > 1
        
        dialog = SearchResultDialog(search_text, self, case_sensitive=False,
                                   search_base=True, search_modi=True,
                                   search_commit_msg=True,
                                   search_all_tabs=search_all_tabs)
        dialog.exec()
    
    def show_commit_msg_context_menu(self, pos, text_widget):
        """Show context menu for commit message"""
        menu = QMenu(self)
        cursor = text_widget.textCursor()
        has_selection = cursor.hasSelection()
        
        search_action = QAction("Search", self)
        search_action.setEnabled(has_selection)
        if has_selection:
            search_action.triggered.connect(lambda: self.search_selected_text(text_widget))
        menu.addAction(search_action)
        
        menu.addSeparator()
        
        # Note taking - need to check if any viewer has a note file
        note_file = self.get_note_file()
        if has_selection and note_file:
            note_action = QAction("Take Note", self)
            note_action.triggered.connect(
                lambda: self.take_commit_msg_note(text_widget, note_file))
            menu.addAction(note_action)
        else:
            note_action = QAction("Take Note (no selection)" if note_file else 
                               "Take Note (no file supplied)", self)
            note_action.setEnabled(False)
            menu.addAction(note_action)
        
        menu.exec(text_widget.mapToGlobal(pos))
    
    def take_commit_msg_note(self, text_widget, note_file):
        """Take note from commit message"""
        cursor = text_widget.textCursor()
        if not cursor.hasSelection():
            return
        
        selected_text = cursor.selectedText()
        selected_text = selected_text.replace('\u2029', '\n')
        
        try:
            with open(note_file, 'a') as f:
                f.write("(commit_msg): Commit Message\n")
                for line in selected_text.split('\n'):
                    f.write(f"  {line}\n")
                f.write('\n')
            
            # Update note count in current viewer if it exists
            viewer = self.get_current_viewer()
            if viewer:
                viewer.note_count += 1
                viewer.update_status()
        except Exception as e:
            QMessageBox.warning(self, 'Error Taking Note',
                              f'Could not write to note file:\n{e}')
    
    def get_note_file(self):
        """Get note file from any viewer"""
        viewers = self.get_all_viewers()
        for viewer in viewers:
            if viewer.note_file:
                return viewer.note_file
        return None
    
    def add_file(self, file_class):
        """
        Add a file to the sidebar.
        
        Args:
            file_class: An object with button_label() and add_viewer(tab_widget) methods
        """
        self.file_classes.append(file_class)
        
        # Create button
        button = FileButton(file_class, self)
        button.clicked.connect(lambda: self.on_file_clicked(file_class))
        
        # Calculate insert position: after "Open All" and commit message (if present)
        insert_position = 1  # After "Open All"
        if self.commit_msg_button:
            insert_position = 2  # After "Open All" and "Commit Message"
        insert_position += len(self.file_buttons)  # After existing file buttons
        
        self.button_layout.insertWidget(insert_position, button)
        self.file_buttons.append(button)
    
    def open_all_files(self):
        """Open all files in tabs"""
        if not self.file_classes:
            return
        
        # Create progress dialog
        progress = QProgressDialog("Loading files...", "Cancel", 0, len(self.file_classes), self)
        progress.setWindowTitle("Opening Files")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(500)  # Only show if takes more than 500ms
        
        for i, file_class in enumerate(self.file_classes):
            if progress.wasCanceled():
                break
            
            # Update progress
            progress.setValue(i)
            progress.setLabelText(f"Loading {file_class.button_label()}...")
            QApplication.processEvents()  # Keep UI responsive
            
            self.on_file_clicked(file_class)
        
        progress.setValue(len(self.file_classes))
        progress.close()
    
    def on_file_clicked(self, file_class):
        """Handle file button click"""
        # Check if tab already exists for this file
        if file_class in self.file_to_tab_index:
            tab_index = self.file_to_tab_index[file_class]
            # Verify tab still exists (might have been closed)
            if 0 <= tab_index < self.tab_widget.count():
                widget = self.tab_widget.widget(tab_index)
                if hasattr(widget, 'file_class') and widget.file_class == file_class:
                    # Tab exists, switch to it
                    self.tab_widget.setCurrentIndex(tab_index)
                    return
            # Tab was closed, remove from mapping
            del self.file_to_tab_index[file_class]
        
        # No existing tab, create new one
        self.current_file_class = file_class  # Store for add_viewer to use
        file_class.add_viewer(self)
        self.current_file_class = None  # Clear after use
    
    def add_viewer(self, diff_viewer, tab_title=None):
        """
        Add a fully configured DiffViewer to a new tab.
        
        Args:
            diff_viewer: A DiffViewer instance that has been configured
            tab_title: Optional title for the tab. If not provided, uses the 
                      button_label() from the file_class
        
        Returns:
            The index of the newly added tab
        """
        # Use the file_class that was stored when button was clicked
        file_class = self.current_file_class
        
        if tab_title is None and file_class:
            # Use the button label as the tab title
            tab_title = file_class.button_label()
        elif tab_title is None:
            # Fallback if no file_class
            base_name = diff_viewer.base_file.split('/')[-1]
            modified_name = diff_viewer.modified_file.split('/')[-1]
            tab_title = f"{base_name} vs {modified_name}"
        
        # Add the viewer's central widget to the tab
        viewer_widget = diff_viewer.centralWidget()
        
        index = self.tab_widget.addTab(viewer_widget, tab_title)
        
        # Store references
        viewer_widget.diff_viewer = diff_viewer
        viewer_widget.file_class = file_class
        
        # Install event filter on text widgets to handle Tab key
        diff_viewer.base_text.installEventFilter(self)
        diff_viewer.modified_text.installEventFilter(self)
        
        # Set up context menus for text widgets
        diff_viewer.base_text.customContextMenuRequested.connect(
            lambda pos: self.show_diff_context_menu(pos, diff_viewer.base_text, 'base'))
        diff_viewer.modified_text.customContextMenuRequested.connect(
            lambda pos: self.show_diff_context_menu(pos, diff_viewer.modified_text, 'modified'))
        
        # Track file to tab mapping
        if file_class:
            self.file_to_tab_index[file_class] = index
        
        # Switch to new tab
        self.tab_widget.setCurrentIndex(index)
        
        # Update button states immediately
        self.update_button_states()
        
        return index
    
    def show_diff_context_menu(self, pos, text_widget, side):
        """Show context menu for diff viewer text widgets"""
        menu = QMenu(self)
        viewer = self.get_current_viewer()
        
        if not viewer:
            return
        
        has_selection = text_widget.textCursor().hasSelection()
        
        search_action = QAction("Search", self)
        search_action.setEnabled(has_selection)
        search_action.triggered.connect(lambda: self.search_selected_text(text_widget))
        menu.addAction(search_action)
        
        menu.addSeparator()
        
        if has_selection and viewer.note_file:
            note_action = QAction("Take Note", self)
            note_action.triggered.connect(lambda: viewer.take_note(side))
            menu.addAction(note_action)
        else:
            note_action = QAction("Take Note (no selection)" if viewer.note_file else 
                           "Take Note (no file supplied)", self)
            note_action.setEnabled(False)
            menu.addAction(note_action)
        
        menu.exec(text_widget.mapToGlobal(pos))
    
    def select_search_result(self, side, line_idx):
        """Navigate to a search result in the current viewer"""
        viewer = self.get_current_viewer()
        if viewer:
            viewer.center_on_line(line_idx)
            if side == 'base':
                viewer.base_text.setFocus()
            else:
                viewer.modified_text.setFocus()
    
    def select_commit_msg_result(self, line_idx):
        """Navigate to a line in the commit message dialog"""
        # Check if viewer has commit message, show it
        viewer = self.get_current_viewer()
        if viewer and viewer.commit_msg_file:
            self.show_commit_msg_dialog(viewer.commit_msg_file, viewer)
        
        # Navigate to the line
        if self.commit_msg_dialog and self.commit_msg_dialog.isVisible():
            self.commit_msg_dialog.select_line(line_idx)
    
    def show_commit_msg_dialog(self, commit_msg_file, viewer):
        """Show the commit message dialog for a viewer"""
        # Check if dialog already exists and is visible
        if self.commit_msg_dialog and self.commit_msg_dialog.isVisible():
            self.commit_msg_dialog.raise_()
            self.commit_msg_dialog.activateWindow()
            return
        
        # Create new dialog
        self.commit_msg_dialog = CommitMsgDialog(commit_msg_file, viewer, self)
        self.commit_msg_dialog.show()
    
    # Methods to support SearchResultDialog (which expects a viewer-like interface)
    @property
    def base_display(self):
        """Get base_display from current viewer"""
        viewer = self.get_current_viewer()
        return viewer.base_display if viewer else []
    
    @property
    def modified_display(self):
        """Get modified_display from current viewer"""
        viewer = self.get_current_viewer()
        return viewer.modified_display if viewer else []
    
    @property
    def base_line_nums(self):
        """Get base_line_nums from current viewer"""
        viewer = self.get_current_viewer()
        return viewer.base_line_nums if viewer else []
    
    @property
    def modified_line_nums(self):
        """Get modified_line_nums from current viewer"""
        viewer = self.get_current_viewer()
        return viewer.modified_line_nums if viewer else []
    
    @property
    def commit_msg_file(self):
        """Get commit_msg_file from current viewer"""
        viewer = self.get_current_viewer()
        return viewer.commit_msg_file if viewer else None
    
    def get_commit_msg_lines(self):
        """Get commit message lines from current viewer"""
        viewer = self.get_current_viewer()
        return viewer.get_commit_msg_lines() if viewer else []
    
    def on_tab_changed(self, index):
        """Handle tab change to update sidebar button states"""
        self.update_button_states()
        
        # Update scrollbars in the newly activated viewer
        viewer = self.get_viewer_at_index(index)
        if viewer:
            viewer.init_scrollbars()
    
    def update_button_states(self):
        """Update all button states based on open tabs"""
        # Update file buttons
        for button in self.file_buttons:
            file_class = button.file_class
            has_open_tab = file_class in self.file_to_tab_index
            if has_open_tab:
                tab_index = self.file_to_tab_index[file_class]
                if not (0 <= tab_index < self.tab_widget.count()):
                    has_open_tab = False
            button.set_active(has_open_tab)
        
        # Update commit message button
        if self.commit_msg_button:
            has_commit_msg_tab = 'commit_msg' in self.file_to_tab_index
            if has_commit_msg_tab:
                tab_index = self.file_to_tab_index['commit_msg']
                if not (0 <= tab_index < self.tab_widget.count()):
                    has_commit_msg_tab = False
            
            if has_commit_msg_tab:
                self.commit_msg_button.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding: 8px 8px 8px 20px;
                        border: none;
                        background-color: #ffe0b2;
                        border-left: 4px solid #ff9800;
                        font-weight: bold;
                        color: #e65100;
                    }
                    QPushButton:hover {
                        background-color: #ffcc80;
                    }
                """)
            else:
                self.commit_msg_button.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding: 8px 8px 8px 20px;
                        border: none;
                        background-color: #fff4e6;
                        border-left: 4px solid #ff9800;
                        font-weight: bold;
                        color: #e65100;
                    }
                    QPushButton:hover {
                        background-color: #ffe0b2;
                    }
                """)
    
    def get_all_viewers(self):
        """
        Get all DiffViewer instances across all tabs.
        
        Returns:
            List of DiffViewer instances
        """
        viewers = []
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if hasattr(widget, 'diff_viewer'):
                viewers.append(widget.diff_viewer)
        return viewers
    
    def get_current_viewer(self):
        """
        Get the currently active DiffViewer instance.
        
        Returns:
            The DiffViewer instance in the current tab, or None if no tabs
        """
        current_widget = self.tab_widget.currentWidget()
        if current_widget and hasattr(current_widget, 'diff_viewer'):
            return current_widget.diff_viewer
        return None
    
    def get_viewer_at_index(self, index):
        """
        Get the DiffViewer instance at a specific tab index.
        
        Args:
            index: Tab index
            
        Returns:
            The DiffViewer instance at that index, or None if invalid index
        """
        if 0 <= index < self.tab_widget.count():
            widget = self.tab_widget.widget(index)
            if hasattr(widget, 'diff_viewer'):
                return widget.diff_viewer
        return None
    
    def close_tab(self, index):
        """Close the tab at the given index"""
        if index >= 0 and index < self.tab_widget.count():
            widget = self.tab_widget.widget(index)
            
            # Check if this is the commit message tab
            if hasattr(widget, 'is_commit_msg') and widget.is_commit_msg:
                if 'commit_msg' in self.file_to_tab_index:
                    del self.file_to_tab_index['commit_msg']
            # Regular file tab
            elif hasattr(widget, 'file_class'):
                file_class = widget.file_class
                if file_class in self.file_to_tab_index:
                    del self.file_to_tab_index[file_class]
            
            # Update indices in mapping for tabs after this one
            for key, tab_idx in list(self.file_to_tab_index.items()):
                if tab_idx > index:
                    self.file_to_tab_index[key] = tab_idx - 1
            
            self.tab_widget.removeTab(index)
            
            # Update button states after closing
            self.update_button_states()
            
            # If no tabs remain, ensure sidebar is visible
            if self.tab_widget.count() == 0 and not self.sidebar_visible:
                self.toggle_sidebar()
    
    def close_current_tab(self):
        """Close the currently active tab"""
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            self.close_tab(current_index)
    
    def toggle_sidebar(self):
        """Toggle sidebar visibility"""
        if self.sidebar_visible:
            self.sidebar_widget.hide()
            self.sidebar_visible = False
        else:
            self.sidebar_widget.show()
            self.sidebar_visible = True
        
        # Update scrollbars in current viewer after sidebar toggle
        current_viewer = self.get_current_viewer()
        if current_viewer:
            # Trigger scrollbar recalculation
            current_viewer.init_scrollbars()
    
    def show_help(self):
        """Show help dialog"""
        help_dialog = HelpDialog(self)
        help_dialog.exec()
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        key = event.key()
        modifiers = event.modifiers()
        
        # Get current viewer for most commands
        viewer = self.get_current_viewer()
        
        # Escape closes the entire application
        if key == Qt.Key.Key_Escape:
            self.close()
            return
        
        # All other shortcuts require an active viewer
        if not viewer:
            super().keyPressEvent(event)
            return
        
        # Alt+H - Toggle diff map
        if key == Qt.Key.Key_H and modifiers & Qt.KeyboardModifier.AltModifier:
            viewer.toggle_diff_map()
            return
        
        # Alt+L - Toggle line numbers
        if key == Qt.Key.Key_L and modifiers & Qt.KeyboardModifier.AltModifier:
            viewer.toggle_line_numbers()
            return
        
        # Ctrl+S - Search
        if key == Qt.Key.Key_S and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.show_search_dialog()
            return
        
        # Ctrl+N - Take note
        if key == Qt.Key.Key_N and modifiers & Qt.KeyboardModifier.ControlModifier:
            # Determine which side has focus
            if viewer.base_text.hasFocus():
                viewer.take_note_from_widget('base')
            elif viewer.modified_text.hasFocus():
                viewer.take_note_from_widget('modified')
            return
        
        # N - Next change
        if key == Qt.Key.Key_N:
            viewer.next_change()
            return
        
        # P - Previous change
        if key == Qt.Key.Key_P:
            viewer.prev_change()
            return
        
        # C - Center on current region
        if key == Qt.Key.Key_C:
            viewer.center_current_region()
            return
        
        # T - Top of file
        if key == Qt.Key.Key_T:
            viewer.current_region = 0
            if viewer.change_regions:
                viewer.center_on_line(0)
            viewer.update_status()
            return
        
        # B - Bottom of file
        if key == Qt.Key.Key_B:
            if viewer.change_regions:
                viewer.current_region = len(viewer.change_regions) - 1
                viewer.center_on_line(len(viewer.base_display) - 1)
            viewer.update_status()
            return
        
        # Pass other events to parent
        super().keyPressEvent(event)
    
    def eventFilter(self, obj, event):
        """Filter events from text widgets to handle Tab key and Ctrl+N"""
        if event.type() == event.Type.KeyPress:
            viewer = self.get_current_viewer()
            key = event.key()
            modifiers = event.modifiers()
            
            # Check if this is the commit message widget
            is_commit_msg = hasattr(obj, 'is_commit_msg') and obj.is_commit_msg
            
            # Ctrl+S - Search (works for both commit message and diff viewers)
            if key == Qt.Key.Key_S and modifiers & Qt.KeyboardModifier.ControlModifier:
                self.show_search_dialog()
                return True
            
            # Ctrl+N - Take note (works for both)
            if key == Qt.Key.Key_N and modifiers & Qt.KeyboardModifier.ControlModifier:
                if is_commit_msg:
                    note_file = self.get_note_file()
                    if note_file:
                        self.take_commit_msg_note(obj, note_file)
                    return True
                elif viewer:
                    if obj == viewer.base_text:
                        viewer.take_note_from_widget('base')
                        return True
                    elif obj == viewer.modified_text:
                        viewer.take_note_from_widget('modified')
                        return True
            
            # Tab - Switch focus between base and modified (only for diff viewers)
            if not is_commit_msg and viewer and key == Qt.Key.Key_Tab and not modifiers:
                if obj == viewer.base_text:
                    # Get current line in base
                    cursor = viewer.base_text.textCursor()
                    current_line = cursor.blockNumber()
                    
                    # Move cursor in modified BEFORE switching focus
                    new_cursor = viewer.modified_text.textCursor()
                    new_cursor.movePosition(new_cursor.MoveOperation.Start)
                    for _ in range(current_line):
                        new_cursor.movePosition(new_cursor.MoveOperation.Down)
                    viewer.modified_text.setTextCursor(new_cursor)
                    
                    # Now switch focus
                    viewer.modified_text.setFocus()
                    viewer.modified_text.ensureCursorVisible()
                    return True
                    
                elif obj == viewer.modified_text:
                    # Get current line in modified
                    cursor = viewer.modified_text.textCursor()
                    current_line = cursor.blockNumber()
                    
                    # Move cursor in base BEFORE switching focus
                    new_cursor = viewer.base_text.textCursor()
                    new_cursor.movePosition(new_cursor.MoveOperation.Start)
                    for _ in range(current_line):
                        new_cursor.movePosition(new_cursor.MoveOperation.Down)
                    viewer.base_text.setTextCursor(new_cursor)
                    
                    # Now switch focus
                    viewer.base_text.setFocus()
                    viewer.base_text.ensureCursorVisible()
                    return True
        return False
    
    def run(self):
        """Show the window and start the application event loop"""
        self.show()
        return sys.exit(self._app.exec())