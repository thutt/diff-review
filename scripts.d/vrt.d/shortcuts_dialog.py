# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Keyboard shortcuts reference dialog for diff_review

This module contains a compact, scannable cheat sheet of all keyboard shortcuts.
"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class ShortcutsDialog(QDialog):
    """Dialog that displays a quick reference card for keyboard shortcuts"""
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Keyboard Shortcuts Reference")
        self.setMinimumSize(900, 700)
        
        layout = QVBoxLayout(self)
        
        shortcuts_text = QTextEdit()
        shortcuts_text.setReadOnly(True)
        shortcuts_text.setHtml(self.get_shortcuts_html())
        
        font = QFont()
        font.setPointSize(10)
        shortcuts_text.setFont(font)
        
        layout.addWidget(shortcuts_text)
        
        button_layout = QHBoxLayout()
        
        print_button = QPushButton("Print / Save PDF")
        print_button.clicked.connect(self.print_shortcuts)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)
        
        button_layout.addWidget(print_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        self.shortcuts_text = shortcuts_text
    
    def print_shortcuts(self):
        """Print or save shortcuts as PDF"""
        from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
        from PyQt6.QtGui import QPageLayout, QPageSize
        
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        page_layout = QPageLayout()
        page_layout.setOrientation(QPageLayout.Orientation.Portrait)
        page_layout.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
        printer.setPageLayout(page_layout)
        
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.shortcuts_text.document().print(printer)
    
    @staticmethod
    def get_shortcuts_html():
        """Returns the HTML content for the shortcuts reference"""
        return """
        <style>
            body { font-family: Arial, sans-serif; }
            h2 { color: #2c5aa0; border-bottom: 2px solid #2c5aa0; padding-bottom: 5px; margin-top: 20px; }
            table { width: 100%; border-collapse: collapse; margin-bottom: 15px; }
            th { background-color: #e8f0f8; text-align: left; padding: 8px; font-weight: bold; border: 1px solid #ccc; }
            td { padding: 6px 8px; border: 1px solid #ddd; }
            .shortcut { font-family: 'Courier New', monospace; background-color: #f5f5f5; 
                       padding: 2px 6px; border-radius: 3px; white-space: nowrap; font-weight: bold; }
            .mac-note { color: #666; font-style: italic; font-size: 0.9em; margin-top: 5px; }
        </style>
        
        <h2>Essential Shortcuts</h2>
        <table>
            <tr>
                <th width="30%">Shortcut</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><span class="shortcut">N</span></td>
                <td>Next change region</td>
            </tr>
            <tr>
                <td><span class="shortcut">P</span></td>
                <td>Previous change region</td>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+F</span> or <span class="shortcut">Ctrl+S</span></td>
                <td>Open search dialog</td>
            </tr>
            <tr>
                <td><span class="shortcut">F3</span> / <span class="shortcut">Shift+F3</span></td>
                <td>Find next / previous match</td>
            </tr>
            <tr>
                <td><span class="shortcut">M</span></td>
                <td>Toggle bookmark on current line</td>
            </tr>
            <tr>
                <td><span class="shortcut">[</span> / <span class="shortcut">]</span></td>
                <td>Previous / next bookmark</td>
            </tr>
        </table>
        
        <h2>File & Tab Management</h2>
        <table>
            <tr>
                <th width="30%">Shortcut</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+Tab</span></td>
                <td>Next tab</td>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+Shift+Tab</span></td>
                <td>Previous tab</td>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+W</span></td>
                <td>Close current tab</td>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+Q</span></td>
                <td>Quit application</td>
            </tr>
            <tr>
                <td><span class="shortcut">F5</span></td>
                <td>Reload current file</td>
            </tr>
            <tr>
                <td><span class="shortcut">Escape</span></td>
                <td>Close application</td>
            </tr>
        </table>
        
        <h2>Navigation</h2>
        <table>
            <tr>
                <th width="30%">Shortcut</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><span class="shortcut">Arrow Keys</span></td>
                <td>Navigate up/down/left/right</td>
            </tr>
            <tr>
                <td><span class="shortcut">PageUp</span> / <span class="shortcut">PageDown</span></td>
                <td>Scroll ~10 lines</td>
            </tr>
            <tr>
                <td><span class="shortcut">Space</span></td>
                <td>Page down</td>
            </tr>
            <tr>
                <td><span class="shortcut">Shift+Space</span></td>
                <td>Page up</td>
            </tr>
            <tr>
                <td><span class="shortcut">Home</span> / <span class="shortcut">End</span></td>
                <td>Jump to start/end of file</td>
            </tr>
            <tr>
                <td><span class="shortcut">Tab</span></td>
                <td>Switch focus between base and modified panes</td>
            </tr>
            <tr>
                <td><span class="shortcut">C</span></td>
                <td>Center on current region</td>
            </tr>
            <tr>
                <td><span class="shortcut">T</span></td>
                <td>Jump to top of file</td>
            </tr>
            <tr>
                <td><span class="shortcut">B</span></td>
                <td>Jump to bottom of file</td>
            </tr>
        </table>
        
        <h2>Notes & Annotations</h2>
        <table>
            <tr>
                <th width="30%">Shortcut</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><span class="shortcut">Double-click</span></td>
                <td>Quick note - add clicked line to notes file</td>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+N</span></td>
                <td>Take note of selected text</td>
            </tr>
            <tr>
                <td><span class="shortcut">Right-click → Take Note</span></td>
                <td>Add selected text to notes file</td>
            </tr>
        </table>
        
        <h2>View Options</h2>
        <table>
            <tr>
                <th width="30%">Shortcut</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+B</span></td>
                <td>Toggle sidebar visibility</td>
            </tr>
            <tr>
                <td><span class="shortcut">Alt+H</span></td>
                <td>Toggle diff map</td>
            </tr>
            <tr>
                <td><span class="shortcut">Alt+L</span></td>
                <td>Toggle line numbers</td>
            </tr>
            <tr>
                <td><span class="shortcut">Alt+T</span></td>
                <td>Toggle tab character highlighting</td>
            </tr>
            <tr>
                <td><span class="shortcut">Alt+W</span></td>
                <td>Toggle trailing whitespace highlighting</td>
            </tr>
            <tr>
                <td><span class="shortcut">Alt+I</span></td>
                <td>Toggle intraline changes</td>
            </tr>
            <tr>
                <td><span class="shortcut">Alt+R</span></td>
                <td>Toggle auto-reload files</td>
            </tr>
        </table>
        
        <h2>Search & Find</h2>
        <table>
            <tr>
                <th width="30%">Shortcut</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+F</span> or <span class="shortcut">Ctrl+S</span></td>
                <td>Open search dialog</td>
            </tr>
            <tr>
                <td><span class="shortcut">F3</span></td>
                <td>Find next match</td>
            </tr>
            <tr>
                <td><span class="shortcut">Shift+F3</span></td>
                <td>Find previous match</td>
            </tr>
            <tr>
                <td><span class="shortcut">Right-click → Search</span></td>
                <td>Search for selected text</td>
            </tr>
        </table>
        
        <h2>Font Size</h2>
        <table>
            <tr>
                <th width="30%">Shortcut</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl++</span></td>
                <td>Increase font size (max 24pt)</td>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+-</span></td>
                <td>Decrease font size (min 6pt)</td>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+0</span></td>
                <td>Reset font size to default (12pt)</td>
            </tr>
        </table>
        
        <p class="mac-note">
        <strong>Mac Users:</strong> On macOS, <span class="shortcut">Cmd</span> can be used instead of 
        <span class="shortcut">Ctrl</span> for most shortcuts. <span class="shortcut">Cmd</span> can also 
        replace <span class="shortcut">Alt</span> for view options when using VNC.
        </p>
        """
