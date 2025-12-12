# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
File tree sidebar for diff_review

This module provides a tree view for organizing files by directory structure
in the sidebar, with collapsible directory nodes.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
                              QPushButton, QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
import color_palettes


class FileTreeSidebar(QWidget):
    """Tree view sidebar that organizes files by directory"""
    
    def __init__(self, tab_widget, parent=None):
        super().__init__(parent)
        self.tab_widget = tab_widget
        self.file_items = {}  # Maps file_class -> QTreeWidgetItem
        self.dir_items = {}   # Maps dir_path -> QTreeWidgetItem
        self.dir_open_counts = {}  # Maps dir_path -> count of open files
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # "Open All Files" button at top
        self.open_all_button = QPushButton("Open All Files")
        self.open_all_button.clicked.connect(self.tab_widget.open_all_files)
        self.open_all_button.setStyleSheet("""
            QPushButton {
                text-align: left;
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
        layout.addWidget(self.open_all_button)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setAnimated(True)
        self.tree.itemClicked.connect(self.on_item_clicked)
        
        # Set up context menu for right-click to focus tree
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.on_tree_right_click)
        
        # Install event filter to intercept spacebar
        self.tree.installEventFilter(self)
        
        layout.addWidget(self.tree)
        
        # Store special buttons (commit msg, review notes) as list items
        self.special_items = []  # List of (item_type, widget) tuples
    
    def add_commit_msg_button(self, button):
        """Add commit message button as tree item"""
        item = QTreeWidgetItem(self.tree)
        item.setText(0, "Commit Message")
        item.setData(0, Qt.ItemDataRole.UserRole, ('commit_msg', None))
        
        # Style as special item
        font = QFont()
        font.setBold(True)
        item.setFont(0, font)
        item.setForeground(0, Qt.GlobalColor.darkRed)
        
        self.special_items.append(('commit_msg', item))
        self.tree.insertTopLevelItem(0, item)
    
    def add_notes_button(self, button):
        """Add review notes button as tree item"""
        item = QTreeWidgetItem(self.tree)
        item.setText(0, "Review Notes")
        item.setData(0, Qt.ItemDataRole.UserRole, ('review_notes', None))
        
        # Style as special item
        font = QFont()
        font.setBold(True)
        item.setFont(0, font)
        item.setForeground(0, Qt.GlobalColor.blue)
        
        self.special_items.append(('review_notes', item))
        # Insert after commit msg if it exists
        insert_pos = 1 if any(t[0] == 'commit_msg' for t in self.special_items) else 0
        self.tree.insertTopLevelItem(insert_pos, item)
    
    def add_file(self, file_class):
        """
        Add a file to the tree, organized by full directory hierarchy
        
        Args:
            file_class: File class object with modi_rel_path_ attribute
        """
        file_path = file_class.modi_rel_path_
        
        # Split path into components
        parts = file_path.split('/')
        
        # If file is in root (no directory), add directly to tree
        if len(parts) == 1:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, parts[0])
            item.setData(0, Qt.ItemDataRole.UserRole, ('file', file_class))
            self.file_items[file_class] = item
            self.tree.addTopLevelItem(item)
            return
        
        # Build nested directory structure
        current_parent = self.tree  # Start at tree root
        dir_path_so_far = ""
        
        # Process all directory components (all but the last part which is the filename)
        for i, dir_name in enumerate(parts[:-1]):
            # Build cumulative path for this directory level
            if dir_path_so_far:
                dir_path_so_far = dir_path_so_far + '/' + dir_name
            else:
                dir_path_so_far = dir_name
            
            # Check if this directory node already exists
            if dir_path_so_far not in self.dir_items:
                # Create new directory node
                if current_parent == self.tree:
                    dir_item = QTreeWidgetItem(self.tree)
                    self.tree.addTopLevelItem(dir_item)
                else:
                    dir_item = QTreeWidgetItem(current_parent)
                
                dir_item.setText(0, dir_name)
                dir_item.setData(0, Qt.ItemDataRole.UserRole, ('directory', dir_path_so_far))
                
                # Style directory nodes
                font = QFont()
                font.setBold(True)
                dir_item.setFont(0, font)
                
                # Expand by default
                dir_item.setExpanded(True)
                
                self.dir_items[dir_path_so_far] = dir_item
                current_parent = dir_item
            else:
                # Use existing directory node
                current_parent = self.dir_items[dir_path_so_far]
        
        # Add file as child of the deepest directory
        filename = parts[-1]
        file_item = QTreeWidgetItem(current_parent)
        file_item.setText(0, filename)
        file_item.setData(0, Qt.ItemDataRole.UserRole, ('file', file_class))
        
        self.file_items[file_class] = file_item
    
    def begin_batch_update(self):
        """Begin a batch update - defer all directory indicator updates"""
        self._batch_mode = True
        self._pending_dir_updates.clear()
    
    def end_batch_update(self):
        """End batch update - process all deferred directory indicator updates"""
        self._batch_mode = False
        self._process_pending_directory_updates()
    
    def _update_directory_label(self, dir_item, dir_path):
        """Update directory label to show open file count"""
        count = self.dir_open_counts.get(dir_path, 0)
        
        # Extract just the directory name (last component of path)
        dir_name = dir_path.split('/')[-1]
        
        if count > 0:
            dir_item.setText(0, f"{dir_name} ({count})")
        else:
            dir_item.setText(0, dir_name)
    
    def on_tree_right_click(self, pos):
        """Handle right-click on tree - gives focus to tree for keyboard navigation"""
        self.tree.setFocus()
    
    def on_item_clicked(self, item, column):
        """Handle tree item click"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        item_type, item_data = data
        
        # Store current scroll position before handling the click
        # This prevents the uncontrolled scrolling issue on Mac when
        # an item is clicked that is mostly out of viewport
        scroll_bar = self.tree.verticalScrollBar()
        saved_scroll_pos = scroll_bar.value()
        
        if item_type == 'commit_msg':
            self.tab_widget.on_commit_msg_clicked()
            # Focus the text widget in the commit message tab
            self._focus_current_tab_widget()
        elif item_type == 'review_notes':
            self.tab_widget.note_mgr.on_notes_clicked()
            # Focus the text widget in the review notes tab
            self._focus_current_tab_widget()
        elif item_type == 'file':
            file_class = item_data
            self.tab_widget.on_file_clicked(file_class)
            # Focus the diff viewer
            self._focus_current_diff_viewer()
        elif item_type == 'directory':
            # Toggle expand/collapse on directory click
            item.setExpanded(not item.isExpanded())
        
        # Restore scroll position to prevent uncontrolled scrolling
        scroll_bar.setValue(saved_scroll_pos)
    
    def _focus_current_diff_viewer(self):
        """Set focus to the base text widget of the current diff viewer"""
        # Skip during bulk loading to avoid unnecessary slowness
        if self.tab_widget._bulk_loading:
            return
        
        viewer = self.tab_widget.get_current_viewer()
        if viewer:
            viewer.focus_content()
            # Update focus mode to content
            if self.tab_widget.focus_mode != 'content':
                self.tab_widget.focus_mode = 'content'
                self.tab_widget.update_focus_tinting()
                self.tab_widget.update_status_focus_indicator()

    def _focus_current_tab_widget(self):
        """Set focus to the current tab's main widget (commit msg or review notes)"""
        # Skip during bulk loading to avoid unnecessary slowness
        if self.tab_widget._bulk_loading:
            return
        
        current_widget = self.tab_widget.tab_widget.currentWidget()
        if current_widget:
            current_widget.focus_content()
            # Update focus mode to content
            if self.tab_widget.focus_mode != 'content':
                self.tab_widget.focus_mode = 'content'
                self.tab_widget.update_focus_tinting()
                self.tab_widget.update_status_focus_indicator()
    
    def eventFilter(self, obj, event):
        """Filter events from tree widget to handle spacebar and enter"""
        if obj == self.tree and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Space or event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                current_item = self.tree.currentItem()
                if current_item:
                    # Trigger the item as if it was clicked
                    self.on_item_clicked(current_item, 0)
                    return True  # Event handled
        
        # Let default handling proceed
        return super().eventFilter(obj, event)
    
    def update_file_state(self, file_class, is_open, is_active):
        """Update visual state of a file item"""
        if file_class not in self.file_items:
            return
        
        item = self.file_items[file_class]
        parent = item.parent()
        
        # Track previous open state to update directory counter (check color instead of prefix)
        current_color = item.foreground(0).color()
        was_open = current_color == Qt.GlobalColor.blue or current_color == QColor(0, 0, 255)
        
        # Update visual indicator - use color only, no prefix
        if is_active:
            # Currently selected - bold with blue color
            font = QFont()
            font.setBold(True)
            item.setFont(0, font)
            item.setForeground(0, Qt.GlobalColor.blue)
        elif is_open:
            # Open but not active - normal with blue color
            font = QFont()
            item.setFont(0, font)
            item.setForeground(0, Qt.GlobalColor.blue)
        else:
            # Closed - normal black text
            font = QFont()
            item.setFont(0, font)
            item.setForeground(0, Qt.GlobalColor.black)
        
        # Update directory counters for ALL ancestor directories
        if parent and (is_open != was_open):
            current = parent
            while current:
                # Get the directory path from the current node's data
                parent_data = current.data(0, Qt.ItemDataRole.UserRole)
                if parent_data and parent_data[0] == 'directory':
                    dir_path = parent_data[1]
                    
                    # Initialize counter if needed
                    if dir_path not in self.dir_open_counts:
                        self.dir_open_counts[dir_path] = 0
                    
                    # Update counter based on state change
                    if is_open and not was_open:
                        # File just opened - increment
                        self.dir_open_counts[dir_path] += 1
                    elif not is_open and was_open:
                        # File just closed - decrement
                        self.dir_open_counts[dir_path] -= 1
                    
                    # Update directory label
                    self._update_directory_label(current, dir_path)
                
                # Move up to parent
                current = current.parent()
    
    def update_commit_msg_state(self, is_open, is_active):
        """Update visual state of commit message item"""
        for item_type, item in self.special_items:
            if item_type == 'commit_msg':
                font = QFont()
                font.setBold(True)
                item.setFont(0, font)
                
                if is_active:
                    item.setForeground(0, Qt.GlobalColor.darkRed)
                elif is_open:
                    item.setForeground(0, Qt.GlobalColor.darkRed)
                else:
                    item.setForeground(0, Qt.GlobalColor.darkRed)
                break
    
    def update_notes_state(self, is_open, is_active):
        """Update visual state of review notes item"""
        for item_type, item in self.special_items:
            if item_type == 'review_notes':
                font = QFont()
                font.setBold(True)
                item.setFont(0, font)
                
                if is_active:
                    item.setForeground(0, Qt.GlobalColor.blue)
                elif is_open:
                    item.setForeground(0, Qt.GlobalColor.blue)
                else:
                    item.setForeground(0, Qt.GlobalColor.blue)
                break
    
    def update_file_label(self, file_class):
        """Update file label (e.g., after stats are loaded)"""
        if file_class not in self.file_items:
            return
        
        item = self.file_items[file_class]
        
        # Get the current text
        text = item.text(0)
        
        # Generate new label from file_class
        file_path = file_class.modi_rel_path_
        parts = file_path.split('/')
        
        # Extract just the filename (last component)
        filename = parts[-1]
        
        # Update text with stats if enabled
        if file_class.stats_file_:
            # Add stats
            if file_class.desc_:
                stats = ("[%d | A: %d / D: %d / C: %d]" %
                        (file_class.modi_line_count(),
                         file_class.add_line_count(),
                         file_class.del_line_count(),
                         file_class.chg_line_count()))
                new_text = "%s  %s" % (filename, stats)
            else:
                new_text = filename
        else:
            new_text = filename
        
        item.setText(0, new_text)
    
    def mark_file_changed(self, file_class, changed):
        """Mark a file as changed (for file watcher integration)"""
        if file_class not in self.file_items:
            return
        
        item = self.file_items[file_class]
        palette = color_palettes.get_current_palette()
        
        if changed:
            # Use orange color for changed files
            item.setForeground(0, Qt.GlobalColor.darkYellow)
        else:
            # Restore normal state based on open/active
            # We'll need to call update_file_state with current state
            # For now, just reset to black
            item.setForeground(0, Qt.GlobalColor.black)
    
    def update_open_all_text(self, total_files):
        """Update the Open All button text"""
        self.open_all_button.setText(f"Open All ({total_files}) Files")
