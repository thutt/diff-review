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

    def is_url(self):
        return self.options_.arg_dossier_url is not None


class FileButton(FileButtonBase): # Committed & not-unstaged uncommited.
    def __init__(self,
                 options,
                 action,
                 root_path,
                 base_disp_path,
                 base_rel_dir,  # "sha.d"
                 base_path,     # relative path
                 modi_disp_path,
                 modi_rel_dir,  # "sha.d"
                 modi_path):    # relative path
        super().__init__(options, action, root_path)


        self.base_disp_path_    = base_disp_path # XXX Need display path for each arg
        self.sha_dir_rel_path_   = base_rel_dir
        self.base_chg_id_        = base_path

        self.modi_disp_path_     = modi_disp_path # XXX need to use this value.
        self.modi_rel_dir_       = modi_rel_dir
        self.modi_chg_path_      = modi_path

    def display_path(self):
        return self.modi_disp_path_

    def base_display_path(self):
        return self.base_disp_path_

    def modi_display_path(self):
        return self.modi_disp_path_

    def generate_label(self, enable_stats):
        if self.desc_ is not None and enable_stats:
            stats =  ("[%d | A: %d / D: %d / C: %d]" %
                      (self.modi_line_count(),
                       self.add_line_count(),
                       self.del_line_count(),
                       self.chg_line_count()))
            label = "%s  %s" % (self.display_path(), stats)
        else:
            label = self.display_path()

        return label


    def button_label(self):
        label = self.generate_label(self.stats_file_)
        return label

    def tab_label(self):
        label = self.generate_label(self.stats_tab_)
        return label

    def tab_relpath(self):
        return self.display_path()

    def make_viewer(self, base_disp_path, base, modi_disp_path, modi):
        viewer = diff_viewer.DiffViewer(base, modi,
                                        base_disp_path,
                                        modi_disp_path,
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

    def get_base_chg_id_path(self):
        if self.is_url():
            return posixpath.join(self.sha_dir_rel_path_, self.base_chg_id_)
        else:
            return posixpath.join(self.root_path_, self.sha_dir_rel_path_,
                                  self.base_chg_id_)

    def get_modi_chg_id_path(self):
        if self.is_url():
            return posixpath.join(self.modi_rel_dir_, self.modi_chg_path_)
        else:
            return posixpath.join(self.root_path_,
                                  self.modi_rel_dir_, self.modi_chg_path_)

    def add_viewer(self, tab_widget):
        base      = self.get_base_chg_id_path()
        modi      = self.get_modi_chg_id_path()
        base_disp = self.base_display_path()
        modi_disp = self.modi_display_path()
        viewer    = self.make_viewer(base_disp, base, modi_disp, modi)
        tab_widget.add_viewer(viewer)


class FileButtonUnstaged(FileButtonBase):
    def __init__(self,
                 options,
                 action,
                 root_path,

                 base_disp_path,
                 base_rel_dir,   # "sha.d"
                 base_path,     # relative-pathname

                 stag_disp_path,
                 stag_rel_dir,  # "sha.d"
                 stag_path,     # relative-pathname

                 modi_disp_path,
                 modi_rel_dir,  # "modi.d"
                 modi_path):    # relative-pathname
        super().__init__(options, action, root_path)

        self.base_disp_path_     = base_disp_path
        self.base_rel_path_      = base_rel_dir
        self.base_chg_id_        = base_path

        self.stag_disp_path_     = stag_disp_path
        self.stag_rel_path_      = base_rel_dir
        self.stag_chg_id_        = stag_path

        self.modi_disp_path_     = modi_disp_path
        self.modi_rel_dir_       = modi_rel_dir
        self.modi_path_          = modi_path

    def get_base_chg_id_path(self):
        if self.is_url():
            return posixpath.join(self.base_rel_path_, self.base_chg_id_)
        else:
            return posixpath.join(self.root_path_,
                                  self.base_rel_path_, self.base_chg_id_)

    def get_stag_chg_id_path(self):
        if self.is_url():
            return posixpath.join(self.stag_rel_path_, self.stag_chg_id_)
        else:
            return posixpath.join(self.root_path_,
                                  self.stag_rel_path_, self.stag_chg_id_)

    def get_modi_path(self):
        if self.is_url():
            return posixpath.join(self.modi_rel_dir_, self.modi_path_)
        else:
            return posixpath.join(self.root_path_,
                                  self.modi_rel_dir_, self.modi_path_)

    def has_staged(self):
        return self.stag_chg_id_ is not None

    def get_diff_paths(self, mode):
        if mode == DIFF_MODE_BASE_STAGE:
            base = self.get_base_chg_id_path()
            modi = self.get_stag_chg_id_path()
        elif mode == DIFF_MODE_STAGE_MODI:
            base = self.get_stag_chg_id_path()
            modi = self.get_modi_path()
        else:
            assert(mode == DIFF_MODE_BASE_MODI)
            base = self.get_base_chg_id_path()
            modi = self.get_modi_path()

        return (base, modi)

    def get_display_paths(self, mode):
        if mode == DIFF_MODE_BASE_STAGE:
            base_disp = self.base_disp_path_
            modi_disp = self.stag_disp_path_
        elif mode == DIFF_MODE_STAGE_MODI:
            base_disp = self.stag_disp_path_
            modi_disp = self.modi_disp_path_
        else:
            assert(mode == DIFF_MODE_BASE_MODI)
            base_disp = self.base_disp_path_
            modi_disp = self.modi_disp_path_

        return (base_disp, modi_disp)

    def display_path(self):
        return self.modi_disp_path_

    def generate_label(self, enable_stats):
        if self.desc_ is not None and enable_stats:
            stats =  ("[%d | A: %d / D: %d / C: %d]" %
                      (self.modi_line_count(),
                       self.add_line_count(),
                       self.del_line_count(),
                       self.chg_line_count()))
            label = "%s  %s" % (self.display_path(), stats)
        else:
            label = self.display_path()

        return label

    def button_label(self):
        label = self.generate_label(self.stats_file_)
        return label

    def tab_label(self):
        label = self.generate_label(self.stats_tab_)
        return label

    def tab_relpath(self):
        return self.display_path()

    def make_viewer(self, base_disp_path, base, modi_disp_path, modi):
        viewer = diff_viewer.DiffViewer(base, modi,
                                        base_disp_path,
                                        modi_disp_path,
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
        mode                    = tab_widget.get_staged_diff_mode()
        (base, modi)            = self.get_diff_paths(mode)
        (base_disp, modi_disp)  = self.get_display_paths(mode)
        viewer                  = self.make_viewer(base_disp, base, modi_disp, modi)
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

    rev   = options.dossier_["revisions"][0]
    cache = options.dossier_["cache"]
    root  = options.dossier_["root"]

    if rev["commit_msg"] is not None:
        tab_widget.add_commit_msg(rev["commit_msg"])

    for f in rev["files"]:
        action         = f["action"]
        base_key       = f["base"]
        modi_key       = f["modi"]

        modi_rel_dir   = cache[modi_key]["rel_dir"]
        modi_path      = cache[modi_key]["pathname"]
        modi_disp_path = cache[modi_key]["display_path"]

        base_rel_dir   = cache[base_key]["rel_dir"]
        base_path      = cache[base_key]["pathname"]
        base_disp_path = cache[base_key]["display_path"]


        if mode == "committed" or f["action"] != "unstaged":
            file_inst = FileButton(options,
                                   action,
                                   root,
                                   base_disp_path,
                                   base_rel_dir,
                                   base_path,
                                   modi_disp_path,
                                   modi_rel_dir,
                                   modi_path)
        else:
            assert(mode == "uncommitted" and f["action"] == "unstaged")
            stag_key       = f["stag"] # Can be 'null'.
            stag_path      = None
            stag_disp_path = None
            stag_rel_dir   = None
            if stag_key is not None:
                stag_path      = cache[stag_key]["pathname"]
                stag_disp_path = cache[stag_key]["display_path"]
                stag_rel_dir   = cache[stag_key]["rel_dir"]

            file_inst = FileButtonUnstaged(options,
                                           action,
                                           root,
                                           base_disp_path,
                                           base_rel_dir,
                                           base_path,
                                           stag_disp_path,
                                           stag_rel_dir,
                                           stag_path,
                                           modi_disp_path,
                                           modi_rel_dir,
                                           modi_path)

        tab_widget.add_file(file_inst)

    tab_widget.run()

    return 0
