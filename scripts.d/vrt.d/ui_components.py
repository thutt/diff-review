# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
UI Components for diff_review

This module contains the custom Qt widgets used in the diff viewer:
- LineNumberArea: Displays line numbers with change indicators
- DiffMapWidget: Mini-map showing overview of changes
- SyncedPlainTextEdit: Text editor with synchronized scrolling
"""
import sys
from PyQt6.QtWidgets import QWidget, QPlainTextEdit, QApplication
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QFont, QTextCursor, QFontMetrics, QPen
from color_palettes import get_current_palette


class LineNumberArea(QWidget):
    """Line number display with note markers"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_nums = []
        self.line_backgrounds = {}
        self.noted_lines = set()
        self._font = None
        self.text_widget = None
        self.setMinimumWidth(90)
    
    def setup_font(self):
        self._font = QFont("Courier", 12, QFont.Weight.Bold)
        self.setFont(self._font)
    
    def set_text_widget(self, widget):
        """Set the text widget to track for scrolling"""
        self.text_widget = widget
    
    def set_line_numbers(self, line_nums):
        self.line_nums = line_nums
        self.update()
    
    def set_line_background(self, line_index, color):
        self.line_backgrounds[line_index] = color
        self.update()
    
    def mark_noted(self, line_index):
        self.noted_lines.add(line_index)
        self.update()
    
    def paintEvent(self, event):
        if not self._font or not self.text_widget:
            return
        
        painter = QPainter(self)
        painter.setFont(self._font)
        fm = painter.fontMetrics()
        line_height = fm.height()
        
        first_visible_block = self.text_widget.firstVisibleBlock()
        viewport_height = self.height()
        current_block = first_visible_block
        
        while current_block.isValid():
            block_num = current_block.blockNumber()
            if block_num >= len(self.line_nums):
                break
            
            block_geom = self.text_widget.blockBoundingGeometry(current_block)
            y_pos = int(block_geom.translated(self.text_widget.contentOffset()).top()) + 1
            
            if y_pos > viewport_height:
                break
            
            line_num = self.line_nums[block_num]
            
            if block_num in self.line_backgrounds:
                painter.fillRect(0, y_pos, self.width(), line_height, 
                               self.line_backgrounds[block_num])
            
            if line_num is not None:
                # Use system palette text color for dark mode compatibility
                painter.setPen(self.palette().color(self.palette().ColorRole.Text))
                painter.drawText(10, y_pos + fm.ascent(), f"{line_num:6d} ")
            else:
                painter.fillRect(0, y_pos, self.width(), line_height,
                               QColor("darkgray"))
            
            current_block = current_block.next()


class DiffMapWidget(QWidget):
    """Mini-map showing change regions"""
    
    clicked = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.change_regions = []
        self.total_lines = 0
        self.viewport_start = 0
        self.viewport_end = 0
        self.setMinimumWidth(30)
        self.setMaximumWidth(30)
    
    def set_change_regions(self, regions, total_lines):
        self.change_regions = regions
        self.total_lines = total_lines
        self.update()
    
    def set_viewport(self, start, end):
        self.viewport_start = start
        self.viewport_end = end
        self.update()
    
    def paintEvent(self, event):
        if self.total_lines == 0:
            return
        
        palette = get_current_palette()
        painter = QPainter(self)
        height = self.height()
        width = self.width()
        
        painter.fillRect(0, 0, width, height, QColor("white"))
        
        for tag, start, end, *_ in self.change_regions:
            y1 = int((start / self.total_lines) * height)
            y2 = int((end / self.total_lines) * height)
            
            if tag == 'insert':
                color = palette.get_color('diffmap_insert')
            elif tag == 'delete':
                color = palette.get_color('diffmap_delete')
            else:
                color = palette.get_color('diffmap_replace')
            
            painter.fillRect(0, y1, width, max(y2 - y1, 2), color)
        
        if self.total_lines > 0 and self.viewport_end > self.viewport_start:
            vy1 = int((self.viewport_start / self.total_lines) * height)
            vy2 = int((self.viewport_end / self.total_lines) * height)
            painter.fillRect(0, vy1, width, max(vy2 - vy1, 2), 
                           palette.get_color('diffmap_viewport'))
    
    def mousePressEvent(self, event):
        if self.total_lines > 0:
            ratio = event.pos().y() / self.height()
            line = int(ratio * self.total_lines)
            self.clicked.emit(line)


