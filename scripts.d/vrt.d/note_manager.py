# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Note manager for diff_review

This module manages all note-taking functionality:
- Review Notes tab creation and display
- Note file watching and auto-reload
- Note taking with standardized format
- Jump to Note functionality
- Yellow highlighting coordination
"""
from PyQt6.QtWidgets import (QPlainTextEdit, QPushButton, QMessageBox, QMenu,
                              QFileDialog)
from PyQt6.QtCore import Qt, QFileSystemWatcher, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QColor, QTextCharFormat

from utils import extract_display_path
from tab_content_base import TabContentBase
from commit_msg_handler import CommitMessageTab


class ReviewNotesTabBase(TabContentBase):
    """
    Abstract base class for review notes tabs.

    Subclasses include:
    - ReviewNotesTab: Uses QPlainTextEdit
    - VimNotesTab: Uses external vim editor (future)
    - EmacsNotesTab: Uses external emacs editor (future)
    """

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
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_notes)

        # Connect text changes to auto-save timer
        self.textChanged.connect(self._on_text_changed)

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

    def reset_font_size(self):
        """Reset font size to default (12pt)"""
        self.current_font_size = 12
        font = self.font()
        font.setPointSize(self.current_font_size)
        self.setFont(font)

    def toggle_bookmark(self):
        """Toggle bookmark - not supported for review notes"""
        pass

    def focus_content(self):
        """Set Qt focus to self (ReviewNotesTab is itself the text widget)"""
        self.setFocus()

    def save_buffer(self):
        """Review notes tabs have nothing to save"""
        pass

    def reload(self):
        """Reload notes from file, prompting if there are unsaved changes"""
        if self.has_unsaved_changes():
            reply = QMessageBox.question(
                self,
                'Unsaved Changes',
                'You have unsaved changes. Discard them and reload from file?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        notes_text = self.note_manager.load_note_text()
        self.setPlainText(notes_text)
        self._has_unsaved_changes = False
        self.original_content = notes_text

    def keyPressEvent(self, event):
        """Handle key press events - most handled by tab_manager keybindings now"""
        # All key handling now goes through tab_manager's keybinding system
        # Pass to parent to allow normal text editing behavior
        super().keyPressEvent(event)

    def search_content(self, search_text, case_sensitive, regex, search_base=True, search_modi=True):
        """
        Search for text in review notes.

        Returns:
            List of tuples: (side, display_line_num, line_idx, line_text, char_pos)
        """
        results = []
        text = self.toPlainText()
        lines = text.split('\n')
        
        for line_idx, line_text in enumerate(lines):
            # Find matches using same logic as search dialog
            matches = self._find_matches_in_line(line_text, search_text, case_sensitive, regex)
            for char_pos, matched_text in matches:
                results.append(('review_notes', line_idx + 1, line_idx, line_text, char_pos))
        
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


class NoteManager:
    """Manages all note-taking functionality across the application"""
    
    def __init__(self, tab_widget, note_file):
        """
        Initialize note manager
        
        Args:
            tab_widget: Reference to DiffViewerTabWidget
            note_file: Path to note file (from command line), or None
        """
        self.tab_widget = tab_widget
        self.note_file = note_file
        self.notes_button = None
        self.note_file_watcher = None
        self.reload_timer = None
        self.editor_class = tab_widget.editor_class
        self.editor_theme = tab_widget.editor_theme

    def is_builtin_editor(self, text_widget):
        """Check if the widget is the built-in editor (not external emacs/vim)"""
        return isinstance(text_widget, ReviewNotesTab)
    
    def get_note_file(self):
        """Get the current note file path"""
        if self.note_file:
            return self.note_file
        
        if self.tab_widget.global_note_file:
            return self.tab_widget.global_note_file
        
        viewers = self.tab_widget.get_all_viewers()
        for viewer in viewers:
            if viewer.note_file:
                return viewer.note_file
        return None
    
    def prompt_for_note_file(self):
        """
        Prompt user to select a note file.
        Returns the file path if selected, None if cancelled.
        Sets the global note file in tab_widget.
        """
        file_dialog = QFileDialog(self.tab_widget)
        file_dialog.setWindowTitle("Select Note File")
        file_dialog.setNameFilter("Text Files (*.txt);;All Files (*)")
        file_dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        file_dialog.setOption(QFileDialog.Option.DontConfirmOverwrite, True)
        file_dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)

        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            files = file_dialog.selectedFiles()
            if files:
                note_file = files[0]
                self.set_note_file(note_file)
                return note_file

        return None
    
    def set_note_file(self, note_file):
        """Set the note file globally across all viewers"""
        self.note_file = note_file
        self.tab_widget.global_note_file = note_file

        # Update all existing viewers
        for viewer in self.tab_widget.get_all_viewers():
            viewer.note_file = note_file
            viewer.update_status()

        # Update commit message tab note file if it exists
        from commit_msg_handler import CommitMessageTab
        for i in range(self.tab_widget.tab_widget.count()):
            widget = self.tab_widget.tab_widget.widget(i)
            if isinstance(widget, CommitMessageTab):
                widget.note_file = note_file
        
        # Update commit message handler status (which updates the labels)
        if self.tab_widget.commit_msg_mgr:
            self.tab_widget.commit_msg_mgr.update_status()

        # Update button text to show the new note file
        self.update_notes_button_text()
        
        # Set up file watching for auto-reload
        self.setup_note_file_watcher(note_file)
        
        # Show the Review Notes button if not already visible
        if not self.notes_button:
            self.create_notes_button()
    
    def update_notes_button_text(self):
        """Update the Review Notes button text"""
        if not self.notes_button:
            return

        self.notes_button.setText("Review Notes")

    def create_notes_button(self):
        """Create the Review Notes button in the sidebar (after Open All Files)"""
        self.notes_button = QPushButton("Review Notes")
        self.notes_button.clicked.connect(self.on_notes_clicked)
        self.notes_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 8px 8px 20px;
                border: none;
                background-color: #f0f8ff;
                border-left: 4px solid transparent;
                font-weight: bold;
                color: #1e90ff;
            }
            QPushButton:hover {
                background-color: #e0f0ff;
            }
        """)

        # Insert at position 1 (after "Open All Files" which is at position 0)
        self.tab_widget.sidebar_widget.add_notes_button(self.notes_button)

        # Update button text to show note file if already set
        self.update_notes_button_text()

        # Update "Open All Files" count to include review notes
        self.tab_widget.update_open_all_button_text()
    
    def on_notes_clicked(self):
        """Handle Review Notes button click"""
        # Check if tab already exists
        if 'review_notes' in self.tab_widget.file_to_tab_index:
            tab_index = self.tab_widget.file_to_tab_index['review_notes']
            if 0 <= tab_index < self.tab_widget.tab_widget.count():
                self.tab_widget.tab_widget.setCurrentIndex(tab_index)
                return
            # Tab was closed, remove from mapping
            del self.tab_widget.file_to_tab_index['review_notes']
        
        # Create new Review Notes tab
        self.create_notes_tab()

    def load_note_text(self):
        """Load note file text and return as string"""
        note_file = self.get_note_file()
        if not note_file:
            return "# No note file configured\n"

        try:
            with open(note_file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return "# No notes yet\n"
        except Exception as e:
            return f"# Error reading note file:\n# {e}\n"
    
    def create_notes_tab(self):
        """Create a tab displaying the review notes"""
        note_file = self.get_note_file()
        if not note_file:
            QMessageBox.information(self.tab_widget, 'No Note File',
                                  'No note file has been configured yet.')
            return

        # Check if using external editor
        if self.editor_class is not None:
            # Use external editor widget (emacs or vim)
            text_widget = self.editor_class(self.tab_widget, self.editor_theme, note_file)
            text_widget.is_review_notes = True

            # Connect subprocess exit signal to tab closure handler
            text_widget.process_exited.connect(self.tab_widget.handle_editor_subprocess_exit)

            # Add to tabs with note file path as title
            index = self.tab_widget.tab_widget.addTab(text_widget, note_file)
            self.tab_widget.file_to_tab_index['review_notes'] = index
            self.tab_widget.tab_widget.setCurrentIndex(index)

            # Update button state
            self.tab_widget.update_button_states()
            return

        # Use built-in editor (original behavior)
        notes_text = self.load_note_text()

        # Create review notes tab widget
        text_widget = ReviewNotesTab(notes_text, self)

        # Set up context menu
        text_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        text_widget.customContextMenuRequested.connect(
            lambda pos: self.show_notes_context_menu(pos, text_widget))

        # Install event filter for keyboard shortcuts
        text_widget.installEventFilter(self.tab_widget)

        # Add to tabs with note file path as title
        index = self.tab_widget.tab_widget.addTab(text_widget, note_file)
        self.tab_widget.file_to_tab_index['review_notes'] = index
        self.tab_widget.tab_widget.setCurrentIndex(index)

        # Update button state
        self.tab_widget.update_button_states()
    
    def show_notes_context_menu(self, pos, text_widget):
        """Show context menu for review notes tab"""
        menu = QMenu(self.tab_widget)
        
        cursor = text_widget.textCursor()
        has_selection = cursor.hasSelection()
        
        search_action = menu.addAction("Search")
        search_action.setEnabled(has_selection)
        if has_selection:
            search_action.triggered.connect(
                lambda: self.tab_widget.search_selected_text(text_widget))
        
        menu.exec(text_widget.mapToGlobal(pos))
    
    def save_notes_content(self, text_widget):
        """Save the notes content to file"""
        # External editors (emacs/vim) save on their own
        if not self.is_builtin_editor(text_widget):
            return

        note_file = self.get_note_file()
        if not note_file:
            return

        try:
            content = text_widget.toPlainText()

            # Temporarily disable file watcher to avoid triggering reload
            if self.note_file_watcher:
                self.note_file_watcher.blockSignals(True)

            # Write to file
            with open(note_file, 'w', encoding='utf-8') as f:
                f.write(content)

            # Update tracking via tab's method
            text_widget.mark_saved()

            # Re-enable file watcher
            if self.note_file_watcher:
                self.note_file_watcher.blockSignals(False)

        except Exception as e:
            QMessageBox.warning(self.tab_widget, 'Save Error',
                              f'Could not save notes file:\n{e}')
    
    def update_notes_tab_title(self, text_widget, dirty):
        """Update the tab title to show dirty state"""
        # External editors don't show dirty state in tab title
        if not self.is_builtin_editor(text_widget):
            return

        note_file = self.get_note_file()
        if not note_file:
            return

        # Find the tab index
        if 'review_notes' not in self.tab_widget.file_to_tab_index:
            return

        tab_index = self.tab_widget.file_to_tab_index['review_notes']
        if not (0 <= tab_index < self.tab_widget.tab_widget.count()):
            return

        # Update title with asterisk if dirty
        if dirty:
            self.tab_widget.tab_widget.setTabText(tab_index, f"*{note_file}")
        else:
            self.tab_widget.tab_widget.setTabText(tab_index, note_file)
    
    def setup_note_file_watcher(self, note_file):
        """Set up file system watching for the note file"""
        import os
        
        # Clean up existing watcher if any
        if self.note_file_watcher:
            self.note_file_watcher.deleteLater()
            self.note_file_watcher = None
        
        if self.reload_timer:
            self.reload_timer.stop()
            self.reload_timer = None
        
        # Create new watcher
        self.note_file_watcher = QFileSystemWatcher()
        
        # Add the file to watch (create if it doesn't exist)
        if os.path.exists(note_file):
            self.note_file_watcher.addPath(note_file)
        else:
            # Create empty file so watcher can track it
            try:
                with open(note_file, 'a', encoding='utf-8'):
                    pass
                self.note_file_watcher.addPath(note_file)
            except Exception:
                pass  # If we can't create it, we'll add it later
        
        self.note_file_watcher.fileChanged.connect(self.on_note_file_changed)
        
        # Create debounce timer
        self.reload_timer = QTimer()
        self.reload_timer.setSingleShot(True)
        self.reload_timer.timeout.connect(self.reload_notes_tab)
    
    def on_note_file_changed(self, path):
        """Handle note file change notification"""
        # Restart debounce timer
        if self.reload_timer:
            self.reload_timer.stop()
            self.reload_timer.start(500)  # 500ms debounce
        
        # Schedule a re-watch check to ensure we stay connected
        # Some editors remove and recreate files, breaking the watch
        QTimer.singleShot(1000, self.ensure_file_watched)
    
    def ensure_file_watched(self):
        """Ensure the note file is still being watched (re-add if needed)"""
        import os
        
        note_file = self.get_note_file()
        if not note_file or not self.note_file_watcher:
            return
        
        watched = self.note_file_watcher.files()
        if note_file not in watched and os.path.exists(note_file):
            try:
                self.note_file_watcher.addPath(note_file)
            except Exception:
                pass
    
    def reload_notes_tab(self):
        """Reload the Review Notes tab content"""
        note_file = self.get_note_file()
        if not note_file:
            return
        
        # Find the review notes tab
        if 'review_notes' not in self.tab_widget.file_to_tab_index:
            return
        
        tab_index = self.tab_widget.file_to_tab_index['review_notes']
        if not (0 <= tab_index < self.tab_widget.tab_widget.count()):
            return
        
        text_widget = self.tab_widget.tab_widget.widget(tab_index)
        if not isinstance(text_widget, ReviewNotesTab):
            return
        
        # Check if there are unsaved changes
        if text_widget.has_unsaved_changes():
            # Show conflict dialog
            reply = QMessageBox.question(
                self.tab_widget,
                'File Changed Externally',
                'The note file has changed on disk, but you have unsaved edits.\n\n'
                'Do you want to reload from disk (losing your changes) or keep editing?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                # User wants to keep editing - don't reload
                return
        
        # Save scroll position and cursor position
        v_scroll_pos = text_widget.verticalScrollBar().value()
        cursor_pos = text_widget.textCursor().position()
        
        # Reload content
        try:
            with open(note_file, 'r', encoding='utf-8') as f:
                notes_text = f.read()
            
            # Block signals to avoid triggering auto-save
            text_widget.blockSignals(True)
            text_widget.setPlainText(notes_text)
            text_widget.blockSignals(False)

            # Mark as saved
            text_widget.mark_saved()
            
            # Restore cursor position
            cursor = text_widget.textCursor()
            cursor.setPosition(min(cursor_pos, len(notes_text)))
            text_widget.setTextCursor(cursor)
            
            # Restore scroll position
            text_widget.verticalScrollBar().setValue(v_scroll_pos)
            
        except Exception as e:
            # If file doesn't exist or can't be read, show error in the tab
            text_widget.blockSignals(True)
            text_widget.setPlainText(f"# Error reading note file:\n# {e}\n")
            text_widget.blockSignals(False)
        
        # Re-add file to watcher (some editors remove and recreate files)
        # This is critical - without it, we lose watching after first edit
        if self.note_file_watcher:
            watched = self.note_file_watcher.files()
            if note_file not in watched:
                try:
                    self.note_file_watcher.addPath(note_file)
                except Exception:
                    # File might not exist yet, watcher will pick it up later
                    pass
    
    def take_note(self, file_path, side, line_numbers, line_texts, is_commit_msg=False):
        """
        Write a note to the note file with standardized format.
        
        Args:
            file_path: Source file path (or "Commit Message")
            side: 'base', 'modified', or 'commit_msg'
            line_numbers: List of line numbers, or (start, end) tuple for commit message
            line_texts: List of line text content
            is_commit_msg: True if this is from commit message
            
        Returns:
            True if note was taken, False if cancelled
        """
        # Get or prompt for note file
        note_file = self.get_note_file()
        if not note_file:
            note_file = self.prompt_for_note_file()
            if not note_file:
                return False
        
        try:
            with open(note_file, 'a', encoding='utf-8') as f:
                if is_commit_msg:
                    # Commit message format with line range [start, end)
                    start_line, end_line = line_numbers
                    f.write(f"> (commit_msg): Commit Message:[{start_line},{end_line})\n")
                    for line_text in line_texts:
                        f.write(f">   {line_text}\n")
                else:
                    # Source file format with range
                    prefix = '(base)' if side == 'base' else '(modi)'
                    clean_filename = extract_display_path(file_path)
                    
                    # Calculate range [start, end)
                    start_line = line_numbers[0]
                    end_line = line_numbers[-1] + 1
                    
                    f.write(f"> {prefix}: {clean_filename}:[{start_line},{end_line})\n")
                    for line_num, line_text in zip(line_numbers, line_texts):
                        f.write(f">   {line_num}: {line_text}\n")
                
                f.write('>\n\n\n')
            
            # Switch to notes tab immediately after taking note
            self.on_notes_clicked()

            return True
            
        except Exception as e:
            QMessageBox.warning(self.tab_widget, 'Error Taking Note',
                              f'Could not write to note file:\n{e}')
            return False
    
    def show_jump_to_note_menu(self, pos, text_widget, side, viewer):
        """
        Add 'Jump to Note' to context menu for yellow highlighted lines.
        
        Args:
            pos: Mouse position
            text_widget: The text widget (base_text or modified_text)
            side: 'base' or 'modified'
            viewer: The DiffViewer instance
        """
        # Get the line under cursor
        cursor = text_widget.cursorForPosition(pos)
        line_idx = cursor.blockNumber()
        
        # Check if this line has a note (yellow highlighting)
        line_nums = viewer.base_line_nums if side == 'base' else viewer.modified_line_nums
        noted_lines = viewer.base_noted_lines if side == 'base' else viewer.modified_noted_lines
        
        if line_idx >= len(line_nums):
            return None
        
        line_num = line_nums[line_idx]
        if line_num is None or line_num not in noted_lines:
            return None
        
        # This line has a note - return the action
        return lambda: self.jump_to_note(viewer.base_file if side == 'base' else viewer.modified_file,
                                         side, line_num, viewer)
    
    def show_jump_to_note_menu_commit_msg(self, pos, text_widget):
        """
        Check if commit message line has a note and return jump action if it does.
        
        Args:
            pos: Mouse position
            text_widget: The commit message text widget
            
        Returns:
            Callable to jump to note, or None if no note exists for this line
        """
        # Get the line under cursor
        cursor = text_widget.cursorForPosition(pos)
        line_idx = cursor.blockNumber()
        
        # Check if this line has yellow highlighting (indicating a note was taken)
        block = text_widget.document().findBlockByNumber(line_idx)
        if not block.isValid():
            return None
        
        # Check for yellow background format
        cursor_check = QTextCursor(block)
        cursor_check.movePosition(cursor_check.MoveOperation.StartOfBlock)
        cursor_check.movePosition(cursor_check.MoveOperation.EndOfBlock, cursor_check.MoveMode.KeepAnchor)
        
        char_format = cursor_check.charFormat()
        bg_color = char_format.background().color()
        
        # Check if it's yellow (RGB: 255, 255, 200 - light yellow)
        if bg_color.red() > 200 and bg_color.green() > 200 and bg_color.blue() > 150:
            # This line has a note - return the jump action
            return lambda: self.jump_to_note_commit_msg(line_idx)
        
        return None
    
    def jump_to_note_commit_msg(self, line_idx):
        """
        Jump to the note for a specific line in the commit message.
        
        Args:
            line_idx: Line index in the commit message display
        """
        note_file = self.get_note_file()
        if not note_file:
            return
        
        # Get the commit message tab
        commit_msg_widget = None
        if 'commit_msg' in self.tab_widget.file_to_tab_index:
            commit_msg_tab_index = self.tab_widget.file_to_tab_index['commit_msg']
            if 0 <= commit_msg_tab_index < self.tab_widget.tab_widget.count():
                widget = self.tab_widget.tab_widget.widget(commit_msg_tab_index)
                if isinstance(widget, CommitMessageTab):
                    commit_msg_widget = widget
        
        if not commit_msg_widget:
            return
        
        # Search for the note
        try:
            with open(note_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return
        
        # Parse to find the note containing this line index
        lines = content.split('\n')
        found_line_idx = None
        note_end_idx = None
        
        for i, line in enumerate(lines):
            if line.startswith("> (commit_msg): Commit Message:"):
                # Extract range [start,end)
                if ':[' in line:
                    range_part = line.split(':[')[1].split(')')[0]
                    try:
                        start, end = map(int, range_part.split(','))
                        if start <= line_idx < end:
                            found_line_idx = i
                            # Find the end of this note (blank line with just '>')
                            for j in range(i + 1, len(lines)):
                                if lines[j].strip() == '>':
                                    note_end_idx = j
                                    break
                            break
                    except (ValueError, IndexError):
                        continue
        
        if found_line_idx is None:
            # Note not found - remove yellow highlighting from this line
            block = commit_msg_widget.text_widget.document().findBlockByNumber(line_idx)
            if block.isValid():
                cursor = QTextCursor(block)
                cursor.movePosition(cursor.MoveOperation.StartOfBlock)
                cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
                
                # Clear the background by setting a format with no background
                char_format = QTextCharFormat()
                char_format.clearBackground()
                cursor.mergeCharFormat(char_format)
            
            QMessageBox.information(self.tab_widget, 'Note Not Found',
                                  'The note for this line was not found in the note file.\n'
                                  'The highlighting has been removed.')
            return
        
        # Open or switch to review notes tab
        self.on_notes_clicked()
        
        # Navigate to the found line
        if 'review_notes' in self.tab_widget.file_to_tab_index:
            review_notes_tab_index = self.tab_widget.file_to_tab_index['review_notes']
            if 0 <= review_notes_tab_index < self.tab_widget.tab_widget.count():
                notes_widget = self.tab_widget.tab_widget.widget(review_notes_tab_index)
                
                # Move cursor to the line
                cursor = notes_widget.textCursor()
                cursor.movePosition(cursor.MoveOperation.Start)
                for _ in range(found_line_idx):
                    cursor.movePosition(cursor.MoveOperation.Down)
                
                # Select the entire note section (from header to blank '>' line)
                cursor.movePosition(cursor.MoveOperation.StartOfBlock)
                end_cursor = notes_widget.textCursor()
                end_cursor.movePosition(end_cursor.MoveOperation.Start)
                if note_end_idx is not None:
                    for _ in range(note_end_idx):
                        end_cursor.movePosition(end_cursor.MoveOperation.Down)
                    end_cursor.movePosition(end_cursor.MoveOperation.EndOfBlock)
                else:
                    end_cursor.movePosition(end_cursor.MoveOperation.End)
                
                cursor.setPosition(end_cursor.position(), cursor.MoveMode.KeepAnchor)
                notes_widget.setTextCursor(cursor)
                notes_widget.ensureCursorVisible()

    
    def jump_to_note(self, file_path, side, line_num, viewer):
        """
        Jump to the note for a specific file and line number.
        
        Args:
            file_path: Source file path
            side: 'base' or 'modified'
            line_num: Line number to search for
            viewer: The DiffViewer instance (to remove highlighting if note not found)
        """
        note_file = self.get_note_file()
        if not note_file:
            QMessageBox.warning(self.tab_widget, 'Error',
                              'No note file has been configured.')
            return
        
        # Search for the note
        try:
            with open(note_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            QMessageBox.warning(self.tab_widget, 'Error',
                              f'Could not read note file:\n{e}')
            return
        
        # Parse to find the note
        clean_filename = extract_display_path(file_path)
        prefix = '(base)' if side == 'base' else '(modi)'
        
        # Search for header line containing this file and line number
        lines = content.split('\n')
        found_line_idx = None
        note_end_idx = None
        
        for i, line in enumerate(lines):
            if line.startswith(f"> {prefix}: {clean_filename}:"):
                # Extract range [start,end)
                if ':[' in line:
                    range_part = line.split(':[')[1].split(')')[0]
                    try:
                        start, end = map(int, range_part.split(','))
                        if start <= line_num < end:
                            found_line_idx = i
                            # Find the end of this note (blank line with just '>')
                            for j in range(i + 1, len(lines)):
                                if lines[j].strip() == '>':
                                    note_end_idx = j
                                    break
                            break
                    except (ValueError, IndexError):
                        continue
        
        # Open or switch to Review Notes tab
        self.on_notes_clicked()
        
        # Get the Review Notes tab widget
        if 'review_notes' not in self.tab_widget.file_to_tab_index:
            QMessageBox.warning(self.tab_widget, 'Error',
                              'Could not open Review Notes tab.')
            return
        
        tab_index = self.tab_widget.file_to_tab_index['review_notes']
        if not (0 <= tab_index < self.tab_widget.tab_widget.count()):
            QMessageBox.warning(self.tab_widget, 'Error',
                              'Review Notes tab index is invalid.')
            return
        
        text_widget = self.tab_widget.tab_widget.widget(tab_index)
        if not (isinstance(text_widget, ReviewNotesTab) or
                getattr(text_widget, 'is_review_notes', False)):
            QMessageBox.warning(self.tab_widget, 'Error',
                              'Review Notes tab has unexpected type.')
            return
        
        if found_line_idx is not None:
            # Note found - highlight it
            cursor = text_widget.textCursor()
            
            # Move to start of note header
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            for _ in range(found_line_idx):
                cursor.movePosition(QTextCursor.MoveOperation.Down)
            
            # Select to end of note (or end of doc if no end found)
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            if note_end_idx:
                for _ in range(found_line_idx, note_end_idx + 1):
                    cursor.movePosition(QTextCursor.MoveOperation.Down,
                                      QTextCursor.MoveMode.KeepAnchor)
            else:
                # No end found, select just the header and first few lines
                for _ in range(5):
                    cursor.movePosition(QTextCursor.MoveOperation.Down,
                                      QTextCursor.MoveMode.KeepAnchor)
            
            text_widget.setTextCursor(cursor)
            text_widget.centerCursor()
        else:
            # Note not found - position cursor at top
            cursor = text_widget.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            text_widget.setTextCursor(cursor)
            
            # Remove highlighting
            if side == 'base':
                viewer.base_noted_lines.discard(line_num)
                # Remove yellow highlighting from display
                for i, num in enumerate(viewer.base_line_nums):
                    if num == line_num:
                        # Clear the noted line marking
                        if hasattr(viewer.base_text, 'noted_lines'):
                            viewer.base_text.noted_lines.discard(i)
                        viewer.base_text.viewport().update()
                        viewer.base_line_area.noted_lines.discard(i)
                        viewer.base_line_area.update()
            else:
                viewer.modified_noted_lines.discard(line_num)
                # Remove yellow highlighting from display
                for i, num in enumerate(viewer.modified_line_nums):
                    if num == line_num:
                        # Clear the noted line marking
                        if hasattr(viewer.modified_text, 'noted_lines'):
                            viewer.modified_text.noted_lines.discard(i)
                        viewer.modified_text.viewport().update()
                        viewer.modified_line_area.noted_lines.discard(i)
                        viewer.modified_line_area.update()
    
    def update_button_state(self, is_open, is_active):
        """Update Review Notes button style based on state"""
        if not self.notes_button:
            return
        
        if is_active:
            # Currently selected - bright highlight
            self.notes_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 8px 8px 20px;
                    border: none;
                    background-color: #b0d4ff;
                    border-left: 6px solid #1e90ff;
                    font-weight: bold;
                    color: #1e90ff;
                }
                QPushButton:hover {
                    background-color: #a0c4ef;
                }
            """)
        elif is_open:
            # Open but not selected - subtle highlight
            self.notes_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 8px 8px 20px;
                    border: none;
                    background-color: #e0f0ff;
                    border-left: 4px solid #1e90ff;
                    font-weight: bold;
                    color: #1e90ff;
                }
                QPushButton:hover {
                    background-color: #d0e0ef;
                }
            """)
        else:
            # Closed - no highlight
            self.notes_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 8px 8px 20px;
                    border: none;
                    background-color: #f0f8ff;
                    border-left: 4px solid transparent;
                    font-weight: bold;
                    color: #1e90ff;
                }
                QPushButton:hover {
                    background-color: #e0f0ff;
                }
            """)
