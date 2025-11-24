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

import color_palettes
import diffmgrng as diffmgr
import diff_viewer
import file_local
import file_url
import tab_manager_module
import utils

home                = os.getenv("HOME", os.path.expanduser("~"))
default_review_dir  = os.path.join(home, "review")
default_review_name = "default"
color_palettes      = {
    "std"  : color_palettes.STANDARD_PALETTE.name,
    "cb"   : color_palettes.COLORBLIND_PALETTE.name,
    "dstd" : color_palettes.DARK_MODE_STANDARD_PALETTE.name,
    "dcb"  : color_palettes.DARK_MODE_COLORBLIND_PALETTE.name
}


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
        url = self.options_.arg_dossier_url
        if url is not None:
            root_path = url
        else:
            root_path = self.root_path_

        base   = os.path.join(root_path, "base.d", self.base_rel_path_)
        modi   = os.path.join(root_path, "modi.d", self.modi_rel_path_)
        viewer = make_viewer(self.options_, base, modi,
                             self.options_.arg_note)
        tab_widget.add_viewer(viewer)


def configure_parser():
    description = ("""

claude facilitates viewing the contents of an already-generated diff.

""")

    help_epilog = ("""


Return Code:
  0       : success
  non-zero: failure
""")
    palette_choices = [ ]
    for f in color_palettes.keys():
        palette_choices.append("%-5s : %s" % (f, color_palettes[f]))

    formatter = argparse.RawTextHelpFormatter
    parser    = argparse.ArgumentParser(usage                 = None,
                                        formatter_class       = formatter,
                                        description           = description,
                                        epilog                = help_epilog,
                                        prog                  = "view-review-tabs",
                                        fromfile_prefix_chars = '@')

    o = parser.add_argument_group("Remote Host Specification Options")
    o.add_argument("--fqdn",
                   help     = ("Fully qualified domain name of the host "
                               "where the diffs were created. "
                               "If the diffs are stored on another "
                               "system to which this system does not have "
                               "direct access specify this name of that system "
                               "with this option.  "
                               "This option option will cause another script "
                               "to be executed that will use rsync to copy "
                               "the files locally.  The current value of "
                               "${USER} will be used for the invocation of "
                               "rsync. [default: %(default)s]"),
                   action   = "store",
                   default  = None,
                   metavar  = "<FQDN of host>",
                   required = False,
                   dest     = "arg_fqdn")

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


    d_group = parser.add_mutually_exclusive_group()
    d_group.add_argument("--dossier",
                         help     = ("JSON file containing change information."),
                         action   = "store",
                         default  = None,
                         required = False,
                         metavar  = "<pathname>",
                         dest     = "arg_dossier_path")

    d_group.add_argument("--url",
                         help     = ("URL from which dossier & diffs can be retrived."),
                         action   = "store",
                         default  = None,
                         required = False,
                         metavar  = "<URL>",
                         dest     = "arg_dossier_url")

    o.add_argument("--intraline-percent",
                   help     = ("Integer percentage of similarity of two lines, "
                               "below which intraline diffs will not be "
                               "enabled. A higher value will reduce "
                               "incomprehensible intraline diff coloring.  A "
                               "lower value will present the lines as deleted "
                               "from the base file and added to the "
                               "modified file.  Value supplied is clamped to "
                               "the range [1, 100] (default: %(default)s)"),
                   action   = "store",
                   type     = int,
                   default  = 60,
                   metavar  = "<intraline percent>",
                   required = False,
                   dest     = "arg_intraline_percent")


    o.add_argument("--max-line-length",
                   help     = ("Set maximum line length of source code."),
                   action   = "store",
                   type     = int,
                   default  = 80,
                   required = False,
                   metavar  = "<integer>",
                   dest     = "arg_max_line_length")


    o = parser.add_argument_group("Automatic Reload Options")
    o.add_argument("--auto-reload",
                   help     = ("Automatically  reload changed files "
                               "into viewer."),
                   action   = "store_true",
                   default  = True,
                   required = False,
                   dest     = "arg_auto_reload")

    o.add_argument("--no-auto-reload",
                   help     = ("Do not automatically reload changed files "
                               "into viewer."),
                   action   = "store_false",
                   required = False,
                   dest     = "arg_auto_reload")


    o = parser.add_argument_group("HTTP Certificate Verification Options")
    o.add_argument("--verify-https-cert",
                         help     = ("Require acknowledgment that a URL signed "
                                     "with an unverified certificate is "
                                     "insecure."),
                         action   = "store_true",
                         default  = True,
                         required = False,
                         dest     = "arg_ack_insecure_cert")

    o.add_argument("--no-verify-https-cert",
                         help     = ("Do not prompt to acknowledge that URLs "
                                     "signed with unverified certificates is "
                                     "are insecure."),
                         action   = "store_false",
                         required = False,
                         dest     = "arg_ack_insecure_cert")


    o = parser.add_argument_group("Display Characteristics")
    o.add_argument("--display-n-lines",
                   help     = ("Set number of lines of source to show."),
                   action   = "store",
                   type     = int,
                   default  = 40,
                   required = False,
                   metavar  = "<integer>",
                   dest     = "arg_display_n_lines")

    o.add_argument("--display-n-chars",
                   help     = ("Set number of characters of source to show."),
                   action   = "store",
                   type     = int,
                   default  = 80,
                   required = False,
                   metavar  = "<integer>",
                   dest     = "arg_display_n_chars")

    o.add_argument("--palette",
                   help     = ("Set initial color palette to use when "
                               "displaying changes (choices: %(choices)s).\n" +
                               '\n'.join(palette_choices)),
                   action   = "store",
                   choices  = color_palettes.keys(),
                   default  = None,
                   required = False,
                   metavar  = "<color palette name>",
                   dest     = "arg_palette")

    o.add_argument("--show-diff-map",
                   help     = ("Show diff map between the two source "
                               "panes on startup."),
                   action   = "store_true",
                   default  = True,
                   required = False,
                   dest     = "arg_diff_map")

    o.add_argument("--no-show-diff-map",
                   help     = ("Do not show diff map between the two source "
                               "panes on startup."),
                   action   = "store_false",
                   required = False,
                   dest     = "arg_diff_map")

    o.add_argument("--show-trailing-whitespace",
                   help     = ("Show trailing whitespace found in "
                               "the file."),
                   action   = "store_false", # Internal semantic is 'ignore'.
                   default  = False,
                   required = False,
                   dest     = "arg_ignore_trailing_whitespace")

    o.add_argument("--no-show-trailing-whitespace",
                   help     = ("Do not show trailing whitespace found in "
                               "the file."),
                   action   = "store_true", # Internal semantic is 'ignore'.
                   required = False,
                   dest     = "arg_ignore_trailing_whitespace")

    o.add_argument("--show-tab",
                   help     = ("Display visually outstanding "
                               "TAB characters."),
                   action   = "store_false", # Internal semantic is 'ignore'.
                   default  = False,
                   required = False,
                   dest     = "arg_ignore_tab")

    o.add_argument("--no-show-tab",
                   help     = ("Do not display visually outstanding "
                               "TAB characters."),
                   action   = "store_true", # Internal semantic is 'ignore'.
                   required = False,
                   dest     = "arg_ignore_tab")

    o.add_argument("--show-intraline",
                   help     = ("Show intraline differences between "
                               "lines in the different panes."),
                   action   = "store_false", # Internal semantic is 'ignore'.
                   default  = False,
                   required = False,
                   dest     = "arg_ignore_intraline")

    o.add_argument("--no-show-intraline",
                   help     = ("Do not show intraline differences between "
                               "lines in the different panes."),
                   action   = "store_true", # Internal semantic is 'ignore'.
                   required = False,
                   dest     = "arg_ignore_intraline")

    o.add_argument("--show-line-numbers",
                   help     = ("When selected, the line numbers will be shown "
                               "on startup."),
                   action   = "store_true",
                   default  = True,
                   required = False,
                   dest     = "arg_line_numbers")

    o.add_argument("--no-show-line-numbers",
                   help     = ("When selected, the line numbers will be hidden "
                               "on startup."),
                   action   = "store_false",
                   required = False,
                   dest     = "arg_line_numbers")

    o = parser.add_argument_group("Note Taking Options")
    o.add_argument("--note-file",
                   help     = ("Name of note file to which notes will "
                               "be written."),
                   action   = "store",
                   default  = None,
                   required = False,
                   metavar  = "<path of file to write>",
                   dest     = "arg_note")

    o = parser.add_argument_group("Output Options")
    o.add_argument("--dump-ir",
                   help     = ("Dump internal representation of diff.  "
                               "Creates 'dr-base-<file>.text' and "
                               "'dr-modi-<file>.text' "
                               "in the specified directory."),
                   action   = "store",
                   default  = None,
                   required = False,
                   metavar  = "<path of directory to write output>",
                   dest     = "arg_dump_ir")

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


