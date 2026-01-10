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
from commit_msg_handler import CommitMessageTab


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
        self.current_bookmark = None  # Currently visited bookmark (tab_index, line_idx)
    
    def navigate_to_next_bookmark(self):
        """Navigate to next bookmark across all tabs"""
        if not self.global_bookmarks:
            return

        sorted_bookmarks = sorted(self.global_bookmarks.keys())

        if self.current_bookmark is None:
            # No current bookmark, go to first
            self.current_bookmark = sorted_bookmarks[0]
            self._jump_to_bookmark(*self.current_bookmark)
            return

        # Find index of current bookmark in sorted list
        try:
            current_idx = sorted_bookmarks.index(self.current_bookmark)
            # Go to next, wrapping around
            next_idx = (current_idx + 1) % len(sorted_bookmarks)
            self.current_bookmark = sorted_bookmarks[next_idx]
            self._jump_to_bookmark(*self.current_bookmark)
        except ValueError:
            # Current bookmark no longer exists, go to first
            self.current_bookmark = sorted_bookmarks[0]
            self._jump_to_bookmark(*self.current_bookmark)
    
    def navigate_to_prev_bookmark(self):
        """Navigate to previous bookmark across all tabs"""
        if not self.global_bookmarks:
            return

        sorted_bookmarks = sorted(self.global_bookmarks.keys())

        if self.current_bookmark is None:
            # No current bookmark, go to last
            self.current_bookmark = sorted_bookmarks[-1]
            self._jump_to_bookmark(*self.current_bookmark)
            return

        # Find index of current bookmark in sorted list
        try:
            current_idx = sorted_bookmarks.index(self.current_bookmark)
            # Go to previous, wrapping around
            prev_idx = (current_idx - 1) % len(sorted_bookmarks)
            self.current_bookmark = sorted_bookmarks[prev_idx]
            self._jump_to_bookmark(*self.current_bookmark)
        except ValueError:
            # Current bookmark no longer exists, go to last
            self.current_bookmark = sorted_bookmarks[-1]
            self._jump_to_bookmark(*self.current_bookmark)
    
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

    def remove_bookmark(self, tab_idx, line_idx):
        """Remove a bookmark and clear current_bookmark if it matches"""
        key = (tab_idx, line_idx)
        if key in self.global_bookmarks:
            del self.global_bookmarks[key]
            if self.current_bookmark == key:
                self.current_bookmark = None

    def add_bookmark(self, tab_idx, line_idx):
        """Add a bookmark"""
        key = (tab_idx, line_idx)
        self.global_bookmarks[key] = True
    
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

        # Clear current_bookmark if it was on the closed tab
        if self.current_bookmark is not None and self.current_bookmark[0] == closed_tab_index:
            self.current_bookmark = None

        # Update bookmark keys for tabs after this one (decrement tab_index)
        updated_bookmarks = {}
        for (tab_idx, line_idx), value in self.global_bookmarks.items():
            if tab_idx > closed_tab_index:
                updated_bookmarks[(tab_idx - 1, line_idx)] = value
            else:
                updated_bookmarks[(tab_idx, line_idx)] = value
        self.global_bookmarks = updated_bookmarks

        # Update current_bookmark index if it was on a tab after the closed one
        if self.current_bookmark is not None and self.current_bookmark[0] > closed_tab_index:
            self.current_bookmark = (self.current_bookmark[0] - 1, self.current_bookmark[1])
