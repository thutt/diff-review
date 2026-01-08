# Copyright (c) 2025, 2026  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import os
import shutil

import drscm
import drutil

def git_is_blob(scm, file_info):
    # Check that the SHA for this file references a blob (file
    # contents), or is an empty file.

    if not file_info.empty() and file_info.chg_id_ is not None:
        cmd = [ scm.scm_path_,
                "cat-file", "-t", file_info.chg_id_ ]
        (stdout, stderr, rc) = drutil.execute(scm.verbose_, cmd)

        if rc == 0:
            return stdout[0] == "blob"
        else:
            drutil.fatal("%s: Unable to execute '%s'." %
                         (drutil.qualid_(), ' '.join(cmd)))
    else:
        return True


def git_get_file_contents(scm, file_info):
    cmd = [ scm.scm_path_, "show", file_info.chg_id_ ]
    (stdout, stderr, rc) = drutil.execute(scm.verbose_, cmd)

    if rc == 0:
        return stdout
    else:
        drutil.fatal("%s: Unable to execute '%s'." %
                     (drutil.qualid_(), ' '.join(cmd)))


def git_get_commit_blob_from_commit_sha(scm, file_info, sha):
    cmd = [ scm.scm_path_, "ls-tree", sha, file_info.rel_path_ ]
    (stdout, stderr, rc) = drutil.execute(scm.verbose_, cmd)

    if rc == 0:
        # 100644 blob b41ff3f4aea3d7ab6e3fd0efd36fc19267fd43a8    scripts.d/dr.d/drgit.py
        line   = ' '.join(stdout[0].split()) # Compress internal whitespace
        fields = line.split()
        return fields[2]
    else:
        drutil.fatal("%s: Unable to execute '%s'." %
                     (drutil.qualid_(), ' '.join(cmd)))


def git_get_staged_file_blob_sha(scm, rel_path):
    cmd = [ scm.scm_path_, "ls-files", "--stage", rel_path ]

    (stdout, stderr, rc) = drutil.execute(scm.verbose_, cmd)

    if rc == 0:
        # 100644 95adebe4a45e9ef66ca92194b58161a417c34b11 0       scripts.d/dr.d/drgit.py
        line   = ' '.join(stdout[0].split()) # Compress internal whitespace
        fields = line.split()
        return fields[1]
    else:
        drutil.fatal("%s: Unable to execute '%s'." %
                     (drutil.qualid_(), ' '.join(cmd)))


def git_get_unstaged_file_blob_sha(scm, rel_path):
    cmd = [ scm.scm_path_, "hash-object", rel_path ]

    (stdout, stderr, rc) = drutil.execute(scm.verbose_, cmd)

    if rc == 0:
        # 28dc515b9954e7fb34f47de895e21de3f104d749
        line   = ' '.join(stdout[0].split()) # Compress internal whitespace
        fields = line.split()
        return fields[0]
    else:
        drutil.fatal("%s: Unable to execute '%s'." %
                     (drutil.qualid_(), ' '.join(cmd)))


def git_get_head_file_blob_sha(scm, rel_path):
    # Gets SHA of HEAD revision.
    cmd = [ scm.scm_path_, "rev-parse", "HEAD:%s" % (rel_path) ]

    (stdout, stderr, rc) = drutil.execute(scm.verbose_, cmd)

    if rc == 0:
        # 756d8d50165a3bdbe5996b3e91b00664cc93a4ed
        line   = ' '.join(stdout[0].split()) # Compress internal whitespace
        fields = line.split()
        return fields[0]
    else:
        drutil.fatal("%s: Unable to execute '%s'." %
                     (drutil.qualid_(), ' '.join(cmd)))


