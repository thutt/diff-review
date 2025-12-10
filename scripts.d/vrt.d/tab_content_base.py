# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Tab content base classes for diff_review

This module defines the abstract base class for all tab content types.
Individual tab implementations are in their respective manager modules:
- CommitMessageTab: in commit_msg_handler.py
- ReviewNotesTab/ReviewNotesTabBase: in note_manager.py
- DiffViewer: in diff_viewer.py
"""


class TabContentBase:
    """
    Abstract base class for all tab content types.

    All tab widgets should inherit from this to provide a consistent interface
    for font management, type identification, and state queries.
    """

    def get_tab_type(self):
        """
        Return the type identifier for this tab.

        Returns:
            str: One of 'commit_msg', 'review_notes', 'diff_viewer'
        """
        raise NotImplementedError("Subclasses must implement get_tab_type()")

    def increase_font_size(self):
        """Increase font size - default implementation does nothing"""
        pass

    def decrease_font_size(self):
        """Decrease font size - default implementation does nothing"""
        pass

    def has_unsaved_changes(self):
        """
        Check if tab has unsaved changes.

        Returns:
            bool: True if there are unsaved changes, False otherwise
        """
        return False