def rsync_and_rerun(options):
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),
                                              "..", ".."))

    rsyncer = os.path.join(parent_dir, "rsyncer")
    cmd     = [ rsyncer,
                "--fqdn", options.arg_fqdn,
                "--dossier", options.arg_dossier_path ]
    os.execv(rsyncer, cmd)


def process_command_line():
    parser  = configure_parser()
    options = parser.parse_args()

    options.diffs_root_dir_ = os.path.join(default_review_dir,
                                          default_review_name)
    if options.arg_dossier_url is not None:
        # Import fetchurl locally to avoid 'requests' module unless
        # '--url' is used.
        import fetchurl
        options.afr_ = file_url.URLFileAccess(options.arg_dossier_url,
                                              options.arg_ack_insecure_cert)
    else:
        review_dir   = os.path.join(options.arg_review_dir,
                                    options.arg_review_name)

        # Check for '--dossier', or use default dossier.
        if options.arg_dossier_path is None:
            options.arg_dossier_path = os.path.join(options.diffs_root_dir_)
        else:
            if options.arg_dossier_path.endswith("dossier.json"):
                utils.fatal("'%s' must not have the dossier name included." %
                            (options.arg_dossier_path))

            options.diffs_root_dir_  = options.arg_dossier_path
        options.afr_ = file_local.LocalFileAccess(options.arg_dossier_path)

    options.arg_intraline_percent = max(1, min(options.arg_intraline_percent,
                                               100))
    assert(1 <= options.arg_intraline_percent and
           options.arg_intraline_percent <= 100)
    options.intraline_percent_ = float(options.arg_intraline_percent) / 100.0

    if options.arg_fqdn is not None:
        rsync_and_rerun(options)
    else:
        dossier = options.afr_.read("dossier.json")
        if options.arg_dossier_url is not None:
            try:
                # Reading breaks the lines into an array of non-'\n'
                # terminated strings.
                #
                options.dossier_ = json.loads('\n'.join(dossier))
            except Exception as exc:
                options.dossier_ = None

            if options.dossier_ is None:
                print("")
                for l in dossier:
                    print(l)
                print("")
                utils.fatal("Unable to retrieve dossier from:\n  '%s'" %
                            (options.arg_dossier_url))
        else:
            # The dossier is now an array of lines with no linefeeds.  Put
            # it back together for json.loads() to parse.
            try:
                options.dossier_ = json.loads('\n'.join(dossier))
            except Exception as exc:
                utils.fatal("Unable to load dossier from:\n  '%s'" %
                            (options.arg_dossier_path))

    # inv: options.dossier_ is now a valid json dictionary.

    return options


