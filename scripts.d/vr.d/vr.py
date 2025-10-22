#!/usr/bin/env python3
# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import argparse
import json
import os
import subprocess
import signal
import sys

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget,
                                 QVBoxLayout, QHBoxLayout, QScrollArea,
                                 QPushButton, QLabel, QMenu, QMessageBox,
                                 QGridLayout, QFrame, QDialog, QTextEdit)
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QAction, QActionGroup, QPalette, QColor
except ImportError:
    print("fatal: Python3 'PyQt6' module must be installed.")
    print("Install with: pip install PyQt6")
    sys.exit(10)

import traceback

class CommitMsgDialog(QDialog):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Commit Messageg")
        self.resize(600, 300)

        # Layout
        layout = QVBoxLayout(self)

        # Text area
        text_box = QTextEdit(self)
        text_box.setPlainText("\n".join(items))
        text_box.setReadOnly(True)
        layout.addWidget(text_box)

        # Close button
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)  # closes the dialog
        layout.addWidget(close_button)


class QtInterface(QMainWindow):
    def __init__(self, options, review_name, dossier, commit_msg):
        # Initialize QApplication if it doesn't exist
        if QApplication.instance() is None:
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()

        super().__init__()

        self.options_ = options
        self.notes_uns_bg_ = "grey"     # Color of Notes button
        self.notes_uns_fg_ = "yellow"

        self.file_uns_bg_ = "white"    # Color before file button poked
        self.file_uns_fg_ = "black"

        self.file_sel_bg_ = "black"     # Color after file button poked
        self.file_sel_fg_ = "white"

        self.dossier_ = dossier
        self.review_name_ = review_name
        self.subp_ = []
        self.notes_ = None
        self.commit_msg_ = commit_msg
        self.viewer_name_ = "TkDiff"  # Default viewer

        self.emacs_ = find_executable([
            "/usr/bin/emacs",
            "/usr/local/bin/emacs",
            "/opt/homebrew/bin/emacs",
            "/opt/local/bin/emacs",
            "Applications/Emacs.app",
            # Windows usually has emacs version in pathname; punt.
        ])

        self.meld_ = find_executable([
            "/usr/bin/meld",
            "/usr/local/bin/meld",
            "/bin/meld",
            "/Applications/Meld.app",
            "/Applications/Meld.app/Contents/MacOS/Meld",
            "c:/program files (x86)/meld/meld.exe"
        ])

        self.tkdiff_ = find_executable([
            "/usr/bin/tkdiff",
            "/usr/local/bin/tkdiff",
            "/opt/local/bin/tkdiff",
            "/opt/homebrew/bin/tkdiff",
            "/opt/local/bin/tkdiff",
            "/bin/tkdiff",
        ])

        self.vim_ = find_executable([
            "/usr/bin/vimdiff",
            "/usr/local/bin/vimdiff",
            "/opt/homebrew/bin/vimdiff",
            "/opt/local/bin/vimdiff",
            # Windows usually has vim version in pathname; punt.
        ])

        self.create_ui(review_name)

    def create_ui(self, review_name):
        self.setWindowTitle(review_name)

        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create menu bar
        self.create_menu_bar()

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Create content widget with grid layout
        self.content_widget = QWidget()
        self.content_layout = QGridLayout(self.content_widget)
        self.content_layout.setSpacing(2)

        scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(scroll_area)

        # Keyboard shortcut for Escape
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.quit()
        else:
            super().keyPressEvent(event)

    def create_menu_bar(self):
        menubar = self.menuBar()

        # Viewer menu
        viewer_menu = menubar.addMenu("Viewer")
        self.viewer_group = QActionGroup(self)
        self.viewer_group.setExclusive(True)

        emacs  = "Emacs"
        meld   = "Meld"
        tkdiff = "TkDiff"
        vim    = "Vim"
        na     = "(not available)"
        if self.emacs_ is None:
            emacs = "%s %s" % (emacs, na)

        if self.meld_ is None:
            meld = "%s %s" % (meld, na)

        if self.tkdiff_ is None:
            tkdiff = "%s %s" % (tkdiff, na)

        if self.vim_ is None:
            vim = "%s %s" % (vim, na)

        viewers = [ emacs, tkdiff, meld, vim ]

        for viewer in viewers:
            action = QAction(viewer, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, v=viewer: self.set_viewer(v))
            action.setEnabled(na not in viewer)
            self.viewer_group.addAction(action)
            viewer_menu.addAction(action)

            if viewer == self.viewer_name_:
                action.setChecked(True)

        # Notes menu
        self.create_notes_menu(menubar)

    def set_viewer(self, viewer):
        self.viewer_name_ = viewer

    def create_notes_menu(self, menubar):
        notes_menu = menubar.addMenu("Notes")
        filename = self.notes_filename()

        # If ${EDITOR} is defined, put it first
        editor = os.getenv("EDITOR", None)
        if editor is not None:
            action = QAction(f"{editor} '{filename}'", self)
            action.triggered.connect(lambda: self.open_notes(editor, filename))
            notes_menu.addAction(action)
            notes_menu.addSeparator()

        # Add emacs and vi
        if self.emacs_ is not None:
            emacs_action = QAction(f"emacs '{filename}'", self)
            emacs_action.triggered.connect(lambda: self.open_notes(self.emacs_,
                                                                   filename))
            notes_menu.addAction(emacs_action)

        if self.vim_ is not None:
            vi_action = QAction(f"vim '{filename}'", self)
            vi_action.triggered.connect(lambda: self.open_notes(self.vim_,
                                                                filename))
            notes_menu.addAction(vi_action)

    def execute_viewer(self, button, base, modi):
        viewer = self.viewer_name_
        if viewer == "Emacs":
            cmd = [ self.emacs_, # Assumes windowed emacs.
                    "--eval", "(ediff-files \"%s\" \"%s\")" % (base, modi) ]
        elif viewer == "Meld":
            cmd = [ self.meld_, base, modi ]
        elif viewer == "TkDiff":
            cmd = [ self.tkdiff_, base, modi ]
        elif viewer == "Vim":
            # Vimdiff starts in the terminal from which this script
            # has been launched.  It also mucks with the stty
            # settings.
            #
            # If TERM is set, its value will be used to launch a new
            # terminal session for vimdiff.  It is assumed to use '-e'
            # as the argument to execute a program.  This terminal
            # will be closed when vr is closed, without affecting the
            # parent terminal.
            #
            # If TERM is not set, vimdiff will be launched directly.
            # A 'finally' clause in main() will ensure that the
            # terminal is returned to a sane state.
            #
            # Note: Only one vimdiff session at a time can be
            #       launched, due to the say that vim functions with
            #       'swp' files.
            #
            vimdiff = [ self.vim_ ]
            term    = os.getenv("TERM", None)
            if term is not None:
                vimdiff = [ term, "-e" ] + vimdiff
            cmd = vimdiff + [ base, modi ]
        else:
            raise NotImplementedError("Unsupported viewer: '%s'" %
                                      (viewer))

        subp = subprocess.Popen(cmd, start_new_session = True)
        self.subp_.append(subp)

        # Change button color to indicate it's been selected
        palette = button.palette()
        palette.setColor(QPalette.ColorRole.Button, QColor(self.file_sel_bg_))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(self.file_sel_fg_))
        button.setPalette(palette)
        button.setAutoFillBackground(True)

    def unselect_button(self, button):
        palette = button.palette()
        palette.setColor(QPalette.ColorRole.Button, QColor(self.file_uns_bg_))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(self.file_uns_fg_))
        button.setPalette(palette)
        button.setAutoFillBackground(True)

    def add_button(self, row, action, base, modi, rel_modi):
        label = QLabel(action)
        button = QPushButton(rel_modi)

        # Set initial button colors
        palette = button.palette()
        palette.setColor(QPalette.ColorRole.Button, QColor(self.file_uns_bg_))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(self.file_uns_fg_))
        button.setPalette(palette)
        button.setAutoFillBackground(True)

        # Connect button click
        button.clicked.connect(lambda: self.execute_viewer(button, base, modi))

        # Right-click to reset color
        button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        button.customContextMenuRequested.connect(lambda pos: self.unselect_button(button))

        self.content_layout.addWidget(label, row, 0)
        self.content_layout.addWidget(button, row, 1)

    def add_quit(self, row):
        quit_button = QPushButton("Quit")
        quit_button.clicked.connect(self.quit)

        # Set red background
        palette = quit_button.palette()
        palette.setColor(QPalette.ColorRole.Button, QColor("red"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("white"))
        quit_button.setPalette(palette)
        quit_button.setAutoFillBackground(True)

        self.content_layout.addWidget(quit_button, row, 1)

    def commit_msg_dialog(self, commit_path):
        commit_msg = [ ]
        with open(commit_path, "r") as fp:
            commit_msg.append(fp.read())

        self.commit_msg_dialog_ = CommitMsgDialog(commit_msg)
        self.commit_msg_dialog_.show()

    def add_commit_msg(self, row, commit_path):
        quit_button = QPushButton("Commit Message")
        quit_button.clicked.connect(lambda: self.commit_msg_dialog(commit_path))

        # Set red background
        palette = quit_button.palette()
        palette.setColor(QPalette.ColorRole.Button, QColor("blue"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("yellow"))
        quit_button.setPalette(palette)
        quit_button.setAutoFillBackground(True)

        self.content_layout.addWidget(quit_button, row, 0)

    def quit(self):
        for subp in self.subp_:
            try:
                os.killpg(os.getpgid(subp.pid), signal.SIGTERM)
            except:
                pass
        self.close()

    def notes_filename(self):
        filename = "%s.%s.%s" % (self.dossier_["user"],
                                 self.dossier_["name"],
                                 self.dossier_["time"])
        home     = os.getenv("HOME", os.path.expanduser("~"))
        notes    = os.path.join(home, "review", "notes", filename)
        return notes

    def create_notes_file(self):
        # Create a file that can be used to take notes on the review.
        notes = self.notes_filename()
        self.mktree(os.path.dirname(notes))

        if not os.path.exists(notes):
            with open(notes, "w") as fp:
                for f in sorted(self.dossier_['files'],
                                key=lambda item: item["modi_rel_path"]):
                    fp.write("%s:\n\n\n" % (f["modi_rel_path"]))

    def open_notes(self, editor, filename):
        self.create_notes_file()
        subp = subprocess.Popen([ editor, filename ],
                                start_new_session = True)
        # This subprocess is not put on the list of processes to kill
        # because the buffer may not be written to disk.

    def size_window(self, rows, cols):
        char_pixel_width  =  8 * cols
        char_pixel_height = 40 * rows
        Y                 = char_pixel_height
        X                 = 150 + char_pixel_width
        Y                 = min(1000, Y)
        X                 = min( 700, X)
        self.resize(X, Y)

    def mktree(self, p):
        if not os.path.exists(p):
            os.makedirs(p)

    def run(self):
        self.show()
        return self.app.exec()


def configure_parser():
    description = ("""

view-review facilitates viewing the contents of an already-generated diff.

""")

    help_epilog = ("""


Return Code:
  0       : success
  non-zero: failure
""")

    home       = os.getenv("HOME", os.path.expanduser("~"))
    review_dir = os.path.join(home, "review")

    formatter = argparse.RawTextHelpFormatter
    parser    = argparse.ArgumentParser(usage           = None,
                                        formatter_class = formatter,
                                        description     = description,
                                        epilog          = help_epilog,
                                        prog            = "diff-review")

    o = parser.add_argument_group("Diff Specification Options")
    o.add_argument("-R", "--review-directory",
                   help     = ("Specifies root directory where diffs will be "
                               "written."),
                   action   = "store",
                   default  = review_dir,
                   metavar  = "<pathname>",
                   required = False,
                   dest     = "arg_review_dir")

    o.add_argument("-r", "--review-name",
                   help     = ("Specifies the name of the diffs as they will "
                               "be written."),
                   action   = "store",
                   default  = "default",
                   metavar  = "<name>",
                   required = False,
                   dest     = "arg_review_name")

    o = parser.add_argument_group("Output Options")
    o.add_argument("--verbose",
                   help     = ("Turn on verbose diagnostic output"),
                   action   = "store_true",
                   default  = False,
                   required = False,
                   dest     = "arg_verbose")

    parser.add_argument("tail",
                        help  = "Command line tail",
                        nargs = "*")
    return parser


def process_command_line():
    parser  = configure_parser()
    options = parser.parse_args()

    options.review_dir = os.path.join(options.arg_review_dir,
                                      options.arg_review_name)
    options.review_base_dir = os.path.join(options.review_dir, "base.d")
    options.review_modi_dir = os.path.join(options.review_dir, "modi.d")

    return options


def generate(options, review_name, dossier):
    qt_intf     = QtInterface(options, review_name, dossier,
                              dossier['commit_msg'])
    row         = 0                # Number of files.
    col         = 0                # Maximum pathname length, in chars
    base_dir    = dossier["base"]
    modi_dir    = dossier["modi"]
    commit_path = dossier["commit_msg"] # Path of commit message.

    for f in sorted(dossier['files'],
                    key=lambda item: item["modi_rel_path"]):
        action   = f["action"]
        rel_base = f["base_rel_path"]
        rel_modi = f["modi_rel_path"]

        base     = os.path.join(base_dir, rel_base)
        modi     = os.path.join(modi_dir, rel_modi)

        col = max(max(col, len(rel_base)), len(rel_modi))

        qt_intf.add_button(row, action, base, modi, rel_modi)
        row = row + 1

    if commit_path is not None:
        qt_intf.add_commit_msg(row, commit_path)
    qt_intf.add_quit(row)
    qt_intf.size_window(row + 1, # Number of rows, including 'quit'.
                        col)

    return qt_intf.run()


def find_executable(search_paths):
    for pn in search_paths:
        if os.access(pn, os.X_OK):
            return pn
    return None


def restore_terminal():
    if os.name == "posix":      # Not POSIX -> no stty
        stty_path = find_executable([ "/bin/stty",
                                      "/usr/bin/stty" ])
        if stty_path is not None:
            subprocess.Popen([ stty_path, "sane" ])


def main():
    try:
        options = process_command_line()

        options.json_ = os.path.join(options.arg_review_dir,
                                     options.arg_review_name, "dossier.json")
        with open(options.json_, "r") as fp:
            dossier = json.load(fp)

        return generate(options, options.arg_review_name, dossier)

    except KeyboardInterrupt:
        return 0

    except NotImplementedError as exc:
        print("")
        print(traceback.format_exc())
        return 1

    except Exception as e:
        print("internal error: unexpected exception\n%s" % str(e))
        print("")
        print(traceback.format_exc())

        return 1

    finally:
        restore_terminal()


if __name__ == "__main__":
    sys.exit(main())
