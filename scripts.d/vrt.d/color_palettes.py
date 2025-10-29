#!/usr/bin/env python3
# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Color palette definitions for diff_review

This module contains color scheme definitions for different viewing preferences.
Each palette defines colors for various diff elements including added, deleted,
changed lines, and UI indicators.
"""

from PyQt6.QtGui import QColor


class ColorPalette:
    """Base class for color palettes"""
    def __init__(self, name, colors):
        self.name = name
        self.colors = colors
    
    def get_color(self, color_type):
        """Get QColor for a specific type, returns None if color should not be applied"""
        if color_type in self.colors:
            color_value = self.colors[color_type]
            if color_value is None:
                return None
            if isinstance(color_value, str):
                return QColor(color_value)
            elif isinstance(color_value, tuple):
                return QColor(*color_value)
            elif isinstance(color_value, QColor):
                return color_value
        return QColor("white")


# Standard color palette - uses traditional red/green
STANDARD_PALETTE = ColorPalette('Standard', {
    # Line backgrounds - more visible
    'placeholder': QColor("darkgray"),
    'base_changed_bg': QColor(255, 220, 220),      # Darker pink/red for better visibility
    'modi_changed_bg': QColor(220, 255, 220),      # Darker green for better visibility
    
    # Run colors (for text highlighting)
    'add_run': QColor("lightgreen"),
    'delete_run': QColor("red"),
    'intraline_run': QColor("yellow"),
    'normal_run': None,                            # No color for normal text
    'unknown_run': QColor("orange"),               # Orange for unknown
    'notpresent_run': None,                        # No color for not present
    
    # Line length indicator
    'max_line_length': QColor(255, 0, 255),        # Magenta
    
    # UI elements
    'noted_line_bg': QColor(255, 255, 200, 100),   # Light yellow
    'focused_border_active': QColor(0, 100, 255),  # Blue
    'focused_border_inactive': QColor(80, 80, 80), # Gray
    'region_highlight': QColor(0, 0, 255, 128),    # Blue with transparency
    
    # Diff map colors
    'diffmap_insert': QColor("green"),
    'diffmap_delete': QColor("red"),
    'diffmap_replace': QColor("salmon"),
    'diffmap_viewport': QColor(128, 128, 128, 100),
})


# Colorblind-friendly palette - avoids red/green combinations
# Uses blue/orange which are distinguishable for most types of colorblindness
COLORBLIND_PALETTE = ColorPalette('Colorblind Friendly', {
    # Line backgrounds - more visible
    'placeholder': QColor("darkgray"),
    'base_changed_bg': QColor(255, 220, 180),      # Darker orange/peach for better visibility
    'modi_changed_bg': QColor(200, 220, 255),      # Darker blue for better visibility
    
    # Run colors (for text highlighting)
    'add_run': QColor(135, 206, 250),              # Sky blue (instead of green)
    'delete_run': QColor(255, 140, 0),             # Dark orange (instead of red)
    'intraline_run': QColor(255, 255, 100),        # Bright yellow (high contrast)
    'normal_run': None,                            # No color for normal text
    'unknown_run': QColor(255, 165, 0),            # Orange for unknown
    'notpresent_run': None,                        # No color for not present
    
    # Line length indicator
    'max_line_length': QColor(255, 0, 255),        # Magenta (still vivid)
    
    # UI elements
    'noted_line_bg': QColor(255, 255, 200, 100),   # Light yellow
    'focused_border_active': QColor(0, 100, 255),  # Blue
    'focused_border_inactive': QColor(80, 80, 80), # Gray
    'region_highlight': QColor(0, 0, 255, 128),    # Blue with transparency
    
    # Diff map colors
    'diffmap_insert': QColor(70, 130, 180),        # Steel blue (instead of green)
    'diffmap_delete': QColor(255, 140, 0),         # Dark orange (instead of red)
    'diffmap_replace': QColor(255, 200, 120),      # Light orange
    'diffmap_viewport': QColor(128, 128, 128, 100),
})


# Dictionary of all available palettes
PALETTES = {
    'Standard': STANDARD_PALETTE,
    'Colorblind Friendly': COLORBLIND_PALETTE,
}


# Default palette
_current_palette = COLORBLIND_PALETTE


def get_current_palette():
    """Get the currently active color palette"""
    return _current_palette


def set_current_palette(palette_name):
    """Set the active color palette by name"""
    global _current_palette
    if palette_name in PALETTES:
        _current_palette = PALETTES[palette_name]
        return True
    return False


def get_palette_names():
    """Get list of available palette names"""
    return list(PALETTES.keys())