class SyncedPlainTextEdit(QPlainTextEdit):
    """Plain text edit with synchronized scrolling"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = None
        
        self.region_highlight_start = -1
        self.region_highlight_end = -1
        self.focused_line = -1
        self.noted_lines = set()  # Track which lines have notes
        self.bookmarked_lines = set()  # Track which lines have bookmarks
        self.max_line_length = None  # Maximum line length indicator
        self.collapsed_markers = {}  # Dict mapping line_idx to num_collapsed_lines
        
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setTabChangesFocus(False)  # Allow Tab key to be handled in keyPressEvent
        
        # Enable text interaction to allow cursor even in read-only mode
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard | 
                                      Qt.TextInteractionFlag.TextSelectableByMouse)
        
        font = QFont("Courier", 12, QFont.Weight.Bold)
        self.setFont(font)
        
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Cursor visibility control - start hidden
        self.setCursorWidth(0)  # Hide cursor by default
        QApplication.instance().setCursorFlashTime(0)  # Disable blinking globally
    
    def focusInEvent(self, event):
        super().focusInEvent(event)
        line = self.textCursor().blockNumber()
        self.set_focused_line(line)
        if self.line_number_area:
            self.line_number_area.update()
        self.viewport().update()
    
    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        if self.line_number_area:
            self.line_number_area.update()
        self.viewport().update()
    
    def set_line_number_area(self, area):
        self.line_number_area = area
    
    def set_focused_line(self, line_num):
        if self.focused_line != line_num:
            self.focused_line = line_num
            self.viewport().update()
            if self.line_number_area:
                self.line_number_area.update()
    
    def get_focused_line(self):
        return self.focused_line
    
    def set_region_highlight(self, start, end):
        self.region_highlight_start = start
        self.region_highlight_end = end
        self.viewport().update()
    
    def clear_region_highlight(self):
        self.region_highlight_start = -1
        self.region_highlight_end = -1
        self.viewport().update()
    
    def set_max_line_length(self, length):
        """Set the maximum line length for the vertical indicator line"""
        self.max_line_length = length
        self.viewport().update()
    
    def keyPressEvent(self, event):
        # Ctrl+N now handled by DiffViewer.eventFilter
        
        key = event.key()
        modifiers = event.modifiers()
        
        is_nav_key = key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_PageUp, 
                             Qt.Key.Key_PageDown, Qt.Key.Key_Home, Qt.Key.Key_End,
                             Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Space)
        
        # Alt+H and Alt+L removed - were debugging code, not used
        
        if is_nav_key:
            # Show cursor for keyboard navigation
            self.setCursorWidth(2)
            
            shift_pressed = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
            move_mode = QTextCursor.MoveMode.KeepAnchor if shift_pressed else QTextCursor.MoveMode.MoveAnchor
            
            cursor = self.textCursor()
            
            if key == Qt.Key.Key_Up:
                cursor.movePosition(QTextCursor.MoveOperation.Up, move_mode)
            elif key == Qt.Key.Key_Down:
                cursor.movePosition(QTextCursor.MoveOperation.Down, move_mode)
            elif key == Qt.Key.Key_Left:
                cursor.movePosition(QTextCursor.MoveOperation.Left, move_mode)
            elif key == Qt.Key.Key_Right:
                cursor.movePosition(QTextCursor.MoveOperation.Right, move_mode)
            elif key == Qt.Key.Key_PageUp:
                cursor.movePosition(QTextCursor.MoveOperation.Up, move_mode, 10)
            elif key == Qt.Key.Key_PageDown:
                cursor.movePosition(QTextCursor.MoveOperation.Down, move_mode, 10)
            elif key == Qt.Key.Key_Space:
                # Space = page down, Shift+Space = page up
                if shift_pressed:
                    cursor.movePosition(QTextCursor.MoveOperation.Up, QTextCursor.MoveMode.MoveAnchor, 10)
                else:
                    cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor, 10)
            elif key == Qt.Key.Key_Home:
                cursor.movePosition(QTextCursor.MoveOperation.Start, move_mode)
            elif key == Qt.Key.Key_End:
                cursor.movePosition(QTextCursor.MoveOperation.End, move_mode)
            
            self.setTextCursor(cursor)
            new_line = cursor.blockNumber()
            self.set_focused_line(new_line)
            
            # Syncing to other_widget removed - now handled by DiffViewer.eventFilter
            
            self.viewport().update()
            if self.line_number_area:
                self.line_number_area.update()
        else:
            super().keyPressEvent(event)
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        palette = get_current_palette()
        painter = QPainter(self.viewport())
        font_metrics = self.fontMetrics()
        line_height = font_metrics.height()
        
        first_visible_block = self.firstVisibleBlock()
        first_visible = first_visible_block.blockNumber()
        
        # Draw bookmarked lines with left edge bar
        if self.bookmarked_lines:
            viewport_lines = self.viewport().height() // line_height if line_height > 0 else 0
            for line_idx in self.bookmarked_lines:
                if (line_idx >= first_visible and 
                    line_idx < first_visible + viewport_lines):
                    
                    block = self.document().findBlockByNumber(line_idx)
                    if block.isValid():
                        block_geom = self.blockBoundingGeometry(block)
                        y_pos = int(block_geom.translated(self.contentOffset()).top())
                        block_height = int(block_geom.height())
                        
                        # Bright cyan vertical bar on left edge - 5px wide for visibility
                        painter.fillRect(0, y_pos, 5, block_height, QColor(0, 255, 255))
        
        # Draw noted lines with background color
        if self.noted_lines:
            viewport_lines = self.viewport().height() // line_height if line_height > 0 else 0
            for line_idx in self.noted_lines:
                if (line_idx >= first_visible and 
                    line_idx < first_visible + viewport_lines):
                    
                    block = self.document().findBlockByNumber(line_idx)
                    if block.isValid():
                        block_geom = self.blockBoundingGeometry(block)
                        y_pos = int(block_geom.translated(self.contentOffset()).top())
                        block_height = int(block_geom.height())
                        
                        # Light yellow/cream background for noted lines
                        painter.fillRect(0, y_pos, self.viewport().width(), 
                                       block_height, palette.get_color('noted_line_bg'))
        
        # Draw current line indicator - blue if focused, gray if not
        if self.focused_line >= 0:
            viewport_lines = self.viewport().height() // line_height if line_height > 0 else 0
            if (self.focused_line >= first_visible and 
                self.focused_line < first_visible + viewport_lines):
                
                focused_block = self.document().findBlockByNumber(self.focused_line)
                if focused_block.isValid():
                    block_geom = self.blockBoundingGeometry(focused_block)
                    y_pos = int(block_geom.translated(self.contentOffset()).top())
                    block_height = int(block_geom.height())
                    
                    # Use blue if this widget has focus, gray otherwise
                    if self.hasFocus():
                        pen = QPen(palette.get_color('focused_border_active'))
                    else:
                        pen = QPen(palette.get_color('focused_border_inactive'))
                    
                    pen.setWidth(3)
                    painter.setPen(pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    # Mac needs top moved UP 2 more pixels
                    if sys.platform == 'darwin':
                        painter.drawRect(1, y_pos - 2, self.viewport().width() - 3, block_height + 1)
                    else:
                        painter.drawRect(1, y_pos + 1, self.viewport().width() - 3, block_height - 3)
        
        # Draw region highlight
        if self.region_highlight_start >= 0 and self.region_highlight_end > self.region_highlight_start:
            painter.setPen(palette.get_color('region_highlight'))
            
            start_block = self.document().findBlockByNumber(self.region_highlight_start)
            end_block = self.document().findBlockByNumber(self.region_highlight_end - 1)
            
            if start_block.isValid() and end_block.isValid():
                start_geom = self.blockBoundingGeometry(start_block).translated(self.contentOffset())
                end_geom = self.blockBoundingGeometry(end_block).translated(self.contentOffset())
                
                y_start = int(start_geom.top())
                y_end = int(end_geom.bottom())
                
                if y_end > 0 and y_start < self.viewport().height():
                    painter.drawRect(0, y_start, self.viewport().width() - 1, y_end - y_start - 1)
        
        # Draw max line length indicator
        if self.max_line_length is not None:
            pen = QPen(palette.get_color('max_line_length'))
            pen.setWidth(2)
            painter.setPen(pen)
            
            char_width = font_metrics.horizontalAdvance('0')
            # Calculate x position relative to content, accounting for horizontal scroll
            content_x_pos = self.max_line_length * char_width
            x_pos = int(content_x_pos + self.contentOffset().x())
            
            # Only draw if the line is visible in the viewport
            if 0 <= x_pos <= self.viewport().width():
                painter.drawLine(x_pos, 0, x_pos, self.viewport().height())
        
        # Draw collapsed region markers
        if hasattr(self, 'collapsed_markers') and self.collapsed_markers:
            viewport_lines = self.viewport().height() // line_height if line_height > 0 else 0
            for line_idx, marker_data in self.collapsed_markers.items():
                if (line_idx >= first_visible and 
                    line_idx < first_visible + viewport_lines):
                    
                    block = self.document().findBlockByNumber(line_idx)
                    if block.isValid() and block.isVisible():
                        block_geom = self.blockBoundingGeometry(block)
                        y_pos = int(block_geom.translated(self.contentOffset()).top())
                        block_height = int(block_geom.height())
                        
                        # Extract num_lines and region_type from marker_data
                        # Handle both old format (int) and new format (tuple)
                        if isinstance(marker_data, tuple):
                            num_lines, region_type = marker_data
                        else:
                            num_lines = marker_data
                            region_type = 'deleted'
                        
                        # Draw a distinct background for the collapse marker line
                        painter.fillRect(0, y_pos, self.viewport().width(), 
                                       block_height, QColor(230, 230, 250))
                        
                        # Draw the collapse marker text with appropriate label
                        marker_text = f"[...{num_lines} {region_type} lines collapsed...]"
                        painter.setPen(QColor(100, 100, 150))
                        text_y = y_pos + font_metrics.ascent() + 2
                        painter.drawText(10, text_y, marker_text)
    
    # wheelEvent removed - wheel scroll syncing now handled by DiffViewer.eventFilter
    
    # scrollContentsBy removed - scroll syncing now handled by DiffViewer signal connections
    
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        
        # Hide cursor on mouse click
        self.setCursorWidth(0)
        
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        
        cursor = self.cursorForPosition(event.pos())
        line_num = cursor.blockNumber()
        
        self.set_focused_line(line_num)
        # other_widget.set_focused_line removed - handled by focusInEvent -> DiffViewer.eventFilter