def git_get_most_recent_commit_blob(scm, file_info):
    assert(isinstance(file_info, drscm.FileInfo))
    assert(file_info.chg_id_ is None) # A known SHA should already be blob.

    sha = [ ]
    cmd = ([ scm.scm_path_, "log", "--oneline", "-1" ] +
           sha +
           [ "--", file_info.rel_path_ ])

    (stdout, stderr, rc) = drutil.execute(scm.verbose_, cmd)

    if rc == 0:
        if len(stdout) > 0:
           sha = stdout[0].split(' ')[0] # Example: 'd90e8f0 Initial commit'
           if sha == "":                 # Empty sha means no previous commit.
               return None

           # Now get the blob of the desired file from the commit.
           # This simplifies copy to the review directory for
           # previous revisions of uncommitted changes, and committed changes.
           return git_get_commit_blob_from_commit_sha(scm, file_info, sha)
        else:
            # No stdout on first command means the file is not
            # committed.
            return None
    else:
        drutil.fatal("%s: Unable to execute '%s'." %
                     (drutil.qualid_(), ' '.join(cmd)))


def git_get_numstat(scm,
                    beg_sha, # Not included in range
                    end_sha):
    cmd = [ scm.scm_path_, "diff-tree",
            "--root",             # Show initial commit as creation event.
            "--ignore-submodules",
            "--numstat",                 # Find renames.
            "-r", "%s..%s" % (beg_sha, end_sha) ]
    (stdout, stderr, rc) = drutil.execute(scm.verbose_, cmd)
    if rc == 0:
        return stdout
    else:
        drutil.fatal("%s: Unable to execute '%s'." %
                     (drutil.qualid_(), ' '.join(cmd)))


def git_get_staged_numstat(scm):
    cmd = [ scm.scm_path_, "diff", "--cached", "--numstat" ]
    (stdout, stderr, rc) = drutil.execute(scm.verbose_, cmd)
    if rc == 0:
        return stdout
    else:
        drutil.fatal("%s: Unable to execute '%s'." %
                     (drutil.qualid_(), ' '.join(cmd)))


def git_get_unstaged_numstat(scm):
    cmd = [ scm.scm_path_, "diff", "--numstat" ]
    (stdout, stderr, rc) = drutil.execute(scm.verbose_, cmd)
    if rc == 0:
        return stdout
    else:
        drutil.fatal("%s: Unable to execute '%s'." %
                     (drutil.qualid_(), ' '.join(cmd)))


def git_diff_tree(scm,
                  beg_sha, # Not included in range
                  end_sha):
    cmd = [ scm.scm_path_, "diff-tree",
            "--root",             # Show initial commit as creation event.
            "--ignore-submodules",
            "-M",                 # Find renames.
            "-r", "%s..%s" % (beg_sha, end_sha) ]
    (stdout, stderr, rc) = drutil.execute(scm.verbose_, cmd)
    if rc == 0:
        return stdout
    else:
        drutil.fatal("%s: Unable to execute '%s'." %
                     (drutil.qualid_(), ' '.join(cmd)))


def git_rev_parse(scm, chg_id):
    assert(isinstance(chg_id, str))
    cmd = [ scm.scm_path_, "rev-parse", chg_id ]
    (stdout, stderr, rc) = drutil.execute(scm.verbose_, cmd)

    if rc == 0:
        return stdout
    else:
        drutil.fatal("%s: Unable to execute '%s'." %
                     (drutil.qualid_(), ' '.join(cmd)))


def git_get_status_short(scm, untracked):
    cmd = [ scm.scm_path_, "status",
            "--ignore-submodules", "--renames",
            "--untracked-files=%s" % (untracked), "--short" ]
    (stdout, stderr, rc) = drutil.execute(scm.verbose_, cmd)

    if rc == 0:
        return stdout
    else:
        drutil.fatal("%s: Unable to execute '%s'." %
                     (drutil.qualid_(), ' '.join(cmd)))


def git_get_commit_msg(scm, beg_sha, end_sha):
    cmd = [ scm.scm_path_, "show",
            "-s",
            "--format=%B",
            "%s..%s" % (beg_sha, end_sha) ]
    (stdout, stderr, rc) = drutil.execute(scm.verbose_, cmd)

    if rc == 0:
        return stdout
    else:
        drutil.fatal("%s: Unable to execute '%s'." %
                     (drutil.qualid_(), ' '.join(cmd)))


