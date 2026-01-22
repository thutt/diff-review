# Copyright (c) 2025, 2026  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
File tree sidebar for diff_review

This module provides a tree view for organizing files by directory structure
in the sidebar, with collapsible directory nodes.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
                              QPushButton, QApplication, QSplitter,
                              QLabel, QFrame, QHBoxLayout, QScrollArea, QLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen
import color_palettes


class VerticalRangeSlider(QWidget):
    """A vertical slider with two handles for selecting a range."""

    range_changed = pyqtSignal(int, int)  # Emits (low_idx, high_idx)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(24)
        self.setMaximumWidth(24)

        self._count = 0  # Number of items
        self._low_idx = 0  # Lower bound index (top handle)
        self._high_idx = 0  # Upper bound index (bottom handle)

        self._dragging = None  # 'low', 'high', or None
        self._handle_height = 12
        self._track_margin = 6  # Margin at top/bottom for handles

    def sizeHint(self):
        from PyQt6.QtCore import QSize
        # Width is fixed at 24, height based on count (or minimum 50)
        height = max(50, self._count * 25 + 2 * self._track_margin)
        return QSize(24, height)

    def set_count(self, count):
        """Set the number of items in the range."""
        self._count = count
        if count > 0:
            self._low_idx = 0
            self._high_idx = count - 1
        else:
            self._low_idx = 0
            self._high_idx = 0
        self.update()

    def set_range(self, low_idx, high_idx):
        """Set the current range selection. low_idx must be less than high_idx."""
        if self._count == 0:
            return
        self._low_idx = max(0, min(low_idx, self._count - 2))
        self._high_idx = max(self._low_idx + 1, min(high_idx, self._count - 1))
        self.update()

    def get_range(self):
        """Return current (low_idx, high_idx)."""
        return (self._low_idx, self._high_idx)

    def _idx_to_y(self, idx):
        """Convert item index to y coordinate."""
        if self._count <= 1:
            return self._track_margin
        usable_height = self.height() - 2 * self._track_margin - self._handle_height
        return self._track_margin + int(idx * usable_height / (self._count - 1))

    def _y_to_idx(self, y):
        """Convert y coordinate to nearest item index."""
        if self._count <= 1:
            return 0
        usable_height = self.height() - 2 * self._track_margin - self._handle_height
        if usable_height <= 0:
            return 0
        idx = round((y - self._track_margin) * (self._count - 1) / usable_height)
        return max(0, min(idx, self._count - 1))

    def paintEvent(self, event):
        """Draw the slider track and handles."""
        if self._count == 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        track_x = width // 2 - 2
        track_width = 4

        # Draw track background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(200, 200, 200)))
        painter.drawRect(track_x, self._track_margin,
                        track_width, self.height() - 2 * self._track_margin)

        # Draw selected range on track
        low_y = self._idx_to_y(self._low_idx)
        high_y = self._idx_to_y(self._high_idx)
        painter.setBrush(QBrush(QColor(100, 150, 255)))
        painter.drawRect(track_x, low_y + self._handle_height // 2,
                        track_width, high_y - low_y)

        # Draw handles
        handle_width = 16
        handle_x = (width - handle_width) // 2

        # Low handle (top)
        painter.setBrush(QBrush(QColor(70, 130, 220)))
        painter.setPen(QPen(QColor(50, 100, 180), 1))
        painter.drawRoundedRect(handle_x, low_y, handle_width, self._handle_height, 3, 3)

        # High handle (bottom)
        painter.drawRoundedRect(handle_x, high_y, handle_width, self._handle_height, 3, 3)

        painter.end()

    def mousePressEvent(self, event):
        """Start dragging a handle."""
        if self._count == 0:
            return

        y = event.position().y()
        low_y = self._idx_to_y(self._low_idx)
        high_y = self._idx_to_y(self._high_idx)

        # Check if clicking on low handle
        if abs(y - (low_y + self._handle_height // 2)) < self._handle_height:
            self._dragging = 'low'
        # Check if clicking on high handle
        elif abs(y - (high_y + self._handle_height // 2)) < self._handle_height:
            self._dragging = 'high'
        else:
            self._dragging = None

    def mouseMoveEvent(self, event):
        """Move the dragged handle."""
        if self._dragging is None or self._count == 0:
            return

        new_idx = self._y_to_idx(event.position().y())

        if self._dragging == 'low':
            # Low handle must stay below high handle (cannot be equal)
            new_idx = min(new_idx, self._high_idx - 1)
            if new_idx != self._low_idx and new_idx >= 0:
                self._low_idx = new_idx
                self.update()
                self.range_changed.emit(self._low_idx, self._high_idx)
        elif self._dragging == 'high':
            # High handle must stay above low handle (cannot be equal)
            new_idx = max(new_idx, self._low_idx + 1)
            if new_idx != self._high_idx and new_idx < self._count:
                self._high_idx = new_idx
                self.update()
                self.range_changed.emit(self._low_idx, self._high_idx)

    def mouseReleaseEvent(self, event):
        """Stop dragging."""
        self._dragging = None


class ClickableCommitLabel(QLabel):
    """A clickable label for commit items."""

    clicked = pyqtSignal(str)  # Emits SHA

    def __init__(self, text, sha, parent=None):
        super().__init__(text, parent)
        self.sha = sha
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QLabel {
                padding: 4px 8px;
                color: darkred;
            }
            QLabel:hover {
                background-color: #e0e0e0;
            }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.sha)
        super().mousePressEvent(event)

    def set_in_range(self, in_range):
        """Update background based on whether commit is in selected range."""
        if in_range:
            self.setStyleSheet("""
                QLabel {
                    padding: 4px 8px;
                    color: darkred;
                    background-color: #e6f0ff;
                }
                QLabel:hover {
                    background-color: #d0e0f0;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    padding: 4px 8px;
                    color: darkred;
                }
                QLabel:hover {
                    background-color: #e0e0e0;
                }
            """)

    def set_active(self, is_active):
        """Set bold if this commit's tab is active."""
        font = self.font()
        font.setBold(is_active)
        self.setFont(font)


class CommitListWidget(QWidget):
    """Widget displaying commit messages in a scrollable list for revision range selection."""

    def __init__(self, tab_widget, parent=None):
        super().__init__(parent)
        self.tab_widget = tab_widget
        self.commit_items = {}  # SHA -> QListWidgetItem mapping
        self.sha_list = []  # Ordered list of SHAs

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header label
        self.header_label = QLabel("Commits")
        self.header_label.setStyleSheet("""
            QLabel {
                padding: 5px;
                background-color: #f0f0f0;
                font-weight: bold;
                border-bottom: 1px solid #ccc;
            }
        """)
        layout.addWidget(self.header_label)

        # Horizontal layout for slider and list inside a scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(False)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

        # Range slider on the left
        self.range_slider = VerticalRangeSlider()
        self.range_slider.range_changed.connect(self._on_range_changed)
        content_layout.addWidget(self.range_slider)

        # Use a simple widget with vertical layout for commit items
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(0)
        self.list_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        content_layout.addWidget(self.list_container)

        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)

    def set_commits(self, commit_msgs_by_sha, commit_summaries_by_sha=None):
        """Populate the list with commits.

        Args:
            commit_msgs_by_sha: Dict mapping SHA -> commit_msg_rel_path
            commit_summaries_by_sha: Dict mapping SHA -> commit summary string (optional)
        """
        # Clear existing items
        self.commit_items.clear()
        self.sha_list = []

        # Remove old labels from layout
        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not commit_msgs_by_sha:
            self.header_label.setText("Commits (0)")
            self.range_slider.set_count(0)
            return

        self.header_label.setText(f"Commits ({len(commit_msgs_by_sha)})")

        if commit_summaries_by_sha is None:
            commit_summaries_by_sha = {}

        for sha, rel_path in commit_msgs_by_sha.items():
            summary = commit_summaries_by_sha.get(sha, "")
            if summary:
                display_text = f"{sha[:7]}: {summary}"
            else:
                display_text = sha[:7]
            label = ClickableCommitLabel(display_text, sha)
            label.clicked.connect(self._on_label_clicked)
            self.list_layout.addWidget(label)
            self.commit_items[sha] = label
            self.sha_list.append(sha)

        # Initialize range slider
        self.range_slider.set_count(len(self.sha_list))

    def set_range(self, low_idx, high_idx):
        """Set the range selection on the slider."""
        self.range_slider.set_range(low_idx, high_idx)
        self._update_range_highlighting()

    def _on_label_clicked(self, sha):
        """Handle click on a commit label."""
        self.tab_widget.on_commit_msg_clicked(sha)

    def _on_range_changed(self, low_idx, high_idx):
        """Handle range slider change."""
        self._update_range_highlighting()
        # Notify tab_widget of range change
        self.tab_widget._set_revision_range(low_idx, high_idx)

    def _update_range_highlighting(self):
        """Update visual highlighting of commits in the selected range."""
        low_idx, high_idx = self.range_slider.get_range()

        for i, sha in enumerate(self.sha_list):
            label = self.commit_items[sha]
            in_range = low_idx <= i <= high_idx
            label.set_in_range(in_range)

    def _on_item_clicked(self, item):
        """Handle click on a commit item."""
        sha = item.data(Qt.ItemDataRole.UserRole)
        if sha:
            self.tab_widget.on_commit_msg_clicked(sha)

    def update_commit_state(self, sha, is_open, is_active):
        """Update visual state of a commit item."""
        if sha not in self.commit_items:
            return

        label = self.commit_items[sha]
        label.set_active(is_active)

    def clear(self):
        """Clear all commits from the list."""
        # Remove old labels from layout
        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.commit_items.clear()
        self.sha_list = []
        self.header_label.setText("Commits (0)")
        self.range_slider.set_count(0)


class CompareLabel(QLabel):
    """A label for compare items (HEAD/Staged/Working)."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            QLabel {
                padding: 4px 8px;
                color: #333;
            }
        """)

    def set_in_range(self, in_range):
        """Update background based on whether item is in selected range."""
        if in_range:
            self.setStyleSheet("""
                QLabel {
                    padding: 4px 8px;
                    color: #333;
                    background-color: #e6f0ff;
                }
            """)
        else:
            self.setStyleSheet("""
                QLabel {
                    padding: 4px 8px;
                    color: #333;
                }
            """)


class CompareListWidget(QWidget):
    """Widget displaying HEAD/Staged/Working states for diff mode selection."""

    def __init__(self, tab_widget, parent=None):
        super().__init__(parent)
        self.tab_widget = tab_widget
        self.labels = []  # List of CompareLabel widgets

        # Prevent this widget from expanding vertically
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header label
        self.header_label = QLabel("Compare")
        self.header_label.setStyleSheet("""
            QLabel {
                padding: 5px;
                background-color: #f0f0f0;
                font-weight: bold;
                border-bottom: 1px solid #ccc;
            }
        """)
        layout.addWidget(self.header_label)

        # Horizontal layout for slider and list
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

        # Range slider on the left
        self.range_slider = VerticalRangeSlider()
        self.range_slider.range_changed.connect(self._on_range_changed)
        content_layout.addWidget(self.range_slider)

        # Labels for the three states
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(0)
        self.list_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)

        # Create the three state labels
        for text in ["HEAD", "Staged", "Working"]:
            label = CompareLabel(text)
            self.list_layout.addWidget(label)
            self.labels.append(label)

        content_layout.addWidget(self.list_container)
        layout.addWidget(content_widget)

        # Initialize slider with 3 items
        self.range_slider.set_count(3)
        # Default: HEAD to Working (0 to 2)
        self.range_slider.set_range(0, 2)
        self._update_range_highlighting()

    def set_range(self, low_idx, high_idx):
        """Set the range selection on the slider."""
        self.range_slider.set_range(low_idx, high_idx)
        self._update_range_highlighting()

    def _on_range_changed(self, low_idx, high_idx):
        """Handle range slider change."""
        self._update_range_highlighting()
        # Convert range to diff mode and notify tab_widget
        self.tab_widget._set_compare_range(low_idx, high_idx)

    def _update_range_highlighting(self):
        """Update visual highlighting of items in the selected range."""
        low_idx, high_idx = self.range_slider.get_range()

        for i, label in enumerate(self.labels):
            in_range = low_idx <= i <= high_idx
            label.set_in_range(in_range)


