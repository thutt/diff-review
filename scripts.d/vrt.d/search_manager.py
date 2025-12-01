# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Search manager for diff_review

This module manages search functionality across all tabs:
- Search dialog display
- Search result navigation
- Two-tier highlighting (all matches + current match)
- Context menu integration
- Support for both diff viewers and commit message tabs
"""
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor
from PyQt6.QtCore import Qt

from search_dialogs import SearchDialog, SearchResultDialog
import color_palettes


class SearchManager:
    """Manages search functionality across all diff viewers and commit message tabs"""
    
    def __init__(self, tab_widget):
        """
        Initialize search manager
        
        Args:
            tab_widget: Reference to DiffViewerTabWidget
        """
        self.tab_widget = tab_widget
        self.search_result_dialogs = []  # Track search result dialogs
        
        # State for Find Next/Previous
        self.current_search_text = None
        self.current_search_case_sensitive = False
        self.current_search_use_regex = False
        self.current_search_results = []  # List of (tab_index, source_type, line_num, line_idx, char_pos)
        self.current_result_index = -1
    
    def show_search_dialog(self):
        """Show search dialog for current tab"""
        viewer = self.tab_widget.get_current_viewer()
        current_widget = self.tab_widget.tab_widget.currentWidget()
        
        dialog = SearchDialog(self.tab_widget)
        if dialog.exec() == dialog.DialogCode.Accepted and dialog.search_text:
            # Update current search state
            self.current_search_text = dialog.search_text
            self.current_search_case_sensitive = dialog.case_sensitive
            self.current_search_use_regex = dialog.use_regex
            
            # Pass tab_widget as parent so search results can navigate properly
            results_dialog = SearchResultDialog(
                search_text=dialog.search_text,
                parent=self.tab_widget,
                case_sensitive=dialog.case_sensitive,
                search_base=dialog.search_base,
                search_modi=dialog.search_modi,
                search_all_tabs=dialog.search_all_tabs,
                use_regex=dialog.use_regex
            )
            
            # Capture search results for Find Next/Previous
            self._capture_search_results(results_dialog)
            
            # Store reference to prevent garbage collection
            self.search_result_dialogs.append(results_dialog)
            # Connect destroyed signal to clean up reference
            results_dialog.destroyed.connect(lambda: self.search_result_dialogs.remove(results_dialog) 
                                            if results_dialog in self.search_result_dialogs else None)
            results_dialog.show()  # Show as modeless, not modal
            
            # Update status bar with match count
            self._update_status_bar()
    
    def search_selected_text(self, text_widget):
        """Search for selected text from any text widget"""
        cursor = text_widget.textCursor()
        if not cursor.hasSelection():
            return
        
        search_text = cursor.selectedText()
        
        # Update current search state
        self.current_search_text = search_text
        self.current_search_case_sensitive = False
        self.current_search_use_regex = False
        
        # Default to searching all tabs if multiple tabs are open
        search_all_tabs = self.tab_widget.tab_widget.count() > 1
        
        dialog = SearchResultDialog(search_text, self.tab_widget, case_sensitive=False,
                                   search_base=True, search_modi=True,
                                   search_all_tabs=search_all_tabs)
        
        # Capture search results for Find Next/Previous
        self._capture_search_results(dialog)
        
        # Store reference to prevent garbage collection
        self.search_result_dialogs.append(dialog)
        # Connect destroyed signal to clean up reference
        dialog.destroyed.connect(lambda: self.search_result_dialogs.remove(dialog) 
                                if dialog in self.search_result_dialogs else None)
        dialog.show()  # Show as modeless, not modal
        
        # Update status bar with match count
        self._update_status_bar()
    
    def _capture_search_results(self, results_dialog):
        """Capture search results from dialog for Find Next/Previous navigation"""
        self.current_search_results = []
        
        # Extract results from the dialog's result_list
        for i in range(results_dialog.result_list.count()):
            item = results_dialog.result_list.item(i)
            result_data = item.data(Qt.ItemDataRole.UserRole)
            if result_data:
                self.current_search_results.append(result_data)
        
        # Initialize to first result
        self.current_result_index = 0 if self.current_search_results else -1
    
    def _update_status_bar(self):
        """Update status bar with current search match count"""
        if self.current_search_results:
            total = len(self.current_search_results)
            current = self.current_result_index + 1 if self.current_result_index >= 0 else 0
            self.tab_widget.statusBar().showMessage(
                f"Search: {current} of {total} matches for '{self.current_search_text}'", 
                5000)  # 5 second message
        else:
            self.tab_widget.statusBar().showMessage(
                f"Search: No matches found for '{self.current_search_text}'", 
                3000)  # 3 second message
    
    def find_next(self):
        """Navigate to next search result"""
        if not self.current_search_results:
            self.tab_widget.statusBar().showMessage("No active search. Press Ctrl+F to search.", 2000)
            return
        
        # Move to next result (wrap around)
        self.current_result_index = (self.current_result_index + 1) % len(self.current_search_results)
        self._navigate_to_current_result()
        self._update_status_bar()
    
    def find_previous(self):
        """Navigate to previous search result"""
        if not self.current_search_results:
            self.tab_widget.statusBar().showMessage("No active search. Press Ctrl+F to search.", 2000)
            return
        
        # Move to previous result (wrap around)
        self.current_result_index = (self.current_result_index - 1) % len(self.current_search_results)
        self._navigate_to_current_result()
        self._update_status_bar()
    
    def _navigate_to_current_result(self):
        """Navigate to the current search result"""
        if self.current_result_index < 0 or self.current_result_index >= len(self.current_search_results):
            return
        
        tab_index, source_type, line_num, line_idx, char_pos = self.current_search_results[self.current_result_index]
        
        # Switch to the appropriate tab
        self.tab_widget.tab_widget.setCurrentIndex(tab_index)
        
        # Navigate within that tab, passing char_pos
        if source_type == 'commit_msg':
            self.select_commit_msg_result(line_idx, self.current_search_text, char_pos)
        elif source_type == 'review_notes':
            self.select_review_notes_result(line_idx, self.current_search_text, char_pos)
        else:
            self.select_search_result(source_type, line_idx, self.current_search_text, char_pos)
    
    def show_diff_context_menu(self, pos, text_widget, side):
        """Show context menu for diff viewer text widgets"""
        menu = QMenu(self.tab_widget)
        viewer = self.tab_widget.get_current_viewer()
        
        if not viewer:
            return
        
        has_selection = text_widget.textCursor().hasSelection()
        
        search_action = menu.addAction("Search")
        search_action.setEnabled(has_selection)
        search_action.triggered.connect(lambda: self.search_selected_text(text_widget))
        
        menu.addSeparator()
        
        if has_selection:
            note_action = menu.addAction("Take Note")
            note_action.triggered.connect(lambda: viewer.take_note(side))
        else:
            note_action = menu.addAction("Take Note (no selection)")
            note_action.setEnabled(False)
        
        # Add "Jump to Note" if this line has a note
        jump_action_func = self.tab_widget.note_mgr.show_jump_to_note_menu(pos, text_widget, side, viewer)
        if jump_action_func:
            menu.addSeparator()
            jump_action = menu.addAction("Jump to Note")
            jump_action.triggered.connect(jump_action_func)
        
        menu.addAction(search_action)
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
        viewer = self.tab_widget.get_current_viewer()
        if not viewer:
            return
        
        viewer.center_on_line(line_idx)
        
        # Select the appropriate text widget
        text_widget = viewer.base_text if side == 'base' else viewer.modified_text
        text_widget.setFocus()
        
        # If search_text is provided, implement two-tier highlighting
        if search_text:
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
    
    def select_review_notes_result(self, line_idx, search_text=None, char_pos=None):
        """Navigate to a line in the review notes tab and highlight search text
        
        Args:
            line_idx: Line index in the review notes
            search_text: Text to search for
            char_pos: Character position of the specific match to highlight bright (optional)
        """
        # Find the review notes tab
        review_notes_widget = None
        review_notes_tab_index = None
        
        if 'review_notes' in self.tab_widget.file_to_tab_index:
            review_notes_tab_index = self.tab_widget.file_to_tab_index['review_notes']
            if 0 <= review_notes_tab_index < self.tab_widget.tab_widget.count():
                widget = self.tab_widget.tab_widget.widget(review_notes_tab_index)
                if hasattr(widget, 'is_review_notes') and widget.is_review_notes:
                    review_notes_widget = widget
        
        if not review_notes_widget:
            # No review notes tab found
            return
        
        # Switch to the review notes tab
        self.tab_widget.tab_widget.setCurrentIndex(review_notes_tab_index)
        
        # Navigate to the line
        cursor = review_notes_widget.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        for _ in range(line_idx):
            cursor.movePosition(cursor.MoveOperation.Down)
        
        # If search_text provided, do two-tier highlighting
        if search_text:
            palette = color_palettes.get_current_palette()
            all_color = palette.get_color('search_highlight_all')
            current_color = palette.get_color('search_highlight_current')
            
            # Check if we need to do initial highlighting (search_text changed)
            if not hasattr(review_notes_widget, '_last_search_text') or review_notes_widget._last_search_text != search_text:
                # First time or new search - clear old and highlight all matches
                self.clear_review_notes_tab_highlights(review_notes_widget)
                
                # TIER 1: Highlight ALL matches (ONCE)
                self.highlight_all_matches_in_review_notes_tab(review_notes_widget, search_text, all_color)
                
                review_notes_widget._last_search_text = search_text
                review_notes_widget._last_bright_pos = None
            else:
                # Same search - just change bright highlight
                # Change previous bright match back to subtle
                if hasattr(review_notes_widget, '_last_bright_pos') and review_notes_widget._last_bright_pos:
                    last_line_idx, last_char_pos, last_len = review_notes_widget._last_bright_pos
                    block = review_notes_widget.document().findBlockByNumber(last_line_idx)
                    if block.isValid():
                        cursor = review_notes_widget.textCursor()
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
                review_notes_widget._last_bright_pos = (line_idx, pos, len(search_text))
                
                cursor.setPosition(block.position() + pos)
                review_notes_widget.setTextCursor(cursor)
            else:
                # Select whole line if not found
                cursor.movePosition(cursor.MoveOperation.StartOfBlock)
                cursor.movePosition(cursor.MoveOperation.EndOfBlock,
                                  cursor.MoveMode.KeepAnchor)
                review_notes_widget.setTextCursor(cursor)
        else:
            # No search text, just select the line
            cursor.movePosition(cursor.MoveOperation.StartOfBlock)
            cursor.movePosition(cursor.MoveOperation.EndOfBlock,
                              cursor.MoveMode.KeepAnchor)
            review_notes_widget.setTextCursor(cursor)
        
        review_notes_widget.centerCursor()
        review_notes_widget.setFocus()
    
    def highlight_all_matches_in_review_notes_tab(self, text_widget, search_text, highlight_color):
        """Highlight all matches in review notes tab"""
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
    
    def clear_review_notes_tab_highlights(self, text_widget):
        """Clear search highlights from review notes tab"""
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
        
        if 'commit_msg' in self.tab_widget.file_to_tab_index:
            commit_msg_tab_index = self.tab_widget.file_to_tab_index['commit_msg']
            if 0 <= commit_msg_tab_index < self.tab_widget.tab_widget.count():
                widget = self.tab_widget.tab_widget.widget(commit_msg_tab_index)
                if hasattr(widget, 'is_commit_msg') and widget.is_commit_msg:
                    commit_msg_widget = widget
        
        if not commit_msg_widget:
            # No commit message tab found
            return
        
        # Switch to the commit message tab
        self.tab_widget.tab_widget.setCurrentIndex(commit_msg_tab_index)
        
        # Navigate to the line
        cursor = commit_msg_widget.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        for _ in range(line_idx):
            cursor.movePosition(cursor.MoveOperation.Down)
        
        # If search_text provided, do two-tier highlighting
        if search_text:
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
