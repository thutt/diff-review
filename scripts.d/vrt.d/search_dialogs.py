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
        
        # Check if item is selected
        is_selected = options.state & QStyle.StateFlag.State_Selected
        
        # Get the HTML text
        html_text = options.text
        
        # If selected, replace the colored filename portion with white text
        if is_selected and '<span style="color:' in html_text:
            # Replace the color in the span with white
            import re
            html_text = re.sub(r'<span style="color: #[0-9a-fA-F]{6};">', 
                             '<span style="color: #ffffff;">', html_text)
        
        doc = QTextDocument()
        doc.setHtml(html_text)
        doc.setTextWidth(options.rect.width())
        
        # Handle selection highlighting
        if is_selected:
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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_text = None
        self.case_sensitive = False
        self.search_base = True
        self.search_modi = True
        self.search_all_tabs = True
        self.use_regex = False
        
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
        
        # Regex documentation link
        regex_link = QLabel('<a href="https://docs.python.org/3/library/re.html">Python regex docs</a>')
        regex_link.setOpenExternalLinks(True)
        regex_link.setToolTip("Open Python re module documentation")
        checkbox_layout1.addWidget(regex_link)
        
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
        text = self.search_input.toPlainText()
        if text:  # Allow whitespace-only searches
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
            # Get search_all_tabs state from checkbox if it exists
            if self.has_multiple_tabs and hasattr(self, 'all_tabs_checkbox'):
                self.search_all_tabs = self.all_tabs_checkbox.isChecked()
            self.accept()


