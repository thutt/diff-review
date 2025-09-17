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

    def create_canvas(self):
        canvas = tkinter.Canvas(self.frm_)
        canvas.grid(row = 0, column = 0, sticky = "nsew")
        return canvas

    def create_scrollbar(self):
        sb = tkinter.Scrollbar(self.frm_,
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
        self.root_.destroy()
        for subp in self.subp_:
            os.killpg(os.getpgid(subp.pid), signal.SIGTERM)


    def tkdiff(self, button, base, modi):
        subp = subprocess.Popen([ "/usr/bin/tkdiff", base, modi ],
                                start_new_session = True)
        self.subp_.append(subp)
        button.configure(bg="grey", fg="white")


    def meld(self, button, base, modi):
        subp = subprocess.Popen([ "/usr/bin/meld", base, modi ],
                                start_new_session = True)
        self.subp_.append(subp)
        button.configure(bg="grey", fg="white")


    def add_button(self, viewer, row, action, base, modi, rel_modi):
        label  = tkinter.Label(self.content_, text=action)
        button = tkinter.Button(self.content_, text=rel_modi)

        if viewer == "tkdiff":
            lamb = lambda slf=self,      \
                          button=button, \
                          b=base,        \
                          m=modi: slf.tkdiff(button, b, m)
        elif viewer == "meld":
            lamb = lambda slf=self,      \
                          button=button, \
                          b=base,        \
                          m=modi: slf.meld(button, b, m)
        else:
            raise NotImplementedError("Unrecognized viewer option, '%s'" %
                                      (viewer))

        button.configure(command=lamb)
        label.grid(column=0, row=row, sticky="nsew")
        button.grid(column=1, row=row, sticky="nsew")


    def add_quit(self, row):
        quit  = tkinter.Button(self.frm_,
                               text    = "Quit",
                               command = self.quit)
        quit.configure(bg = "red", fg = "white")
        quit.grid(column = 1, row = row, sticky = "nsew")

    def size_window(self, rows, cols):
        char_pixel_width  =  8 * cols
        char_pixel_height = 40 * rows;
        Y                 = char_pixel_height
        X                 = 150 + char_pixel_width
        Y                 = min(1000, Y)
        X                 = min( 700, X)
        self.root_.geometry("%dx%d" % (X, Y))

    def __init__(self, review_name):
        self.review_name_ = review_name
        self.root_        = self.create_root_window(review_name)
        self.frm_         = self.create_frame()
        self.canvas_      = self.create_canvas()
        self.scrollbar_   = self.create_scrollbar()
        self.content_     = self.create_content_frame()
        self.subp_        = [ ]


def configure_parser():
    description = ("""

view-review facilitates viewing the contents of changes an already-generated diff.


""")

    help_epilog = ("""


Return Code:
  0       : success
  non-zero: failure
""")

    home       = os.getenv("HOME", os.path.expanduser("~"))
    review_dir = os.path.join(home, "review")

    formatter = argparse. RawDescriptionHelpFormatter
    parser    = argparse.ArgumentParser(usage           = None,
                                        formatter_class = formatter,
                                        description     = description,
                                        epilog          = help_epilog,
                                        prog            = "diff-review")

    o = parser.add_argument_group("Viewer Options")
    o.add_argument("--viewer",
                   help     = ("Specifies which diff viewer to use."),
                   action   = "store",
                   default  = "tkdiff",
                   choices  = [ "tkdiff", "meld" ],
                   dest     = "arg_viewer")

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


def generate(viewer, review_name, dossier):
    tkintf   = TkInterface(review_name)
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

        tkintf.add_button(viewer, row, action, base, modi, rel_modi)
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

        generate(options.arg_viewer, options.arg_review_name, dossier)

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


if __name__ == "__main__":
    sys.exit(main())
