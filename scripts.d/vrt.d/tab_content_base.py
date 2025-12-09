# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Tab content base classes for diff_review

This module defines the base class hierarchy for all tab content types:
- TabContentBase: Abstract base for all tabs
- CommitMessageTab: Commit message display tab
- ReviewNotesTabBase: Base for review notes tabs (built-in, vim, emacs)
- DiffViewerTab: Wrapper for diff viewer (future)
"""
from PyQt6.QtWidgets import QPlainTextEdit, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPainter


class TabContentBase:
    """
    Abstract base class for all tab content types.

    All tab widgets must inherit from this to provide a consistent interface
    for font management, type identification, and state queries.
    """

    def get_tab_type(self):
        """
        Return the type identifier for this tab.

        Returns:
            str: One of 'commit_msg', 'review_notes', 'diff_viewer'
        """
        raise NotImplementedError("Subclasses must implement get_tab_type()")

    def increase_font_size(self):
        """Increase font size - default implementation does nothing"""
        pass

    def decrease_font_size(self):
        """Decrease font size - default implementation does nothing"""
        pass

    def has_unsaved_changes(self):
        """
        Check if tab has unsaved changes.

        Returns:
            bool: True if there are unsaved changes, False otherwise
        """
        return False


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

    def get_tab_type(self):
        """Return tab type identifier"""
        return 'commit_msg'

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


class ReviewNotesTabBase(TabContentBase):
    """
    Abstract base class for review notes tabs.

    Subclasses include:
    - BuiltInNotesTab: Uses QPlainTextEdit
    - VimNotesTab: Uses external vim editor
    - EmacsNotesTab: Uses external emacs editor
    """

    def get_tab_type(self):
        """Return tab type identifier"""
        return 'review_notes'

    def center_cursor(self):
        """Center cursor in view - must be implemented by subclass"""
        pass

    def has_unsaved_changes(self):
        """Check for unsaved changes - must be implemented by subclass"""
        return False


class ReviewNotesTab(QPlainTextEdit, ReviewNotesTabBase):
    """
    Built-in review notes tab using QPlainTextEdit.

    This is an editable view of the notes file with auto-save,
    ASCII filtering, and context menu support.
    """

    def __init__(self, notes_text, note_manager):
        """
        Initialize review notes tab.

        Args:
            notes_text: The initial notes text to display
            note_manager: Reference to NoteManager for saving and operations
        """
        super().__init__()
        self.note_manager = note_manager
        self.current_font_size = 12
        self._has_unsaved_changes = False
        self.original_content = notes_text

        # Configure as editable
        self.setReadOnly(False)
        self.setPlainText(notes_text)
        self.setFont(QFont("Courier", self.current_font_size, QFont.Weight.Bold))

        # Style with light blue tone
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #f5f9ff;
                color: #2c3e50;
            }
        """)

        # Create auto-save timer
        from PyQt6.QtCore import QTimer
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_notes)

        # Connect text changes to auto-save timer
        self.textChanged.connect(self._on_text_changed)

    def get_tab_type(self):
        """Return tab type identifier"""
        return 'review_notes'

    def increase_font_size(self):
        """Increase font size in review notes"""
        self.current_font_size += 1
        font = self.font()
        font.setPointSize(self.current_font_size)
        self.setFont(font)

    def decrease_font_size(self):
        """Decrease font size in review notes"""
        if self.current_font_size > 6:
            self.current_font_size -= 1
            font = self.font()
            font.setPointSize(self.current_font_size)
            self.setFont(font)

    def center_cursor(self):
        """Center the cursor in the view"""
        cursor = self.textCursor()
        self.setTextCursor(cursor)
        self.centerCursor()

    def has_unsaved_changes(self):
        """Check if there are unsaved changes"""
        return self._has_unsaved_changes

    def _on_text_changed(self):
        """Handle text changes - filter ASCII and trigger auto-save"""
        # Filter out non-ASCII characters
        cursor_pos = self.textCursor().position()
        text = self.toPlainText()

        # Filter to ASCII only
        filtered_text = ''.join(char for char in text if ord(char) < 128)

        if filtered_text != text:
            # Non-ASCII characters were present - replace text
            self.blockSignals(True)
            self.setPlainText(filtered_text)
            # Restore cursor position (adjusted for removed chars)
            new_cursor = self.textCursor()
            new_cursor.setPosition(min(cursor_pos, len(filtered_text)))
            self.setTextCursor(new_cursor)
            self.blockSignals(False)

        # Mark as having unsaved changes
        if not self._has_unsaved_changes:
            self._has_unsaved_changes = True
            self.note_manager.update_notes_tab_title(self, dirty=True)

        # Restart auto-save timer (2.5 seconds)
        self.save_timer.stop()
        self.save_timer.start(2500)

    def _save_notes(self):
        """Save notes content via note manager"""
        self.note_manager.save_notes_content(self)

    def mark_saved(self):
        """Mark the notes as saved (called by note manager)"""
        self._has_unsaved_changes = False
        self.original_content = self.toPlainText()
        self.note_manager.update_notes_tab_title(self, dirty=False)
