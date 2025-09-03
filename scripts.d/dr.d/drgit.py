# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import os
import shutil

import drscm
import drutil



class ChangedFile(drscm.ChangedFile):
    def __init__(self, git_path, verbose, base_dir, modi_dir, cid, rel_path):
        super().__init__(git_path, verbose, base_dir, modi_dir, cid, rel_path)

    def current_revision_id(self, rel_path):
        cmd = [ self.scm_path_, "log", "--oneline", "-1", "--", rel_path ]

        (stdout, stderr, rc) = drutil.execute(self.verbose_, cmd)

        if rc == 0:
            sha = stdout[0].split(' ')[0] # Example: 'd90e8f0 Initial commit'
            if sha == "":                 # Empty sha means no previous commit.
                sha = None
            return sha
        else:
            drutil.fatal("Unable to execute '%s'." % (' '.join(cmd)))

    def previous_revision_id(self):
        sha = [ ]
        if self.revision_ is not None:
            sha = [ "%s^" % (self.revision_) ]

        cmd = ([ self.scm_path_, "log", "--oneline", "-1" ] +
               sha +
               [ "--", self.rel_path_ ])

        (stdout, stderr, rc) = drutil.execute(self.verbose_, cmd)

        if rc == 0:
            sha = stdout[0].split(' ')[0] # Example: 'd90e8f0 Initial commit'
            if sha == "":                 # Empty sha means no previous commit.
                sha = None
            return sha
        else:
            drutil.fatal("Unable to execute '%s'." % (' '.join(cmd)))

    def output_name(self, dest_dir, rel_path):
        return os.path.join(dest_dir, rel_path)

    def create_output_dir(self, out_name):
        out_dir = os.path.dirname(out_name)
        if not os.path.exists(out_dir):
            drutil.mktree(out_dir)

    def write_file(self, out_name, stdout):
        with open(out_name, "w") as fp:
            for l in stdout:
                fp.write("%s\n" % (l))

    def copy_revision(self, dest_dir, rel_path, sha):
        cmd = [ self.scm_path_, "show", "%s:%s" % (sha, rel_path) ]
        (stdout, stderr, rc) = drutil.execute(self.verbose_, cmd)

        if rc == 0:
            out_name = self.output_name(dest_dir, rel_path)
            self.create_output_dir(out_name)
            self.write_file(out_name, stdout)
        else:
            drutil.fatal("Unable to execute '%s'." % (' '.join(cmd)))

    def copy_previous_revision(self, dest_dir):
        self.copy_revision(dest_dir, self.rel_path_, self.previous_revision_id())

    def copy_current_file(self, dest_dir):
        out_name = self.output_name(dest_dir, self.rel_path_)
        self.create_output_dir(out_name)
        shutil.copyfile(self.rel_path_, out_name)

    def copy_empty_file(self, dest_dir):
        out_name = self.output_name(dest_dir, self.rel_path_)
        self.create_output_dir(out_name)
        with open(out_name, "w") as fp:
            pass


class Committed(ChangedFile):
    def __init__(self, git_path, verbose, base_dir, modi_dir, cid, rel_path):
        super().__init__(git_path, verbose, base_dir, modi_dir, cid, rel_path)

    def action(self):
        return "committed"

    def copy_file(self, review_base_dir, review_modi_dir):
        if self.previous_revision_id() is not None:
            self.copy_previous_revision(review_base_dir)
        else:
            self.copy_empty_file(review_base_dir)

        self.copy_revision(review_modi_dir, self.rel_path_, self.revision_)


class Untracked(ChangedFile):
    def __init__(self, git_path, verbose, base_dir, modi_dir, rel_path):
        super().__init__(git_path, verbose, base_dir, modi_dir, None, rel_path)

    def action(self):
        return "untracked"

    def previous_revision_id(self):
        return None             # No previous revision.

    def copy_file(self, review_base_dir, review_modi_dir):
        if not os.path.isdir(self.rel_path_):
            self.copy_empty_file(review_base_dir)
            self.copy_current_file(review_modi_dir)
        else:
            drutil.TODO("Ignoring untracked directories.")


class Unstaged(ChangedFile):
    def __init__(self, git_path, verbose, base_dir, modi_dir, relative_pathname):
        super().__init__(git_path, verbose, base_dir, modi_dir, None, relative_pathname)

    def action(self):
        return "unstaged"

    def copy_file(self, review_base_dir, review_modi_dir):
        self.copy_previous_revision(review_base_dir)
        self.copy_current_file(review_modi_dir)


class Staged(ChangedFile):
    def __init__(self, git_path, verbose, base_dir, modi_dir, relative_pathname):
        super().__init__(git_path, verbose, base_dir, modi_dir, None, relative_pathname)

    def action(self):
        return "staged"

    def copy_file(self, review_base_dir, review_modi_dir):
        self.copy_previous_revision(review_base_dir)
        self.copy_current_file(review_modi_dir)


