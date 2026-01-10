# Copyright (c) 2026  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import posixpath

import diffmgrng as diffmgr
import diff_viewer
import tab_manager_module

# Diff mode constants for staged files.
# These control which pair of files to compare.
DIFF_MODE_BASE_MODI  = 0  # HEAD vs Working (default)
DIFF_MODE_BASE_STAGE = 1  # HEAD vs Staged
DIFF_MODE_STAGE_MODI = 2  # Staged vs Working

class FileButtonBase(object):
    def __init__(self, options, action, root_path):
        self.options_            = options
        self.action_             = action
        self.root_path_          = root_path

        self.desc_               = None
        self.stats_tab_          = options.arg_tab_label_stats
        self.stats_file_         = options.arg_file_label_stats

    def set_stats_tab(self, state):
        assert(isinstance(state, bool))
        self.stats_tab_ = state

    def set_stats_file(self, state):
        assert(isinstance(state, bool))
        self.stats_file_ = state

    # Modified file line count.
    #
    # The line counts of the other files are immaterial, because this
    # is the file that will be commited..
    #
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


class FileButton(FileButtonBase): # Committed & not-unstaged uncommited.
    def __init__(self, options, action,
                 root_path,
                 base_dir_rel_path, base_file_rel_path,
                 modi_dir_rel_path, modi_file_rel_path):
        super().__init__(options, action, root_path)

        self.base_dir_rel_path_  = base_dir_rel_path
        self.base_rel_path_      = base_file_rel_path

        self.modi_dir_rel_path_  = modi_dir_rel_path
        self.modi_rel_path_      = modi_file_rel_path

    def modi_file_rel_path(self):
        # Return source-tree relative path.
        return self.modi_rel_path_

    def base_file_rel_path(self):
        # Return source-tree relative path.
        return self.base_rel_path_

    def generate_label(self, enable_stats):
        if self.desc_ is not None and enable_stats:
            stats =  ("[%d | A: %d / D: %d / C: %d]" %
                      (self.modi_line_count(),
                       self.add_line_count(),
                       self.del_line_count(),
                       self.chg_line_count()))
            label = "%s  %s" % (self.modi_file_rel_path(), stats)
        else:
            label = self.modi_file_rel_path()

        return label


    def button_label(self):
        label = self.generate_label(self.stats_file_)
        return label

    def tab_label(self):
        label = self.generate_label(self.stats_tab_)
        return label

    def tab_relpath(self):
        return self.modi_file_rel_path()

    def make_viewer(self, base, modi):
        viewer = diff_viewer.DiffViewer(base, modi,
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
        base   = posixpath.join(root_path,
                                self.base_dir_rel_path_,
                                self.base_file_rel_path())
        modi   = posixpath.join(root_path,
                                self.modi_dir_rel_path_,
                                self.modi_file_rel_path())
        viewer = self.make_viewer(base, modi)
        tab_widget.add_viewer(viewer)


class FileButtonUnstaged(FileButtonBase):
    def __init__(self, options, action,
                 root_path,
                 base_dir_rel_path, base_file_rel_path,
                 modi_dir_rel_path, modi_file_rel_path,
                 stage_dir_rel_path, stage_file_rel_path):
        super().__init__(options, action, root_path)

        self.base_dir_rel_path_  = base_dir_rel_path
        self.base_rel_path_      = base_file_rel_path

        self.modi_dir_rel_path_  = modi_dir_rel_path
        self.modi_rel_path_      = modi_file_rel_path

        self.stage_dir_rel_path_ = stage_dir_rel_path
        self.stage_rel_path_     = stage_file_rel_path

    def has_staged(self):
        return self.stage_rel_path_ is not None

    def get_diff_paths(self, mode, root_path):
        # Returns (base_path, modi_path) for the given diff mode.
        # root_path is the resolved root (URL or local path).
        if mode == DIFF_MODE_BASE_STAGE:
            base_dir = self.base_dir_rel_path_
            base_rel = self.base_file_rel_path()
            modi_dir = self.stage_dir_rel_path_
            modi_rel = self.stage_file_rel_path()
        elif mode == DIFF_MODE_STAGE_MODI:
            base_dir = self.stage_dir_rel_path_
            base_rel = self.stage_file_rel_path()
            modi_dir = self.modi_dir_rel_path_
            modi_rel = self.modi_file_rel_path()
        else:  # DIFF_MODE_BASE_MODI (default)
            base_dir = self.base_dir_rel_path_
            base_rel = self.base_file_rel_path()
            modi_dir = self.modi_dir_rel_path_
            modi_rel = self.modi_file_rel_path()

        base = posixpath.join(root_path, base_dir, base_rel)
        modi = posixpath.join(root_path, modi_dir, modi_rel)
        return (base, modi)

    def modi_file_rel_path(self):
        # Return source-tree relative path.
        return self.modi_rel_path_

    def stage_file_rel_path(self):
        # Return source-tree relative path.
        return self.stage_rel_path_

    def base_file_rel_path(self):
        # Return source-tree relative path.
        return self.base_rel_path_

    def generate_label(self, enable_stats):
        if self.desc_ is not None and enable_stats:
            stats =  ("[%d | A: %d / D: %d / C: %d]" %
                      (self.modi_line_count(),
                       self.add_line_count(),
                       self.del_line_count(),
                       self.chg_line_count()))
            label = "%s  %s" % (self.modi_file_rel_path(), stats)
        else:
            label = self.modi_file_rel_path()

        return label


    def button_label(self):
        label = self.generate_label(self.stats_file_)
        return label

    def tab_label(self):
        label = self.generate_label(self.stats_tab_)
        return label

    def tab_relpath(self):
        return self.modi_file_rel_path()

    def make_viewer(self, base, modi):
        viewer = diff_viewer.DiffViewer(base, modi,
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

        mode = tab_widget.get_staged_diff_mode()
        base, modi = self.get_diff_paths(mode, root_path)
        viewer = self.make_viewer(base, modi)
        tab_widget.add_viewer(viewer)


def show_diff_map(options):
    return options.arg_diff_map


def auto_reload_enabled(options):
    return options.arg_auto_reload


def show_line_numbers(options):
    return options.arg_line_numbers


def add_diff_to_viewer(desc, viewer):
    assert(len(desc.base_.lines_) == len(desc.modi_.lines_))

    # Set the changed region count from the diff descriptor
    viewer.set_changed_region_count(desc.base_.n_changed_regions_)

    for idx in range(0, len(desc.base_.lines_)):
        base = desc.base_.lines_[idx]
        modi = desc.modi_.lines_[idx]
        viewer.add_line(base, modi)

    viewer.finalize()


def generate(options, mode, note):
    tab_widget = tab_manager_module.DiffViewerTabWidget(options.afr_,
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
                                                        options.arg_file_label_stats,
                                                        options.editor_class_,
                                                        options.editor_theme_,
                                                        options.arg_keybindings,
                                                        note,
                                                        mode)

    rev = options.dossier_["revisions"][0]
    if rev["commit_msg"] is not None:
        tab_widget.add_commit_msg(rev["commit_msg"])

    for f in rev["files"]:
        if mode == "committed" or f["action"] != "unstaged":
            file_inst = FileButton(options,
                                   f["action"],
                                   options.dossier_["root"],
                                   rev["rel_base_dir"],
                                   f["base_rel_path"],
                                   rev["rel_modi_dir"],
                                   f["modi_rel_path"])
        else:
            assert(mode == "uncommitted" and f["action"] == "unstaged")
            file_inst = FileButtonUnstaged(options,
                                           f["action"],
                                           options.dossier_["root"],
                                           rev["rel_base_dir"],
                                           f["base_rel_path"],
                                           rev["rel_modi_dir"],
                                           f["modi_rel_path"],
                                           rev["rel_stage_dir"],
                                           f["stage_rel_path"])

        tab_widget.add_file(file_inst)

    tab_widget.run()

    return 0
