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
from PyQt6.QtGui import QFont, QPalette, QKeySequence, QShortcut
import color_palettes


def is_dark_mode(palette):
    """
    Detect if the system is in dark mode by checking palette brightness.
    
    Args:
        palette: QPalette to check
        
    Returns:
        True if dark mode is detected, False otherwise
    """
    # First check macOS dark mode
    if color_palettes.is_macos_dark_mode():
        return True
    
    # For other platforms, check window background brightness
    bg_color = palette.color(QPalette.ColorRole.Window)
    # Calculate perceived brightness (0-255)
    brightness = (0.299 * bg_color.red() + 
                  0.587 * bg_color.green() + 
                  0.114 * bg_color.blue())
    # If brightness is less than 128, consider it dark mode
    return brightness < 128


class ShortcutsDialog(QDialog):
    """Dialog that displays a quick reference card for keyboard shortcuts"""
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Keyboard Shortcuts Reference")
        self.setMinimumSize(900, 700)
        
        layout = QVBoxLayout(self)
        
        shortcuts_text = QTextEdit()
        shortcuts_text.setReadOnly(True)
        
        # Detect dark mode and generate appropriate HTML
        is_dark = is_dark_mode(self.palette())
        shortcuts_text.setHtml(self.get_shortcuts_html(is_dark))
        
        self.current_font_size = 10
        font = QFont()
        font.setPointSize(self.current_font_size)
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
        
        # Setup font size shortcuts
        self.setup_font_shortcuts()
    
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
    
    def setup_font_shortcuts(self):
        """Setup keyboard shortcuts for font size adjustment"""
        # Ctrl++ or Ctrl+=
        increase_shortcut = QShortcut(QKeySequence("Ctrl++"), self)
        increase_shortcut.activated.connect(self.increase_font_size)
        increase_shortcut2 = QShortcut(QKeySequence("Ctrl+="), self)
        increase_shortcut2.activated.connect(self.increase_font_size)
        
        # Ctrl+-
        decrease_shortcut = QShortcut(QKeySequence("Ctrl+-"), self)
        decrease_shortcut.activated.connect(self.decrease_font_size)
        
        # Ctrl+0
        reset_shortcut = QShortcut(QKeySequence("Ctrl+0"), self)
        reset_shortcut.activated.connect(self.reset_font_size)
        
        # Add Cmd shortcuts for macOS
        # Cmd++ or Cmd+=
        cmd_increase_shortcut = QShortcut(QKeySequence("Meta++"), self)
        cmd_increase_shortcut.activated.connect(self.increase_font_size)
        cmd_increase_shortcut2 = QShortcut(QKeySequence("Meta+="), self)
        cmd_increase_shortcut2.activated.connect(self.increase_font_size)
        
        # Cmd+-
        cmd_decrease_shortcut = QShortcut(QKeySequence("Meta+-"), self)
        cmd_decrease_shortcut.activated.connect(self.decrease_font_size)
        
        # Cmd+0
        cmd_reset_shortcut = QShortcut(QKeySequence("Meta+0"), self)
        cmd_reset_shortcut.activated.connect(self.reset_font_size)
    
    def increase_font_size(self):
        """Increase font size (max 24pt)"""
        if self.current_font_size < 24:
            self.current_font_size += 1
            self.update_font_size()
    
    def decrease_font_size(self):
        """Decrease font size (min 6pt)"""
        if self.current_font_size > 6:
            self.current_font_size -= 1
            self.update_font_size()
    
    def reset_font_size(self):
        """Reset font size to default (12pt)"""
        self.current_font_size = 12
        self.update_font_size()
    
    def update_font_size(self):
        """Apply current font size to the text widget"""
        font = self.shortcuts_text.font()
        font.setPointSize(self.current_font_size)
        self.shortcuts_text.setFont(font)
    
    @staticmethod
    def get_shortcuts_html(is_dark):
        """
        Returns the HTML content for the shortcuts reference.
        
        Args:
            is_dark: True if dark mode is detected, False for light mode
            
        Returns:
            HTML string with appropriate color scheme
        """
        if is_dark:
            # Dark mode colors
            bg_color = "#2b2b2b"
            text_color = "#e0e0e0"
            header_color = "#6ba3d8"
            header_border = "#4a7ba7"
            table_header_bg = "#3a3a3a"
            table_border = "#555555"
            cell_border = "#444444"
            shortcut_bg = "#404040"
            shortcut_text = "#ffffff"
            note_color = "#a0a0a0"
        else:
            # Light mode colors
            bg_color = "#ffffff"
            text_color = "#000000"
            header_color = "#2c5aa0"
            header_border = "#2c5aa0"
            table_header_bg = "#e8f0f8"
            table_border = "#cccccc"
            cell_border = "#dddddd"
            shortcut_bg = "#f5f5f5"
            shortcut_text = "#000000"
            note_color = "#666666"
        
        return f"""
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                background-color: {bg_color};
                color: {text_color};
            }}
            h2 {{ 
                color: {header_color}; 
                border-bottom: 2px solid {header_border}; 
                padding-bottom: 5px; 
                margin-top: 20px; 
            }}
            table {{ 
                width: 100%; 
                border-collapse: collapse; 
                margin-bottom: 15px; 
            }}
            th {{ 
                background-color: {table_header_bg}; 
                text-align: left; 
                padding: 8px; 
                font-weight: bold; 
                border: 1px solid {table_border}; 
                color: {text_color};
            }}
            td {{ 
                padding: 6px 8px; 
                border: 1px solid {cell_border}; 
            }}
            .shortcut {{ 
                font-family: 'Courier New', monospace; 
                background-color: {shortcut_bg}; 
                color: {shortcut_text};
                padding: 2px 6px; 
                border-radius: 3px; 
                white-space: nowrap; 
                font-weight: bold; 
            }}
            .mac-note {{ 
                color: {note_color}; 
                font-style: italic; 
                font-size: 0.9em; 
                margin-top: 5px; 
            }}
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
                <td><span class="shortcut">Right-click -> Take Note</span></td>
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
                <td><span class="shortcut">Ctrl+H</span></td>
                <td>Toggle diff map</td>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+L</span></td>
                <td>Toggle line numbers</td>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+T</span></td>
                <td>Toggle tab character highlighting</td>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+E</span></td>
                <td>Toggle trailing whitespace highlighting</td>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+I</span></td>
                <td>Toggle intraline changes</td>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+R</span></td>
                <td>Toggle auto-reload files</td>
            </tr>
            <tr>
                <td><span class="shortcut">Ctrl+Y</span></td>
                <td>Cycle stats display (None -> Tabs Only -> Sidebar Only)</td>
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
                <td><span class="shortcut">Right-click -> Search</span></td>
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
        <strong>Mac Users:</strong> On macOS, all <span class="shortcut">Ctrl</span> shortcuts 
        work with <span class="shortcut">Cmd</span> instead. For example, <span class="shortcut">Ctrl+H</span> 
        becomes <span class="shortcut">Cmd+H</span>.
        </p>
        """
