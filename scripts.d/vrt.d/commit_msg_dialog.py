#!/usr/bin/env python3
"""
Commit Message dialog for diff_review

This module contains the dialog for viewing commit messages.
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QPlainTextEdit, QPushButton, 
                              QMenu, QMessageBox)
from PyQt6.QtCore import Qt, QObject
from PyQt6.QtGui import QFont, QFontMetrics, QAction, QTextCursor

from search_dialogs import SearchDialog, SearchResultDialog


class CommitMsgDialog(QDialog):
    """Dialog for viewing and interacting with commit messages"""
    
    def __init__(self, commit_msg_file, parent_viewer, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.commit_msg_file = commit_msg_file
        self.parent_viewer = parent_viewer
        
        self.setWindowTitle("Commit Message")
        
        # Read commit message file
        try:
            with open(commit_msg_file, 'r') as f:
                commit_msg_text = f.read()
        except Exception as e:
            QMessageBox.warning(self, 'Error Reading Commit Message',
                              f'Could not read commit message file:\n{e}')
            return
        
        # Setup font and size
        font = QFont("Courier", 12, QFont.Weight.Bold)
        fm = QFontMetrics(font)
        char_width = fm.horizontalAdvance('0')
        
        dialog_width = (100 * char_width) + 40
        dialog_height = 500
        
        self.resize(dialog_width, dialog_height)
        
        # Create text area
        self.commit_msg_text_area = QPlainTextEdit()
        self.commit_msg_text_area.setReadOnly(True)
        self.commit_msg_text_area.setPlainText(commit_msg_text)
        self.commit_msg_text_area.setFont(font)
        
        # Setup context menu
        self.commit_msg_text_area.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.commit_msg_text_area.customContextMenuRequested.connect(self.show_context_menu)
        
        # Install event filter for keyboard shortcuts
        event_filter = CommitMsgEventFilter(self, self.show_search_dialog, self.take_note)
        self.commit_msg_text_area.installEventFilter(event_filter)
        self.installEventFilter(event_filter)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.commit_msg_text_area)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
    
    def show_context_menu(self, pos):
        """Show context menu for commit message text area"""
        menu = QMenu(self)
        cursor = self.commit_msg_text_area.textCursor()
        has_selection = cursor.hasSelection()
        
        search_action = QAction("Search", self)
        search_action.setEnabled(has_selection)
        if has_selection:
            search_action.triggered.connect(self.search_selected_text)
        menu.addAction(search_action)
        
        menu.addSeparator()
        
        if has_selection and self.parent_viewer.note_file:
            note_action = QAction("Take Note", self)
            note_action.triggered.connect(self.take_note)
            menu.addAction(note_action)
        else:
            note_action = QAction("Take Note (no selection)" if self.parent_viewer.note_file else 
                               "Take Note (no file supplied)", self)
            note_action.setEnabled(False)
            menu.addAction(note_action)
        
        menu.exec(self.commit_msg_text_area.mapToGlobal(pos))
    
    def show_search_dialog(self):
        """Show search dialog"""
        search_dialog = SearchDialog(self, has_commit_msg=True)
        if search_dialog.exec() == QDialog.DialogCode.Accepted and search_dialog.search_text:
            results_dialog = SearchResultDialog(search_dialog.search_text, self.parent_viewer, 
                                               search_dialog.case_sensitive,
                                               search_dialog.search_base,
                                               search_dialog.search_modi,
                                               search_dialog.search_desc)
            results_dialog.exec()
    
    def search_selected_text(self):
        """Search for selected text"""
        cursor = self.commit_msg_text_area.textCursor()
        if not cursor.hasSelection():
            return
        
        search_text = cursor.selectedText()
        dialog = SearchResultDialog(search_text, self.parent_viewer, case_sensitive=False,
                                   search_base=True, search_modi=True, search_desc=True)
        dialog.exec()
    
    def take_note(self):
        """Take note from selected text"""
        if not self.parent_viewer.note_file:
            QMessageBox.information(self, 'Note Taking Disabled',
                                  'No note file supplied.')
            return
        
        cursor = self.commit_msg_text_area.textCursor()
        if not cursor.hasSelection():
            return
        
        selected_text = cursor.selectedText()
        selected_text = selected_text.replace('\u2029', '\n')
        
        with open(self.parent_viewer.note_file, 'a') as f:
            f.write("(desc): Commit Message\n")
            for line in selected_text.split('\n'):
                f.write(f"  {line}\n")
            f.write('\n')
        
        self.parent_viewer.note_count += 1
        self.parent_viewer.update_status()
    
    def select_line(self, line_idx):
        """Select and highlight a specific line in the commit message"""
        cursor = self.commit_msg_text_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        
        for _ in range(line_idx):
            cursor.movePosition(QTextCursor.MoveOperation.Down)
        
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        
        self.commit_msg_text_area.setTextCursor(cursor)
        self.commit_msg_text_area.centerCursor()
        
        self.raise_()
        self.activateWindow()


class CommitMsgEventFilter(QObject):
    """Event filter for keyboard shortcuts in commit message dialog"""
    
    def __init__(self, parent, search_func, note_func):
        super().__init__(parent)
        self.search_func = search_func
        self.note_func = note_func
    
    def eventFilter(self, obj, event):
        if event.type() == event.Type.KeyPress:
            if (event.key() == Qt.Key.Key_S and 
                event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                self.search_func()
                return True
            elif (event.key() == Qt.Key.Key_N and 
                  event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                cursor = obj.textCursor() if hasattr(obj, 'textCursor') else None
                if cursor and not cursor.hasSelection():
                    cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, 
                                      QTextCursor.MoveMode.KeepAnchor)
                    obj.setTextCursor(cursor)
                self.note_func()
                return True
        return False