class ChangedFile(drscm.ChangedFile):
    def __init__(self, scm, action, base_file, modi_file):
        super().__init__(scm)
        self.action_ = action
        assert(isinstance(modi_file, drscm.FileInfo))
        self.modi_file_info_ = modi_file

        assert(isinstance(base_file, drscm.FileInfo))
        self.base_file_info_ = base_file

    def action(self):
        return self.action_

    def write_file(self, out_name, contents):
        assert(isinstance(contents, list))
        with open(out_name, "w") as fp:
            for l in contents:
                fp.write("%s\n" % (l))

    def copy_to_review_directory_(self, dest_dir, file_info):
        assert(isinstance(file_info, drscm.FileInfo))
        assert(not file_info.empty()) # Empty handled by caller.
        assert(git_is_blob(self.scm_, file_info))

        if file_info.chg_id_ is not None:
            contents = git_get_file_contents(self.scm_, file_info)
            out_name = self.output_name(dest_dir, file_info)
            self.create_output_dir(out_name)
            self.write_file(out_name, contents)
        else:
            out_name = self.output_name(dest_dir, file_info)
            self.create_output_dir(out_name)
            try:
                shutil.copyfile(file_info.rel_path_, out_name)
            except Exception as exc:
                # The on-disk file could not be copied.
                #
                # One cause of this is emacs .#<filename> files that
                # are created for unsaved modified files.
                #
                with open(out_name, "w") as fp:
                    fp.write("Unable to copy this file from the source tree to "
                             "the review directory.\n"
                             "\n"
                             "This template is used in its place.\n")


class ChangedFileUnstaged(ChangedFile):
    def __init__(self, scm, base_file, modi_file):
        super().__init__(scm, "unstaged", base_file, modi_file)

        # An unstaged file has a 2-stage diff.
        #
        # 1. The unstaged change with the staged version.
        # 2. The on-disk version with the in-git version.
        #
        # Here, the base file is the in-git version.

        staged_sha    = git_get_staged_file_blob_sha(scm, base_file.rel_path_)
        unstaged_sha  = git_get_unstaged_file_blob_sha(scm, base_file.rel_path_)
        head_sha      = git_get_head_file_blob_sha(scm, base_file.rel_path_)
        no_chgs       = (staged_sha == head_sha) and (staged_sha == unstaged_sha)
        unstaged_chgs = (staged_sha == head_sha) and (staged_sha != unstaged_sha)
        staged_chgs   = (staged_sha != head_sha) and (staged_sha == unstaged_sha)
        both_chgs     = (staged_sha != head_sha) and (staged_sha != unstaged_sha)

        if staged_chgs or both_chgs:
            # The file has staged changes; the difference between
            # unstaged and staged should be viewable.
            self.staged_file_ = drscm.FileInfo(base_file.rel_path_, staged_sha)
        else:
            self.staged_file_ = None

    def update_review_directory(self):
        super().update_review_directory()
        # What do do here?
        print("update_review_directory for an unstaged change.")


class ChangedFileDelete(ChangedFile):
    def __init__(self, scm, base_file, modi_file):
        super().__init__(scm, "delete", base_file, modi_file)


class ChangedFileRename(ChangedFile):
    def __init__(self, scm, base_file, modi_file):
        super().__init__(scm, "rename", base_file, modi_file)


class ChangedFileAdd(ChangedFile):
    def __init__(self, scm, base_file, modi_file):
        super().__init__(scm, "add", base_file, modi_file)


class ChangedFileAdd(ChangedFile):
    def __init__(self, scm, base_file, modi_file):
        super().__init__(scm, "add", base_file, modi_file)


class ChangedFileStaged(ChangedFile):
    def __init__(self, scm, base_file, modi_file):
        super().__init__(scm, "staged", base_file, modi_file)


class ChangedFileUntracked(ChangedFile):
    def __init__(self, scm, base_file, modi_file):
        super().__init__(scm, "untracked", base_file, modi_file)


