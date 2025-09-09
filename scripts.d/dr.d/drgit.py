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

    def get_blob_from_commit_sha(self, file_info, sha):
        cmd = [ self.scm_.scm_path_, "ls-tree", sha, file_info.rel_path_ ]
        (stdout, stderr, rc) = drutil.execute(self.scm_.verbose_, cmd)

        if rc == 0:
            # 100644 blob b41ff3f4aea3d7ab6e3fd0efd36fc19267fd43a8    scripts.d/dr.d/drgit.py
            line   = ' '.join(stdout[0].split()) # Compress internal whitespace
            fields = line.split()
            return fields[2]
        else:
            drutil.fatal("%s: Unable to execute '%s'." %
                         (self.qualid_(), ' '.join(cmd)))

    def get_most_recent_commit_blob(self, file_info):
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
                return None

            # Now get the blob of the desired file from the commit.
            # This simplifies copy to the review directory for
            # previous revisions of uncommitted changes, and committed changes.
            return self.get_blob_from_commit_sha(file_info, sha)
        else:
            drutil.fatal("%s: Unable to execute '%s'." %
                         (self.qualid_(), ' '.join(cmd)))

    def is_blob(self, file_info):
        # Check that the SHA for this file references a blob (file
        # contents), or is an empty file.

        if not file_info.empty() and file_info.chg_id_ is not None:
            cmd = [ self.scm_.scm_path_,
                    "cat-file", "-t", file_info.chg_id_ ]
            (stdout, stderr, rc) = drutil.execute(self.scm_.verbose_, cmd)
        
            if rc == 0:
                return stdout[0] == "blob"
            else:
                drutil.fatal("%s: Unable to execute '%s'." %
                             (self.qualid_(), ' '.join(cmd)))
        else:
            return True

    def copy_to_review_directory_(self, dest_dir, file_info):
        assert(isinstance(file_info, drscm.FileInfo))
        assert(not file_info.empty()) # Empty handled by caller.
        assert(self.is_blob(file_info))

        if file_info.chg_id_ is not None:
            cmd = [ self.scm_.scm_path_, "show", file_info.chg_id_ ]
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
        sha = self.get_most_recent_commit_blob(file_info)
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
        sha = self.get_most_recent_commit_blob(file_info)
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
        return "delete"


class Added(Uncommitted):
    def __init__(self, scm, modi_rel_path):
        super().__init__(scm)
        self.set_modi_file_info(drscm.FileInfo(modi_rel_path, None))
        self.set_base_file_info(drscm.FileInfoEmpty(modi_rel_path))

    def action(self):
        return "add"


class Committed(ChangedFile):
    def __init__(self, scm):
        super().__init__(scm)


class CommittedDelete(Committed):
    def __init__(self, scm, base_rel_path, base_sha):
        super().__init__(scm)
        self.set_modi_file_info(drscm.FileInfoEmpty(base_rel_path))
        self.set_base_file_info(drscm.FileInfo(base_rel_path, base_sha))

    def action(self):
        return "delete"


class CommittedModify(Committed):
    def __init__(self, scm, base_rel_path, base_file_sha, modi_file_sha):
        super().__init__(scm)
        self.set_modi_file_info(drscm.FileInfo(base_rel_path, modi_file_sha))
        self.set_base_file_info(drscm.FileInfo(base_rel_path, base_file_sha))

    def action(self):
        return "modify"


class CommittedRename(Committed):
    def __init__(self, scm,
                 base_rel_path, base_file_sha,
                 modi_rel_path, modi_file_sha):
        super().__init__(scm)
        self.set_modi_file_info(drscm.FileInfo(modi_rel_path, modi_file_sha))
        self.set_base_file_info(drscm.FileInfo(base_rel_path, base_file_sha))

    def action(self):
        return "rename"


