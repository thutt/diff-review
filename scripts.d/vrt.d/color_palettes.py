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

import platform
import subprocess
from PyQt6.QtGui import QColor


def is_macos_dark_mode():
    """Detect if macOS is in dark mode"""
    if platform.system() != 'Darwin':
        return False
    
    try:
        result = subprocess.run(
            ['defaults', 'read', '-g', 'AppleInterfaceStyle'],
            capture_output=True,
            text=True,
            timeout=1
        )
        return result.returncode == 0 and 'Dark' in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


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
    
    # Whitespace visualization
    'TAB': QColor(255, 180, 255),                  # Light magenta for tabs - better contrast
    'TRAILINGWS': QColor(255, 200, 200),           # Light red for trailing whitespace
    
    # Search highlighting - two-tier system
    'search_highlight_all': QColor(255, 255, 150),     # Subtle yellow for all matches
    'search_highlight_current': QColor(255, 255, 0),   # Bright yellow for current match
    
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
    
    # Whitespace visualization
    'TAB': QColor(255, 200, 100),                  # Light orange/yellow for tabs - better contrast
    'TRAILINGWS': QColor(255, 200, 150),           # Light orange for trailing whitespace
    
    # Search highlighting - two-tier system for colorblind palette
    'search_highlight_all': QColor(255, 180, 255),     # Subtle magenta for all matches
    'search_highlight_current': QColor(255, 0, 255),   # Bright magenta for current match
    
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


# Dark mode standard palette - red/green for dark backgrounds
DARK_MODE_STANDARD_PALETTE = ColorPalette('Dark Mode Standard', {
    # Line backgrounds - subdued but visible on dark
    'placeholder': QColor(60, 60, 60),
    'base_changed_bg': QColor(80, 40, 40),         # Dark red/brown
    'modi_changed_bg': QColor(40, 80, 40),         # Dark green
    
    # Run colors (for text highlighting)
    'add_run': QColor(100, 200, 100),              # Bright green
    'delete_run': QColor(255, 100, 100),           # Bright red
    'intraline_run': QColor(100, 100, 0),          # Dark yellow - readable with white text
    'normal_run': None,
    'unknown_run': QColor(255, 165, 0),            # Orange
    'notpresent_run': None,
    
    # Whitespace visualization
    'TAB': QColor(180, 100, 180),                  # Medium magenta
    'TRAILINGWS': QColor(180, 80, 80),             # Medium red
    
    # Search highlighting
    'search_highlight_all': QColor(100, 100, 50),      # Dark yellow for all matches
    'search_highlight_current': QColor(200, 200, 0),   # Bright yellow for current
    
    # Line length indicator
    'max_line_length': QColor(200, 0, 200),        # Bright magenta
    
    # UI elements
    'noted_line_bg': QColor(80, 80, 40, 100),      # Dark yellow
    'focused_border_active': QColor(100, 150, 255), # Bright blue
    'focused_border_inactive': QColor(100, 100, 100), # Medium gray
    'region_highlight': QColor(100, 100, 255, 128), # Blue with transparency
    
    # Diff map colors
    'diffmap_insert': QColor(50, 150, 50),         # Medium green
    'diffmap_delete': QColor(200, 50, 50),         # Medium red
    'diffmap_replace': QColor(200, 120, 60),       # Orange
    'diffmap_viewport': QColor(150, 150, 150, 100),
})


# Dark mode colorblind palette - blue/orange for dark backgrounds
DARK_MODE_COLORBLIND_PALETTE = ColorPalette('Dark Mode Colorblind', {
    # Line backgrounds - subdued but visible on dark
    'placeholder': QColor(60, 60, 60),
    'base_changed_bg': QColor(80, 60, 40),         # Dark orange/brown
    'modi_changed_bg': QColor(40, 60, 80),         # Dark blue
    
    # Run colors (for text highlighting)
    'add_run': QColor(120, 180, 255),              # Bright sky blue
    'delete_run': QColor(255, 160, 80),            # Bright orange
    'intraline_run': QColor(100, 100, 0),          # Dark yellow - readable with white text
    'normal_run': None,
    'unknown_run': QColor(255, 165, 0),            # Orange
    'notpresent_run': None,
    
    # Whitespace visualization
    'TAB': QColor(200, 150, 100),                  # Light orange/yellow
    'TRAILINGWS': QColor(200, 140, 100),           # Light orange
    
    # Search highlighting
    'search_highlight_all': QColor(100, 80, 100),      # Dark magenta for all matches
    'search_highlight_current': QColor(200, 100, 200), # Bright magenta for current
    
    # Line length indicator
    'max_line_length': QColor(200, 0, 200),        # Bright magenta
    
    # UI elements
    'noted_line_bg': QColor(80, 80, 40, 100),      # Dark yellow
    'focused_border_active': QColor(100, 150, 255), # Bright blue
    'focused_border_inactive': QColor(100, 100, 100), # Medium gray
    'region_highlight': QColor(100, 100, 255, 128), # Blue with transparency
    
    # Diff map colors
    'diffmap_insert': QColor(70, 130, 200),        # Medium steel blue
    'diffmap_delete': QColor(255, 140, 60),        # Medium orange
    'diffmap_replace': QColor(220, 160, 100),      # Light orange
    'diffmap_viewport': QColor(150, 150, 150, 100),
})


# Dictionary of all available palettes
PALETTES = {
    'Standard': STANDARD_PALETTE,
    'Colorblind Friendly': COLORBLIND_PALETTE,
    'Dark Mode Standard': DARK_MODE_STANDARD_PALETTE,
    'Dark Mode Colorblind': DARK_MODE_COLORBLIND_PALETTE,
}


# Default palette - auto-select based on system theme
_current_palette = DARK_MODE_COLORBLIND_PALETTE if is_macos_dark_mode() else COLORBLIND_PALETTE


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
