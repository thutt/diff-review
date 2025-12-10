# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Bookmark manager for diff_review

This module manages global bookmarks across all tabs including:
- Bookmark tracking (tab_index, line_idx) -> True
- Navigation to next/previous bookmarks
- Cross-tab bookmark jumping
"""
from tab_content_base import CommitMessageTab


class BookmarkManager:
    """Manages global bookmarks across all diff viewer tabs"""
    
    def __init__(self, tab_widget):
        """
        Initialize bookmark manager
        
        Args:
            tab_widget: Reference to DiffViewerTabWidget
        """
        self.tab_widget = tab_widget
        self.global_bookmarks = {}  # Maps (tab_index, line_idx) -> True
    
    def navigate_to_next_bookmark(self):
        """Navigate to next bookmark across all tabs"""
        if not self.global_bookmarks:
            return

        current_tab = self.tab_widget.tab_widget.currentIndex()

        # Get current line based on widget type
        current_widget = self.tab_widget.tab_widget.currentWidget()
        current_line = 0

        if isinstance(current_widget, CommitMessageTab):
            # Commit message tab
            current_line = current_widget.text_widget.textCursor().blockNumber()
        else:
            # Regular diff viewer
            viewer = self.tab_widget.get_current_viewer()
            if viewer:
                if viewer.base_text.hasFocus():
                    current_line = viewer.base_text.textCursor().blockNumber()
                elif viewer.modified_text.hasFocus():
                    current_line = viewer.modified_text.textCursor().blockNumber()

        # Sort all bookmarks
        sorted_bookmarks = sorted(self.global_bookmarks.keys())

        # Find next bookmark
        for tab_idx, line_idx in sorted_bookmarks:
            if tab_idx > current_tab or (tab_idx == current_tab and line_idx > current_line):
                self._jump_to_bookmark(tab_idx, line_idx)
                return

        # Wrap around to first bookmark
        if sorted_bookmarks:
            tab_idx, line_idx = sorted_bookmarks[0]
            self._jump_to_bookmark(tab_idx, line_idx)
    
    def navigate_to_prev_bookmark(self):
        """Navigate to previous bookmark across all tabs"""
        if not self.global_bookmarks:
            return

        current_tab = self.tab_widget.tab_widget.currentIndex()

        # Get current line based on widget type
        current_widget = self.tab_widget.tab_widget.currentWidget()
        current_line = 0

        if isinstance(current_widget, CommitMessageTab):
            # Commit message tab
            current_line = current_widget.text_widget.textCursor().blockNumber()
        else:
            # Regular diff viewer
            viewer = self.tab_widget.get_current_viewer()
            if viewer:
                if viewer.base_text.hasFocus():
                    current_line = viewer.base_text.textCursor().blockNumber()
                elif viewer.modified_text.hasFocus():
                    current_line = viewer.modified_text.textCursor().blockNumber()

        # Sort all bookmarks in reverse
        sorted_bookmarks = sorted(self.global_bookmarks.keys(), reverse=True)

        # Find previous bookmark
        for tab_idx, line_idx in sorted_bookmarks:
            if tab_idx < current_tab or (tab_idx == current_tab and line_idx < current_line):
                self._jump_to_bookmark(tab_idx, line_idx)
                return

        # Wrap around to last bookmark
        if sorted_bookmarks:
            tab_idx, line_idx = sorted_bookmarks[0]
            self._jump_to_bookmark(tab_idx, line_idx)
    
    def _jump_to_bookmark(self, tab_idx, line_idx):
        """Jump to a specific bookmark"""
        # Switch to tab
        self.tab_widget.tab_widget.setCurrentIndex(tab_idx)

        # Get the widget at this tab
        current_widget = self.tab_widget.tab_widget.widget(tab_idx)

        # Check if it's a commit message tab
        if isinstance(current_widget, CommitMessageTab):
            # It's a commit message - center on line
            self.tab_widget.commit_msg_mgr.center_on_line(current_widget.text_widget, line_idx)
            current_widget.text_widget.setFocus()
            return

        # Get viewer
        viewer = self.tab_widget.get_viewer_at_index(tab_idx)
        if not viewer:
            return

        # Center on line
        viewer.center_on_line(line_idx)

        # Set focus to base text (arbitrary choice)
        viewer.base_text.setFocus()
    
    def cleanup_tab_bookmarks(self, closed_tab_index):
        """
        Clean up bookmarks when a tab is closed and update indices
        
        Args:
            closed_tab_index: Index of the tab being closed
        """
        # Remove bookmarks for the closed tab
        keys_to_remove = [key for key in self.global_bookmarks if key[0] == closed_tab_index]
        for key in keys_to_remove:
            del self.global_bookmarks[key]
        
        # Update bookmark keys for tabs after this one (decrement tab_index)
        updated_bookmarks = {}
        for (tab_idx, line_idx), value in self.global_bookmarks.items():
            if tab_idx > closed_tab_index:
                updated_bookmarks[(tab_idx - 1, line_idx)] = value
            else:
                updated_bookmarks[(tab_idx, line_idx)] = value
        self.global_bookmarks = updated_bookmarks
