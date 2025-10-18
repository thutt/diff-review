#!/usr/bin/env python3
# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Tab manager for diff_review

This module contains the tab widget that manages multiple DiffViewer instances.
"""
import sys
from PyQt6.QtWidgets import QApplication, QTabWidget, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction


class DiffViewerTabWidget(QMainWindow):
    """Main window containing tabs of DiffViewer instances"""
    
    def __init__(self):
        if QApplication.instance() is None:
            self._app = QApplication(sys.argv)
        else:
            self._app = QApplication.instance()
        
        super().__init__()
        
        self.setWindowTitle("Diff Viewer")
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
        # Set as central widget
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tab_widget)
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
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        help_action = QAction("How to Use", self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        # Default window size
        self.resize(1400, 900)
    
    def add_viewer(self, diff_viewer, tab_title=None):
        """
        Add a fully configured DiffViewer to a new tab.
        
        Args:
            diff_viewer: A DiffViewer instance that has been configured
            tab_title: Optional title for the tab. If not provided, uses the 
                      diff_viewer's base and modified filenames
        
        Returns:
            The index of the newly added tab
        """
        if tab_title is None:
            # Extract base filename from path
            base_name = diff_viewer.base_file.split('/')[-1]
            modified_name = diff_viewer.modified_file.split('/')[-1]
            tab_title = f"{base_name} vs {modified_name}"
        
        # Add the viewer's central widget to the tab
        # We need to extract the central widget from the diff_viewer
        viewer_widget = diff_viewer.centralWidget()
        
        index = self.tab_widget.addTab(viewer_widget, tab_title)
        
        # Store reference to the diff_viewer on the widget
        viewer_widget.diff_viewer = diff_viewer
        
        return index
    
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
        self.tab_widget.removeTab(index)
    
    def close_current_tab(self):
        """Close the currently active tab"""
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            self.close_tab(current_index)
    
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
