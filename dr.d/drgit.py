# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import os
import shutil

import drscm
import drutil



class ChangedFile(drscm.ChangedFile):
    def __init__(self, git_path, base_dir, modi_dir, cid, rel_path):
        super().__init__(git_path, base_dir, modi_dir, cid, rel_path)

    def previous_revision_id(self):
        cmd = [ self.scm_path_, "log", "--oneline",
                "-1",           # Limit to 1 commit.
                "--", self.rel_path_ ]
        (stdout, stderr, rc) = drutil.execute(cmd)

        if rc == 0:
            sha = stdout[0].split(' ')[0] # Example: 'd90e8f0 Initial commit'
            return sha
        else:
            fatal("Unable to execute '%s'." % (' '.join(cmd)))

    def output_name(self, dest_dir):
        return os.path.join(dest_dir, self.rel_path_)

    def create_output_dir(self, out_name):
        out_dir = os.path.dirname(out_name)
        if not os.path.exists(out_dir):
            drutil.mktree(out_dir)

    def write_file(self, out_name, stdout):
        with open(out_name, "w") as fp:
            for l in stdout:
                fp.write("%s\n" % (l))

    def copy_revision(self, dest_dir, sha):
        cmd = [ self.scm_path_, "show", "%s:%s" % (sha, self.rel_path_) ]
        (stdout, stderr, rc) = drutil.execute(cmd)

        if rc == 0:
            out_name = self.output_name(dest_dir)
            self.create_output_dir(out_name)
            self.write_file(out_name, stdout)
        else:
            fatal("Unable to execute '%s'." % (' '.join(cmd)))

    def copy_previous_revision(self, dest_dir):
        self.copy_revision(dest_dir, self.previous_revision_id())

    def copy_current_file(self, dest_dir):
        out_name = self.output_name(dest_dir)
        self.create_output_dir(out_name)
        shutil.copyfile(self.rel_path_, out_name)

    def copy_empty_file(self, dest_dir):
        out_name = self.output_name(dest_dir)
        self.create_output_dir(out_name)
        with open(out_name, "w") as fp:
            pass


class Untracked(ChangedFile):
    def __init__(self, git_path, base_dir, modi_dir, cid, rel_path):
        super().__init__(git_path, base_dir, modi_dir, cid, rel_path)

    def action(self):
        return "untracked"

    def previous_revision_id(self):
        return None             # No previous revision.

    def copy_file(self, review_base_dir, review_modi_dir):
        self.copy_empty_file(review_base_dir)
        self.copy_current_file(review_modi_dir)


class Unstaged(ChangedFile):
    def __init__(self, git_path, base_dir, modi_dir, cid, relative_pathname):
        super().__init__(git_path, base_dir, modi_dir, cid, relative_pathname)

    def action(self):
        return "unstaged"

    def copy_file(self, review_base_dir, review_modi_dir):
        self.copy_previous_revision(review_base_dir)
        self.copy_current_file(review_modi_dir)


class Staged(ChangedFile):
    def __init__(self, git_path, base_dir, modi_dir, cid, relative_pathname):
        super().__init__(git_path, base_dir, modi_dir, cid, relative_pathname)

    def action(self):
        return "staged"

    def copy_file(self, review_base_dir, review_modi_dir):
        self.copy_previous_revision(review_base_dir)
        self.copy_current_file(review_modi_dir)


class Deleted(ChangedFile):
    def __init__(self, git_path, base_dir, modi_dir, cid, rel_path):
        super().__init__(git_path, base_dir, modi_dir, cid, rel_path)

    def action(self):
        return "deleted"

    def copy_file(self, review_base_dir, review_modi_dir):
        self.copy_previous_revision(review_base_dir)
        self.copy_empty_file(review_modi_dir)


class Added(ChangedFile):
    def __init__(self, git_path, base_dir, modi_dir, cid, rel_path):
        super().__init__(git_path, base_dir, modi_dir, cid, rel_path)

    def action(self):
        return "added"

    def previous_revision_id(self):
        return None             # No previous revision.

    def copy_file(self, review_base_dir, review_modi_dir):
        self.copy_empty_file(review_base_dir)
        self.copy_current_file(review_modi_dir)


class NotYetSupportedState(ChangedFile):
    def __init__(self, git_path, base_dir, modi_dir, cid, rel_path, idx, wrk):
        super().__init__(git_path, base_dir, modi_dir, cid, rel_path)
        self.idx_ = idx
        self.wrk_ = wrk

    def action(self):
        return "UNKNOWN"

    def previous_revision_id(self):
        return None  # Previous revision unknown -- unsupported state.

    def copy_file(self, review_base_dir, review_modi_dir):
        self.copy_empty_file(review_base_dir)
        self.copy_current_file(review_modi_dir)


class Git(drscm.SCM):
    def __init__(self, options):
        super().__init__(options)

    def status_parse_action(self, idx_ch, wrk_ch, rel_path):
        if (idx_ch == 'D') or (wrk_ch == 'D'):
            return Deleted(self.scm_path_,
                           self.review_base_dir_, self.review_modi_dir_,
                           None, rel_path)
        elif (idx_ch in (' ', 'A', 'M')) and (wrk_ch == 'M'):
            # Unstaged files take precendence over all others.
            return Unstaged(self.scm_path_, 
                            self.review_base_dir_, self.review_modi_dir_,
                            None, rel_path)
        elif (idx_ch == 'A') and (wrk_ch == ' '):
            return Added(self.scm_path_,
                         self.review_base_dir_, self.review_modi_dir_,
                         None, rel_path)
        elif (idx_ch == 'M') and wrk_ch == ' ':
            return Staged(self.scm_path_,
                          self.review_base_dir_, self.review_modi_dir_,
                          None, rel_path)
        elif (idx_ch == '?') or (wrk_ch == '?'):
            return Untracked(self.scm_path_,
                             self.review_base_dir_, self.review_modi_dir_,
                             None, rel_path)
        else:
            drutil.warning("unhandled state: index: %c  tree: %c  path: %s" %
                           (idx_ch, wrk_ch, rel_path))
            return NotYetSupportedState(self.scm_path_,
                                        self.review_base_dir,
                                        self.review_modi_dir,
                                        None, rel_path,
                                        idx_ch, wrk_ch)

    def client_status(self):
        # See the 'man git-status' for the meaning of the first two
        # characters for each line of output.
        #
        # The first character refers to the index (staged changes).
        # The second character refers to the working tree (unstaged changes).
        #
        cmd = [ self.scm_path_, "status", "--short" ]
        (stdout, stderr, rc) = drutil.execute(cmd)

        if rc == 0:
            result = [ ]
            for l in stdout:
                if len(l) > 2:
                    i_ch     = l[0]
                    w_ch     = l[1]
                    rel_path = l[3:]
                    action   = self.status_parse_action(i_ch, w_ch, rel_path)
                    result.append(action)
                else:           # Last blank line.
                    break
        else:
            drutil.fatal("Unable to execute '%s'." % (' '.join(cmd)))

        return result

    def dossier(self):
        if self.change_id_ is None:
            # Unstaged and staged files.
            self.dossier_ = self.client_status()
        else:
            # Committed SHA.
            #
            # Show previous commit SHA of a file:
            #  git log --oneline -1 1de3ace^ -- dr.d/dropts.py
            #
            # Show files in a commit:
            #  git diff-tree --no-commit-id --name-only 0cf31e7 -r
            #
            raise NotImplementedError("git committed changes: not implemented")