class FileTreeWidget(QTreeWidget):
    """Custom tree widget that handles Space key like Enter"""

    def keyPressEvent(self, event):
        """Handle Space and Enter keys to activate current item, block Tab navigation"""
        # Block Tab and Shift+Tab to prevent focus navigation
        if event.key() == Qt.Key.Key_Tab:
            event.accept()
            return

        # Handle both Enter and Space to activate items (needed for macOS compatibility)
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            current_item = self.currentItem()
            if current_item:
                # Emit itemActivated signal
                self.itemActivated.emit(current_item, 0)
                event.accept()
                return

        # Let default handling proceed for all other keys
        super().keyPressEvent(event)


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
        self.open_all_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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

        # Vertical splitter for commit list/compare list and file tree
        self.vsplitter = QSplitter(Qt.Orientation.Vertical)

        # Commit list widget (for committed mode, initially hidden)
        self.commit_list_widget = CommitListWidget(tab_widget)
        self.commit_list_widget.setVisible(False)
        self.vsplitter.addWidget(self.commit_list_widget)

        # Compare list widget (for uncommitted mode, initially hidden)
        self.compare_list_widget = CompareListWidget(tab_widget)
        self.compare_list_widget.setVisible(False)
        self.vsplitter.addWidget(self.compare_list_widget)

        # Container for file tree
        self.tree_container = QWidget()
        tree_layout = QVBoxLayout(self.tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(0)

        # Tree widget (custom class handles Space key)
        self.tree = FileTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setAnimated(True)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemActivated.connect(self.on_item_clicked)

        # Set up context menu for right-click to focus tree
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.on_tree_right_click)

        tree_layout.addWidget(self.tree)
        self.vsplitter.addWidget(self.tree_container)

        # Set initial splitter sizes (commit list, compare list, tree)
        # The visible widget(s) will get appropriate sizes when shown
        self.vsplitter.setSizes([150, 150, 400])

        layout.addWidget(self.vsplitter)

        # Store special buttons (commit msg, review notes) as list items
        self.special_items = []  # List of (item_type, widget) tuples
        self.commit_msg_folder = None  # Reference to commit messages folder item (legacy)
        self.commit_msg_items = {}  # SHA -> QTreeWidgetItem mapping (legacy)

    def add_commit_msg_button(self, button):
        """Legacy method - adds single commit message as tree item (for uncommitted mode)"""
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

    def add_commit_messages_folder(self, commit_msgs_by_sha, commit_summaries_by_sha=None):
        """Add commits to the commit list widget (for committed mode with multiple revisions).

        Args:
            commit_msgs_by_sha: Dict mapping SHA -> commit_msg_rel_path
                               Only includes revisions that have commit messages.
            commit_summaries_by_sha: Dict mapping SHA -> commit summary string (optional)
        """
        if not commit_msgs_by_sha:
            self.commit_list_widget.setVisible(False)
            return

        # Populate the commit list widget and make it visible
        self.commit_list_widget.set_commits(commit_msgs_by_sha, commit_summaries_by_sha)
        self.commit_list_widget.setVisible(True)

        # Store SHA -> item mapping for state updates
        self.commit_msg_items = self.commit_list_widget.commit_items

        # Sync slider with current revision range from tab_widget
        base_idx = self.tab_widget.revision_base_idx_
        modi_idx = self.tab_widget.revision_modi_idx_
        if base_idx is not None and modi_idx is not None:
            self.commit_list_widget.set_range(base_idx, modi_idx)
    
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
        file_path = file_class.display_path()
        
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
            # item_data is SHA (or None for legacy single commit message)
            self.tab_widget.on_commit_msg_clicked(item_data)
            # Focus the text widget in the commit message tab
            self._focus_current_tab_widget()
        elif item_type == 'commit_msg_folder':
            # Toggle expand/collapse on folder click
            item.setExpanded(not item.isExpanded())
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
                self.tab_widget.last_content_tab_index = self.tab_widget.tab_widget.currentIndex()
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
                self.tab_widget.last_content_tab_index = self.tab_widget.tab_widget.currentIndex()
                self.tab_widget.update_focus_tinting()
                self.tab_widget.update_status_focus_indicator()
    
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
    
    def update_commit_msg_state(self, is_open, is_active, sha=None):
        """Update visual state of commit message item.

        Args:
            is_open: Whether the commit message tab is open
            is_active: Whether it's the currently active tab
            sha: Commit SHA (None for legacy single commit message)
        """
        if sha is not None:
            # Multi-commit case - delegate to commit list widget
            self.commit_list_widget.update_commit_state(sha, is_open, is_active)
            return

        # Legacy single commit message case
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
        file_path = file_class.display_path()
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

    def update_file_visibility_for_mode(self, file_classes, diff_mode):
        """Update file visibility based on diff mode.

        HEAD vs Working: Show all files
        HEAD vs Staged: Show only files with staged content
        Staged vs Working: Show only files with both staged and unstaged content

        Args:
            file_classes: List of all file class instances
            diff_mode: Current diff mode constant
        """
        import generate_viewer

        visible_count = 0
        for file_class in file_classes:
            if file_class not in self.file_items:
                continue

            item = self.file_items[file_class]

            if diff_mode == generate_viewer.DIFF_MODE_BASE_MODI:
                # HEAD vs Working: show all files
                should_show = True
            elif diff_mode == generate_viewer.DIFF_MODE_BASE_STAGE:
                # HEAD vs Staged: show files with staged content
                # FileButton (staged-only) or FileButtonUnstaged with has_staged()
                if isinstance(file_class, generate_viewer.FileButtonUnstaged):
                    should_show = file_class.has_staged()
                else:
                    # FileButton is used for staged-only files
                    should_show = True
            else:  # DIFF_MODE_STAGE_MODI
                # Staged vs Working: show only files with both staged and unstaged
                should_show = (isinstance(file_class, generate_viewer.FileButtonUnstaged)
                               and file_class.has_staged())

            item.setHidden(not should_show)
            if should_show:
                visible_count += 1

        # Update directory visibility - hide empty directories
        self._update_directory_visibility()

        # Update Open All button text with visible count
        self.open_all_button.setText(f"Open All ({visible_count}) Files")

    def _update_directory_visibility(self):
        """Hide directories that have no visible children."""
        # Process directories from deepest to shallowest
        # Sort by path depth (number of slashes) in reverse order
        sorted_dirs = sorted(self.dir_items.keys(),
                            key=lambda p: p.count('/'),
                            reverse=True)

        for dir_path in sorted_dirs:
            dir_item = self.dir_items[dir_path]
            has_visible_child = False

            for i in range(dir_item.childCount()):
                child = dir_item.child(i)
                if not child.isHidden():
                    has_visible_child = True
                    break

            dir_item.setHidden(not has_visible_child)
