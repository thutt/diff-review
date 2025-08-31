# Copyright (c) 2025  Logic Magicians Software.
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import argparse
import os

def configure_parser():
    description = ("""

diff-review facilitates viewing the contents of changes to the
contents of text files with a side-by-side diff utility such as
'tkdiff' or 'meld'.

There are four states in which a file can exist, and three for which
diffs can be generated.  They are as follows:

  o untracked  (All SCM)

    Untracked files are unknown to the SCM.  Diffs cannot be
    generated for untracked files.

    A diagnostic will be produced for each untracked file found in
    the source tree.

  o unstaged   (Git)

    An unstaged file is known to the SCM.  Diffs can be generated
    for unstaged changes.

    Diffs for unstaged changes will be made, in this order, against:

    + Staged changes to the same file.

    + If no changes to the same file are staged, against the most
      recently committed change to the same file on the same branch.
      If there is no such previous committed change, the diff will
      show as a new file.

  o staged   (Git)

    Staged changes are known to the SCM.  Diffs can be generated for
    staged changes.

    Diffs for staged changes will be made against the most recently
    committed change to the same file on the same branch.  If there is
    no such previous committed change, the diff will show as a new
    file.

  o committed  (All SCM)

    Committed changes are known to the SCM.  Diffs can be generated
    for committed changes.

    Diffs for committed changes will be made against the previous
    committed change to the same file on the same branch.  If there is
    no such previous committed change, the diff will show as a new
    file.


The tool will generate console output like the following:

    <DESCRIBE THE CONSOLE OUTPUT>


Implementation notes:

  o Unstaged files take precendence over staged files; simultaneously
    creating diffs for unstaged & staged changes to the same file is
    not supported.

  o An SCM that does not support unstaged and staged file states will
    not support those semantics.


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

    o = parser.add_argument_group("SCM Control")
    o.add_argument("-c",
                   help     = ("Select a change, using the SCM's change "
                               "identifier, that you want to 'diff'."),
                   action   = "append",
                   default  = [],
                   metavar  = "<change id>",
                   required = True,
                   dest     = "arg_changeid")

    o.add_argument("--scm",
                   help     = ("Choose the SCM that holds the data you want "
                               "to 'diff'."),
                   action   = "store",
                   default  = "git",
                   choices  = [ "git" ],
                   required = True,
                   dest     = "arg_scm")

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
