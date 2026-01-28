# Copyright (c) 2025, 2026  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import datetime
import getpass
import inspect
import json
import os
import threading

import drutil


# FileInfoBase, FileInfo, FileInfoSha & FileInfoEmpty
#
#   These two classes provide references to files in the source
#   client.  A FileInfo instance refers to a file on-disk, or in the
#   SCM.
#
#   A FileInfoEmptyFile instance refers to a file that doesn't
#   actually exist, but is needed to provide the diffing tool with a
#   on-disk file to compare against.  When a file represented by this
#   class is copied, an empty file will be created.  An empty file
#   does not has an associated SCM change id.
#
#   inv: FileInfo.rel_path_ is not None
#
#   inv: FileInfo.empty()             -> FileInfo.chg_id_ a special sentinel
#
#   inv: not FileInfo.empty() and
#        FileInfo.chg_id_ is None     -> On-disk disk file.
#
#   inv: not FileInfo.empty() and
#        FileInfo.chg_id_ is not None -> In-SCM file.
#
#   inv: not FileInfo.empty()         -> File contents specified by
#                                        rel_path_ and chg_id_
#
#   inv: FileInfo.empty()             -> File contents are empty file,
#                                        with a special FileInfo.chg_id_
#
class FileInfoBase(object):
    def __init__(self, display_path, rel_dir, rel_path, chg_id):
        assert(chg_id is None or isinstance(chg_id, str))
        self.rel_dir_      = rel_dir
        self.rel_path_     = rel_path
        self.chg_id_       = chg_id
        self.display_path_ = display_path

    def empty(self):
        return False

    def get_dossier_representation(self):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    def dossier_chg_id(self):
        return (self.rel_dir_, self.chg_id_)

    def display_path(self):
        assert(self.display_path_ is not None)
        return self.display_path_


class FileInfo(FileInfoBase):
    def __init__(self, display_path, rel_dir, rel_path):
        super().__init__(display_path, rel_dir, rel_path, None)

    def get_dossier_cache_key(self):
        return self.rel_path_

    def get_dossier_representation(self):
        return (self.display_path_, self.rel_dir_, self.rel_path_)


class FileInfoSha(FileInfoBase): # XXX Rename ChgId
    def __init__(self, display_path, rel_dir, cache_key, chg_id):
        super().__init__(display_path, rel_dir, None, chg_id)
        self.cache_key_ = cache_key

    def get_dossier_cache_key(self):
        return self.cache_key_

    def get_dossier_representation(self):
        return (self.display_path_, self.rel_dir_, self.chg_id_)


class FileInfoEmpty(FileInfoSha):
    n_instances_     = 0
    empty_file_name_ = '_______________EMPTY_FILE_______________'

    def __init__(self, display_path, rel_dir):
        # This empty_file_name_ is 'change id' used as a sentinel used
        # for emtpy files.  It will not conflict with a real change
        # id, but can be shared by all files that are empty.
        self.instance_ = FileInfoEmpty.n_instances_
        FileInfoEmpty.n_instances_ += 1

        # The cache key must be used here so the index into "cache" is
        # correct for the changed file that is referencing the empty
        # file.
        cache_key = "%s%s" % (FileInfoEmpty.empty_file_name_[:-5],
                              "%5.5d" % self.instance_)
        super().__init__(display_path, rel_dir,
                         cache_key, FileInfoEmpty.empty_file_name_)

    def get_dossier_representation(self):
        return (self.display_path_, self.rel_dir_, self.chg_id_, self.cache_key_)

    def empty(self):
        return True


