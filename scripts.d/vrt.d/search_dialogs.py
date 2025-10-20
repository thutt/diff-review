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
import re
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPlainTextEdit, QCheckBox, QPushButton, 
                              QListWidget, QListWidgetItem, QMessageBox, QStyledItemDelegate, QStyle)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QTextDocument, QPalette


class HTMLDelegate(QStyledItemDelegate):
    """Delegate to render HTML in QListWidget items"""
    
    def paint(self, painter, option, index):
        options = option
        self.initStyleOption(options, index)
        
        painter.save()
        
        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())
        
        # Handle selection highlighting
        if options.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(options.rect, options.palette.highlight())
        
        painter.translate(options.rect.left(), options.rect.top())
        clip = QRectF(0, 0, options.rect.width(), options.rect.height())
        doc.drawContents(painter, clip)
        
        painter.restore()
    
    def sizeHint(self, option, index):
        options = option
        self.initStyleOption(options, index)
        
        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())
        
        return doc.size().toSize()


class SearchDialog(QDialog):
    """Dialog to input search text"""
    
    def __init__(self, parent=None, has_commit_msg=False):
        super().__init__(parent)
        self.search_text = None
        self.case_sensitive = False
        self.search_base = True
        self.search_modi = True
        self.search_commit_msg = True
        self.search_all_tabs = True
        self.use_regex = False
        self.has_commit_msg = has_commit_msg
        
        # Check if parent is tab widget with multiple tabs
        self.has_multiple_tabs = False
        if hasattr(parent, 'tab_widget'):
            self.has_multiple_tabs = parent.tab_widget.count() > 1
        
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
        
        # Checkboxes row 1
        checkbox_layout1 = QHBoxLayout()
        
        # Case sensitivity checkbox
        self.case_checkbox = QCheckBox("Case sensitive")
        self.case_checkbox.setChecked(False)
        checkbox_layout1.addWidget(self.case_checkbox)
        
        # Regex checkbox
        self.regex_checkbox = QCheckBox("Regular expression")
        self.regex_checkbox.setChecked(False)
        checkbox_layout1.addWidget(self.regex_checkbox)
        
        checkbox_layout1.addStretch()
        
        layout.addLayout(checkbox_layout1)
        
        # Checkboxes row 2 (only if multiple tabs)
        if self.has_multiple_tabs:
            checkbox_layout2 = QHBoxLayout()
            self.all_tabs_checkbox = QCheckBox("Search all tabs")
            self.all_tabs_checkbox.setChecked(True)
            checkbox_layout2.addWidget(self.all_tabs_checkbox)
            checkbox_layout2.addStretch()
            layout.addLayout(checkbox_layout2)
        
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
            self.use_regex = self.regex_checkbox.isChecked()
            
            # Validate regex if enabled
            if self.use_regex:
                try:
                    flags = 0 if self.case_sensitive else re.IGNORECASE
                    re.compile(text, flags)
                except re.error as e:
                    QMessageBox.warning(self, "Invalid Regular Expression", 
                                      f"The regular expression is invalid:\n{e}")
                    return
            
            # Always search all sources
            self.search_base = True
            self.search_modi = True
            self.search_commit_msg = True
            # Get search_all_tabs state from checkbox if it exists
            if self.has_multiple_tabs and hasattr(self, 'all_tabs_checkbox'):
                self.search_all_tabs = self.all_tabs_checkbox.isChecked()
            self.accept()


