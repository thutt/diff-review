# Copyright (c) 2025, 2026  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import argparse
import os
import socket
import sys

import drgit
import drutil


def get_script_dir():
    return os.path.dirname(sys.argv[0])


def get_help_dir():
    return os.path.join(get_script_dir(), "help")


def uncommitted_review(options):
    return (options.arg_change_id is None and
            len(options.arg_change_append_id) == 0)


def process_extended_help_request(options, opt_extended):
    # If any extended help was requested, display its file and exit.
    for ext in opt_extended:
        topic    = ext[0]
        field    = ext[1]
        help_arg = getattr(options, field)

        if help_arg:
            help_dir = get_help_dir()
            fname = os.path.join(help_dir, "%s_extended.text" % (topic))
            with open(fname, "r") as fp:
                lines = fp.read()

            print("\n--%s\n" % (topic))
            for l in lines.splitlines():
                print("  %s" % (l))

            print("\n")
            sys.exit(0)


def regular_help(ext, extended, topic):
    assert(isinstance(topic, str))
    help_dir = get_help_dir()
    fname = os.path.join(help_dir, "%s.text" % (topic))
    assert(os.path.exists(fname))
    with open(fname, "r") as fp:
        lines = fp.read()

    ext_help = "--help-%s" % (topic)
    ext_dest = "arg_%s_ext_help" % (topic)

    extended.append((topic, ext_dest))

    lines += "See %s." % (ext_help)

    ext.add_argument(ext_help,
                     help     = argparse.SUPPRESS,
                     action   = "store_true",
                     default  = False,
                     required = False,
                     dest     = ext_dest)

    return lines


def read_description():
    help_dir    = get_help_dir()
    desc_name   = os.path.join(help_dir, "help-description.text")
    epilog_name = os.path.join(help_dir, "help-epilog.text")

    assert(os.path.exists(desc_name))
    assert(os.path.exists(epilog_name))

    with open(desc_name, "r") as fp:
        description = fp.read()

    with open(epilog_name, "r") as fp:
        epilog = fp.read()
    return (description, epilog)


def configure_parser(ext_options):
    assert(isinstance(ext_options, list))
    (description, epilog) = read_description()
    home       = os.getenv("HOME", os.path.expanduser("~"))
    review_dir = os.path.join(home, "review")
    formatter  = argparse. RawDescriptionHelpFormatter
    parser     = argparse.ArgumentParser(usage                 = None,
                                         formatter_class       = formatter,
                                         description           = description,
                                         epilog                = epilog,
                                         prog                  = "diff-review",
                                         fromfile_prefix_chars = '@')

    ext = parser.add_argument_group("Extended Help Information")

    o = parser.add_argument_group("Change Selection")
    g = o.add_mutually_exclusive_group()
    g.add_argument("-c", "--change",
                   help     = regular_help(ext, ext_options, "change"),
                   action   = "store",
                   default  = None,
                   metavar  = "<change id>",
                   required = False,
                   dest     = "arg_change_id")

    g.add_argument("--ca", "--change-append",
                   help     = regular_help(ext, ext_options, "change-append"),
                   action   = "append",
                   default  = [ ],
                   metavar  = "<change id>",
                   required = False,
                   dest     = "arg_change_append_id")


    o = parser.add_argument_group("SCM Control")
    o.add_argument("--scm",
                   help     = ("Choose the SCM that holds the data you want "
                               "to 'diff'.  "
                               "[default: %(default)s] "
                               "[choices: %(choices)s]"),
                   action   = "store",
                   default  = "git",
                   choices  = [ "git" ],
                   dest     = "arg_scm")

    o.add_argument("--git-path",
                   help     = ("Allows overriding default path for git. "
                               "[default: %(default)s]"),
                   action   = "store",
                   default  = "/usr/bin/git",
                   metavar  = "<path of git executable>",
                   required = False,
                   dest     = "arg_git_path")


    o = parser.add_argument_group("HTTP Specification Options")
    o.add_argument("--url-port",
                   help     = regular_help(ext, ext_options, "url-port"),
                   action   = "store",
                   default  = None,
                   metavar  = "<HTTP protocol port number>",
                   required = False,
                   dest     = "arg_url_port")

    o.add_argument("--url-R", "--url-review-directory",
                   help     = regular_help(ext, ext_options, "url-R"),
                   action   = "store",
                   default  = None,
                   metavar  = "<Web server review directory>",
                   required = False,
                   dest     = "arg_url_review_directory")

    o.add_argument("--url-server",
                   help     = regular_help(ext, ext_options, "url-server"),
                   action   = "store",
                   default  = socket.getfqdn(),
                   metavar  = "<FQDN of Web Server host>",
                   required = False,
                   dest     = "arg_url_server")


    o = parser.add_argument_group("Miscellaneous Options")
    o.add_argument("--threads",
                   help     = ("Overrides the default number of"
                               "threads used internally.  The default is based "
                               "on the number of CPUs the system has.  "
                               "[default: %(default)s]"),
                   action   = "store",
                   type     = int,
                   default  = 4 * os.cpu_count(),
                   metavar  = "<number-of-threads>",
                   required = False,
                   dest     = "arg_threads")

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
                   default  = "default",
                   metavar  = "<name>",
                   dest     = "arg_review_name")

    o.add_argument("--verbose",
                   help     = ("Turn on verbose diagnostic output"),
                   action   = "store_true",
                   default  = False,
                   required = False,
                   dest     = "arg_verbose")


    o = parser.add_argument_group("Git-specific Control")
    o.add_argument("--git-tracked",
                   help     = ("Set untracked file handling.  "
                               "'no' shows no untracked files.  "
                               "'all' shows all untracked files.  "
                               "[default: %(default)s] "
                               "[choices: %(choices)s]"),
                   action   = "store",
                   default  = "all",
                   required = False,
                   choices  = [ "no", "all" ],
                   dest     = "arg_git_untracked")


    d_group = parser.add_mutually_exclusive_group()
    d_group.add_argument("--url-https",
                         help     = ("Sets Web-based diffs protocol to HTTPS "
                                     "(default)."),
                         action   = "store_true",
                         default  = True,
                         required = False,
                         dest     = "arg_url_https")

    d_group.add_argument("--no-url-https",
                         help     = ("Sets Web-based diffs protocol to HTTP."),
                         action   = "store_false",
                         required = False,
                         dest     = "arg_url_https")


    parser.add_argument("tail",
                        help  = "Command line tail",
                        nargs = "*")
    return parser

def process_command_line():
    opt_extended = [ ]
    parser       = configure_parser(opt_extended)
    options      = parser.parse_args()

    process_extended_help_request(options, opt_extended)

    options.review_dir = os.path.join(options.arg_review_dir,
                                      options.arg_review_name)
    options.review_sha_dir  = os.path.join(options.review_dir, "sha.d")
    options.review_modi_dir = os.path.join(options.review_dir, "modi.d")

    if options.arg_scm == "git":
        if uncommitted_review(options):
            options.scm = drgit.GitStaged(options)
        else:
            options.scm = drgit.GitCommitted(options)
    else:
        drutil.fatal("Uhandled SCM instantiation.")

    if options.arg_url_port is None:
        # Set the URL port to the default only if it wasn't set on command line.
        options.arg_url_port = "80";
        if options.arg_url_https:
            options.arg_url_port = "443";

    drutil.mktree(options.review_dir)
    drutil.mktree(options.review_modi_dir) # XXX REMOVE. mktree used on copy file.

    return options
