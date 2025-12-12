# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Commit message handler for diff_review

This module manages commit message tab functionality:
- Creating and displaying commit message tabs
- Context menus for commit messages
- Note taking from commit messages
- Font size management for commit message tabs
"""
from PyQt6.QtWidgets import QPlainTextEdit, QMenu, QMessageBox, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCharFormat, QColor, QPainter
from tab_content_base import TabContentBase


class CommitMessageTab(QWidget, TabContentBase):
    """
    Tab widget for displaying commit messages.

    This is a read-only view of the commit message with bookmark support
    and note-taking capability.
    """

    def __init__(self, commit_msg_text, commit_msg_handler):
        """
        Initialize commit message tab.

        Args:
            commit_msg_text: The commit message text to display
            commit_msg_handler: Reference to CommitMsgHandler for bookmarks
        """
        super().__init__()
        self.commit_msg_handler = commit_msg_handler
        self.current_font_size = 12

        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create text widget
        self.text_widget = QPlainTextEdit()
        self.text_widget.setReadOnly(True)
        self.text_widget.setPlainText(commit_msg_text)
        self.text_widget.setFont(QFont("Courier", self.current_font_size, QFont.Weight.Bold))

        # Store reference to handler for bookmark lookup
        self.text_widget.commit_msg_handler = commit_msg_handler

        # Override paintEvent to draw bookmark indicators
        original_paintEvent = self.text_widget.paintEvent
        def paintEvent_with_bookmarks(event):
            original_paintEvent(event)
            painter = QPainter(self.text_widget.viewport())

            for line_idx in commit_msg_handler.bookmarked_lines:
                block = self.text_widget.document().findBlockByNumber(line_idx)
                if block.isValid():
                    rect = self.text_widget.blockBoundingGeometry(block).translated(
                        self.text_widget.contentOffset())
                    y = int(rect.top())
                    height = int(rect.height())
                    # Bright cyan vertical bar on left edge - 5px wide
                    painter.fillRect(0, y, 5, height, QColor(0, 255, 255))

        self.text_widget.paintEvent = paintEvent_with_bookmarks

        # Style commit message with subtle sepia tone
        self.text_widget.setStyleSheet("""
            QPlainTextEdit {
                background-color: #fdf6e3;
                color: #5c4a3a;
            }
        """)

        # Create status bar with bookmark count
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(5, 2, 5, 2)

        self.bookmarks_label = QLabel("Bookmarks: 0")
        self.bookmarks_label.setStyleSheet("color: #5c4a3a; font-weight: bold;")
        status_layout.addWidget(self.bookmarks_label)
        status_layout.addStretch()

        # Add widgets to layout
        layout.addWidget(self.text_widget)
        layout.addWidget(status_widget)

    def increase_font_size(self):
        """Increase font size in commit message"""
        self.current_font_size += 1
        font = self.text_widget.font()
        font.setPointSize(self.current_font_size)
        self.text_widget.setFont(font)

    def decrease_font_size(self):
        """Decrease font size in commit message"""
        if self.current_font_size > 6:
            self.current_font_size -= 1
            font = self.text_widget.font()
            font.setPointSize(self.current_font_size)
            self.text_widget.setFont(font)

    def reset_font_size(self):
        """Reset font size to default (12pt)"""
        self.current_font_size = 12
        font = self.text_widget.font()
        font.setPointSize(self.current_font_size)
        self.text_widget.setFont(font)

    def reload(self):
        """Reload commit message from file"""
        commit_msg_text = self.commit_msg_handler.load_commit_msg_text()
        self.text_widget.setPlainText(commit_msg_text)

    def jump_to_note_from_cursor(self):
        """Jump to note for the line at cursor position (Ctrl+J handler)"""
        cursor = self.text_widget.textCursor()
        pos = self.text_widget.cursorRect(cursor).center()

        jump_action_func = self.commit_msg_handler.tab_widget.note_mgr.show_jump_to_note_menu_commit_msg(pos, self.text_widget)
        if jump_action_func:
            jump_action_func()

    def keyPressEvent(self, event):
        """Handle key press events"""
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_F5:
            self.reload()
            return

        if key == Qt.Key.Key_N and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.commit_msg_handler.take_commit_msg_note(self.text_widget)
            return

        if key == Qt.Key.Key_J and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.jump_to_note_from_cursor()
            return

        if ((key == Qt.Key.Key_S or key == Qt.Key.Key_F) and
            modifiers & Qt.KeyboardModifier.ControlModifier):
            self.commit_msg_handler.tab_widget.show_search_dialog()
            return

        if key == Qt.Key.Key_F3:
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                self.commit_msg_handler.tab_widget.search_mgr.find_previous()
            else:
                self.commit_msg_handler.tab_widget.search_mgr.find_next()
            return

        super().keyPressEvent(event)

    def toggle_bookmark(self):
        """Toggle bookmark on current line"""
        self.commit_msg_handler.toggle_bookmark(self.text_widget)

    def search_content(self, search_text, case_sensitive, regex, search_base=True, search_modi=True):
        """
        Search for text in commit message.

        Returns:
            List of tuples: (side, display_line_num, line_idx, line_text, char_pos)
        """
        results = []
        text = self.text_widget.toPlainText()
        lines = text.split('\n')
        
        for line_idx, line_text in enumerate(lines):
            # Find matches using same logic as search dialog
            matches = self._find_matches_in_line(line_text, search_text, case_sensitive, regex)
            for char_pos, matched_text in matches:
                results.append(('commit_msg', line_idx + 1, line_idx, line_text, char_pos))
        
        return results

    def _find_matches_in_line(self, line_text, search_text, case_sensitive, regex):
        """Find all match positions in a line. Returns list of (start_pos, match_text) tuples."""
        import re
        matches = []
        
        if regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(search_text, flags)
                for match in pattern.finditer(line_text):
                    matches.append((match.start(), match.group()))
            except re.error:
                pass
        else:
            search_str = search_text if case_sensitive else search_text.lower()
            search_in = line_text if case_sensitive else line_text.lower()
            
            pos = 0
            while True:
                found_pos = search_in.find(search_str, pos)
                if found_pos < 0:
                    break
                matched_text = line_text[found_pos:found_pos + len(search_text)]
                matches.append((found_pos, matched_text))
                pos = found_pos + len(search_text)
        
        return matches


class CommitMsgHandler:
    """Manages commit message tab creation and interaction"""
    
    def __init__(self, tab_widget):
        """
        Initialize commit message handler
        
        Args:
            tab_widget: Reference to DiffViewerTabWidget
        """
        self.tab_widget = tab_widget
        self.commit_msg_rel_path = None  # Track commit message file (internal)
        self.commit_msg_button = None  # Track commit message button
        self.bookmarked_lines = set()  # Line indices that are bookmarked in commit msg
    
    def add_commit_msg(self, commit_msg_rel_path):
        """
        Add commit message to the sidebar as the first item.
        
        Args:
            commit_msg_rel_path: Path to the commit message file
        """
        from PyQt6.QtWidgets import QPushButton
        
        self.commit_msg_rel_path = commit_msg_rel_path
        
        # Create a special button for commit message
        self.commit_msg_button = QPushButton("Commit Message")
        self.commit_msg_button.clicked.connect(self.on_commit_msg_clicked)
        self.commit_msg_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 8px 8px 20px;
                border: none;
                background-color: #fff4e6;
                border-left: 4px solid transparent;
                font-weight: bold;
                color: #e65100;
            }
            QPushButton:hover {
                background-color: #ffe0b2;
            }
        """)
        
        # Insert after "Open All" button (position 1)
        self.tab_widget.sidebar_widget.add_commit_msg_button(self.commit_msg_button)
    
    def on_commit_msg_clicked(self):
        """Handle commit message button click"""
        # Check if tab already exists
        if 'commit_msg' in self.tab_widget.file_to_tab_index:
            tab_index = self.tab_widget.file_to_tab_index['commit_msg']
            if 0 <= tab_index < self.tab_widget.tab_widget.count():
                self.tab_widget.tab_widget.setCurrentIndex(tab_index)
                return
            # Tab was closed, remove from mapping
            del self.tab_widget.file_to_tab_index['commit_msg']
        
        # Create new commit message tab
        self.create_commit_msg_tab()
    
    def load_commit_msg_text(self):
        """Load commit message text from file and return as string"""
        commit_msg_text = self.tab_widget.afr_.read(self.commit_msg_rel_path)

        # The afr_.read() will return the lines as an array of
        # non-'\n' strings.  The setPlainText() function seems to need
        # a single string.  So, for this special case, put the lines
        # back together.
        return '\n'.join(commit_msg_text)

    def create_commit_msg_tab(self):
        """Create a tab displaying the commit message"""
        commit_msg_text = self.load_commit_msg_text()

        # Create commit message tab widget
        tab_widget = CommitMessageTab(commit_msg_text, self)

        # Store reference for bookmark label updates
        self.bookmarks_label = tab_widget.bookmarks_label

        # Set up context menu
        tab_widget.text_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tab_widget.text_widget.customContextMenuRequested.connect(
            lambda pos: self.show_commit_msg_context_menu(pos, tab_widget.text_widget))

        # Install event filter for keyboard shortcuts
        tab_widget.text_widget.installEventFilter(self.tab_widget)

        # Add to tabs
        index = self.tab_widget.tab_widget.addTab(tab_widget, "Commit Message")
        self.tab_widget.file_to_tab_index['commit_msg'] = index
        self.tab_widget.tab_widget.setCurrentIndex(index)

        # Update button state
        self.tab_widget.update_button_states()
    
    def show_commit_msg_context_menu(self, pos, text_widget):
        """Show context menu for commit message"""
        menu = QMenu(self.tab_widget)
        cursor = text_widget.textCursor()
        has_selection = cursor.hasSelection()
        
        search_action = menu.addAction("Search")
        search_action.setEnabled(has_selection)
        if has_selection:
            search_action.triggered.connect(
                lambda: self.tab_widget.search_selected_text(text_widget))
        
        menu.addSeparator()
        
        # Note taking - always enable if there's a selection
        if has_selection:
            note_action = menu.addAction("Take Note")
            note_action.triggered.connect(
                lambda: self.take_commit_msg_note(text_widget))
        else:
            note_action = menu.addAction("Take Note (no selection)")
            note_action.setEnabled(False)
        
        # Add "Jump to Note" if this line has a note
        jump_action_func = self.tab_widget.note_mgr.show_jump_to_note_menu_commit_msg(pos, text_widget)
        if jump_action_func:
            menu.addSeparator()
            jump_action = menu.addAction("Jump to Note")
            jump_action.triggered.connect(jump_action_func)
        
        menu.exec(text_widget.mapToGlobal(pos))
    
    def take_commit_msg_note(self, text_widget):
        """Take note from commit message"""
        cursor = text_widget.textCursor()
        if not cursor.hasSelection():
            return
        
        # Get NoteManager
        note_mgr = self.tab_widget.note_mgr
        
        # Save selection range before doing anything
        selection_start = cursor.selectionStart()
        selection_end = cursor.selectionEnd()
        
        # Calculate line number range for the selection
        doc = text_widget.document()
        start_block = doc.findBlock(selection_start)
        end_block = doc.findBlock(selection_end)
        
        start_line = start_block.blockNumber()
        end_line = end_block.blockNumber() + 1  # Half-open range [start, end)
        
        selected_text = cursor.selectedText()
        selected_text = selected_text.replace('\u2029', '\n')
        
        # Split into lines for note taking
        line_texts = selected_text.split('\n')
        
        # Take note using NoteManager with line range
        if note_mgr.take_note("Commit Message", 'commit_msg', (start_line, end_line), line_texts, is_commit_msg=True):
            # Apply permanent yellow background to noted text
            # Create new cursor with saved selection
            highlight_cursor = text_widget.textCursor()
            highlight_cursor.setPosition(selection_start)
            highlight_cursor.setPosition(selection_end, highlight_cursor.MoveMode.KeepAnchor)
            
            # Create yellow highlight format (match DiffViewer color)
            highlight_format = QTextCharFormat()
            highlight_format.setBackground(QColor(255, 255, 200))  # Light yellow like DiffViewer
            
            # Apply permanent yellow highlight
            highlight_cursor.mergeCharFormat(highlight_format)
            
            # Update note count in current viewer if it exists
            viewer = self.tab_widget.get_current_viewer()
            if viewer:
                viewer.note_count += 1
                viewer.update_status()
    
    def change_commit_msg_font_size(self, text_widget, delta):
        """Change font size for commit message tab"""
        if not hasattr(text_widget, 'current_font_size'):
            text_widget.current_font_size = 12  # Initialize if not set
        
        new_size = text_widget.current_font_size + delta
        # Clamp to range [6, 24]
        new_size = max(6, min(24, new_size))
        
        if new_size != text_widget.current_font_size:
            text_widget.current_font_size = new_size
            font = QFont("Courier", new_size, QFont.Weight.Bold)
            text_widget.setFont(font)
            text_widget.viewport().update()
    
    def reset_commit_msg_font_size(self, text_widget):
        """Reset font size for commit message tab to default (12pt)"""
        text_widget.current_font_size = 12
        font = QFont("Courier", 12, QFont.Weight.Bold)
        text_widget.setFont(font)
        text_widget.viewport().update()

    def toggle_bookmark(self, text_widget):
        """Toggle bookmark on current line in commit message"""
        cursor = text_widget.textCursor()
        line_idx = cursor.blockNumber()

        if line_idx in self.bookmarked_lines:
            self.bookmarked_lines.remove(line_idx)
        else:
            self.bookmarked_lines.add(line_idx)

        # Sync with global bookmarks
        tab_index = self.tab_widget.tab_widget.currentIndex()
        key = (tab_index, line_idx)

        if line_idx in self.bookmarked_lines:
            self.tab_widget.bookmark_mgr.global_bookmarks[key] = True
        elif key in self.tab_widget.bookmark_mgr.global_bookmarks:
            del self.tab_widget.bookmark_mgr.global_bookmarks[key]

        # Force repaint to show bookmark indicators
        text_widget.viewport().update()

        # Update status
        self.update_status()

    def update_status(self):
        """Update status bar with current bookmark count"""
        self.bookmarks_label.setText(f"Bookmarks: {len(self.bookmarked_lines)}")

    def center_on_line(self, text_widget, line_idx):
        """Center the view on a specific line"""
        cursor = text_widget.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        for _ in range(line_idx):
            cursor.movePosition(cursor.MoveOperation.Down)
        text_widget.setTextCursor(cursor)
        text_widget.ensureCursorVisible()
    
    def update_button_state(self, is_open, is_active):
        """Update commit message button style based on state"""
        if not self.commit_msg_button:
            return
        
        if is_active:
            # Currently selected - bright highlight
            self.commit_msg_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 8px 8px 20px;
                    border: none;
                    background-color: #ffd699;
                    border-left: 6px solid #ff9800;
                    font-weight: bold;
                    color: #e65100;
                }
                QPushButton:hover {
                    background-color: #ffcc80;
                }
            """)
        elif is_open:
            # Open but not selected - subtle highlight
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
            # Closed - no highlight
            self.commit_msg_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 8px 8px 20px;
                    border: none;
                    background-color: #fff4e6;
                    border-left: 4px solid transparent;
                    font-weight: bold;
                    color: #e65100;
                }
                QPushButton:hover {
                    background-color: #ffe0b2;
                }
            """)
