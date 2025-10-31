#!/usr/bin/env python3
# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Tab manager for diff_review

This module contains the tab widget that manages multiple DiffViewer instances
with a sidebar for file selection.
"""
import sys
from PyQt6.QtWidgets import (QApplication, QTabWidget, QMainWindow, QHBoxLayout, 
                              QVBoxLayout, QWidget, QPushButton, QScrollArea, QSplitter,
                              QPlainTextEdit, QMenu, QMessageBox, QProgressDialog, QFileDialog)
from PyQt6.QtCore import Qt, QFileSystemWatcher, QTimer
from PyQt6.QtGui import (QAction, QFont, QKeySequence, QActionGroup, QFontMetrics, 
                         QColor, QTextDocument, QShortcut)

from help_dialog import HelpDialog
from search_dialogs import SearchDialog, SearchResultDialog
from commit_msg_dialog import CommitMsgDialog
import color_palettes


class FileButton(QPushButton):
    """Custom button for file selection in sidebar"""
    
    def __init__(self, file_class, parent=None):
        super().__init__(parent)
        self.file_class = file_class
        self.is_open = False       # Tab exists for this file
        self.is_active = False     # This tab is currently selected
        self.setText(file_class.button_label())
        self.setCheckable(False)
        self.setStyleSheet(self._get_stylesheet())
    
    def set_state(self, is_open, is_active):
        """Set whether this button's tab is open and/or currently active"""
        self.is_open = is_open
        self.is_active = is_active
        self.setStyleSheet(self._get_stylesheet())
    
    def _get_stylesheet(self):
        """Generate stylesheet based on open/active state"""
        if self.is_active:
            # Currently selected tab - bright highlight with thick border
            return """
                QPushButton {
                    text-align: left;
                    padding: 8px 8px 8px 20px;
                    border: none;
                    background-color: #e0e0e0;
                    border-left: 6px solid #0066cc;
                    font-weight: bold;
                    color: #000000;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                    color: #000000;
                }
            """
        elif self.is_open:
            # Tab is open but not selected - subtle highlight
            return """
                QPushButton {
                    text-align: left;
                    padding: 8px 8px 8px 20px;
                    border: none;
                    background-color: #f0f0f0;
                    border-left: 4px solid #0066cc;
                    color: #000000;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                    color: #000000;
                }
            """
        else:
            # Tab is closed - no highlight
            return """
                QPushButton {
                    text-align: left;
                    padding: 8px 8px 8px 20px;
                    border: none;
                    background-color: #f8f8f8;
                    border-left: 4px solid transparent;
                    color: #000000;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                    color: #000000;
                }
            """


