# Copyright (c) 2025, 2026  Logic Magicians Software (Taylor Hutt).
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
import sys
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

    def __init__(self, parent=None, keybindings=None, diff_keybindings=None,
                 commit_msg_keybindings=None, terminal_keybindings=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Keyboard Shortcuts Reference")
        self.setMinimumSize(900, 700)

        # Store keybindings for dynamic shortcut display
        self.keybindings = keybindings
        self.diff_keybindings = diff_keybindings
        self.commit_msg_keybindings = commit_msg_keybindings
        self.terminal_keybindings = terminal_keybindings
        
        layout = QVBoxLayout(self)
        
        shortcuts_text = QTextEdit()
        shortcuts_text.setReadOnly(True)
        
        # Detect dark mode and generate appropriate HTML
        is_dark = is_dark_mode(self.palette())
        shortcuts_text.setHtml(self.get_shortcuts_html(is_dark))
        
        self.current_font_size = 12
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
    
    def _get_shortcut_text(self, action_name, keybindings_obj):
        """Get formatted shortcut text for display.
        
        Args:
            action_name: Name of the action
            keybindings_obj: KeyBindings object to query
            
        Returns:
            Formatted string like 'Ctrl+B' or 'Cmd+B', or empty if no binding
        """
        if keybindings_obj is None:
            return ""
        
        sequences = keybindings_obj.get_sequences(action_name)
        if not sequences:
            return ""
        
        # Use the first sequence for display
        seq = sequences[0]
        parts = []
        
        from PyQt6.QtCore import Qt
        for qt_key, modifiers in seq.keys:
            key_parts = []
            
            # On macOS, show Cmd instead of Ctrl for Control modifier
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                if sys.platform == 'darwin':
                    key_parts.append("Cmd")
                else:
                    key_parts.append("Ctrl")
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                key_parts.append("Shift")
            if modifiers & Qt.KeyboardModifier.AltModifier:
                key_parts.append("Alt")
            if modifiers & Qt.KeyboardModifier.MetaModifier:
                # Meta is Cmd on macOS (already shown for Control)
                # On other platforms, show Meta
                if sys.platform != 'darwin':
                    key_parts.append("Meta")
            
            # Get key name
            key_name = self._qt_key_to_name(qt_key)
            key_parts.append(key_name)
            
            parts.append("+".join(key_parts))
        
        return " ".join(parts)
    
    def _qt_key_to_name(self, qt_key):
        """Convert Qt.Key enum to display string."""
        from PyQt6.QtCore import Qt
        
        # Map Qt.Key enums to display characters
        key_display_map = {
            # Symbols
            Qt.Key.Key_BracketLeft: '[',
            Qt.Key.Key_BracketRight: ']',
            Qt.Key.Key_Question: '?',
            Qt.Key.Key_Slash: '/',
            Qt.Key.Key_Backslash: '\\',
            Qt.Key.Key_Equal: '=',
            Qt.Key.Key_Minus: '-',
            Qt.Key.Key_Plus: '+',
            Qt.Key.Key_Asterisk: '*',
            Qt.Key.Key_Period: '.',
            Qt.Key.Key_Comma: ',',
            Qt.Key.Key_Semicolon: ';',
            Qt.Key.Key_Colon: ':',
            Qt.Key.Key_Apostrophe: "'",
            Qt.Key.Key_QuoteDbl: '"',
            Qt.Key.Key_Less: '<',
            Qt.Key.Key_Greater: '>',
            Qt.Key.Key_Exclam: '!',
            Qt.Key.Key_At: '@',
            Qt.Key.Key_NumberSign: '#',
            Qt.Key.Key_Dollar: '$',
            Qt.Key.Key_Percent: '%',
            Qt.Key.Key_AsciiCircum: '^',
            Qt.Key.Key_Ampersand: '&',
            Qt.Key.Key_ParenLeft: '(',
            Qt.Key.Key_ParenRight: ')',
            Qt.Key.Key_BraceLeft: '{',
            Qt.Key.Key_BraceRight: '}',
            Qt.Key.Key_Bar: '|',
            Qt.Key.Key_AsciiTilde: '~',
            Qt.Key.Key_QuoteLeft: '`',
            # Navigation and special keys
            Qt.Key.Key_Space: 'Space',
            Qt.Key.Key_Tab: 'Tab',
            Qt.Key.Key_Return: 'Return',
            Qt.Key.Key_Enter: 'Enter',
            Qt.Key.Key_Backspace: 'Backspace',
            Qt.Key.Key_Delete: 'Delete',
            Qt.Key.Key_Escape: 'Esc',
            Qt.Key.Key_Home: 'Home',
            Qt.Key.Key_End: 'End',
            Qt.Key.Key_PageUp: 'PageUp',
            Qt.Key.Key_PageDown: 'PageDown',
            Qt.Key.Key_Up: 'Up',
            Qt.Key.Key_Down: 'Down',
            Qt.Key.Key_Left: 'Left',
            Qt.Key.Key_Right: 'Right',
            Qt.Key.Key_Insert: 'Insert',
        }
        
        # Check if we have a direct mapping
        if qt_key in key_display_map:
            return key_display_map[qt_key]
        
        # Try to find the key name from Qt.Key enum
        for attr_name in dir(Qt.Key):
            if attr_name.startswith('Key_'):
                if getattr(Qt.Key, attr_name) == qt_key:
                    key_name = attr_name[4:]  # Strip 'Key_' prefix
                    # Lowercase single letter keys to match config file format
                    if len(key_name) == 1 and key_name.isalpha():
                        key_name = key_name.lower()
                    return key_name
        return f"Key_{qt_key}"
    
    def get_shortcuts_html(self, is_dark):
        """
        Returns the HTML content for the shortcuts reference.
        
        Args:
            is_dark: True if dark mode is detected, False for light mode
            
        Returns:
            HTML string with appropriate color scheme
        """
        # Detect platform and set modifier key name
        if sys.platform == 'darwin':
            mod_key = "Cmd"
        else:
            mod_key = "Ctrl"
        
        # Get shortcuts from keybindings
        close_tab = self._get_shortcut_text('close_tab', self.keybindings) or f"{mod_key}+w"
        quit_application = self._get_shortcut_text('quit_application', self.keybindings) or f"{mod_key}+q"
        search = self._get_shortcut_text('search', self.keybindings) or f"{mod_key}+f"
        find_next = self._get_shortcut_text('find_next', self.keybindings) or "F3"
        find_prev = self._get_shortcut_text('find_prev', self.keybindings) or "Shift+F3"
        toggle_sidebar = self._get_shortcut_text('toggle_sidebar', self.keybindings) or f"{mod_key}+b"
        toggle_focus_mode = self._get_shortcut_text('toggle_focus_mode', self.keybindings) or f"{mod_key}+\\"
        shortcuts_help = self._get_shortcut_text('shortcuts_help', self.keybindings) or "F1"
        increase_font = self._get_shortcut_text('increase_font', self.keybindings) or f"{mod_key}++"
        decrease_font = self._get_shortcut_text('decrease_font', self.keybindings) or f"{mod_key}+-"
        reset_font = self._get_shortcut_text('reset_font', self.keybindings) or f"{mod_key}+0"

        # Terminal editor shortcuts
        terminal_escape = self._get_shortcut_text('terminal_escape', self.terminal_keybindings) or f"{mod_key}+`"
        term_next_bookmark = self._get_shortcut_text('next_bookmark', self.terminal_keybindings) or "]"
        term_prev_bookmark = self._get_shortcut_text('prev_bookmark', self.terminal_keybindings) or "["
        
        # Diff viewer shortcuts
        next_change = self._get_shortcut_text('next_change', self.diff_keybindings) or "n"
        prev_change = self._get_shortcut_text('prev_change', self.diff_keybindings) or "p"
        top_of_file = self._get_shortcut_text('top_of_file', self.diff_keybindings) or "t"
        bottom_of_file = self._get_shortcut_text('bottom_of_file', self.diff_keybindings) or "b"
        toggle_bookmark = self._get_shortcut_text('toggle_bookmark', self.diff_keybindings) or "m"
        next_bookmark = self._get_shortcut_text('next_bookmark', self.diff_keybindings) or "]"
        prev_bookmark = self._get_shortcut_text('prev_bookmark', self.diff_keybindings) or "["
        center_region = self._get_shortcut_text('center_region', self.diff_keybindings) or "c"
        toggle_collapse = self._get_shortcut_text('toggle_collapse_region', self.diff_keybindings) or "x"
        toggle_collapse_all = self._get_shortcut_text('toggle_collapse_all', self.diff_keybindings) or "Shift+x"
        take_note = self._get_shortcut_text('take_note', self.diff_keybindings) or f"{mod_key}+n"
        jump_to_note = self._get_shortcut_text('jump_to_note', self.diff_keybindings) or f"{mod_key}+j"
        reload = self._get_shortcut_text('reload', self.diff_keybindings) or "F5"
        toggle_diff_map = self._get_shortcut_text('toggle_diff_map', self.diff_keybindings) or f"{mod_key}+h"
        toggle_line_numbers = self._get_shortcut_text('toggle_line_numbers', self.diff_keybindings) or f"{mod_key}+l"
        toggle_tab_highlight = self._get_shortcut_text('toggle_tab_highlight', self.diff_keybindings) or f"{mod_key}+t"
        toggle_eol = self._get_shortcut_text('toggle_eol_highlight', self.diff_keybindings) or f"{mod_key}+e"
        toggle_intraline = self._get_shortcut_text('toggle_intraline', self.diff_keybindings) or f"{mod_key}+i"
        
        # Commit message shortcuts
        cm_take_note = self._get_shortcut_text('take_note', self.commit_msg_keybindings) or f"{mod_key}+n"
        cm_jump_to_note = self._get_shortcut_text('jump_to_note', self.commit_msg_keybindings) or f"{mod_key}+j"
        cm_toggle_bookmark = self._get_shortcut_text('toggle_bookmark', self.commit_msg_keybindings) or "m"
        cm_next_bookmark = self._get_shortcut_text('next_bookmark', self.commit_msg_keybindings) or "]"
        cm_prev_bookmark = self._get_shortcut_text('prev_bookmark', self.commit_msg_keybindings) or "["
        
        # Optional/user-configured shortcuts (not in defaults)
        # These are shown only if configured by the user
        optional_shortcuts = {}
        
        # Check for cursor movement actions
        cursor_actions = ['cursor_up', 'cursor_down', 'cursor_left', 'cursor_right',
                         'cursor_pageup', 'cursor_pagedown', 'cursor_home', 'cursor_end']
        for action in cursor_actions:
            shortcut = self._get_shortcut_text(action, self.diff_keybindings)
            if shortcut:
                optional_shortcuts[action] = shortcut
        
        # Check for selection actions
        select_actions = ['select_up', 'select_down', 'select_left', 'select_right',
                         'select_pageup', 'select_pagedown']
        for action in select_actions:
            shortcut = self._get_shortcut_text(action, self.diff_keybindings)
            if shortcut:
                optional_shortcuts[action] = shortcut
        
        # Check for tab navigation shortcuts
        first_file = self._get_shortcut_text('first_file', self.keybindings)
        if first_file:
            optional_shortcuts['first_file'] = first_file
        last_file = self._get_shortcut_text('last_file', self.keybindings)
        if last_file:
            optional_shortcuts['last_file'] = last_file
        
        # Check for stats cycling shortcut
        cycle_stats = self._get_shortcut_text('cycle_file_change_stats', self.keybindings)
        if cycle_stats:
            optional_shortcuts['cycle_file_change_stats'] = cycle_stats
        
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
        
        html_result = f"""
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
            h3 {{
                color: {header_color};
                margin-top: 15px;
                margin-bottom: 8px;
                font-size: 1.1em;
            }}
        </style>
        
        <h2>Mode Selection</h2>
        <table>
            <tr>
                <th width="30%">Shortcut</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><span class="shortcut">{toggle_focus_mode}</span></td>
                <td>Toggle between File Selection mode and Viewer mode</td>
            </tr>
        </table>
        <p style="color: {note_color}; margin-left: 10px; margin-top: 5px; font-size: 0.95em;">
            The viewer has two modes. In <b>File Selection</b> mode, keyboard input navigates the file tree sidebar.
            In <b>Viewer</b> mode, keyboard input controls the active tab. The unfocused area is shown with a gray overlay.
            Click in an area to switch to that mode automatically.
        </p>
        
        <h2>File Selection Mode (Sidebar)</h2>
        <table>
            <tr>
                <th width="30%">Shortcut</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><span class="shortcut">Arrow Keys</span></td>
                <td>Navigate up/down through file tree</td>
            </tr>
            <tr>
                <td><span class="shortcut">Left/Right Arrows</span></td>
                <td>Collapse/expand directories</td>
            </tr>
            <tr>
                <td><span class="shortcut">Enter</span> or <span class="shortcut">Space</span></td>
                <td>Open selected file and switch to Viewer mode</td>
            </tr>
            <tr>
                <td><span class="shortcut">Left-click file</span></td>
                <td>Open file and switch to Viewer mode</td>
            </tr>
            <tr>
                <td><span class="shortcut">Right-click anywhere</span></td>
                <td>Enter File Selection mode</td>
            </tr>
            <tr>
                <td><span class="shortcut">{quit_application}</span></td>
                <td>Quit application</td>
            </tr>
        </table>

        <h2>Viewer Mode (Content Area)</h2>
        
        <h3>Common to All Tab Types</h3>
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
            </tr>"""
        
        # Add optional first/last file shortcuts if configured
        if optional_shortcuts.get('first_file'):
            html_result += f"""
            <tr>
                <td><span class="shortcut">{optional_shortcuts['first_file']}</span></td>
                <td>Jump to first tab</td>
            </tr>"""
        if optional_shortcuts.get('last_file'):
            html_result += f"""
            <tr>
                <td><span class="shortcut">{optional_shortcuts['last_file']}</span></td>
                <td>Jump to last tab</td>
            </tr>"""
        
        html_result += f"""
            <tr>
                <td><span class="shortcut">{close_tab}</span></td>
                <td>Close current tab</td>
            </tr>
            <tr>
                <td><span class="shortcut">{quit_application}</span></td>
                <td>Quit application</td>
            </tr>
            <tr>
                <td><span class="shortcut">{search}</span></td>
                <td>Open search dialog</td>
            </tr>
            <tr>
                <td><span class="shortcut">{find_next}</span> / <span class="shortcut">{find_prev}</span></td>
                <td>Find next / previous search match</td>
            </tr>
            <tr>
                <td><span class="shortcut">Arrow Keys</span></td>
                <td>Navigate up/down/left/right</td>
            </tr>"""
        
        # Only show PageUp/PageDown if optional cursor shortcuts aren't configured
        if not optional_shortcuts.get('cursor_pageup') and not optional_shortcuts.get('cursor_pagedown'):
            html_result += """
            <tr>
                <td><span class="shortcut">PageUp</span> / <span class="shortcut">PageDown</span></td>
                <td>Scroll up/down by ~10 lines</td>
            </tr>"""
        
        html_result += """
            <tr>
                <td><span class="shortcut">Space</span> / <span class="shortcut">Shift+Space</span></td>
                <td>Page down / page up</td>
            </tr>
            <tr>
                <td><span class="shortcut">Home</span> / <span class="shortcut">End</span></td>
                <td>Jump to start/end of file</td>
            </tr>"""
        
        # Add optional cursor movement shortcuts if configured
        cursor_shortcuts_html = []
        if optional_shortcuts.get('cursor_up'):
            cursor_shortcuts_html.append(f"<tr><td><span class=\"shortcut\">{optional_shortcuts['cursor_up']}</span></td><td>Move cursor up</td></tr>")
        if optional_shortcuts.get('cursor_down'):
            cursor_shortcuts_html.append(f"<tr><td><span class=\"shortcut\">{optional_shortcuts['cursor_down']}</span></td><td>Move cursor down</td></tr>")
        if optional_shortcuts.get('cursor_left'):
            cursor_shortcuts_html.append(f"<tr><td><span class=\"shortcut\">{optional_shortcuts['cursor_left']}</span></td><td>Move cursor left</td></tr>")
        if optional_shortcuts.get('cursor_right'):
            cursor_shortcuts_html.append(f"<tr><td><span class=\"shortcut\">{optional_shortcuts['cursor_right']}</span></td><td>Move cursor right</td></tr>")
        if optional_shortcuts.get('cursor_pageup'):
            cursor_shortcuts_html.append(f"<tr><td><span class=\"shortcut\">{optional_shortcuts['cursor_pageup']}</span></td><td>Move cursor page up</td></tr>")
        if optional_shortcuts.get('cursor_pagedown'):
            cursor_shortcuts_html.append(f"<tr><td><span class=\"shortcut\">{optional_shortcuts['cursor_pagedown']}</span></td><td>Move cursor page down</td></tr>")
        if optional_shortcuts.get('cursor_home'):
            cursor_shortcuts_html.append(f"<tr><td><span class=\"shortcut\">{optional_shortcuts['cursor_home']}</span></td><td>Move cursor to start of file</td></tr>")
        if optional_shortcuts.get('cursor_end'):
            cursor_shortcuts_html.append(f"<tr><td><span class=\"shortcut\">{optional_shortcuts['cursor_end']}</span></td><td>Move cursor to end of file</td></tr>")
        
        # Add optional selection shortcuts if configured
        if optional_shortcuts.get('select_up'):
            cursor_shortcuts_html.append(f"<tr><td><span class=\"shortcut\">{optional_shortcuts['select_up']}</span></td><td>Select text upward</td></tr>")
        if optional_shortcuts.get('select_down'):
            cursor_shortcuts_html.append(f"<tr><td><span class=\"shortcut\">{optional_shortcuts['select_down']}</span></td><td>Select text downward</td></tr>")
        if optional_shortcuts.get('select_left'):
            cursor_shortcuts_html.append(f"<tr><td><span class=\"shortcut\">{optional_shortcuts['select_left']}</span></td><td>Select text leftward</td></tr>")
        if optional_shortcuts.get('select_right'):
            cursor_shortcuts_html.append(f"<tr><td><span class=\"shortcut\">{optional_shortcuts['select_right']}</span></td><td>Select text rightward</td></tr>")
        if optional_shortcuts.get('select_pageup'):
            cursor_shortcuts_html.append(f"<tr><td><span class=\"shortcut\">{optional_shortcuts['select_pageup']}</span></td><td>Select text page up</td></tr>")
        if optional_shortcuts.get('select_pagedown'):
            cursor_shortcuts_html.append(f"<tr><td><span class=\"shortcut\">{optional_shortcuts['select_pagedown']}</span></td><td>Select text page down</td></tr>")
        
        if cursor_shortcuts_html:
            html_result += "\n" + "\n            ".join(cursor_shortcuts_html)
        
        html_result += f"""
            <tr>
                <td><span class="shortcut">{toggle_sidebar}</span></td>
                <td>Toggle sidebar visibility</td>
            </tr>
            <tr>
                <td><span class="shortcut">{shortcuts_help}</span></td>
                <td>Show this shortcuts reference</td>
            </tr>
            <tr>
                <td><span class="shortcut">{increase_font}</span> / <span class="shortcut">{decrease_font}</span></td>
                <td>Increase / decrease font size</td>
            </tr>
            <tr>
                <td><span class="shortcut">{reset_font}</span></td>
                <td>Reset font size to default</td>
            </tr>
        </table>
        
        <h3>Diff Viewer Tabs</h3>
        <table>
            <tr>
                <th width="30%">Shortcut</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><span class="shortcut">{next_change}</span></td>
                <td>Next change region</td>
            </tr>
            <tr>
                <td><span class="shortcut">{prev_change}</span></td>
                <td>Previous change region</td>
            </tr>
            <tr>
                <td><span class="shortcut">{center_region}</span></td>
                <td>Center on current region</td>
            </tr>
            <tr>
                <td><span class="shortcut">{top_of_file}</span></td>
                <td>Jump to top of file</td>
            </tr>
            <tr>
                <td><span class="shortcut">{bottom_of_file}</span></td>
                <td>Jump to bottom of file</td>
            </tr>
            <tr>
                <td><span class="shortcut">Tab</span></td>
                <td>Switch focus between base and modified panes (Content mode only)</td>
            </tr>
            <tr>
                <td><span class="shortcut">{toggle_collapse}</span></td>
                <td>Collapse/expand added/deleted region at cursor</td>
            </tr>
            <tr>
                <td><span class="shortcut">{toggle_collapse_all}</span></td>
                <td>Collapse/expand all added/deleted regions</td>
            </tr>
            <tr>
                <td><span class="shortcut">{toggle_bookmark}</span></td>
                <td>Toggle bookmark on current line</td>
            </tr>
            <tr>
                <td><span class="shortcut">{prev_bookmark}</span></td>
                <td>Previous bookmark</td>
            </tr>
            <tr>
                <td><span class="shortcut">{next_bookmark}</span></td>
                <td>Next bookmark</td>
            </tr>
            <tr>
                <td><span class="shortcut">{take_note}</span></td>
                <td>Take note of selected text</td>
            </tr>
            <tr>
                <td><span class="shortcut">{jump_to_note}</span></td>
                <td>Jump to note for current line (if exists)</td>
            </tr>
            <tr>
                <td><span class="shortcut">Right-click -> Take Note</span></td>
                <td>Add selected text to notes file</td>
            </tr>
            <tr>
                <td><span class="shortcut">Right-click -> Jump to Note</span></td>
                <td>Jump to note for clicked line</td>
            </tr>
            <tr>
                <td><span class="shortcut">Double-click line</span></td>
                <td>Quick note - add line to notes file</td>
            </tr>
            <tr>
                <td><span class="shortcut">{reload}</span></td>
                <td>Reload current file</td>
            </tr>
            <tr>
                <td><span class="shortcut">{toggle_diff_map}</span></td>
                <td>Toggle diff map</td>
            </tr>
            <tr>
                <td><span class="shortcut">{toggle_line_numbers}</span></td>
                <td>Toggle line numbers</td>
            </tr>
            <tr>
                <td><span class="shortcut">{toggle_tab_highlight}</span></td>
                <td>Toggle tab character highlighting</td>
            </tr>
            <tr>
                <td><span class="shortcut">{toggle_eol}</span></td>
                <td>Toggle trailing whitespace highlighting</td>
            </tr>
            <tr>
                <td><span class="shortcut">{toggle_intraline}</span></td>
                <td>Toggle intraline changes highlighting</td>
            </tr>
            <tr>
                <td><span class="shortcut">{mod_key}+r</span></td>
                <td>Toggle auto-reload files</td>
            </tr>"""
        
        # Add optional cycle stats shortcut if configured
        if optional_shortcuts.get('cycle_file_change_stats'):
            html_result += f"""
            <tr>
                <td><span class="shortcut">{optional_shortcuts['cycle_file_change_stats']}</span></td>
                <td>Cycle stats display (None / Tabs / Sidebar)</td>
            </tr>"""
        
        html_result += f"""
        </table>
        
        <h3>Commit Message Tabs</h3>
        <table>
            <tr>
                <th width="30%">Shortcut</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><span class="shortcut">{cm_toggle_bookmark}</span></td>
                <td>Toggle bookmark on current line</td>
            </tr>
            <tr>
                <td><span class="shortcut">{cm_prev_bookmark}</span></td>
                <td>Previous bookmark</td>
            </tr>
            <tr>
                <td><span class="shortcut">{cm_next_bookmark}</span></td>
                <td>Next bookmark</td>
            </tr>
            <tr>
                <td><span class="shortcut">{cm_take_note}</span></td>
                <td>Take note of selected text</td>
            </tr>
            <tr>
                <td><span class="shortcut">{cm_jump_to_note}</span></td>
                <td>Jump to note for current line</td>
            </tr>
        </table>
        
        <h3>Review Notes Tabs</h3>
        <p style="color: {note_color}; margin-left: 10px; margin-top: 5px; font-size: 0.95em;">
            Review Notes tabs support standard text navigation and search (listed under "Common to All Tab Types" above).
            They do not have additional specialized shortcuts.
        </p>

        <h3>Terminal Editor Tabs (Vim, Emacs)</h3>
        <p style="color: {note_color}; margin-left: 10px; margin-top: 5px; font-size: 0.95em;">
            When using a terminal-based editor for review notes, all keyboard input is passed directly to the editor.
            To access global shortcuts or terminal-specific commands, use the escape prefix sequence.
        </p>
        <table>
            <tr>
                <th width="30%">Shortcut</th>
                <th>Action</th>
            </tr>
            <tr>
                <td><span class="shortcut">{terminal_escape}</span></td>
                <td>Escape prefix - next key is interpreted as a global or terminal shortcut</td>
            </tr>
            <tr>
                <td><span class="shortcut">{terminal_escape}</span> then <span class="shortcut">{toggle_focus_mode}</span></td>
                <td>Switch to File Selection mode</td>
            </tr>
            <tr>
                <td><span class="shortcut">{terminal_escape}</span> then <span class="shortcut">{toggle_sidebar}</span></td>
                <td>Toggle sidebar visibility</td>
            </tr>
            <tr>
                <td><span class="shortcut">{terminal_escape}</span> then <span class="shortcut">{close_tab}</span></td>
                <td>Close current tab (saves and exits editor)</td>
            </tr>
            <tr>
                <td><span class="shortcut">{terminal_escape}</span> then <span class="shortcut">{quit_application}</span></td>
                <td>Quit application</td>
            </tr>
            <tr>
                <td><span class="shortcut">{terminal_escape}</span> then <span class="shortcut">{term_next_bookmark}</span></td>
                <td>Navigate to next bookmark</td>
            </tr>
            <tr>
                <td><span class="shortcut">{terminal_escape}</span> then <span class="shortcut">{term_prev_bookmark}</span></td>
                <td>Navigate to previous bookmark</td>
            </tr>
        </table>
        <p style="color: {note_color}; margin-left: 10px; margin-top: 5px; font-size: 0.95em;">
            When the escape prefix is active, the terminal border turns blue. The prefix times out after 2 seconds
            if no key is pressed. If a non-recognized key is pressed after the prefix, it is ignored and the border reverts.
        </p>
        """

        return html_result
