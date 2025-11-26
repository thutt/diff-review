# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
View state manager for diff_review

This module manages global view state across all tabs including:
- Diff map visibility
- Line numbers visibility
- Tab character visibility
- Trailing whitespace visibility
- Intraline changes visibility
"""


class ViewStateManager:
    """Manages global view state for all diff viewers"""
    
    def __init__(self, tab_widget,
                 show_diff_map,
                 show_line_numbers,
                 ignore_tab,
                 ignore_trailing_ws,
                 ignore_intraline):
        """
        Initialize view state manager
        
        Args:
            tab_widget: Reference to DiffViewerTabWidget
            show_diff_map: Initial diff map visibility
            show_line_numbers: Initial line numbers visibility
            ignore_tab: Initial tab ignore state
            ignore_trailing_ws: Initial trailing whitespace ignore state
            ignore_intraline: Initial intraline ignore state
        """
        self.tab_widget = tab_widget
        self.diff_map_visible = show_diff_map
        self.line_numbers_visible = show_line_numbers
        self.ignore_tab = ignore_tab
        self.ignore_trailing_ws = ignore_trailing_ws
        self.ignore_intraline = ignore_intraline
    
    def toggle_diff_map(self):
        """Toggle diff map in all viewers"""
        self.diff_map_visible = not self.diff_map_visible
        viewers = self.tab_widget.get_all_viewers()
        for viewer in viewers:
            if viewer.diff_map_visible != self.diff_map_visible:
                viewer.toggle_diff_map()
        
        # Update checkbox state
        self.tab_widget.show_diff_map_action.setChecked(self.diff_map_visible)
    
    def toggle_line_numbers(self):
        """Toggle line numbers in all viewers"""
        self.line_numbers_visible = not self.line_numbers_visible
        viewers = self.tab_widget.get_all_viewers()
        for viewer in viewers:
            if viewer.line_numbers_visible != self.line_numbers_visible:
                viewer.toggle_line_numbers()
        
        # Update checkbox state
        self.tab_widget.show_line_numbers_action.setChecked(self.line_numbers_visible)
    
    def toggle_tab_visibility(self):
        """Toggle tab character visibility in all viewers"""
        self.ignore_tab = not self.tab_widget.show_tab_action.isChecked()
        # Update current viewer immediately
        viewer = self.tab_widget.get_current_viewer()
        if viewer:
            viewer.ignore_tab = self.ignore_tab
            viewer.restart_highlighting()
        # Mark all other viewers as needing update
        for v in self.tab_widget.get_all_viewers():
            if v != viewer:
                v.ignore_tab = self.ignore_tab
                v._needs_highlighting_update = True
    
    def toggle_trailing_ws_visibility(self):
        """Toggle trailing whitespace visibility in all viewers"""
        self.ignore_trailing_ws = not self.tab_widget.show_trailing_ws_action.isChecked()
        # Update current viewer immediately
        viewer = self.tab_widget.get_current_viewer()
        if viewer:
            viewer.ignore_trailing_ws = self.ignore_trailing_ws
            viewer.restart_highlighting()
        # Mark all other viewers as needing update
        for v in self.tab_widget.get_all_viewers():
            if v != viewer:
                v.ignore_trailing_ws = self.ignore_trailing_ws
                v._needs_highlighting_update = True
    
    def toggle_intraline_visibility(self):
        """Toggle intraline changes visibility in all viewers"""
        self.ignore_intraline = not self.tab_widget.show_intraline_action.isChecked()
        # Update current viewer immediately
        viewer = self.tab_widget.get_current_viewer()
        if viewer:
            viewer.ignore_intraline = self.ignore_intraline
            viewer.restart_highlighting()
        # Mark all other viewers as needing update
        for v in self.tab_widget.get_all_viewers():
            if v != viewer:
                v.ignore_intraline = self.ignore_intraline
                v._needs_highlighting_update = True
    
    def apply_to_viewer(self, viewer):
        """
        Apply current view state to a newly created viewer
        
        Args:
            viewer: DiffViewer instance to apply state to
        """
        # Apply global view state to new viewer
        if self.diff_map_visible != viewer.diff_map_visible:
            viewer.toggle_diff_map()
        if self.line_numbers_visible != viewer.line_numbers_visible:
            viewer.toggle_line_numbers()
        
        # Apply global whitespace ignore settings
        viewer.ignore_tab = self.ignore_tab
        viewer.ignore_trailing_ws = self.ignore_trailing_ws
        viewer.ignore_intraline = self.ignore_intraline
