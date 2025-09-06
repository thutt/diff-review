# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import os
import shutil

import drscm
import drutil


class ChangedFile(drscm.ChangedFile):
    def __init__(self, scm):
        super().__init__(scm)

    def write_file(self, out_name, contents):
        assert(isinstance(contents, list))
        with open(out_name, "w") as fp:
            for l in contents:
                fp.write("%s\n" % (l))

    def get_most_recent_commit(self, file_info):
        assert(isinstance(file_info, drscm.FileInfo))

        sha = [ ]
        if file_info.chg_id_ is not None:
            # This simplifies generating difffs for committed changes:
            #
            #   When the SHA of a commit is provided, use the SHA of
            #   the previous commit as the latest.
            #
            sha = [ "%s^" % (file_info.chg_id_) ]

        cmd = ([ self.scm_.scm_path_,
                 "log", "--oneline", "-1" ] +
               sha +
               [ "--", file_info.rel_path_ ])

        (stdout, stderr, rc) = drutil.execute(self.scm_.verbose_, cmd)

        if rc == 0:
            sha = stdout[0].split(' ')[0] # Example: 'd90e8f0 Initial commit'
            if sha == "":                 # Empty sha means no previous commit.
                sha = None
            return sha
        else:
            drutil.fatal("%s: Unable to execute '%s'." %
                         (self.qualid_(), ' '.join(cmd)))

    def copy_to_review_directory_(self, dest_dir, file_info):
        assert(isinstance(file_info, drscm.FileInfo))
        assert(not file_info.empty()) # Empty handled by caller.

        if file_info.chg_id_ is not None:
            cmd = [ self.scm_.scm_path_,
                    "show", "%s:%s" % (file_info.chg_id_,
                                       file_info.rel_path_) ]
            (stdout, stderr, rc) = drutil.execute(self.scm_.verbose_, cmd)

            if rc == 0:
                out_name = self.output_name(dest_dir, file_info)
                self.create_output_dir(out_name)
                self.write_file(out_name, stdout)
            else:
                drutil.fatal("%s: Unable to execute '%s'." %
                             (self.qualid_(), ' '.join(cmd)))
        else:
            out_name = self.output_name(dest_dir, file_info)
            self.create_output_dir(out_name)
            shutil.copyfile(file_info.rel_path_, out_name)


class Uncommitted(ChangedFile):
    def __init__(self, scm):
        super().__init__(scm)

    def find_and_set_base_file_info(self, file_info):
        assert(isinstance(file_info, drscm.FileInfo))
        sha = self.get_most_recent_commit(file_info)
        self.set_base_file_info(drscm.FileInfo(file_info.rel_path_, sha))


class Untracked(ChangedFile):
    def __init__(self, scm, modi_rel_path):
        super().__init__(scm)
        self.set_modi_file_info(drscm.FileInfo(modi_rel_path, None))
        self.set_base_file_info(drscm.FileInfoEmpty(modi_rel_path))

    def action(self):
        return "untracked"

    def update_review_directory(self):
        # Untracked directories are ignored.  Untracked directories
        # only show up if there are files in them.
        #
        if not os.path.isdir(self.modi_file_info_.rel_path_):
            self.copy_to_review_directory(self.scm_.review_base_dir_,
                                          self.base_file_info_)
            self.copy_to_review_directory(self.scm_.review_modi_dir_,
                                          self.modi_file_info_)
        else:
            drutil.TODO("Ignoring untracked directories (%s)." %
                        (self.modi_file_info_.rel_path_))


class Unstaged(Uncommitted):
    def __init__(self, scm, modi_rel_path):
        super().__init__(scm)
        self.set_modi_file_info(drscm.FileInfo(modi_rel_path, None))
        self.find_and_set_base_file_info(self.modi_file_info_)

    def action(self):
        return "unstaged"


class Staged(Uncommitted):
    def __init__(self, scm, modi_rel_path):
        super().__init__(scm)
        self.set_modi_file_info(drscm.FileInfo(modi_rel_path, None))
        self.find_and_set_base_file_info(self.modi_file_info_)

    def action(self):
        return "staged"


