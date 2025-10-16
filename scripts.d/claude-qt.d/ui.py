#!/usr/bin/env python3
"""
Diff Viewer using PyQt6 - Clean rebuild with Search functionality

Installation:
    pip install PyQt6
"""
import sys
import os
from typing import Optional

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                  QHBoxLayout, QLabel, QScrollBar, QFrame, QMenu,
                                  QMessageBox, QPlainTextEdit, QDialog, QListWidget,
                                  QPushButton, QListWidgetItem, QTextEdit, QCheckBox)
    from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QtMsgType, qInstallMessageHandler
    from PyQt6.QtGui import (QColor, QPainter, QFont, QTextCursor, QAction, 
                             QFontMetrics, QTextCharFormat, QPalette, QPen,
                             QTextBlockFormat)
except ImportError:
    print("Error: PyQt6 is not installed.", file=sys.stderr)
    print("Please install it with: pip install PyQt6", file=sys.stderr)
    sys.exit(1)


# Custom message handler to suppress XKB warnings
def qt_message_handler(mode, context, message):
    # Suppress XKB compose warnings
    if 'xkb' in message.lower() or 'compose' in message.lower():
        return
    # For other messages, print to stderr as normal
    if mode == QtMsgType.QtDebugMsg:
        print(f"Qt Debug: {message}", file=sys.stderr)
    elif mode == QtMsgType.QtWarningMsg:
        print(f"Qt Warning: {message}", file=sys.stderr)
    elif mode == QtMsgType.QtCriticalMsg:
        print(f"Qt Critical: {message}", file=sys.stderr)
    elif mode == QtMsgType.QtFatalMsg:
        print(f"Qt Fatal: {message}", file=sys.stderr)

# Install the message handler
qInstallMessageHandler(qt_message_handler)


class SearchDialog(QDialog):
    """Dialog to input search text"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_text = None
        self.case_sensitive = False
        self.search_base = True
        self.search_modi = True
        
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
        
        # Checkboxes row
        checkbox_layout = QHBoxLayout()
        
        # Case sensitivity checkbox
        self.case_checkbox = QCheckBox("Case sensitive")
        self.case_checkbox.setChecked(False)
        checkbox_layout.addWidget(self.case_checkbox)
        
        checkbox_layout.addStretch()
        
        # Base file checkbox
        self.base_checkbox = QCheckBox("Base")
        self.base_checkbox.setChecked(True)
        checkbox_layout.addWidget(self.base_checkbox)
        
        # Modified file checkbox
        self.modi_checkbox = QCheckBox("Modi")
        self.modi_checkbox.setChecked(True)
        checkbox_layout.addWidget(self.modi_checkbox)
        
        layout.addLayout(checkbox_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.on_search)
        self.search_button.setDefault(True)  # Make it default so Enter triggers it
        
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
        text = self.search_input.toPlainText().strip()
        if text:
            self.search_text = text
            self.case_sensitive = self.case_checkbox.isChecked()
            self.search_base = self.base_checkbox.isChecked()
            self.search_modi = self.modi_checkbox.isChecked()
            self.accept()


class SearchResultDialog(QDialog):
    """Dialog to show search results and allow selection"""
    
    def __init__(self, search_text, parent=None, case_sensitive=False, search_base=True, search_modi=True):
        super().__init__(parent)
        self.search_text = search_text
        self.selected_result = None
        self.case_sensitive = case_sensitive
        self.search_base = search_base
        self.search_modi = search_modi
        self.parent_viewer = parent
        
        self.setWindowTitle(f"Search Results for: {search_text}")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Checkboxes row
        checkbox_layout = QHBoxLayout()
        
        # Case sensitivity checkbox
        self.case_checkbox = QCheckBox("Case sensitive")
        self.case_checkbox.setChecked(case_sensitive)
        self.case_checkbox.stateChanged.connect(self.on_checkbox_changed)
        checkbox_layout.addWidget(self.case_checkbox)
        
        checkbox_layout.addStretch()
        
        # Base file checkbox
        self.base_checkbox = QCheckBox("Base")
        self.base_checkbox.setChecked(search_base)
        self.base_checkbox.stateChanged.connect(self.on_checkbox_changed)
        checkbox_layout.addWidget(self.base_checkbox)
        
        # Modified file checkbox
        self.modi_checkbox = QCheckBox("Modi")
        self.modi_checkbox.setChecked(search_modi)
        self.modi_checkbox.stateChanged.connect(self.on_checkbox_changed)
        checkbox_layout.addWidget(self.modi_checkbox)
        
        layout.addLayout(checkbox_layout)
        
        # Info label
        self.info_label = QLabel()
        layout.addWidget(self.info_label)
        
        # Results list
        self.result_list = QListWidget()
        self.result_list.itemDoubleClicked.connect(self.on_select)
        layout.addWidget(self.result_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.on_select)
        self.select_button.setEnabled(False)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.select_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Enable/disable select button based on selection
        self.result_list.itemSelectionChanged.connect(self.on_selection_changed)
        
        # Initial search
        self.perform_search()
    
    def on_checkbox_changed(self, state):
        """Handle checkbox changes"""
        self.case_sensitive = self.case_checkbox.isChecked()
        self.search_base = self.base_checkbox.isChecked()
        self.search_modi = self.modi_checkbox.isChecked()
        self.perform_search()
    
    def perform_search(self):
        """Perform the search and populate results"""
        # Clear existing results
        self.result_list.clear()
        
        if not self.parent_viewer:
            return
        
        # Perform search
        results = []
        search_text = self.search_text
        
        # Determine comparison function based on case sensitivity
        if self.case_sensitive:
            matches = lambda line: search_text in line
        else:
            search_lower = search_text.lower()
            matches = lambda line: search_lower in line.lower()
        
        # Search in base (only if checkbox is selected)
        if self.search_base:
            for i, (line_text, line_num) in enumerate(zip(self.parent_viewer.base_display, 
                                                           self.parent_viewer.base_line_nums)):
                if line_num is not None and matches(line_text):
                    results.append(('base', line_num, i, line_text))
        
        # Search in modified (only if checkbox is selected)
        if self.search_modi:
            for i, (line_text, line_num) in enumerate(zip(self.parent_viewer.modified_display, 
                                                           self.parent_viewer.modified_line_nums)):
                if line_num is not None and matches(line_text):
                    results.append(('modified', line_num, i, line_text))
        
        # Update info label
        self.info_label.setText(f"Found {len(results)} matches:")
        
        # Populate results list
        for side, line_num, line_idx, line_text in results:
            display_text = f"[{side.upper()}] Line {line_num}: {line_text}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, (side, line_num, line_idx))
            self.result_list.addItem(item)
    
    def on_selection_changed(self):
        """Enable select button when an item is selected"""
        self.select_button.setEnabled(len(self.result_list.selectedItems()) > 0)
    
    def on_select(self):
        """Handle selection"""
        selected_items = self.result_list.selectedItems()
        if selected_items:
            item = selected_items[0]
            self.selected_result = item.data(Qt.ItemDataRole.UserRole)
            # Emit signal to parent but don't close dialog
            # Parent will handle navigation
            if self.parent_viewer:
                side, line_num, line_idx = self.selected_result
                self.parent_viewer.select_search_result(side, line_idx)


class LineNumberArea(QWidget):
    """Line number display with note markers"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_nums = []
        self.line_backgrounds = {}
        self.noted_lines = set()
        self._font = None
        self.text_widget = None  # Reference to the text widget we're tracking
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
        
        # Check if text widget has focus
        widget_has_focus = self.text_widget.hasFocus()
        
        # Get the first visible block to calculate offset
        first_visible_block = self.text_widget.firstVisibleBlock()
        first_visible_line = first_visible_block.blockNumber()
        
        # Get the vertical offset of the first visible block
        block_top = self.text_widget.blockBoundingGeometry(first_visible_block).translated(
            self.text_widget.contentOffset()).top()
        
        # Draw line numbers starting from first visible
        viewport_height = self.height()
        current_block = first_visible_block
        
        while current_block.isValid():
            block_num = current_block.blockNumber()
            if block_num >= len(self.line_nums):
                break
            
            # Calculate y position
            block_geom = self.text_widget.blockBoundingGeometry(current_block)
            y_pos = int(block_geom.translated(self.text_widget.contentOffset()).top())
            
            # Stop if we're past the viewport
            if y_pos > viewport_height:
                break
            
            line_num = self.line_nums[block_num]
            
            # Background color if set
            if block_num in self.line_backgrounds:
                painter.fillRect(0, y_pos, self.width(), line_height, 
                               self.line_backgrounds[block_num])
            
            # Draw focus indicator (blue circle) on the left if this widget has focus
            # and this is the focused line
            if widget_has_focus and block_num == self.text_widget.focused_line:
                painter.setBrush(QColor(100, 150, 255))  # Light blue
                painter.setPen(Qt.PenStyle.NoPen)
                # Draw small circle on the left side
                circle_x = 2
                circle_y = y_pos + line_height // 2
                painter.drawEllipse(circle_x - 3, circle_y - 3, 6, 6)
            
            if line_num is not None:
                # Draw line number (shifted right to make room for focus indicator)
                painter.setPen(QColor("black"))
                painter.drawText(10, y_pos + fm.ascent(), f"{line_num:6d} ")
                
                # Draw note marker if noted
                if block_num in self.noted_lines:
                    painter.setPen(QColor("red"))
                    arrow_x = 10 + fm.horizontalAdvance(f"{line_num:6d} ")
                    painter.drawText(arrow_x, y_pos + fm.ascent(), "►")
            else:
                # NotPresent line
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
        
        painter = QPainter(self)
        height = self.height()
        width = self.width()
        
        # White background
        painter.fillRect(0, 0, width, height, QColor("white"))
        
        # Draw change regions
        for tag, start, end, *_ in self.change_regions:
            y1 = int((start / self.total_lines) * height)
            y2 = int((end / self.total_lines) * height)
            
            if tag == 'insert':
                color = QColor("green")
            elif tag == 'delete':
                color = QColor("red")
            else:
                color = QColor("salmon")
            
            painter.fillRect(0, y1, width, max(y2 - y1, 2), color)
        
        # Draw viewport indicator
        if self.total_lines > 0 and self.viewport_end > self.viewport_start:
            vy1 = int((self.viewport_start / self.total_lines) * height)
            vy2 = int((self.viewport_end / self.total_lines) * height)
            painter.fillRect(0, vy1, width, max(vy2 - vy1, 2), 
                           QColor(128, 128, 128, 100))
    
    def mousePressEvent(self, event):
        if self.total_lines > 0:
            ratio = event.pos().y() / self.height()
            line = int(ratio * self.total_lines)
            self.clicked.emit(line)


