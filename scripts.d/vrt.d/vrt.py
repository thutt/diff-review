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
import diff_viewer
import tab_manager_module

home                = os.getenv("HOME", os.path.expanduser("~"))
default_review_dir  = os.path.join(home, "review")
default_review_name = "default"


class FileButton (object):
    def __init__(self, options, action,
                 root_path, base_rel_path, modi_rel_path):
        self.options_       = options
        self.action_        = action
        self.root_path_     = root_path
        self.base_rel_path_ = base_rel_path
        self.modi_rel_path_ = modi_rel_path

    def button_label(self):
        return self.modi_rel_path_

    def add_viewer(self, tab_widget):
        base = os.path.join(self.root_path_, "base.d", self.base_rel_path_)
        modi = os.path.join(self.root_path_, "modi.d", self.modi_rel_path_)
        viewer  = make_viewer(self.options_, base, modi,
                              self.options_.arg_note,
                              self.options_.dossier_["commit_msg"])
        tab_widget.add_viewer(viewer)


def fatal(msg):
    print("fatal: %s" % (msg))
    sys.exit(1)


def configure_parser():
    description = ("""

claude facilitates viewing the contents of an already-generated diff.

""")

    help_epilog = ("""


Return Code:
  0       : success
  non-zero: failure
""")
    formatter = argparse. RawTextHelpFormatter
    parser    = argparse.ArgumentParser(usage                 = None,
                                        formatter_class       = formatter,
                                        description           = description,
                                        epilog                = help_epilog,
                                        prog                  = "view-review-tabs",
                                        fromfile_prefix_chars = '@')

    o = parser.add_argument_group("Diff Specification Options")
    o.add_argument("-R", "--review-directory",
                   help     = ("Specifies root directory where diffs will be "
                               "written."),
                   action   = "store",
                   default  = default_review_dir,
                   metavar  = "<pathname>",
                   required = False,
                   dest     = "arg_review_dir")

    o.add_argument("-r", "--review-name",
                   help     = ("Specifies the name of the diffs as they will "
                               "be written."),
                   action   = "store",
                   default  = default_review_name,
                   metavar  = "<name>",
                   required = False,
                   dest     = "arg_review_name")

    o = parser.add_argument_group("Diff Specification Options")
    o.add_argument("--dossier",
                   help     = ("Json file containing change information"),
                   action   = "store",
                   default  = None,
                   required = False,
                   dest     = "arg_dossier")

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

    if options.arg_dossier is None:
        options.arg_dossier = os.path.join(default_review_dir,
                                           default_review_name,
                                           "dossier.json")
    if os.path.exists(options.arg_dossier):
        with open(options.arg_dossier, "r") as fp:
            options.dossier_ = json.load(fp)
    else:
        fatal("dossier '%s' does not exist." % (options.arg_dossier))

    return options


def add_diff_to_viewer(desc, viewer):
    assert(len(desc.base_) == len(desc.modi_))

    for idx in range(0, len(desc.base_)):
        base = desc.base_[idx]
        modi = desc.modi_[idx]
        viewer.add_line(base, modi)  # Repeat for each line pair

    viewer.finalize() 
    viewer.apply_highlighting()


def make_viewer(options, base, modi, note, commit_msg):
    viewer = diff_viewer.DiffViewer(base, modi, note, commit_msg)

    desc = diffmgr.create_diff_descriptor(options.arg_verbose,
                                          base, modi)
    add_diff_to_viewer(desc, viewer)

    return viewer

def generate(options, note):
    application = PyQt6.QtWidgets.QApplication(sys.argv)
    tab_widget  = tab_manager_module.DiffViewerTabWidget()

    if options.dossier_['commit_msg'] is not None:
        tab_widget.add_commit_msg(options.dossier_['commit_msg'])

    for f in options.dossier_['files']:
        file_inst = FileButton(options,
                               f["action"],
                               options.dossier_["root"],
                               f["base_rel_path"],
                               f["modi_rel_path"])
        
        tab_widget.add_file(file_inst)

    tab_widget.run()

    return 0


def main():
    try:
        options = process_command_line()

        return generate(options, options.arg_note)

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
