#!/usr/bin/env python3
# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Search dialog classes for diff_review

This module contains the search input dialog and search results dialog
with unified search across base, modified, and commit message files.
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPlainTextEdit, QCheckBox, QPushButton, 
                              QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt


class SearchDialog(QDialog):
    """Dialog to input search text"""
    
    def __init__(self, parent=None, has_commit_msg=False):
        super().__init__(parent)
        self.search_text = None
        self.case_sensitive = False
        self.search_base = True
        self.search_modi = True
        self.search_desc = True
        self.has_commit_msg = has_commit_msg
        
        self.setWindowTitle("Search")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Search text input
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Search for:"))
        self.search_input = QPlainTextEdit()
        self.search_input.setMaximumHeight(60)
        self.search_input.setPlaceholderText("Enter search text...")
        input_layout.addWidget(self.search_input)
        layout.addLayout(input_layout)
        
        # Checkboxes row
        checkbox_layout = QHBoxLayout()
        
        # Case sensitivity checkbox
        self.case_checkbox = QCheckBox("Case sensitive")
        self.case_checkbox.setChecked(False)
        checkbox_layout.addWidget(self.case_checkbox)
        
        checkbox_layout.addStretch()
        
        # Base file checkbox
        self.base_checkbox = QCheckBox("Base")
        self.base_checkbox.setChecked(True)
        checkbox_layout.addWidget(self.base_checkbox)
        
        # Modified file checkbox
        self.modi_checkbox = QCheckBox("Modi")
        self.modi_checkbox.setChecked(True)
        checkbox_layout.addWidget(self.modi_checkbox)
        
        # Commit message checkbox (only if commit message file exists)
        if has_commit_msg:
            self.desc_checkbox = QCheckBox("Desc")
            self.desc_checkbox.setChecked(True)
            checkbox_layout.addWidget(self.desc_checkbox)
        
        layout.addLayout(checkbox_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.on_search)
        self.search_button.setDefault(True)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.search_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Focus on input field
        self.search_input.setFocus()
    
    def on_search(self):
        """Handle search button click"""
        text = self.search_input.toPlainText().strip()
        if text:
            self.search_text = text
            self.case_sensitive = self.case_checkbox.isChecked()
            self.search_base = self.base_checkbox.isChecked()
            self.search_modi = self.modi_checkbox.isChecked()
            if self.has_commit_msg:
                self.search_desc = self.desc_checkbox.isChecked()
            self.accept()


