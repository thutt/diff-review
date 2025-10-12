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
    import tkinter
except:
    print("fatal: Python3 'tkinter' module must be installed.")
    sys.exit(10)
import traceback


class TkInterface(object):
    def create_root_window(self, review_name):
        root = tkinter.Tk()
        root.title(review_name)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight = 1)
        root.columnconfigure(0, weight = 1)
        root.bind("<Escape>", lambda event: self.quit())
        return root

    def create_frame(self):
        frm = tkinter.Frame(self.root_)
        frm.grid(row = 0, column = 0, sticky = "nsew")
        frm.columnconfigure(0, weight = 1)
        frm.rowconfigure(0, weight = 1)
        return frm

    def execute_viewer(self, button, base, modi):
        viewer = self.viewer_.get()

        if viewer == "Emacs":
            cmd = [ "/usr/bin/emacs", # Assumes window-ed emacs.
                    "--eval", "(ediff-files \"%s\" \"%s\")" % (base, modi) ]
        elif viewer == "Meld":
            cmd = [ "/usr/bin/meld", base, modi ]
        elif viewer == "TkDiff":
            cmd = [ "/usr/bin/tkdiff", base, modi ]
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
            vimdiff = [ "/usr/bin/vimdiff" ]
            term    = os.getenv("TERM", None)
            if term is not None:
                vimdiff = [ term, "-e" ] + vimdiff
            cmd = vimdiff + [ base, modi ]
        elif viewer == "Claude-QT (experimental)":
            path   = os.path.split(sys.argv[0])
            claude = os.path.abspath(os.path.join(path[0], "..",
                                                  "claude-qt.d", "claude.py"))
            notes  = [ ]
            if self.options_.arg_claude_note_file is not None:
                notes = [ "--note", self.options_.arg_claude_note_file ]
            cmd = [ "python3", "-B", claude,
                    "--base", base,
                    "--modi", modi ] + notes
        elif viewer == "Claude (experimental)":
            path   = os.path.split(sys.argv[0])
            claude = os.path.abspath(os.path.join(path[0], "..",
                                                      "claude.d", "claude.py"))
            notes  = [ ]
            if self.options_.arg_claude_note_file is not None:
                notes = [ "--note", self.options_.arg_claude_note_file ]
            cmd = [ "python3", "-B", claude,
                    "--base", base,
                    "--modi", modi ] + notes
        else:
            raise NotImplementedError("Unsupported viewer: '%s'" %
                                      (self.viewer_.get()))

        subp = subprocess.Popen(cmd, start_new_session = True)
        self.subp_.append(subp)
        button.configure(bg=self.file_sel_bg_, fg=self.file_sel_fg_)

    def add_viewer_menu(self, menu):
        claude    = "Claude (experimental)"
        claude_qt = "Claude-QT (experimental)"
        viewer    = tkinter.Menu(menu, tearoff = 0)
        menu.add_cascade(label = "Viewer", menu = viewer)
        viewer.add_radiobutton(label = "Emacs"  , variable = self.viewer_)
        viewer.add_radiobutton(label = "Meld"   , variable = self.viewer_)
        viewer.add_radiobutton(label = "TkDiff" , variable = self.viewer_)
        viewer.add_radiobutton(label = "Vim"    , variable = self.viewer_)
        viewer.add_radiobutton(label = claude   , variable = self.viewer_)
        viewer.add_radiobutton(label = claude_qt, variable = self.viewer_)
        self.viewer_.set("TkDiff")     # Start with tkdiff.

    def create_menu_bar(self):
        menu = tkinter.Menu(self.frame_)
        self.add_viewer_menu(menu)
        self.add_notes_menu(menu)
        return menu

    def create_canvas(self):
        canvas = tkinter.Canvas(self.frame_)
        canvas.grid(row = 0, column = 0, sticky = "nsew")
        return canvas

    def create_scrollbar(self):
        sb = tkinter.Scrollbar(self.frame_,
                               orient  = "vertical",
                               command = self.canvas_.yview)
        sb.grid(row = 0, column = 1, sticky = "ns")
        self.canvas_.configure(yscrollcommand = sb.set)
        return sb

    def create_content_frame(self):
        cf = tkinter.Frame(self.canvas_)
        cf.bind("<Configure>",
                lambda e: self.canvas_.configure(scrollregion =
                                                 self.canvas_.bbox("all")))
        self.canvas_.create_window((0, 0), window = cf, anchor = "nw")
        return cf

    def quit(self):
        for subp in self.subp_:
            os.killpg(os.getpgid(subp.pid), signal.SIGTERM)
        self.root_.destroy()

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

    def unselect_button(self, button):
        button.configure(bg=self.file_uns_bg_, fg=self.file_uns_fg_)

    def add_button(self, row, action, base, modi, rel_modi):
        label  = tkinter.Label(self.content_, text=action)
        button = tkinter.Button(self.content_, text=rel_modi)

        lamb = lambda slf=self, button=button, \
                      b=base, m=modi: slf.execute_viewer(button, b, m)

        button.configure(command=lamb,
                         bg=self.file_uns_bg_, fg=self.file_uns_fg_)
        label.grid(column=0, row=row, sticky="nsew")
        button.grid(column=1, row=row, sticky="nsew")

        # Set right click to reset color.
        button.bind("<Button-3>",
                    lambda event, button = button: self.unselect_button(button))

    def add_quit(self, row):
        quit = tkinter.Button(self.frame_,
                              text    = "Quit",
                              command = self.quit)
        quit.configure(bg = "red", fg = "white")
        quit.grid(column = 1, row = row, sticky = "nsew")

    def add_notes_menu(self, menu):
        notes    = tkinter.Menu(menu, tearoff = 0)
        filename = self.notes_filename()
        menu.add_cascade(label = "Notes", menu = notes)

        # If ${EDITOR} is defined, put it first in the list, as that
        # will be the one someone wants to use most.
        editor = os.getenv("EDITOR", None)
        if editor is not None:
            notes.add_command(label   = "%s '%s'" % (editor, filename),
                              command = (lambda editor=editor,
                                         filename=filename:
                                         self.open_notes(editor, filename)))
            notes.add_separator()

        # Put vi and emacs, even if they duplicate the first entry.
        notes.add_command(label   = "emacs '%s'" % (filename),
                          command = (lambda editor="/usr/bin/emacs",
                                     filename=filename:
                                     self.open_notes(editor, filename)))
        notes.add_command(label   = "vi '%s'" % (filename),
                          command = (lambda editor="/usr/bin/vi",
                                     filename=filename:
                                     self.open_notes(editor, filename)))

    def size_window(self, rows, cols):
        char_pixel_width  =  8 * cols
        char_pixel_height = 40 * rows;
        Y                 = char_pixel_height
        X                 = 150 + char_pixel_width
        Y                 = min(1000, Y)
        X                 = min( 700, X)
        self.root_.geometry("%dx%d" % (X, Y))

    def mktree(self, p):
        if not os.path.exists(p):
            os.makedirs(p)


    def __init__(self, options, review_name, dossier):
        self.options_      = options
        self.notes_uns_bg_ = "grey"   # Color of Notes button.
        self.notes_uns_fg_ = "yellow"

        self.file_uns_bg_  = "grey92" # Color before file button poked.
        self.file_uns_fg_  = "black"

        self.file_sel_bg_  = "black"  # Color after file button poked.
        self.file_sel_fg_  = "white"
        self.dossier_      = dossier
        self.review_name_  = review_name
        self.subp_         = [ ]
        self.notes_        = None

        self.root_         = self.create_root_window(review_name)

        self.viewer_       = tkinter.StringVar() # Must be after root creation.
        self.frame_        = self.create_frame()
        self.menu_         = self.create_menu_bar()
        self.canvas_       = self.create_canvas()
        self.scrollbar_    = self.create_scrollbar()
        self.content_      = self.create_content_frame()
        self.root_.config(menu = self.menu_)


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

    formatter = argparse. RawTextHelpFormatter
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


    o = parser.add_argument_group("Claude Viewer Options")
    o.add_argument("--claude-note-file",
                   help     = ("Sets pathname to which Claude UI will write "
                               "notes.\n\n"
                               "Notes can be created by double-clicking a "
                               "single line of code,\n"
                               "or by highlighting a range of lines and using "
                               "the right-click\n"
                               "context menu, 'Add Note'.\n\n"
                               "The software will write the filename and line "
                               "contents to the\n"
                               "note file, allowing a reviewer to write review "
                               "comments using\n"
                               "the editor that makes them most productive, "
                               "concurrent with\n"
                               "diff viewing."),
                   action   = "store",
                   default  = None,
                   required = False,
                   dest     = "arg_claude_note_file")


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
    tkintf   = TkInterface(options, review_name, dossier)
    row      = 0                # Number of files.
    col      = 0                # Maximum pathname length, in chars
    base_dir = dossier["base"]
    modi_dir = dossier["modi"]
    for f in sorted(dossier['files'],
                    key=lambda item: item["modi_rel_path"]):
        action   = f["action"]
        rel_base = f["base_rel_path"]
        rel_modi = f["modi_rel_path"]

        base   = os.path.join(base_dir, rel_base)
        modi   = os.path.join(modi_dir, rel_modi)

        col = max(max(col, len(rel_base)), len(rel_modi))

        tkintf.add_button(row, action, base, modi, rel_modi)
        row = row + 1

    tkintf.add_quit(row)
    tkintf.size_window(row + 1, # Number of rows, including 'quit'.
                       col)
    tkintf.root_.mainloop()


def main():
    try:
        options = process_command_line()

        pathname = os.path.join(options.arg_review_dir,
                                options.arg_review_name, "diff.json")
        with open(pathname, "r") as fp:
            dossier = json.load(fp)

        generate(options, options.arg_review_name, dossier)

    except KeyboardInterrupt:
        return 0

    except NotImplementedError as exc:
        print("")
        print(traceback.format_exc())
        return 1;

    except Exception as e:
        print("internal error: unexpected exception\n%s" % str(e))
        print("")
        print(traceback.format_exc())

        return 1

    finally:
        subprocess.Popen([ "/usr/bin/stty", "sane" ])


if __name__ == "__main__":
    sys.exit(main())