class SearchResultDialog(QDialog):
    """Dialog to show search results and allow selection"""
    
    def __init__(self, search_text, parent, case_sensitive=False, 
                 search_base=True, search_modi=True,
                 search_all_tabs=False, use_regex=False):
        super().__init__(parent)
        self.search_text = search_text
        self.selected_result = None
        self.case_sensitive = case_sensitive
        self.search_base = search_base
        self.search_modi = search_modi
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
        
        # Regex documentation link
        regex_link = QLabel('<a href="https://docs.python.org/3/library/re.html">Python regex docs</a>')
        regex_link.setOpenExternalLinks(True)
        regex_link.setToolTip("Open Python re module documentation")
        checkbox_layout1.addWidget(regex_link)
        
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
        
        self.prev_button = QPushButton("Previous")
        self.prev_button.clicked.connect(self.on_previous)
        self.prev_button.setEnabled(False)
        
        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.on_next)
        self.next_button.setEnabled(False)
        
        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.on_select)
        self.select_button.setEnabled(False)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.prev_button)
        button_layout.addWidget(self.next_button)
        button_layout.addStretch()
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Enable/disable select button based on selection
        self.result_list.itemSelectionChanged.connect(self.on_selection_changed)
        
        # Initial search
        self.perform_search()
        
        # If there are results, select the first one
        if self.result_list.count() > 0:
            self.result_list.setCurrentRow(0)
    
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
        new_search_text = self.search_input.toPlainText()
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
    
    def find_all_matches_in_line(self, line_text):
        """Find all match positions in a line. Returns list of (start_pos, match_text) tuples."""
        matches = []
        
        if self.use_regex:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                pattern = re.compile(self.search_text, flags)
                for match in pattern.finditer(line_text):
                    matches.append((match.start(), match.group()))
            except re.error:
                pass
        else:
            search_text = self.search_text if self.case_sensitive else self.search_text.lower()
            search_in = line_text if self.case_sensitive else line_text.lower()
            
            pos = 0
            while True:
                found_pos = search_in.find(search_text, pos)
                if found_pos < 0:
                    break
                # Get the actual matched text (with original case)
                matched_text = line_text[found_pos:found_pos + len(self.search_text)]
                matches.append((found_pos, matched_text))
                pos = found_pos + len(self.search_text)
        
        return matches
    
    def perform_search(self):
        """Perform the search and populate results - creates one result per match"""
        self.result_list.clear()
        results = []
        
        if self.search_all_tabs:
            # Search all tabs
            for tab_index in range(self.parent_tab_widget.tab_widget.count()):
                tab_widget = self.parent_tab_widget.tab_widget.widget(tab_index)
                tab_title = self.parent_tab_widget.tab_widget.tabText(tab_index)
                
                # Ask the tab to search itself
                tab_results = tab_widget.search_content(
                    self.search_text,
                    self.case_sensitive,
                    self.use_regex,
                    self.search_base,
                    self.search_modi
                )
                
                # Add tab_index and tab_title to each result
                for side, display_line_num, line_idx, line_text, char_pos in tab_results:
                    results.append((tab_index, tab_title, side, display_line_num, line_idx, line_text, char_pos))
        else:
            # Search current tab only
            current_widget = self.parent_tab_widget.tab_widget.currentWidget()
            tab_index = self.parent_tab_widget.tab_widget.currentIndex()
            tab_title = self.parent_tab_widget.tab_widget.tabText(tab_index)
            
            # Ask the tab to search itself
            tab_results = current_widget.search_content(
                self.search_text,
                self.case_sensitive,
                self.use_regex,
                self.search_base,
                self.search_modi
            )
            
            # Add tab_index and tab_title to each result
            for side, display_line_num, line_idx, line_text, char_pos in tab_results:
                results.append((tab_index, tab_title, side, display_line_num, line_idx, line_text, char_pos))
        
        # Update info label
        tab_info = " across all tabs" if self.search_all_tabs else " in current tab"
        regex_info = " (regex)" if self.use_regex else ""
        self.info_label.setText(f"Found {len(results)} matches{tab_info}{regex_info}:")
        
        # Populate results list
        for tab_index, tab_title, source_type, line_num, line_idx, line_text, char_pos in results:
            # Determine color based on source type
            if source_type == 'base':
                color = '#2a70c9'  # Darker blue
            elif source_type == 'modified':
                color = '#4e9a06'  # Darker green
            elif source_type == 'review_notes':
                color = '#6a0dad'  # Purple for review notes
            else:  # commit_msg
                color = '#8b4513'  # Saddle brown
            
            # Format location prefix
            if self.search_all_tabs:
                location_prefix = f'<span style="color: {color};">[{tab_title}:{line_num}]</span>'
            else:
                location_prefix = f'<span style="color: {color};">[{tab_title}:{line_num}]</span>'
            
            item = QListWidgetItem()
            
            # Build display with highlighted search match
            prefix = f'{location_prefix}: '
            
            # Highlight the specific match at char_pos
            before = line_text[:char_pos]
            match = line_text[char_pos:char_pos + len(self.search_text)]
            after = line_text[char_pos + len(self.search_text):]
            
            # Escape HTML
            before_escaped = before.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace(' ', '&nbsp;')
            match_escaped = match.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace(' ', '&nbsp;')
            after_escaped = after.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace(' ', '&nbsp;')
            
            html_text = (prefix + before_escaped + 
                        f'<span style="background-color: #ffff00; color: #000000; font-weight: bold;">{match_escaped}</span>' +
                        after_escaped)
            
            item.setData(Qt.ItemDataRole.DisplayRole, html_text)
            
            # Store metadata including char_pos for navigation
            item.setData(Qt.ItemDataRole.UserRole, 
                        (tab_index, source_type, line_num, line_idx, char_pos))
            self.result_list.addItem(item)
        
        # Update button states
        if self.result_list.count() == 0:
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
    
    def on_selection_changed(self):
        """Enable select button when an item is selected"""
        has_selection = len(self.result_list.selectedItems()) > 0
        self.select_button.setEnabled(has_selection)
        
        # Update Next/Prev button states
        if self.result_list.count() == 0:
            self.prev_button.setEnabled(False)
            self.next_button.setEnabled(False)
        else:
            current_row = self.result_list.currentRow()
            self.prev_button.setEnabled(current_row > 0)
            self.next_button.setEnabled(current_row < self.result_list.count() - 1)
    
    def on_previous(self):
        """Navigate to previous result"""
        current_row = self.result_list.currentRow()
        if current_row > 0:
            self.result_list.setCurrentRow(current_row - 1)
            self.on_select()  # Navigate to the result
    
    def on_next(self):
        """Navigate to next result"""
        current_row = self.result_list.currentRow()
        if current_row < self.result_list.count() - 1:
            self.result_list.setCurrentRow(current_row + 1)
            self.on_select()  # Navigate to the result
    
    def on_select(self):
        """Handle selection"""
        selected_items = self.result_list.selectedItems()
        if selected_items:
            item = selected_items[0]
            tab_index, source_type, line_num, line_idx, char_pos = item.data(Qt.ItemDataRole.UserRole)
            
            # Switch to the appropriate tab
            self.parent_tab_widget.tab_widget.setCurrentIndex(tab_index)
            
            # Navigate within that tab, passing char_pos
            if source_type == 'commit_msg':
                self.parent_tab_widget.select_commit_msg_result(line_idx, self.search_text, char_pos)
            elif source_type == 'review_notes':
                self.parent_tab_widget.select_review_notes_result(line_idx, self.search_text, char_pos)
            else:
                self.parent_tab_widget.select_search_result(source_type, line_idx, self.search_text, char_pos)
            
            # Don't close the dialog - let user select more results or manually close