class Git(drscm.SCM):
    def __init__(self, options):
        super().__init__(options)
        self.git_untracked_ = options.arg_git_untracked

    def process_numstat_output(self, stdout):
        files   = len(stdout)
        added   = 0
        deleted = 0
        for l in stdout:
            info = l.split('\t')
            if info[0][0] != '-':
                added   += int(info[0])
            if info[1][0] != '-':
                deleted += int(info[1])
        return (files, added, deleted)


# GitStaged:
#
#  An interface to Git that facilitates reviewing uncommitted changes.
#
class GitStaged(Git):
    def __init__(self, options):
        super().__init__(options)

    def get_unstaged_change_info(self):
        stdout = git_get_unstaged_numstat(self)
        return self.process_numstat_output(stdout)

    def get_staged_change_info(self):
        stdout = git_get_staged_numstat(self)
        return self.process_numstat_output(stdout)

    def get_changed_info_(self):
        (files, added, deleted) = self.get_unstaged_change_info()
        staged = "unstaged [%s files, %s lines]  " % (files, added + deleted)

        (files, added, deleted) = self.get_staged_change_info()
        unstaged = "staged [%s files  %s lines]" % (files, added + deleted)
        return staged + unstaged

    def parse_action(self, idx_ch, wrk_ch, rel_path):
        if (idx_ch == 'D') or (wrk_ch == 'D'):
            modi_file = drscm.FileInfoEmpty(rel_path)
            blob_sha  = git_get_most_recent_commit_blob(self, modi_file)
            base_file = drscm.FileInfo(rel_path, blob_sha)
            action    = ChangedFileDelete(self, base_file, modi_file)

        elif (idx_ch in (' ', 'A', 'M')) and (wrk_ch == 'M'):
            # Rename (idx_ch == 'R') is a special case that cannot be
            # processed by Unstaged.
            #
            modi_file = drscm.FileInfo(rel_path, None)
            blob_sha  = git_get_most_recent_commit_blob(self, modi_file)
            base_file = drscm.FileInfo(rel_path, blob_sha)
            action    = ChangedFileUnstaged(self, base_file, modi_file)

        elif (idx_ch == 'R') and (wrk_ch in (' ', 'M')):
            # The file has been renamed.
            # rel_path is of the form:
            #
            #  dr.d/dr.py -> scripts.d/dr.d/dr.py
            #
            parts         =  rel_path.split(' ')
            base_rel_path = parts[0]
            modi_rel_path = parts[2]
            modi_file     = drscm.FileInfo(modi_rel_path, None)
            base_file     = drscm.FileInfo(base_rel_path, None)
            blob_sha      = git_get_most_recent_commit_blob(self, base_file)
            base_file     = drscm.FileInfo(base_rel_path, blob_sha)
            action        = ChangedFileRename(self, base_file, modi_file)

        elif (idx_ch == 'A') and (wrk_ch == ' '):
            modi_file = drscm.FileInfo(rel_path, None)
            base_file = drscm.FileInfoEmpty(rel_path)
            action    = ChangedFileAdd(self, base_file, modi_file)

        elif (idx_ch == 'M') and wrk_ch == ' ':
            modi_file = drscm.FileInfo(rel_path, None)
            blob_sha  = git_get_most_recent_commit_blob(self, modi_file)
            base_file = drscm.FileInfo(rel_path, blob_sha)
            action    = ChangedFileStaged(self, base_file, modi_file)

        elif (idx_ch == '?') or (wrk_ch == '?'):
            modi_file = drscm.FileInfo(rel_path, None)
            base_file = drscm.FileInfoEmpty(rel_path)
            action    = ChangedFileUntracked(self, base_file, modi_file)

        else:
            raise NotImplementedError("Unknown action: '%s' '%s'  '%s'" %
                                      (idx_ch, wrk_ch, rel_path))

        return action;

    def generate_dossier_(self):
        # See the 'man git-status' for the meaning of the first two
        # characters for each line of output.
        #
        # The first character refers to the index (staged changes).
        # The second character refers to the working tree (unstaged changes).
        #
        result = [ ]
        stdout = git_get_status_short(self, self.git_untracked_)
        for l in stdout:
            i_ch     = l[0]
            w_ch     = l[1]
            rel_path = l[3:]
            action   = self.parse_action(i_ch, w_ch, rel_path)
            result.append(action)
        return result