class SyncedPlainTextEdit(QPlainTextEdit):
    """Plain text edit with synchronized scrolling"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.other_widget = None
        self.line_number_area = None  # Reference to associated line number area
        self._in_wheel_event = False
        self._in_scroll_event = False
        self._in_key_event = False
        
        # Store region highlight rectangles
        self.region_highlight_start = -1
        self.region_highlight_end = -1
        
        # Track focused line for grey border
        self.focused_line = -1
        
        # Setup
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        
        # Enable keyboard focus but don't participate in tab focus chain
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        
        # Font
        font = QFont("Courier", 12, QFont.Weight.Bold)
        self.setFont(font)
        
        # Hide scrollbars
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    
    def focusInEvent(self, event):
        """Called when widget gains focus"""
        super().focusInEvent(event)
        line = self.textCursor().blockNumber()
        # Update focused line and repaint line number area
        self.set_focused_line(line)
        if self.other_widget:
            self.other_widget.set_focused_line(line)
        # Force line number area to repaint to show focus indicator
        if self.line_number_area:
            self.line_number_area.update()
        if self.other_widget and self.other_widget.line_number_area:
            self.other_widget.line_number_area.update()
    
    def focusOutEvent(self, event):
        """Called when widget loses focus"""
        super().focusOutEvent(event)
        # Force line number area to repaint to remove focus indicator
        if self.line_number_area:
            self.line_number_area.update()
        if self.other_widget and self.other_widget.line_number_area:
            self.other_widget.line_number_area.update()
    
    def set_other_widget(self, other):
        """Set the other text widget to sync with"""
        self.other_widget = other
    
    def set_line_number_area(self, area):
        """Set the line number area to update"""
        self.line_number_area = area
    
    def set_focused_line(self, line_num):
        """Set the focused line and update display"""
        if self.focused_line != line_num:
            self.focused_line = line_num
            self.viewport().update()
            if self.line_number_area:
                self.line_number_area.update()
    
    def get_focused_line(self):
        """Get the currently focused line"""
        return self.focused_line
    
    def set_region_highlight(self, start, end):
        """Set region to highlight with box"""
        self.region_highlight_start = start
        self.region_highlight_end = end
        self.viewport().update()
    
    def clear_region_highlight(self):
        """Clear region highlight"""
        self.region_highlight_start = -1
        self.region_highlight_end = -1
        self.viewport().update()
    
    def keyPressEvent(self, event):
        """Override to sync on keyboard navigation"""
        
        if not self._in_key_event:
            self._in_key_event = True
            
            # Check for Tab to toggle focus between panes
            if event.key() == Qt.Key.Key_Tab:
                # Find the parent DiffViewer
                parent = self.parent()
                while parent and not isinstance(parent, QMainWindow):
                    parent = parent.parent()
                    
                if parent and hasattr(parent, 'base_text') and hasattr(parent, 'modified_text'):
                    # Get current line
                    current_line = self.textCursor().blockNumber()
                    
                    # Determine which widget we are and which is the target
                    if parent.base_text == self:
                        target_widget = parent.modified_text
                    else:
                        target_widget = parent.base_text
                    
                    # Move target widget's cursor to same line
                    block = target_widget.document().findBlockByNumber(current_line)
                    if block.isValid():
                        cursor = target_widget.textCursor()
                        cursor.setPosition(block.position())
                        target_widget.setTextCursor(cursor)
                    
                    # Set focus on target widget
                    target_widget.setFocus(Qt.FocusReason.TabFocusReason)
                    
                    # Update focused line on both widgets
                    self.set_focused_line(current_line)
                    target_widget.set_focused_line(current_line)
                
                self._in_key_event = False
                return  # Don't call super, we handled it
            
            # Check for Ctrl+N for note taking
            if event.key() == Qt.Key.Key_N and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                cursor = self.textCursor()
                
                # If no selection, create a selection for the current line
                if not cursor.hasSelection():
                    # Select the entire current line
                    cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
                    self.setTextCursor(cursor)
                
                # Now take the note (whether it was pre-selected or we just selected the line)
                parent = self.parent()
                while parent and not isinstance(parent, QMainWindow):
                    parent = parent.parent()
                if parent and hasattr(parent, 'take_note_from_widget'):
                    # Determine which side this widget is
                    side = 'base' if parent.base_text == self else 'modified'
                    parent.take_note_from_widget(side)
                
                # Don't call super - we've handled it
                self._in_key_event = False
                return
            
            # Check if it's a navigation key before processing
            key = event.key()
            modifiers = event.modifiers()
            
            is_nav_key = key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_PageUp, 
                                 Qt.Key.Key_PageDown, Qt.Key.Key_Home, Qt.Key.Key_End,
                                 Qt.Key.Key_Left, Qt.Key.Key_Right)
            
            # Check if it's a parent window command key (N, P, C, T, B, Escape)
            is_parent_command = key in (Qt.Key.Key_N, Qt.Key.Key_P, Qt.Key.Key_C,
                                       Qt.Key.Key_T, Qt.Key.Key_B, Qt.Key.Key_Escape)
            
            # Check if it's Alt+H or Alt+L
            is_alt_command = ((key == Qt.Key.Key_H or key == Qt.Key.Key_L) and 
                            modifiers & Qt.KeyboardModifier.AltModifier)
            
            # Forward parent command keys and Alt commands to the main window
            if (is_parent_command or is_alt_command) and not (modifiers & Qt.KeyboardModifier.ControlModifier):
                parent = self.parent()
                while parent and not isinstance(parent, QMainWindow):
                    parent = parent.parent()
                if parent:
                    parent.keyPressEvent(event)
                    self._in_key_event = False
                    return
            
            
            if is_nav_key:
                # Check if Shift is pressed for selection
                shift_pressed = event.modifiers() & Qt.KeyboardModifier.ShiftModifier
                move_mode = QTextCursor.MoveMode.KeepAnchor if shift_pressed else QTextCursor.MoveMode.MoveAnchor
                
                # For read-only widgets, manually move the cursor
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
                elif key == Qt.Key.Key_Home:
                    cursor.movePosition(QTextCursor.MoveOperation.Start, move_mode)
                elif key == Qt.Key.Key_End:
                    cursor.movePosition(QTextCursor.MoveOperation.End, move_mode)
                
                self.setTextCursor(cursor)
                
                # Get new line after movement
                new_line = cursor.blockNumber()
                
                # Update focused line to current cursor position
                self.set_focused_line(new_line)
                
                if self.other_widget and not self.other_widget._in_key_event:
                    self.other_widget._in_key_event = True
                    self.other_widget.verticalScrollBar().setValue(
                        self.verticalScrollBar().value())
                    self.other_widget.horizontalScrollBar().setValue(
                        self.horizontalScrollBar().value())
                    # Sync focused line to other widget
                    self.other_widget.set_focused_line(new_line)
                    # Force viewport update
                    self.other_widget.viewport().update()
                    # Update other widget's line number area
                    if self.other_widget.line_number_area:
                        self.other_widget.line_number_area.update()
                    self.other_widget._in_key_event = False
                
                # Force this widget's viewport update too
                self.viewport().update()
                # Update this widget's line number area
                if self.line_number_area:
                    self.line_number_area.update()
            else:
                # For non-navigation keys, use default behavior
                super().keyPressEvent(event)
            
            self._in_key_event = False
        else:
            super().keyPressEvent(event)
    
    def paintEvent(self, event):
        """Override paint to draw region box and focused line border"""
        super().paintEvent(event)
        
        painter = QPainter(self.viewport())
        font_metrics = self.fontMetrics()
        line_height = font_metrics.height()
        
        # Get first visible block
        first_visible_block = self.firstVisibleBlock()
        first_visible = first_visible_block.blockNumber()
        
        # Draw focused line border
        if self.focused_line >= 0:
            # Check if focused line is visible
            viewport_lines = self.viewport().height() // line_height if line_height > 0 else 0
            if (self.focused_line >= first_visible and 
                self.focused_line < first_visible + viewport_lines):
                
                # Get the actual block for the focused line
                focused_block = self.document().findBlockByNumber(self.focused_line)
                if focused_block.isValid():
                    # Calculate y position using block geometry (same as LineNumberArea)
                    block_geom = self.blockBoundingGeometry(focused_block)
                    y_pos = int(block_geom.translated(self.contentOffset()).top())
                    block_height = int(block_geom.height())
                    
                    # Draw prominent grey border around the line
                    pen = QPen(QColor(80, 80, 80))  # Darker grey
                    pen.setWidth(3)  # 3 pixels thick
                    painter.setPen(pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawRect(1, y_pos + 1, self.viewport().width() - 3, block_height - 3)
        
        # Draw region highlight box
        if self.region_highlight_start >= 0 and self.region_highlight_end > self.region_highlight_start:
            painter.setPen(QColor(0, 0, 255, 128))  # Semi-transparent blue
            
            # Get the blocks for start and end
            start_block = self.document().findBlockByNumber(self.region_highlight_start)
            end_block = self.document().findBlockByNumber(self.region_highlight_end - 1)  # -1 because end is exclusive
            
            if start_block.isValid() and end_block.isValid():
                # Calculate positions using block geometry
                start_geom = self.blockBoundingGeometry(start_block).translated(self.contentOffset())
                end_geom = self.blockBoundingGeometry(end_block).translated(self.contentOffset())
                
                y_start = int(start_geom.top())
                y_end = int(end_geom.bottom())
                
                # Only draw if visible
                if y_end > 0 and y_start < self.viewport().height():
                    # Draw rectangle
                    painter.drawRect(0, y_start, self.viewport().width() - 1, y_end - y_start - 1)
    
    def wheelEvent(self, event):
        """Override wheel event to sync scrolling"""
        if not self._in_wheel_event:
            self._in_wheel_event = True
            
            # Scroll this widget
            super().wheelEvent(event)
            
            # Sync the other widget
            if self.other_widget and not self.other_widget._in_wheel_event:
                self.other_widget._in_wheel_event = True
                self.other_widget.verticalScrollBar().setValue(
                    self.verticalScrollBar().value())
                self.other_widget.horizontalScrollBar().setValue(
                    self.horizontalScrollBar().value())
                # Update other widget's line number area
                if self.other_widget.line_number_area:
                    self.other_widget.line_number_area.update()
                self.other_widget._in_wheel_event = False
            
            # Update this widget's line number area
            if self.line_number_area:
                self.line_number_area.update()
            
            self._in_wheel_event = False
    
    def scrollContentsBy(self, dx, dy):
        """Override to sync horizontal scrolling"""
        super().scrollContentsBy(dx, dy)
        
        if not self._in_scroll_event and self.other_widget:
            self._in_scroll_event = True
            self.other_widget._in_scroll_event = True
            self.other_widget.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value())
            self.other_widget.verticalScrollBar().setValue(
                self.verticalScrollBar().value())
            # Update other widget's line number area
            if self.other_widget.line_number_area:
                self.other_widget.line_number_area.update()
            self.other_widget._in_scroll_event = False
            self._in_scroll_event = False
        
        # Update this widget's line number area
        if self.line_number_area:
            self.line_number_area.update()
    
    def mousePressEvent(self, event):
        """Override to set focused line on click"""
        super().mousePressEvent(event)
        
        # Make sure this widget gets keyboard focus
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        
        # Get the line that was clicked
        cursor = self.cursorForPosition(event.pos())
        line_num = cursor.blockNumber()
        
        
        # Set focus on this line for both widgets
        self.set_focused_line(line_num)
        if self.other_widget:
            self.other_widget.set_focused_line(line_num)


class DiffViewer(QMainWindow):
    def __init__(self, base_file: str, modified_file: str, note_file: Optional[str] = None, description_file: Optional[str] = None):
        # Ensure QApplication exists
        if QApplication.instance() is None:
            self._app = QApplication(sys.argv)
        else:
            self._app = QApplication.instance()
        
        super().__init__()
        
        self.base_file = base_file
        self.modified_file = modified_file
        self.note_file = note_file
        self.description_file = description_file
        self.note_count = 0
        
        self.base_noted_lines = set()
        self.modified_noted_lines = set()
        
        self.base_display = []
        self.modified_display = []
        self.base_line_nums = []
        self.modified_line_nums = []
        self.change_regions = []
        self.base_line_objects = []
        self.modified_line_objects = []
        
        self.current_region = 0
        
        # Store region highlight data
        self.current_region_highlight = None
        
        # Track the target region during navigation to prevent scroll interference
        self._target_region = None
        
        self.setup_gui()
    
    def extract_display_path(self, filepath):
        """Extract the display path starting after base.d/ or modi.d/"""
        # Look for 'base.d/' or 'modi.d/' in the path and return what comes after
        if 'base.d/' in filepath:
            idx = filepath.find('base.d/')
            return filepath[idx + len('base.d/'):]
        elif 'modi.d/' in filepath:
            idx = filepath.find('modi.d/')
            return filepath[idx + len('modi.d/'):]
        elif 'base.d' in filepath:
            # Handle case without trailing slash
            idx = filepath.find('base.d')
            remaining = filepath[idx + len('base.d'):]
            return remaining.lstrip('/')
        elif 'modi.d' in filepath:
            # Handle case without trailing slash
            idx = filepath.find('modi.d')
            remaining = filepath[idx + len('modi.d'):]
            return remaining.lstrip('/')
        else:
            # If neither found, return the original path
            return filepath
    
    def setup_gui(self):
        """Setup the GUI"""
        self.setWindowTitle(f"Diff Viewer: {self.base_file} vs {self.modified_file}")
        
        # Create menu bar
        menubar = self.menuBar()
        help_menu = menubar.addMenu("Help")
        
        # Add "How to Use" action
        help_action = QAction("How to Use", self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # File labels
        label_layout = QHBoxLayout()
        
        # Base side with label
        base_container = QHBoxLayout()
        base_type_label = QLabel("Base")
        base_type_label.setStyleSheet("font-weight: bold; color: blue; padding: 2px 5px;")
        base_file_label = QLabel(self.extract_display_path(self.base_file))
        base_file_label.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
        base_container.addWidget(base_type_label)
        base_container.addWidget(base_file_label, 1)
        
        # Spacer for diff map
        spacer = QLabel("")
        
        # Modified side with label
        modified_container = QHBoxLayout()
        modified_type_label = QLabel("Modified")
        modified_type_label.setStyleSheet("font-weight: bold; color: green; padding: 2px 5px;")
        modified_file_label = QLabel(self.extract_display_path(self.modified_file))
        modified_file_label.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
        modified_container.addWidget(modified_type_label)
        modified_container.addWidget(modified_file_label, 1)
        
        # Add to main layout
        label_layout.addLayout(base_container, 1)
        label_layout.addWidget(spacer, 0)
        label_layout.addLayout(modified_container, 1)
        main_layout.addLayout(label_layout)
        
        # Content area
        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)
        
        # Base side
        base_layout = QHBoxLayout()
        base_layout.setSpacing(0)
        self.base_line_area = LineNumberArea()
        self.base_line_area.setup_font()
        self.base_text = SyncedPlainTextEdit()
        self.base_line_area.set_text_widget(self.base_text)
        self.base_text.set_line_number_area(self.base_line_area)
        base_layout.addWidget(self.base_line_area)
        base_layout.addWidget(self.base_text)
        base_container = QWidget()
        base_container.setLayout(base_layout)
        content_layout.addWidget(base_container, 1)
        
        # Diff map
        self.diff_map = DiffMapWidget()
        self.diff_map.clicked.connect(self.on_diff_map_click)
        self.diff_map_visible = True  # Track visibility state
        content_layout.addWidget(self.diff_map)
        
        # Modified side
        modified_layout = QHBoxLayout()
        modified_layout.setSpacing(0)
        self.modified_line_area = LineNumberArea()
        self.modified_line_area.setup_font()
        self.modified_text = SyncedPlainTextEdit()
        self.modified_line_area.set_text_widget(self.modified_text)
        self.modified_text.set_line_number_area(self.modified_line_area)
        modified_layout.addWidget(self.modified_line_area)
        modified_layout.addWidget(self.modified_text)
        modified_container = QWidget()
        modified_container.setLayout(modified_layout)
        content_layout.addWidget(modified_container, 1)
        
        # Track line number visibility
        self.line_numbers_visible = True
        
        # External scrollbars
        self.v_scrollbar = QScrollBar(Qt.Orientation.Vertical)
        self.v_scrollbar.valueChanged.connect(self.on_v_scroll)
        content_layout.addWidget(self.v_scrollbar)
        
        main_layout.addLayout(content_layout, 1)
        
        self.h_scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        self.h_scrollbar.valueChanged.connect(self.on_h_scroll)
        main_layout.addWidget(self.h_scrollbar)
        
        # Status bar
        status_layout = QHBoxLayout()
        self.region_label = QLabel("Region: 0 of 0")
        self.notes_label = QLabel("Notes: 0")
        
        # Description button
        self.description_button = QPushButton("Description")
        self.description_button.clicked.connect(self.show_description)
        if not self.description_file:
            self.description_button.setEnabled(False)
        
        status_layout.addWidget(self.region_label)
        status_layout.addStretch()
        status_layout.addWidget(self.description_button)
        status_layout.addWidget(self.notes_label)
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)
        status_frame.setLayout(status_layout)
        main_layout.addWidget(status_frame)
        
        # Link the two text widgets for synchronized scrolling
        self.base_text.set_other_widget(self.modified_text)
        self.modified_text.set_other_widget(self.base_text)
        
        # Connect scrollbars
        self.base_text.verticalScrollBar().valueChanged.connect(self.sync_v_scroll)
        self.base_text.horizontalScrollBar().valueChanged.connect(self.sync_h_scroll)
        
        # Connect text widget updates to line number area repaints
        self.base_text.verticalScrollBar().valueChanged.connect(self.base_line_area.update)
        self.modified_text.verticalScrollBar().valueChanged.connect(self.modified_line_area.update)
        
        # Context menus
        self.base_text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.modified_text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.base_text.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, 'base'))
        self.modified_text.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(pos, 'modified'))
        
        # Double-click
        self.base_text.mouseDoubleClickEvent = lambda e: self.on_double_click(e, 'base')
        self.modified_text.mouseDoubleClickEvent = lambda e: self.on_double_click(e, 'modified')
        
        # Mouse wheel on diff map
        self.diff_map.wheelEvent = self.on_diff_map_wheel
        
        # Set initial size
        font_metrics = QFont("Courier", 12, QFont.Weight.Bold)
        fm = QFontMetrics(font_metrics)
        char_width = fm.horizontalAdvance('0')
        line_height = fm.height()
        
        total_width = (160 * char_width) + (90 * 2) + 30 + 20 + 40
        total_height = (50 * line_height) + 40 + 20 + 30 + 20
        self.resize(total_width, total_height)
    
    def add_line(self, base, modi):
        """Add a line pair"""
        base_text = base.line_.rstrip('\n') if hasattr(base, 'line_') else ''
        modi_text = modi.line_.rstrip('\n') if hasattr(modi, 'line_') else ''
        
        base_num = base.line_num_ if base.show_line_number() else None
        modi_num = modi.line_num_ if modi.show_line_number() else None
        
        self.base_display.append(base_text)
        self.modified_display.append(modi_text)
        self.base_line_nums.append(base_num)
        self.modified_line_nums.append(modi_num)
        self.base_line_objects.append(base)
        self.modified_line_objects.append(modi)
    
    def finalize(self):
        """Finalize and display content"""
        self.build_change_regions()
        self.populate_content()
        self.apply_highlighting()
        self.update_status()
        QTimer.singleShot(100, self.init_scrollbars)
        
        # Force initial render of line number areas
        QTimer.singleShot(150, self.base_line_area.update)
        QTimer.singleShot(150, self.modified_line_area.update)
        QTimer.singleShot(150, self.base_text.viewport().update)
        QTimer.singleShot(150, self.modified_text.viewport().update)
        
        # Navigate to first change region if any exist
        if self.change_regions:
            QTimer.singleShot(200, self.navigate_to_first_region)
    
    def navigate_to_first_region(self):
        """Navigate to the first change region on startup"""
        if self.change_regions:
            self.current_region = 0
            _, start, *_ = self.change_regions[0]
            self.center_on_line(start)
            self.highlight_current_region()
    
    def build_change_regions(self):
        """Build change regions"""
        self.change_regions = []
        region_start = None
        region_tag = None
        
        for i, (base_line, modi_line) in enumerate(zip(self.base_line_objects,
                                                        self.modified_line_objects)):
            base_present = base_line.show_line_number()
            modi_present = modi_line.show_line_number()
            
            if base_present and modi_present:
                is_changed = self.line_has_changes(base_line) or self.line_has_changes(modi_line)
                current_tag = 'replace' if is_changed else None
            elif base_present and not modi_present:
                current_tag = 'delete'
            elif not base_present and modi_present:
                current_tag = 'insert'
            else:
                current_tag = None
            
            if current_tag is not None:
                if region_start is None:
                    region_start = i
                    region_tag = current_tag
                elif region_tag != current_tag:
                    self.change_regions.append((region_tag, region_start, i, 0, 0, 0, 0))
                    region_start = i
                    region_tag = current_tag
            else:
                if region_start is not None:
                    self.change_regions.append((region_tag, region_start, i, 0, 0, 0, 0))
                    region_start = None
                    region_tag = None
        
        if region_start is not None:
            self.change_regions.append((region_tag, region_start, 
                                       len(self.base_line_objects), 0, 0, 0, 0))
    
    def line_has_changes(self, line_obj):
        """Check if line has changes"""
        if not hasattr(line_obj, 'runs_'):
            return False
        return any(run.changed_ for run in line_obj.runs_)
    
    def populate_content(self):
        """Populate text content"""
        self.base_line_area.set_line_numbers(self.base_line_nums)
        self.modified_line_area.set_line_numbers(self.modified_line_nums)
        
        self.base_text.setPlainText('\n'.join(self.base_display))
        self.modified_text.setPlainText('\n'.join(self.modified_display))
        
        self.diff_map.set_change_regions(self.change_regions, len(self.base_display))
    
    def apply_highlighting(self):
        """Apply syntax highlighting"""
        for i, (base_line, modi_line) in enumerate(zip(self.base_line_objects,
                                                        self.modified_line_objects)):
            # Base
            if not base_line.show_line_number():
                self.highlight_line(self.base_text, i, QColor("darkgray"))
            else:
                self.apply_runs(self.base_text, i, base_line)
                if self.line_has_changes(base_line):
                    self.base_line_area.set_line_background(i, QColor(255, 238, 238))
            
            # Modified
            if not modi_line.show_line_number():
                self.highlight_line(self.modified_text, i, QColor("darkgray"))
            else:
                self.apply_runs(self.modified_text, i, modi_line)
                if self.line_has_changes(modi_line):
                    self.modified_line_area.set_line_background(i, QColor(238, 255, 238))
    
    def highlight_line(self, text_widget, line_num, color):
        """Highlight entire line with block format"""
        
        # Get block directly by number - much faster than cursor movement
        block = text_widget.document().findBlockByNumber(line_num)
        if not block.isValid():
            return
        
        cursor = text_widget.textCursor()
        cursor.setPosition(block.position())
        
        # Use block format for full-width background
        block_fmt = QTextBlockFormat()
        block_fmt.setBackground(color)
        cursor.setBlockFormat(block_fmt)
    
    def apply_runs(self, text_widget, line_idx, line_obj):
        """Apply run highlighting"""
        if not hasattr(line_obj, 'runs_'):
            return
        
        # Get block directly - much faster than cursor movement
        block = text_widget.document().findBlockByNumber(line_idx)
        if not block.isValid():
            return
        
        # Get document length for bounds checking
        doc_length = text_widget.document().characterCount()
        block_pos = block.position()
        
        # If block position is out of range, skip this line
        if block_pos >= doc_length:
            return
        
        for run in line_obj.runs_:
            color_name = run.color()
            color = None
            
            if color_name == 'ADD':
                color = QColor("lightgreen")
            elif color_name == 'DELETE':
                color = QColor("red")
            elif color_name == 'INTRALINE':
                color = QColor("yellow")
            
            if color:
                line_text = block.text()
                
                # If run covers the entire line, use block format for full width
                if run.start_ == 0 and run.len_ >= len(line_text):
                    cursor = text_widget.textCursor()
                    if block_pos < doc_length:
                        cursor.setPosition(block_pos)
                        block_fmt = QTextBlockFormat()
                        block_fmt.setBackground(color)
                        cursor.setBlockFormat(block_fmt)
                else:
                    # Character-level formatting for partial line
                    cursor = text_widget.textCursor()
                    start_pos = block_pos + run.start_
                    end_pos = block_pos + run.start_ + run.len_
                    
                    # Ensure positions are within document bounds
                    if start_pos < doc_length:
                        # Clamp end position to not exceed block or document
                        block_end = block_pos + len(line_text)
                        end_pos = min(end_pos, block_end, doc_length - 1)
                        
                        # Only apply formatting if we have a valid range
                        if end_pos > start_pos:
                            cursor.setPosition(start_pos)
                            cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
                            
                            fmt = QTextCharFormat()
                            fmt.setBackground(color)
                            cursor.mergeCharFormat(fmt)
    
    def init_scrollbars(self):
        """Initialize scrollbar ranges"""
        self.v_scrollbar.setMaximum(self.base_text.verticalScrollBar().maximum())
        self.h_scrollbar.setMaximum(self.base_text.horizontalScrollBar().maximum())
        self.update_diff_map_viewport()
    
    def on_v_scroll(self, value):
        """Handle external vertical scrollbar"""
        self.base_text.verticalScrollBar().setValue(value)
        self.modified_text.verticalScrollBar().setValue(value)
        self.update_diff_map_viewport()
    
    def on_h_scroll(self, value):
        """Handle external horizontal scrollbar"""
        self.base_text.horizontalScrollBar().setValue(value)
        self.modified_text.horizontalScrollBar().setValue(value)
    
    def sync_v_scroll(self, value):
        """Sync vertical scrolling"""
        self.v_scrollbar.setValue(value)
        self.modified_text.verticalScrollBar().setValue(value)
        self.update_diff_map_viewport()
        self.update_current_region_from_scroll()
    
    def sync_h_scroll(self, value):
        """Sync horizontal scrolling"""
        self.h_scrollbar.setValue(value)
        self.modified_text.horizontalScrollBar().setValue(value)
    
    def on_diff_map_wheel(self, event):
        """Handle mouse wheel on diff map"""
        # Forward to base text widget
        self.base_text.wheelEvent(event)
    
    def update_diff_map_viewport(self):
        """Update diff map viewport indicator"""
        if len(self.base_display) == 0:
            return
        
        block = self.base_text.firstVisibleBlock()
        first_visible = block.blockNumber()
        
        viewport_height = self.base_text.viewport().height()
        line_height = self.base_text.fontMetrics().height()
        visible_lines = viewport_height // line_height if line_height > 0 else 10
        
        self.diff_map.set_viewport(first_visible, first_visible + visible_lines)
    
    def update_current_region_from_scroll(self):
        """Update current region based on first visible line"""
        # Don't interfere with explicit navigation to a target region
        if self._target_region is not None:
            return
            
        if not self.change_regions:
            return
        
        block = self.base_text.firstVisibleBlock()
        first_visible = block.blockNumber()
        
        # Find which region contains the first visible line
        for i, (tag, start, end, *_) in enumerate(self.change_regions):
            if start <= first_visible < end:
                if self.current_region != i:
                    self.current_region = i
                    self.update_status()
                return
        
        # If not in a region, find the nearest following region
        for i, (tag, start, end, *_) in enumerate(self.change_regions):
            if start > first_visible:
                if self.current_region != i:
                    self.current_region = i
                    self.update_status()
                return
    
    def on_double_click(self, event, side):
        """Handle double-click for note taking"""
        if not self.note_file:
            QMessageBox.information(self, 'Note Taking Disabled',
                                  'No note file supplied.')
            return
        
        text_widget = self.base_text if side == 'base' else self.modified_text
        line_nums = self.base_line_nums if side == 'base' else self.modified_line_nums
        display_lines = self.base_display if side == 'base' else self.modified_display
        filename = self.base_file if side == 'base' else self.modified_file
        
        cursor = text_widget.cursorForPosition(event.pos())
        line_idx = cursor.blockNumber()
        
        if line_idx >= len(line_nums) or line_nums[line_idx] is None:
            return
        
        with open(self.note_file, 'a') as f:
            prefix = '(base): ' if side == 'base' else '(modi): '
            clean_filename = self.extract_display_path(filename)
            f.write(f"{prefix}{clean_filename}\n")
            f.write(f"  {line_nums[line_idx]}: {display_lines[line_idx]}\n\n")
        
        self.mark_noted_line(side, line_nums[line_idx])
        self.note_count += 1
        self.update_status()
    
    def show_help(self):
        """Show help dialog with usage instructions"""
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Diff Viewer - How to Use")
        help_dialog.setMinimumSize(700, 600)
        
        layout = QVBoxLayout(help_dialog)
        
        # Create scrollable text area for help content
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h2>Diff Viewer - User Guide</h2>
        
        <h3>Overview</h3>
        <p>This diff viewer displays side-by-side comparison of two files with synchronized scrolling and highlighting of changes.</p>
        <p>The left pane shows the <b>Base</b> file (original version) and the right pane shows the <b>Modified</b> file (changed version). Each pane is clearly labeled at the top.</p>
        
        <h3>Navigation</h3>
        <ul>
            <li><b>Arrow Keys:</b> Navigate up/down/left/right through the text</li>
            <li><b>Page Up/Down:</b> Scroll by page</li>
            <li><b>Home/End:</b> Jump to beginning/end of document</li>
            <li><b>Mouse Wheel:</b> Scroll vertically (syncs both panes)</li>
            <li><b>Tab:</b> Switch focus between base and modified panes</li>
            <li><b>N:</b> Jump to next change region</li>
            <li><b>P:</b> Jump to previous change region</li>
            <li><b>C:</b> Center on the currently selected region</li>
            <li><b>T:</b> Jump to top of document</li>
            <li><b>B:</b> Jump to bottom of document</li>
            <li><b>Alt+H:</b> Toggle diff map visibility (hides/shows center column)</li>
            <li><b>Alt+L:</b> Toggle line numbers visibility (hides/shows line number columns)</li>
            <li><b>Ctrl+S:</b> Open search dialog</li>
            <li><b>Ctrl+N:</b> Take a note for the current line or selection</li>
            <li><b>Escape:</b> Close the viewer</li>
        </ul>
        
        <h3>Visual Indicators</h3>
        <ul>
            <li><b>"Base" Label (Blue):</b> Identifies the left pane showing the original file</li>
            <li><b>"Modified" Label (Green):</b> Identifies the right pane showing the changed file</li>
            <li><b>Line Numbers:</b> Displayed on the left side of each pane</li>
            <li><b>Blue Circle:</b> Indicates the currently focused line in the active pane</li>
            <li><b>Grey Border:</b> Highlights the focused line</li>
            <li><b>Blue Box:</b> Shows the current change region</li>
            <li><b>Pink Background:</b> Lines with changes in base file</li>
            <li><b>Light Green Background:</b> Lines with changes in modified file</li>
            <li><b>Dark Gray:</b> Lines not present in one of the files</li>
            <li><b>Yellow Highlight:</b> Intra-line changes (character-level differences)</li>
            <li><b>Red Arrow (►):</b> Lines that have been noted</li>
        </ul>
        
        <h3>Diff Map (Center Column)</h3>
        <ul>
            <li>Provides a bird's-eye view of all changes in the document</li>
            <li><b>Green:</b> Insertions</li>
            <li><b>Red:</b> Deletions</li>
            <li><b>Salmon:</b> Replacements/modifications</li>
            <li><b>Gray Box:</b> Current viewport position</li>
            <li><b>Click:</b> Jump to that location and select the nearest change region</li>
            <li>Clicking anywhere near a region will select it (no need for pixel-perfect accuracy)</li>
            <li>If you click in an area with no changes, the nearest region in the document is selected</li>
            <li>The selected region will be highlighted with a blue box and shown in the status bar</li>
            <li><b>Tip:</b> If the selected region is not visible, press <b>C</b> to center it on screen</li>
        </ul>
        
        <h3>Taking Notes</h3>
        <p>If a note file is specified, you can save notes about specific lines:</p>
        <ul>
            <li><b>Double-click:</b> Take a note for the clicked line</li>
            <li><b>Right-click → Take Note:</b> Take a note for selected lines</li>
            <li><b>Ctrl+N:</b> Take a note for the current line or selection</li>
            <li>Notes are appended to the note file with line numbers and content</li>
        </ul>
        
        <h3>Search Functionality</h3>
        <p>There are two ways to search:</p>
        <ul>
            <li><b>Ctrl+S:</b> Opens a search dialog where you can enter any text
                <ul>
                    <li>Enter your search text in the input box</li>
                    <li>Optionally check "Case sensitive" for exact case matching</li>
                    <li><b>Base checkbox:</b> Include/exclude matches from the base file (checked by default)</li>
                    <li><b>Modi checkbox:</b> Include/exclude matches from the modified file (checked by default)</li>
                    <li>Press Enter or click "Search" to find matches</li>
                </ul>
            </li>
            <li><b>Right-click → Search:</b> Search for currently selected text
                <ul>
                    <li>Select text in either pane</li>
                    <li>Right-click and choose "Search"</li>
                    <li>Search is case-insensitive by default and searches both files</li>
                </ul>
            </li>
        </ul>
        <p><b>Search Results Dialog:</b></p>
        <ul>
            <li>Shows matches based on selected options</li>
            <li>Displays side (BASE/MODIFIED), line number, and line content</li>
            <li><b>Case sensitive checkbox:</b> Toggle to re-run search with/without case sensitivity</li>
            <li><b>Base checkbox:</b> Toggle to show/hide matches from base file</li>
            <li><b>Modi checkbox:</b> Toggle to show/hide matches from modified file</li>
            <li>Results update immediately when any checkbox is toggled</li>
            <li><b>Select a result:</b> Click and press "Select" to navigate to that line</li>
            <li><b>Dialog stays open:</b> Navigate to multiple results before closing</li>
            <li><b>Cancel:</b> Close the search results dialog</li>
        </ul>
        
        <h3>Status Bar</h3>
        <ul>
            <li><b>Region:</b> Shows current change region number and total</li>
            <li><b>Description:</b> Button to view commit description (if provided)</li>
            <li><b>Notes:</b> Shows number of notes taken</li>
        </ul>
        
        <h3>Commit Description</h3>
        <p>The fourth command-line argument specifies the description file. Use 'None' for no description, or provide the absolute path to a text file containing the commit message or change description. When provided, the Description button in the status bar will be enabled and clicking it opens a window showing the description.</p>
        <p><b>Description Window Features:</b></p>
        <ul>
            <li>Non-modal window (can use main diff viewer while description is open)</li>
            <li><b>Ctrl+S:</b> Search within the description text</li>
            <li><b>Right-click → Search:</b> Search for selected text in description</li>
            <li><b>Ctrl+N:</b> Take a note for the current line or selection</li>
            <li><b>Right-click → Take Note:</b> Take a note for selected text</li>
            <li>Search results dialog shows all matches with line numbers</li>
            <li>Notes are saved with "(desc):" prefix to indicate they're from the description</li>
            <li>Same font as source code for consistency</li>
        </ul>
        
        <h3>Tips</h3>
        <ul>
            <li>Use the diff map for quick navigation to changed regions</li>
            <li>Use Tab to quickly compare the same line in both panes</li>
            <li>Select multiple lines and take notes to document important changes</li>
            <li>The viewer maintains synchronized scrolling and cursor position</li>
        </ul>
        """)
        
        layout.addWidget(help_text)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(help_dialog.accept)
        layout.addWidget(close_button)
        
        help_dialog.exec()
    
    def show_description(self):
        """Show commit description dialog"""
        if not self.description_file:
            return
        
        # If dialog already exists and is visible, just raise it
        if hasattr(self, 'description_dialog') and self.description_dialog.isVisible():
            self.description_dialog.raise_()
            self.description_dialog.activateWindow()
            return
        
        # Read description file
        try:
            with open(self.description_file, 'r') as f:
                description_text = f.read()
        except Exception as e:
            QMessageBox.warning(self, 'Error Reading Description',
                              f'Could not read description file:\n{e}')
            return
        
        # Create dialog
        self.description_dialog = QDialog(self, Qt.WindowType.Window)  # Window flag removes stay-on-top
        self.description_dialog.setWindowTitle("Commit Description")
        
        # Calculate width for 100 characters using the font
        font = QFont("Courier", 12, QFont.Weight.Bold)
        fm = QFontMetrics(font)
        char_width = fm.horizontalAdvance('0')
        
        # Width: 100 characters + margins/padding
        dialog_width = (100 * char_width) + 40  # Extra for margins and scrollbar
        dialog_height = 500
        
        self.description_dialog.resize(dialog_width, dialog_height)
        
        # Store reference to text area for search functionality
        self.description_text_area = QPlainTextEdit()
        self.description_text_area.setReadOnly(True)
        self.description_text_area.setPlainText(description_text)
        
        # Use same font as source code
        font = QFont("Courier", 12, QFont.Weight.Bold)
        self.description_text_area.setFont(font)
        
        layout = QVBoxLayout(self.description_dialog)
        
        # Add Ctrl+S search functionality - shows results dialog
        def show_search_dialog_from_description():
            # Create simple search dialog without Base/Modi checkboxes
            search_dialog = QDialog(self.description_dialog)
            search_dialog.setWindowTitle("Search")
            search_dialog.setMinimumWidth(400)
            
            dialog_layout = QVBoxLayout(search_dialog)
            
            # Search text input
            input_layout = QHBoxLayout()
            input_layout.addWidget(QLabel("Search for:"))
            search_input = QPlainTextEdit()
            search_input.setMaximumHeight(60)
            search_input.setPlaceholderText("Enter search text...")
            input_layout.addWidget(search_input)
            dialog_layout.addLayout(input_layout)
            
            # Case sensitivity checkbox only
            case_checkbox = QCheckBox("Case sensitive")
            case_checkbox.setChecked(False)
            dialog_layout.addWidget(case_checkbox)
            
            # Buttons
            button_layout = QHBoxLayout()
            search_button = QPushButton("Search")
            search_button.setDefault(True)
            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(search_dialog.reject)
            button_layout.addStretch()
            button_layout.addWidget(search_button)
            button_layout.addWidget(cancel_button)
            dialog_layout.addLayout(button_layout)
            
            search_input.setFocus()
            
            # Handle search
            def do_search():
                text = search_input.toPlainText().strip()
                if text:
                    search_dialog.accept()
                    self.show_description_search_results(text, case_checkbox.isChecked())
            
            search_button.clicked.connect(do_search)
            
            search_dialog.exec()
        
        # Add right-click context menu with search
        def show_context_menu_description(pos):
            menu = QMenu(self.description_dialog)
            cursor = self.description_text_area.textCursor()
            has_selection = cursor.hasSelection()
            
            # Add Search action
            search_action = QAction("Search", self.description_dialog)
            search_action.setEnabled(has_selection)
            if has_selection:
                search_action.triggered.connect(lambda: search_selected_text_description())
            menu.addAction(search_action)
            
            # Add separator
            menu.addSeparator()
            
            # Add Take Note action
            if has_selection and self.note_file:
                note_action = QAction("Take Note", self.description_dialog)
                note_action.triggered.connect(lambda: take_note_from_description())
                menu.addAction(note_action)
            else:
                note_action = QAction("Take Note (no selection)" if self.note_file else 
                                   "Take Note (no file supplied)", self.description_dialog)
                note_action.setEnabled(False)
                menu.addAction(note_action)
            
            menu.exec(self.description_text_area.mapToGlobal(pos))
        
        def search_selected_text_description():
            cursor = self.description_text_area.textCursor()
            if not cursor.hasSelection():
                return
            
            search_text = cursor.selectedText()
            # Show search results dialog (case-insensitive by default)
            self.show_description_search_results(search_text, False)
        
        def take_note_from_description():
            """Take note from description selection"""
            if not self.note_file:
                QMessageBox.information(self.description_dialog, 'Note Taking Disabled',
                                      'No note file supplied.')
                return
            
            cursor = self.description_text_area.textCursor()
            if not cursor.hasSelection():
                return
            
            # Get selected text
            selected_text = cursor.selectedText()
            # Qt uses U+2029 (paragraph separator) for newlines in selectedText
            selected_text = selected_text.replace('\u2029', '\n')
            
            # Write to note file
            with open(self.note_file, 'a') as f:
                f.write("(desc): Commit Description\n")
                # Indent each line
                for line in selected_text.split('\n'):
                    f.write(f"  {line}\n")
                f.write('\n')
            
            self.note_count += 1
            self.update_status()
        
        # Set up context menu
        self.description_text_area.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.description_text_area.customContextMenuRequested.connect(show_context_menu_description)
        
        # Install event filter for Ctrl+S and Ctrl+N
        from PyQt6.QtCore import QObject
        class DescriptionEventFilter(QObject):
            def __init__(self, parent, search_func, note_func):
                super().__init__(parent)
                self.search_func = search_func
                self.note_func = note_func
            
            def eventFilter(self, obj, event):
                if event.type() == event.Type.KeyPress:
                    if (event.key() == Qt.Key.Key_S and 
                        event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                        self.search_func()
                        return True
                    elif (event.key() == Qt.Key.Key_N and 
                          event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                        # Handle Ctrl+N for note taking
                        cursor = obj.textCursor() if hasattr(obj, 'textCursor') else None
                        if cursor and not cursor.hasSelection():
                            # Select the current line if no selection
                            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
                            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, 
                                              QTextCursor.MoveMode.KeepAnchor)
                            obj.setTextCursor(cursor)
                        self.note_func()
                        return True
                return False
        
        search_filter = DescriptionEventFilter(self.description_dialog, 
                                               show_search_dialog_from_description,
                                               take_note_from_description)
        self.description_text_area.installEventFilter(search_filter)
        self.description_dialog.installEventFilter(search_filter)
        
        layout.addWidget(self.description_text_area)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.description_dialog.close)
        layout.addWidget(close_button)
        
        # Show non-modal
        self.description_dialog.show()
    
    def show_description_search_results(self, search_text, case_sensitive):
        """Show search results for description text"""
        # Create results dialog
        results_dialog = QDialog(self.description_dialog)
        results_dialog.setWindowTitle(f"Search Results for: {search_text}")
        results_dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(results_dialog)
        
        # Case sensitivity checkbox
        case_checkbox = QCheckBox("Case sensitive")
        case_checkbox.setChecked(case_sensitive)
        layout.addWidget(case_checkbox)
        
        # Info label
        info_label = QLabel()
        layout.addWidget(info_label)
        
        # Results list
        result_list = QListWidget()
        result_list.itemDoubleClicked.connect(lambda item: self.select_description_search_result(item))
        layout.addWidget(result_list)
        
        # Function to perform search and update results
        def perform_search():
            result_list.clear()
            
            # Search in description text
            description_lines = self.description_text_area.toPlainText().split('\n')
            results = []
            
            is_case_sensitive = case_checkbox.isChecked()
            
            if is_case_sensitive:
                matches = lambda line: search_text in line
            else:
                search_lower = search_text.lower()
                matches = lambda line: search_lower in line.lower()
            
            for line_num, line_text in enumerate(description_lines):
                if matches(line_text):
                    results.append((line_num, line_text))
            
            # Populate results
            info_label.setText(f"Found {len(results)} matches:")
            
            for line_num, line_text in results:
                display_text = f"Line {line_num + 1}: {line_text}"
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, line_num)
                result_list.addItem(item)
        
        # Connect checkbox to re-run search
        case_checkbox.stateChanged.connect(perform_search)
        
        # Initial search
        perform_search()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        select_button = QPushButton("Select")
        select_button.clicked.connect(lambda: self.select_description_search_result(result_list.currentItem()))
        select_button.setEnabled(False)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(results_dialog.reject)
        
        result_list.itemSelectionChanged.connect(
            lambda: select_button.setEnabled(len(result_list.selectedItems()) > 0))
        
        button_layout.addStretch()
        button_layout.addWidget(select_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        results_dialog.exec()
    
    def select_description_search_result(self, item):
        """Navigate to selected search result in description"""
        if not item:
            return
        
        line_num = item.data(Qt.ItemDataRole.UserRole)
        
        # Move cursor to that line
        cursor = self.description_text_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        
        # Move down to the target line
        for _ in range(line_num):
            cursor.movePosition(QTextCursor.MoveOperation.Down)
        
        # Select the entire line
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        
        self.description_text_area.setTextCursor(cursor)
        self.description_text_area.centerCursor()
        
        # Raise the description window
        self.description_dialog.raise_()
        self.description_dialog.activateWindow()
    
    def show_context_menu(self, pos, side):
        """Show context menu with search option"""
        menu = QMenu(self)
        text_widget = self.base_text if side == 'base' else self.modified_text
        
        has_selection = text_widget.textCursor().hasSelection()
        
        # Add Search action
        search_action = QAction("Search", self)
        search_action.setEnabled(has_selection)
        search_action.triggered.connect(lambda: self.search_selected_text(side))
        menu.addAction(search_action)
        
        # Add separator
        menu.addSeparator()
        
        # Add Take Note action
        if has_selection and self.note_file:
            note_action = QAction("Take Note", self)
            note_action.triggered.connect(lambda: self.take_note(side))
            menu.addAction(note_action)
        else:
            note_action = QAction("Take Note (no selection)" if self.note_file else 
                           "Take Note (no file supplied)", self)
            note_action.setEnabled(False)
            menu.addAction(note_action)
        
        menu.exec(text_widget.mapToGlobal(pos))
    
    def show_search_dialog(self):
        """Show search input dialog (Ctrl+S)"""
        dialog = SearchDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.search_text:
            # Show search results with all parameters from the search dialog
            results_dialog = SearchResultDialog(dialog.search_text, self, 
                                               dialog.case_sensitive,
                                               dialog.search_base,
                                               dialog.search_modi)
            results_dialog.exec()
    
    def search_selected_text(self, side):
        """Search for selected text in both base and modified sources"""
        text_widget = self.base_text if side == 'base' else self.modified_text
        cursor = text_widget.textCursor()
        
        if not cursor.hasSelection():
            return
        
        search_text = cursor.selectedText()
        
        # Show search results dialog - it stays open until Cancel is clicked
        # The dialog will perform the initial search
        dialog = SearchResultDialog(search_text, self)
        dialog.exec()
    
    def select_search_result(self, side, line_idx):
        """Select and navigate to a search result"""
        # Center on the line
        self.center_on_line(line_idx)
        
        # Set focus to the appropriate widget
        if side == 'base':
            self.base_text.setFocus()
        else:
            self.modified_text.setFocus()
    
    def take_note(self, side):
        """Take note from selection"""
        if not self.note_file:
            QMessageBox.information(self, 'Note Taking Disabled',
                                  'No note file supplied.')
            return
        
        text_widget = self.base_text if side == 'base' else self.modified_text
        line_nums = self.base_line_nums if side == 'base' else self.modified_line_nums
        display_lines = self.base_display if side == 'base' else self.modified_display
        filename = self.base_file if side == 'base' else self.modified_file
        
        cursor = text_widget.textCursor()
        if not cursor.hasSelection():
            return
        
        # Get the actual block numbers from the cursor positions
        selection_start = cursor.selectionStart()
        selection_end = cursor.selectionEnd()
        
        # Find blocks containing the selection
        doc = text_widget.document()
        start_block = doc.findBlock(selection_start)
        end_block = doc.findBlock(selection_end)
        
        start_block_num = start_block.blockNumber()
        end_block_num = end_block.blockNumber()
        
        # If selection ends at the start of a line, don't include that line
        if selection_end == end_block.position():
            end_block_num -= 1
        
        with open(self.note_file, 'a') as f:
            prefix = '(base): ' if side == 'base' else '(modi): '
            clean_filename = self.extract_display_path(filename)
            f.write(f"{prefix}{clean_filename}\n")
            
            for i in range(start_block_num, end_block_num + 1):
                if i < len(line_nums) and line_nums[i] is not None:
                    f.write(f"  {line_nums[i]}: {display_lines[i]}\n")
                    self.mark_noted_line(side, line_nums[i])
            f.write('\n')
        
        self.note_count += 1
        self.update_status()
    
    def take_note_from_widget(self, side):
        """Wrapper for take_note that can be called from widget keyPressEvent"""
        self.take_note(side)
    
    def mark_noted_line(self, side, line_num):
        """Mark line as noted"""
        if side == 'base':
            self.base_noted_lines.add(line_num)
            for i, num in enumerate(self.base_line_nums):
                if num == line_num:
                    self.base_line_area.mark_noted(i)
        else:
            self.modified_noted_lines.add(line_num)
            for i, num in enumerate(self.modified_line_nums):
                if num == line_num:
                    self.modified_line_area.mark_noted(i)
    
    def on_diff_map_click(self, line):
        """Handle diff map click"""
        # First, try to find a region that contains this line
        found_region = False
        for i, (tag, start, end, *_) in enumerate(self.change_regions):
            if start <= line < end:
                self.current_region = i
                found_region = True
                break
        
        # If no exact match, find the nearest region
        if not found_region and self.change_regions:
            # Find the closest region (either before or after the clicked line)
            min_distance = float('inf')
            nearest_region = 0
            
            for i, (tag, start, end, *_) in enumerate(self.change_regions):
                # Calculate distance to region (use start of region)
                distance = abs(start - line)
                if distance < min_distance:
                    min_distance = distance
                    nearest_region = i
            
            self.current_region = nearest_region
        
        self.center_on_line(line)
        self.highlight_current_region()
        self.update_status()
    
    def center_on_line(self, line):
        """Center on specific line"""
        # Get block directly - much faster
        base_block = self.base_text.document().findBlockByNumber(line)
        if base_block.isValid():
            cursor = self.base_text.textCursor()
            cursor.setPosition(base_block.position())
            self.base_text.setTextCursor(cursor)
            self.base_text.centerCursor()
        
        modi_block = self.modified_text.document().findBlockByNumber(line)
        if modi_block.isValid():
            cursor = self.modified_text.textCursor()
            cursor.setPosition(modi_block.position())
            self.modified_text.setTextCursor(cursor)
            self.modified_text.centerCursor()
        
        # Update focused line for border display
        self.base_text.set_focused_line(line)
        self.modified_text.set_focused_line(line)
        
        # Update line number areas
        self.base_line_area.update()
        self.modified_line_area.update()
        
        # Update diff map viewport after navigation
        self.update_diff_map_viewport()
    
    def center_current_region(self):
        """Center on the currently selected region"""
        if self.change_regions and 0 <= self.current_region < len(self.change_regions):
            self._target_region = self.current_region
            
            _, start, *_ = self.change_regions[self.current_region]
            self.center_on_line(start)
            self.highlight_current_region()
            self.update_status()
            
            # Check if navigation completed after scroll settles
            QTimer.singleShot(200, self.check_navigation_complete)
    
    def check_navigation_complete(self):
        """Check if we've reached the target region and clear the lock"""
        if self._target_region is None:
            return
        
        # Check if the target region is now visible
        if not self.change_regions or self._target_region >= len(self.change_regions):
            self._target_region = None
            return
        
        _, start, end, *_ = self.change_regions[self._target_region]
        block = self.base_text.firstVisibleBlock()
        first_visible = block.blockNumber()
        
        viewport_height = self.base_text.viewport().height()
        line_height = self.base_text.fontMetrics().height()
        visible_lines = viewport_height // line_height if line_height > 0 else 10
        last_visible = first_visible + visible_lines
        
        # If the target region is in the visible range, we're done navigating
        if start >= first_visible and start < last_visible:
            self._target_region = None
    
    def next_change(self):
        """Go to next change"""
        if not self.change_regions:
            return
        
        # If we're at the last region, wrap to the first
        if self.current_region >= len(self.change_regions) - 1:
            if len(self.change_regions) == 1:
                # Single region - just navigate to it
                self._target_region = 0
                self.current_region = 0
                _, start, *_ = self.change_regions[0]
                self.center_on_line(start)
                self.highlight_current_region()
                self.update_status()
                QTimer.singleShot(200, self.check_navigation_complete)
            return
        
        self.current_region += 1
        self._target_region = self.current_region
        _, start, *_ = self.change_regions[self.current_region]
        self.center_on_line(start)
        self.highlight_current_region()
        self.update_status()
        
        # Check if navigation completed after scroll settles
        QTimer.singleShot(200, self.check_navigation_complete)
    
    def prev_change(self):
        """Go to previous change"""
        if not self.change_regions:
            return
        
        # If we're at the first region, handle single region case
        if self.current_region <= 0:
            if len(self.change_regions) == 1:
                # Single region - just navigate to it
                self._target_region = 0
                self.current_region = 0
                _, start, *_ = self.change_regions[0]
                self.center_on_line(start)
                self.highlight_current_region()
                self.update_status()
                QTimer.singleShot(200, self.check_navigation_complete)
            return
        
        self.current_region -= 1
        self._target_region = self.current_region
        _, start, *_ = self.change_regions[self.current_region]
        self.center_on_line(start)
        self.highlight_current_region()
        self.update_status()
        
        # Check if navigation completed after scroll settles
        QTimer.singleShot(200, self.check_navigation_complete)
    
    def highlight_current_region(self):
        """Highlight the current region with a box"""
        if not self.change_regions:
            return
        
        # Get current region bounds
        _, start, end, *_ = self.change_regions[self.current_region]
        
        # Set box highlight on both widgets
        self.base_text.set_region_highlight(start, end)
        self.modified_text.set_region_highlight(start, end)
    
    def remove_region_highlights(self):
        """Remove region highlight boxes"""
        self.base_text.clear_region_highlight()
        self.modified_text.clear_region_highlight()
    
    def add_region_highlight(self, text_widget, start, end):
        """This method is no longer used - kept for compatibility"""
        pass
    
    def update_status(self):
        """Update status bar"""
        total = len(self.change_regions)
        current = self.current_region + 1 if total > 0 else 0
        self.region_label.setText(f"Region: {current} of {total}")
        self.notes_label.setText(f"Notes: {self.note_count}")
    
    def event(self, event):
        """Override event to catch Tab key before Qt's focus management"""
        if event.type() == event.Type.KeyPress:
            key_event = event
            if key_event.key() == Qt.Key.Key_Tab:
                
                # Get which widget currently has focus
                if self.base_text.hasFocus():
                    current_widget = self.base_text
                    target_widget = self.modified_text
                elif self.modified_text.hasFocus():
                    current_widget = self.modified_text
                    target_widget = self.base_text
                else:
                    self.base_text.setFocus()
                    return True  # Event handled
                
                # Get current line
                current_line = current_widget.textCursor().blockNumber()
                
                # Move target widget's cursor to same line
                block = target_widget.document().findBlockByNumber(current_line)
                if block.isValid():
                    cursor = target_widget.textCursor()
                    cursor.setPosition(block.position())
                    target_widget.setTextCursor(cursor)
                
                # Set focus on target widget
                target_widget.setFocus(Qt.FocusReason.TabFocusReason)
                
                # Update focused line for borders on BOTH widgets
                current_widget.set_focused_line(current_line)
                target_widget.set_focused_line(current_line)
                
                return True  # Event handled, don't propagate
        
        # For all other events, use default handling
        return super().event(event)
    
    def toggle_diff_map(self):
        """Toggle diff map visibility"""
        if self.diff_map_visible:
            self.diff_map.hide()
            self.diff_map_visible = False
        else:
            self.diff_map.show()
            self.diff_map_visible = True
    
    def toggle_line_numbers(self):
        """Toggle line number visibility"""
        if self.line_numbers_visible:
            self.base_line_area.hide()
            self.modified_line_area.hide()
            self.line_numbers_visible = False
        else:
            self.base_line_area.show()
            self.modified_line_area.show()
            self.line_numbers_visible = True
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        key = event.key()
        modifiers = event.modifiers()
        
        # Check for Alt+H to toggle diff map
        if key == Qt.Key.Key_H and modifiers & Qt.KeyboardModifier.AltModifier:
            self.toggle_diff_map()
            return
        
        # Check for Alt+L to toggle line numbers
        if key == Qt.Key.Key_L and modifiers & Qt.KeyboardModifier.AltModifier:
            self.toggle_line_numbers()
            return
        
        # Check for Ctrl+S
        if key == Qt.Key.Key_S and modifiers & Qt.KeyboardModifier.ControlModifier:
            self.show_search_dialog()
            return
        
        if key == Qt.Key.Key_Tab:
            
            # Get which widget currently has focus
            if self.base_text.hasFocus():
                current_widget = self.base_text
                target_widget = self.modified_text
            elif self.modified_text.hasFocus():
                current_widget = self.modified_text
                target_widget = self.base_text
            else:
                self.base_text.setFocus()
                return
            
            # Get current line
            current_line = current_widget.textCursor().blockNumber()
            
            # Move target widget's cursor to same line
            block = target_widget.document().findBlockByNumber(current_line)
            if block.isValid():
                cursor = target_widget.textCursor()
                cursor.setPosition(block.position())
                target_widget.setTextCursor(cursor)
            
            # Set focus on target widget
            target_widget.setFocus(Qt.FocusReason.TabFocusReason)
            
            # Update focused line for borders on BOTH widgets
            current_widget.set_focused_line(current_line)
            target_widget.set_focused_line(current_line)
            
        elif key == Qt.Key.Key_N:
            self.next_change()
        elif key == Qt.Key.Key_P:
            self.prev_change()
        elif key == Qt.Key.Key_C:
            self.center_current_region()
        elif key == Qt.Key.Key_T:
            self.current_region = 0
            if self.change_regions:
                self.center_on_line(0)
            self.update_status()
        elif key == Qt.Key.Key_B:
            if self.change_regions:
                self.current_region = len(self.change_regions) - 1
                self.center_on_line(len(self.base_display) - 1)
            self.update_status()
        elif key == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
    
    def resizeEvent(self, event):
        """Handle window resize"""
        super().resizeEvent(event)
        self.update_diff_map_viewport()
    
    def run(self):
        """Run the application"""
        self.show()
        sys.exit(self._app.exec())


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print("Usage: python diff_viewer_qt.py <base_file> <modified_file> <note_file> <description_file>")
        print("  note_file: path to note file or 'None' for no notes")
        print("  description_file: path to description file or 'None' for no description")
        sys.exit(1)
    
    base_file = sys.argv[1]
    modified_file = sys.argv[2]
    note_file = sys.argv[3] if sys.argv[3] != 'None' else None
    description_file = sys.argv[4] if sys.argv[4] != 'None' else None
    
    try:
        with open(base_file, 'r') as f:
            base_lines = f.readlines()
        with open(modified_file, 'r') as f:
            modified_lines = f.readlines()
        
        viewer = DiffViewer(base_file, modified_file, note_file, description_file)
        viewer.run()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
