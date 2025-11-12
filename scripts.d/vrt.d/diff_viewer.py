#!/usr/bin/env python3
# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
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
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QLabel, QScrollBar, QFrame, QMenu,
                              QMessageBox, QDialog, QPushButton)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (QColor, QFont, QTextCursor, QAction, QFontMetrics,
                         QTextCharFormat, QTextBlockFormat, QPainter, QPen)

from utils import extract_display_path
from search_dialogs import SearchDialog, SearchResultDialog
from ui_components import LineNumberArea, DiffMapWidget, SyncedPlainTextEdit
from commit_msg_dialog import CommitMsgDialog
import color_palettes


class DiffViewer(QMainWindow):
    def __init__(self, base_file: str, modified_file: str, note_file: str, 
                 commit_msg_file: str, max_line_length: int, show_diff_map: bool,
                 show_line_numbers: bool):
        if QApplication.instance() is None:
            self._app = QApplication(sys.argv)
        else:
            self._app = QApplication.instance()
        
        super().__init__()
        
        self.base_file = base_file
        self.modified_file = modified_file
        self.note_file = note_file
        self.commit_msg_file = commit_msg_file
        self.max_line_length = max_line_length
        self.show_diff_map = show_diff_map
        self.show_line_numbers = show_line_numbers
        self.note_count = 0
        
        self.base_noted_lines = set()
        self.modified_noted_lines = set()
        
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
        self.highlighting_applied = False  # Deferred until tab becomes visible
        self.highlighting_in_progress = False  # True during background highlighting
        self.highlighting_next_line = 0  # Next line to highlight
        self._needs_highlighting_update = False  # Set by tab_manager for deferred updates
        self._needs_color_refresh = False  # Set by tab_manager for deferred color updates
        
        self.setup_gui()
    
    def setup_gui(self):
        self.setWindowTitle(f"Diff Viewer: {self.base_file} vs {self.modified_file}")
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        label_layout = QHBoxLayout()
        
        base_container = QHBoxLayout()
        base_type_label = QLabel("Base")
        base_type_label.setStyleSheet("font-weight: bold; color: blue; padding: 2px 5px;")
        base_file_label = QLabel(extract_display_path(self.base_file))
        base_file_label.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
        base_container.addWidget(base_type_label)
        base_container.addWidget(base_file_label, 1)
        
        spacer = QLabel("")
        
        modified_container = QHBoxLayout()
        modified_type_label = QLabel("Modified")
        modified_type_label.setStyleSheet("font-weight: bold; color: green; padding: 2px 5px;")
        modified_file_label = QLabel(extract_display_path(self.modified_file))
        modified_file_label.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
        modified_container.addWidget(modified_type_label)
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
        self.notes_label = QLabel("Notes: 0")
        
        status_layout.addWidget(self.region_label)
        status_layout.addStretch()
        status_layout.addWidget(self.highlighting_label)
        status_layout.addStretch()
        status_layout.addWidget(self.notes_label)
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
        status_frame.setLayout(status_layout)
        main_layout.addWidget(status_frame)
        
        self.base_text.set_other_widget(self.modified_text)
        self.modified_text.set_other_widget(self.base_text)
        
        self.base_text.verticalScrollBar().valueChanged.connect(self.sync_v_scroll)
        self.base_text.horizontalScrollBar().valueChanged.connect(self.sync_h_scroll)
        
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
    
    def set_changed_region_count(self, count):
        """Set the number of changed regions from the diff descriptor"""
        self.n_changed_regions = count
    
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
            if hasattr(base_line, 'region_') and base_line.region_:
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
        
        # Defer diff_map update until highlighting starts
        # self.diff_map.set_change_regions(self.change_regions, len(self.base_display))
    
    def apply_highlighting(self):
        if False:  # Debug timing
            import time
            start_time = time.time()
        
        import diff_desc
        palette = color_palettes.get_current_palette()
        
        for i, (base_line, modi_line) in enumerate(zip(self.base_line_objects,
                                                        self.modified_line_objects)):
            
            # BASE SIDE
            if not base_line.show_line_number():
                # Placeholder line
                self.highlight_line(self.base_text, i, palette.get_color('placeholder'))
            elif hasattr(base_line, 'uncolored_') and base_line.uncolored_:
                # Line has no colors to apply - skip all highlighting
                pass
            else:
                # Determine background color based on region type
                bg_color = None
                
                if hasattr(base_line, 'region_') and base_line.region_:
                    region_kind = base_line.region_.kind_
                    
                    if region_kind == diff_desc.RegionDesc.DELETE or \
                       region_kind == diff_desc.RegionDesc.CHANGE:
                        bg_color = palette.get_color('base_changed_bg')
                    # EQUAL and ADD regions don't get background on base side
                
                if bg_color:
                    self.highlight_line(self.base_text, i, bg_color)
                    self.base_line_area.set_line_background(i, bg_color)
                
                # Always apply runs for colored lines
                self.apply_runs(self.base_text, i, base_line)
            
            # MODIFIED SIDE
            if not modi_line.show_line_number():
                # Placeholder line
                self.highlight_line(self.modified_text, i, palette.get_color('placeholder'))
            elif hasattr(modi_line, 'uncolored_') and modi_line.uncolored_:
                # Line has no colors to apply - skip all highlighting
                pass
            else:
                # Determine background color based on region type
                bg_color = None
                
                if hasattr(modi_line, 'region_') and modi_line.region_:
                    region_kind = modi_line.region_.kind_
                    
                    if region_kind == diff_desc.RegionDesc.ADD or \
                       region_kind == diff_desc.RegionDesc.CHANGE:
                        bg_color = palette.get_color('modi_changed_bg')
                    # EQUAL and DELETE regions don't get background on modi side
                
                if bg_color:
                    self.highlight_line(self.modified_text, i, bg_color)
                    self.modified_line_area.set_line_background(i, bg_color)
                
                # Always apply runs for colored lines
                self.apply_runs(self.modified_text, i, modi_line)
        
        if False:  # Debug timing
            elapsed = time.time() - start_time
            print(f"apply_highlighting: {elapsed:.3f} seconds ({len(self.base_line_objects)} lines)")
            sys.stdout.flush()
    
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
        """Highlight next chunk of lines."""
        if not self.highlighting_in_progress:
            return
        
        chunk_size = 500
        start_line = self.highlighting_next_line
        end_line = min(start_line + chunk_size, len(self.base_line_objects))
        
        import diff_desc
        palette = color_palettes.get_current_palette()
        
        for i in range(start_line, end_line):
            base_line = self.base_line_objects[i]
            modi_line = self.modified_line_objects[i]
            
            # BASE SIDE
            if not base_line.show_line_number():
                self.highlight_line(self.base_text, i, palette.get_color('placeholder'))
            elif hasattr(base_line, 'uncolored_') and base_line.uncolored_:
                pass
            else:
                bg_color = None
                if hasattr(base_line, 'region_') and base_line.region_:
                    region_kind = base_line.region_.kind_
                    if region_kind == diff_desc.RegionDesc.DELETE or \
                       region_kind == diff_desc.RegionDesc.CHANGE:
                        bg_color = palette.get_color('base_changed_bg')
                
                if bg_color:
                    self.highlight_line(self.base_text, i, bg_color)
                    self.base_line_area.set_line_background(i, bg_color)
                self.apply_runs(self.base_text, i, base_line)
            
            # MODIFIED SIDE
            if not modi_line.show_line_number():
                self.highlight_line(self.modified_text, i, palette.get_color('placeholder'))
            elif hasattr(modi_line, 'uncolored_') and modi_line.uncolored_:
                pass
            else:
                bg_color = None
                if hasattr(modi_line, 'region_') and modi_line.region_:
                    region_kind = modi_line.region_.kind_
                    if region_kind == diff_desc.RegionDesc.ADD or \
                       region_kind == diff_desc.RegionDesc.CHANGE:
                        bg_color = palette.get_color('modi_changed_bg')
                
                if bg_color:
                    self.highlight_line(self.modified_text, i, bg_color)
                    self.modified_line_area.set_line_background(i, bg_color)
                self.apply_runs(self.modified_text, i, modi_line)
        
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

    
    def highlight_line(self, text_widget, line_num, color):
        block = text_widget.document().findBlockByNumber(line_num)
        if not block.isValid():
            return
        
        cursor = text_widget.textCursor()
        cursor.setPosition(block.position())
        
        block_fmt = QTextBlockFormat()
        block_fmt.setBackground(color)
        cursor.setBlockFormat(block_fmt)
    
    def apply_runs(self, text_widget, line_idx, line_obj):
        if not hasattr(line_obj, 'runs_'):
            return
        
        block = text_widget.document().findBlockByNumber(line_idx)
        if not block.isValid():
            return
        
        doc_length = text_widget.document().characterCount()
        block_pos = block.position()
        
        if block_pos >= doc_length:
            return
        
        for run in line_obj.runs_:
            color_name = run.color()
            color = None
            palette = color_palettes.get_current_palette()
            
            if color_name == 'ADD':
                color = palette.get_color('add_run')
            elif color_name == 'DELETE':
                color = palette.get_color('delete_run')
            elif color_name == 'INTRALINE':
                color = palette.get_color('intraline_run')
            elif color_name == 'WS':
                # Only highlight if not ignoring whitespace
                if not self.ignore_ws:
                    color = palette.get_color('WS')
                else:
                    # Actively clear WS formatting
                    color = QColor(0, 0, 0, 0)
            elif color_name == 'TAB':
                # Only highlight if not ignoring tabs
                if not self.ignore_tab:
                    color = palette.get_color('TAB')
                else:
                    # Actively clear TAB formatting
                    color = QColor(0, 0, 0, 0)
            elif color_name == 'TRAILINGWS':
                # Only highlight if not ignoring trailing whitespace
                if not self.ignore_trailing_ws:
                    color = palette.get_color('TRAILINGWS')
                else:
                    # Actively clear TRAILINGWS formatting
                    color = QColor(0, 0, 0, 0)
            
            if color:
                line_text = block.text()
                
                if run.start_ == 0 and run.len_ >= len(line_text):
                    cursor = text_widget.textCursor()
                    if block_pos < doc_length:
                        cursor.setPosition(block_pos)
                        block_fmt = QTextBlockFormat()
                        block_fmt.setBackground(color)
                        cursor.setBlockFormat(block_fmt)
                else:
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
    
    def sync_v_scroll(self, value):
        self.v_scrollbar.setValue(value)
        self.modified_text.verticalScrollBar().setValue(value)
        self.update_diff_map_viewport()
        self.update_current_region_from_scroll()
    
    def sync_h_scroll(self, value):
        self.h_scrollbar.setValue(value)
        self.modified_text.horizontalScrollBar().setValue(value)
    
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
        if not self.note_file:
            QMessageBox.information(self, 'Note Taking Disabled',
                                  'No note file supplied.')
            return
        
        text_widget = self.base_text if side == 'base' else self.modified_text
        line_nums = self.base_line_nums if side == 'base' else self.modified_line_nums
        display_lines = self.base_display if side == 'base' else self.modified_display
        filename = self.base_file if side == 'base' else self.modified_file
        
        cursor = text_widget.cursorForPosition(event.pos())
        line_idx = cursor.blockNumber()
        
        if line_idx >= len(line_nums) or line_nums[line_idx] is None:
            return
        
        with open(self.note_file, 'a') as f:
            prefix = '(base): ' if side == 'base' else '(modi): '
            clean_filename = extract_display_path(filename)
            f.write(f"> {prefix}{clean_filename}\n")
            f.write(f">   {line_nums[line_idx]}: {display_lines[line_idx]}\n>\n\n\n")
        
        self.mark_noted_line(side, line_nums[line_idx])
        self.note_count += 1
        self.update_status()
    
    def get_commit_msg_lines(self):
        if not self.commit_msg_file:
            return []
        
        try:
            with open(self.commit_msg_file, 'r') as f:
                return f.read().split('\n')
        except Exception:
            return []
    
    def take_note(self, side):
        if not self.note_file:
            QMessageBox.information(self, 'Note Taking Disabled',
                                  'No note file supplied.')
            return
        
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
        
        with open(self.note_file, 'a') as f:
            prefix = '(base): ' if side == 'base' else '(modi): '
            clean_filename = extract_display_path(filename)
            f.write(f"> {prefix}{clean_filename}\n")
            
            for i in range(start_block_num, end_block_num + 1):
                if i < len(line_nums) and line_nums[i] is not None:
                    f.write(f">   {line_nums[i]}: {display_lines[i]}\n")
                    self.mark_noted_line(side, line_nums[i])
            f.write('>\n\n\n')
        
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
    
    def showEvent(self, event):
        """Override to ensure highlighting is applied when window becomes visible"""
        super().showEvent(event)
        # This is a safety net in case the tab becomes visible through a path
        # other than on_tab_changed (e.g., first show, or restoration from minimize)
        self.ensure_highlighting_applied()
    
    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        
        if key == Qt.Key.Key_H and modifiers & Qt.KeyboardModifier.AltModifier:
            self.toggle_diff_map()
            return
        
        if key == Qt.Key.Key_L and modifiers & Qt.KeyboardModifier.AltModifier:
            self.toggle_line_numbers()
            return
        
        if key == Qt.Key.Key_S and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.show_search_dialog()
            return
        
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
        elif key == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_diff_map_viewport()
    
    def refresh_colors(self):
        """Refresh all colors from the current palette"""
        self.apply_highlighting()
        self.diff_map.update()
    
    def run(self):
        self.show()
        sys.exit(self._app.exec())
