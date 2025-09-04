# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import argparse
import json
import os
import sys
try:
    import tkinter
except:
    print("fatal: Python3 'tkinter' module must be installed.")
    sys.exit(10)
import traceback

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

    o = parser.add_argument_group("Output Options")
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
                   default  = None,
                   metavar  = "<name>",
                   required = True,
                   dest     = "arg_review_name")

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


def tkdiff(button, base, modi):
    os.system("/usr/bin/tkdiff %s %s &" % (base, modi))
    button.configure(bg="grey", fg="white")


def generate(review_name, dossier):
    root = tkinter.Tk()
    root.title(review_name)
    frm  = tkinter.Frame(root)
    row  = 0
    frm.grid()

    base_dir = dossier["base"]
    modi_dir = dossier["modi"]
    for f in dossier['files']:
        action   = f["action"]
        rel_base = f["orig_rel_path"]
        rel_modi = f["curr_rel_path"]

        base   = os.path.join(base_dir, rel_base)
        modi   = os.path.join(modi_dir, rel_modi)

        label  = tkinter.Label(frm, text=action)
        button = tkinter.Button(frm, text=rel_modi)
        lamb   = lambda button=button, b=base, m=modi: tkdiff(button, b, m)
        button.configure(command=lamb)

        label.grid(column=0, row=row, sticky="nsew")
        button.grid(column=1, row=row, sticky="nsew")
        row = row + 1

    quit  = tkinter.Button(frm, text="Quit", command=root.destroy)
    quit.configure(bg="red", fg="white")
    quit.grid(column=1, row=row, sticky="nsew")

    root.mainloop()


def main():
    try:
        options = process_command_line()

        pathname = os.path.join(options.arg_review_dir,
                                options.arg_review_name, "diff.json")
        with open(pathname, "r") as fp:
            dossier = json.load(fp)

        generate(options.arg_review_name, dossier)

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
