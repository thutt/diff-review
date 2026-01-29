# Copyright (c) 2025, 2026  Logic Magicians Software (Taylor Hutt).
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

    def __init__(self, commit_msg_text, commit_msg_handler, sha=None):
        """
        Initialize commit message tab.

        Args:
            commit_msg_text: The commit message text to display
            commit_msg_handler: Reference to CommitMsgHandler for bookmarks
            sha: Commit SHA (None for legacy single commit message)
        """
        super().__init__()
        self.commit_msg_handler = commit_msg_handler
        self.sha = sha
        self.revision_index_ = None  # Set by tab_manager for multi-revision mode
        self.current_font_size = 12

        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create text widget
        self.text_widget = QPlainTextEdit()
        # Use TextInteractionFlags instead of setReadOnly to allow cursor display
        # TextSelectableByMouse | TextSelectableByKeyboard allows selection and cursor
        # but prevents editing
        self.text_widget.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self.text_widget.setPlainText(commit_msg_text)
        self.text_widget.setFont(QFont("Courier", self.current_font_size, QFont.Weight.Bold))

        # Initialize cursor as hidden
        self.text_widget.setCursorWidth(0)

        # Store reference to handler for bookmark lookup
        self.text_widget.commit_msg_handler = commit_msg_handler

        # Override paintEvent to draw bookmark indicators
        original_paintEvent = self.text_widget.paintEvent
        def paintEvent_with_bookmarks(event):
            original_paintEvent(event)
            painter = QPainter(self.text_widget.viewport())

            bookmarked_lines = commit_msg_handler.get_bookmarked_lines(sha)
            for line_idx in bookmarked_lines:
                block = self.text_widget.document().findBlockByNumber(line_idx)
                if block.isValid():
                    rect = self.text_widget.blockBoundingGeometry(block).translated(
                        self.text_widget.contentOffset())
                    y = int(rect.top())
                    height = int(rect.height())
                    # Bright cyan vertical bar on left edge - 5px wide
                    painter.fillRect(0, y, 5, height, QColor(0, 255, 255))

        self.text_widget.paintEvent = paintEvent_with_bookmarks

        # Override mousePressEvent to hide cursor on mouse click
        original_mousePressEvent = self.text_widget.mousePressEvent
        def mousePressEvent_with_cursor_hide(event):
            self.text_widget.setCursorWidth(0)
            original_mousePressEvent(event)

        self.text_widget.mousePressEvent = mousePressEvent_with_cursor_hide

        # Override keyPressEvent to show cursor on navigation keys
        original_keyPressEvent = self.text_widget.keyPressEvent
        def keyPressEvent_with_cursor_show(event):
            key = event.key()
            is_nav_key = key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_PageUp,
                                 Qt.Key.Key_PageDown, Qt.Key.Key_Home, Qt.Key.Key_End,
                                 Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Space)
            if is_nav_key:
                self.text_widget.setCursorWidth(2)
            original_keyPressEvent(event)

        self.text_widget.keyPressEvent = keyPressEvent_with_cursor_show

        # Override focusNextPrevChild to ignore Tab key (prevent focus from leaving)
        self.text_widget.focusNextPrevChild = lambda next: True

        # Style commit message with subtle sepia tone
        self.text_widget.setStyleSheet("""
            QPlainTextEdit {
                background-color: #fdf6e3;
                color: #5c4a3a;
            }
        """)

        # Create status bar with revision range and bookmark count
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(5, 2, 5, 2)

        self.revision_range_label = QLabel("")
        status_layout.addWidget(self.revision_range_label)

        self.bookmarks_label = QLabel("Bookmarks: 0")
        self.bookmarks_label.setStyleSheet("color: #5c4a3a; font-weight: bold;")
        status_layout.addWidget(self.bookmarks_label)

        status_layout.addStretch()

        # Add widgets to layout
        layout.addWidget(self.text_widget)
        layout.addWidget(status_widget)

    def set_revision_index(self, index):
        """Set the revision index for this commit message and update the status bar.

        Args:
            index: The 1-based index of this commit in the revision list
        """
        self.revision_index_ = index
        self.revision_range_label.setText(f"Range: [{index}]")

    def update_status(self):
        """Update status bar with current bookmark count"""
        self.bookmarks_label.setText(f"Bookmarks: {len(self.commit_msg_handler.bookmarked_lines)}")

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

    def take_note(self):
        """Take a note from the selected text in the commit message"""
        cursor = self.text_widget.textCursor()
        if not cursor.hasSelection():
            return

        selection_start = cursor.selectionStart()
        selection_end = cursor.selectionEnd()

        doc = self.text_widget.document()
        start_block = doc.findBlock(selection_start)
        end_block = doc.findBlock(selection_end)

        start_line = start_block.blockNumber()
        end_line = end_block.blockNumber()

        if selection_end == end_block.position():
            end_line -= 1

        selected_texts = []
        for line_num in range(start_line, end_line + 1):
            block = doc.findBlockByNumber(line_num)
            if block.isValid():
                selected_texts.append(block.text())

        if not selected_texts:
            return

        tab_widget = self.commit_msg_handler.tab_widget
        if not tab_widget:
            return

        note_mgr = tab_widget.note_mgr
        line_range = (start_line, end_line + 1)

        # Get short SHA for note header
        sha = self.sha[:7] if self.sha else None

        if note_mgr.take_note(None, "commit_msg", line_range, selected_texts, is_commit_msg=True, sha=sha):
            pass

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

    def focus_content(self):
        """Set Qt focus to the text widget"""
        self.text_widget.setFocus()

    def save_buffer(self):
        """Commit message tabs have nothing to save"""
        pass

    def keyPressEvent(self, event):
        """Handle key press events - most handled by tab_manager keybindings now"""
        # All key handling now goes through tab_manager's keybinding system
        # Pass to parent to allow normal text editing behavior
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
        self.commit_msg_rel_path = None  # Track commit message file (internal, legacy)
        self.commit_msg_button = None  # Track commit message button (legacy)
        self.bookmarked_lines = set()  # Line indices that are bookmarked in commit msg (legacy)
        self.commit_msg_tab = None  # Reference to CommitMessageTab when created (legacy)

        # Multi-commit-message support
        self.commit_msgs = {}  # SHA -> rel_path mapping
        self.bookmarked_lines_by_sha = {}  # SHA -> set of bookmarked line indices

    def add_commit_msg(self, commit_msg_rel_path):
        """
        Add commit message to the sidebar as the first item (legacy, for uncommitted mode).

        Args:
            commit_msg_rel_path: Path to the commit message file
        """
        from PyQt6.QtWidgets import QPushButton

        self.commit_msg_rel_path = commit_msg_rel_path

        # Create a special button for commit message
        self.commit_msg_button = QPushButton("Commit Message")
        self.commit_msg_button.clicked.connect(lambda: self.on_commit_msg_clicked(None))
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

    def add_commit_messages_from_dossier(self, dossier):
        """
        Add commit messages folder from dossier (for committed mode with multiple revisions).

        Args:
            dossier: The full dossier dictionary
        """
        order = dossier["order"]
        revisions = dossier["revisions"]

        # Collect all revisions that have commit messages, preserving order
        commit_msgs_by_sha = {}
        commit_summaries_by_sha = {}
        for sha in order:
            rev = revisions[sha]
            if rev["commit_msg"] is not None:
                commit_msgs_by_sha[sha] = rev["commit_msg"]
                commit_summaries_by_sha[sha] = rev.get("commit_summary", "")
                if sha not in self.bookmarked_lines_by_sha:
                    self.bookmarked_lines_by_sha[sha] = set()

        self.commit_msgs = commit_msgs_by_sha

        if commit_msgs_by_sha:
            self.tab_widget.sidebar_widget.add_commit_messages_folder(
                commit_msgs_by_sha, commit_summaries_by_sha)

    def on_commit_msg_clicked(self, sha=None):
        """Handle commit message button/item click

        Args:
            sha: Commit SHA (None for legacy single commit message)
        """
        # Determine tab key
        tab_key = f'commit_msg_{sha}' if sha else 'commit_msg'

        # Check if tab already exists
        if tab_key in self.tab_widget.file_to_tab_index:
            tab_index = self.tab_widget.file_to_tab_index[tab_key]
            if 0 <= tab_index < self.tab_widget.tab_widget.count():
                self.tab_widget.tab_widget.setCurrentIndex(tab_index)
                return
            # Tab was closed, remove from mapping
            del self.tab_widget.file_to_tab_index[tab_key]

        # Create new commit message tab
        self.create_commit_msg_tab(sha)

    def load_commit_msg_text(self, sha=None):
        """Load commit message text from file and return as string

        Args:
            sha: Commit SHA (None for legacy single commit message)
        """
        if sha and sha in self.commit_msgs:
            rel_path = self.commit_msgs[sha]
        else:
            rel_path = self.commit_msg_rel_path

        commit_msg_text = self.tab_widget.afr_.read(rel_path)

        # The afr_.read() will return the lines as an array of
        # non-'\n' strings.  The setPlainText() function seems to need
        # a single string.  So, for this special case, put the lines
        # back together.
        return '\n'.join(commit_msg_text)

    def get_bookmarked_lines(self, sha=None):
        """Get bookmarked lines for a specific commit message.

        Args:
            sha: Commit SHA (None for legacy single commit message)
        """
        if sha and sha in self.bookmarked_lines_by_sha:
            return self.bookmarked_lines_by_sha[sha]
        return self.bookmarked_lines

    def create_commit_msg_tab(self, sha=None):
        """Create a tab displaying the commit message

        Args:
            sha: Commit SHA (None for legacy single commit message)
        """
        commit_msg_text = self.load_commit_msg_text(sha)

        # Create commit message tab widget
        tab_widget = CommitMessageTab(commit_msg_text, self, sha)

        # Store reference to tab for status updates
        self.commit_msg_tab = tab_widget

        # Set revision index for multi-revision mode
        if (sha is not None
                and self.tab_widget.review_mode_ == "committed"
                and self.tab_widget.dossier_ is not None
                and len(self.tab_widget.dossier_["order"]) >= 2):
            order = self.tab_widget.dossier_["order"]
            try:
                # Find index in order list, add 1 for 1-based display
                idx = order.index(sha)
                tab_widget.set_revision_index(idx + 1)
            except ValueError:
                pass  # SHA not in order list

        # Set up context menu
        tab_widget.text_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tab_widget.text_widget.customContextMenuRequested.connect(
            lambda pos: self.show_commit_msg_context_menu(pos, tab_widget.text_widget, sha))

        # Install event filter for keyboard shortcuts
        tab_widget.text_widget.installEventFilter(self.tab_widget)

        # Determine tab title and key
        if sha:
            tab_title = f"Commit ({sha[:7]})"
            tab_key = f'commit_msg_{sha}'
        else:
            tab_title = "Commit Message"
            tab_key = 'commit_msg'

        # Add to tabs
        index = self.tab_widget.tab_widget.addTab(tab_widget, tab_title)
        self.tab_widget.file_to_tab_index[tab_key] = index
        self.tab_widget.tab_widget.setCurrentIndex(index)

        # Update button state
        self.tab_widget.update_button_states()

        # Update status to show note file if set
        tab_widget.update_status()
    
    def show_commit_msg_context_menu(self, pos, text_widget, sha=None):
        """Show context menu for commit message

        Args:
            pos: Position for the menu
            text_widget: The text widget
            sha: Commit SHA (None for legacy single commit message)
        """
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
                lambda: self.take_commit_msg_note(text_widget, sha))
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
    
    def take_commit_msg_note(self, text_widget, sha=None):
        """Take note from commit message

        Args:
            text_widget: The text widget containing the commit message
            sha: Commit SHA (None for legacy single commit message)
        """
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

        # Get short SHA for note header
        short_sha = sha[:7] if sha else None

        # Take note using NoteManager with line range
        if note_mgr.take_note(None, "commit_msg", (start_line, end_line), line_texts, is_commit_msg=True, sha=short_sha):
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

        if line_idx in self.bookmarked_lines:
            self.tab_widget.bookmark_mgr.add_bookmark(tab_index, line_idx)
        else:
            self.tab_widget.bookmark_mgr.remove_bookmark(tab_index, line_idx)

        # Force repaint to show bookmark indicators
        text_widget.viewport().update()

        # Update status if tab exists
        if self.commit_msg_tab:
            self.commit_msg_tab.update_status()

    def update_status(self):
        """Update status bar - delegates to commit message tab if it exists"""
        if self.commit_msg_tab:
            self.commit_msg_tab.update_status()

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
