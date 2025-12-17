# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#

from PyQt6.QtCore import QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import QApplication
from editerm import TerminalWidget
import pty
import os
import sys
import select
import signal
import fcntl
import termios


class EmacsWidget(TerminalWidget):
    def __init__(self, parent, theme, pathname):
        super().__init__(parent, theme, pathname)
        self.setup_emacs()

    def setup_emacs(self):
        master_fd, slave_fd = pty.openpty()
        self.set_master_fd(master_fd)

        pid = os.fork()
        if pid == 0:
            os.close(master_fd)
            os.setsid()
            fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)
            if slave_fd > 2:
                os.close(slave_fd)
            os.execvpe("emacs", ["emacs", "-nw",
                                 "--eval", "(global-font-lock-mode 1)",
                                 self.pathname ],
                       {**os.environ, "TERM": "xterm-256color"})

        os.close(slave_fd)
        self.process_pid = pid

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.read_output)
        self.timer.start(50)

    def center_cursor(self):
        """Center the cursor in the emacs window by sending Ctrl-G, Esc, x, recenter, Enter"""
        if self.master_fd is not None and self.process_pid is not None:
            os.write(self.master_fd, b'\x07')  # Ctrl-G
            os.write(self.master_fd, b'\x1b')  # Esc
            os.write(self.master_fd, b'x')     # x
            os.write(self.master_fd, b'recenter')  # recenter
            os.write(self.master_fd, b'\r')    # Enter

    def keyPressEvent(self, event):
        if self.master_fd is not None and self.process_pid is not None:
            modifiers = event.modifiers()
            text = event.text()
            key = event.key()

            if key == Qt.Key.Key_Up:
                os.write(self.master_fd, b'\x1b[A')
            elif key == Qt.Key.Key_Down:
                os.write(self.master_fd, b'\x1b[B')
            elif key == Qt.Key.Key_Right:
                os.write(self.master_fd, b'\x1b[C')
            elif key == Qt.Key.Key_Left:
                os.write(self.master_fd, b'\x1b[D')
            elif key == Qt.Key.Key_PageUp:
                os.write(self.master_fd, b'\x1b[5~')
            elif key == Qt.Key.Key_PageDown:
                os.write(self.master_fd, b'\x1b[6~')
            elif key == Qt.Key.Key_Backspace:
                os.write(self.master_fd, b'\x7f')
            elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                os.write(self.master_fd, b'\r')
            elif modifiers & Qt.KeyboardModifier.AltModifier and text:
                os.write(self.master_fd, b'\x1b')
                os.write(self.master_fd, text.encode('utf-8'))
            elif text:
                os.write(self.master_fd, text.encode('utf-8'))
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            if self.master_fd is not None and self.process_pid is not None:
                clipboard = QApplication.clipboard()
                text = clipboard.text(QApplication.clipboard().Mode.Selection)
                if text:
                    text = text.replace('\n', '\r')
                    os.write(self.master_fd, text.encode('utf-8'))
                    for _ in range(10):
                        self.read_output()
                event.accept()
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def closeEvent(self, event):
        if self.process_pid is not None:
            try:
                os.kill(self.process_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        if self.master_fd is not None:
            os.close(self.master_fd)
        super().closeEvent(event)