class Rename(Uncommitted):
    def __init__(self, scm, base_rel_path, modi_rel_path):
        super().__init__(scm)
        file_info = drscm.FileInfo(base_rel_path, None)
        sha = self.get_most_recent_commit(file_info)
        self.set_base_file_info(drscm.FileInfo(base_rel_path, sha))
        self.set_modi_file_info(drscm.FileInfo(modi_rel_path, None))

    def action(self):
        return "rename"


class Deleted(Uncommitted):
    def __init__(self, scm, modi_rel_path):
        super().__init__(scm)
        self.set_modi_file_info(drscm.FileInfoEmpty(modi_rel_path))
        self.find_and_set_base_file_info(drscm.FileInfo(modi_rel_path, None))

    def action(self):
        return "deleted"


class Added(Uncommitted):
    def __init__(self, scm, modi_rel_path):
        super().__init__(scm)
        self.set_modi_file_info(drscm.FileInfo(modi_rel_path, None))
        self.set_base_file_info(drscm.FileInfoEmpty(modi_rel_path))

    def action(self):
        return "added"


class Committed(ChangedFile):
    def action_add(self, commit_sha, rel_path):
        self.action_ = "add"
        self.set_modi_file_info(drscm.FileInfo(rel_path, commit_sha))
        self.set_base_file_info(drscm.FileInfoEmpty(rel_path))

    def action_broken_pair(self):
        raise NotImplementedError("%s: B not implemented" % (self.qualid_()))

    def action_copy(self):
        raise NotImplementedError("%s: C not implemented" % (self.qualid_()))

    def action_delete(self, rel_path, base_sha):
        self.action_ = "delete"
        self.set_base_file_info(drscm.FileInfo(rel_path, base_sha))
        self.set_modi_file_info(drscm.FileInfoEmpty(rel_path))

    def action_modify(self, rel_path, base_sha, modi_sha):
        self.action_ = "modify"
        self.set_base_file_info(drscm.FileInfo(rel_path, base_sha))
        self.set_modi_file_info(drscm.FileInfo(rel_path, modi_sha))

    def action_rename(self, base_rel_path, base_sha, modi_rel_path, modi_sha):
        self.action_ = "rename"
        self.set_base_file_info(drscm.FileInfo(base_rel_path, base_sha))
        self.set_modi_file_info(drscm.FileInfo(modi_rel_path, modi_sha))

    def action_type_change(self):
        raise NotImplementedError("%s: T not implemented" % (self.qualid_()))

    def action_unmerged(self):
        raise NotImplementedError("%s: U not implemented" % (self.qualid_()))

    def action_unknown(self):
        raise NotImplementedError("%s: X not implemented" % (self.qualid_()))

    def set_files_based_on_action(self, modi_rel_path, base_sha, modi_sha):
        if base_sha is None:
            # If there is no original sha, this is an add.
            self.action_add(modi_sha, modi_rel_path)
            return
        else:
            cmd = ([ self.scm_.scm_path_,
                     "diff", "--name-status", "-C",
                     "%s" % (base_sha),
                     "%s" % (modi_sha) ])

            (stdout, stderr, rc) = drutil.execute(self.scm_.verbose_, cmd)
            if rc == 0:
                for l in stdout:
                    l = ' '.join(l.split()) # Compress internal whitespace.
                    fields = l.split()
                    if modi_rel_path in fields:
                        action = fields[0][0]
                        assert(action in ('A', 'B', 'C', 'D', 'M',
                                          'R', 'T', 'U', 'X'))
                        if action == 'A':   # Add
                            # fields: ['A', 'file-to-delete']
                            self.action_add(modi_sha, fields[1])
                            return

                        elif action == 'B': # Pairing broken
                            # It is not known how to create this record.
                            self.action_broken_pair()
                            return

                        elif action == 'C': # Copy
                            # It is not known how to create this record.
                            self.action_copy()
                            return

                        elif action == 'D': # Delete
                            # fields: ['D', 'file-to-delete']
                            self.action_delete()
                            return

                        elif action == 'M': # Modified
                            # fields: ['M', 'diff-review']
                            self.action_modify(fields[1], base_sha, modi_sha)
                            return

                        elif action == 'R': # Renamed
                            # fields: ['R100', 'dr.d/dr.py', 'scripts.d/dr.d/dr.py']
                            self.action_rename(fields[1], base_sha,
                                               fields[2], modi_sha)
                            return

                        elif action == 'T': # Type change
                            # It is not known how to create this record.
                            self.action_type_change()
                            return

                        elif action == 'U': # Unmerged
                            # It is not known how to create this record.
                            self.action_unmerged()
                            return

                        elif action == 'X': # Unknown
                            # It is not known how to create this record.
                            self.action_unknown()
                            return

                drutil.fatal("%s: '%s' not found in '%s'" %
                             (self.qualid_(), modi_rel_path, ' '.join(cmd)))

            else:
                drutil.fatal("%s: Unable to execute '%s'." %
                             (self.qualid_(), ' '.join(cmd)))

    def __init__(self, scm, modi_rel_path, chg_id):
        super().__init__(scm)
        self.action_ = None

        # Get previous commit for this current file.
        modi_file = drscm.FileInfo(modi_rel_path, chg_id)
        base_sha = self.get_most_recent_commit(modi_file)
        # base_sha is None -> file added in this change.

        self.set_files_based_on_action(modi_rel_path, base_sha, chg_id)

    def action(self):
        return self.action_