class CommittedAdd(Committed):
    def __init__(self, scm, modi_rel_path, modi_file_sha):
        super().__init__(scm)
        self.set_modi_file_info(drscm.FileInfo(modi_rel_path, modi_file_sha))
        self.set_base_file_info(drscm.FileInfoEmpty(modi_rel_path))

    def action(self):
        return "add"


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
        cmd = [ self.scm_path_, "status",
                "--ignore-submodules", "--renames", "--short" ]
        (stdout, stderr, rc) = drutil.execute(self.verbose_, cmd)

        if rc == 0:
            result = [ ]
            if len(stdout) > 0:
                for l in stdout:
                    i_ch     = l[0]
                    w_ch     = l[1]
                    rel_path = l[3:]
                    action   = self.parse_action(i_ch, w_ch, rel_path)
                    result.append(action)
            else:
                result = None
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

    def rev_parse(self, chg_id):
        assert(isinstance(chg_id, str))
        cmd = [ self.scm_path_, "rev-parse", chg_id ]
        (stdout, stderr, rc) = drutil.execute(self.verbose_, cmd)

        if rc == 0:
            return stdout
        else:
            drutil.fatal("%s: Unable to execute '%s'." %
                         (self.qualid_(), ' '.join(cmd)))

    # Returns a range that covers a single SHA, or a range of SHA values.
    def get_change_range(self):
        assert(isinstance(self.change_id_, str))
        stdout = self.rev_parse(self.change_id_)
        if len(stdout) == 1:
            # Single SHA specified.
            chg_id = "%s^..%s" % (self.change_id_, self.change_id_)
            stdout = self.rev_parse(chg_id)

        assert(len(stdout) == 2)
        # Remove leading '^' on second line of output.
        stdout[1] = stdout[1][1:]
        return (stdout[1],      # beg_sha  (not included in range).
                stdout[0])      # end_sha.


    def diff_tree(self,
                  beg_sha, # Not included in range
                  end_sha):
        cmd = [ self.scm_path_, "diff-tree",
                "--root",             # Show initial commit as creation event.
                "--ignore-submodules",
                "-M",                 # Find renames.
                "-r", "%s..%s" % (beg_sha, end_sha) ]
        (stdout, stderr, rc) = drutil.execute(self.verbose_, cmd)
        if rc == 0:
            return stdout
        else:
            drutil.fatal("%s: Unable to execute '%s'." %
                         (self.qualid_(), ' '.join(cmd)))

    def parse_action(self, action, base_file_sha, modi_file_sha, tail):
        assert(action in ('A', 'B', 'C', 'D', 'M', 'R', 'T', 'U', 'X'))

        if action == 'A':
            assert(base_file_sha == "0000000000000000000000000000000000000000")
            modi_rel_path = tail[0]
            action =  CommittedAdd(self, modi_rel_path, modi_file_sha)

        elif action == 'B':     # Pairing broken.
            # It is not known how to generate this action.
            raise NotImplementedError("Pairing Broken action: %s" % (tail))

        elif action == 'C':     # Copy.
            # It is not known how to generate this action.
            raise NotImplementedError("Copy action: %s" % (tail))

        elif action == 'D':     # Delete.
            base_rel_path = tail[0]
            assert(modi_file_sha == "0000000000000000000000000000000000000000")
            action = CommittedDelete(self, base_rel_path, base_file_sha)

        elif action == 'M':     # Modify.
            base_rel_path = tail[0]
            action = CommittedModify(self, base_rel_path,
                                     base_file_sha, modi_file_sha)
            
        elif action == 'R':    # Rename.
            base_rel_path = tail[0]
            modi_rel_path = tail[1]
            action        = CommittedRename(self,
                                            base_rel_path, base_file_sha,
                                            modi_rel_path, modi_file_sha)

        elif action == 'T':    # Type change.
            # It is not known how to generate this action.
            raise NotImplementedError("Type change action: %s" % (tail))
            
        elif action == 'U':    # Unmerged.
            # It is not known how to generate this action.
            raise NotImplementedError("Unmerged action: %s" % (tail))

        elif action == 'X':    # Unknown
            # It is not known how to generate this action.
            raise NotImplementedError("Unknown action: %s" % (tail))

        else:
            raise NotImplementedError("Unrecognized action: %s  %s" % (action, tail))

        return action;

    def generate_dossier_(self):
        (base_sha, modi_sha) = self.get_change_range()

        diff = self.diff_tree(base_sha, modi_sha)
        result = [ ]
        for l in diff:
            l = l.replace(' ', '\t') # Line has both space and tab.
            fields = l.split('\t')
            base_file_mode = fields[0]
            modi_file_mode = fields[1]
            base_file_sha  = fields[2]
            modi_file_sha  = fields[3]
            action         = fields[4]
            tail           = fields[5:] # Action and pathnames.

            operation = self.parse_action(action[0],
                                          base_file_sha, modi_file_sha, tail)
            result.append(operation)
        return result
