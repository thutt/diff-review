# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import argparse
import os
import posixpath
import PyQt6
import subprocess
import signal
import sys
import traceback

import cmdlineargs
import color_palettes
import diffmgrng as diffmgr
import diff_viewer
import tab_manager_module


class FileButton (object):
    def __init__(self, options, action,
                 root_path, base_rel_path, modi_rel_path):
        self.options_       = options
        self.action_        = action
        self.root_path_     = root_path
        self.base_rel_path_ = base_rel_path
        self.modi_rel_path_ = modi_rel_path
        self.stats_display_ = True
        self.desc_          = None
        self.stats_tab_     = options.arg_tab_label_stats
        self.stats_file_    = options.arg_file_label_stats

    def set_stats_tab(self, state):
        assert(isinstance(state, bool))
        self.stats_tab_ = state

    def set_stats_file(self, state):
        assert(isinstance(state, bool))
        self.stats_file_ = state

    def modi_line_count(self):
        result = 0
        if self.desc_ is not None:
            result = self.desc_.modi_line_count()
        return result

    def add_line_count(self):
        result = 0
        if self.desc_ is not None:
            result = self.desc_.add_line_count()
        return result

    def del_line_count(self):
        result = 0
        if self.desc_ is not None:
            result = self.desc_.del_line_count()
        return result

    def chg_line_count(self):
        result = 0
        if self.desc_ is not None:
            result = self.desc_.chg_line_count()
        return result

    def generate_label(self, enable_stats):
        if self.desc_ is not None and enable_stats:
            stats =  ("[%d | A: %d / D: %d / C: %d]" %
                      (self.modi_line_count(),
                       self.add_line_count(),
                       self.del_line_count(),
                       self.chg_line_count()))
            label = "%s  %s" % (self.modi_rel_path_, stats)
        else:
            label = self.modi_rel_path_

        return label


    def button_label(self):
        label = self.generate_label(self.stats_file_)
        return label

    def tab_label(self):
        label = self.generate_label(self.stats_tab_)
        return label

    def make_viewer(self, base, modi, note):
        viewer = diff_viewer.DiffViewer(base, modi, note,
                                        self.options_.arg_max_line_length,
                                        show_diff_map(self.options_),
                                        show_line_numbers(self.options_))

        self.desc_ = diffmgr.create_diff_descriptor(self.options_.afr_,
                                                    self.options_.arg_verbose,
                                                    self.options_.intraline_percent_,
                                                    self.options_.arg_dump_ir,
                                                    base, modi)
        add_diff_to_viewer(self.desc_, viewer)

        return viewer

    def add_viewer(self, tab_widget):
        url = self.options_.arg_dossier_url
        if url is not None:
            root_path = url
        else:
            root_path = self.root_path_

        # Using posixpath here because:
        #
        #  Internally, Windows can use '/'.
        #  These relative pathnames can be converted into a URL, which
        #  requires '/'.
        #
        base   = posixpath.join(root_path, "base.d", self.base_rel_path_)
        modi   = posixpath.join(root_path, "modi.d", self.modi_rel_path_)
        viewer = self.make_viewer(base, modi, self.options_.arg_note)
        tab_widget.add_viewer(viewer)


def rsync_and_rerun(options):
    # This rsync system is not supported on Windows.
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),
                                              "..", ".."))

    rsyncer = os.path.join(parent_dir, "rsyncer")
    cmd     = [ rsyncer,
                "--fqdn", options.arg_fqdn,
                "--dossier", options.arg_dossier_path ]
    os.execv(rsyncer, cmd)


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


def generate(options, note):
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
                                                         options.selected_palette_,
                                                         options.arg_dump_ir,
                                                         options.arg_tab_label_stats,
                                                         options.arg_file_label_stats)

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
        options = cmdlineargs.process_command_line()
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