class SearchResultDialog(QDialog):
    """Dialog to show search results and allow selection"""
    
    def __init__(self, search_text, parent, case_sensitive=False, 
                 search_base=True, search_modi=True, search_commit_msg=True,
                 search_all_tabs=False, use_regex=False):
        super().__init__(parent)
        self.search_text = search_text
        self.selected_result = None
        self.case_sensitive = case_sensitive
        self.search_base = search_base
        self.search_modi = search_modi
        self.search_commit_msg = search_commit_msg
        self.search_all_tabs = search_all_tabs
        self.use_regex = use_regex
        self.parent_tab_widget = parent
 
        # Check if we have multiple tabs
        self.has_multiple_tabs = False
        if hasattr(parent, 'tab_widget'):
            self.has_multiple_tabs = parent.tab_widget.count() > 1
        
        self.setWindowTitle(f"Search Results for: {search_text}")
        self.setMinimumSize(700, 400)
        
        layout = QVBoxLayout(self)
        
        # Search text input (editable)
        search_input_layout = QHBoxLayout()
        search_input_layout.addWidget(QLabel("Search:"))
        self.search_input = QPlainTextEdit()
        self.search_input.setPlainText(search_text)
        self.search_input.setMaximumHeight(60)
        search_input_layout.addWidget(self.search_input)
        
        # Re-search button
        self.research_button = QPushButton("Search")
        self.research_button.clicked.connect(self.on_research)
        search_input_layout.addWidget(self.research_button)
        
        layout.addLayout(search_input_layout)
        
        # Checkboxes row 1
        checkbox_layout1 = QHBoxLayout()
        
        # Case sensitivity checkbox
        self.case_checkbox = QCheckBox("Case sensitive")
        self.case_checkbox.setChecked(case_sensitive)
        self.case_checkbox.stateChanged.connect(self.on_case_changed)
        checkbox_layout1.addWidget(self.case_checkbox)
        
        # Regex checkbox
        self.regex_checkbox = QCheckBox("Regular expression")
        self.regex_checkbox.setChecked(use_regex)
        self.regex_checkbox.stateChanged.connect(self.on_regex_changed)
        checkbox_layout1.addWidget(self.regex_checkbox)
        
        checkbox_layout1.addStretch()
        
        layout.addLayout(checkbox_layout1)
        
        # Checkboxes row 2 (only show if multiple tabs)
        if self.has_multiple_tabs:
            checkbox_layout2 = QHBoxLayout()
            self.all_tabs_checkbox = QCheckBox("Search all tabs")
            self.all_tabs_checkbox.setChecked(self.search_all_tabs)
            self.all_tabs_checkbox.stateChanged.connect(self.on_all_tabs_changed)
            checkbox_layout2.addWidget(self.all_tabs_checkbox)
            checkbox_layout2.addStretch()
            layout.addLayout(checkbox_layout2)
        
        # Info label
        self.info_label = QLabel()
        layout.addWidget(self.info_label)
        
        # Results list
        self.result_list = QListWidget()
        self.result_list.setTextElideMode(Qt.TextElideMode.ElideNone)  # Don't truncate text
        self.result_list.setItemDelegate(HTMLDelegate())  # Enable HTML rendering
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
    
    def on_case_changed(self, state):
        """Handle 'case sensitive' checkbox change"""
        self.case_sensitive = self.case_checkbox.isChecked()
        self.perform_search()
    
    def on_regex_changed(self, state):
        """Handle 'regular expression' checkbox change"""
        self.use_regex = self.regex_checkbox.isChecked()
        self.perform_search()
    
    def on_all_tabs_changed(self, state):
        """Handle 'search all tabs' checkbox change"""
        self.search_all_tabs = self.all_tabs_checkbox.isChecked()
        self.perform_search()
    
    def on_research(self):
        """Handle re-search button click with new search text"""
        new_search_text = self.search_input.toPlainText().strip()
        if not new_search_text:
            return
        
        # Validate regex if enabled
        if self.use_regex:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                re.compile(new_search_text, flags)
            except re.error as e:
                QMessageBox.warning(self, "Invalid Regular Expression", 
                                  f"The regular expression is invalid:\n{e}")
                return
        
        self.search_text = new_search_text
        self.setWindowTitle(f"Search Results for: {self.search_text}")
        self.perform_search()
    
    def perform_search(self):
        """Perform the search and populate results"""
        self.result_list.clear()
        results = []
        
        # Determine comparison function based on case sensitivity and regex
        if self.use_regex:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                pattern = re.compile(self.search_text, flags)
                matches = lambda line: pattern.search(line) is not None
            except re.error as e:
                self.info_label.setText(f"Invalid regular expression: {e}")
                return
        else:
            if self.case_sensitive:
                matches = lambda line: self.search_text in line
            else:
                search_lower = self.search_text.lower()
                matches = lambda line: search_lower in line.lower()
        
        if self.search_all_tabs:
            # Search all tabs
            for tab_index in range(self.parent_tab_widget.tab_widget.count()):
                tab_widget = self.parent_tab_widget.tab_widget.widget(tab_index)
                tab_title = self.parent_tab_widget.tab_widget.tabText(tab_index)
                
                # Check if it's a commit message tab
                if hasattr(tab_widget, 'is_commit_msg') and tab_widget.is_commit_msg:
                    if self.search_commit_msg:
                        text = tab_widget.toPlainText()
                        lines = text.split('\n')
                        for line_num, line_text in enumerate(lines):
                            if matches(line_text):
                                results.append((tab_index, tab_title, 'commit_msg', 
                                              line_num + 1, line_num, line_text))
                # Otherwise it's a diff viewer
                elif hasattr(tab_widget, 'diff_viewer'):
                    viewer = tab_widget.diff_viewer
                    
                    # Search in base
                    if self.search_base:
                        for i, (line_text, line_num) in enumerate(zip(viewer.base_display, 
                                                                       viewer.base_line_nums)):
                            if line_num is not None and matches(line_text):
                                results.append((tab_index, tab_title, 'base', 
                                              line_num, i, line_text))
                    
                    # Search in modified
                    if self.search_modi:
                        for i, (line_text, line_num) in enumerate(zip(viewer.modified_display, 
                                                                       viewer.modified_line_nums)):
                            if line_num is not None and matches(line_text):
                                results.append((tab_index, tab_title, 'modified', 
                                              line_num, i, line_text))
                    
                    # Don't search viewer's commit message file when searching all tabs
                    # The commit message tab is separate and will be searched in its own iteration
        else:
            # Search current tab only
            current_widget = self.parent_tab_widget.tab_widget.currentWidget()
            tab_index = self.parent_tab_widget.tab_widget.currentIndex()
            tab_title = self.parent_tab_widget.tab_widget.tabText(tab_index)
            
            # Check if it's a commit message tab
            if hasattr(current_widget, 'is_commit_msg') and current_widget.is_commit_msg:
                # Only search commit message if this IS the commit message tab
                if self.search_commit_msg:
                    text = current_widget.toPlainText()
                    lines = text.split('\n')
                    for line_num, line_text in enumerate(lines):
                        if matches(line_text):
                            results.append((tab_index, tab_title, 'commit_msg', 
                                          line_num + 1, line_num, line_text))
            # Otherwise it's a diff viewer
            elif hasattr(current_widget, 'diff_viewer'):
                viewer = current_widget.diff_viewer
                
                # Search in base
                if self.search_base:
                    for i, (line_text, line_num) in enumerate(zip(viewer.base_display, 
                                                                   viewer.base_line_nums)):
                        if line_num is not None and matches(line_text):
                            results.append((tab_index, tab_title, 'base', 
                                          line_num, i, line_text))
                
                # Search in modified
                if self.search_modi:
                    for i, (line_text, line_num) in enumerate(zip(viewer.modified_display, 
                                                                   viewer.modified_line_nums)):
                        if line_num is not None and matches(line_text):
                            results.append((tab_index, tab_title, 'modified', 
                                          line_num, i, line_text))
                
                # Don't search commit message when searching current tab only
        
        # Update info label
        tab_info = " across all tabs" if self.search_all_tabs else " in current tab"
        regex_info = " (regex)" if self.use_regex else ""
        self.info_label.setText(f"Found {len(results)} matches{tab_info}{regex_info}:")
        
        # Populate results list
        for tab_index, tab_title, source_type, line_num, line_idx, line_text in results:
            if source_type == 'commit_msg':
                if self.search_all_tabs:
                    display_text = f"[{tab_title}] [COMMIT MSG] Line {line_num}: {line_text}"
                else:
                    display_text = f"[COMMIT MSG] Line {line_num}: {line_text}"
            else:
                if self.search_all_tabs:
                    display_text = f"[{tab_title}] [{source_type.upper()}] Line {line_num}: {line_text}"
                else:
                    display_text = f"[{source_type.upper()}] Line {line_num}: {line_text}"
            
            item = QListWidgetItem(display_text)
            
            # Highlight matched text with yellow background
            # Find the position of the actual line content after the prefix
            prefix_end = display_text.rfind(': ') + 2
            line_content = display_text[prefix_end:]
            prefix = display_text[:prefix_end]
            
            # Escape prefix HTML
            prefix_escaped = prefix.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            # Find and highlight all matches in the line content
            highlighted = False
            if self.use_regex:
                try:
                    flags = 0 if self.case_sensitive else re.IGNORECASE
                    pattern = re.compile(self.search_text, flags)
                    
                    # Find all matches
                    html_parts = []
                    last_end = 0
                    for match in pattern.finditer(line_content):
                        # Add text before match
                        before = line_content[last_end:match.start()]
                        before_escaped = before.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        html_parts.append(before_escaped)
                        
                        # Add highlighted match
                        matched = line_content[match.start():match.end()]
                        matched_escaped = matched.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        html_parts.append(f'<span style="background-color: #ffff00; color: #000000; font-weight: bold;">{matched_escaped}</span>')
                        
                        last_end = match.end()
                    
                    # Add remaining text after last match
                    if last_end < len(line_content):
                        after = line_content[last_end:]
                        after_escaped = after.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        html_parts.append(after_escaped)
                    
                    if html_parts:
                        html_text = prefix_escaped + ''.join(html_parts)
                        item.setData(Qt.ItemDataRole.DisplayRole, html_text)
                        highlighted = True
                except:
                    pass  # If highlighting fails, just show plain text
            
            if not highlighted and not self.use_regex:
                # Simple string search - find all occurrences
                if self.case_sensitive:
                    search_for = self.search_text
                else:
                    search_for = self.search_text.lower()
                    line_content_lower = line_content.lower()
                
                html_parts = []
                last_end = 0
                pos = 0
                
                while True:
                    if self.case_sensitive:
                        pos = line_content.find(search_for, last_end)
                    else:
                        pos = line_content_lower.find(search_for, last_end)
                    
                    if pos < 0:
                        break
                    
                    # Add text before match
                    before = line_content[last_end:pos]
                    before_escaped = before.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    html_parts.append(before_escaped)
                    
                    # Add highlighted match
                    matched = line_content[pos:pos + len(self.search_text)]
                    matched_escaped = matched.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    html_parts.append(f'<span style="background-color: #ffff00; color: #000000; font-weight: bold;">{matched_escaped}</span>')
                    
                    last_end = pos + len(self.search_text)
                
                # Add remaining text after last match
                if last_end < len(line_content):
                    after = line_content[last_end:]
                    after_escaped = after.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    html_parts.append(after_escaped)
                
                if html_parts:
                    html_text = prefix_escaped + ''.join(html_parts)
                    item.setData(Qt.ItemDataRole.DisplayRole, html_text)
                    highlighted = True
            
            # Store the metadata for navigation
            item.setData(Qt.ItemDataRole.UserRole, 
                        (tab_index, source_type, line_num, line_idx))
            self.result_list.addItem(item)
    
    def on_selection_changed(self):
        """Enable select button when an item is selected"""
        self.select_button.setEnabled(len(self.result_list.selectedItems()) > 0)
    
    def on_select(self):
        """Handle selection"""
        selected_items = self.result_list.selectedItems()
        if selected_items:
            item = selected_items[0]
            tab_index, source_type, line_num, line_idx = item.data(Qt.ItemDataRole.UserRole)
            
            # Switch to the appropriate tab
            self.parent_tab_widget.tab_widget.setCurrentIndex(tab_index)
            
            # Navigate within that tab
            if source_type == 'commit_msg':
                self.parent_tab_widget.select_commit_msg_result(line_idx)
            else:
                self.parent_tab_widget.select_search_result(source_type, line_idx)
            
            # Don't close the dialog - let user select more results or manually close
