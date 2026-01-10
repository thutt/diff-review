# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#

from PyQt6.QtWidgets import QTextEdit, QApplication
from PyQt6.QtGui import QFont, QTextCursor, QFontMetrics, QTextCharFormat, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from tab_content_base import TabContentBase
import pyte
import struct
import fcntl
import termios
import os
import select
import signal


class CompatScreen(pyte.Screen):
    def select_graphic_rendition(self, *attrs, **kwargs):
        kwargs.pop('private', None)
        super().select_graphic_rendition(*attrs)


class TerminalTheme:
    SOLARIZED_DARK = ("solarized_dark", "#002b36", "#839496")
    MONOKAI = ("monokai", "#272822", "#F8F8F2")
    DRACULA = ("dracula", "#282a36", "#f8f8f2")
    GRUVBOX_DARK = ("gruvbox_dark", "#282828", "#ebdbb2")
    NORD = ("nord", "#2e3440", "#d8dee9")
    TOMORROW_NIGHT = ("tomorrow_night", "#1d1f21", "#c5c8c6")
    CLASSIC_GREEN = ("classic_green", "#000000", "#00ff00")
    CLASSIC_AMBER = ("classic_amber", "#000000", "#ffb000")
    LIGHT = ("light", "#ffffff", "#000000")

    @staticmethod
    def get_theme(theme_name):
        themes = {
            "solarized_dark": TerminalTheme.SOLARIZED_DARK,
            "monokai": TerminalTheme.MONOKAI,
            "dracula": TerminalTheme.DRACULA,
            "gruvbox_dark": TerminalTheme.GRUVBOX_DARK,
            "nord": TerminalTheme.NORD,
            "tomorrow_night": TerminalTheme.TOMORROW_NIGHT,
            "classic_green": TerminalTheme.CLASSIC_GREEN,
            "classic_amber": TerminalTheme.CLASSIC_AMBER,
            "light": TerminalTheme.LIGHT,
        }
        return themes.get(theme_name, TerminalTheme.CLASSIC_GREEN)