class DiffViewerTabWidget(QMainWindow):
    """Main window containing tabs of DiffViewer instances with file sidebar"""
    
    def __init__(self, display_lines: int, display_chars: int, show_diff_map: bool,
                 show_line_numbers: bool, auto_reload: bool):
        if QApplication.instance() is None:
            self._app = QApplication(sys.argv)
        else:
            self._app = QApplication.instance()
        
        super().__init__()
        
        self.display_lines = display_lines
        self.display_chars = display_chars
        
        self.setWindowTitle("Diff Viewer")
        
        # Storage for file classes and their buttons
        self.file_classes = []
        self.file_buttons = []
        self.file_to_tab_index = {}  # Maps file_class to tab index
        self.current_file_class = None  # Track which file is being added
        self.sidebar_visible = True
        self._commit_msg_file = None  # Track commit message file (internal)
        self.commit_msg_button = None  # Track commit message button
        self.commit_msg_dialog = None  # Track commit message dialog
        self.search_result_dialogs = []  # Track search result dialogs
        
        # Global view state for all tabs
        self.diff_map_visible = show_diff_map  # Initial state for diff map
        self.line_numbers_visible = show_line_numbers  # Initial state for line numbers
        self.global_note_file = None  # Global note file for all viewers
        
        # File watching and auto-reload
        self.auto_reload_enabled = auto_reload  # Initial auto-reload state from parameter
        self.file_watchers = {}  # Maps viewer -> QFileSystemWatcher
        self.reload_timers = {}  # Maps viewer -> QTimer (for debouncing)
        self.changed_files = {}  # Maps viewer -> set of changed files
        
        # Create main layout
        central = QWidget()
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create splitter for resizable sidebar
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create sidebar
        self.sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(self.sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Scroll area for buttons
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.button_container = QWidget()
        self.button_layout = QVBoxLayout(self.button_container)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(0)
        
        # Add "Open All" button at the top
        self.open_all_button = QPushButton("Open All Files")
        self.open_all_button.clicked.connect(self.open_all_files)
        self.open_all_button.setStyleSheet("""
            QPushButton {
                text-align: center;
                padding: 10px;
                border: none;
                background-color: #e8f4f8;
                font-weight: bold;
                color: #0066cc;
            }
            QPushButton:hover {
                background-color: #d0e8f0;
            }
        """)
        self.button_layout.addWidget(self.open_all_button)
        
        self.button_layout.addStretch()
        
        scroll_area.setWidget(self.button_container)
        sidebar_layout.addWidget(scroll_area)
        
        # Add sidebar and tab widget to splitter
        self.splitter.addWidget(self.sidebar_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)  # Allow tabs to be reordered by dragging
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        self.splitter.addWidget(self.tab_widget)
        
        # Set initial splitter sizes (sidebar: 250px, main area: rest)
        self.splitter.setSizes([250, 1350])
        
        main_layout.addWidget(self.splitter)
        
        self.setCentralWidget(central)
        
        # Create menu bar
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_note_action = QAction("Open Note...", self)
        open_note_action.triggered.connect(self.open_note_file)
        file_menu.addAction(open_note_action)
        
        file_menu.addSeparator()
        
        close_tab_action = QAction("Close Tab", self)
        close_tab_action.setShortcut("Ctrl+W")
        close_tab_action.triggered.connect(self.close_current_tab)
        file_menu.addAction(close_tab_action)
        
        quit_action = QAction("Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        toggle_sidebar_action = QAction("Toggle Sidebar", self)
        toggle_sidebar_action.setShortcuts([QKeySequence("Ctrl+B"), QKeySequence("Meta+B")])
        toggle_sidebar_action.triggered.connect(self.toggle_sidebar)
        view_menu.addAction(toggle_sidebar_action)
        
        view_menu.addSeparator()
        
        toggle_diff_map_action = QAction("Toggle Diff Map", self)
        toggle_diff_map_action.setShortcuts([QKeySequence("Alt+H"), QKeySequence("Meta+H")])
        toggle_diff_map_action.triggered.connect(self.toggle_diff_map)
        view_menu.addAction(toggle_diff_map_action)
        
        toggle_line_numbers_action = QAction("Toggle Line Numbers", self)
        toggle_line_numbers_action.setShortcuts([QKeySequence("Alt+L"), QKeySequence("Meta+L")])
        toggle_line_numbers_action.triggered.connect(self.toggle_line_numbers)
        view_menu.addAction(toggle_line_numbers_action)
        
        view_menu.addSeparator()
        
        self.auto_reload_action = QAction("Auto-reload Files", self)
        self.auto_reload_action.setCheckable(True)
        self.auto_reload_action.setChecked(auto_reload)  # Set from parameter
        self.auto_reload_action.triggered.connect(self.toggle_auto_reload)
        view_menu.addAction(self.auto_reload_action)
        
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
        
        # Tab navigation shortcuts
        next_tab_shortcut = QShortcut(QKeySequence("Shift+Tab"), self)
        next_tab_shortcut.activated.connect(self.next_tab)
        
        prev_tab_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        prev_tab_shortcut.activated.connect(self.prev_tab)
        
        self.resize(total_width, total_height)
    
    def add_commit_msg(self, commit_msg_file):
        """
        Add commit message to the sidebar as the first item.
        
        Args:
            commit_msg_file: Path to the commit message file
        """
        # Check if file exists
        try:
            with open(commit_msg_file, 'r') as f:
                f.read()
        except Exception:
            return  # File doesn't exist or can't be read, don't add
        
        self._commit_msg_file = commit_msg_file
        
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
        self.button_layout.insertWidget(1, self.commit_msg_button)
    
    def on_commit_msg_clicked(self):
        """Handle commit message button click"""
        # Check if tab already exists
        if 'commit_msg' in self.file_to_tab_index:
            tab_index = self.file_to_tab_index['commit_msg']
            if 0 <= tab_index < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(tab_index)
                return
            # Tab was closed, remove from mapping
            del self.file_to_tab_index['commit_msg']
        
        # Create new commit message tab
        self.create_commit_msg_tab()
    
    def create_commit_msg_tab(self):
        """Create a tab displaying the commit message"""
        try:
            with open(self._commit_msg_file, 'r') as f:
                commit_msg_text = f.read()
        except Exception as e:
            QMessageBox.warning(self, 'Error Reading Commit Message',
                              f'Could not read commit message file:\n{e}')
            return
        
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
        text_widget.installEventFilter(self)
        
        # Store reference to tab widget for later use
        text_widget.is_commit_msg = True
        
        # Add to tabs
        index = self.tab_widget.addTab(text_widget, "Commit Message")
        self.file_to_tab_index['commit_msg'] = index
        self.tab_widget.setCurrentIndex(index)
        
        # Update button state
        self.update_button_states()
    
    def show_search_dialog(self):
        """Show search dialog for current tab"""
        viewer = self.get_current_viewer()
        current_widget = self.tab_widget.currentWidget()
        
        # Determine if we have a commit message
        has_commit_msg = False
        if viewer and viewer.commit_msg_file:
            has_commit_msg = True
        elif hasattr(current_widget, 'is_commit_msg') and current_widget.is_commit_msg:
            has_commit_msg = True
        
        dialog = SearchDialog(self, has_commit_msg=has_commit_msg)
        if dialog.exec() == dialog.DialogCode.Accepted and dialog.search_text:
            # Pass self (tab widget) as parent so search results can navigate properly
            results_dialog = SearchResultDialog(
                search_text=dialog.search_text,
                parent=self,
                case_sensitive=dialog.case_sensitive,
                search_base=dialog.search_base,
                search_modi=dialog.search_modi,
                search_commit_msg=dialog.search_commit_msg,
                search_all_tabs=dialog.search_all_tabs,
                use_regex=dialog.use_regex
            )
            # Store reference to prevent garbage collection
            self.search_result_dialogs.append(results_dialog)
            # Connect destroyed signal to clean up reference
            results_dialog.destroyed.connect(lambda: self.search_result_dialogs.remove(results_dialog) 
                                            if results_dialog in self.search_result_dialogs else None)
            results_dialog.show()  # Show as modeless, not modal
    
    def search_selected_text(self, text_widget):
        """Search for selected text from any text widget"""
        cursor = text_widget.textCursor()
        if not cursor.hasSelection():
            return
        
        search_text = cursor.selectedText()
        
        # Default to searching all tabs if multiple tabs are open
        search_all_tabs = self.tab_widget.count() > 1
        
        dialog = SearchResultDialog(search_text, self, case_sensitive=False,
                                   search_base=True, search_modi=True,
                                   search_commit_msg=True,
                                   search_all_tabs=search_all_tabs)
        # Store reference to prevent garbage collection
        self.search_result_dialogs.append(dialog)
        # Connect destroyed signal to clean up reference
        dialog.destroyed.connect(lambda: self.search_result_dialogs.remove(dialog) 
                                if dialog in self.search_result_dialogs else None)
        dialog.show()  # Show as modeless, not modal
    
    def show_commit_msg_context_menu(self, pos, text_widget):
        """Show context menu for commit message"""
        menu = QMenu(self)
        cursor = text_widget.textCursor()
        has_selection = cursor.hasSelection()
        
        search_action = QAction("Search", self)
        search_action.setEnabled(has_selection)
        if has_selection:
            search_action.triggered.connect(lambda: self.search_selected_text(text_widget))
        menu.addAction(search_action)
        
        menu.addSeparator()
        
        # Note taking - need to check if any viewer has a note file
        note_file = self.get_note_file()
        if has_selection and note_file:
            note_action = QAction("Take Note", self)
            note_action.triggered.connect(
                lambda: self.take_commit_msg_note(text_widget, note_file))
            menu.addAction(note_action)
        else:
            note_action = QAction("Take Note (no selection)" if note_file else 
                               "Take Note (no file supplied)", self)
            note_action.setEnabled(False)
            menu.addAction(note_action)
        
        menu.exec(text_widget.mapToGlobal(pos))
    
    def take_commit_msg_note(self, text_widget, note_file):
        """Take note from commit message"""
        cursor = text_widget.textCursor()
        if not cursor.hasSelection():
            return
        
        # Save selection range before doing anything
        selection_start = cursor.selectionStart()
        selection_end = cursor.selectionEnd()
        
        selected_text = cursor.selectedText()
        selected_text = selected_text.replace('\u2029', '\n')
        
        try:
            with open(note_file, 'a') as f:
                f.write("> (commit_msg): Commit Message\n")
                for line in selected_text.split('\n'):
                    f.write(f">   {line}\n")
                f.write('>\n\n\n')
            
            # Apply permanent yellow background to noted text
            from PyQt6.QtGui import QTextCharFormat, QColor
            
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
            viewer = self.get_current_viewer()
            if viewer:
                viewer.note_count += 1
                viewer.update_status()
        except Exception as e:
            QMessageBox.warning(self, 'Error Taking Note',
                              f'Could not write to note file:\n{e}')
    
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
            
            # Set global note file
            self.global_note_file = file_path
            
            # Set the note file for all existing viewers
            viewers = self.get_all_viewers()
            for viewer in viewers:
                viewer.note_file = file_path
            
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
        
        # Create button
        button = FileButton(file_class, self)
        button.clicked.connect(lambda: self.on_file_clicked(file_class))
        
        # Calculate insert position: after "Open All" and commit message (if present)
        insert_position = 1  # After "Open All"
        if self.commit_msg_button:
            insert_position = 2  # After "Open All" and "Commit Message"
        insert_position += len(self.file_buttons)  # After existing file buttons
        
        self.button_layout.insertWidget(insert_position, button)
        self.file_buttons.append(button)
    
    def open_all_files(self):
        """Open all files in tabs, including commit message if present"""
        # Calculate total items (files + commit message if present)
        total_items = len(self.file_classes)
        if self._commit_msg_file:
            total_items += 1
        
        if total_items == 0:
            return
        
        # Create progress dialog
        progress = QProgressDialog("Loading files...", "Cancel", 0, total_items, self)
        progress.setWindowTitle("Opening Files")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(500)  # Only show if takes more than 500ms
        
        current_index = 0
        
        # Open commit message first if it exists
        if self._commit_msg_file:
            if not progress.wasCanceled():
                progress.setValue(current_index)
                progress.setLabelText("Loading Commit Message...")
                QApplication.processEvents()  # Keep UI responsive
                self.on_commit_msg_clicked()
                current_index += 1
        
        # Open all file diffs
        for file_class in self.file_classes:
            if progress.wasCanceled():
                break
            
            # Update progress
            progress.setValue(current_index)
            progress.setLabelText(f"Loading {file_class.button_label()}...")
            QApplication.processEvents()  # Keep UI responsive
            
            self.on_file_clicked(file_class)
            current_index += 1
        
        progress.setValue(total_items)
        progress.close()
        
        # Focus the first tab (commit message if present, otherwise first file)
        if self.tab_widget.count() > 0:
            self.tab_widget.setCurrentIndex(0)
    
    def on_file_clicked(self, file_class):
        """Handle file button click"""
        # Check if tab already exists for this file
        if file_class in self.file_to_tab_index:
            tab_index = self.file_to_tab_index[file_class]
            # Verify tab still exists (might have been closed)
            if 0 <= tab_index < self.tab_widget.count():
                widget = self.tab_widget.widget(tab_index)
                if hasattr(widget, 'file_class') and widget.file_class == file_class:
                    # Tab exists, switch to it
                    self.tab_widget.setCurrentIndex(tab_index)
                    return
            # Tab was closed, remove from mapping
            del self.file_to_tab_index[file_class]
        
        # No existing tab, create new one
        self.current_file_class = file_class  # Store for add_viewer to use
        file_class.add_viewer(self)
        self.current_file_class = None  # Clear after use
    
    def add_viewer(self, diff_viewer, tab_title=None):
        """
        Add a fully configured DiffViewer to a new tab.
        
        Args:
            diff_viewer: A DiffViewer instance that has been configured
            tab_title: Optional title for the tab. If not provided, uses the 
                      button_label() from the file_class
        
        Returns:
            The index of the newly added tab
        """
        # Use the file_class that was stored when button was clicked
        file_class = self.current_file_class
        
        if tab_title is None and file_class:
            # Use the button label as the tab title
            tab_title = file_class.button_label()
        elif tab_title is None:
            # Fallback if no file_class
            base_name = diff_viewer.base_file.split('/')[-1]
            modified_name = diff_viewer.modified_file.split('/')[-1]
            tab_title = f"{base_name} vs {modified_name}"
        
        # Add the viewer's central widget to the tab
        viewer_widget = diff_viewer.centralWidget()
        
        index = self.tab_widget.addTab(viewer_widget, tab_title)
        
        # Store references
        viewer_widget.diff_viewer = diff_viewer
        viewer_widget.file_class = file_class
        
        # Install event filter on text widgets to handle Tab key
        diff_viewer.base_text.installEventFilter(self)
        diff_viewer.modified_text.installEventFilter(self)
        
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
        
        # Switch to new tab
        self.tab_widget.setCurrentIndex(index)
        
        # Apply global view state to new viewer
        if self.diff_map_visible != diff_viewer.diff_map_visible:
            diff_viewer.toggle_diff_map()
        if self.line_numbers_visible != diff_viewer.line_numbers_visible:
            diff_viewer.toggle_line_numbers()
        
        # Apply global note file if set
        if self.global_note_file:
            diff_viewer.note_file = self.global_note_file
        
        # Set up file watching for this viewer
        self.setup_file_watcher(diff_viewer)
        
        # Update button states immediately
        self.update_button_states()
        
        return index
    
    def show_diff_context_menu(self, pos, text_widget, side):
        """Show context menu for diff viewer text widgets"""
        menu = QMenu(self)
        viewer = self.get_current_viewer()
        
        if not viewer:
            return
        
        has_selection = text_widget.textCursor().hasSelection()
        
        search_action = QAction("Search", self)
        search_action.setEnabled(has_selection)
        search_action.triggered.connect(lambda: self.search_selected_text(text_widget))
        menu.addAction(search_action)
        
        menu.addSeparator()
        
        if has_selection and viewer.note_file:
            note_action = QAction("Take Note", self)
            note_action.triggered.connect(lambda: viewer.take_note(side))
            menu.addAction(note_action)
        else:
            note_action = QAction("Take Note (no selection)" if viewer.note_file else 
                           "Take Note (no file supplied)", self)
            note_action.setEnabled(False)
            menu.addAction(note_action)
        
        menu.exec(text_widget.mapToGlobal(pos))
    
    def highlight_all_matches_in_widget(self, text_widget, search_text, highlight_color):
        """
        Find and highlight ALL occurrences of search_text in the text widget.
        Uses case-insensitive search.
        
        Args:
            text_widget: The QPlainTextEdit to search in
            search_text: The text to search for (case-insensitive)
            highlight_color: QColor to use for highlighting all matches
        """
        from PyQt6.QtGui import QTextCharFormat, QTextCursor
        
        # Get all text
        all_text = text_widget.toPlainText()
        search_lower = search_text.lower()
        all_text_lower = all_text.lower()
        
        # Find all positions manually
        pos = 0
        while True:
            pos = all_text_lower.find(search_lower, pos)
            if pos < 0:
                break
            
            # Create cursor at this position and select the match
            cursor = text_widget.textCursor()
            cursor.setPosition(pos)
            cursor.setPosition(pos + len(search_text), QTextCursor.MoveMode.KeepAnchor)
            
            # Apply highlight format
            fmt = QTextCharFormat()
            fmt.setBackground(highlight_color)
            cursor.mergeCharFormat(fmt)
            
            # Move to next potential match
            pos += len(search_text)
    
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
        viewer = self.get_current_viewer()
        if not viewer:
            return
        
        viewer.center_on_line(line_idx)
        
        # Select the appropriate text widget
        text_widget = viewer.base_text if side == 'base' else viewer.modified_text
        text_widget.setFocus()
        
        # If search_text is provided, implement two-tier highlighting
        if search_text:
            from PyQt6.QtGui import QTextCharFormat, QTextCursor
            import color_palettes
            
            palette = color_palettes.get_current_palette()
            all_color = palette.get_color('search_highlight_all')
            current_color = palette.get_color('search_highlight_current')
            
            # Check if we need to do initial highlighting (search_text changed)
            if not hasattr(viewer, '_last_search_text') or viewer._last_search_text != search_text:
                # First time or new search - clear old highlights and highlight all matches
                self.clear_search_highlights(viewer.base_text)
                self.clear_search_highlights(viewer.modified_text)
                
                # TIER 1: Highlight ALL matches in BOTH panes with subtle color (ONCE)
                self.highlight_all_matches_in_widget(viewer.base_text, search_text, all_color)
                self.highlight_all_matches_in_widget(viewer.modified_text, search_text, all_color)
                
                viewer._last_search_text = search_text
                viewer._last_bright_pos = None  # Track last bright position
            else:
                # Same search - just need to change bright highlight
                # Change previous bright match back to subtle (if exists)
                if hasattr(viewer, '_last_bright_pos') and viewer._last_bright_pos:
                    last_widget, last_line_idx, last_char_pos, last_len = viewer._last_bright_pos
                    block = last_widget.document().findBlockByNumber(last_line_idx)
                    if block.isValid():
                        cursor = last_widget.textCursor()
                        cursor.setPosition(block.position() + last_char_pos)
                        cursor.setPosition(block.position() + last_char_pos + last_len,
                                         QTextCursor.MoveMode.KeepAnchor)
                        fmt = QTextCharFormat()
                        fmt.setBackground(all_color)  # Back to subtle
                        cursor.mergeCharFormat(fmt)
            
            # TIER 2: Find and highlight the CURRENT match with bright color
            block = text_widget.document().findBlockByNumber(line_idx)
            if block.isValid():
                line_text = block.text()
                
                # Use provided char_pos if available, otherwise find first match
                if char_pos is not None:
                    pos = char_pos
                else:
                    search_lower = search_text.lower()
                    line_lower = line_text.lower()
                    pos = line_lower.find(search_lower)
                
                if pos >= 0 and pos < len(line_text):
                    # Apply bright highlight to current match
                    cursor = text_widget.textCursor()
                    cursor.setPosition(block.position() + pos)
                    cursor.setPosition(block.position() + pos + len(search_text), 
                                     QTextCursor.MoveMode.KeepAnchor)
                    
                    fmt = QTextCharFormat()
                    fmt.setBackground(current_color)
                    cursor.mergeCharFormat(fmt)
                    
                    # Remember this position for next time
                    viewer._last_bright_pos = (text_widget, line_idx, pos, len(search_text))
                    
                    # Position cursor at current match (without selection to avoid blue overlay)
                    cursor.setPosition(block.position() + pos)
                    text_widget.setTextCursor(cursor)
                    text_widget.ensureCursorVisible()
    
    def clear_search_highlights(self, text_widget):
        """Clear all search highlights from a text widget by removing search highlight colors"""
        from PyQt6.QtGui import QTextCharFormat, QTextCursor
        import color_palettes
        
        palette = color_palettes.get_current_palette()
        search_all_color = palette.get_color('search_highlight_all')
        search_current_color = palette.get_color('search_highlight_current')
        
        # Iterate through the document and remove search highlight backgrounds
        cursor = QTextCursor(text_widget.document())
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        
        # Save current position
        saved_cursor = text_widget.textCursor()
        current_pos = saved_cursor.position()
        
        # Go through each character and check/clear search highlighting
        while not cursor.atEnd():
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
            fmt = cursor.charFormat()
            bg = fmt.background().color()
            
            # If this character has a search highlight color, clear it
            if bg == search_all_color or bg == search_current_color:
                # Create format that only sets background to transparent
                clear_fmt = QTextCharFormat()
                clear_fmt.setBackground(QColor(0, 0, 0, 0))  # Transparent
                cursor.mergeCharFormat(clear_fmt)
            
            # Move to next position
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
        
        # Restore original cursor position
        saved_cursor.setPosition(current_pos)
        text_widget.setTextCursor(saved_cursor)
    
    def select_commit_msg_result(self, line_idx, search_text=None, char_pos=None):
        """Navigate to a line in the commit message tab and highlight search text
        
        Args:
            line_idx: Line index in the commit message
            search_text: Text to search for
            char_pos: Character position of the specific match to highlight bright (optional)
        """
        # Find the commit message tab
        commit_msg_widget = None
        commit_msg_tab_index = None
        
        if 'commit_msg' in self.file_to_tab_index:
            commit_msg_tab_index = self.file_to_tab_index['commit_msg']
            if 0 <= commit_msg_tab_index < self.tab_widget.count():
                widget = self.tab_widget.widget(commit_msg_tab_index)
                if hasattr(widget, 'is_commit_msg') and widget.is_commit_msg:
                    commit_msg_widget = widget
        
        if not commit_msg_widget:
            # No commit message tab found
            return
        
        # Switch to the commit message tab
        self.tab_widget.setCurrentIndex(commit_msg_tab_index)
        
        # Navigate to the line
        cursor = commit_msg_widget.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        for _ in range(line_idx):
            cursor.movePosition(cursor.MoveOperation.Down)
        
        # If search_text provided, do two-tier highlighting
        if search_text:
            from PyQt6.QtGui import QTextCharFormat, QTextCursor
            import color_palettes
            
            palette = color_palettes.get_current_palette()
            all_color = palette.get_color('search_highlight_all')
            current_color = palette.get_color('search_highlight_current')
            
            # Check if we need to do initial highlighting (search_text changed)
            if not hasattr(commit_msg_widget, '_last_search_text') or commit_msg_widget._last_search_text != search_text:
                # First time or new search - clear old and highlight all matches
                self.clear_commit_msg_tab_highlights(commit_msg_widget)
                
                # TIER 1: Highlight ALL matches (ONCE)
                self.highlight_all_matches_in_commit_msg_tab(commit_msg_widget, search_text, all_color)
                
                commit_msg_widget._last_search_text = search_text
                commit_msg_widget._last_bright_pos = None
            else:
                # Same search - just change bright highlight
                # Change previous bright match back to subtle
                if hasattr(commit_msg_widget, '_last_bright_pos') and commit_msg_widget._last_bright_pos:
                    last_line_idx, last_char_pos, last_len = commit_msg_widget._last_bright_pos
                    block = commit_msg_widget.document().findBlockByNumber(last_line_idx)
                    if block.isValid():
                        cursor = commit_msg_widget.textCursor()
                        cursor.setPosition(block.position() + last_char_pos)
                        cursor.setPosition(block.position() + last_char_pos + last_len,
                                         QTextCursor.MoveMode.KeepAnchor)
                        fmt = QTextCharFormat()
                        fmt.setBackground(all_color)  # Back to subtle
                        cursor.mergeCharFormat(fmt)
            
            # TIER 2: Highlight current match
            cursor.movePosition(cursor.MoveOperation.StartOfBlock)
            block = cursor.block()
            line_text = block.text()
            
            # Use provided char_pos if available, otherwise find first match
            if char_pos is not None:
                pos = char_pos
            else:
                search_lower = search_text.lower()
                line_lower = line_text.lower()
                pos = line_lower.find(search_lower)
            
            if pos >= 0 and pos < len(line_text):
                cursor.setPosition(block.position() + pos)
                cursor.setPosition(block.position() + pos + len(search_text),
                                 cursor.MoveMode.KeepAnchor)
                
                fmt = QTextCharFormat()
                fmt.setBackground(current_color)
                cursor.mergeCharFormat(fmt)
                
                # Remember this position
                commit_msg_widget._last_bright_pos = (line_idx, pos, len(search_text))
                
                cursor.setPosition(block.position() + pos)
                commit_msg_widget.setTextCursor(cursor)
            else:
                # Select whole line if not found
                cursor.movePosition(cursor.MoveOperation.StartOfBlock)
                cursor.movePosition(cursor.MoveOperation.EndOfBlock,
                                  cursor.MoveMode.KeepAnchor)
                commit_msg_widget.setTextCursor(cursor)
        else:
            # No search text, just select the line
            cursor.movePosition(cursor.MoveOperation.StartOfBlock)
            cursor.movePosition(cursor.MoveOperation.EndOfBlock,
                              cursor.MoveMode.KeepAnchor)
            commit_msg_widget.setTextCursor(cursor)
        
        commit_msg_widget.centerCursor()
        commit_msg_widget.setFocus()
    
    def highlight_all_matches_in_commit_msg_tab(self, text_widget, search_text, highlight_color):
        """Highlight all matches in commit message tab"""
        from PyQt6.QtGui import QTextCharFormat, QTextCursor
        
        # Get all text
        all_text = text_widget.toPlainText()
        search_lower = search_text.lower()
        all_text_lower = all_text.lower()
        
        # Find all positions manually
        pos = 0
        while True:
            pos = all_text_lower.find(search_lower, pos)
            if pos < 0:
                break
            
            # Create cursor at this position and select the match
            cursor = text_widget.textCursor()
            cursor.setPosition(pos)
            cursor.setPosition(pos + len(search_text), QTextCursor.MoveMode.KeepAnchor)
            
            # Apply highlight format
            fmt = QTextCharFormat()
            fmt.setBackground(highlight_color)
            cursor.mergeCharFormat(fmt)
            
            # Move to next potential match
            pos += len(search_text)
    
    def clear_commit_msg_tab_highlights(self, text_widget):
        """Clear search highlights from commit message tab"""
        from PyQt6.QtGui import QTextCharFormat, QTextCursor
        import color_palettes
        
        palette = color_palettes.get_current_palette()
        search_all_color = palette.get_color('search_highlight_all')
        search_current_color = palette.get_color('search_highlight_current')
        
        cursor = QTextCursor(text_widget.document())
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        
        saved_cursor = text_widget.textCursor()
        current_pos = saved_cursor.position()
        
        while not cursor.atEnd():
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
            fmt = cursor.charFormat()
            bg = fmt.background().color()
            
            if bg == search_all_color or bg == search_current_color:
                clear_fmt = QTextCharFormat()
                clear_fmt.setBackground(QColor(0, 0, 0, 0))
                cursor.mergeCharFormat(clear_fmt)
            
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
        
        saved_cursor.setPosition(current_pos)
        text_widget.setTextCursor(saved_cursor)
    
    def show_commit_msg_dialog(self, commit_msg_file, viewer):
        """Show the commit message dialog for a viewer"""
        # Check if dialog already exists and is visible
        if self.commit_msg_dialog and self.commit_msg_dialog.isVisible():
            self.commit_msg_dialog.raise_()
            self.commit_msg_dialog.activateWindow()
            return
        
        # Create new dialog
        self.commit_msg_dialog = CommitMsgDialog(commit_msg_file, viewer, self)
        self.commit_msg_dialog.show()
    
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
    
    @property
    def commit_msg_file(self):
        """Get commit_msg_file from current viewer"""
        viewer = self.get_current_viewer()
        return viewer.commit_msg_file if viewer else None
    
    def get_commit_msg_lines(self):
        """Get commit message lines from current viewer"""
        viewer = self.get_current_viewer()
        return viewer.get_commit_msg_lines() if viewer else []
    
    def on_tab_changed(self, index):
        """Handle tab change to update sidebar button states"""
        self.update_button_states()
        
        # Update scrollbars in the newly activated viewer
        viewer = self.get_viewer_at_index(index)
        if viewer:
            viewer.init_scrollbars()
    
    def update_button_states(self):
        """Update all button states based on open tabs and currently selected tab"""
        current_tab_index = self.tab_widget.currentIndex()
        
        # Update file buttons
        for button in self.file_buttons:
            file_class = button.file_class
            
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
            
            button.set_state(is_open, is_active)
        
        # Update commit message button if it exists
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
            
            # Update commit message button style based on state
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
    
    def get_all_viewers(self):
        """
        Get all DiffViewer instances across all tabs.
        
        Returns:
            List of DiffViewer instances
        """
        viewers = []
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if hasattr(widget, 'diff_viewer'):
                viewers.append(widget.diff_viewer)
        return viewers
    
    def get_current_viewer(self):
        """
        Get the currently active DiffViewer instance.
        
        Returns:
            The DiffViewer instance in the current tab, or None if no tabs
        """
        current_widget = self.tab_widget.currentWidget()
        if current_widget and hasattr(current_widget, 'diff_viewer'):
            return current_widget.diff_viewer
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
            if hasattr(widget, 'diff_viewer'):
                return widget.diff_viewer
        return None
    
    def close_tab(self, index):
        """Close the tab at the given index"""
        if index >= 0 and index < self.tab_widget.count():
            widget = self.tab_widget.widget(index)
            
            # Clean up file watcher if this is a DiffViewer
            if hasattr(widget, 'base_file'):
                self.cleanup_file_watcher(widget)
            
            # Check if this is the commit message tab
            if hasattr(widget, 'is_commit_msg') and widget.is_commit_msg:
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
            
            self.tab_widget.removeTab(index)
            
            # Update button states after closing
            self.update_button_states()
            
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
    
    def prev_tab(self):
        """Navigate to previous tab (right-to-left, wraps around)"""
        if self.tab_widget.count() > 0:
            current = self.tab_widget.currentIndex()
            prev_index = (current - 1) % self.tab_widget.count()
            self.tab_widget.setCurrentIndex(prev_index)
    
    def toggle_sidebar(self):
        """Toggle sidebar visibility"""
        if self.sidebar_visible:
            self.sidebar_widget.hide()
            self.sidebar_visible = False
        else:
            self.sidebar_widget.show()
            self.sidebar_visible = True
        
        # Update scrollbars in current viewer after sidebar toggle
        current_viewer = self.get_current_viewer()
        if current_viewer:
            # Trigger scrollbar recalculation
            current_viewer.init_scrollbars()
    
    def toggle_diff_map(self):
        """Toggle diff map in all viewers"""
        self.diff_map_visible = not self.diff_map_visible
        viewers = self.get_all_viewers()
        for viewer in viewers:
            if viewer.diff_map_visible != self.diff_map_visible:
                viewer.toggle_diff_map()
    
    def toggle_line_numbers(self):
        """Toggle line numbers in all viewers"""
        self.line_numbers_visible = not self.line_numbers_visible
        viewers = self.get_all_viewers()
        for viewer in viewers:
            if viewer.line_numbers_visible != self.line_numbers_visible:
                viewer.toggle_line_numbers()
    
    def toggle_auto_reload(self):
        """Toggle auto-reload preference"""
        self.auto_reload_enabled = self.auto_reload_action.isChecked()
        
        # If turning on, immediately reload any files that have changed
        if self.auto_reload_enabled:
            for viewer in list(self.changed_files.keys()):
                if viewer in self.changed_files and self.changed_files[viewer]:
                    self.reload_viewer(viewer)
    
    def setup_file_watcher(self, viewer):
        """Set up file system watching for a viewer's files"""
        watcher = QFileSystemWatcher()
        
        # Watch base and modified files
        files_to_watch = []
        if viewer.base_file:
            files_to_watch.append(viewer.base_file)
        if viewer.modified_file:
            files_to_watch.append(viewer.modified_file)
        
        if files_to_watch:
            watcher.addPaths(files_to_watch)
            watcher.fileChanged.connect(lambda path: self.on_file_changed(viewer, path))
            self.file_watchers[viewer] = watcher
            self.changed_files[viewer] = set()
            
            # Create debounce timer
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self.process_file_changes(viewer))
            self.reload_timers[viewer] = timer
    
    def on_file_changed(self, viewer, path):
        """Handle file change notification"""
        # Add to changed files set
        if viewer not in self.changed_files:
            self.changed_files[viewer] = set()
        self.changed_files[viewer].add(path)
        
        # Mark tab as changed (visual indicator)
        self.mark_tab_changed(viewer, True)
        
        # Restart debounce timer
        if viewer in self.reload_timers:
            self.reload_timers[viewer].stop()
            self.reload_timers[viewer].start(500)  # 500ms debounce
    
    def process_file_changes(self, viewer):
        """Process accumulated file changes after debounce period"""
        if self.auto_reload_enabled and viewer in self.changed_files:
            self.reload_viewer(viewer)
    
    def mark_tab_changed(self, viewer, changed):
        """Mark a viewer as having changed files by updating sidebar button color"""
        # Find the file_class for this viewer
        # The viewer is a DiffViewer, we need to find its tab widget
        file_class = None
        for i in range(self.tab_widget.count()):
            widget = self.tab_widget.widget(i)
            if hasattr(widget, 'diff_viewer') and widget.diff_viewer == viewer:
                if hasattr(widget, 'file_class'):
                    file_class = widget.file_class
                break
        
        if not file_class:
            return
        
        # Find the corresponding button in the sidebar
        for button in self.file_buttons:
            if button.file_class == file_class:
                if changed:
                    # File has changed - use special "changed" styling
                    import color_palettes
                    palette = color_palettes.get_current_palette()
                    color = palette.get_color('base_changed_bg')
                    
                    # Check if this is the currently active tab
                    tab_index = self.file_to_tab_index.get(file_class, -1)
                    is_active = (tab_index == self.tab_widget.currentIndex())
                    
                    if is_active:
                        # Changed AND active - bright changed color with thick border
                        button.setStyleSheet(f"""
                            QPushButton {{
                                text-align: left;
                                padding: 8px 8px 8px 20px;
                                border: none;
                                background-color: {color.name()};
                                border-left: 6px solid #ff6600;
                                font-weight: bold;
                            }}
                            QPushButton:hover {{
                                background-color: {color.darker(110).name()};
                            }}
                        """)
                    else:
                        # Changed but not active - changed color with normal border
                        button.setStyleSheet(f"""
                            QPushButton {{
                                text-align: left;
                                padding: 8px 8px 8px 20px;
                                border: none;
                                background-color: {color.name()};
                                border-left: 4px solid #ff6600;
                            }}
                            QPushButton:hover {{
                                background-color: {color.darker(110).name()};
                            }}
                        """)
                else:
                    # File no longer changed - restore normal state
                    # Determine if tab is open and active
                    tab_index = self.file_to_tab_index.get(file_class, -1)
                    is_open = (0 <= tab_index < self.tab_widget.count())
                    is_active = is_open and (tab_index == self.tab_widget.currentIndex())
                    button.set_state(is_open, is_active)
                break
    
    def reload_viewer(self, viewer):
        """Reload a viewer's diff data"""
        import diffmgr
        
        # Save current scroll position
        v_scroll_pos = viewer.base_text.verticalScrollBar().value()
        h_scroll_pos = viewer.base_text.horizontalScrollBar().value()
        
        # Clear line number area backgrounds (O(1) operation)
        viewer.base_line_area.line_backgrounds.clear()
        viewer.modified_line_area.line_backgrounds.clear()
        
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
            desc = diffmgr.create_diff_descriptor(False, viewer.base_file, viewer.modified_file)
            
            for idx in range(len(desc.base_)):
                base = desc.base_[idx]
                modi = desc.modi_[idx]
                viewer.add_line(base, modi)
            
            viewer.finalize()
            
            # Restore scroll position
            viewer.base_text.verticalScrollBar().setValue(v_scroll_pos)
            viewer.base_text.horizontalScrollBar().setValue(h_scroll_pos)
            viewer.modified_text.verticalScrollBar().setValue(v_scroll_pos)
            viewer.modified_text.horizontalScrollBar().setValue(h_scroll_pos)
            
            # Clear changed files for this viewer
            if viewer in self.changed_files:
                self.changed_files[viewer].clear()
            
            # Remove changed indicator from tab
            self.mark_tab_changed(viewer, False)
            
            # Re-add files to watcher (they may have been removed by some editors)
            if viewer in self.file_watchers:
                watcher = self.file_watchers[viewer]
                watched = watcher.files()
                
                files_to_watch = []
                if viewer.base_file and viewer.base_file not in watched:
                    files_to_watch.append(viewer.base_file)
                if viewer.modified_file and viewer.modified_file not in watched:
                    files_to_watch.append(viewer.modified_file)
                
                if files_to_watch:
                    watcher.addPaths(files_to_watch)
            
            # Show brief notification
            self.statusBar().showMessage("File reloaded", 2000)  # 2 second message
            
        except Exception as e:
            QMessageBox.warning(self, 'Reload Error', f'Could not reload files:\n{str(e)}')
    
    def cleanup_file_watcher(self, viewer):
        """Clean up file watcher for a viewer being closed"""
        if viewer in self.file_watchers:
            self.file_watchers[viewer].deleteLater()
            del self.file_watchers[viewer]
        if viewer in self.reload_timers:
            self.reload_timers[viewer].stop()
            del self.reload_timers[viewer]
        if viewer in self.changed_files:
            del self.changed_files[viewer]
    
    def show_help(self):
        """Show help dialog"""
        help_dialog = HelpDialog(self)
        help_dialog.exec()
    
    def switch_palette(self, palette_name):
        """Switch to a different color palette and refresh all viewers"""
        if color_palettes.set_current_palette(palette_name):
            # Refresh all open diff viewers
            viewers = self.get_all_viewers()
            for viewer in viewers:
                viewer.refresh_colors()
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        key = event.key()
        modifiers = event.modifiers()
        
        # Get current viewer for most commands
        viewer = self.get_current_viewer()
        
        # Escape closes the entire application
        if key == Qt.Key.Key_Escape:
            self.close()
            return
        
        # All other shortcuts require an active viewer
        if not viewer:
            super().keyPressEvent(event)
            return
        
        # Alt+H - Toggle diff map (Alt on Win/Linux, Cmd on Mac for VNC compatibility)
        if key == Qt.Key.Key_H and (modifiers & Qt.KeyboardModifier.AltModifier or
                                      modifiers & Qt.KeyboardModifier.MetaModifier):
            self.toggle_diff_map()
            return
        
        # Alt+L - Toggle line numbers (Alt on Win/Linux, Cmd on Mac for VNC compatibility)
        if key == Qt.Key.Key_L and (modifiers & Qt.KeyboardModifier.AltModifier or
                                      modifiers & Qt.KeyboardModifier.MetaModifier):
            self.toggle_line_numbers()
            return
        
        # Ctrl+S - Search
        if key == Qt.Key.Key_S and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.show_search_dialog()
            return
        
        # F5 - Manual reload
        if key == Qt.Key.Key_F5:
            if viewer and hasattr(viewer, 'base_file'):
                self.reload_viewer(viewer)
            return
        
        # Ctrl+N - Take note (Ctrl on Win/Linux, Cmd on Mac)
        if key == Qt.Key.Key_N and (modifiers & Qt.KeyboardModifier.ControlModifier or 
                                      modifiers & Qt.KeyboardModifier.MetaModifier):
            # Determine which side has focus
            if viewer.base_text.hasFocus():
                viewer.take_note_from_widget('base')
            elif viewer.modified_text.hasFocus():
                viewer.take_note_from_widget('modified')
            return
        
        # N - Next change
        if key == Qt.Key.Key_N:
            viewer.next_change()
            return
        
        # P - Previous change
        if key == Qt.Key.Key_P:
            viewer.prev_change()
            return
        
        # C - Center on current region
        if key == Qt.Key.Key_C:
            viewer.center_current_region()
            return
        
        # T - Top of file
        if key == Qt.Key.Key_T:
            viewer.current_region = 0
            if viewer.change_regions:
                viewer.center_on_line(0)
            viewer.update_status()
            return
        
        # B - Bottom of file
        if key == Qt.Key.Key_B:
            if viewer.change_regions:
                viewer.current_region = len(viewer.change_regions) - 1
                viewer.center_on_line(len(viewer.base_display) - 1)
            viewer.update_status()
            return
        
        # Pass other events to parent
        super().keyPressEvent(event)
    
    def eventFilter(self, obj, event):
        """Filter events from text widgets to handle Tab key and Ctrl+N"""
        if event.type() == event.Type.KeyPress:
            viewer = self.get_current_viewer()
            key = event.key()
            modifiers = event.modifiers()
            
            # Check if this is the commit message widget
            is_commit_msg = hasattr(obj, 'is_commit_msg') and obj.is_commit_msg
            
            # Ctrl+S - Search (works for both commit message and diff viewers)
            if key == Qt.Key.Key_S and (modifiers & Qt.KeyboardModifier.ControlModifier or
                                          modifiers & Qt.KeyboardModifier.MetaModifier):
                self.show_search_dialog()
                return True
            
            # Ctrl+N - Take note (works for both)
            if key == Qt.Key.Key_N and (modifiers & Qt.KeyboardModifier.ControlModifier or
                                          modifiers & Qt.KeyboardModifier.MetaModifier):
                if is_commit_msg:
                    note_file = self.get_note_file()
                    if note_file:
                        self.take_commit_msg_note(obj, note_file)
                    return True
                elif viewer:
                    if obj == viewer.base_text:
                        viewer.take_note_from_widget('base')
                        return True
                    elif obj == viewer.modified_text:
                        viewer.take_note_from_widget('modified')
                        return True
            
            # Tab - Switch focus between base and modified (only for diff viewers)
            if not is_commit_msg and viewer and key == Qt.Key.Key_Tab and not modifiers:
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
                    return True
                    
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
                    return True
        return False
    
    def run(self):
        """Show the window and start the application event loop"""
        self.show()
        return sys.exit(self._app.exec())
