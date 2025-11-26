# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
File watcher for diff_review

This module manages file system watching and auto-reload functionality:
- Watches source files for changes
- Debounces rapid file changes
- Triggers automatic reloads
- Visual indicators for changed files
"""
from PyQt6.QtCore import QFileSystemWatcher, QTimer
import color_palettes


class FileWatcherManager:
    """Manages file watching and auto-reload for diff viewers"""
    
    def __init__(self, tab_widget, auto_reload_enabled):
        """
        Initialize file watcher manager
        
        Args:
            tab_widget: Reference to DiffViewerTabWidget
            auto_reload_enabled: Initial auto-reload state
        """
        self.tab_widget = tab_widget
        self.auto_reload_enabled = auto_reload_enabled
        self.file_watchers = {}  # Maps viewer -> QFileSystemWatcher
        self.reload_timers = {}  # Maps viewer -> QTimer (for debouncing)
        self.changed_files = {}  # Maps viewer -> set of changed files
    
    def setup_file_watcher(self, viewer):
        """Set up file system watching for a viewer's files"""
        watcher = QFileSystemWatcher()
        
        # Watch base and modified files
        files_to_watch = []
        if viewer.base_file:
            files_to_watch.append(viewer.base_file)
        if viewer.modified_file:
            files_to_watch.append(viewer.modified_file)
        
        if files_to_watch:
            watcher.addPaths(files_to_watch)
            watcher.fileChanged.connect(lambda path: self.on_file_changed(viewer, path))
            self.file_watchers[viewer] = watcher
            self.changed_files[viewer] = set()
            
            # Create debounce timer
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self.process_file_changes(viewer))
            self.reload_timers[viewer] = timer
    
    def on_file_changed(self, viewer, path):
        """Handle file change notification"""
        # Add to changed files set
        if viewer not in self.changed_files:
            self.changed_files[viewer] = set()
        self.changed_files[viewer].add(path)
        
        # Mark tab as changed (visual indicator)
        self.mark_tab_changed(viewer, True)
        
        # Restart debounce timer
        if viewer in self.reload_timers:
            self.reload_timers[viewer].stop()
            self.reload_timers[viewer].start(500)  # 500ms debounce
    
    def process_file_changes(self, viewer):
        """Process accumulated file changes after debounce period"""
        if self.auto_reload_enabled and viewer in self.changed_files:
            self.tab_widget.reload_viewer(viewer)
    
    def mark_tab_changed(self, viewer, changed):
        """Mark a viewer as having changed files by updating sidebar button color"""
        # Find the file_class for this viewer
        # The viewer is a DiffViewer, we need to find its tab widget
        file_class = None
        for i in range(self.tab_widget.tab_widget.count()):
            widget = self.tab_widget.tab_widget.widget(i)
            if hasattr(widget, 'diff_viewer') and widget.diff_viewer == viewer:
                if hasattr(widget, 'file_class'):
                    file_class = widget.file_class
                break
        
        if not file_class:
            return
        
        # Find the corresponding button in the sidebar
        for button in self.tab_widget.file_buttons:
            if button.file_class == file_class:
                if changed:
                    # File has changed - use special "changed" styling
                    palette = color_palettes.get_current_palette()
                    color = palette.get_color('base_changed_bg')
                    
                    # Check if this is the currently active tab
                    tab_index = self.tab_widget.file_to_tab_index.get(file_class, -1)
                    is_active = (tab_index == self.tab_widget.tab_widget.currentIndex())
                    
                    if is_active:
                        # Changed AND active - bright changed color with thick border
                        button.setStyleSheet(f"""
                            QPushButton {{
                                text-align: left;
                                padding: 8px 8px 8px 20px;
                                border: none;
                                background-color: {color.name()};
                                border-left: 6px solid #ff6600;
                                font-weight: bold;
                            }}
                            QPushButton:hover {{
                                background-color: {color.darker(110).name()};
                            }}
                        """)
                    else:
                        # Changed but not active - changed color with normal border
                        button.setStyleSheet(f"""
                            QPushButton {{
                                text-align: left;
                                padding: 8px 8px 8px 20px;
                                border: none;
                                background-color: {color.name()};
                                border-left: 4px solid #ff6600;
                            }}
                            QPushButton:hover {{
                                background-color: {color.darker(110).name()};
                            }}
                        """)
                else:
                    # File no longer changed - restore normal state
                    # Determine if tab is open and active
                    tab_index = self.tab_widget.file_to_tab_index.get(file_class, -1)
                    is_open = (0 <= tab_index < self.tab_widget.tab_widget.count())
                    is_active = is_open and (tab_index == self.tab_widget.tab_widget.currentIndex())
                    button.set_state(is_open, is_active)
                break
    
    def cleanup_file_watcher(self, viewer):
        """Clean up file watcher for a viewer being closed"""
        if viewer in self.file_watchers:
            self.file_watchers[viewer].deleteLater()
            del self.file_watchers[viewer]
        if viewer in self.reload_timers:
            self.reload_timers[viewer].stop()
            del self.reload_timers[viewer]
        if viewer in self.changed_files:
            del self.changed_files[viewer]
    
    def toggle_auto_reload(self):
        """Toggle auto-reload preference"""
        self.auto_reload_enabled = not self.auto_reload_enabled
        
        # If turning on, immediately reload any files that have changed
        if self.auto_reload_enabled:
            for viewer in list(self.changed_files.keys()):
                if viewer in self.changed_files and self.changed_files[viewer]:
                    self.tab_widget.reload_viewer(viewer)
        
        return self.auto_reload_enabled
    
    def re_add_watched_files(self, viewer):
        """Re-add files to watcher (they may have been removed by some editors)"""
        if viewer in self.file_watchers:
            watcher = self.file_watchers[viewer]
            watched = watcher.files()
            
            files_to_watch = []
            if viewer.base_file and viewer.base_file not in watched:
                files_to_watch.append(viewer.base_file)
            if viewer.modified_file and viewer.modified_file not in watched:
                files_to_watch.append(viewer.modified_file)
            
            if files_to_watch:
                watcher.addPaths(files_to_watch)
    
    def clear_changed_files(self, viewer):
        """Clear changed files for a viewer after reload"""
        if viewer in self.changed_files:
            self.changed_files[viewer].clear()