def map_pyte_color_to_qcolor(color_name, is_background):
    color_map = {
        "black": (0, 0, 0),
        "red": (205, 49, 49),
        "green": (13, 188, 121),
        "brown": (229, 229, 16),
        "blue": (36, 114, 200),
        "magenta": (188, 63, 188),
        "cyan": (17, 168, 205),
        "white": (229, 229, 229),
        "brightblack": (102, 102, 102),
        "brightred": (241, 76, 76),
        "brightgreen": (35, 209, 139),
        "brightyellow": (245, 245, 67),
        "brightblue": (59, 142, 234),
        "brightmagenta": (214, 112, 214),
        "brightcyan": (41, 184, 219),
        "brightwhite": (255, 255, 255),
    }

    if isinstance(color_name, str):
        if color_name == "default":
            return None
        if len(color_name) == 6:
            try:
                r = int(color_name[0:2], 16)
                g = int(color_name[2:4], 16)
                b = int(color_name[4:6], 16)
                return QColor(r, g, b)
            except ValueError:
                pass
        rgb = color_map.get(color_name)
        if rgb:
            return QColor(*rgb)
        return None
    elif isinstance(color_name, int):
        if color_name < 16:
            names = ["black", "red", "green", "brown", "blue", "magenta", "cyan", "white",
                     "brightblack", "brightred", "brightgreen", "brightyellow",
                     "brightblue", "brightmagenta", "brightcyan", "brightwhite"]
            if color_name < len(names):
                rgb = color_map.get(names[color_name])
                if rgb:
                    return QColor(*rgb)
        elif color_name < 232:
            color_name -= 16
            r = (color_name // 36) * 51
            g = ((color_name % 36) // 6) * 51
            b = (color_name % 6) * 51
            return QColor(r, g, b)
        else:
            gray = 8 + (color_name - 232) * 10
            return QColor(gray, gray, gray)

    return None


class TerminalWidget(QTextEdit, TabContentBase):
    process_exited = pyqtSignal(int)

    ESCAPE_PREFIX_TIMEOUT = 2000  # milliseconds
    ESCAPE_PREFIX_BORDER_COLOR = "#4499DD"  # Medium bright blue

    def __init__(self, parent, theme, pathname):
        super().__init__(parent)
        self.current_font_size = 10
        self.theme = TerminalTheme.get_theme(theme)
        self.pathname = pathname
        self.command_buffer = ""
        self.history = []
        self.history_index = -1
        self.screen = CompatScreen(80, 24)
        self.stream = pyte.Stream(self.screen)
        self.master_fd = None
        self.updating_display = False
        self.process_pid = None
        self.timer = None
        self.escape_prefix_active = False
        self.escape_prefix_timer = None
        self.setup_terminal()

    def setup_terminal(self):
        self.setReadOnly(False)
        font = QFont("Courier New", self.current_font_size)
        self.setFont(font)
        theme_name, bg_color, fg_color = self.theme
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg_color};
                color: {fg_color};
            }}
        """)
        self.setCursorWidth(10)

    def increase_font_size(self):
        """Increase terminal font size"""
        self.current_font_size = min(self.current_font_size + 1, 24)
        font = QFont("Courier New", self.current_font_size)
        self.setFont(font)
        self.update_terminal_size()

    def decrease_font_size(self):
        """Decrease terminal font size"""
        self.current_font_size = max(self.current_font_size - 1, 6)
        font = QFont("Courier New", self.current_font_size)
        self.setFont(font)
        self.update_terminal_size()

    def reset_font_size(self):
        """Reset terminal font size to default (10pt)"""
        self.current_font_size = 10
        font = QFont("Courier New", self.current_font_size)
        self.setFont(font)
        self.update_terminal_size()

    def set_escape_prefix_active(self, active):
        """Set the escape prefix state and update border visual feedback"""
        self.escape_prefix_active = active

        if active:
            # Show colored border
            theme_name, bg_color, fg_color = self.theme
            self.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {bg_color};
                    color: {fg_color};
                    border: 3px solid {self.ESCAPE_PREFIX_BORDER_COLOR};
                }}
            """)
            # Start timeout timer
            if self.escape_prefix_timer is None:
                self.escape_prefix_timer = QTimer(self)
                self.escape_prefix_timer.setSingleShot(True)
                self.escape_prefix_timer.timeout.connect(self._on_escape_prefix_timeout)
            self.escape_prefix_timer.start(self.ESCAPE_PREFIX_TIMEOUT)
        else:
            # Restore normal border
            theme_name, bg_color, fg_color = self.theme
            self.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {bg_color};
                    color: {fg_color};
                }}
            """)
            # Stop timer if running
            if self.escape_prefix_timer is not None:
                self.escape_prefix_timer.stop()

    def is_escape_prefix_active(self):
        """Return whether the escape prefix is currently active"""
        return self.escape_prefix_active

    def _on_escape_prefix_timeout(self):
        """Handle escape prefix timeout - revert border"""
        self.set_escape_prefix_active(False)

    def has_unsaved_changes(self):
        """Terminal has no concept of unsaved changes"""
        return False

    def is_terminal_widget(self):
        """This is a terminal-based widget"""
        return True

    def focus_content(self):
        """Set Qt focus to this terminal widget"""
        self.setFocus()

    def get_process_pid(self):
        """Return the child process ID"""
        return self.process_pid

    def centerCursor(self):
        """External editors manage their own cursor positioning"""
        pass

    def search_content(self, search_text, case_sensitive, regex, search_base=True, search_modi=True):
        """Terminal content is not searchable via the normal search mechanism"""
        return []

    def quit_editor(self):
        """Send quit command to editor - must be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement quit_editor()")

    def closeEvent(self, event):
        """Handle tab close - save and quit if process still alive"""
        if self.process_pid is not None:
            try:
                # Check if process is still alive
                os.kill(self.process_pid, 0)
                # Process is alive - user closed tab, not editor
                # Save and quit cleanly
                self.save_buffer()
                self.quit_editor()
                import time
                time.sleep(0.1)  # Give editor time to exit
                # If process is still running, kill it
                try:
                    os.kill(self.process_pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            except ProcessLookupError:
                # Process already dead - user closed from within editor
                pass
            except OSError:
                pass
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
        super().closeEvent(event)

    def set_master_fd(self, fd):
        self.master_fd = fd
        self.update_terminal_size()
        rows, cols = self.calculate_terminal_size()

    def calculate_terminal_size(self):
        metrics = QFontMetrics(self.font())
        char_width = metrics.horizontalAdvance('M')
        char_height = metrics.height()

        width = self.viewport().width()
        height = self.viewport().height()

        cols = max(1, width // char_width)
        rows = max(1, height // char_height)

        return rows, cols

    def update_terminal_size(self):
        if self.master_fd is None:
            return

        rows, cols = self.calculate_terminal_size()

        if rows != self.screen.lines or cols != self.screen.columns:
            self.screen.resize(rows, cols)

            winsize = struct.pack('HHHH', rows, cols, 0, 0)
            try:
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
                if self.process_pid:
                    os.kill(self.process_pid, signal.SIGWINCH)
            except OSError:
                pass

    def resizeEvent(self, event):
        if not self.updating_display:
            super().resizeEvent(event)
            self.update_terminal_size()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(100, self.update_terminal_size)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            clipboard = QApplication.clipboard()
            text = clipboard.text(QApplication.clipboard().Mode.Selection)
            if text:
                self.insertPlainText(text)
            event.accept()
        else:
            super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.process_command()
        elif event.key() == Qt.Key.Key_Up:
            self.navigate_history(-1)
        elif event.key() == Qt.Key.Key_Down:
            self.navigate_history(1)
        else:
            super().keyPressEvent(event)

    def process_command(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self.insertPlainText("\n")
        command = self.command_buffer.strip()
        if command:
            self.history.append(command)
            self.history_index = -1
        self.command_buffer = ""

    def navigate_history(self, direction):
        if not self.history:
            return
        new_index = self.history_index + direction
        if -len(self.history) <= new_index < 0:
            self.history_index = new_index
            self.replace_current_line(self.history[self.history_index])

    def replace_current_line(self, text):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        self.insertPlainText(text)

    def append_text(self, text):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self.insertPlainText(text)

    def process_output(self, data):
        self.stream.feed(data)
        self.update_display()

    def update_display(self):
        self.updating_display = True

        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.removeSelectedText()

        theme_name, bg_color_str, fg_color_str = self.theme
        default_bg = QColor(bg_color_str)
        default_fg = QColor(fg_color_str)

        for y in range(self.screen.lines):
            if y > 0:
                cursor.insertText("\n")

            x = 0
            while x < self.screen.columns:
                char = self.screen.buffer[y][x]

                fg_color = map_pyte_color_to_qcolor(char.fg, False)
                bg_color = map_pyte_color_to_qcolor(char.bg, True)

                if fg_color is None:
                    fg_color = default_fg
                if bg_color is None:
                    bg_color = default_bg

                fmt = QTextCharFormat()
                fmt.setForeground(fg_color)
                fmt.setBackground(bg_color)

                if char.bold:
                    fmt.setFontWeight(700)
                if char.italics:
                    fmt.setFontItalic(True)
                if char.underscore:
                    fmt.setFontUnderline(True)
                if char.reverse:
                    fmt.setForeground(bg_color)
                    fmt.setBackground(fg_color)

                run_start = x
                run_text = char.data

                x += 1
                while x < self.screen.columns:
                    next_char = self.screen.buffer[y][x]
                    if (next_char.fg != char.fg or
                        next_char.bg != char.bg or
                        next_char.bold != char.bold or
                        next_char.italics != char.italics or
                        next_char.underscore != char.underscore or
                        next_char.reverse != char.reverse):
                        break
                    run_text += next_char.data
                    x += 1

                cursor.insertText(run_text, fmt)

        cursor.endEditBlock()
        self.update_cursor_position()
        self.updating_display = False

    def update_cursor_position(self):
        cursor_y = self.screen.cursor.y
        cursor_x = self.screen.cursor.x

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        for _ in range(cursor_y):
            cursor.movePosition(QTextCursor.MoveOperation.Down)

        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        for _ in range(cursor_x):
            cursor.movePosition(QTextCursor.MoveOperation.Right)

        self.setTextCursor(cursor)

    def read_output(self):
        if self.master_fd is None:
            return

        try:
            while True:
                ready, _, _ = select.select([self.master_fd], [], [], 0)
                if not ready:
                    break
                data = os.read(self.master_fd, 4096)
                if not data:
                    break
                text = data.decode('utf-8', errors='replace')
                self.process_output(text)
        except OSError:
            pass

        if self.process_pid:
            pid, status = os.waitpid(self.process_pid, os.WNOHANG)
            if pid != 0:
                self.timer.stop()
                exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
                self.process_output(f"\n[Process exited with code {exit_code}]\n")
                self.process_pid = None
                self.process_exited.emit(exit_code)
