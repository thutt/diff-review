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


class NoteManager:
    """Manages all note-taking functionality across the application"""
    
    def __init__(self, tab_widget):
        """
        Initialize note manager
        
        Args:
            tab_widget: Reference to DiffViewerTabWidget
        """
        self.tab_widget = tab_widget
        self.notes_button = None
        self.note_file_watcher = None
        self.reload_timer = None
    
    def get_note_file(self):
        """Get the current note file path"""
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
        self.tab_widget.global_note_file = note_file
        
        # Update all existing viewers
        for viewer in self.tab_widget.get_all_viewers():
            viewer.note_file = note_file
            viewer.update_status()
        
        # Set up file watching for auto-reload
        self.setup_note_file_watcher(note_file)
        
        # Show the Review Notes button if not already visible
        if not self.notes_button:
            self.create_notes_button()
    
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
        self.tab_widget.button_layout.insertWidget(1, self.notes_button)
    
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
    
    def create_notes_tab(self):
        """Create a tab displaying the review notes"""
        note_file = self.get_note_file()
        if not note_file:
            QMessageBox.information(self.tab_widget, 'No Note File',
                                  'No note file has been configured yet.')
            return
        
        # Read note file content
        try:
            with open(note_file, 'r', encoding='utf-8') as f:
                notes_text = f.read()
        except FileNotFoundError:
            notes_text = "# No notes yet\n"
        except Exception as e:
            notes_text = f"# Error reading note file:\n# {e}\n"
        
        # Create text widget
        text_widget = QPlainTextEdit()
        text_widget.setReadOnly(True)
        text_widget.setPlainText(notes_text)
        text_widget.setFont(QFont("Courier", 12, QFont.Weight.Bold))
        
        # Style with light blue tone
        text_widget.setStyleSheet("""
            QPlainTextEdit {
                background-color: #f5f9ff;
                color: #2c3e50;
            }
        """)
        
        # Set up context menu
        text_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        text_widget.customContextMenuRequested.connect(
            lambda pos: self.show_notes_context_menu(pos, text_widget))
        
        # Install event filter for keyboard shortcuts
        text_widget.installEventFilter(self.tab_widget)
        
        # Store reference to tab widget for later use
        text_widget.is_review_notes = True
        
        # Add to tabs
        index = self.tab_widget.tab_widget.addTab(text_widget, "Review Notes")
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
        if not (hasattr(text_widget, 'is_review_notes') and text_widget.is_review_notes):
            return
        
        # Save scroll position
        v_scroll_pos = text_widget.verticalScrollBar().value()
        
        # Reload content
        try:
            with open(note_file, 'r', encoding='utf-8') as f:
                notes_text = f.read()
            text_widget.setPlainText(notes_text)
            
            # Restore scroll position
            text_widget.verticalScrollBar().setValue(v_scroll_pos)
            
        except Exception as e:
            # If file doesn't exist or can't be read, show error in the tab
            text_widget.setPlainText(f"# Error reading note file:\n# {e}\n")
        
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
            line_numbers: List of line numbers (or None for commit message)
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
                    # Commit message format (no line numbers)
                    f.write("> (commit_msg): Commit Message\n")
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
            return
        
        # Search for the note
        try:
            with open(note_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return
        
        # Parse to find the note
        clean_filename = extract_display_path(file_path)
        prefix = '(base)' if side == 'base' else '(modi)'
        
        # Search for header line containing this file and line number
        lines = content.split('\n')
        found_line_idx = None
        
        for i, line in enumerate(lines):
            if line.startswith(f"> {prefix}: {clean_filename}:"):
                # Extract range [start,end)
                if ':[' in line:
                    range_part = line.split(':[')[1].split(')')[0]
                    try:
                        start, end = map(int, range_part.split(','))
                        if start <= line_num < end:
                            found_line_idx = i
                            break
                    except (ValueError, IndexError):
                        continue
        
        if found_line_idx is not None:
            # Note found - open/switch to Review Notes tab and center on it
            self.on_notes_clicked()  # This will open or switch to the tab
            
            # Get the Review Notes tab widget
            if 'review_notes' in self.tab_widget.file_to_tab_index:
                tab_index = self.tab_widget.file_to_tab_index['review_notes']
                text_widget = self.tab_widget.tab_widget.widget(tab_index)
                
                if hasattr(text_widget, 'is_review_notes') and text_widget.is_review_notes:
                    # Move cursor to the found line
                    cursor = text_widget.textCursor()
                    cursor.movePosition(QTextCursor.MoveOperation.Start)
                    for _ in range(found_line_idx):
                        cursor.movePosition(QTextCursor.MoveOperation.Down)
                    
                    text_widget.setTextCursor(cursor)
                    text_widget.centerCursor()
        else:
            # Note not found - remove highlighting and show dialog
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
            
            # Show dialog
            QMessageBox.information(
                self.tab_widget,
                'Note Deleted',
                f'The note for line {line_num} has been deleted from the note file.\n\n'
                'The highlighting has been removed.'
            )
    
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
