# Copyright (c) 2025, 2026  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Tab manager for diff_review

This module contains the tab widget that manages multiple DiffViewer instances
with a sidebar for file selection.
"""
import os
import sys
import signal
from PyQt6.QtWidgets import (QApplication, QTabWidget, QMainWindow, QHBoxLayout,
                              QVBoxLayout, QWidget, QPushButton, QSplitter,
                              QPlainTextEdit, QMenu, QMessageBox, QProgressDialog, QFileDialog)
from PyQt6.QtCore import Qt, QFileSystemWatcher, QTimer
from PyQt6.QtGui import (QAction, QFont, QKeySequence, QActionGroup, QFontMetrics,
                         QColor, QTextDocument, QShortcut)

from help_dialog import HelpDialog
from shortcuts_dialog import ShortcutsDialog
from search_dialogs import SearchDialog, SearchResultDialog
import color_palettes
import view_state_manager
import bookmark_manager
import file_watcher
import commit_msg_handler
import search_manager
import file_tree_sidebar
import keybindings
import generate_viewer
from commit_msg_handler import CommitMessageTab
from note_manager import ReviewNotesTab, ReviewNotesTabBase
from tab_content_base import TabContentBase
from diff_viewer import DiffViewer


class OverlayWidget(QWidget):
    """Widget that can have a dimming overlay that auto-resizes"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.overlay = QWidget(self)
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.overlay.hide()
        # Ensure overlay fills the entire container
        self.overlay.setGeometry(0, 0, self.width(), self.height())

    def resizeEvent(self, event):
        """Resize overlay to match widget size"""
        super().resizeEvent(event)
        # Always update overlay geometry when container resizes
        self.overlay.setGeometry(0, 0, self.width(), self.height())

    def showEvent(self, event):
        """Ensure overlay is sized correctly when shown"""
        super().showEvent(event)
        if self.overlay.isVisible():
            self.overlay.setGeometry(0, 0, self.width(), self.height())


