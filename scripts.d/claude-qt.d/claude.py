# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import argparse
import json
import os
import PyQt6
import subprocess
import signal
import sys
import traceback

import diffmgr
import ui


def fatal(msg):
    print("fatal: %s" % (msg))
    sys.exit(1)


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
    o.add_argument("--base",
                   help     = ("Base file"),
                   action   = "store",
                   default  = None,
                   required = True,
                   dest     = "arg_base")

    o.add_argument("--modi",
                   help     = ("Modified file"),
                   action   = "store",
                   default  = None,
                   required = True,
                   dest     = "arg_modi")

    o = parser.add_argument_group("Note Taking Options")
    o.add_argument("--note-file",
                   help     = ("Name of note file."),
                   action   = "store",
                   default  = None,
                   required = False,
                   dest     = "arg_note")

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

    if options.arg_base is None:
        fatal("Base file must be specified.")

    if options.arg_modi is None:
        fatal("Modified file must be specified.")

    return options


def add_diff_to_viewer(desc, viewer):
    assert(len(desc.base_) == len(desc.modi_))

    for idx in range(0, len(desc.base_)):
        base = desc.base_[idx]
        modi = desc.modi_[idx]
        viewer.add_line(base, modi)  # Repeat for each line pair

    viewer.finalize() 
    viewer.apply_highlighting()


def generate(options, base, modi, note):
    application = PyQt6.QtWidgets.QApplication(sys.argv)
    viewer      = ui.DiffViewer(base, modi, note)

    desc = diffmgr.create_diff_descriptor(options.arg_verbose,
                                          options.arg_base,
                                          options.arg_modi)

    add_diff_to_viewer(desc, viewer)

    viewer.show()
    return application.exec()


def main():
    try:
        options = process_command_line()
        return generate(options, options.arg_base, options.arg_modi,
                        options.arg_note)

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