# ChangedFile is an abstract class that must be extended for an
# implementation.  It is used to encapsulate the state of files
# on-disk and in the SCM.  This is used to determine the operations
# that must be invoked to copy the last revision and the current
# revision of files to the review directory.
#
# For example, an 'added' file has no previous revision, so an empty
# file will be created for it.  The current on-disk file represents
# the current revision and it will be copied to the appropirate review
# directory.
#
# Each SCM will have its own set of classes to implement file
# operations.  See drgit.py for examples.
#
class ChangedFile(object):
    # qualid: Produces a qualified identifier using the class
    #         instance name and the calling functions name.
    #
    # For internal use only.
    def qualid_(self):
        return "%s.%s" % (type(self).__name__,
                          inspect.stack()[1].function)

    def __init__(self, scm):
        assert(isinstance(scm, SCM))
        self.scm_ = scm

        # inv: modi_file_info_ is not None
        #
        # Describes the modified file in a change.
        #
        # inv: rel_path_ is not None
        # inv: chg_id_   is not None -> chg_id_ is a blob commit of the file.
        # inv: chg_id_   is None     -> file is in the source directory tree
        #
        self.modi_file_info_   = None

        # inv: base_file_info_ is not None
        #
        # Describes the base file in a change.
        #
        # inv: rel_path_ is not None
        # inv: chg_id_   is not None -> chg_id_ is a blob commit of the file.
        # inv: chg_id_   is None     -> the file doesn't exist in the SCM.
        #
        self.base_file_info_   = None

    def output_name(self, dest_dir, file_info):
        assert(isinstance(file_info, FileInfoBase))
        return os.path.join(dest_dir, file_info.rel_path_)

    def create_output_dir(self, out_name):
        out_dir = os.path.dirname(out_name)
        if not os.path.exists(out_dir):
            drutil.mktree(out_dir)

    # This function must be implemented by an extension of this
    # type.  It is called when needing to know the operation that
    # is being performed on the file (add, delete, modify, etc.)
    #
    def action(self):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    # This function copies 'file_info' into the review directory.
    # 'file_info' might need to be checked out from the SCM.
    #
    # If the file is empty, an empty file is created.
    #
    def copy_to_review_directory_(self, dest_dir, file_info):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    # This function gets the contents of the 'chg_id_' field of 'file_info'.
    #
    def get_change_contents_(self, scm, file_info):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    def get_change_contents(self, scm, file_info):
        return self.get_change_contents_(scm, file_info)

    def create_empty_file(self, dest_dir, file_info):
        out_name = self.output_name(dest_dir, file_info)
        self.create_output_dir(out_name)
        with open(out_name, "w") as fp:
            pass

    # This function copies 'file_info' into the review directory by
    # invoking the extension-implemented copy_to_review_directory_().
    # The called function will extract the file from the SCM, or from
    # the source client directory structure and copy it to the
    # destination directory.
    #
    # If the file is empty, an empty file is created.
    #
    def copy_to_review_directory(self, dest_dir, file_info):
        assert(isinstance(file_info, FileInfoBase))
        if not file_info.empty():
            # Copy non-empty file.
            self.copy_to_review_directory_(dest_dir, file_info)
        else:
            self.create_empty_file(dest_dir, file_info)

    def copy_to_review_sha_directory(self, file_info):
        assert(isinstance(file_info, FileInfoBase))
        assert(file_info.chg_id_ is not None) # Only uncommitted files have no chg_id_

        fname = os.path.join(self.scm_.review_sha_dir_, file_info.chg_id_)
        self.create_output_dir(fname)

        if not os.path.exists(fname):
            contents = ""
            if not file_info.empty():
                contents = self.get_change_contents(self.scm_, file_info)
                contents = '\n'.join(contents)

            with open(fname, "w") as fp:
                fp.write(contents)

    # This function copies both the base and modified files into the
    # review directory.
    #
    def update_review_directory(self):
        self.copy_to_review_sha_directory(self.base_file_info_)

        if self.modi_file_info_.chg_id_ is not None:
            self.copy_to_review_sha_directory(self.modi_file_info_)
        else:
            # No chg_id_ means no blob sha; copy physical file.
            self.copy_to_review_directory(self.scm_.review_modi_dir_,
                                          self.modi_file_info_)

    def get_dossier_representation_(self):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    def get_dossier_representation(self):
        return self.get_dossier_representation_()

    def get_file_gungla_(self):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    def get_file_gungla(self):
        return self.get_file_gungla_()

    def add_dossier_files_(self, info, file_info):
        finfo        = file_info.get_dossier_representation()
        display_path = finfo[0]
        rel_dir      = finfo[1]
        pathname     = finfo[2]
        key          = pathname
        if len(finfo) > 3:
            # Special case:
            #
            #  Files that are 'empty' are all represented by a single
            #  on-disk file in the sha.d directory, but all have a
            #  unique display_path.  To allow this the empty file adds
            #  a fourth element to this value that will be a unique
            #  key value, and that provides multiple display_path
            #  values for a single on-disk file.
            #
            # This is a terrible interface, since a higher level
            # abstraction (drgit) is affecting this lower-level
            # abstraction.
            #
            key = finfo[3]

        if key not in info["cache"]:
            info["cache"][key] = {
                "display_path": display_path,
                "rel_dir"     : rel_dir,
                "pathname"    : pathname
            }

