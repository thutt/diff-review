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
    for font management and state queries. Type identification is done via
    isinstance() rather than a type string.
    """

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