def add_diff_to_viewer(desc, viewer):
    assert(len(desc.base_.lines_) == len(desc.modi_.lines_))

    # Set the changed region count from the diff descriptor
    viewer.set_changed_region_count(desc.base_.n_changed_regions_)

    for idx in range(0, len(desc.base_.lines_)):
        base = desc.base_.lines_[idx]
        modi = desc.modi_.lines_[idx]
        viewer.add_line(base, modi)

    viewer.finalize()


def show_diff_map(options):
    return options.arg_diff_map


def auto_reload_enabled(options):
    return options.arg_auto_reload


def show_line_numbers(options):
    return options.arg_line_numbers


def make_viewer(options, base, modi, note):
    viewer = diff_viewer.DiffViewer(base, modi, note,
                                    options.arg_max_line_length,
                                    show_diff_map(options),
                                    show_line_numbers(options))

    desc = diffmgr.create_diff_descriptor(options.afr_,
                                          options.arg_verbose,
                                          options.intraline_percent_,
                                          options.arg_dump_ir,
                                          base, modi)
    add_diff_to_viewer(desc, viewer)

    return viewer

def generate(options, note):
    selected_palette = None
    if options.arg_palette is not None:
        selected_palette = color_palettes[options.arg_palette]
        
    tab_widget  = tab_manager_module.DiffViewerTabWidget(options.afr_,
                                                         options.arg_display_n_lines,
                                                         options.arg_display_n_chars,
                                                         show_diff_map(options),
                                                         show_line_numbers(options),
                                                         auto_reload_enabled(options),
                                                         options.arg_ignore_tab,
                                                         options.arg_ignore_trailing_whitespace,
                                                         options.arg_ignore_intraline,
                                                         options.intraline_percent_,
                                                         selected_palette,
                                                         options.arg_dump_ir)


    if options.dossier_["commit_msg"] is not None:
        tab_widget.add_commit_msg(options.dossier_["commit_msg"])

    for f in options.dossier_["files"]:
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
        application = PyQt6.QtWidgets.QApplication(sys.argv)
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
