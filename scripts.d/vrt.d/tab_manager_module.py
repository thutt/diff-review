# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
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
from commit_msg_handler import CommitMessageTab
from note_manager import ReviewNotesTab
from diff_viewer import DiffViewer


class DiffViewerTabWidget(QMainWindow):
    """Main window containing tabs of DiffViewer instances with file sidebar"""
    
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
                 file_label_stats  : bool):
        if QApplication.instance() is None:
            self._app = QApplication(sys.argv)
        else:
            self._app = QApplication.instance()
        
        super().__init__()
        
        self.afr_ = afr
        self.display_lines = display_lines
        self.display_chars = display_chars
        self.ignore_tab = ignore_tab
        self.ignore_trailing_ws = ignore_trailing_ws
        self.ignore_intraline = ignore_intraline
        self.dump_ir = dump_ir
        self.intraline_percent = intraline_percent
        self._bulk_loading = False  # Suppress highlighting during "Open All Files"
        
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
        
        # Global view state for all tabs
        self.diff_map_visible = show_diff_map  # Initial state for diff map
        self.line_numbers_visible = show_line_numbers  # Initial state for line numbers
        self.global_note_file = None  # Global note file for all viewers
        
        # Create view state manager
        self.view_state_mgr = view_state_manager.ViewStateManager(
            self, show_diff_map, show_line_numbers,
            ignore_tab, ignore_trailing_ws, ignore_intraline)
        
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
        self.note_mgr = note_manager.NoteManager(self)
        
        # Create search manager
        self.search_mgr = search_manager.SearchManager(self)
        
        # Keep reference for compatibility
        self.search_result_dialogs = self.search_mgr.search_result_dialogs
        
        # Focus mode: 'sidebar' or 'content'
        self.focus_mode = 'sidebar'  # Start with sidebar focused (files must be selected first)
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
        
        # Create sidebar with tree view
        self.sidebar_widget = file_tree_sidebar.FileTreeSidebar(self)
        
        # Keep references for backward compatibility
        self.open_all_button = self.sidebar_widget.open_all_button
        self.button_layout = None  # No longer used
        self.button_container = None  # No longer used
        
        # Add sidebar and tab widget to splitter
        self.splitter.addWidget(self.sidebar_widget)
        
        # Create tab widget
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
        
        self.splitter.addWidget(self.tab_widget)
        
        # Set initial splitter sizes (sidebar: 250px, main area: rest)
        self.splitter.setSizes([250, 1350])
        
        main_layout.addWidget(self.splitter)
        
        self.setCentralWidget(central)
        
        # Store base stylesheets for focus tinting
        self.sidebar_base_stylesheet = self.sidebar_widget.styleSheet()
        self.tab_widget_base_stylesheet = self.tab_widget.styleSheet()
        
        # Create overlay widgets for dimming without affecting layout
        self.sidebar_overlay = QWidget(self.sidebar_widget)
        self.sidebar_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        self.sidebar_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.sidebar_overlay.hide()
        
        self.tab_overlay = QWidget(self.tab_widget)
        self.tab_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")
        self.tab_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.tab_overlay.hide()
        
        # Install event filters to handle resizing
        self.sidebar_widget.installEventFilter(self)
        self.tab_widget.installEventFilter(self)

        # Install event filters on sidebar children to capture clicks
        self.sidebar_widget.tree.installEventFilter(self)
        self.sidebar_widget.open_all_button.installEventFilter(self)

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
        
        close_tab_action = QAction("Close Tab", self)
        close_tab_action.setShortcut(QKeySequence("Ctrl+W"))
        close_tab_action.triggered.connect(self.close_current_tab)
        file_menu.addAction(close_tab_action)
        
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        self.show_sidebar_action = QAction("Show Sidebar", self)
        self.show_sidebar_action.setShortcut(QKeySequence("Ctrl+B"))
        self.show_sidebar_action.setCheckable(True)
        self.show_sidebar_action.setChecked(True)  # Sidebar starts visible
        self.show_sidebar_action.triggered.connect(self.toggle_sidebar)
        view_menu.addAction(self.show_sidebar_action)
        
        view_menu.addSeparator()
        
        self.show_diff_map_action = QAction("Show Diff Map", self)
        self.show_diff_map_action.setShortcut(QKeySequence("Ctrl+D"))
        self.show_diff_map_action.setCheckable(True)
        self.show_diff_map_action.setChecked(show_diff_map)
        self.show_diff_map_action.triggered.connect(self.toggle_diff_map)
        view_menu.addAction(self.show_diff_map_action)
        
        self.show_line_numbers_action = QAction("Show Line Numbers", self)
        self.show_line_numbers_action.setShortcut(QKeySequence("Ctrl+L"))
        self.show_line_numbers_action.setCheckable(True)
        self.show_line_numbers_action.setChecked(show_line_numbers)
        self.show_line_numbers_action.triggered.connect(self.toggle_line_numbers)
        view_menu.addAction(self.show_line_numbers_action)
        
        view_menu.addSeparator()
        
        self.show_tab_action = QAction("Show Tabs", self)
        self.show_tab_action.setShortcut(QKeySequence("Ctrl+T"))
        self.show_tab_action.setCheckable(True)
        self.show_tab_action.setChecked(not ignore_tab)
        self.show_tab_action.triggered.connect(self.toggle_tab_visibility)
        view_menu.addAction(self.show_tab_action)
        
        self.show_trailing_ws_action = QAction("Show Trailing Whitespace", self)
        self.show_trailing_ws_action.setShortcut(QKeySequence("Ctrl+E"))
        self.show_trailing_ws_action.setCheckable(True)
        self.show_trailing_ws_action.setChecked(not ignore_trailing_ws)
        self.show_trailing_ws_action.triggered.connect(self.toggle_trailing_ws_visibility)
        view_menu.addAction(self.show_trailing_ws_action)
        
        self.show_intraline_action = QAction("Show Intraline Changes", self)
        self.show_intraline_action.setShortcut(QKeySequence("Ctrl+I"))
        self.show_intraline_action.setCheckable(True)
        self.show_intraline_action.setChecked(not ignore_intraline)
        self.show_intraline_action.triggered.connect(self.toggle_intraline_visibility)
        view_menu.addAction(self.show_intraline_action)
        
        view_menu.addSeparator()
        
        self.auto_reload_action = QAction("Auto-reload Files", self)
        self.auto_reload_action.setShortcut(QKeySequence("Ctrl+R"))
        self.auto_reload_action.setCheckable(True)
        self.auto_reload_action.setChecked(auto_reload)  # Set from parameter
        self.auto_reload_action.triggered.connect(self.toggle_auto_reload)
        view_menu.addAction(self.auto_reload_action)
        
        view_menu.addSeparator()
        
        self.cycle_stats_action = QAction("Cycle Stats Display (None -> Tabs -> Sidebar)", self)
        self.cycle_stats_action.setShortcut(QKeySequence("Ctrl+Y"))
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
        
        reset_font_action = QAction("Reset Font Size", self)
        reset_font_action.setShortcut(QKeySequence("Ctrl+0"))
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
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        shortcuts_action = QAction("Keyboard Shortcuts", self)
        shortcuts_action.setShortcuts([QKeySequence("Ctrl+?"), QKeySequence("F1")])
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
    
    def get_note_file(self):
        """Get note file - prefer global, fallback to any viewer"""
        if self.global_note_file:
            return self.global_note_file
        
        viewers = self.get_all_viewers()
        for viewer in viewers:
            if viewer.note_file:
                return viewer.note_file
        return None
    
    def open_note_file(self):
        """Open a note file using file picker dialog"""
        # Use getOpenFileName but with DontConfirmOverwrite since we're not overwriting
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Select Note File")
        file_dialog.setNameFilter("Text Files (*.txt);;All Files (*)")
        file_dialog.setFileMode(QFileDialog.FileMode.AnyFile)  # Allow typing non-existent files
        file_dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        file_dialog.setOption(QFileDialog.Option.DontConfirmOverwrite, True)  # Don't warn about overwrite
        file_dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)  # Use Qt dialog on macOS to allow typing
        
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            files = file_dialog.selectedFiles()
            if not files:
                return
            
            file_path = files[0]
            
            # Use NoteManager to set the note file - this creates button and updates count
            self.note_mgr.set_note_file(file_path)
            
            # Check if file exists to customize message
            import os
            if os.path.exists(file_path):
                msg = f"Note file set to:\n{file_path}\n\nAll viewers will now append notes to this existing file."
            else:
                msg = f"Note file set to:\n{file_path}\n\nThis file will be created when the first note is taken."
            
            # Show confirmation
            QMessageBox.information(
                self,
                "Note File Set",
                msg
            )
    
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
        if self.global_note_file and 'review_notes' not in self.file_to_tab_index:
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
                if widget.file_class == file_class:
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
        
        # Install event filter on text widgets to handle Tab key
        diff_viewer.installEventFilter(self)
        diff_viewer.base_text.installEventFilter(self)
        diff_viewer.modified_text.installEventFilter(self)

        # Install event filter on other visible child widgets to capture clicks
        if diff_viewer.base_line_area:
            diff_viewer.base_line_area.installEventFilter(self)
        if diff_viewer.modified_line_area:
            diff_viewer.modified_line_area.installEventFilter(self)
        if diff_viewer.diff_map:
            diff_viewer.diff_map.installEventFilter(self)
        if diff_viewer.v_scrollbar:
            diff_viewer.v_scrollbar.installEventFilter(self)
        if diff_viewer.h_scrollbar:
            diff_viewer.h_scrollbar.installEventFilter(self)
        
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
        
        # Apply global note file if set
        if self.global_note_file:
            diff_viewer.note_file = self.global_note_file
        elif diff_viewer.note_file:
            # Viewer has a note file (from --note-file) but global doesn't know about it
            # Notify NoteManager to create button and set up file watching
            self.note_mgr.set_note_file(diff_viewer.note_file)
            self.global_note_file = diff_viewer.note_file
        
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
        self.update_button_states()
        
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
            
            # Clean up file watcher if this is a DiffViewer
            if hasattr(widget, 'base_file'):
                self.cleanup_file_watcher(widget)
            
            # Clean up bookmarks for this tab
            self.bookmark_mgr.cleanup_tab_bookmarks(index)
            
            # Check if this is the commit message tab
            if isinstance(widget, CommitMessageTab):
                if 'commit_msg' in self.file_to_tab_index:
                    del self.file_to_tab_index['commit_msg']
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
                widget = self.tab_widget.widget(i)
                if isinstance(widget, DiffViewer):
                    widget.tab_index = i
            
            self.tab_widget.removeTab(index)
            
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
    
    def next_tab(self):
        """Navigate to next tab (left-to-right, wraps around)"""
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
        if self.sidebar_visible:
            self.sidebar_widget.hide()
            self.sidebar_visible = False
        else:
            self.sidebar_widget.show()
            self.sidebar_visible = True
        
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
            self.shortcuts_dialog = ShortcutsDialog(self)
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
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        key = event.key()
        modifiers = event.modifiers()
        
        # Get current viewer for most commands
        viewer = self.get_current_viewer()
        
        # F1 or Ctrl+? - Show keyboard shortcuts
        if key == Qt.Key.Key_F1 or (key == Qt.Key.Key_Question and
                                      modifiers & Qt.KeyboardModifier.ControlModifier):
            self.show_shortcuts()
            return
        
        # All other shortcuts require an active viewer
        if not viewer:
            super().keyPressEvent(event)
            return
        
        # Pass other events to parent
        super().keyPressEvent(event)
    
    def eventFilter(self, obj, event):
        """Filter events from text widgets to handle Tab key and Ctrl+N"""
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
            elif in_content and self.focus_mode != 'content':
                self.focus_mode = 'content'
                self.update_focus_tinting()
                self.update_status_focus_indicator()

        # Handle resize events for overlay widgets
        if event.type() == event.Type.Resize:
            if obj == self.sidebar_widget and self.sidebar_overlay.isVisible():
                self.sidebar_overlay.setGeometry(self.sidebar_widget.rect())
            elif obj == self.tab_widget and self.tab_overlay.isVisible():
                self.tab_overlay.setGeometry(self.tab_widget.rect())
        
        if event.type() == event.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            
            # Ctrl-\ - Toggle focus mode (handle before focus filtering)
            if key == Qt.Key.Key_Backslash and modifiers & Qt.KeyboardModifier.ControlModifier:
                self.toggle_focus_mode()
                return True
            
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
            
            # Block keyboard events based on focus mode
            if self.focus_mode == 'sidebar' and in_content:
                # Sidebar has focus, block content area keyboard events
                return True
            elif self.focus_mode == 'content' and in_sidebar:
                # Content has focus, block sidebar keyboard events
                return True
            
            # Block Tab key in sidebar mode (prevent Qt's default tab navigation)
            if self.focus_mode == 'sidebar' and in_sidebar and key == Qt.Key.Key_Tab:
                return True
            
            # If we reach here, the keyboard event is allowed for the current focus mode
            viewer = self.get_current_viewer()
            
            # Check if this is the commit message widget
            is_commit_msg = isinstance(obj.parent(), CommitMessageTab) if obj.parent() else False
        return False

    def toggle_focus_mode(self):
        """Toggle between sidebar and content focus modes"""
        if self.focus_mode == 'content':
            self.focus_mode = 'sidebar'
            # Give Qt focus to the tree widget
            self.sidebar_widget.tree.setFocus()
        else:
            self.focus_mode = 'content'
            # Give Qt focus to the current content widget
            current_widget = self.tab_widget.currentWidget()
            if current_widget:
                current_widget.focus_content()
        
        self.update_focus_tinting()
        self.update_status_focus_indicator()
    
    def update_focus_tinting(self):
        """Apply background tinting based on current focus mode"""
        if self.focus_mode == 'sidebar':
            # Sidebar focused: hide sidebar overlay, show tab overlay
            self.sidebar_overlay.hide()
            self.tab_overlay.setGeometry(self.tab_widget.rect())
            self.tab_overlay.raise_()
            self.tab_overlay.show()
        else:  # content focused
            # Content focused: hide tab overlay, show sidebar overlay
            self.tab_overlay.hide()
            self.sidebar_overlay.setGeometry(self.sidebar_widget.rect())
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
        self.show()
        return sys.exit(self._app.exec())
