# Copyright (c) 2025, 2026  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import argparse
import json
import os
import sys

import color_palettes
import file_local
import file_url
import utils

home                = os.getenv("HOME", os.path.expanduser("~"))
default_review_dir  = os.path.join(home, "review")
default_review_name = "default"
color_palettes_dict = {
    "std"  : color_palettes.STANDARD_PALETTE.name,
    "cb"   : color_palettes.COLORBLIND_PALETTE.name,
    "dstd" : color_palettes.DARK_MODE_STANDARD_PALETTE.name,
    "dcb"  : color_palettes.DARK_MODE_COLORBLIND_PALETTE.name
}


def get_script_dir():
    return os.path.dirname(sys.argv[0])


def get_help_dir():
    return os.path.join(get_script_dir(), "help")


def get_keybinding_dir():
    return os.path.join(get_script_dir(), "keybindings.d")


def rsync_and_rerun(options):
    # This rsync system is not supported on Windows.
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),
                                              "..", ".."))

    rsyncer = os.path.join(parent_dir, "rsyncer")
    cmd     = [ rsyncer,
                "--fqdn", options.arg_fqdn,
                "--diff-dir", options.arg_dossier_path ]
    os.execv(rsyncer, cmd)


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


def configure_parser(ext_options):
    assert(isinstance(ext_options, list))
    description = ("""

claude facilitates viewing the contents of an already-generated diff.

""")

    help_epilog = ("""


Return Code:
  0       : success
  non-zero: failure
""")
    palette_choices = [ ]
    for f in color_palettes_dict.keys():
        palette_choices.append("%-5s : %s" % (f, color_palettes_dict[f]))

    formatter = argparse.RawTextHelpFormatter
    parser    = argparse.ArgumentParser(usage                 = None,
                                        formatter_class       = formatter,
                                        description           = description,
                                        epilog                = help_epilog,
                                        prog                  = "view-review-tabs",
                                        fromfile_prefix_chars = '@')

    dso = parser.add_argument_group("Diff Specification Options")
    dro = parser.add_argument_group("Diff Rendering Options")
    nto = parser.add_argument_group("Note Taking Options")
    aro = parser.add_argument_group("Automatic Reload Options")
    hco = parser.add_argument_group("HTTPS Certificate Options")
    dco = parser.add_argument_group("Display Characteristics Options")
    oo  = parser.add_argument_group("Output Options")
    ext = parser.add_argument_group("Extended Help Information")
    kbo = parser.add_argument_group("Keybinding Options")

    # Diff Specification Options
    d_group = dso.add_mutually_exclusive_group()
    d_group.add_argument("--diff-dir",
                         help     = regular_help(ext, ext_options, "diff-dir"),
                         action   = "store",
                         default  = None,
                         required = False,
                         metavar  = "<pathname>",
                         dest     = "arg_dossier_path")

    d_group.add_argument("--diff-url",
                         help     = regular_help(ext, ext_options, "diff-url"),
                         action   = "store",
                         default  = None,
                         required = False,
                         metavar  = "<URL>",
                         dest     = "arg_dossier_url")

    dso.add_argument("--keyring",
                     help     = ("Use system keyring to store credentials"),
                     action   = "store_true",
                     default  = True,
                     required = False,
                     dest     = "arg_keyring")

    dso.add_argument("--no-keyring", 
                     help     = ("Do not use system keyring to "
                                 "store credentials"),
                     action   = "store_false",
                     dest     = "arg_keyring")

    dso.add_argument("--fqdn",
                     help     = regular_help(ext, ext_options, "fqdn"),
                     action   = "store",
                     default  = None,
                     metavar  = "<FQDN>",
                     required = False,
                     dest     = "arg_fqdn")


    # Diff Rendering Options
    dro.add_argument("--intraline-percent",
                     help     = regular_help(ext, ext_options, "intraline-percent"),
                     action   = "store",
                     type     = int,
                     default  = 60,
                     metavar  = "<intraline percent>",
                     required = False,
                     dest     = "arg_intraline_percent")


    dro.add_argument("--max-line-length",
                     help     = regular_help(ext, ext_options, "max-line-length"),
                     action   = "store",
                     type     = int,
                     default  = 80,
                     required = False,
                     metavar  = "<integer>",
                     dest     = "arg_max_line_length")

    dro.add_argument("--palette",
                     help     = regular_help(ext, ext_options, "palette"),
                     action   = "store",
                     choices  = color_palettes_dict.keys(),
                     default  = None,
                     required = False,
                     metavar  = "<color palette name>",
                     dest     = "arg_palette")


    # Note Taking Options
    nto.add_argument("--note-file",
                     help     = regular_help(ext, ext_options, "note-file"),
                     action   = "store",
                     default  = None,
                     required = False,
                     metavar  = "<path of file to write>",
                     dest     = "arg_note")

    nto.add_argument("--note-editor",
                     help     = "An editor for writing review notes.",
                     action   = "store",
                     default  = None,
                     required = False,
                     choices  = ("emacs", "vim"),
                     metavar  = "<text editor for notes>",
                     dest     = "arg_note_editor")

    nto.add_argument("--note-editor-theme",
                     help     = "A color theme for the notes editor.",
                     action   = "store",
                     default  = "classic_amber",
                     required = False,
                     choices  = ("solarized_dark", "monokai", "dracula",
                                 "gruvbox_dark", "nord", "tomorrow_night",
                                 "classic_green", "classic_amber", "light"),
                     metavar  = "<text editor color theme>",
                     dest     = "arg_note_editor_theme")


    # Auto-reload Options
    aro.add_argument("--auto-reload",
                     help     = regular_help(ext, ext_options, "auto-reload"),
                     action   = "store_true",
                     default  = True,
                     required = False,
                     dest     = "arg_auto_reload")

    aro.add_argument("--no-auto-reload",
                     action   = "store_false",
                     required = False,
                     dest     = "arg_auto_reload")


    # HTTP Certificate Options
    hco.add_argument("--verify-https-cert",
                     help     = regular_help(ext, ext_options, "verify-https-cert"),
                     action   = "store_true",
                     default  = True,
                     required = False,
                     dest     = "arg_ack_insecure_cert")

    hco.add_argument("--no-verify-https-cert",
                     action   = "store_false",
                     required = False,
                     dest     = "arg_ack_insecure_cert")


    # Display Characteristics Options
    dco.add_argument("--display-n-lines",
                     help     = ("Set initial number of lines of source "
                                 "to show in viewer.\n[default: %(default)s]"),
                     action   = "store",
                     type     = int,
                     default  = 40,
                     required = False,
                     metavar  = "<integer>",
                     dest     = "arg_display_n_lines")

    dco.add_argument("--display-n-chars",
                     help     = ("Set initial number of characters per line "
                                 "to show in viewer.\n[default: %(default)s]"),
                     action   = "store",
                     type     = int,
                     default  = 80,
                     required = False,
                     metavar  = "<integer>",
                     dest     = "arg_display_n_chars")

    dco.add_argument("--show-diff-map",
                     help     = "Show diff map in viewer.",
                     action   = "store_true",
                     default  = True,
                     required = False,
                     dest     = "arg_diff_map")

    dco.add_argument("--no-show-diff-map",
                     help     = "Do not show diff map in viewer.",
                     action   = "store_false",
                     required = False,
                     dest     = "arg_diff_map")

    dco.add_argument("--show-trailing-whitespace",
                     help     = "Visually expose trailing whitespace.",
                     action   = "store_false", # Internal semantic is 'ignore'.
                     default  = False,
                     required = False,
                     dest     = "arg_ignore_trailing_whitespace")

    dco.add_argument("--no-show-trailing-whitespace",
                     help     = ("Do not visually expose trailing whitespace."),
                     action   = "store_true", # Internal semantic is 'ignore'.
                     required = False,
                     dest     = "arg_ignore_trailing_whitespace")

    dco.add_argument("--show-tab",
                     help     = ("Visually expose TABs."),
                     action   = "store_false", # Internal semantic is 'ignore'.
                     default  = False,
                     required = False,
                     dest     = "arg_ignore_tab")

    dco.add_argument("--no-show-tab",
                     help     = ("Do not visually expose TABs."),
                     action   = "store_true", # Internal semantic is 'ignore'.
                     required = False,
                     dest     = "arg_ignore_tab")

    dco.add_argument("--show-intraline",
                     help     = ("Visually show intraline changes."),
                     action   = "store_false", # Internal semantic is 'ignore'.
                     default  = False,
                     required = False,
                     dest     = "arg_ignore_intraline")

    dco.add_argument("--no-show-intraline",
                     help     = ("Do not visually show intraline changes."),
                     action   = "store_true", # Internal semantic is 'ignore'.
                     required = False,
                     dest     = "arg_ignore_intraline")

    dco.add_argument("--show-line-numbers",
                     help     = ("Show line numbers."),
                     action   = "store_true",
                     default  = True,
                     required = False,
                     dest     = "arg_line_numbers")

    dco.add_argument("--no-show-line-numbers",
                     help     = ("Do not show line numbers."),
                     action   = "store_false",
                     required = False,
                     dest     = "arg_line_numbers")

    dco.add_argument("--tab-label-show-stats",
                     help     = ("Show file stats in tab labels."),
                     action   = "store_true",
                     default  = True,
                     required = False,
                     dest     = "arg_tab_label_stats")

    dco.add_argument("--no-tab-label-show-stats",
                     help     = ("Do not show file stats in tab labels."),
                     action   = "store_false",
                     required = False,
                     dest     = "arg_tab_label_stats")

    dco.add_argument("--file-label-show-stats",
                     help     = ("Show stats in file labels in sidebar."),
                     action   = "store_true",
                     default  = False,
                     required = False,
                     dest     = "arg_file_label_stats")

    dco.add_argument("--no-file-label-show-stats",
                     help     = ("Do not show stats in file labels in sidebar."),
                     action   = "store_false",
                     required = False,
                     dest     = "arg_file_label_stats")

    # Keybinding Options
    kbo.add_argument("--keybindings",
                     help     = "Keybinding json file.",
                     action   = "store",
                     default  = os.path.join(get_keybinding_dir(),
                                             "default.json"),
                     required = False,
                     metavar  = "<keybinding json description pathname>",
                     dest     = "arg_keybindings")
                     

    # Output Options
    oo.add_argument("--dump-ir",
                    help     = argparse.SUPPRESS, # Internal use only.
                    action   = "store",
                    default  = None,
                    required = False,
                    metavar  = "<path of directory to write output>",
                    dest     = "arg_dump_ir")

    oo.add_argument("--verbose",
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
    opt_extended = [ ]
    parser  = configure_parser(opt_extended)
    options = parser.parse_args()

    process_extended_help_request(options, opt_extended)

    options.arg_intraline_percent = max(1, min(options.arg_intraline_percent,
                                               100))
    assert(1 <= options.arg_intraline_percent and
           options.arg_intraline_percent <= 100)
    options.intraline_percent_ = float(options.arg_intraline_percent) / 100.0

    options.arg_max_line_length = max(1, options.arg_max_line_length)

    if options.arg_dossier_url is not None:
        # Import fetchurl locally to avoid 'requests' module unless
        # '--url' is used.  The 'requests' module isn't always
        # installed, and there is no reason to need it to be installed
        # if it's not used.
        import fetchurl
        fetchurl.set_keyring_disabled(not options.arg_keyring)
        options.afr_ = file_url.URLFileAccess(options.arg_dossier_url,
                                              options.arg_ack_insecure_cert)

    else:
        # options.arg_dossier_path can be None.  When that is the
        # case, use the default review name.
        if options.arg_dossier_path is None:
            options.arg_dossier_path = os.path.join(default_review_dir,
                                                    default_review_name)
        elif options.arg_dossier_path.endswith("dossier.json"):
            utils.fatal("'%s' must not have the dossier name included." %
                        (options.arg_dossier_path))

        options.afr_ = file_local.LocalFileAccess(options.arg_dossier_path)

    options.selected_palette_ = None
    if options.arg_palette is not None:
        options.selected_palette_ = color_palettes_dict[options.arg_palette]

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
                print("")
                for l in dossier:
                    print(l)
                print("")
                utils.fatal("Unable to load dossier from:\n  '%s'" %
                            (options.arg_dossier_path))

    if options.arg_note_editor == "emacs":
        try:
            import pyte
        except Exception as exc:
            utils.fatal("Unable to import 'pyte'.  "
                        "It must be installed to use emacs.")
            
        try:
            import emacsterm
            options.editor_class_ = emacsterm.EmacsWidget
            options.editor_theme_ = options.arg_note_editor_theme
        except Exception as exc:
            utils.fatal("Unable to configure emacs.  Is pyte installed?")

    elif options.arg_note_editor == "vim":
        try:
            import pyte
        except Exception as exc:
            utils.fatal("Unable to import 'pyte'.  "
                        "It must be installed to use Vim.")
            
        try:
            import vimterm
            options.editor_class_ = vimterm.VimWidget
            options.editor_theme_ = options.arg_note_editor_theme
        except Exception as exc:
            utils.fatal("Unable to configure vim.  Is pyte installed?")
    else:
        options.editor_class_ = None
        options.editor_theme_ = None
        
    # inv: options.dossier_ is now a valid json dictionary.
    return options
