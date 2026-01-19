# Copyright (c) 2025, 2026  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
DiffViewer main class for diff_review

This module contains the main DiffViewer window class that orchestrates
the entire diff viewing application.
"""
import sys
from typing import Optional
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel, QScrollBar, QFrame, QMenu,
                              QMessageBox, QDialog, QPushButton)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (QColor, QFont, QTextCursor, QAction, QFontMetrics,
                         QTextCharFormat, QTextBlockFormat, QPainter, QPen)

from search_dialogs import SearchDialog, SearchResultDialog
from ui_components import LineNumberArea, DiffMapWidget, SyncedPlainTextEdit
import color_palettes
import generate_viewer
from tab_content_base import TabContentBase


class DiffViewer(QWidget, TabContentBase):
    def __init__(self,
                 base_file: str,
                 modified_file: str,
                 base_display_path: str,
                 modi_display_path : str,
                 max_line_length: int,
                 show_diff_map: bool,
                 show_line_numbers: bool):
        if QApplication.instance() is None:
            self._app = QApplication(sys.argv)
        else:
            self._app = QApplication.instance()

        super().__init__()

        self.base_file = base_file
        self.modified_file = modified_file
        self.base_display_path = base_display_path
        self.modi_display_path = modi_display_path
        self.max_line_length = max_line_length
        self.show_diff_map = show_diff_map
        self.show_line_numbers = show_line_numbers
        self.note_count = 0
        
        self.base_noted_lines = set()
        self.modified_noted_lines = set()
        self.bookmarked_lines = set()  # Line indices that are bookmarked
        
        self.base_display = []
        self.modified_display = []
        self.base_line_nums = []
        self.modified_line_nums = []
        self.change_regions = []
        self.base_line_objects = []
        self.modified_line_objects = []
        self.n_changed_regions = 0  # Count of non-EQUAL regions from diff descriptor
        
        self.current_region = 0
        self.current_region_highlight = None
        self._target_region = None
        self.ignore_ws = False  # Will be set by tab manager
        self.ignore_tab = False  # Will be set by tab manager
        self.ignore_trailing_ws = False  # Will be set by tab manager
        self.ignore_intraline = False  # Will be set by tab manager
        self.highlighting_applied = False  # Deferred until tab becomes visible
        self.highlighting_in_progress = False  # True during background highlighting
        self.highlighting_next_line = 0  # Next line to highlight
        self._needs_highlighting_update = False  # Set by tab_manager for deferred updates
        self._needs_color_refresh = False  # Set by tab_manager for deferred color updates
        self._needs_staged_mode_reload = False  # Set when staged diff mode changes
        self.staged_diff_mode = None  # Diff mode for unstaged files (set by tab_manager)

        self.current_font_size = 12  # Default font size
        
        self.collapsed_regions = []  # List of (start_line, end_line, region_type) tuples for collapsed change regions
        self.all_collapsed = False  # Track if all change regions are collapsed
        
        self._syncing_scroll = False  # Prevent recursion in scroll syncing
        
        self.setup_gui()
    
    def setup_gui(self):
        # Note: No window title needed when used in tabs

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        label_layout = QHBoxLayout()

        base_container = QHBoxLayout()
        self.base_type_label = QLabel("Base")
        self.base_type_label.setStyleSheet("font-weight: bold; color: blue; padding: 2px 5px;")
        base_file_label = QLabel(self.base_display_path)
        base_file_label.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
        base_container.addWidget(self.base_type_label)
        base_container.addWidget(base_file_label, 1)

        spacer = QLabel("")

        modified_container = QHBoxLayout()
        self.modified_type_label = QLabel("Modified")
        self.modified_type_label.setStyleSheet("font-weight: bold; color: green; padding: 2px 5px;")
        modified_file_label = QLabel(self.modi_display_path)
        modified_file_label.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
        modified_container.addWidget(self.modified_type_label)
        modified_container.addWidget(modified_file_label, 1)

        label_layout.addLayout(base_container, 1)
        label_layout.addWidget(spacer, 0)
        label_layout.addLayout(modified_container, 1)
        main_layout.addLayout(label_layout)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)
        
        base_layout = QHBoxLayout()
        base_layout.setSpacing(0)
        self.base_line_area = LineNumberArea()
        self.base_line_area.setup_font()
        self.base_text = SyncedPlainTextEdit()
        self.base_line_area.set_text_widget(self.base_text)
        self.base_text.set_line_number_area(self.base_line_area)
        self.base_text.set_max_line_length(self.max_line_length)
        self.base_text.viewer = self  # Reference for bookmark lookup
        base_layout.addWidget(self.base_line_area)
        base_layout.addWidget(self.base_text)
        base_container = QWidget()
        base_container.setLayout(base_layout)
        content_layout.addWidget(base_container, 1)
        
        self.diff_map = DiffMapWidget()
        self.diff_map.clicked.connect(self.on_diff_map_click)
        self.diff_map_visible = self.show_diff_map
        content_layout.addWidget(self.diff_map)
        if not self.show_diff_map:
            self.diff_map.hide()
        
        modified_layout = QHBoxLayout()
        modified_layout.setSpacing(0)
        self.modified_line_area = LineNumberArea()
        self.modified_line_area.setup_font()
        self.modified_text = SyncedPlainTextEdit()
        self.modified_line_area.set_text_widget(self.modified_text)
        self.modified_text.set_line_number_area(self.modified_line_area)
        self.modified_text.set_max_line_length(self.max_line_length)
        self.modified_text.viewer = self  # Reference for bookmark lookup
        modified_layout.addWidget(self.modified_line_area)
        modified_layout.addWidget(self.modified_text)
        modified_container = QWidget()
        modified_container.setLayout(modified_layout)
        content_layout.addWidget(modified_container, 1)
        
        self.line_numbers_visible = self.show_line_numbers
        if not self.show_line_numbers:
            self.base_line_area.hide()
            self.modified_line_area.hide()
        
        self.v_scrollbar = QScrollBar(Qt.Orientation.Vertical)
        self.v_scrollbar.valueChanged.connect(self.on_v_scroll)
        content_layout.addWidget(self.v_scrollbar)
        
        main_layout.addLayout(content_layout, 1)
        
        self.h_scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        self.h_scrollbar.valueChanged.connect(self.on_h_scroll)
        main_layout.addWidget(self.h_scrollbar)
        
        status_layout = QHBoxLayout()
        self.region_label = QLabel("Region: 0 of 0")
        self.highlighting_label = QLabel("")
        self.highlighting_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.highlighting_label.setMinimumWidth(392)
        self.highlighting_label.setTextFormat(Qt.TextFormat.PlainText)
        self.bookmarks_label = QLabel("Bookmarks: 0")
        self.notes_label = QLabel("Notes: 0")
        
        status_layout.addWidget(self.region_label)
        status_layout.addStretch()
        status_layout.addWidget(self.highlighting_label)
        status_layout.addStretch()
        status_layout.addWidget(self.bookmarks_label)
        status_layout.addWidget(self.notes_label)
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
        status_frame.setLayout(status_layout)
        main_layout.addWidget(status_frame)
        
        # Bidirectional scroll syncing
        self.base_text.verticalScrollBar().valueChanged.connect(self.sync_v_scroll_from_base)
        self.base_text.horizontalScrollBar().valueChanged.connect(self.sync_h_scroll_from_base)
        self.modified_text.verticalScrollBar().valueChanged.connect(self.sync_v_scroll_from_modified)
        self.modified_text.horizontalScrollBar().valueChanged.connect(self.sync_h_scroll_from_modified)
        
        self.base_text.verticalScrollBar().valueChanged.connect(self.base_line_area.update)
        self.modified_text.verticalScrollBar().valueChanged.connect(self.modified_line_area.update)
        
        self.base_text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.modified_text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        # Context menus will be handled by the tab widget
        
        self.base_text.mouseDoubleClickEvent = lambda e: self.on_double_click(e, 'base')
        self.modified_text.mouseDoubleClickEvent = lambda e: self.on_double_click(e, 'modified')
        
        self.diff_map.wheelEvent = self.on_diff_map_wheel
        
        # Create font and set it on text widgets
        text_font = QFont("Courier", 12, QFont.Weight.Bold)
        self.base_text.setFont(text_font)
        self.modified_text.setFont(text_font)
        
        # Install event filters to handle all events centrally
        self.base_text.installEventFilter(self)
        self.modified_text.installEventFilter(self)
    
    def set_changed_region_count(self, count):
        """Set the number of changed regions from the diff descriptor"""
        self.n_changed_regions = count

    def set_staged_diff_mode(self, mode):
        """Set the staged diff mode and update panel labels accordingly.

        For unstaged files, this shows which versions are being compared:
        - DIFF_MODE_BASE_MODI: Base (HEAD) vs Modified (Working)
        - DIFF_MODE_BASE_STAGE: Base (HEAD) vs Modified (Staged)
        - DIFF_MODE_STAGE_MODI: Base (Staged) vs Modified (Working)
        """
        self.staged_diff_mode = mode

        if mode == generate_viewer.DIFF_MODE_BASE_MODI:
            self.base_type_label.setText("Base (HEAD)")
            self.modified_type_label.setText("Modified (Working)")
        elif mode == generate_viewer.DIFF_MODE_BASE_STAGE:
            self.base_type_label.setText("Base (HEAD)")
            self.modified_type_label.setText("Modified (Staged)")
        elif mode == generate_viewer.DIFF_MODE_STAGE_MODI:
            self.base_type_label.setText("Base (Staged)")
            self.modified_type_label.setText("Modified (Working)")

    def add_line(self, base, modi):
        base_text = base.line_.rstrip('\n') if hasattr(base, 'line_') else ''
        modi_text = modi.line_.rstrip('\n') if hasattr(modi, 'line_') else ''
        
        base_num = base.line_num_ if base.show_line_number() else None
        modi_num = modi.line_num_ if modi.show_line_number() else None
        
        self.base_display.append(base_text)
        self.modified_display.append(modi_text)
        self.base_line_nums.append(base_num)
        self.modified_line_nums.append(modi_num)
        self.base_line_objects.append(base)
        self.modified_line_objects.append(modi)
    
    def finalize(self):
        self.build_change_regions()
        self.populate_content()
        # NOTE: apply_highlighting() is deferred until tab becomes visible
        # This is handled by ensure_highlighting_applied() called from on_tab_changed()
        self.update_status()
        QTimer.singleShot(100, self.init_scrollbars)
        
        QTimer.singleShot(150, self.base_line_area.update)
        QTimer.singleShot(150, self.modified_line_area.update)
        QTimer.singleShot(150, self.base_text.viewport().update)
        QTimer.singleShot(150, self.modified_text.viewport().update)
        
        if self.change_regions:
            QTimer.singleShot(200, self.navigate_to_first_region)
    
    def navigate_to_first_region(self):
        if self.change_regions:
            self.current_region = 0
            _, start, *_ = self.change_regions[0]
            self.center_on_line(start)
            self.highlight_current_region()
    
    def build_change_regions(self):
        """Build change regions from line.region_ references (only non-EQUAL regions)"""
        self.change_regions = []
        
        import diff_desc
        
        region_start = None
        region_kind = None
        
        for i, base_line in enumerate(self.base_line_objects):
            # Get the region from the line object
            if base_line.region_:
                current_kind = base_line.region_.kind_
                
                # Only track non-EQUAL regions
                if current_kind != diff_desc.RegionDesc.EQUAL:
                    if region_start is None or region_kind != current_kind:
                        # Start new region
                        if region_start is not None:
                            # Close previous region
                            tag_name = {
                                diff_desc.RegionDesc.DELETE: 'delete',
                                diff_desc.RegionDesc.ADD: 'insert',
                                diff_desc.RegionDesc.CHANGE: 'replace'
                            }.get(region_kind, 'unknown')
                            self.change_regions.append((tag_name, region_start, i, 0, 0, 0, 0))
                        
                        region_start = i
                        region_kind = current_kind
                else:
                    # EQUAL region - close any open region
                    if region_start is not None:
                        tag_name = {
                            diff_desc.RegionDesc.DELETE: 'delete',
                            diff_desc.RegionDesc.ADD: 'insert',
                            diff_desc.RegionDesc.CHANGE: 'replace'
                        }.get(region_kind, 'unknown')
                        self.change_regions.append((tag_name, region_start, i, 0, 0, 0, 0))
                        region_start = None
                        region_kind = None
        
        # Close final region if open
        if region_start is not None:
            tag_name = {
                diff_desc.RegionDesc.DELETE: 'delete',
                diff_desc.RegionDesc.ADD: 'insert',
                diff_desc.RegionDesc.CHANGE: 'replace'
            }.get(region_kind, 'unknown')
            self.change_regions.append((tag_name, region_start, len(self.base_line_objects), 0, 0, 0, 0))
    
    def populate_content(self):
        self.base_line_area.set_line_numbers(self.base_line_nums)
        self.modified_line_area.set_line_numbers(self.modified_line_nums)
        
        self.base_text.setPlainText('\n'.join(self.base_display))
        self.modified_text.setPlainText('\n'.join(self.modified_display))
        
        # Store QTextBlock references in line objects for fast highlighting
        for i, line_obj in enumerate(self.base_line_objects):
            block = self.base_text.document().findBlockByNumber(i)
            line_obj.text_block_ = block
        
        for i, line_obj in enumerate(self.modified_line_objects):
            block = self.modified_text.document().findBlockByNumber(i)
            line_obj.text_block_ = block
        
        # Defer diff_map update until highlighting starts
        # self.diff_map.set_change_regions(self.change_regions, len(self.base_display))
    
    def apply_highlighting(self):
        import diff_desc
        palette = color_palettes.get_current_palette()
        
        for i, (base_line, modi_line) in enumerate(zip(self.base_line_objects,
                                                        self.modified_line_objects)):
            
            # BASE SIDE
            if not base_line.show_line_number():
                # Placeholder line
                self.highlight_line(self.base_text, i, palette.get_color('placeholder'))
            else:
                # Determine background color based on region type
                bg_color = None
                
                if base_line.region_:
                    region_kind = base_line.region_.kind_
                    
                    if region_kind == diff_desc.RegionDesc.DELETE or \
                       region_kind == diff_desc.RegionDesc.CHANGE:
                        bg_color = palette.get_color('base_changed_bg')
                    # EQUAL and ADD regions don't get background on base side
                
                if bg_color:
                    self.highlight_line(self.base_text, i, bg_color)
                    self.base_line_area.set_line_background(i, bg_color)
                
                # Always apply runs
                self.apply_runs(self.base_text, i, base_line)
            
            # MODIFIED SIDE
            if not modi_line.show_line_number():
                # Placeholder line
                self.highlight_line(self.modified_text, i, palette.get_color('placeholder'))
            else:
                # Determine background color based on region type
                bg_color = None
                
                if modi_line.region_:
                    region_kind = modi_line.region_.kind_
                    
                    if region_kind == diff_desc.RegionDesc.ADD or \
                       region_kind == diff_desc.RegionDesc.CHANGE:
                        bg_color = palette.get_color('modi_changed_bg')
                    # EQUAL and DELETE regions don't get background on modi side
                
                if bg_color:
                    self.highlight_line(self.modified_text, i, bg_color)
                    self.modified_line_area.set_line_background(i, bg_color)
                
                # Always apply runs
                self.apply_runs(self.modified_text, i, modi_line)
        
    def ensure_highlighting_applied(self):
        """Start progressive highlighting if not yet done."""
        if not self.highlighting_applied and not self.highlighting_in_progress:
            self.start_progressive_highlighting()
    
    def start_progressive_highlighting(self):
        """Start background highlighting in chunks."""
        # Update diff_map now that we're rendering
        self.diff_map.set_change_regions(self.change_regions, len(self.base_display))
        
        self.highlighting_in_progress = True
        self.highlighting_next_line = 0
        self.update_highlighting_status()
        QTimer.singleShot(0, self.highlight_next_chunk)
    
    def highlight_next_chunk(self):
        """Highlight next chunk of lines with batch formatting for performance."""
        if not self.highlighting_in_progress:
            return
        
        chunk_size = 1000  # Increased from 500 for better throughput
        start_line = self.highlighting_next_line
        end_line = min(start_line + chunk_size, len(self.base_line_objects))
        
        import diff_desc
        palette = color_palettes.get_current_palette()
        
        # Begin edit block for base text widget - batches all operations into single repaint
        base_cursor = self.base_text.textCursor()
        base_cursor.beginEditBlock()
        
        # Begin edit block for modified text widget
        modi_cursor = self.modified_text.textCursor()
        modi_cursor.beginEditBlock()
        
        try:
            for i in range(start_line, end_line):
                base_line = self.base_line_objects[i]
                modi_line = self.modified_line_objects[i]
                
                # BASE SIDE
                if not base_line.show_line_number():
                    self.highlight_line(self.base_text, i, palette.get_color('placeholder'), base_line)
                else:
                    bg_color = None
                    if base_line.region_:
                        region_kind = base_line.region_.kind_
                        if region_kind == diff_desc.RegionDesc.DELETE or \
                           region_kind == diff_desc.RegionDesc.CHANGE:
                            bg_color = palette.get_color('base_changed_bg')
                    
                    if bg_color:
                        self.highlight_line(self.base_text, i, bg_color, base_line)
                        self.base_line_area.set_line_background(i, bg_color)
                    
                    self.apply_runs(self.base_text, i, base_line)
                
                # MODIFIED SIDE
                if not modi_line.show_line_number():
                    self.highlight_line(self.modified_text, i, palette.get_color('placeholder'), modi_line)
                else:
                    bg_color = None
                    if modi_line.region_:
                        region_kind = modi_line.region_.kind_
                        if region_kind == diff_desc.RegionDesc.ADD or \
                           region_kind == diff_desc.RegionDesc.CHANGE:
                            bg_color = palette.get_color('modi_changed_bg')
                    
                    if bg_color:
                        self.highlight_line(self.modified_text, i, bg_color, modi_line)
                        self.modified_line_area.set_line_background(i, bg_color)
                    
                    self.apply_runs(self.modified_text, i, modi_line)
        finally:
            # End edit blocks - triggers single repaint for each widget
            base_cursor.endEditBlock()
            modi_cursor.endEditBlock()
        
        self.highlighting_next_line = end_line
        
        if end_line >= len(self.base_line_objects):
            # Done
            self.highlighting_in_progress = False
            self.highlighting_applied = True
            self.clear_highlighting_status()
        else:
            # Continue
            self.update_highlighting_status()
            QTimer.singleShot(0, self.highlight_next_chunk)
    
    def update_highlighting_status(self):
        """Update status bar with highlighting progress."""
        if not self.highlighting_in_progress:
            return
        total = len(self.base_line_objects)
        current = self.highlighting_next_line
        percent = int((current / total) * 100) if total > 0 else 0
        self.highlighting_label.setText(f"  Highlighting: {percent}% ({current}/{total} lines)")
    
    def clear_highlighting_status(self):
        """Clear highlighting status message."""
        self.highlighting_label.setText("")
    
    def restart_highlighting(self):
        """Cancel current highlighting and restart from beginning."""
        self.highlighting_in_progress = False
        self.highlighting_applied = False
        self.highlighting_next_line = 0
        self.start_progressive_highlighting()

    
    def highlight_line(self, text_widget, line_num, color, line_obj=None):
        # Use cached QTextBlock if available
        if line_obj and hasattr(line_obj, 'text_block_'):
            block = line_obj.text_block_
        else:
            block = text_widget.document().findBlockByNumber(line_num)
        
        if not block.isValid():
            return
        
        cursor = text_widget.textCursor()
        cursor.setPosition(block.position())
        
        block_fmt = QTextBlockFormat()
        block_fmt.setBackground(color)
        cursor.setBlockFormat(block_fmt)
    
    def apply_runs(self, text_widget, line_idx, line_obj):
        # Use cached QTextBlock reference from line object
        block = line_obj.text_block_ if hasattr(line_obj, 'text_block_') else text_widget.document().findBlockByNumber(line_idx)
        
        if not block.isValid():
            return
        
        doc_length = text_widget.document().characterCount()
        block_pos = block.position()
        
        if block_pos >= doc_length:
            return
        
        palette = color_palettes.get_current_palette()
        line_text = block.text()
        
        # Map color names to palette keys
        color_map = {
            'ADD': 'add_run',
            'DELETE': 'delete_run',
            'INTRALINE': 'intraline_run',
            'TRAILINGWS': 'TRAILINGWS',
            'TAB': 'TAB'
        }
        
        # Map color names to ignore flags
        ignore_map = {
            'INTRALINE': self.ignore_intraline,
            'TRAILINGWS': self.ignore_trailing_ws,
            'TAB': self.ignore_tab
        }
        
        # First pass: clear formatting for ignored run types
        for runs in [line_obj.runs_intraline_, line_obj.runs_tws_, line_obj.runs_tabs_]:
            if not runs:
                continue
                
            for run in runs:
                color_name = run.color()
                
                # If this type is being ignored, clear its formatting
                if color_name in ignore_map and ignore_map[color_name]:
                    # Check if this is a full-line run
                    if run.start_ == 0 and run.len_ >= len(line_text):
                        # Clear block formatting for full-line runs
                        cursor = text_widget.textCursor()
                        if block_pos < doc_length:
                            cursor.setPosition(block_pos)
                            block_fmt = QTextBlockFormat()
                            cursor.setBlockFormat(block_fmt)
                    else:
                        # Clear character formatting for partial-line runs
                        cursor = text_widget.textCursor()
                        start_pos = block_pos + run.start_
                        end_pos = block_pos + run.start_ + run.len_
                        
                        if start_pos < doc_length:
                            block_end = block_pos + len(line_text)
                            end_pos = min(end_pos, block_end, doc_length - 1)
                            
                            if end_pos > start_pos:
                                cursor.setPosition(start_pos)
                                cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
                                fmt = QTextCharFormat()
                                cursor.setCharFormat(fmt)  # Clear formatting
        
        # Second pass: apply all non-ignored run types in priority order
        # Lower priority: ADD, DELETE, INTRALINE
        # Higher priority: TRAILINGWS, TAB (both equal, never overlap)
        for runs in [line_obj.runs_added_, line_obj.runs_deleted_, 
                     line_obj.runs_intraline_, line_obj.runs_tws_, line_obj.runs_tabs_]:
            if not runs:
                continue
                
            for run in runs:
                color_name = run.color()
                
                # Skip if ignoring this type
                if color_name in ignore_map and ignore_map[color_name]:
                    continue
                
                # Get color from palette
                if color_name in color_map:
                    color = palette.get_color(color_map[color_name])
                    self._apply_single_run(text_widget, block, block_pos, doc_length, line_text, run, color)
    
    def _apply_single_run(self, text_widget, block, block_pos, doc_length, line_text, run, color):
        """Apply formatting for a single run."""
        if run.start_ == 0 and run.len_ >= len(line_text):
            # Full line formatting
            cursor = text_widget.textCursor()
            if block_pos < doc_length:
                cursor.setPosition(block_pos)
                block_fmt = QTextBlockFormat()
                block_fmt.setBackground(color)
                cursor.setBlockFormat(block_fmt)
        else:
            # Partial line formatting
            cursor = text_widget.textCursor()
            start_pos = block_pos + run.start_
            end_pos = block_pos + run.start_ + run.len_
            
            if start_pos < doc_length:
                block_end = block_pos + len(line_text)
                end_pos = min(end_pos, block_end, doc_length - 1)
                
                if end_pos > start_pos:
                    cursor.setPosition(start_pos)
                    cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
                    
                    fmt = QTextCharFormat()
                    fmt.setBackground(color)
                    cursor.mergeCharFormat(fmt)
    
    def init_scrollbars(self):
        self.v_scrollbar.setMaximum(self.base_text.verticalScrollBar().maximum())
        self.h_scrollbar.setMaximum(self.base_text.horizontalScrollBar().maximum())
        self.update_diff_map_viewport()
    
    def on_v_scroll(self, value):
        self.base_text.verticalScrollBar().setValue(value)
        self.modified_text.verticalScrollBar().setValue(value)
        self.update_diff_map_viewport()
    
    def on_h_scroll(self, value):
        self.base_text.horizontalScrollBar().setValue(value)
        self.modified_text.horizontalScrollBar().setValue(value)
    
    def sync_v_scroll_from_base(self, value):
        """Sync vertical scroll from base to modified"""
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self.v_scrollbar.setValue(value)
        self.modified_text.verticalScrollBar().setValue(value)
        self.update_diff_map_viewport()
        self.update_current_region_from_scroll()
        if self.modified_line_area:
            self.modified_line_area.update()
        self._syncing_scroll = False
    
    def sync_h_scroll_from_base(self, value):
        """Sync horizontal scroll from base to modified"""
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self.h_scrollbar.setValue(value)
        self.modified_text.horizontalScrollBar().setValue(value)
        if self.modified_line_area:
            self.modified_line_area.update()
        self._syncing_scroll = False
    
    def sync_v_scroll_from_modified(self, value):
        """Sync vertical scroll from modified to base"""
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self.v_scrollbar.setValue(value)
        self.base_text.verticalScrollBar().setValue(value)
        self.update_diff_map_viewport()
        self.update_current_region_from_scroll()
        if self.base_line_area:
            self.base_line_area.update()
        self._syncing_scroll = False
    
    def sync_h_scroll_from_modified(self, value):
        """Sync horizontal scroll from modified to base"""
        if self._syncing_scroll:
            return
        self._syncing_scroll = True
        self.h_scrollbar.setValue(value)
        self.base_text.horizontalScrollBar().setValue(value)
        if self.base_line_area:
            self.base_line_area.update()
        self._syncing_scroll = False
    
    def on_diff_map_wheel(self, event):
        self.base_text.wheelEvent(event)
    
    def update_diff_map_viewport(self):
        if len(self.base_display) == 0:
            return
        
        block = self.base_text.firstVisibleBlock()
        first_visible = block.blockNumber()
        
        viewport_height = self.base_text.viewport().height()
        line_height = self.base_text.fontMetrics().height()
        visible_lines = viewport_height // line_height if line_height > 0 else 10
        
        self.diff_map.set_viewport(first_visible, first_visible + visible_lines)
    
    def update_current_region_from_scroll(self):
        if self._target_region is not None:
            return
            
        if not self.change_regions:
            return
        
        block = self.base_text.firstVisibleBlock()
        first_visible = block.blockNumber()
        
        for i, (tag, start, end, *_) in enumerate(self.change_regions):
            if start <= first_visible < end:
                if self.current_region != i:
                    self.current_region = i
                    self.update_status()
                return
        
        for i, (tag, start, end, *_) in enumerate(self.change_regions):
            if start > first_visible:
                if self.current_region != i:
                    self.current_region = i
                    self.update_status()
                return
    
    def on_double_click(self, event, side):
        # Use NoteManager to take note
        if not hasattr(self, 'tab_manager') or not self.tab_manager:
            return
        
        note_mgr = self.tab_manager.note_mgr
        
        text_widget = self.base_text if side == 'base' else self.modified_text
        line_nums = self.base_line_nums if side == 'base' else self.modified_line_nums
        display_lines = self.base_display if side == 'base' else self.modified_display
        filename = self.base_file if side == 'base' else self.modified_file
        
        cursor = text_widget.cursorForPosition(event.pos())
        line_idx = cursor.blockNumber()
        
        if line_idx >= len(line_nums) or line_nums[line_idx] is None:
            return
        
        # Take note using NoteManager
        line_number = line_nums[line_idx]
        line_text = display_lines[line_idx]
        
        if note_mgr.take_note(filename, side, [line_number], [line_text], is_commit_msg=False):
            self.mark_noted_line(side, line_number)
            self.note_count += 1
            self.update_status()
    
    def take_note(self, side):
        # Use NoteManager to take note
        if not hasattr(self, 'tab_manager') or not self.tab_manager:
            return
        
        note_mgr = self.tab_manager.note_mgr
        
        text_widget = self.base_text if side == 'base' else self.modified_text
        line_nums = self.base_line_nums if side == 'base' else self.modified_line_nums
        display_lines = self.base_display if side == 'base' else self.modified_display
        filename = self.base_file if side == 'base' else self.modified_file
        
        cursor = text_widget.textCursor()
        if not cursor.hasSelection():
            return
        
        selection_start = cursor.selectionStart()
        selection_end = cursor.selectionEnd()
        
        doc = text_widget.document()
        start_block = doc.findBlock(selection_start)
        end_block = doc.findBlock(selection_end)
        
        start_block_num = start_block.blockNumber()
        end_block_num = end_block.blockNumber()
        
        if selection_end == end_block.position():
            end_block_num -= 1
        
        # Collect line numbers and texts
        selected_line_nums = []
        selected_line_texts = []
        
        for i in range(start_block_num, end_block_num + 1):
            if i < len(line_nums) and line_nums[i] is not None:
                selected_line_nums.append(line_nums[i])
                selected_line_texts.append(display_lines[i])
        
        if not selected_line_nums:
            return
        
        # Take note using NoteManager
        if note_mgr.take_note(filename, side, selected_line_nums, selected_line_texts, is_commit_msg=False):
            for line_num in selected_line_nums:
                self.mark_noted_line(side, line_num)
            self.note_count += 1
            self.update_status()
    
    def take_note_from_widget(self, side):
        self.take_note(side)
    
    def mark_noted_line(self, side, line_num):
        if side == 'base':
            self.base_noted_lines.add(line_num)
            for i, num in enumerate(self.base_line_nums):
                if num == line_num:
                    self.base_line_area.mark_noted(i)
                    # Mark the line with background color in the text widget
                    self.mark_text_line_noted(self.base_text, i)
        else:
            self.modified_noted_lines.add(line_num)
            for i, num in enumerate(self.modified_line_nums):
                if num == line_num:
                    self.modified_line_area.mark_noted(i)
                    # Mark the line with background color in the text widget
                    self.mark_text_line_noted(self.modified_text, i)
    
    def mark_text_line_noted(self, text_widget, line_idx):
        """Mark a line as noted with a background color"""
        if not hasattr(text_widget, 'noted_lines'):
            text_widget.noted_lines = set()
        text_widget.noted_lines.add(line_idx)
        text_widget.viewport().update()
    
    def on_diff_map_click(self, line):
        found_region = False
        for i, (tag, start, end, *_) in enumerate(self.change_regions):
            if start <= line < end:
                self.current_region = i
                found_region = True
                break
        
        if not found_region and self.change_regions:
            min_distance = float('inf')
            nearest_region = 0
            
            for i, (tag, start, end, *_) in enumerate(self.change_regions):
                distance = abs(start - line)
                if distance < min_distance:
                    min_distance = distance
                    nearest_region = i
            
            self.current_region = nearest_region
        
        self.center_on_line(line)
        self.highlight_current_region()
        self.update_status()
    
    def center_on_line(self, line):
        base_block = self.base_text.document().findBlockByNumber(line)
        if base_block.isValid():
            cursor = self.base_text.textCursor()
            cursor.setPosition(base_block.position())
            self.base_text.setTextCursor(cursor)
            self.base_text.centerCursor()
        
        modi_block = self.modified_text.document().findBlockByNumber(line)
        if modi_block.isValid():
            cursor = self.modified_text.textCursor()
            cursor.setPosition(modi_block.position())
            self.modified_text.setTextCursor(cursor)
            self.modified_text.centerCursor()
        
        self.base_text.set_focused_line(line)
        self.modified_text.set_focused_line(line)
        
        self.base_line_area.update()
        self.modified_line_area.update()
        
        self.update_diff_map_viewport()
    
    def center_current_region(self):
        if self.change_regions and 0 <= self.current_region < len(self.change_regions):
            self._target_region = self.current_region
            
            _, start, *_ = self.change_regions[self.current_region]
            self.center_on_line(start)
            self.highlight_current_region()
            self.update_status()
            
            QTimer.singleShot(200, self.check_navigation_complete)
    
    def check_navigation_complete(self):
        if self._target_region is None:
            return
        
        if not self.change_regions or self._target_region >= len(self.change_regions):
            self._target_region = None
            return
        
        _, start, end, *_ = self.change_regions[self._target_region]
        block = self.base_text.firstVisibleBlock()
        first_visible = block.blockNumber()
        
        viewport_height = self.base_text.viewport().height()
        line_height = self.base_text.fontMetrics().height()
        visible_lines = viewport_height // line_height if line_height > 0 else 10
        last_visible = first_visible + visible_lines
        
        if start >= first_visible and start < last_visible:
            self._target_region = None
    
    def next_change(self):
        if not self.change_regions:
            return
        
        if self.current_region >= len(self.change_regions) - 1:
            if len(self.change_regions) == 1:
                self._target_region = 0
                self.current_region = 0
                _, start, *_ = self.change_regions[0]
                self.center_on_line(start)
                self.highlight_current_region()
                self.update_status()
                QTimer.singleShot(200, self.check_navigation_complete)
            return
        
        self.current_region += 1
        self._target_region = self.current_region
        _, start, *_ = self.change_regions[self.current_region]
        self.center_on_line(start)
        self.highlight_current_region()
        self.update_status()
        
        QTimer.singleShot(200, self.check_navigation_complete)
    
    def prev_change(self):
        if not self.change_regions:
            return
        
        if self.current_region <= 0:
            if len(self.change_regions) == 1:
                self._target_region = 0
                self.current_region = 0
                _, start, *_ = self.change_regions[0]
                self.center_on_line(start)
                self.highlight_current_region()
                self.update_status()
                QTimer.singleShot(200, self.check_navigation_complete)
            return
        
        self.current_region -= 1
        self._target_region = self.current_region
        _, start, *_ = self.change_regions[self.current_region]
        self.center_on_line(start)
        self.highlight_current_region()
        self.update_status()
        
        QTimer.singleShot(200, self.check_navigation_complete)
    
    def highlight_current_region(self):
        if not self.change_regions:
            return
        
        _, start, end, *_ = self.change_regions[self.current_region]
        
        self.base_text.set_region_highlight(start, end)
        self.modified_text.set_region_highlight(start, end)
    
    def update_status(self):
        total = self.n_changed_regions
        current = self.current_region + 1 if total > 0 else 0
        self.region_label.setText(f"Region: {current} of {total}")
        self.bookmarks_label.setText(f"Bookmarks: {len(self.bookmarked_lines)}")
        self.notes_label.setText(f"Notes: {self.note_count}")
    
    def toggle_diff_map(self):
        if self.diff_map_visible:
            self.diff_map.hide()
            self.diff_map_visible = False
        else:
            self.diff_map.show()
            self.diff_map_visible = True
    
    def toggle_line_numbers(self):
        if self.line_numbers_visible:
            self.base_line_area.hide()
            self.modified_line_area.hide()
            self.line_numbers_visible = False
        else:
            self.base_line_area.show()
            self.modified_line_area.show()
            self.line_numbers_visible = True
    
    def toggle_bookmark(self):
        """Toggle bookmark on current focused line"""
        # Determine which text widget has focus
        if self.base_text.hasFocus():
            line_idx = self.base_text.textCursor().blockNumber()
            text_widget = self.base_text
        elif self.modified_text.hasFocus():
            line_idx = self.modified_text.textCursor().blockNumber()
            text_widget = self.modified_text
        else:
            return
        
        # Toggle in local set
        if line_idx in self.bookmarked_lines:
            self.bookmarked_lines.remove(line_idx)
        else:
            self.bookmarked_lines.add(line_idx)
        
        # Store on BOTH text widgets so paintEvent can access directly
        if not hasattr(self.base_text, 'bookmarked_lines'):
            self.base_text.bookmarked_lines = set()
        if not hasattr(self.modified_text, 'bookmarked_lines'):
            self.modified_text.bookmarked_lines = set()
        
        if line_idx in self.bookmarked_lines:
            self.base_text.bookmarked_lines.add(line_idx)
            self.modified_text.bookmarked_lines.add(line_idx)
        else:
            self.base_text.bookmarked_lines.discard(line_idx)
            self.modified_text.bookmarked_lines.discard(line_idx)

        # Sync with global bookmarks using stored references
        if hasattr(self, 'tab_manager') and hasattr(self, 'tab_index'):
            if line_idx in self.bookmarked_lines:
                self.tab_manager.bookmark_mgr.add_bookmark(self.tab_index, line_idx)
            else:
                self.tab_manager.bookmark_mgr.remove_bookmark(self.tab_index, line_idx)

        # Update visuals
        self.base_text.viewport().update()
        self.modified_text.viewport().update()
        self.update_status()
    
    def jump_to_note_from_cursor(self):
        """Jump to note for the line at cursor position (Ctrl+J handler)"""
        # Determine which text widget has focus
        if self.base_text.hasFocus():
            text_widget = self.base_text
            side = 'base'
        elif self.modified_text.hasFocus():
            text_widget = self.modified_text
            side = 'modified'
        else:
            return
        
        # Get cursor position
        cursor = text_widget.textCursor()
        pos = text_widget.cursorRect(cursor).center()
        
        # Use note_manager's show_jump_to_note_menu to check and get jump action
        if not hasattr(self, 'tab_manager') or not hasattr(self.tab_manager, 'note_mgr'):
            return
        
        jump_action_func = self.tab_manager.note_mgr.show_jump_to_note_menu(pos, text_widget, side, self)
        if jump_action_func:
            jump_action_func()
    
    def increase_font_size(self):
        """Increase font size (max 24pt)"""
        if self.current_font_size < 24:
            self.current_font_size += 1
            self._apply_font_size()
    
    def decrease_font_size(self):
        """Decrease font size (min 6pt)"""
        if self.current_font_size > 6:
            self.current_font_size -= 1
            self._apply_font_size()
    
    def reset_font_size(self):
        """Reset font size to default (12pt)"""
        self.current_font_size = 12
        self._apply_font_size()
    
    def _apply_font_size(self):
        """Apply current font size to all text widgets and line number areas"""
        text_font = QFont("Courier", self.current_font_size, QFont.Weight.Bold)
        
        # Apply to text widgets
        self.base_text.setFont(text_font)
        self.modified_text.setFont(text_font)
        
        # Apply to line number areas
        self.base_line_area.setFont(text_font)
        self.base_line_area._font = text_font
        self.modified_line_area.setFont(text_font)
        self.modified_line_area._font = text_font
        
        # Force update of line number areas
        self.base_line_area.update()
        self.modified_line_area.update()
        
        # Force update of text widget viewports
        self.base_text.viewport().update()
        self.modified_text.viewport().update()
    
    def showEvent(self, event):
        """Override to ensure highlighting is applied when window becomes visible"""
        super().showEvent(event)
        # This is a safety net in case the tab becomes visible through a path
        # other than on_tab_changed (e.g., first show, or restoration from minimize)
        self.ensure_highlighting_applied()
    
    def eventFilter(self, obj, event):
        """Central event coordinator for base and modified text widgets"""
        # Handle Tab/Shift+Tab for switching between panes
        if event.type() == event.Type.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            
            if key == Qt.Key.Key_Tab or key == Qt.Key.Key_Backtab:
                if obj == self.base_text or obj == self.modified_text:
                    current_line = obj.textCursor().blockNumber()
                    
                    # Determine target widget
                    if obj == self.base_text:
                        target_widget = self.modified_text
                    else:
                        target_widget = self.base_text
                    
                    # Move cursor in target widget to same line
                    block = target_widget.document().findBlockByNumber(current_line)
                    if block.isValid():
                        cursor = target_widget.textCursor()
                        cursor.setPosition(block.position())
                        target_widget.setTextCursor(cursor)
                    
                    # Set focus to target widget
                    target_widget.setFocus(Qt.FocusReason.TabFocusReason)
                    
                    # Update focused line markers
                    obj.set_focused_line(current_line)
                    target_widget.set_focused_line(current_line)
                    
                    # Consume the event
                    return True
            
            # All key handling now goes through tab_manager's keybinding system
            # No hardcoded keys here anymore
            
            # Handle navigation keys - sync scroll position between panes
            is_nav_key = key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_PageUp,
                                Qt.Key.Key_PageDown, Qt.Key.Key_Home, Qt.Key.Key_End,
                                Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Space)
            
            if is_nav_key and (obj == self.base_text or obj == self.modified_text):
                # Let the event propagate so widget can move its cursor first
                # We'll sync afterward using a timer
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._sync_navigation_scroll(obj))
        
        # Handle wheel events - sync scroll position between panes
        if event.type() == event.Type.Wheel:
            if obj == self.base_text or obj == self.modified_text:
                # Let event propagate so widget can scroll first
                # We'll sync afterward using a timer
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._sync_wheel_scroll(obj))
        
        # Handle focus events for synchronized focused line markers
        if event.type() == event.Type.FocusIn:
            if obj == self.base_text or obj == self.modified_text:
                line = obj.textCursor().blockNumber()
                # Update focused line markers on both widgets
                self.base_text.set_focused_line(line)
                self.modified_text.set_focused_line(line)
                # Update line number areas
                if self.base_line_area:
                    self.base_line_area.update()
                if self.modified_line_area:
                    self.modified_line_area.update()
                # Update viewports
                self.base_text.viewport().update()
                self.modified_text.viewport().update()
        
        elif event.type() == event.Type.FocusOut:
            if obj == self.base_text or obj == self.modified_text:
                # Update line number areas
                if self.base_line_area:
                    self.base_line_area.update()
                if self.modified_line_area:
                    self.modified_line_area.update()
                # Update viewports
                self.base_text.viewport().update()
                self.modified_text.viewport().update()
        
        # Pass through - handlers still in SyncedPlainTextEdit for other events
        return False  # Let event propagate normally
    
    def _sync_navigation_scroll(self, source_widget):
        """Sync scroll position from source widget to the other widget after navigation key"""
        if source_widget == self.base_text:
            target_widget = self.modified_text
        else:
            target_widget = self.base_text

        # Sync scroll positions
        target_widget.verticalScrollBar().setValue(
            source_widget.verticalScrollBar().value())
        target_widget.horizontalScrollBar().setValue(
            source_widget.horizontalScrollBar().value())

        # Get new line from source widget
        new_line = source_widget.textCursor().blockNumber()

        # Update focused line markers
        target_widget.set_focused_line(new_line)

        # Update viewports and line number areas
        target_widget.viewport().update()
        if target_widget.line_number_area:
            target_widget.line_number_area.update()

    def _sync_navigation_from_widget(self, source_widget, new_line):
        """Sync navigation from source widget to target widget - called from SyncedPlainTextEdit.keyPressEvent"""
        if source_widget == self.base_text:
            target_widget = self.modified_text
        else:
            target_widget = self.base_text

        # Sync scroll positions
        target_widget.verticalScrollBar().setValue(
            source_widget.verticalScrollBar().value())
        target_widget.horizontalScrollBar().setValue(
            source_widget.horizontalScrollBar().value())

        # Update focused line on target
        target_widget.set_focused_line(new_line)

        # Update target viewport and line number area
        target_widget.viewport().update()
        if target_widget.line_number_area:
            target_widget.line_number_area.update()

        QApplication.processEvents()
    
    def _sync_wheel_scroll(self, source_widget):
        """Sync scroll position from source widget to the other widget after wheel event"""
        if source_widget == self.base_text:
            target_widget = self.modified_text
        else:
            target_widget = self.base_text
        
        # Sync scroll positions
        target_widget.verticalScrollBar().setValue(
            source_widget.verticalScrollBar().value())
        target_widget.horizontalScrollBar().setValue(
            source_widget.horizontalScrollBar().value())
        
        # Update line number areas
        if target_widget.line_number_area:
            target_widget.line_number_area.update()
    
    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        # All command keys now handled by DiffViewer.eventFilter
        # This keyPressEvent is only reached when DiffViewer itself has focus (rare/never)
        # The handlers below (N, P, C, T, B) are also in eventFilter and are duplicates
        
        if key == Qt.Key.Key_N:
            self.next_change()
        elif key == Qt.Key.Key_P:
            self.prev_change()
        elif key == Qt.Key.Key_C:
            self.center_current_region()
        elif key == Qt.Key.Key_T:
            self.current_region = 0
            if self.change_regions:
                self.center_on_line(0)
            self.update_status()
        elif key == Qt.Key.Key_B:
            if self.change_regions:
                self.current_region = len(self.change_regions) - 1
                self.center_on_line(len(self.base_display) - 1)
            self.update_status()
        else:
            super().keyPressEvent(event)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_diff_map_viewport()
    
    def is_change_region(self, line_idx):
        """Check if a line is part of a change region (deleted or added)"""
        import diff_desc
        
        # Check base file for deleted regions
        if 0 <= line_idx < len(self.base_line_objects):
            line_obj = self.base_line_objects[line_idx]
            if line_obj.region_:
                if line_obj.region_.kind_ == diff_desc.RegionDesc.DELETE:
                    return True
        
        # Check modified file for added regions
        if 0 <= line_idx < len(self.modified_line_objects):
            line_obj = self.modified_line_objects[line_idx]
            if line_obj.region_:
                if line_obj.region_.kind_ == diff_desc.RegionDesc.ADD:
                    return True
        
        return False
    
    def find_change_region_bounds(self, line_idx):
        """Find the start and end of the change region (deleted or added) containing line_idx"""
        import diff_desc
        if not self.is_change_region(line_idx):
            return None, None
        
        # Determine which type of region we're in
        is_deleted = False
        is_added = False
        
        if 0 <= line_idx < len(self.base_line_objects):
            line_obj = self.base_line_objects[line_idx]
            if line_obj.region_ and line_obj.region_.kind_ == diff_desc.RegionDesc.DELETE:
                is_deleted = True
        
        if 0 <= line_idx < len(self.modified_line_objects):
            line_obj = self.modified_line_objects[line_idx]
            if line_obj.region_ and line_obj.region_.kind_ == diff_desc.RegionDesc.ADD:
                is_added = True
        
        # Helper to check if line is same region type
        def is_same_region_type(idx):
            if is_deleted:
                if 0 <= idx < len(self.base_line_objects):
                    obj = self.base_line_objects[idx]
                    return obj.region_ and obj.region_.kind_ == diff_desc.RegionDesc.DELETE
            elif is_added:
                if 0 <= idx < len(self.modified_line_objects):
                    obj = self.modified_line_objects[idx]
                    return obj.region_ and obj.region_.kind_ == diff_desc.RegionDesc.ADD
            return False
        
        start = line_idx
        while start > 0 and is_same_region_type(start - 1):
            start -= 1
        
        max_lines = max(len(self.base_line_objects), len(self.modified_line_objects))
        end = line_idx
        while end < max_lines - 1 and is_same_region_type(end + 1):
            end += 1
        
        return start, end
    
    def collapse_change_region(self, line_idx):
        """Collapse the change region (deleted or added) containing line_idx"""
        import diff_desc
        start, end = self.find_change_region_bounds(line_idx)
        if start is None or end is None:
            return
        
        # Determine region type
        region_type = None
        if 0 <= line_idx < len(self.base_line_objects):
            line_obj = self.base_line_objects[line_idx]
            if line_obj.region_ and line_obj.region_.kind_ == diff_desc.RegionDesc.DELETE:
                region_type = 'deleted'
        
        if 0 <= line_idx < len(self.modified_line_objects):
            line_obj = self.modified_line_objects[line_idx]
            if line_obj.region_ and line_obj.region_.kind_ == diff_desc.RegionDesc.ADD:
                region_type = 'added'
        
        if region_type is None:
            return
        
        region_tuple = (start, end, region_type)
        if region_tuple in self.collapsed_regions:
            return
        
        self.collapsed_regions.append(region_tuple)
        self._apply_collapsed_regions()
    
    def collapse_all_change_regions(self):
        """Collapse all change regions (deleted and added)"""
        import diff_desc
        
        # Store tuples of (start, end, 'deleted'/'added') to track which side
        self.collapsed_regions = []
        
        # Process deleted regions in base file
        in_delete_region = False
        region_start = None
        
        for i, line_obj in enumerate(self.base_line_objects):
            is_deleted = (line_obj.region_ and 
                         line_obj.region_.kind_ == diff_desc.RegionDesc.DELETE)
            
            if is_deleted and not in_delete_region:
                in_delete_region = True
                region_start = i
            elif not is_deleted and in_delete_region:
                self.collapsed_regions.append((region_start, i - 1, 'deleted'))
                in_delete_region = False
                region_start = None
        
        if in_delete_region and region_start is not None:
            self.collapsed_regions.append((region_start, len(self.base_line_objects) - 1, 'deleted'))
        
        # Process added regions in modified file
        in_add_region = False
        region_start = None
        
        for i, line_obj in enumerate(self.modified_line_objects):
            is_added = (line_obj.region_ and 
                       line_obj.region_.kind_ == diff_desc.RegionDesc.ADD)
            
            if is_added and not in_add_region:
                in_add_region = True
                region_start = i
            elif not is_added and in_add_region:
                self.collapsed_regions.append((region_start, i - 1, 'added'))
                in_add_region = False
                region_start = None
        
        if in_add_region and region_start is not None:
            self.collapsed_regions.append((region_start, len(self.modified_line_objects) - 1, 'added'))
        
        self.all_collapsed = True
        self._apply_collapsed_regions()
    
    def uncollapse_region(self, line_idx):
        """Uncollapse the region containing line_idx"""
        for region in self.collapsed_regions:
            start, end, region_type = region
            if start <= line_idx <= end:
                self.collapsed_regions.remove(region)
                self._apply_collapsed_regions()
                return
    
    def uncollapse_all_regions(self):
        """Uncollapse all regions"""
        self.collapsed_regions = []
        self.all_collapsed = False
        self._apply_collapsed_regions()
    
    def is_line_in_collapsed_region(self, line_idx):
        """Check if line_idx is within any collapsed region"""
        for start, end, region_type in self.collapsed_regions:
            if start <= line_idx <= end:
                return True
        return False
    
    def _apply_collapsed_regions(self):
        """Apply the current collapsed regions by hiding blocks"""
        base_doc = self.base_text.document()
        modified_doc = self.modified_text.document()
        
        # Update visibility of all blocks
        for i in range(base_doc.blockCount()):
            base_block = base_doc.findBlockByNumber(i)
            modified_block = modified_doc.findBlockByNumber(i)
            
            if not base_block.isValid() or not modified_block.isValid():
                continue
            
            should_hide = False
            
            # Check if this line is inside a collapsed region (but not the first line)
            for start, end, region_type in self.collapsed_regions:
                if start < i <= end:
                    should_hide = True
                    break
            
            # Set visibility
            base_block.setVisible(not should_hide)
            modified_block.setVisible(not should_hide)
        
        # Store collapsed marker info for painting
        self.base_text.collapsed_markers = {}
        self.modified_text.collapsed_markers = {}
        
        for start, end, region_type in self.collapsed_regions:
            num_lines = end - start + 1
            
            # Store marker on BOTH sides (so both panes show the marker)
            self.base_text.collapsed_markers[start] = (num_lines, region_type)
            self.modified_text.collapsed_markers[start] = (num_lines, region_type)
        
        # Update the document layout
        base_doc.markContentsDirty(0, base_doc.characterCount())
        modified_doc.markContentsDirty(0, modified_doc.characterCount())
        
        # Force immediate repaint of the entire viewport
        self.base_text.viewport().repaint()
        self.modified_text.viewport().repaint()
        self.base_line_area.repaint()
        self.modified_line_area.repaint()
    
    def refresh_colors(self):
        """Refresh all colors from the current palette"""
        self.apply_highlighting()
        self.diff_map.update()
    
    def has_unsaved_changes(self):
        """Diff viewers don't have unsaved changes"""
        return False

    def focus_content(self):
        """Set Qt focus to the base text widget"""
        self.base_text.setFocus()

    def save_buffer(self):
        """Diff viewer tabs have nothing to save"""
        pass

    def search_content(self, search_text, case_sensitive, regex, search_base=True, search_modi=True):
        """
        Search for text in diff viewer.

        Returns:
            List of tuples: (side, display_line_num, line_idx, line_text, char_pos)
        """
        results = []
        
        # Search in base
        if search_base:
            for line_idx, (line_text, line_num) in enumerate(zip(self.base_display, self.base_line_nums)):
                if line_num is not None:
                    matches = self._find_matches_in_line(line_text, search_text, case_sensitive, regex)
                    for char_pos, matched_text in matches:
                        results.append(('base', line_num, line_idx, line_text, char_pos))
        
        # Search in modified
        if search_modi:
            for line_idx, (line_text, line_num) in enumerate(zip(self.modified_display, self.modified_line_nums)):
                if line_num is not None:
                    matches = self._find_matches_in_line(line_text, search_text, case_sensitive, regex)
                    for char_pos, matched_text in matches:
                        results.append(('modified', line_num, line_idx, line_text, char_pos))
        
        return results

    def _find_matches_in_line(self, line_text, search_text, case_sensitive, regex):
        """Find all match positions in a line. Returns list of (start_pos, match_text) tuples."""
        import re
        matches = []
        
        if regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(search_text, flags)
                for match in pattern.finditer(line_text):
                    matches.append((match.start(), match.group()))
            except re.error:
                pass
        else:
            search_str = search_text if case_sensitive else search_text.lower()
            search_in = line_text if case_sensitive else line_text.lower()
            
            pos = 0
            while True:
                found_pos = search_in.find(search_str, pos)
                if found_pos < 0:
                    break
                matched_text = line_text[found_pos:found_pos + len(search_text)]
                matches.append((found_pos, matched_text))
                pos = found_pos + len(search_text)
        
        return matches
    
    def run(self):
        self.show()
        sys.exit(self._app.exec())