class NotYetSupportedState(ChangedFile):
    def __init__(self, modi_rel_path):
        super().__init__()
        self.idx_ = idx
        self.wrk_ = wrk

        self.set_modi_file_info(drscm.FileInfo(modi_rel_path, None))
        self.set_base_file_info(drscm.FileInfoEmpty(modi_rel_path))

    def action(self):
        return "%c%c" % (self.idx_, self.wrk_)


class Git(drscm.SCM):
    def __init__(self, options):
        super().__init__(options)


# GitStaged:
#
#  An interface to Git that facilitates reviewing uncommitted chagnes.
#
class GitStaged(Git):
    def __init__(self, options):
        super().__init__(options)

    def parse_action(self, idx_ch, wrk_ch, rel_path):
        if (idx_ch == 'D') or (wrk_ch == 'D'):
            action = Deleted(self, rel_path)
        elif (idx_ch in (' ', 'A', 'M')) and (wrk_ch == 'M'):
            # Rename (idx_ch == 'R') is a special case that cannot be
            # processed by Unstaged.
            #
            action = Unstaged(self, rel_path)
        elif (idx_ch == 'R') and (wrk_ch in (' ', 'M')):
            # The file has been renamed.
            # rel_path is of the form:
            #
            #  dr.d/dr.py -> scripts.d/dr.d/dr.py
            #
            parts         =  rel_path.split(' ')
            base_rel_path = parts[0]
            modi_rel_path = parts[2]
            action        = Rename(self, base_rel_path, modi_rel_path)
        elif (idx_ch == 'A') and (wrk_ch == ' '):
            action =  Added(self, rel_path)
        elif (idx_ch == 'M') and wrk_ch == ' ':
            action = Staged(self, rel_path)
        elif (idx_ch == '?') or (wrk_ch == '?'):
            action = Untracked(self, rel_path)
        else:
            drutil.warning("unhandled state: index: %c  tree: %c  path: %s" %
                           (idx_ch, wrk_ch, rel_path))
            action = NotYetSupportedState(self)

        return action;

    def generate_dossier_(self):
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
                action   = self.parse_action(i_ch, w_ch, rel_path)
                result.append(action)
        else:
            drutil.fatal("%s: Unable to execute '%s'." %
                         (self.qualid_(), ' '.join(cmd)))

        return result


# GitCommitted:
#
#  An interface to Git that facilitates reviewing committed chagnes.
#
class GitCommitted(Git):
    def __init__(self, options):
        super().__init__(options)

    def generate_dossier_(self):
        # Show files in a commit:
        #  git diff-tree --no-commit-id --name-only 0cf31e7 -r
        #
        cmd = [ self.scm_path_, "diff-tree", "--no-commit-id",
                "--name-only", "-r", self.change_id_ ]
        (stdout, stderr, rc) = drutil.execute(self.verbose_, cmd)
        if rc == 0:
            result = [ ]
            for rel_path in stdout:
                c = Committed(self, rel_path, self.change_id_)
                result.append(c)
            return result
        else:
            drutil.fatal("%s: Unable to execute '%s'." %
                         (self.qualid_(), ' '.join(cmd)))
