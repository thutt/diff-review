# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import argparse
import json
import os
import subprocess
import sys
import traceback

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
    return options


def execute(verbose, cmd):
    assert(isinstance(cmd, list))
    #    XXX find rsync in known locations: assert(os.path.exists(cmd[0]))

    if verbose:
        print("EXEC: '%s'" % (' '.join(cmd)))

    p = subprocess.Popen(cmd,
                         shell    = False,
                         errors   = "replace",
                         stdin    = subprocess.PIPE,
                         stdout   = subprocess.PIPE,
                         stderr   = subprocess.PIPE)
    (stdout, stderr) = p.communicate(None)

    # None is returned when no pipe is attached to stdout/stderr.
    if stdout is None:
        stdout = ''
    if stderr is None:
        stderr = ''
    rc = p.returncode

    if len(stdout) > 0:
        stdout = stdout[:-1].replace("\r", "").split("\n")
    else:
        stdout = [ ]
    if len(stderr) > 0:
        stderr = stderr[:-1].replace("\r", "").split("\n"),
    else:
        stderr = [ ]


    # stdout block becomes a list of lines.  For Windows, delete
    # carriage-return so that regexes will match '$' correctly.
    #
    return (stdout, stderr, rc)


def make_dest_directory(dirname):
    os.makedirs(dirname, exist_ok = True)


def rsync(options):
    home       = os.getenv("HOME", os.path.expanduser("~"))
    user       = os.getenv("USER", None)
    review_dir = os.path.join(home, "review")

    if user is None:
        fatal("Unable to get value of ${USER} from environment.")

    assert(options.arg_dossier[0] == '/') # Absolute path
    src_dir     = os.path.dirname(options.arg_dossier)
    review_name = os.path.basename(os.path.dirname(options.arg_dossier))
    review_dir  = os.path.dirname(src_dir)
    rel_dest    = os.path.dirname(src_dir)[1:]
    src         = "%s@%s:%s" % (user, options.arg_fqdn, src_dir)
    dst         = os.path.join(review_dir, options.arg_fqdn, rel_dest)
    cmd         = [ "rsync", "-avz", src, dst ]

    print("Notice:\n"
          "  The following command:\n"
          "\n"
          "     %s\n"
          "\n"
          "  is being executed.  It may ask for your password.\n"
          "\n" %
          (' '.join(cmd)))

    make_dest_directory(dst)
    (stdout, stderr, rc) = execute(options.arg_verbose, cmd)
    if rc == 0:
        for l in stdout:
            print(l)
    else:
        fatal("%s failed." % (' '.join(cmd)))

    options.new_dossier = os.path.join(dst, review_dir,
                                       review_name, "dossier.json")


def execute_vrt(options):
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),
                                              "..", ".."))
    vrt = os.path.join(parent_dir, "view-review-tabs")
    cmd = [ vrt,
            "--dossier", options.new_dossier ]
    os.execv(vrt, cmd)


def main():
    try:
        options = process_command_line()

        rsync(options)
        execute_vrt(options)
        return 0

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
