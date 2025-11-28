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
from PyQt6.QtWidgets import QPlainTextEdit, QMenu, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCharFormat, QColor


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
        self.tab_widget.button_layout.insertWidget(1, self.commit_msg_button)
    
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
    
    def create_commit_msg_tab(self):
        """Create a tab displaying the commit message"""
        commit_msg_text = self.tab_widget.afr_.read(self.commit_msg_rel_path)

        # The afr_.read() will return the lines as an array of
        # non-'\n' strings.  The setPlainText() function seems to need
        # a single string.  So, for this special case, put the lines
        # back together.
        commit_msg_text = '\n'.join(commit_msg_text)
        
        # Create text widget
        text_widget = QPlainTextEdit()
        text_widget.setReadOnly(True)
        text_widget.setPlainText(commit_msg_text)
        text_widget.setFont(QFont("Courier", 12, QFont.Weight.Bold))
        
        # Style commit message with subtle sepia tone
        text_widget.setStyleSheet("""
            QPlainTextEdit {
                background-color: #fdf6e3;
                color: #5c4a3a;
            }
        """)
        
        # Set up context menu
        text_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        text_widget.customContextMenuRequested.connect(
            lambda pos: self.show_commit_msg_context_menu(pos, text_widget))
        
        # Install event filter for keyboard shortcuts
        text_widget.installEventFilter(self.tab_widget)
        
        # Store reference to tab widget for later use
        text_widget.is_commit_msg = True
        
        # Add to tabs
        index = self.tab_widget.tab_widget.addTab(text_widget, "Commit Message")
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
        
        menu.exec(text_widget.mapToGlobal(pos))
    
    def take_commit_msg_note(self, text_widget):
        """Take note from commit message"""
        cursor = text_widget.textCursor()
        if not cursor.hasSelection():
            return
        
        # Get note file - prompt if not configured
        note_file = self.tab_widget.get_note_file()
        if not note_file:
            note_file = self.prompt_for_note_file()
            if not note_file:
                return
        
        # Save selection range before doing anything
        selection_start = cursor.selectionStart()
        selection_end = cursor.selectionEnd()
        
        selected_text = cursor.selectedText()
        selected_text = selected_text.replace('\u2029', '\n')
        
        try:
            with open(note_file, 'a', encoding='utf-8') as f:
                f.write("> (commit_msg): Commit Message\n")
                for line in selected_text.split('\n'):
                    f.write(f">   {line}\n")
                f.write('>\n\n\n')
            
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
        except Exception as e:
            QMessageBox.warning(self.tab_widget, 'Error Taking Note',
                              f'Could not write to note file:\n{e}')
    
    def prompt_for_note_file(self):
        """
        Prompt user to select a note file.
        Returns the file path if selected, None if cancelled.
        Also sets the global note file in tab_widget.
        """
        from PyQt6.QtWidgets import QFileDialog
        
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
                # Set global note file
                self.tab_widget.global_note_file = note_file
                # Update all existing viewers
                for viewer in self.tab_widget.get_all_viewers():
                    viewer.note_file = note_file
                    viewer.update_status()
                return note_file
        
        return None
    
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
