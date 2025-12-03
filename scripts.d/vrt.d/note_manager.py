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
- Terminal editor integration
"""
import os
import subprocess
import sys
import signal
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
        self.terminal_editor_button = None
        self.note_file_watcher = None
        self.reload_timer = None
        self.terminal_process = None
    
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
        
        # Show the Terminal Editor button if not already visible
        if not self.terminal_editor_button:
            self.create_terminal_editor_button()
    
    def create_notes_button(self):
        """Create the Review Notes button in the sidebar (after Open All Files)"""
        self.notes_button = QPushButton("Review Notes in vrt")
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
        
        # Update "Open All Files" count to include review notes
        self.tab_widget.update_open_all_button_text()
    
    def create_terminal_editor_button(self):
        """Create the Terminal Editor button in the sidebar (after Review Notes)"""
        editor = os.environ.get('EDITOR', 'EDITOR')
        self.terminal_editor_button = QPushButton(f"Review Notes using {editor}")
        self.terminal_editor_button.clicked.connect(self.on_terminal_editor_clicked)
        self.terminal_editor_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px 8px 8px 20px;
                border: none;
                background-color: #f0fff0;
                border-left: 4px solid transparent;
                font-weight: bold;
                color: #228b22;
            }
            QPushButton:hover {
                background-color: #e0ffe0;
            }
        """)
        
        # This will be inserted after Review Notes button
        self.tab_widget.sidebar_widget.add_terminal_editor_button(self.terminal_editor_button)
        
        # Update "Open All Files" count to include terminal editor
        self.tab_widget.update_open_all_button_text()
    
    def cleanup_terminal_process(self):
        """Kill terminal subprocess and its children"""
        if self.terminal_process is None:
            return
        
        try:
            if sys.platform.startswith('linux') or sys.platform == 'darwin':
                # Get the process group and kill all processes in it
                try:
                    pgid = os.getpgid(self.terminal_process.pid)
                    os.killpg(pgid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            
            # Also try direct termination
            try:
                self.terminal_process.terminate()
                self.terminal_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.terminal_process.kill()
            except ProcessLookupError:
                pass
        except Exception:
            pass
        
        self.terminal_process = None
    
    def on_terminal_editor_clicked(self):
        """Handle Terminal Editor button click - opens editor in external terminal"""
        self.create_terminal_editor_tab()
    
    def create_terminal_editor_tab(self):
        """Open the note file in ${EDITOR} in an external terminal window"""
        note_file = self.get_note_file()
        if not note_file:
            QMessageBox.information(self.tab_widget, 'No Note File',
                                  'No note file has been configured yet.')
            return
        
        # Get editor from environment, fallback to existing Review Notes functionality
        editor = os.environ.get('EDITOR')
        
        if not editor:
            # No EDITOR set - just open regular Review Notes tab
            QMessageBox.information(
                self.tab_widget,
                'No EDITOR Set',
                'The EDITOR environment variable is not set.\n\n'
                'Opening the built-in Review Notes editor instead.'
            )
            self.on_notes_clicked()
            return
        
        # Clean up any existing terminal process
        self.cleanup_terminal_process()
        
        try:
            if sys.platform == 'darwin':
                # macOS - use Terminal.app, create minimized window
                script = f'''tell application "Terminal"
    do script "{editor} {note_file}"
    tell front window
        set miniaturized to true
    end tell
end tell'''
                proc = subprocess.Popen(['osascript', '-e', script],
                                      start_new_session=True,
                                      stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL)
                self.terminal_process = proc
            elif sys.platform.startswith('linux'):
                # Linux - try common terminals in order
                # Use xterm with -iconic which actually works
                terminals = [
                    ['xterm', '-iconic', '-e', editor, note_file],
                    ['gnome-terminal', '--', editor, note_file],
                    ['konsole', '-e', editor, note_file],
                    ['x-terminal-emulator', '-e', editor, note_file],
                ]
                
                launched = False
                for term_cmd in terminals:
                    try:
                        proc = subprocess.Popen(term_cmd,
                                              start_new_session=True,
                                              stdout=subprocess.DEVNULL,
                                              stderr=subprocess.DEVNULL)
                        self.terminal_process = proc
                        launched = True
                        break
                    except FileNotFoundError:
                        continue
                
                if not launched:
                    QMessageBox.warning(
                        self.tab_widget,
                        'No Terminal Found',
                        'Could not find a terminal emulator.\n\n'
                        'Opening the built-in Review Notes editor instead.'
                    )
                    self.on_notes_clicked()
                    return
            else:
                # Windows or unknown platform
                QMessageBox.information(
                    self.tab_widget,
                    'Platform Not Supported',
                    'External terminal editor is not supported on this platform.\n\n'
                    'Opening the built-in Review Notes editor instead.'
                )
                self.on_notes_clicked()
                return
            
            # Show brief message
            self.tab_widget.statusBar().showMessage(
                f'Opened {os.path.basename(note_file)} in {editor}', 
                3000
            )
            
        except Exception as e:
            QMessageBox.warning(
                self.tab_widget,
                'Error Opening Editor',
                f'Could not open external editor:\n{e}\n\n'
                'Opening the built-in Review Notes editor instead.'
            )
            self.on_notes_clicked()

    
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
        """Create a new Review Notes tab"""
        note_file = self.get_note_file()
        if not note_file:
            note_file = self.prompt_for_note_file()
            if not note_file:
                return
        
        # Create text widget for notes
        text_widget = QPlainTextEdit()
        text_widget.setReadOnly(True)
        text_widget.is_review_notes = True
        
        font = QFont("Courier", 10)
        text_widget.setFont(font)
        
        # Load content
        if os.path.exists(note_file):
            try:
                with open(note_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                text_widget.setPlainText(content)
            except Exception as e:
                text_widget.setPlainText(f"Error loading note file: {e}")
        else:
            text_widget.setPlainText("Note file does not exist yet.\n\nTake a note to create it.")
        
        # Add tab
        tab_name = "Review Notes"
        tab_index = self.tab_widget.tab_widget.addTab(text_widget, tab_name)
        self.tab_widget.file_to_tab_index['review_notes'] = tab_index
        self.tab_widget.tab_widget.setCurrentIndex(tab_index)
    
    def setup_note_file_watcher(self, note_file):
        """Set up file system watcher for note file auto-reload"""
        # Clean up old watcher if it exists
        if self.note_file_watcher:
            self.note_file_watcher.deleteLater()
            self.note_file_watcher = None
        
        if self.reload_timer:
            self.reload_timer.stop()
            self.reload_timer.deleteLater()
            self.reload_timer = None
        
        # Create new watcher
        self.note_file_watcher = QFileSystemWatcher([note_file], self.tab_widget)
        self.note_file_watcher.fileChanged.connect(self.on_note_file_changed)
        
        # Create debounce timer
        self.reload_timer = QTimer(self.tab_widget)
        self.reload_timer.setSingleShot(True)
        self.reload_timer.timeout.connect(self.reload_notes_tab)
    
    def on_note_file_changed(self, path):
        """Handle note file change - debounced reload"""
        # Re-add the watch (some editors remove and recreate files)
        if path not in self.note_file_watcher.files():
            if os.path.exists(path):
                self.note_file_watcher.addPath(path)
        
        # Start/restart debounce timer
        self.reload_timer.start(500)  # 500ms debounce
    
    def on_notes_text_changed(self):
        """Handle text changes in Review Notes tab"""
        # This tab is read-only, so this shouldn't be called
        pass
    
    def reload_notes_tab(self):
        """Reload the Review Notes tab content"""
        if 'review_notes' not in self.tab_widget.file_to_tab_index:
            return
        
        tab_index = self.tab_widget.file_to_tab_index['review_notes']
        if tab_index < 0 or tab_index >= self.tab_widget.tab_widget.count():
            return
        
        text_widget = self.tab_widget.tab_widget.widget(tab_index)
        if not text_widget:
            return
        
        note_file = self.get_note_file()
        if not note_file or not os.path.exists(note_file):
            return
        
        # Save cursor position
        cursor = text_widget.textCursor()
        pos = cursor.position()
        
        # Reload content
        try:
            with open(note_file, 'r', encoding='utf-8') as f:
                content = f.read()
            text_widget.setPlainText(content)
            
            # Restore cursor position
            cursor = text_widget.textCursor()
            cursor.setPosition(min(pos, len(content)))
            text_widget.setTextCursor(cursor)
            
        except Exception:
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
        note_file = self.get_note_file()
        if not note_file:
            note_file = self.prompt_for_note_file()
            if not note_file:
                return False
        
        try:
            with open(note_file, 'a', encoding='utf-8') as f:
                if is_commit_msg:
                    f.write("> (commit_msg): Commit Message\n")
                    for line_text in line_texts:
                        f.write(f">   {line_text}\n")
                else:
                    prefix = '(base)' if side == 'base' else '(modi)'
                    clean_filename = extract_display_path(file_path)
                    
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
        
        if found_line_idx is not None:
            # Note found - open/switch to Review Notes tab and highlight it
            self.on_notes_clicked()  # This will open or switch to the tab
            
            # Get the Review Notes tab widget
            if 'review_notes' in self.tab_widget.file_to_tab_index:
                tab_index = self.tab_widget.file_to_tab_index['review_notes']
                text_widget = self.tab_widget.tab_widget.widget(tab_index)
                
                if text_widget.is_review_notes:
                    # Select the entire note for visual feedback
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
                        for _ in range(5):  # Select ~5 lines
                            cursor.movePosition(QTextCursor.MoveOperation.Down,
                                              QTextCursor.MoveMode.KeepAnchor)
                    
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