class Rename(Staged):
    def __init__(self, git_path, verbose, base_dir, modi_dir,
                 org_rel_path, new_rel_path):
        super().__init__(git_path, verbose, base_dir, modi_dir, new_rel_path)
        self.org_rel_path_ = org_rel_path
        self.org_sha_      = self.current_revision_id(org_rel_path)

    def action(self):
        return "rename"

    def copy_file(self, review_base_dir, review_modi_dir):
        # Copying instances of a renamed file is different:
        #
        #  The last version of the original needs to be copied out.
        #  The current version of the new name also needs to be copied.
        self.copy_revision(review_base_dir,
                           self.org_rel_path_, self.org_sha_)
        self.copy_current_file(review_modi_dir)

class Deleted(ChangedFile):
    def __init__(self, git_path, verbose, base_dir, modi_dir, rel_path):
        super().__init__(git_path, verbose, base_dir, modi_dir, None, rel_path)

    def action(self):
        return "deleted"

    def copy_file(self, review_base_dir, review_modi_dir):
        self.copy_previous_revision(review_base_dir)
        self.copy_empty_file(review_modi_dir)


class Added(ChangedFile):
    def __init__(self, git_path, verbose, base_dir, modi_dir, rel_path):
        super().__init__(git_path, verbose, base_dir, modi_dir, None, rel_path)

    def action(self):
        return "added"

    def previous_revision_id(self):
        return None             # No previous revision.

    def copy_file(self, review_base_dir, review_modi_dir):
        self.copy_empty_file(review_base_dir)
        self.copy_current_file(review_modi_dir)


class NotYetSupportedState(ChangedFile):
    def __init__(self, git_path, verbose, base_dir, modi_dir, rel_path, idx, wrk):
        super().__init__(git_path, verbose, base_dir, modi_dir, None, rel_path)
        self.idx_ = idx
        self.wrk_ = wrk

    def action(self):
        return "%c%c" % (self.idx_, self.wrk_)

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
            return Deleted(self.scm_path_, self.verbose_,
                           self.review_base_dir_, self.review_modi_dir_,
                           rel_path)
        elif (idx_ch in (' ', 'A', 'M')) and (wrk_ch == 'M'):
            # Unstaged files take precendence over all others.
            #
            # Rename (idx_ch == 'R') is a special case that cannot be
            # processed by Unstaged.
            #
            return Unstaged(self.scm_path_, self.verbose_,
                            self.review_base_dir_, self.review_modi_dir_,
                            rel_path)
        elif (idx_ch == 'R') and (wrk_ch in (' ', 'M')):
            # The file has been renamed.
            # rel_path is of the form:
            #
            #  dr.d/dr.py -> scripts.d/dr.d/dr.py
            #
            parts    =  rel_path.split(' ')
            org_rel_path = parts[0]
            rel_path     = parts[2]
            return Rename(self.scm_path_, self.verbose_,
                          self.review_base_dir_, self.review_modi_dir_,
                          org_rel_path, rel_path)
        elif (idx_ch == 'A') and (wrk_ch == ' '):
            return Added(self.scm_path_, self.verbose_,
                         self.review_base_dir_, self.review_modi_dir_,
                         rel_path)
        elif (idx_ch == 'M') and wrk_ch == ' ':
            return Staged(self.scm_path_, self.verbose_,
                          self.review_base_dir_, self.review_modi_dir_,
                          rel_path)
        elif (idx_ch == '?') or (wrk_ch == '?'):
            return Untracked(self.scm_path_, self.verbose_,
                             self.review_base_dir_, self.review_modi_dir_,
                             rel_path)
        else:
            drutil.warning("unhandled state: index: %c  tree: %c  path: %s" %
                           (idx_ch, wrk_ch, rel_path))
            return NotYetSupportedState(self.scm_path_, self.verbose_,
                                        self.review_base_dir_,
                                        self.review_modi_dir_,
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
        (stdout, stderr, rc) = drutil.execute(self.verbose_, cmd)

        if rc == 0:
            result = [ ]
            for l in stdout:
                i_ch     = l[0]
                w_ch     = l[1]
                rel_path = l[3:]
                action   = self.status_parse_action(i_ch, w_ch, rel_path)
                result.append(action)
        else:
            drutil.fatal("Unable to execute '%s'." % (' '.join(cmd)))

        return result

    def commit_status(self):
        #
        # Show previous commit SHA of a file:
        #  git log --oneline -1 1de3ace^ -- dr.d/dropts.py
        #
        # Show files in a commit:
        #  git diff-tree --no-commit-id --name-only 0cf31e7 -r
        #
        cmd = [ self.scm_path_, "diff-tree", "--no-commit-id",
                "--name-only", "-r", self.change_id_ ]
        (stdout, stderr, rc) = drutil.execute(self.verbose_, cmd)
        if rc == 0:
            result = [ ]
            for rel_path in stdout:
                if len(rel_path) == 0:
                    break
                c = Committed(self.scm_path_, self.verbose_,
                              self.review_base_dir_, self.review_modi_dir_,
                              self.change_id_, rel_path)
                result.append(c)
            return result
        else:
            drutil.fatal("Unable to execute '%s'." % (' '.join(cmd)))

    def generate_dossier_(self):
        if self.change_id_ is None:
            # Unstaged and staged files.
            self.dossier_ = self.client_status()
        else:
            # Committed SHA.
            #
            self.dossier_ = self.commit_status()