class DiffViewerTabWidget(QMainWindow):
    """Main window containing tabs of DiffViewer instances with file sidebar"""

    def _get_shortcut_text(self, action_name, keybindings_obj):
        """Get formatted shortcut text for menu display.

        Args:
            action_name: Name of the action (e.g., 'toggle_sidebar')
            keybindings_obj: KeyBindings object to query

        Returns:
            Formatted string like 'Ctrl+B' or 'Cmd+B', or empty string if no binding
        """
        sequences = keybindings_obj.get_sequences(action_name)
        if not sequences:
            return ""

        # Use the first sequence for menu display
        seq = sequences[0]
        parts = []

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
                # Meta is Cmd on macOS (already shown above for Control)
                # On other platforms, show Meta
                if sys.platform != 'darwin':
                    key_parts.append("Meta")

            # Get key name
            key_name = self._qt_key_to_name(qt_key)
            key_parts.append(key_name)

            parts.append("+".join(key_parts))

        return " ".join(parts)

    def _qt_key_to_name(self, qt_key):
        """Convert Qt.Key enum to display string.

        Args:
            qt_key: Qt.Key enum value

        Returns:
            String representation of the key
        """
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
                    return key_name
        return f"Key_{qt_key}"

    def __init__(self,
                 afr,           # Abstract file reader
                 display_lines     : int,
                 display_chars     : int,
                 show_diff_map     : bool,
                 show_line_numbers : bool,
                 auto_reload       : bool,
                 ignore_tab        : bool,
                 ignore_trailing_ws: bool,
                 ignore_intraline  : bool,
                 intraline_percent : float,
                 palette           : str,
                 dump_ir           : bool,
                 tab_label_stats   : bool,
                 file_label_stats  : bool,
                 editor_class,
                 editor_theme,
                 keybindings_file,
                 note_file,
                 review_mode       : str):  # "committed" or "uncommitted"
        if QApplication.instance() is None:
            self._app = QApplication(sys.argv)
        else:
            self._app = QApplication.instance()

        super().__init__()

        self.review_mode_ = review_mode

        self.afr_ = afr
        self.display_lines = display_lines
        self.display_chars = display_chars
        self.ignore_tab = ignore_tab
        self.ignore_trailing_ws = ignore_trailing_ws
        self.ignore_intraline = ignore_intraline
        self.dump_ir = dump_ir
        self.intraline_percent = intraline_percent
        self._bulk_loading = False  # Suppress highlighting during "Open All Files"
        self.editor_class = editor_class
        self.editor_theme = editor_theme

        # Stats display mode: 0=none, 1=tabs only, 2=sidebar only
        # Determine initial mode from command line args
        if not tab_label_stats and not file_label_stats:
            self.stats_display_mode = 0  # No stats
        elif tab_label_stats and not file_label_stats:
            self.stats_display_mode = 1  # Tab stats only
        else:  # not tab_label_stats and file_label_stats
            self.stats_display_mode = 2  # Sidebar stats only

        # Store individual flags for compatibility
        self.tab_label_stats = tab_label_stats
        self.file_label_stats = file_label_stats

        # Apply explicit palette if specified, otherwise use auto-selected default
        if palette is not None:
            color_palettes.set_current_palette(palette)

        self.setWindowTitle("Diff Viewer")

        # Storage for file classes and their buttons
        self.file_classes = []
        self.file_buttons = []
        self.file_to_tab_index = {}  # Maps file_class to tab index
        self.current_file_class = None  # Track which file is being added
        self.sidebar_visible = True
        self.saved_splitter_sizes = None  # Stores splitter sizes when sidebar is hidden

        # Global view state for all tabs
        self.diff_map_visible = show_diff_map  # Initial state for diff map
        self.line_numbers_visible = show_line_numbers  # Initial state for line numbers

        # Staged diff mode: controls which file pair to compare for staged files
        self.staged_diff_mode_ = generate_viewer.DIFF_MODE_BASE_MODI

        # Create view state manager
        self.view_state_mgr = view_state_manager.ViewStateManager(
            self, show_diff_map, show_line_numbers,
            ignore_tab, ignore_trailing_ws, ignore_intraline)

        # Initialize key bindings for different contexts
        self.keybindings = keybindings.KeyBindings(keybindings_file, context='global')
        self.diff_keybindings = keybindings.KeyBindings(keybindings_file, context='diff')
        self.note_keybindings = keybindings.KeyBindings(keybindings_file, context='note')
        self.commit_msg_keybindings = keybindings.KeyBindings(keybindings_file, context='commit_msg')
        self.terminal_keybindings = keybindings.KeyBindings(keybindings_file, context='terminal')
        self.pending_keys = []  # For multi-key sequences

        # Create bookmark manager
        self.bookmark_mgr = bookmark_manager.BookmarkManager(self)

        # Dialog instance tracking to prevent multiple instances
        self.help_dialog = None
        self.shortcuts_dialog = None

        # Create file watcher manager
        self.file_watcher_mgr = file_watcher.FileWatcherManager(self, auto_reload)

        # Keep references for compatibility
        self.auto_reload_enabled = self.file_watcher_mgr.auto_reload_enabled
        self.file_watchers = self.file_watcher_mgr.file_watchers
        self.reload_timers = self.file_watcher_mgr.reload_timers
        self.changed_files = self.file_watcher_mgr.changed_files

        # Create commit message handler
        self.commit_msg_mgr = commit_msg_handler.CommitMsgHandler(self)

        # Keep references for compatibility
        self.commit_msg_rel_path_ = self.commit_msg_mgr.commit_msg_rel_path
        self.commit_msg_button = self.commit_msg_mgr.commit_msg_button

        # Create note manager
        import note_manager
        self.note_mgr = note_manager.NoteManager(self, note_file)

        # Create search manager
        self.search_mgr = search_manager.SearchManager(self)

        # Keep reference for compatibility
        self.search_result_dialogs = self.search_mgr.search_result_dialogs

        # Focus mode: 'sidebar' or 'content'
        self.focus_mode = 'sidebar'  # Start with sidebar focused (files must be selected first)
        self.last_content_tab_index = None  # Track last focused content tab for restoring focus
        self.sidebar_base_stylesheet = ""  # Will be set after sidebar is created
        self.tab_widget_base_stylesheet = ""  # Will be set after tab_widget is created
        self.focus_mode_label = None  # Label for showing focus mode in status bar

        # Create main layout
        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create splitter for resizable sidebar
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Create sidebar with overlay container
        self.sidebar_container = OverlayWidget()
        sidebar_layout = QVBoxLayout(self.sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar_widget = file_tree_sidebar.FileTreeSidebar(self)
        sidebar_layout.addWidget(self.sidebar_widget)
        self.sidebar_overlay = self.sidebar_container.overlay

        # Keep references for backward compatibility
        self.open_all_button = self.sidebar_widget.open_all_button
        self.button_layout = None  # No longer used
        self.button_container = None  # No longer used

        # Add sidebar container to splitter
        self.splitter.addWidget(self.sidebar_container)

        # Create tab widget with overlay container
        self.tab_container = OverlayWidget()
        tab_layout = QVBoxLayout(self.tab_container)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)  # Allow tabs to be reordered by dragging

        # On MacOS, prevent tab widget from expanding the window when many tabs are added
        # This fixes a regression where the window would grow wider and the sidebar would
        # shrink and become unresizable after opening many files
        if sys.platform == 'darwin':
            from PyQt6.QtWidgets import QSizePolicy
            policy = self.tab_widget.sizePolicy()
            policy.setHorizontalPolicy(QSizePolicy.Policy.Ignored)
            self.tab_widget.setSizePolicy(policy)

        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        tab_layout.addWidget(self.tab_widget)
        self.tab_overlay = self.tab_container.overlay

        # Disable keyboard focus on tab bar to prevent Tab/Shift+Tab from reaching it
        self.tab_widget.tabBar().setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.splitter.addWidget(self.tab_container)

        # Set initial splitter sizes (sidebar: 250px, main area: rest)
        self.splitter.setSizes([250, 1350])

        main_layout.addWidget(self.splitter)

        self.setCentralWidget(central)

        # Install event filter on tab bar to capture clicks on tabs
        self.tab_widget.tabBar().installEventFilter(self)

        # Install global event filter on application to catch ALL mouse clicks
        self._app.installEventFilter(self)

        # Don't apply initial focus tinting - wait until first file loads
        # self.update_focus_tinting()

        # Create menu bar
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        open_note_action = QAction("Open Note...", self)
        open_note_action.triggered.connect(self.open_note_file)
        file_menu.addAction(open_note_action)

        file_menu.addSeparator()

        shortcut_text = self._get_shortcut_text('close_tab', self.keybindings)
        menu_text = "Close Tab" + (f"\t{shortcut_text}" if shortcut_text else "")
        close_tab_action = QAction(menu_text, self)
        # Shortcut handled by keybinding system
        # close_tab_action.setShortcut(QKeySequence("Ctrl+W"))
        close_tab_action.triggered.connect(self.close_current_tab)
        file_menu.addAction(close_tab_action)

        # Quit - shortcut handled by keybinding system
        shortcut_text = self._get_shortcut_text('quit_application', self.keybindings)
        quit_text = "Quit" + (f"\t{shortcut_text}" if shortcut_text else "")
        quit_action = QAction(quit_text, self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # View menu
        view_menu = menubar.addMenu("View")

        shortcut_text = self._get_shortcut_text('toggle_sidebar', self.keybindings)
        menu_text = "Show Sidebar" + (f"\t{shortcut_text}" if shortcut_text else "")
        self.show_sidebar_action = QAction(menu_text, self)
        # Shortcut handled by keybinding system
        # self.show_sidebar_action.setShortcut(QKeySequence("Ctrl+B"))
        self.show_sidebar_action.setCheckable(True)
        self.show_sidebar_action.setChecked(True)  # Sidebar starts visible
        self.show_sidebar_action.triggered.connect(self.toggle_sidebar)
        view_menu.addAction(self.show_sidebar_action)

        view_menu.addSeparator()

        shortcut_text = self._get_shortcut_text('toggle_diff_map', self.diff_keybindings)
        menu_text = "Show Diff Map" + (f"\t{shortcut_text}" if shortcut_text else "")
        self.show_diff_map_action = QAction(menu_text, self)
        # Shortcut handled by keybinding system
        # self.show_diff_map_action.setShortcut(QKeySequence("Ctrl+D"))
        self.show_diff_map_action.setCheckable(True)
        self.show_diff_map_action.setChecked(show_diff_map)
        self.show_diff_map_action.triggered.connect(self.toggle_diff_map)
        view_menu.addAction(self.show_diff_map_action)

        shortcut_text = self._get_shortcut_text('toggle_line_numbers', self.diff_keybindings)
        menu_text = "Show Line Numbers" + (f"\t{shortcut_text}" if shortcut_text else "")
        self.show_line_numbers_action = QAction(menu_text, self)
        # Shortcut handled by keybinding system
        # self.show_line_numbers_action.setShortcut(QKeySequence("Ctrl+L"))
        self.show_line_numbers_action.setCheckable(True)
        self.show_line_numbers_action.setChecked(show_line_numbers)
        self.show_line_numbers_action.triggered.connect(self.toggle_line_numbers)
        view_menu.addAction(self.show_line_numbers_action)

        view_menu.addSeparator()

        shortcut_text = self._get_shortcut_text('toggle_tab_highlight', self.diff_keybindings)
        menu_text = "Show Tabs" + (f"\t{shortcut_text}" if shortcut_text else "")
        self.show_tab_action = QAction(menu_text, self)
        # Shortcut handled by keybinding system
        # self.show_tab_action.setShortcut(QKeySequence("Ctrl+T"))
        self.show_tab_action.setCheckable(True)
        self.show_tab_action.setChecked(not ignore_tab)
        self.show_tab_action.triggered.connect(self.toggle_tab_visibility)
        view_menu.addAction(self.show_tab_action)

        shortcut_text = self._get_shortcut_text('toggle_eol_highlight', self.diff_keybindings)
        menu_text = "Show Trailing Whitespace" + (f"\t{shortcut_text}" if shortcut_text else "")
        self.show_trailing_ws_action = QAction(menu_text, self)
        # Shortcut handled by keybinding system
        # self.show_trailing_ws_action.setShortcut(QKeySequence("Ctrl+E"))
        self.show_trailing_ws_action.setCheckable(True)
        self.show_trailing_ws_action.setChecked(not ignore_trailing_ws)
        self.show_trailing_ws_action.triggered.connect(self.toggle_trailing_ws_visibility)
        view_menu.addAction(self.show_trailing_ws_action)

        shortcut_text = self._get_shortcut_text('toggle_intraline', self.diff_keybindings)
        menu_text = "Show Intraline Changes" + (f"\t{shortcut_text}" if shortcut_text else "")
        self.show_intraline_action = QAction(menu_text, self)
        # Shortcut handled by keybinding system
        # self.show_intraline_action.setShortcut(QKeySequence("Ctrl+I"))
        self.show_intraline_action.setCheckable(True)
        self.show_intraline_action.setChecked(not ignore_intraline)
        self.show_intraline_action.triggered.connect(self.toggle_intraline_visibility)
        view_menu.addAction(self.show_intraline_action)

        view_menu.addSeparator()

        self.auto_reload_action = QAction("Auto-reload Files", self)
        # Shortcut handled by keybinding system if configured
        # self.auto_reload_action.setShortcut(QKeySequence("Ctrl+R"))
        self.auto_reload_action.setCheckable(True)
        self.auto_reload_action.setChecked(auto_reload)  # Set from parameter
        self.auto_reload_action.triggered.connect(self.toggle_auto_reload)
        view_menu.addAction(self.auto_reload_action)

        view_menu.addSeparator()

        self.cycle_stats_action = QAction("Cycle Stats Display (None -> Tabs -> Sidebar)", self)
        # Shortcut handled by keybinding system if configured
        # self.cycle_stats_action.setShortcut(QKeySequence("Ctrl+Y"))
        self.cycle_stats_action.triggered.connect(self.cycle_stats_display)
        view_menu.addAction(self.cycle_stats_action)

        # Set initial menu text with current mode boldfaced
        self._update_stats_menu_text()

        view_menu.addSeparator()

        increase_font_action = QAction("Increase Font Size", self)
        increase_font_action.setShortcuts([QKeySequence.StandardKey.ZoomIn])
        increase_font_action.triggered.connect(self.increase_font_size)
        view_menu.addAction(increase_font_action)

        decrease_font_action = QAction("Decrease Font Size", self)
        decrease_font_action.setShortcuts([QKeySequence.StandardKey.ZoomOut])
        decrease_font_action.triggered.connect(self.decrease_font_size)
        view_menu.addAction(decrease_font_action)

        shortcut_text = self._get_shortcut_text('reset_font', self.keybindings)
        menu_text = "Reset Font Size" + (f"\t{shortcut_text}" if shortcut_text else "")
        reset_font_action = QAction(menu_text, self)
        # Shortcut handled by keybinding system
        # reset_font_action.setShortcut(QKeySequence("Ctrl+0"))
        reset_font_action.triggered.connect(self.reset_font_size)
        view_menu.addAction(reset_font_action)

        # Palette menu
        palette_menu = menubar.addMenu("Palette")

        # Create action group for exclusive palette selection
        self.palette_action_group = QActionGroup(self)
        self.palette_action_group.setExclusive(True)

        # Get current palette name
        current_palette = color_palettes.get_current_palette().name

        # Add action for each palette
        for palette_name in color_palettes.get_palette_names():
            action = QAction(palette_name, self)
            action.setCheckable(True)
            action.setChecked(palette_name == current_palette)
            action.triggered.connect(lambda checked, name=palette_name: self.switch_palette(name))
            self.palette_action_group.addAction(action)
            palette_menu.addAction(action)

        # Compare menu (only for uncommitted reviews)
        self.compare_menu = menubar.addMenu("Compare")
        self.compare_action_group = QActionGroup(self)
        self.compare_action_group.setExclusive(True)

        self.compare_base_modi_action = QAction("HEAD vs Working", self)
        self.compare_base_modi_action.setCheckable(True)
        self.compare_base_modi_action.setChecked(True)  # Default mode
        self.compare_base_modi_action.triggered.connect(
            lambda: self.set_staged_diff_mode(generate_viewer.DIFF_MODE_BASE_MODI))
        self.compare_action_group.addAction(self.compare_base_modi_action)
        self.compare_menu.addAction(self.compare_base_modi_action)

        self.compare_base_stage_action = QAction("HEAD vs Staged", self)
        self.compare_base_stage_action.setCheckable(True)
        self.compare_base_stage_action.triggered.connect(
            lambda: self.set_staged_diff_mode(generate_viewer.DIFF_MODE_BASE_STAGE))
        self.compare_action_group.addAction(self.compare_base_stage_action)
        self.compare_menu.addAction(self.compare_base_stage_action)

        self.compare_stage_modi_action = QAction("Staged vs Working", self)
        self.compare_stage_modi_action.setCheckable(True)
        self.compare_stage_modi_action.triggered.connect(
            lambda: self.set_staged_diff_mode(generate_viewer.DIFF_MODE_STAGE_MODI))
        self.compare_action_group.addAction(self.compare_stage_modi_action)
        self.compare_menu.addAction(self.compare_stage_modi_action)

        # Hide Compare menu for committed reviews
        if self.review_mode_ == "committed":
            self.compare_menu.menuAction().setVisible(False)

        # Help menu
        help_menu = menubar.addMenu("Help")

        shortcut_text = self._get_shortcut_text('shortcuts_help', self.keybindings)
        menu_text = "Keyboard Shortcuts" + (f"\t{shortcut_text}" if shortcut_text else "")
        shortcuts_action = QAction(menu_text, self)
        # Shortcuts handled by keybinding system
        # shortcuts_action.setShortcuts([QKeySequence("Ctrl+?"), QKeySequence("F1")])
        shortcuts_action.triggered.connect(self.show_shortcuts)
        help_menu.addAction(shortcuts_action)

        help_action = QAction("How to Use", self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

        # Calculate window size based on display parameters
        # Use Courier 12 Bold to match the text widget font
        text_font = QFont("Courier", 12, QFont.Weight.Bold)
        fm = QFontMetrics(text_font)
        char_width = fm.horizontalAdvance('0')
        line_height = fm.height()

        # Width: (chars * 2 panes) + line numbers (90*2) + diff map (30) + scrollbar (20) + margins (40) + sidebar (250)
        total_width = (self.display_chars * char_width * 2) + (90 * 2) + 30 + 20 + 40 + 250
        # Height: lines + labels (40) + scrollbar (20) + status bar (30) + margins (20) + menubar (30)
        total_height = (self.display_lines * line_height) + 40 + 20 + 30 + 20 + 30

        # Tab navigation shortcuts (support both Ctrl and Meta for Mac compatibility)
        next_tab_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), self)
        next_tab_shortcut.activated.connect(self.next_tab)
        next_tab_shortcut_alt = QShortcut(QKeySequence("Meta+Tab"), self)
        next_tab_shortcut_alt.activated.connect(self.next_tab)

        prev_tab_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        prev_tab_shortcut.activated.connect(self.prev_tab)
        prev_tab_shortcut_alt = QShortcut(QKeySequence("Meta+Shift+Tab"), self)
        prev_tab_shortcut_alt.activated.connect(self.prev_tab)

        self.resize(total_width, total_height)

    def add_commit_msg(self, commit_msg_rel_path):
        """Add commit message to the sidebar as the first item"""
        self.commit_msg_mgr.add_commit_msg(commit_msg_rel_path)
        # Sync references
        self.commit_msg_rel_path_ = self.commit_msg_mgr.commit_msg_rel_path
        self.commit_msg_button = self.commit_msg_mgr.commit_msg_button

        # Update "Open All Files" count to include commit message
        self.update_open_all_button_text()

    def on_commit_msg_clicked(self):
        """Handle commit message button click"""
        self.commit_msg_mgr.on_commit_msg_clicked()

    def create_commit_msg_tab(self):
        """Create a tab displaying the commit message"""
        self.commit_msg_mgr.create_commit_msg_tab()

    def show_search_dialog(self):
        """Show search dialog for current tab"""
        self.search_mgr.show_search_dialog()


    def search_selected_text(self, text_widget):
        """Search for selected text from any text widget"""
        self.search_mgr.search_selected_text(text_widget)

    def show_commit_msg_context_menu(self, pos, text_widget):
        """Show context menu for commit message"""
        self.commit_msg_mgr.show_commit_msg_context_menu(pos, text_widget)

    def take_commit_msg_note(self, text_widget):
        """Take note from commit message"""
        self.commit_msg_mgr.take_commit_msg_note(text_widget)

    def open_note_file(self):
        """Open a note file using file picker dialog"""
        self.note_mgr.prompt_for_note_file()

    def add_file(self, file_class):
        """
        Add a file to the sidebar.

        Args:
            file_class: An object with button_label() and add_viewer(tab_widget) methods
        """
        self.file_classes.append(file_class)

        # Add to tree view
        self.sidebar_widget.add_file(file_class)

        # Store reference in file_class for later updates
        file_class.ui_button_ = None  # No longer a button

        # Keep file_buttons list for compatibility, though items are no longer buttons
        # Instead, we'll track file_classes directly
        self.file_buttons.append(file_class)  # Store file_class for compatibility

        # Update "Open All Files" button text with current file count
        self.update_open_all_button_text()

    def update_open_all_button_text(self):
        """Update the 'Open All Files' button text to show file count"""
        total_files = len(self.file_classes)

        # Add commit message if present
        if self.commit_msg_button:
            total_files += 1

        # Add review notes if present
        if self.note_mgr.notes_button:
            total_files += 1

        self.sidebar_widget.update_open_all_text(total_files)

    def open_all_files(self):
        """Open all files in tabs, including commit message and review notes if present"""
        # Build list of files that need to be opened
        files_to_open = []

        if self.commit_msg_rel_path_ and 'commit_msg' not in self.file_to_tab_index:
            files_to_open.append(('commit_msg', None))

        # Add review notes if note file is configured and not already open
        if self.note_mgr.get_note_file() and 'review_notes' not in self.file_to_tab_index:
            files_to_open.append(('review_notes', None))

        # Check which files aren't open yet
        for file_class in self.file_classes:
            if file_class not in self.file_to_tab_index:
                files_to_open.append(('file', file_class))

        if len(files_to_open) == 0:
            # All already open, just focus first tab
            if self.tab_widget.count() > 0:
                self.tab_widget.setCurrentIndex(0)
            return

        # Enable bulk loading mode to suppress highlighting during load
        self._bulk_loading = True

        # Create progress dialog
        progress = QProgressDialog("Loading files...", "Cancel", 0, len(files_to_open), self)
        progress.setWindowTitle("Opening Files")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(500)  # Only show if takes more than 500ms

        current_index = 0

        # Open files that aren't already open
        for item_type, item_data in files_to_open:
            if progress.wasCanceled():
                break

            # Update progress text
            if item_type == 'commit_msg':
                progress.setLabelText("Loading Commit Message...")
            elif item_type == 'review_notes':
                progress.setLabelText("Loading Review Notes...")
            else:
                progress.setLabelText(f"Loading {item_data.button_label()}...")

            progress.setValue(current_index)
            QApplication.processEvents()  # Keep UI responsive

            # Load the file
            if item_type == 'commit_msg':
                self.on_commit_msg_clicked()
            elif item_type == 'review_notes':
                self.note_mgr.on_notes_clicked()
            else:
                self.on_file_clicked(item_data)

            current_index += 1

        progress.setValue(len(files_to_open))
        progress.close()

        # Disable bulk loading mode
        self._bulk_loading = False

        # Focus the first tab (commit message if present, otherwise first file)
        if self.tab_widget.count() > 0:
            self.tab_widget.setCurrentIndex(0)
            # Now apply highlighting to the visible tab
            viewer = self.get_viewer_at_index(0)
            if viewer:
                viewer.ensure_highlighting_applied()

            # Focus the content area (first tab)
            self.focus_mode = 'content'
            current_widget = self.tab_widget.currentWidget()
            if current_widget:
                current_widget.focus_content()
            self.update_focus_tinting()
            self.update_status_focus_indicator()

    def on_file_clicked(self, file_class):
        """Handle file button click"""
        # Check if tab already exists for this file
        if file_class in self.file_to_tab_index:
            tab_index = self.file_to_tab_index[file_class]
            # Verify tab still exists (might have been closed)
            if 0 <= tab_index < self.tab_widget.count():
                widget = self.tab_widget.widget(tab_index)
                if isinstance(widget, DiffViewer) and widget.file_class == file_class:
                    # Tab exists, switch to it
                    self.tab_widget.setCurrentIndex(tab_index)
                    return
            # Tab was closed, remove from mapping
            del self.file_to_tab_index[file_class]

        # No existing tab, create new one
        self.current_file_class = file_class  # Store for add_viewer to use
        file_class.add_viewer(self)
        self.current_file_class = None  # Clear after use

        # Update tree item label now that file is loaded and stats are available
        self.sidebar_widget.update_file_label(file_class)

    def add_viewer(self, diff_viewer, tab_title=None):
        """
        Add a fully configured DiffViewer to a new tab.

        Args:
            diff_viewer: A DiffViewer instance that has been configured
            tab_title: Optional title for the tab. If not provided, uses the
                      tab_label() from the file_class

        Returns:
            The index of the newly added tab
        """
        # Use the file_class that was stored when button was clicked
        file_class = self.current_file_class

        if tab_title is None and file_class:
            # Use the tab label as the tab title
            tab_title = file_class.tab_label()
        elif tab_title is None:
            # Fallback if no file_class
            base_name = diff_viewer.base_file.split('/')[-1]
            modified_name = diff_viewer.modified_file.split('/')[-1]
            tab_title = f"{base_name} vs {modified_name}"

        # Add the diff_viewer directly to the tab (it's now a QWidget)
        index = self.tab_widget.addTab(diff_viewer, tab_title)

        # Store references
        diff_viewer.file_class = file_class
        diff_viewer.tab_manager = self  # Back-reference for bookmark sync
        diff_viewer.tab_index = index  # Store tab index

        # Install event filter on DiffViewer itself to capture mouse clicks
        # on all its children (line areas, diff map, scrollbars, etc.)
        # Mouse events bubble up, so filtering the parent catches all clicks
        diff_viewer.installEventFilter(self)

        # Force proper repaints on horizontal scroll to avoid visual artifacts
        # Use repaint() instead of update() to force immediate redraw
        diff_viewer.base_text.horizontalScrollBar().valueChanged.connect(
            lambda: diff_viewer.base_text.viewport().repaint())
        diff_viewer.modified_text.horizontalScrollBar().valueChanged.connect(
            lambda: diff_viewer.modified_text.viewport().repaint())

        # Set up context menus for text widgets
        diff_viewer.base_text.customContextMenuRequested.connect(
            lambda pos: self.show_diff_context_menu(pos, diff_viewer.base_text, 'base'))
        diff_viewer.modified_text.customContextMenuRequested.connect(
            lambda pos: self.show_diff_context_menu(pos, diff_viewer.modified_text, 'modified'))

        # Track file to tab mapping
        if file_class:
            self.file_to_tab_index[file_class] = index

        # Switch to new tab (skip during bulk loading to avoid visual slowdown)
        if not self._bulk_loading:
            self.tab_widget.setCurrentIndex(index)

        # Apply highlighting immediately if not in bulk loading mode
        # (on_tab_changed is suppressed during bulk load)
        if not self._bulk_loading:
            diff_viewer.ensure_highlighting_applied()

        # Apply global view state to new viewer
        self.view_state_mgr.apply_to_viewer(diff_viewer)

        # Set viewer's note file for display in status bar
        diff_viewer.note_file = self.note_mgr.get_note_file()

        # Set up file watching for this viewer
        self.setup_file_watcher(diff_viewer)

        # Update button states immediately
        self.update_button_states()

        # If this is the first tab, apply focus tinting now that we have content
        if self.tab_widget.count() == 1:
            self.update_focus_tinting()

        return index

    def show_diff_context_menu(self, pos, text_widget, side):
        """Show context menu for diff viewer text widgets"""
        self.search_mgr.show_diff_context_menu(pos, text_widget, side)

    def highlight_all_matches_in_widget(self, text_widget, search_text, highlight_color):
        """
        Find and highlight ALL occurrences of search_text in the text widget.
        Uses case-insensitive search.

        Args:
            text_widget: The QPlainTextEdit to search in
            search_text: The text to search for (case-insensitive)
            highlight_color: QColor to use for highlighting all matches
        """
        self.search_mgr.highlight_all_matches_in_widget(text_widget, search_text, highlight_color)

    def select_search_result(self, side, line_idx, search_text=None, char_pos=None):
        """Navigate to a search result and use two-tier highlighting

        Two-tier highlighting system:
        - ALL matches in both panes highlighted with subtle color (done once)
        - CURRENT match highlighted with bright color (changed on each navigation)
        - User can see all matches while navigating through results

        Args:
            side: 'base' or 'modified'
            line_idx: Line index in the display
            search_text: Text to search for
            char_pos: Character position of the specific match to highlight bright (optional)
        """
        self.search_mgr.select_search_result(side, line_idx, search_text, char_pos)

    def clear_search_highlights(self, text_widget):
        """Clear all search highlights from a text widget by removing search highlight colors"""
        self.search_mgr.clear_search_highlights(text_widget)

    def select_commit_msg_result(self, line_idx, search_text=None, char_pos=None):
        """Navigate to a line in the commit message tab and highlight search text

        Args:
            line_idx: Line index in the commit message
            search_text: Text to search for
            char_pos: Character position of the specific match to highlight bright (optional)
        """
        self.search_mgr.select_commit_msg_result(line_idx, search_text, char_pos)

    def highlight_all_matches_in_commit_msg_tab(self, text_widget, search_text, highlight_color):
        """Highlight all matches in commit message tab"""
        self.search_mgr.highlight_all_matches_in_commit_msg_tab(text_widget, search_text, highlight_color)

    def clear_commit_msg_tab_highlights(self, text_widget):
        """Clear search highlights from commit message tab"""
        self.search_mgr.clear_commit_msg_tab_highlights(text_widget)

    # Methods to support SearchResultDialog (which expects a viewer-like interface)
    @property
    def base_display(self):
        """Get base_display from current viewer"""
        viewer = self.get_current_viewer()
        return viewer.base_display if viewer else []

    @property
    def modified_display(self):
        """Get modified_display from current viewer"""
        viewer = self.get_current_viewer()
        return viewer.modified_display if viewer else []

    @property
    def base_line_nums(self):
        """Get base_line_nums from current viewer"""
        viewer = self.get_current_viewer()
        return viewer.base_line_nums if viewer else []

    @property
    def modified_line_nums(self):
        """Get modified_line_nums from current viewer"""
        viewer = self.get_current_viewer()
        return viewer.modified_line_nums if viewer else []

    def on_tab_changed(self, index):
        """Handle tab change to update sidebar button states"""
        # Save previous tab's buffer when switching away
        if self.last_content_tab_index is not None and self.last_content_tab_index >= 0:
            if self.last_content_tab_index < self.tab_widget.count():
                prev_widget = self.tab_widget.widget(self.last_content_tab_index)
                if prev_widget is not None:
                    prev_widget.save_buffer()

        self.update_button_states()
        self.update_view_menu_states()

        # Track last content tab if in content mode
        if self.focus_mode == 'content' and index >= 0:
            self.last_content_tab_index = index

        # Update scrollbars in the newly activated viewer
        viewer = self.get_viewer_at_index(index)
        if viewer:
            viewer.init_scrollbars()
            # Skip highlighting if we're in bulk loading mode
            if not self._bulk_loading:
                # Apply highlighting if this viewer hasn't been highlighted yet
                viewer.ensure_highlighting_applied()
            # Apply highlighting if this viewer needs an update
            if viewer._needs_highlighting_update:
                viewer.restart_highlighting()
                viewer._needs_highlighting_update = False
            # Refresh colors if this viewer needs a color update
            if viewer._needs_color_refresh:
                viewer.refresh_colors()
                viewer._needs_color_refresh = False
            # Reload if staged diff mode changed while this tab was not visible
            if viewer._needs_staged_mode_reload:
                file_class = viewer.file_class
                if isinstance(file_class, generate_viewer.FileButtonUnstaged):
                    self.reload_staged_viewer(viewer, file_class)

    def update_view_menu_states(self):
        """Enable/disable View menu items based on current tab type"""
        current_widget = self.tab_widget.currentWidget()
        is_diff_viewer = isinstance(current_widget, DiffViewer)
        has_tabs = self.tab_widget.count() > 0

        # Diff viewer specific options - grey out if not a diff viewer
        self.show_diff_map_action.setEnabled(is_diff_viewer)
        self.show_line_numbers_action.setEnabled(is_diff_viewer)
        self.show_tab_action.setEnabled(is_diff_viewer)
        self.show_trailing_ws_action.setEnabled(is_diff_viewer)
        self.show_intraline_action.setEnabled(is_diff_viewer)

        # Show Sidebar requires tabs to be open (matches focus mode logic)
        self.show_sidebar_action.setEnabled(has_tabs)

        # Auto-reload is always enabled (applies globally)
        # Cycle Stats is always enabled (applies globally)

    def update_button_states(self):
        """Update all item states in tree view based on open tabs and currently selected tab"""
        current_tab_index = self.tab_widget.currentIndex()

        # Update file items in tree view
        for file_class in self.file_classes:
            # Check if tab is open
            is_open = file_class in self.file_to_tab_index
            if is_open:
                tab_index = self.file_to_tab_index[file_class]
                if not (0 <= tab_index < self.tab_widget.count()):
                    is_open = False

            # Check if this tab is currently selected
            is_active = False
            if is_open:
                tab_index = self.file_to_tab_index[file_class]
                is_active = (tab_index == current_tab_index)

            self.sidebar_widget.update_file_state(file_class, is_open, is_active)

        # Update commit message item if it exists
        if self.commit_msg_button:
            is_open = 'commit_msg' in self.file_to_tab_index
            if is_open:
                tab_index = self.file_to_tab_index['commit_msg']
                if not (0 <= tab_index < self.tab_widget.count()):
                    is_open = False

            is_active = False
            if is_open:
                tab_index = self.file_to_tab_index['commit_msg']
                is_active = (tab_index == current_tab_index)

            # Update commit message item style in tree
            self.sidebar_widget.update_commit_msg_state(is_open, is_active)

        # Update Review Notes item if it exists
        if self.note_mgr.notes_button:
            is_open = 'review_notes' in self.file_to_tab_index
            if is_open:
                tab_index = self.file_to_tab_index['review_notes']
                if not (0 <= tab_index < self.tab_widget.count()):
                    is_open = False

            is_active = False
            if is_open:
                tab_index = self.file_to_tab_index['review_notes']
                is_active = (tab_index == current_tab_index)

            # Update Review Notes item style in tree
            self.sidebar_widget.update_notes_state(is_open, is_active)

    def get_staged_diff_mode(self):
        """Return the current staged diff mode."""
        return self.staged_diff_mode_

    def set_staged_diff_mode(self, mode):
        """Set the staged diff mode and update affected viewers.

        The current tab (if it's a staged file) is reloaded immediately.
        Other staged file tabs are marked dirty and reloaded when selected.
        """
        if mode == self.staged_diff_mode_:
            return

        self.staged_diff_mode_ = mode

        # Update sidebar visibility based on mode
        self.sidebar_widget.update_file_visibility_for_mode(
            self.file_classes, mode)

        # Find all open staged file viewers and mark them for reload
        current_index = self.tab_widget.currentIndex()
        for file_class in self.file_classes:
            if not isinstance(file_class, generate_viewer.FileButtonUnstaged):
                continue
            if file_class not in self.file_to_tab_index:
                continue

            tab_index = self.file_to_tab_index[file_class]
            viewer = self.tab_widget.widget(tab_index)
            if not isinstance(viewer, DiffViewer):
                continue

            if tab_index == current_index:
                # Current tab: reload immediately
                self.reload_staged_viewer(viewer, file_class)
            else:
                # Other tabs: mark dirty for reload on selection
                viewer._needs_staged_mode_reload = True

    def reload_staged_viewer(self, viewer, file_class):
        """Reload a staged file viewer with the current diff mode."""
        import diffmgrng as diffmgr

        url = file_class.options_.arg_dossier_url
        if url is not None:
            root_path = url
        else:
            root_path = file_class.root_path_

        base, modi = file_class.get_diff_paths(self.staged_diff_mode_, root_path)

        # Save current scroll position
        v_scroll_pos = viewer.base_text.verticalScrollBar().value()
        h_scroll_pos = viewer.base_text.horizontalScrollBar().value()

        # Clear line number area backgrounds
        viewer.base_line_area.line_backgrounds.clear()
        viewer.modified_line_area.line_backgrounds.clear()

        # Reset highlighting state
        viewer.highlighting_applied = False
        viewer.highlighting_in_progress = False
        viewer.highlighting_next_line = 0

        # Clear bookmarks
        viewer.bookmarked_lines.clear()
        viewer.base_text.bookmarked_lines.clear()
        viewer.modified_text.bookmarked_lines.clear()

        # Clear notes
        viewer.note_count = 0
        viewer.base_noted_lines.clear()
        viewer.modified_noted_lines.clear()
        viewer.base_text.noted_lines.clear()
        viewer.modified_text.noted_lines.clear()
        viewer.base_line_area.noted_lines.clear()
        viewer.modified_line_area.noted_lines.clear()

        # Clear existing data
        viewer.base_display = []
        viewer.modified_display = []
        viewer.base_line_nums = []
        viewer.modified_line_nums = []
        viewer.change_regions = []
        viewer.base_line_objects = []
        viewer.modified_line_objects = []

        # Update file paths
        viewer.base_file = base
        viewer.modified_file = modi

        # Reload diff
        desc = diffmgr.create_diff_descriptor(self.afr_,
                                              False,
                                              self.intraline_percent,
                                              self.dump_ir,
                                              base, modi)

        # Set changed region count
        viewer.set_changed_region_count(desc.base_.n_changed_regions_)

        for idx in range(len(desc.base_.lines_)):
            base_line = desc.base_.lines_[idx]
            modi_line = desc.modi_.lines_[idx]
            viewer.add_line(base_line, modi_line)

        viewer.finalize()
        viewer.ensure_highlighting_applied()

        # Restore scroll position
        viewer.base_text.verticalScrollBar().setValue(v_scroll_pos)
        viewer.base_text.horizontalScrollBar().setValue(h_scroll_pos)
        viewer.modified_text.verticalScrollBar().setValue(v_scroll_pos)
        viewer.modified_text.horizontalScrollBar().setValue(h_scroll_pos)

        viewer._needs_staged_mode_reload = False

    def has_any_staged_content(self):
        """Return True if any file has staged content (for HEAD vs Staged mode).

        This includes:
        - FileButton instances (staged-only files, always show HEAD vs Staged)
        - FileButtonUnstaged instances where has_staged() is True
        """
        for file_class in self.file_classes:
            if isinstance(file_class, generate_viewer.FileButtonUnstaged):
                if file_class.has_staged():
                    return True
            elif isinstance(file_class, generate_viewer.FileButton):
                # FileButton is used for staged-only files in uncommitted mode
                return True
        return False

    def has_any_staged_and_unstaged(self):
        """Return True if any file has both staged and unstaged changes.

        Only FileButtonUnstaged instances with has_staged() True qualify.
        """
        for file_class in self.file_classes:
            if isinstance(file_class, generate_viewer.FileButtonUnstaged):
                if file_class.has_staged():
                    return True
        return False

    def update_compare_menu_state(self):
        """Enable/disable Compare menu items based on staged content availability."""
        if self.review_mode_ == "committed":
            return

        has_staged_content = self.has_any_staged_content()
        has_staged_and_unstaged = self.has_any_staged_and_unstaged()

        self.compare_base_stage_action.setEnabled(has_staged_content)
        self.compare_stage_modi_action.setEnabled(has_staged_and_unstaged)

        # If current mode is not available, reset to default mode
        if (self.staged_diff_mode_ == generate_viewer.DIFF_MODE_BASE_STAGE
                and not has_staged_content):
            self.compare_base_modi_action.setChecked(True)
            self.set_staged_diff_mode(generate_viewer.DIFF_MODE_BASE_MODI)
        elif (self.staged_diff_mode_ == generate_viewer.DIFF_MODE_STAGE_MODI
                and not has_staged_and_unstaged):
            self.compare_base_modi_action.setChecked(True)
            self.set_staged_diff_mode(generate_viewer.DIFF_MODE_BASE_MODI)

    def get_all_viewers(self):
        """
        Get all DiffViewer instances across all tabs.

        Returns:
            List of DiffViewer instances
        """
        viewers = []
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if isinstance(widget, DiffViewer):
                viewers.append(widget)
        return viewers

    def get_current_viewer(self):
        """
        Get the currently active DiffViewer instance.

        Returns:
            The DiffViewer instance in the current tab, or None if no tabs
        """
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, DiffViewer):
            return current_widget
        return None

    def get_viewer_at_index(self, index):
        """
        Get the DiffViewer instance at a specific tab index.

        Args:
            index: Tab index

        Returns:
            The DiffViewer instance at that index, or None if invalid index
        """
        if 0 <= index < self.tab_widget.count():
            widget = self.tab_widget.widget(index)
            if isinstance(widget, DiffViewer):
                return widget
        return None

    def close_tab(self, index):
        """Close the tab at the given index"""
        if index >= 0 and index < self.tab_widget.count():
            widget = self.tab_widget.widget(index)

            # Save buffer before closing
            if widget is not None:
                widget.save_buffer()
                # For external editors, also quit the editor cleanly
                if widget.is_terminal_widget():
                    widget.quit_editor()
                    import time
                    time.sleep(0.15)  # Give editor time to exit
                    # Reap the child process to prevent zombies
                    process_pid = widget.get_process_pid()
                    if process_pid is not None:
                        try:
                            os.waitpid(process_pid, os.WNOHANG)
                        except (ChildProcessError, OSError):
                            pass

            # Clean up file watcher if this is a DiffViewer
            if hasattr(widget, 'base_file'):
                self.cleanup_file_watcher(widget)

            # Clean up bookmarks for this tab
            self.bookmark_mgr.cleanup_tab_bookmarks(index)

            # Check if this is the commit message tab
            if isinstance(widget, CommitMessageTab):
                if 'commit_msg' in self.file_to_tab_index:
                    del self.file_to_tab_index['commit_msg']
            # Check if this is the review notes tab (built-in or external editor)
            elif isinstance(widget, ReviewNotesTabBase) or (widget.is_terminal_widget() and getattr(widget, 'is_review_notes', False)):
                if 'review_notes' in self.file_to_tab_index:
                    del self.file_to_tab_index['review_notes']
            # Regular file tab
            elif hasattr(widget, 'file_class'):
                file_class = widget.file_class
                if file_class in self.file_to_tab_index:
                    del self.file_to_tab_index[file_class]

            # Update indices in mapping for tabs after this one
            for key, tab_idx in list(self.file_to_tab_index.items()):
                if tab_idx > index:
                    self.file_to_tab_index[key] = tab_idx - 1

            # Update tab_index in remaining viewers
            for i in range(self.tab_widget.count()):
                w = self.tab_widget.widget(i)
                if isinstance(w, DiffViewer):
                    w.tab_index = i

            self.tab_widget.removeTab(index)

            # Clear last_content_tab_index if we closed that tab
            # (prevents save_buffer being called on a new tab at the same index)
            if self.last_content_tab_index == index:
                self.last_content_tab_index = None
            elif self.last_content_tab_index is not None and self.last_content_tab_index > index:
                # Adjust for shifted indices
                self.last_content_tab_index -= 1

            # Delete the widget to prevent dangling references
            if widget is not None:
                widget.deleteLater()

            # Update button states after closing
            self.update_button_states()

            # Give focus to the new current tab (if any remain)
            if self.tab_widget.count() > 0:
                current_widget = self.tab_widget.currentWidget()
                if current_widget:
                    current_widget.focus_content()
            else:
                # No tabs remain, focus sidebar
                self.focus_mode = 'sidebar'
                self.sidebar_widget.tree.setFocus()
                self.update_focus_tinting()
                self.update_status_focus_indicator()

            # If no tabs remain, ensure sidebar is visible
            if self.tab_widget.count() == 0 and not self.sidebar_visible:
                self.toggle_sidebar()

    def close_current_tab(self):
        """Close the currently active tab"""
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            self.close_tab(current_index)

    def handle_editor_subprocess_exit(self, exit_code):
        """Handle editor subprocess exit by closing the associated tab"""
        sender_widget = self.sender()
        if sender_widget is None:
            return

        for i in range(self.tab_widget.count()):
            if self.tab_widget.widget(i) == sender_widget:
                self.close_tab(i)
                break

    def _should_block_shortcut_for_terminal(self):
        """Check if a shortcut should be blocked because a terminal is focused without escape prefix.

        Returns True if the current widget is a terminal, focus is on content,
        and the escape prefix is not active.
        """
        current_widget = self.tab_widget.currentWidget()
        if (current_widget is not None and
                current_widget.is_terminal_widget() and
                self.focus_mode == 'content' and
                not current_widget.is_escape_prefix_active()):
            return True
        return False

    def next_tab(self):
        """Navigate to next tab (left-to-right, wraps around)"""
        if self._should_block_shortcut_for_terminal():
            return
        if self.tab_widget.count() > 0:
            current = self.tab_widget.currentIndex()
            next_index = (current + 1) % self.tab_widget.count()
            self.tab_widget.setCurrentIndex(next_index)
            # Give focus to the new tab
            current_widget = self.tab_widget.currentWidget()
            if current_widget:
                current_widget.focus_content()

    def prev_tab(self):
        """Navigate to previous tab (right-to-left, wraps around)"""
        if self._should_block_shortcut_for_terminal():
            return
        if self.tab_widget.count() > 0:
            current = self.tab_widget.currentIndex()
            prev_index = (current - 1) % self.tab_widget.count()
            self.tab_widget.setCurrentIndex(prev_index)
            # Give focus to the new tab
            current_widget = self.tab_widget.currentWidget()
            if current_widget:
                current_widget.focus_content()

    def toggle_sidebar(self):
        """Toggle sidebar visibility"""
        # Cannot hide sidebar when no content tabs are open
        if self.sidebar_visible and self.tab_widget.count() == 0:
            return

        if self.sidebar_visible:
            # Hiding the sidebar
            # If currently in sidebar context, switch to content and focus last content tab
            if self.focus_mode == 'sidebar':
                self.focus_mode = 'content'
                # Focus the last focused content tab, or leftmost if none
                if self.last_content_tab_index is not None and self.last_content_tab_index < self.tab_widget.count():
                    self.tab_widget.setCurrentIndex(self.last_content_tab_index)
                else:
                    self.tab_widget.setCurrentIndex(0)
                current_widget = self.tab_widget.currentWidget()
                if current_widget:
                    current_widget.focus_content()
                self.update_focus_tinting()
                self.update_status_focus_indicator()

            # Save current splitter sizes before hiding
            self.saved_splitter_sizes = self.splitter.sizes()
            self.sidebar_container.hide()
            self.sidebar_visible = False
            # Expand content area to fill the freed space
            total_width = sum(self.saved_splitter_sizes)
            self.splitter.setSizes([0, total_width])
        else:
            # Showing the sidebar
            self.sidebar_container.show()
            self.sidebar_visible = True
            # Restore previous splitter sizes, or use default if not saved
            if self.saved_splitter_sizes:
                self.splitter.setSizes(self.saved_splitter_sizes)
            else:
                self.splitter.setSizes([250, 1350])

        # Update checkbox state
        self.show_sidebar_action.setChecked(self.sidebar_visible)

        # Update scrollbars in current viewer after sidebar toggle
        current_viewer = self.get_current_viewer()
        if current_viewer:
            # Trigger scrollbar recalculation
            current_viewer.init_scrollbars()

    def toggle_diff_map(self):
        """Toggle diff map in all viewers"""
        self.view_state_mgr.toggle_diff_map()
        # Sync local state
        self.diff_map_visible = self.view_state_mgr.diff_map_visible

    def toggle_line_numbers(self):
        """Toggle line numbers in all viewers"""
        self.view_state_mgr.toggle_line_numbers()
        # Sync local state
        self.line_numbers_visible = self.view_state_mgr.line_numbers_visible

    def toggle_auto_reload(self):
        """Toggle auto-reload preference"""
        # Get the checkbox state first
        checked = self.auto_reload_action.isChecked()
        # Update file watcher manager
        self.file_watcher_mgr.auto_reload_enabled = checked
        # Let it handle the toggle logic
        self.auto_reload_enabled = self.file_watcher_mgr.toggle_auto_reload()

    def cycle_stats_display(self):
        """Cycle through stats display modes: 0=none, 1=tabs, 2=sidebar"""
        # Increment mode modulo 3
        self.stats_display_mode = (self.stats_display_mode + 1) % 3

        # Update individual flags based on mode
        if self.stats_display_mode == 0:
            # No stats
            self.tab_label_stats = False
            self.file_label_stats = False
        elif self.stats_display_mode == 1:
            # Tab stats only
            self.tab_label_stats = True
            self.file_label_stats = False
        else:  # mode == 2
            # Sidebar stats only
            self.tab_label_stats = False
            self.file_label_stats = True

        # Update all file buttons to use new settings
        for file_class in self.file_buttons:
            file_class.set_stats_tab(self.tab_label_stats)
            file_class.set_stats_file(self.file_label_stats)
            self.sidebar_widget.update_file_label(file_class)


        # Re-render all tab labels
        for file_class, tab_index in self.file_to_tab_index.items():
            # Skip commit_msg and review_notes - they don't have file_class
            if isinstance(file_class, str):
                continue

            if 0 <= tab_index < self.tab_widget.count():
                new_label = file_class.tab_label()
                self.tab_widget.setTabText(tab_index, new_label)

        # Update menu action text with current mode in bold
        self._update_stats_menu_text()

        # Show brief status message
        mode_names = ["None", "Tabs Only", "Sidebar Only"]
        self.statusBar().showMessage(f"Stats Display: {mode_names[self.stats_display_mode]}", 2000)

    def _update_stats_menu_text(self):
        """Update the Cycle Stats Display menu text with current mode marked by square brackets"""
        if self.stats_display_mode == 0:
            text = "Cycle Stats Display ([None] -> Tabs -> Sidebar)"
        elif self.stats_display_mode == 1:
            text = "Cycle Stats Display (None -> [Tabs] -> Sidebar)"
        else:  # mode == 2
            text = "Cycle Stats Display (None -> Tabs -> [Sidebar])"
        self.cycle_stats_action.setText(text)

    def increase_font_size(self):
        """Increase font size in current tab"""
        current_widget = self.tab_widget.currentWidget()
        if current_widget:
            current_widget.increase_font_size()

    def decrease_font_size(self):
        """Decrease font size in current tab"""
        current_widget = self.tab_widget.currentWidget()
        if current_widget:
            current_widget.decrease_font_size()

    def reset_font_size(self):
        """Reset font size to default in current tab"""
        current_widget = self.tab_widget.currentWidget()
        if current_widget:
            current_widget.reset_font_size()

    def toggle_tab_visibility(self):
        """Toggle tab character visibility in all viewers"""
        self.view_state_mgr.toggle_tab_visibility()
        # Sync local state
        self.ignore_tab = self.view_state_mgr.ignore_tab

    def toggle_trailing_ws_visibility(self):
        """Toggle trailing whitespace visibility in all viewers"""
        self.view_state_mgr.toggle_trailing_ws_visibility()
        # Sync local state
        self.ignore_trailing_ws = self.view_state_mgr.ignore_trailing_ws

    def toggle_intraline_visibility(self):
        """Toggle intraline changes visibility in all viewers"""
        self.view_state_mgr.toggle_intraline_visibility()
        # Sync local state
        self.ignore_intraline = self.view_state_mgr.ignore_intraline

    def setup_file_watcher(self, viewer):
        """Set up file system watching for a viewer's files"""
        self.file_watcher_mgr.setup_file_watcher(viewer)

    def on_file_changed(self, viewer, path):
        """Handle file change notification"""
        self.file_watcher_mgr.on_file_changed(viewer, path)

    def process_file_changes(self, viewer):
        """Process accumulated file changes after debounce period"""
        self.file_watcher_mgr.process_file_changes(viewer)

    def mark_tab_changed(self, viewer, changed):
        """Mark a viewer as having changed files by updating sidebar button color"""
        self.file_watcher_mgr.mark_tab_changed(viewer, changed)

    def reload_viewer(self, viewer):
        """Reload a viewer's diff data"""
        import diffmgrng as diffmgr

        # Save current scroll position
        v_scroll_pos = viewer.base_text.verticalScrollBar().value()
        h_scroll_pos = viewer.base_text.horizontalScrollBar().value()

        # Clear line number area backgrounds (O(1) operation)
        viewer.base_line_area.line_backgrounds.clear()
        viewer.modified_line_area.line_backgrounds.clear()

        # Reset highlighting state
        viewer.highlighting_applied = False
        viewer.highlighting_in_progress = False
        viewer.highlighting_next_line = 0

        # Clear existing data
        viewer.base_display = []
        viewer.modified_display = []
        viewer.base_line_nums = []
        viewer.modified_line_nums = []
        viewer.change_regions = []
        viewer.base_line_objects = []
        viewer.modified_line_objects = []

        # Reload diff
        try:
            desc = diffmgr.create_diff_descriptor(self.afr_,
                                                  False,
                                                  self.intraline_percent,
                                                  self.dump_ir,
                                                  viewer.base_file,
                                                  viewer.modified_file)

            for idx in range(len(desc.base_.lines_)):
                base = desc.base_.lines_[idx]
                modi = desc.modi_.lines_[idx]
                viewer.add_line(base, modi)

            viewer.finalize()

            # Since this viewer is currently visible (being reloaded), apply highlighting now
            viewer.ensure_highlighting_applied()

            # Restore scroll position
            viewer.base_text.verticalScrollBar().setValue(v_scroll_pos)
            viewer.base_text.horizontalScrollBar().setValue(h_scroll_pos)
            viewer.modified_text.verticalScrollBar().setValue(v_scroll_pos)
            viewer.modified_text.horizontalScrollBar().setValue(h_scroll_pos)

            # Clear changed files for this viewer
            self.file_watcher_mgr.clear_changed_files(viewer)

            # Remove changed indicator from tab
            self.mark_tab_changed(viewer, False)

            # Re-add files to watcher (they may have been removed by some editors)
            self.file_watcher_mgr.re_add_watched_files(viewer)

            # Show brief notification
            self.statusBar().showMessage("File reloaded", 2000)  # 2 second message

        except Exception as e:
            QMessageBox.warning(self, 'Reload Error', f'Could not reload files:\n{str(e)}')

    def cleanup_file_watcher(self, viewer):
        """Clean up file watcher for a viewer being closed"""
        self.file_watcher_mgr.cleanup_file_watcher(viewer)

    def show_help(self):
        """Show help dialog - reuses existing instance if open"""
        if self.help_dialog is None or not self.help_dialog.isVisible():
            self.help_dialog = HelpDialog(self)
            self.help_dialog.show()
        else:
            self.help_dialog.raise_()
            self.help_dialog.activateWindow()

    def show_shortcuts(self):
        """Show keyboard shortcuts reference - reuses existing instance if open"""
        if self.shortcuts_dialog is None or not self.shortcuts_dialog.isVisible():
            self.shortcuts_dialog = ShortcutsDialog(
                self,
                keybindings=self.keybindings,
                diff_keybindings=self.diff_keybindings,
                commit_msg_keybindings=self.commit_msg_keybindings,
                terminal_keybindings=self.terminal_keybindings
            )
            self.shortcuts_dialog.show()
        else:
            self.shortcuts_dialog.raise_()
            self.shortcuts_dialog.activateWindow()

    def switch_palette(self, palette_name):
        """Switch to a different color palette and refresh all viewers"""
        if color_palettes.set_current_palette(palette_name):
            # Refresh current viewer immediately
            viewer = self.get_current_viewer()
            if viewer:
                viewer.refresh_colors()
            # Mark all other viewers as needing color refresh
            for v in self.get_all_viewers():
                if v != viewer:
                    v._needs_color_refresh = True

    def _is_sequence_prefix(self, sequence, context_keybindings=None):
        """Check if sequence is a prefix of any valid keybinding"""
        # Check global keybindings
        for valid_seq in self.keybindings.sequence_to_action.keys():
            if len(sequence.keys) <= len(valid_seq.keys):
                if valid_seq.keys[:len(sequence.keys)] == sequence.keys:
                    return True
        
        # Check context-specific keybindings if provided
        if context_keybindings:
            for valid_seq in context_keybindings.sequence_to_action.keys():
                if len(sequence.keys) <= len(valid_seq.keys):
                    if valid_seq.keys[:len(sequence.keys)] == sequence.keys:
                        return True
        
        return False

    def _is_potential_sequence_start(self, key_tuple, context_keybindings=None):
        """Check if a single key press could be the start of a multi-key sequence"""
        test_seq = keybindings.KeySequence([key_tuple])
        return self._is_sequence_prefix(test_seq, context_keybindings)

    def _execute_action(self, action):
        """Execute the action associated with a keybinding"""
        viewer = self.get_current_viewer()
        current_widget = self.tab_widget.currentWidget()

        # Font size actions work on any widget
        if action == 'increase_font':
            if current_widget:
                current_widget.increase_font_size()
            return
        elif action == 'decrease_font':
            if current_widget:
                current_widget.decrease_font_size()
            return
        elif action == 'reset_font':
            if current_widget:
                current_widget.reset_font_size()
            return

        # Actions that work on any widget (including commit msg, review notes)
        if action == 'search':
            self.show_search_dialog()
            return
        elif action == 'shortcuts_help':
            self.show_shortcuts()
            return
        elif action == 'quit_application':
            self.close()
            return
        elif action == 'find_next':
            self.search_mgr.find_next()
            return
        elif action == 'find_prev':
            self.search_mgr.find_previous()
            return
        elif action == 'close_tab':
            current_index = self.tab_widget.currentIndex()
            if current_index >= 0:
                self.tab_widget.tabCloseRequested.emit(current_index)
            return
        elif action == 'next_tab':
            count = self.tab_widget.count()
            if count > 0:
                current = self.tab_widget.currentIndex()
                self.tab_widget.setCurrentIndex((current + 1) % count)
            return
        elif action == 'prev_tab':
            count = self.tab_widget.count()
            if count > 0:
                current = self.tab_widget.currentIndex()
                self.tab_widget.setCurrentIndex((current - 1) % count)
            return
        elif action == 'first_file':
            if self.tab_widget.count() > 0:
                self.tab_widget.setCurrentIndex(0)
            return
        elif action == 'last_file':
            count = self.tab_widget.count()
            if count > 0:
                self.tab_widget.setCurrentIndex(count - 1)
            return
        elif action == 'toggle_sidebar':
            self.toggle_sidebar()
            return
        elif action == 'toggle_focus_mode':
            self.toggle_focus_mode()
            return
        elif action == 'toggle_diff_map':
            self.toggle_diff_map()
            return
        elif action == 'toggle_line_numbers':
            self.toggle_line_numbers()
            return
        elif action == 'toggle_tab_highlight':
            self.toggle_tab_visibility()
            return
        elif action == 'toggle_eol_highlight':
            self.toggle_trailing_ws_visibility()
            return
        elif action == 'toggle_intraline':
            self.toggle_intraline_visibility()
            return
        elif action == 'cycle_file_change_stats':
            self.cycle_stats_display()
            return

        # Cursor movement and selection actions - synthesize key events for the focused widget
        if action and (action.startswith('cursor_') or action.startswith('select_')):
            current_widget = self.tab_widget.currentWidget()
            if current_widget:
                from PyQt6.QtGui import QKeyEvent
                from PyQt6.QtCore import QEvent
                
                # Map cursor/select actions to Qt keys
                cursor_key_map = {
                    'cursor_up': Qt.Key.Key_Up,
                    'cursor_down': Qt.Key.Key_Down,
                    'cursor_left': Qt.Key.Key_Left,
                    'cursor_right': Qt.Key.Key_Right,
                    'cursor_pageup': Qt.Key.Key_PageUp,
                    'cursor_pagedown': Qt.Key.Key_PageDown,
                    'cursor_home': Qt.Key.Key_Home,
                    'cursor_end': Qt.Key.Key_End,
                    'select_up': Qt.Key.Key_Up,
                    'select_down': Qt.Key.Key_Down,
                    'select_left': Qt.Key.Key_Left,
                    'select_right': Qt.Key.Key_Right,
                    'select_pageup': Qt.Key.Key_PageUp,
                    'select_pagedown': Qt.Key.Key_PageDown,
                }
                
                qt_key = cursor_key_map.get(action)
                if qt_key:
                    # Determine if this is a select action (needs Shift modifier)
                    modifiers = Qt.KeyboardModifier.ShiftModifier if action.startswith('select_') else Qt.KeyboardModifier.NoModifier
                    
                    # Find the focused text widget
                    focused_widget = None
                    if viewer:
                        if viewer.base_text.hasFocus():
                            focused_widget = viewer.base_text
                        elif viewer.modified_text.hasFocus():
                            focused_widget = viewer.modified_text
                    else:
                        # For notes or commit_msg tabs
                        focused_widget = current_widget
                    
                    if focused_widget:
                        # Create and send a key press event
                        key_event = QKeyEvent(QEvent.Type.KeyPress, qt_key, modifiers)
                        focused_widget.keyPressEvent(key_event)
                        return

        # Bookmark navigation works from any tab type
        if action == 'next_bookmark':
            self.bookmark_mgr.navigate_to_next_bookmark()
            return
        elif action == 'prev_bookmark':
            self.bookmark_mgr.navigate_to_prev_bookmark()
            return

        # Actions that require a viewer
        if not viewer:
            return

        if action == 'next_change':
            viewer.next_change()
        elif action == 'prev_change':
            viewer.prev_change()
        elif action == 'top_of_file':
            viewer.current_region = 0
            if viewer.change_regions:
                viewer.center_on_line(0)
            viewer.update_status()
        elif action == 'bottom_of_file':
            if viewer.change_regions:
                viewer.current_region = len(viewer.change_regions) - 1
                viewer.center_on_line(len(viewer.base_display) - 1)
            viewer.update_status()
        elif action == 'toggle_bookmark':
            viewer.toggle_bookmark()
        elif action == 'center_region':
            viewer.center_current_region()
        elif action == 'toggle_collapse_region':
            if viewer.base_text.hasFocus():
                line_idx = viewer.base_text.textCursor().blockNumber()
            elif viewer.modified_text.hasFocus():
                line_idx = viewer.modified_text.textCursor().blockNumber()
            else:
                return

            if viewer.is_line_in_collapsed_region(line_idx):
                viewer.uncollapse_region(line_idx)
            elif viewer.is_change_region(line_idx):
                viewer.collapse_change_region(line_idx)
        elif action == 'toggle_collapse_all':
            if viewer.collapsed_regions:
                viewer.uncollapse_all_regions()
            else:
                viewer.collapse_all_change_regions()
        elif action == 'reload':
            # Reload works for viewers, notes, and commit_msg tabs
            current_widget = self.tab_widget.currentWidget()
            if current_widget:
                if viewer:
                    self.reload_viewer(viewer)
                else:
                    # For notes or commit_msg tabs
                    current_widget.reload()
        elif action == 'take_note':
            if viewer.base_text.hasFocus():
                viewer.take_note_from_widget('base')
            elif viewer.modified_text.hasFocus():
                viewer.take_note_from_widget('modified')
        elif action == 'jump_to_note':
            viewer.jump_to_note_from_cursor()
        elif action == 'toggle_base_modi_focus':
            if not viewer.base_text.hasFocus():
                viewer.base_text.setFocus()
            else:
                viewer.modified_text.setFocus()

    def keyPressEvent(self, event):
        """Handle key press events using configurable keybindings"""
        key = event.key()
        modifiers = event.modifiers()

        # Ignore modifier-only key presses (Shift, Ctrl, Alt, Meta by themselves)
        if key in (Qt.Key.Key_Shift, Qt.Key.Key_Control, Qt.Key.Key_Alt,
                   Qt.Key.Key_Meta, Qt.Key.Key_AltGr, Qt.Key.Key_CapsLock):
            return

        # Build current key press as (qt_key, modifiers)
        current_key = (key, modifiers)

        # Add to pending sequence
        self.pending_keys.append(current_key)

        # Get context-specific keybindings for current widget
        current_widget = self.tab_widget.currentWidget()
        context_keybindings = self._get_keybindings_for_widget(current_widget) if current_widget else self.keybindings

        # Try to match current sequence in global keybindings first
        sequence = keybindings.KeySequence(self.pending_keys[:])
        action = self.keybindings.get_action(sequence)
        
        # If not found in global, try context-specific
        if not action and context_keybindings != self.keybindings:
            action = context_keybindings.get_action(sequence)

        if action:
            # Found a complete match - execute action
            self.pending_keys = []
            self._execute_action(action)
            return

        # Check if current sequence is a prefix of any valid sequence (global or context-specific)
        is_prefix = self._is_sequence_prefix(sequence, context_keybindings)

        if not is_prefix:
            # Not a valid prefix - reset and pass to parent
            self.pending_keys = []
            super().keyPressEvent(event)
            return

        # Valid prefix - wait for more keys
        # (pending_keys remains populated)

    def _get_keybindings_for_widget(self, widget):
        """
        Get the appropriate keybindings instance for a widget.
        
        Args:
            widget: The widget to determine keybindings for
            
        Returns:
            KeyBindings instance (diff_keybindings, note_keybindings, commit_msg_keybindings, or global keybindings)
        """
        from diff_viewer import DiffViewer
        from note_manager import ReviewNotesTabBase
        from commit_msg_handler import CommitMessageTab
        
        # Walk up parent hierarchy to find the tab content widget
        current = widget
        while current is not None:
            if isinstance(current, DiffViewer):
                return self.diff_keybindings
            elif isinstance(current, ReviewNotesTabBase):
                return self.note_keybindings
            elif isinstance(current, CommitMessageTab):
                return self.commit_msg_keybindings
            current = current.parent()
        
        # Default to global keybindings
        return self.keybindings

    def eventFilter(self, obj, event):
        """Filter events from text widgets to handle Tab key and Ctrl+N"""
        # DEBUG: Track Tab events to ALL objects
        if event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Tab or event.key() == Qt.Key.Key_Backtab:
                pass  # Could add logging here if needed

        # Handle mouse press events for focus switching
        if event.type() == event.Type.MouseButtonPress:
            # Determine if the click is in the sidebar or content area
            # by walking up the widget hierarchy
            widget = obj
            in_sidebar = False
            in_content = False
            is_tree_widget = (obj == self.sidebar_widget.tree)

            while widget is not None:
                if widget == self.sidebar_widget:
                    in_sidebar = True
                    break
                elif widget == self.tab_widget:
                    in_content = True
                    break
                widget = widget.parent()

            # Switch focus based on which area was clicked
            # Don't update focus_mode for tree clicks - let on_item_clicked handle it
            if in_sidebar and self.focus_mode != 'sidebar' and not is_tree_widget:
                self.focus_mode = 'sidebar'
                self.update_focus_tinting()
                self.update_status_focus_indicator()
            elif in_content and self.focus_mode != 'content' and self.tab_widget.count() > 0:
                self.focus_mode = 'content'
                self.update_focus_tinting()
                self.update_status_focus_indicator()

        if event.type() == event.Type.KeyPress:
            # Only process events for widgets that are part of our application
            # Let dialogs and other Qt widgets handle their own events

            is_our_widget = False
            widget = obj
            while widget is not None:
                # Check if this is a diff viewer text widget
                if isinstance(widget.parent() if widget.parent() else None, DiffViewer):
                    is_our_widget = True
                    break
                # Check if this is a commit message text widget
                if isinstance(widget.parent() if widget.parent() else None, CommitMessageTab):
                    is_our_widget = True
                    break
                # Check if this is a sidebar widget
                if widget == self.sidebar_widget or (widget.parent() and widget.parent() == self.sidebar_widget):
                    is_our_widget = True
                    break
                # Check if this is a terminal widget
                if isinstance(widget, TabContentBase) and widget.is_terminal_widget():
                    is_our_widget = True
                    break
                widget = widget.parent()
            
            # If not our widget, let it handle its own events
            if not is_our_widget:
                return False
            
            key = event.key()
            modifiers = event.modifiers()

            # Normalize modifiers to ensure consistent comparison with keybindings
            # event.modifiers() can return KeyboardModifier(0) which may not equal
            # Qt.KeyboardModifier.NoModifier in direct comparison
            if not modifiers:
                modifiers = Qt.KeyboardModifier.NoModifier

            # Qt reports ShiftModifier for shifted symbols like $, %, etc.
            # But these symbols can't be typed without Shift, so the Shift is implicit.
            # Strip Shift for these keys to match user expectations.
            shifted_symbol_keys = {
                Qt.Key.Key_Exclam, Qt.Key.Key_At, Qt.Key.Key_NumberSign,
                Qt.Key.Key_Dollar, Qt.Key.Key_Percent, Qt.Key.Key_AsciiCircum,
                Qt.Key.Key_Ampersand, Qt.Key.Key_Asterisk, Qt.Key.Key_ParenLeft,
                Qt.Key.Key_ParenRight, Qt.Key.Key_Underscore, Qt.Key.Key_Plus,
                Qt.Key.Key_BraceLeft, Qt.Key.Key_BraceRight, Qt.Key.Key_Bar,
                Qt.Key.Key_Colon, Qt.Key.Key_QuoteDbl, Qt.Key.Key_Less,
                Qt.Key.Key_Greater, Qt.Key.Key_Question, Qt.Key.Key_AsciiTilde
            }
            if key in shifted_symbol_keys and modifiers & Qt.KeyboardModifier.ShiftModifier:
                modifiers = modifiers & ~Qt.KeyboardModifier.ShiftModifier
            
            viewer = self.get_current_viewer()

            # Check if current widget is a terminal widget - must be done early
            # to bypass all global key handling except terminal escape prefix.
            # Only apply terminal passthrough when focus is on content area,
            # not when sidebar has focus.
            current_widget = self.tab_widget.currentWidget()
            is_terminal = (current_widget is not None and
                           current_widget.is_terminal_widget() and
                           self.focus_mode == 'content')

            if is_terminal:
                # Build key sequence for keybinding checks
                current_key = (key, modifiers)
                sequence = keybindings.KeySequence([current_key])

                # Check terminal-specific bindings (includes terminal_escape)
                terminal_action = self.terminal_keybindings.get_action(sequence)

                # Check if escape prefix is currently active
                if current_widget.is_escape_prefix_active():
                    # Ignore modifier-only key presses (Shift, Ctrl, Alt, Meta)
                    # These occur when pressing key combinations like Ctrl+Shift+Q
                    modifier_keys = (
                        Qt.Key.Key_Shift, Qt.Key.Key_Control,
                        Qt.Key.Key_Alt, Qt.Key.Key_Meta,
                        Qt.Key.Key_Super_L, Qt.Key.Key_Super_R,
                        Qt.Key.Key_Hyper_L, Qt.Key.Key_Hyper_R,
                        Qt.Key.Key_AltGr
                    )
                    if key in modifier_keys:
                        return True  # Consume but don't clear prefix

                    # Clear the prefix state (reverts border)
                    current_widget.set_escape_prefix_active(False)

                    # Check global keybindings first, then terminal-specific
                    global_action = self.keybindings.get_action(sequence)
                    if global_action:
                        self._execute_action(global_action)
                    elif terminal_action and terminal_action != 'terminal_escape':
                        # Execute terminal-specific action (e.g., bookmark navigation)
                        self._execute_action(terminal_action)
                    # Consume the key either way (action executed or not)
                    return True

                # Check if this key is the terminal escape prefix
                if terminal_action == 'terminal_escape':
                    current_widget.set_escape_prefix_active(True)
                    return True

                # Let all other keys pass through to the terminal
                return False

            # Determine if the event originated from sidebar or content
            widget = obj
            in_sidebar = False
            in_content = False

            while widget is not None:
                if widget == self.sidebar_widget:
                    in_sidebar = True
                    break
                elif widget == self.tab_widget:
                    in_content = True
                    break
                widget = widget.parent()

            # Block Tab/Shift+Tab when in sidebar mode to prevent any focus navigation
            if self.focus_mode == 'sidebar' and key == Qt.Key.Key_Tab:
                return True

            # Block keyboard events based on focus mode
            if self.focus_mode == 'sidebar' and in_content:
                # Sidebar has focus, block content area keyboard events
                return True
            elif self.focus_mode == 'content' and in_sidebar:
                # Content has focus, block sidebar keyboard events
                return True

            # If we reach here, the keyboard event is allowed for the current focus mode

            # Check if this is the commit message widget
            is_commit_msg = isinstance(obj.parent(), CommitMessageTab) if obj.parent() else False

            # Get context-appropriate keybindings
            context_keybindings = self._get_keybindings_for_widget(obj)

            # Build current key press for keybinding check
            current_key = (key, modifiers)
            sequence = keybindings.KeySequence([current_key])
            action = context_keybindings.get_action(sequence)

            # Handle search action
            if action == 'search':
                self.show_search_dialog()
                return True

            # Handle take_note action - needs context about which pane
            if action == 'take_note':
                if is_commit_msg:
                    obj.parent().take_note()
                elif viewer:
                    if obj == viewer.base_text:
                        viewer.take_note_from_widget('base')
                    elif obj == viewer.modified_text:
                        viewer.take_note_from_widget('modified')
                return True  # Always consume this action here

            # Handle toggle_base_modi_focus action - needs cursor position sync
            if action == 'toggle_base_modi_focus':
                if not is_commit_msg and viewer:
                    if obj == viewer.base_text:
                        # Get current line in base
                        cursor = viewer.base_text.textCursor()
                        current_line = cursor.blockNumber()

                        # Move cursor in modified BEFORE switching focus
                        new_cursor = viewer.modified_text.textCursor()
                        new_cursor.movePosition(new_cursor.MoveOperation.Start)
                        for _ in range(current_line):
                            new_cursor.movePosition(new_cursor.MoveOperation.Down)
                        viewer.modified_text.setTextCursor(new_cursor)

                        # Now switch focus
                        viewer.modified_text.setFocus()
                        viewer.modified_text.ensureCursorVisible()

                    elif obj == viewer.modified_text:
                        # Get current line in modified
                        cursor = viewer.modified_text.textCursor()
                        current_line = cursor.blockNumber()

                        # Move cursor in base BEFORE switching focus
                        new_cursor = viewer.base_text.textCursor()
                        new_cursor.movePosition(new_cursor.MoveOperation.Start)
                        for _ in range(current_line):
                            new_cursor.movePosition(new_cursor.MoveOperation.Down)
                        viewer.base_text.setTextCursor(new_cursor)

                        # Now switch focus
                        viewer.base_text.setFocus()
                        viewer.base_text.ensureCursorVisible()
                return True  # Always consume this action here

            # If we found any other complete single-key action, execute it
            if action:
                self._execute_action(action)
                return True

            # Check if current key could be part of a multi-key sequence
            # by checking if it's a valid prefix OR continuing an existing sequence
            if self.pending_keys or self._is_potential_sequence_start(current_key, context_keybindings):
                # Forward to keyPressEvent for keybinding processing
                self.keyPressEvent(event)
                return True

        return False

    def toggle_focus_mode(self):
        """Toggle between sidebar and content focus modes"""
        if self.focus_mode == 'content':
            self.focus_mode = 'sidebar'
            # Ensure sidebar is visible when switching to sidebar context
            if not self.sidebar_visible:
                self.toggle_sidebar()
            # Give Qt focus to the tree widget
            self.sidebar_widget.tree.setFocus()
        elif self.tab_widget.count() > 0: # Only switch if there are tabs open.
            self.focus_mode = 'content'
            # Give Qt focus to the current content widget
            current_widget = self.tab_widget.currentWidget()
            if current_widget:
                current_widget.focus_content()
            # Track which content tab is focused
            self.last_content_tab_index = self.tab_widget.currentIndex()
        else:
            return

        self.update_focus_tinting()
        self.update_status_focus_indicator()

    def update_focus_tinting(self):
        """Apply background tinting based on current focus mode"""
        if self.focus_mode == 'sidebar':
            # Sidebar focused: hide sidebar overlay, show tab overlay
            self.sidebar_overlay.hide()
            self.tab_overlay.raise_()
            self.tab_overlay.show()
        else:  # content focused
            # Content focused: hide tab overlay, show sidebar overlay
            self.tab_overlay.hide()
            self.sidebar_overlay.raise_()
            self.sidebar_overlay.show()

    def update_status_focus_indicator(self):
        """Update status bar in current tab to show focus mode"""
        current_widget = self.tab_widget.currentWidget()
        if not current_widget:
            return

        # Check if it's a DiffViewer with a region_label
        if isinstance(current_widget, DiffViewer):
            focus_text = f"Focus: {'Sidebar' if self.focus_mode == 'sidebar' else 'Content'}"
            # The region_label is directly accessible on the DiffViewer
            # We'll update it to include focus mode, or add a separate label

    def run(self):
        """Show the window and start the application event loop"""

        # Add review notes button to sidebar if note file was provided.
        # It is done here to ensure it is last.
        note_file = self.note_mgr.get_note_file()
        if note_file is not None:
            self.note_mgr.create_notes_button()

        # Set initial View menu states
        self.update_view_menu_states()
        # Set initial Compare menu states (enable/disable based on staged content)
        self.update_compare_menu_state()
        # Apply initial focus tinting (sidebar focused, content dimmed)
        self.update_focus_tinting()
        self.show()
        return sys.exit(self._app.exec())
