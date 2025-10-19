#!/usr/bin/env python3
"""
Tab manager for diff_review

This module contains the tab widget that manages multiple DiffViewer instances
with a sidebar for file selection.
"""
import sys
from PyQt6.QtWidgets import (QApplication, QTabWidget, QMainWindow, QHBoxLayout, 
                              QVBoxLayout, QWidget, QPushButton, QScrollArea, QSplitter)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction


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
        
        # Insert before the stretch (after "Open All" button and existing file buttons)
        insert_position = len(self.file_buttons) + 1  # +1 for "Open All" button
        self.button_layout.insertWidget(insert_position, button)
        self.file_buttons.append(button)
    
    def open_all_files(self):
        """Open all files in tabs"""
        for file_class in self.file_classes:
            self.on_file_clicked(file_class)
    
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
        
        # Track file to tab mapping
        if file_class:
            self.file_to_tab_index[file_class] = index
        
        # Switch to new tab
        self.tab_widget.setCurrentIndex(index)
        
        # Update button states immediately
        self.update_button_states()
        
        return index
    
    def on_tab_changed(self, index):
        """Handle tab change to update sidebar button states"""
        self.update_button_states()
        
        # Update scrollbars in the newly activated viewer
        viewer = self.get_viewer_at_index(index)
        if viewer:
            viewer.init_scrollbars()
    
    def update_button_states(self):
        """Update all button states based on open tabs"""
        # Update all buttons based on whether their file has an open tab
        for button in self.file_buttons:
            file_class = button.file_class
            # Check if this file has an open tab
            has_open_tab = file_class in self.file_to_tab_index
            if has_open_tab:
                # Verify the tab still exists
                tab_index = self.file_to_tab_index[file_class]
                if not (0 <= tab_index < self.tab_widget.count()):
                    has_open_tab = False
            button.set_active(has_open_tab)
    
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
            
            # Remove from file_to_tab_index mapping
            if hasattr(widget, 'file_class'):
                file_class = widget.file_class
                if file_class in self.file_to_tab_index:
                    del self.file_to_tab_index[file_class]
            
            # Update indices in mapping for tabs after this one
            for file_class, tab_idx in list(self.file_to_tab_index.items()):
                if tab_idx > index:
                    self.file_to_tab_index[file_class] = tab_idx - 1
            
            self.tab_widget.removeTab(index)
            
            # Update button states after closing
            self.update_button_states()
    
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
        """Show help for the currently active viewer"""
        viewer = self.get_current_viewer()
        if viewer:
            viewer.show_help()
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        # Escape closes the entire application
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
    
    def run(self):
        """Show the window and start the application event loop"""
        self.show()
        return sys.exit(self._app.exec())
