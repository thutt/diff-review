# Copyright (c) 2025  Logic Magicians Software.
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import argparse
import os

def configure_parser():
    description = ("""

Return Code:
  0       : success
  non-zero: failure
""")

    home       = os.getenv("HOME", os.path.expanduser("~"))
    review_dir = os.path.join(home, "review")

    formatter = argparse.ArgumentDefaultsHelpFormatter
    parser    = argparse.ArgumentParser(usage           = None,
                                        formatter_class = formatter,
                                        description     = description,
                                        prog            = "diff-review")

    o = parser.add_argument_group("SCM Control")
    o.add_argument("-c",
                   help     = ("Select change(s) you want to 'diff'.  "
                               "For Git, each argument can be a value "
                               "that can be used with 'git rev-parse'."),
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
