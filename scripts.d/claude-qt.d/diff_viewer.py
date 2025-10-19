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
                         QTextCharFormat, QTextBlockFormat)

from utils import extract_display_path
from search_dialogs import SearchDialog, SearchResultDialog
from ui_components import LineNumberArea, DiffMapWidget, SyncedPlainTextEdit
from help_dialog import HelpDialog
from commit_msg_dialog import CommitMsgDialog


class DiffViewer(QMainWindow):
    def __init__(self, base_file: str, modified_file: str, note_file: Optional[str] = None, 
                 commit_msg_file: Optional[str] = None):
        if QApplication.instance() is None:
            self._app = QApplication(sys.argv)
        else:
            self._app = QApplication.instance()
        
        super().__init__()
        
        self.base_file = base_file
        self.modified_file = modified_file
        self.note_file = note_file
        self.commit_msg_file = commit_msg_file
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
        
        self.current_region = 0
        self.current_region_highlight = None
        self._target_region = None
        
        self.setup_gui()
    
    def setup_gui(self):
        self.setWindowTitle(f"Diff Viewer: {self.base_file} vs {self.modified_file}")
        
        menubar = self.menuBar()
        help_menu = menubar.addMenu("Help")
        help_action = QAction("How to Use", self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
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
        base_layout.addWidget(self.base_line_area)
        base_layout.addWidget(self.base_text)
        base_container = QWidget()
        base_container.setLayout(base_layout)
        content_layout.addWidget(base_container, 1)
        
        self.diff_map = DiffMapWidget()
        self.diff_map.clicked.connect(self.on_diff_map_click)
        self.diff_map_visible = True
        content_layout.addWidget(self.diff_map)
        
        modified_layout = QHBoxLayout()
        modified_layout.setSpacing(0)
        self.modified_line_area = LineNumberArea()
        self.modified_line_area.setup_font()
        self.modified_text = SyncedPlainTextEdit()
        self.modified_line_area.set_text_widget(self.modified_text)
        self.modified_text.set_line_number_area(self.modified_line_area)
        modified_layout.addWidget(self.modified_line_area)
        modified_layout.addWidget(self.modified_text)
        modified_container = QWidget()
        modified_container.setLayout(modified_layout)
        content_layout.addWidget(modified_container, 1)
        
        self.line_numbers_visible = True
        
        self.v_scrollbar = QScrollBar(Qt.Orientation.Vertical)
        self.v_scrollbar.valueChanged.connect(self.on_v_scroll)
        content_layout.addWidget(self.v_scrollbar)
        
        main_layout.addLayout(content_layout, 1)
        
        self.h_scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        self.h_scrollbar.valueChanged.connect(self.on_h_scroll)
        main_layout.addWidget(self.h_scrollbar)
        
        status_layout = QHBoxLayout()
        self.region_label = QLabel("Region: 0 of 0")
        self.notes_label = QLabel("Notes: 0")
        
        self.commit_msg_button = QPushButton("Commit Message")
        self.commit_msg_button.clicked.connect(self.show_commit_msg)
        if not self.commit_msg_file:
            self.commit_msg_button.setEnabled(False)
        
        status_layout.addWidget(self.region_label)
        status_layout.addStretch()
        status_layout.addWidget(self.commit_msg_button)
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
        self.base_text.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, 'base'))
        self.modified_text.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, 'modified'))
        
        self.base_text.mouseDoubleClickEvent = lambda e: self.on_double_click(e, 'base')
        self.modified_text.mouseDoubleClickEvent = lambda e: self.on_double_click(e, 'modified')
        
        self.diff_map.wheelEvent = self.on_diff_map_wheel
        
        font_metrics = QFont("Courier", 12, QFont.Weight.Bold)
        fm = QFontMetrics(font_metrics)
        char_width = fm.horizontalAdvance('0')
        line_height = fm.height()
        
        total_width = (160 * char_width) + (90 * 2) + 30 + 20 + 40
        total_height = (50 * line_height) + 40 + 20 + 30 + 20
        self.resize(total_width, total_height)
    
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
        self.apply_highlighting()
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
        self.change_regions = []
        region_start = None
        region_tag = None
        
        for i, (base_line, modi_line) in enumerate(zip(self.base_line_objects,
                                                        self.modified_line_objects)):
            base_present = base_line.show_line_number()
            modi_present = modi_line.show_line_number()
            
            if base_present and modi_present:
                is_changed = self.line_has_changes(base_line) or self.line_has_changes(modi_line)
                current_tag = 'replace' if is_changed else None
            elif base_present and not modi_present:
                current_tag = 'delete'
            elif not base_present and modi_present:
                current_tag = 'insert'
            else:
                current_tag = None
            
            if current_tag is not None:
                if region_start is None:
                    region_start = i
                    region_tag = current_tag
                elif region_tag != current_tag:
                    self.change_regions.append((region_tag, region_start, i, 0, 0, 0, 0))
                    region_start = i
                    region_tag = current_tag
            else:
                if region_start is not None:
                    self.change_regions.append((region_tag, region_start, i, 0, 0, 0, 0))
                    region_start = None
                    region_tag = None
        
        if region_start is not None:
            self.change_regions.append((region_tag, region_start, 
                                       len(self.base_line_objects), 0, 0, 0, 0))
    
    def line_has_changes(self, line_obj):
        if not hasattr(line_obj, 'runs_'):
            return False
        return any(run.changed_ for run in line_obj.runs_)
    
    def populate_content(self):
        self.base_line_area.set_line_numbers(self.base_line_nums)
        self.modified_line_area.set_line_numbers(self.modified_line_nums)
        
        self.base_text.setPlainText('\n'.join(self.base_display))
        self.modified_text.setPlainText('\n'.join(self.modified_display))
        
        self.diff_map.set_change_regions(self.change_regions, len(self.base_display))
    
    def apply_highlighting(self):
        for i, (base_line, modi_line) in enumerate(zip(self.base_line_objects,
                                                        self.modified_line_objects)):
            if not base_line.show_line_number():
                self.highlight_line(self.base_text, i, QColor("darkgray"))
            else:
                self.apply_runs(self.base_text, i, base_line)
                if self.line_has_changes(base_line):
                    self.base_line_area.set_line_background(i, QColor(255, 238, 238))
            
            if not modi_line.show_line_number():
                self.highlight_line(self.modified_text, i, QColor("darkgray"))
            else:
                self.apply_runs(self.modified_text, i, modi_line)
                if self.line_has_changes(modi_line):
                    self.modified_line_area.set_line_background(i, QColor(238, 255, 238))
    
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
            
            if color_name == 'ADD':
                color = QColor("lightgreen")
            elif color_name == 'DELETE':
                color = QColor("red")
            elif color_name == 'INTRALINE':
                color = QColor("yellow")
            
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
            f.write(f"{prefix}{clean_filename}\n")
            f.write(f"  {line_nums[line_idx]}: {display_lines[line_idx]}\n\n")
        
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
    
    def select_commit_msg_result(self, line_idx):
        if not hasattr(self, 'commit_msg_dialog') or not self.commit_msg_dialog.isVisible():
            self.show_commit_msg()
        
        if hasattr(self, 'commit_msg_dialog'):
            self.commit_msg_dialog.select_line(line_idx)
    
    def show_help(self):
        help_dialog = HelpDialog(self)
        help_dialog.exec()
    
    def show_commit_msg(self):
        if not self.commit_msg_file:
            return
        
        if hasattr(self, 'commit_msg_dialog') and self.commit_msg_dialog.isVisible():
            self.commit_msg_dialog.raise_()
            self.commit_msg_dialog.activateWindow()
            return
        
        self.commit_msg_dialog = CommitMsgDialog(self.commit_msg_file, self, self)
        self.commit_msg_dialog.show()
    
    def show_context_menu(self, pos, side):
        menu = QMenu(self)
        text_widget = self.base_text if side == 'base' else self.modified_text
        
        has_selection = text_widget.textCursor().hasSelection()
        
        search_action = QAction("Search", self)
        search_action.setEnabled(has_selection)
        search_action.triggered.connect(lambda: self.search_selected_text(side))
        menu.addAction(search_action)
        
        menu.addSeparator()
        
        if has_selection and self.note_file:
            note_action = QAction("Take Note", self)
            note_action.triggered.connect(lambda: self.take_note(side))
            menu.addAction(note_action)
        else:
            note_action = QAction("Take Note (no selection)" if self.note_file else 
                           "Take Note (no file supplied)", self)
            note_action.setEnabled(False)
            menu.addAction(note_action)
        
        menu.exec(text_widget.mapToGlobal(pos))
    
    def show_search_dialog(self):
        dialog = SearchDialog(self, has_commit_msg=(self.commit_msg_file is not None))
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.search_text:
            results_dialog = SearchResultDialog(dialog.search_text, self, 
                                               dialog.case_sensitive,
                                               dialog.search_base,
                                               dialog.search_modi,
                                               dialog.search_desc)
            results_dialog.exec()
    
    def search_selected_text(self, side):
        text_widget = self.base_text if side == 'base' else self.modified_text
        cursor = text_widget.textCursor()
        
        if not cursor.hasSelection():
            return
        
        search_text = cursor.selectedText()
        
        dialog = SearchResultDialog(search_text, self, case_sensitive=False, 
                                   search_base=True, search_modi=True, 
                                   search_desc=True)
        dialog.exec()
    
    def select_search_result(self, side, line_idx):
        self.center_on_line(line_idx)
        
        if side == 'base':
            self.base_text.setFocus()
        else:
            self.modified_text.setFocus()
    
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
            f.write(f"{prefix}{clean_filename}\n")
            
            for i in range(start_block_num, end_block_num + 1):
                if i < len(line_nums) and line_nums[i] is not None:
                    f.write(f"  {line_nums[i]}: {display_lines[i]}\n")
                    self.mark_noted_line(side, line_nums[i])
            f.write('\n')
        
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
        else:
            self.modified_noted_lines.add(line_num)
            for i, num in enumerate(self.modified_line_nums):
                if num == line_num:
                    self.modified_line_area.mark_noted(i)
    
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
        total = len(self.change_regions)
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
    
    def run(self):
        self.show()
        sys.exit(self._app.exec())