# GitCommitted:
#
#  An interface to Git that facilitates reviewing committed changes.
#
class GitCommitted(Git):
    def __init__(self, options):
        super().__init__(options)

    # Returns a range that covers a single SHA, or a range of SHA values.
    def get_change_range(self):
        assert(isinstance(self.change_id_, str))
        stdout = git_rev_parse(self, self.change_id_)
        if len(stdout) == 1:
            # Single SHA specified; double it to get a full range.
            chg_id = "%s^..%s" % (self.change_id_, self.change_id_)
            stdout = git_rev_parse(self, chg_id)

        assert(len(stdout) == 2)
        # Remove leading '^' on second line of output.
        stdout[1] = stdout[1][1:]
        return (stdout[1],      # beg_sha  (not included in range).
                stdout[0])      # end_sha.


    def parse_action(self, action, base_file_sha, modi_file_sha, tail):
        assert(action in ('A', 'B', 'C', 'D', 'M', 'R', 'T', 'U', 'X'))

        if action == 'A':       # Add.
            assert(base_file_sha == "0000000000000000000000000000000000000000")
            modi_rel_path = tail[0]
            modi_file     = drscm.FileInfo(modi_rel_path, modi_file_sha)
            base_file     = drscm.FileInfoEmpty(modi_rel_path)
            action        = ChangedFile(self, "add", base_file, modi_file)

        elif action == 'B':     # Pairing broken.
            # It is not known how to generate this action.
            raise NotImplementedError("Pairing Broken action: %s" % (tail))

        elif action == 'C':     # Copy.
            # It is not known how to generate this action.
            raise NotImplementedError("Copy action: %s" % (tail))

        elif action == 'D':     # Delete.
            assert(modi_file_sha == "0000000000000000000000000000000000000000")
            base_rel_path = tail[0]
            modi_file     = drscm.FileInfoEmpty(base_rel_path)
            base_file     = drscm.FileInfo(base_rel_path, base_file_sha)
            action        = ChangedFile(self, "delete", base_file, modi_file)

        elif action == 'M':     # Modify.
            base_rel_path = tail[0]
            modi_file     = drscm.FileInfo(base_rel_path, modi_file_sha)
            base_file     = drscm.FileInfo(base_rel_path, base_file_sha)
            action        = ChangedFile(self, "modify", base_file, modi_file)

        elif action == 'R':    # Rename.
            base_rel_path = tail[0]
            modi_rel_path = tail[1]
            modi_file     = drscm.FileInfo(modi_rel_path, modi_file_sha)
            base_file     = drscm.FileInfo(base_rel_path, base_file_sha)
            action        = ChangedFile(self, "rename", base_file, modi_file)

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

    def get_changed_info_(self):
        (base_sha, modi_sha) = self.get_change_range()
        stdout = git_get_numstat(self, base_sha, modi_sha)
        (files, added, deleted) = self.process_numstat_output(stdout)
        msg = ("committed [%s files, %s lines]  " % (files, added + deleted))
        return msg

    def generate_dossier_(self):
        (beg_sha, end_sha) = self.get_change_range()

        self.commit_msg_ = git_get_commit_msg(self, beg_sha, end_sha)
        diff = git_diff_tree(self, beg_sha, end_sha)
        result = [ ]
        for l in diff:
            l = l.replace(' ', '\t') # Line has both space and tab.
            fields = l.split('\t')
            # fields[0]: base_file_mode
            # fields[1]: modi_file_mode
            base_file_sha  = fields[2]
            modi_file_sha  = fields[3]
            action         = fields[4]
            tail           = fields[5:] # Action and pathnames.

            operation = self.parse_action(action[0],
                                          base_file_sha, modi_file_sha, tail)
            result.append(operation)
        return result
