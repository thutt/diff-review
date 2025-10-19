#!/usr/bin/env python3
# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Help dialog for diff_review

This module contains the help dialog that displays user documentation.
"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton


class HelpDialog(QDialog):
    """Dialog that displays help documentation for the diff viewer"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Diff Viewer - How to Use")
        self.setMinimumSize(700, 600)
        
        layout = QVBoxLayout(self)
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml(self.get_help_html())
        
        layout.addWidget(help_text)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
    
    @staticmethod
    def get_help_html():
        """Returns the HTML content for the help dialog"""
        return """
        <h2>Diff Viewer - User Guide</h2>
        
        <h3>Overview</h3>
        <p>This diff viewer displays side-by-side comparison of two files with synchronized scrolling and highlighting of changes.</p>
        
        <h3>Navigation</h3>
        <ul>
            <li><b>Arrow Keys:</b> Navigate up/down/left/right</li>
            <li><b>Tab:</b> Switch focus between base and modified panes</li>
            <li><b>N:</b> Jump to next change region</li>
            <li><b>P:</b> Jump to previous change region</li>
            <li><b>C:</b> Center on the currently selected region</li>
            <li><b>T:</b> Jump to top of file</li>
            <li><b>B:</b> Jump to bottom of file</li>
            <li><b>Escape:</b> Close the viewer</li>
        </ul>
        
        <h3>Color Coding</h3>
        <ul>
            <li><b>Light Green:</b> Added lines or content</li>
            <li><b>Light Red/Pink:</b> Deleted lines or content</li>
            <li><b>Yellow:</b> Modified content within a line (intraline changes)</li>
            <li><b>Dark Gray:</b> Lines that don't exist in one version (placeholder lines)</li>
        </ul>
        
        <h3>Search Functionality</h3>
        <ul>
            <li><b>Ctrl+S:</b> Open search dialog to search across base, modified, and commit message files</li>
            <li><b>Right-click → Search:</b> Search for currently selected text</li>
            <li>Use checkboxes in search dialog to choose which sources to search (Base/Modi/Desc)</li>
            <li>Toggle case sensitivity in search dialog</li>
            <li>Double-click search results to jump to that location</li>
        </ul>
        
        <h3>Note Taking</h3>
        <ul>
            <li><b>Double-click:</b> Quick note - adds the clicked line to your notes file</li>
            <li><b>Right-click → Take Note:</b> Add selected text to notes file</li>
            <li><b>Ctrl+N:</b> Take note of selected text (works in commit message view too)</li>
            <li>Notes are marked with a blue dot in the line number area</li>
            <li>All notes are appended to the notes file specified at startup</li>
        </ul>
        
        <h3>Diff Map</h3>
        <ul>
            <li>Vertical bar on the right shows overview of all changes in the file</li>
            <li><b>Red:</b> Deletions</li>
            <li><b>Green:</b> Insertions</li>
            <li><b>Yellow:</b> Modifications</li>
            <li><b>Blue rectangle:</b> Current viewport position</li>
            <li><b>Click on diff map:</b> Jump to that location in the file</li>
            <li><b>Alt+H:</b> Toggle diff map visibility</li>
        </ul>
        
        <h3>Line Numbers</h3>
        <ul>
            <li>Shows original line numbers from each file</li>
            <li>Background colors indicate changed lines (pink for base, light green for modified)</li>
            <li>Blue dots mark lines you've taken notes on</li>
            <li><b>Alt+L:</b> Toggle line number visibility</li>
        </ul>
        
        <h3>Status Bar</h3>
        <ul>
            <li><b>Region:</b> Shows current change region number and total regions</li>
            <li><b>Commit Message:</b> Button to view commit message (if available)</li>
            <li><b>Notes:</b> Count of notes taken during this session</li>
        </ul>
        
        <h3>Commit Message View</h3>
        <ul>
            <li>Click "Commit Message" button to view commit message</li>
            <li>Search and note-taking work the same way in commit message view</li>
            <li>Ctrl+S and Ctrl+N shortcuts work in commit message window</li>
        </ul>
        """