# SCM
#
#  This is an abstract class that is used as an interface to the SCM.
#
#  The generate_dossier_ method must be implemented by an SCM
#  interface, and it must return a list of ChangedFile instances.
#
class SCM(object):
    # qualid: Produces a qualified identifier using the class
    #         instance name and the calling functions name.
    #
    # For internal use only.
    def qualid_(self):
        return "%s.%s" % (type(self).__name__,
                          inspect.stack()[1].function)

    def __init__(self, options):
        self.review_name_      = options.arg_review_name
        self.review_dir_       = options.review_dir
        self.review_sha_dir_   = options.review_sha_dir
        self.review_modi_dir_  = options.review_modi_dir
        self.dossier_          = None # None -> no change to review.
        self.verbose_          = options.arg_verbose
        self.n_threads_        = options.arg_threads
        self.commit_msg_       = None # Change description /
                                      # commit message, if present.
        self.commit_msg_file_  = None # Pathname of file.
        self.commit_summary_   = None # First line of commit message.
        self.dossier_mode_     = self.get_dossier_mode()
        self.scm_name_         = self.get_name()

        if options.arg_scm == "git":
            self.scm_path_ = options.arg_git_path
        else:
            drutil.fatal("Unhandled path to SCM tool.")

    def get_name_(self):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    def get_dossier_mode_(self):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    def get_name(self):
        return self.get_name_()

    def get_dossier_mode(self):
        mode = self.get_dossier_mode_()

        # There are two dossier formats that must be processed by
        # view-review-tabs (vrt).  If a new SCM is added, and a new
        # mode is added, vrt will need to be updated.
        assert(mode in ("committed",    # Dossier: committed change.
                        "uncommitted")) # Dossier: uncommitted change.
        return mode

    # Returns a single string that represents the information about
    # the change that should be conveyed to the user.  For example the
    # number of files and lines changed.
    #
    # It should be formatted to fit on one (1) line of no more than 80
    # columns.
    #
    def get_changed_info_(self, change_id):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    def get_changed_info(self, change_id):
        result = self.get_changed_info_(change_id)
        assert(isinstance(result, str))
        return result

    # Examines the current source client, in addition to the command
    # line options, and returns a, possibly empty, list of ChangedFile
    # instances.  Each ChangedFile instance will describe a base file,
    # and a modified file that, together, can be compared to see the
    # differences make to a single file.
    #
    def generate_dossier_(self, change_id):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    def generate_dossier(self, change_id):
        dossier = self.generate_dossier_(change_id)
        if len(dossier) > 0:
            self.dossier_ = dossier

    def get_revision_key_(self, chg_id):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    def get_revision_key(self, chg_id):
        return self.get_revision_key_(chg_id)

    def copy_file(self, dummy, changed_file, semaphore):
        changed_file.update_review_directory()
        semaphore.release()

    def update_files_in_review_directory(self):
        n_semaphore = self.n_threads_
        semaphore   = threading.Semaphore(n_semaphore)
        processes   = [ ]
        running     = [ ]
        for changed_file in self.dossier_:
            p = threading.Thread(target = self.copy_file,
                                 args   = (self,
                                           changed_file, semaphore))
            processes.append(p)
            semaphore.acquire()
            p.start()

        for p in processes:
            p.join()

    def get_change_revision(self, info, commit_msg_file):
        now       = datetime.datetime.now()
        timestamp = datetime.datetime.strftime(now, "%Y.%m.%d.%H.%M.%S")
        revision  = {
            "time"           : timestamp,
            "commit_msg"     : self.commit_msg_file_, # Can be None
            "commit_summary" : self.commit_summary_,
            "files"          : [ ]
        }

        for f in self.dossier_:
            assert(isinstance(f, ChangedFile))
            assert(f.modi_file_info_ is not None)
            assert(f.base_file_info_ is not None)

            finfo = f.get_dossier_representation()
            revision["files"].append(finfo)

        return revision

    def create_dossier_files(self, info):
        for f in self.dossier_:
            f.create_dossier_files_(info)

    def get_dossier_pathname(self):
        return os.path.join(self.review_dir_, "dossier.json")

    def create_json_dictionary(self, chg_id):
        # Create a JSON dictionary that contains information about the
        # files written to the review directory.  This is used by the
        # 'view-review' program to display the review file-selection
        # menu.
        #
        info = {
            "version"     : 2,
            "scm"         : self.scm_name_,
            "mode"        : self.dossier_mode_,
            "user"        : getpass.getuser(),
            "name"        : self.review_name_,
            "root"        : self.review_dir_,
            "order"       : self.ordered_, # Ordered revisions in 'revisions'.
            "revisions"   : { },
            "cache"       : { },
        }

        revision = self.get_change_revision(info, self.commit_msg_file_)
        key      = self.get_revision_key(chg_id)

        if key not in info["revisions"]:
            info["revisions"][key] = revision
        else:
            drutil.fatal("What does this failure mean?  Change re-added?")

        self.create_dossier_files(info)
        return info


    def load_existing_dossier(self):
        # If the dossier exists, and this is a revision extension,
        # load it.
        if self.dossier_mode_ != "committed":
            return (None, None, None)

        dossier_path = self.get_dossier_pathname()
        dossier      = None
        if os.path.exists(dossier_path):
            with open(dossier_path, "r") as fp:
                dossier = json.load(fp)

        if dossier is not None:
            if dossier["version"] != 2:
                drutil.fatal("Existing dossier is not version 2.")
                
            if dossier["mode"] != "committed":
                return (None, None, None) # No information.  Start new dossier.
            return (dossier["order"], dossier["revisions"], dossier["cache"])
        else:
            return (None, None, None)

    def write_dossier(self, chg_id):
        (order,
         revisions,
         cache) = self.load_existing_dossier()
        dossier = self.create_json_dictionary(chg_id)
 
        if (order is not None and
            revisions is not None and
            cache is not None):
            # Copy revision information from existing dossier.
            for key in order:
                if key not in dossier["revisions"]:
                    dossier["revisions"][key] = revisions[key]

            # Copy cache information from existing dossier.
            for key in cache.keys():
                if key not in dossier["cache"]:
                    dossier["cache"][key] = cache[key]

        dossier_name = self.get_dossier_pathname()
        with open(dossier_name, "w") as fp:
            json.dump(dossier, fp, indent = 2)

    def generate(self, options, change_id):
        self.generate_dossier(change_id)
        if self.dossier_ is not None:
            self.update_files_in_review_directory()

            review_dir = os.path.join(options.arg_review_dir,
                                      options.arg_review_name)

            if self.commit_msg_ is not None:
                # Write commit message / change description file.
                self.commit_msg_file_ = "commit_msg_%s.text" % (change_id)
                with open(os.path.join(self.review_dir_,
                                       self.commit_msg_file_), "w") as fp:
                    for l in self.commit_msg_:
                        fp.write("%s\n" % (l))
            else:
                self.commit_msg_file_ = None