class SearchResultDialog(QDialog):
    """Dialog to show search results and allow selection"""
    
    def __init__(self, search_text, parent=None, case_sensitive=False, 
                 search_base=True, search_modi=True, search_desc=True):
        super().__init__(parent)
        self.search_text = search_text
        self.selected_result = None
        self.case_sensitive = case_sensitive
        self.search_base = search_base
        self.search_modi = search_modi
        self.search_desc = search_desc
        self.parent_viewer = parent
        
        self.setWindowTitle(f"Search Results for: {search_text}")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Checkboxes row
        checkbox_layout = QHBoxLayout()
        
        # Case sensitivity checkbox
        self.case_checkbox = QCheckBox("Case sensitive")
        self.case_checkbox.setChecked(case_sensitive)
        self.case_checkbox.stateChanged.connect(self.on_checkbox_changed)
        checkbox_layout.addWidget(self.case_checkbox)
        
        checkbox_layout.addStretch()
        
        # Base file checkbox
        self.base_checkbox = QCheckBox("Base")
        self.base_checkbox.setChecked(search_base)
        self.base_checkbox.stateChanged.connect(self.on_checkbox_changed)
        checkbox_layout.addWidget(self.base_checkbox)
        
        # Modified file checkbox
        self.modi_checkbox = QCheckBox("Modi")
        self.modi_checkbox.setChecked(search_modi)
        self.modi_checkbox.stateChanged.connect(self.on_checkbox_changed)
        checkbox_layout.addWidget(self.modi_checkbox)
        
        # Commit message checkbox (only if commit message file exists)
        if parent and parent.commit_msg_file:
            self.desc_checkbox = QCheckBox("Desc")
            self.desc_checkbox.setChecked(search_desc)
            self.desc_checkbox.stateChanged.connect(self.on_checkbox_changed)
            checkbox_layout.addWidget(self.desc_checkbox)
        
        layout.addLayout(checkbox_layout)
        
        # Info label
        self.info_label = QLabel()
        layout.addWidget(self.info_label)
        
        # Results list
        self.result_list = QListWidget()
        self.result_list.itemDoubleClicked.connect(self.on_select)
        layout.addWidget(self.result_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.on_select)
        self.select_button.setEnabled(False)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Enable/disable select button based on selection
        self.result_list.itemSelectionChanged.connect(self.on_selection_changed)
        
        # Initial search
        self.perform_search()
    
    def on_checkbox_changed(self, state):
        """Handle checkbox changes"""
        self.case_sensitive = self.case_checkbox.isChecked()
        self.search_base = self.base_checkbox.isChecked()
        self.search_modi = self.modi_checkbox.isChecked()
        if self.parent_viewer and self.parent_viewer.commit_msg_file:
            self.search_desc = self.desc_checkbox.isChecked()
        self.perform_search()
    
    def perform_search(self):
        """Perform the search and populate results"""
        # Clear existing results
        self.result_list.clear()
        
        if not self.parent_viewer:
            return
        
        # Perform search
        results = []
        search_text = self.search_text
        
        # Determine comparison function based on case sensitivity
        if self.case_sensitive:
            matches = lambda line: search_text in line
        else:
            search_lower = search_text.lower()
            matches = lambda line: search_lower in line.lower()
        
        # Search in base (only if checkbox is selected)
        if self.search_base:
            for i, (line_text, line_num) in enumerate(zip(self.parent_viewer.base_display, 
                                                           self.parent_viewer.base_line_nums)):
                if line_num is not None and matches(line_text):
                    results.append(('base', line_num, i, line_text))
        
        # Search in modified (only if checkbox is selected)
        if self.search_modi:
            for i, (line_text, line_num) in enumerate(zip(self.parent_viewer.modified_display, 
                                                           self.parent_viewer.modified_line_nums)):
                if line_num is not None and matches(line_text):
                    results.append(('modified', line_num, i, line_text))
        
        # Search in commit message  (only if checkbox is selected and commit message exists)
        if self.search_desc and self.parent_viewer.commit_msg_file:
            desc_lines = self.parent_viewer.get_commit_msg_lines()
            for line_num, line_text in enumerate(desc_lines):
                if matches(line_text):
                    results.append(('commit_msg', line_num + 1, line_num, line_text))
        
        # Update info label
        self.info_label.setText(f"Found {len(results)} matches:")
        
        # Populate results list
        for side, line_num, line_idx, line_text in results:
            if side == 'commit_msg':
                display_text = f"[DESC] Line {line_num}: {line_text}"
            else:
                display_text = f"[{side.upper()}] Line {line_num}: {line_text}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, (side, line_num, line_idx))
            self.result_list.addItem(item)
    
    def on_selection_changed(self):
        """Enable select button when an item is selected"""
        self.select_button.setEnabled(len(self.result_list.selectedItems()) > 0)
    
    def on_select(self):
        """Handle selection"""
        selected_items = self.result_list.selectedItems()
        if selected_items:
            item = selected_items[0]
            self.selected_result = item.data(Qt.ItemDataRole.UserRole)
            # Parent will handle navigation
            if self.parent_viewer:
                side, line_num, line_idx = self.selected_result
                if side == 'commit_msg':
                    # Navigate to commit message.
                    self.parent_viewer.select_commit_msg_result(line_idx)
                else:
                    # Navigate to source file
                    self.parent_viewer.select_search_result(side, line_idx)
