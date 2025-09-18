# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import datetime
import inspect
import json
import os
import threading

import drutil


# FileInfo & FileInfoEmpty
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
#   inv: FileInfo.chg_id_ is     None   -> On-disk disk file.
#   inv: FileInfo.chg_id_ is not None   -> In-SCM file.
#
#   inv: not FileInfo.empty() -> File contents specified by rel_path_ and
#                                chg_id_
#   inv: FileInfo.empty()     -> File contents are empty file
#
class FileInfo(object):
    def __init__(self, rel_path, chg_id):
        assert(rel_path is not None)
        self.rel_path_ = rel_path
        self.chg_id_   = chg_id

    def empty(self):
        return False


class FileInfoEmpty(FileInfo):
    def __init__(self, rel_path):
        super().__init__(rel_path, None)

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

    def set_base_file_info(self, file_info):
        assert(isinstance(file_info, FileInfo))
        self.base_file_info_ = file_info

    def set_modi_file_info(self, file_info):
        assert(isinstance(file_info, FileInfo))
        self.modi_file_info_ = file_info

    def output_name(self, dest_dir, file_info):
        assert(isinstance(file_info, FileInfo))
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

    # This function copies 'file_info' into the review directory by
    # invoking the extension-implemented copy_to_review_directory_().
    # The called function will extract the file from the SCM, or from
    # the source client directory structure and copy it to the
    # destination directory.
    #
    # If the file is empty, an empty file is created.
    #
    def copy_to_review_directory(self, dest_dir, file_info):
        assert(isinstance(file_info, FileInfo))
        if not file_info.empty():
            self.copy_to_review_directory_(dest_dir, file_info)
        else:
            out_name = self.output_name(dest_dir, file_info)
            self.create_output_dir(out_name)
            with open(out_name, "w") as fp:
                pass

    # This function copies both the base and modified files into the
    # review directory.
    #
    def update_review_directory(self):
        self.copy_to_review_directory(self.scm_.review_base_dir_,
                                      self.base_file_info_)
        self.copy_to_review_directory(self.scm_.review_modi_dir_,
                                      self.modi_file_info_)


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
        self.change_id_       = options.arg_change_id
        self.review_dir_      = options.review_dir
        self.review_base_dir_ = options.review_base_dir
        self.review_modi_dir_ = options.review_modi_dir
        self.dossier_         = None # None -> no change to review.
        self.verbose_         = options.arg_verbose
        self.n_threads_       = options.arg_threads

        if options.arg_scm == "git":
            self.scm_path_ = options.arg_git_path
        else:
            drutil.fatal("Unhandled path to SCM tool.")

    # Returns a single string that represents the information about
    # the change that should be conveyed to the user.  For example the
    # number of files and lines changed.
    #
    # It should be formatted to fit on one (1) line of no more than 80
    # columns.
    #
    def get_changed_info_(self):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    def get_changed_info(self):
        result = self.get_changed_info_()
        assert(isinstance(result, str))
        return result

    # Examines the current source client, in addition to the command
    # line options, and returns a, possibly empty, list of ChangedFile
    # instances.  Each ChangedFile instance will describe a base file,
    # and a modified file that, together, can be compared to see the
    # differences make to a single file.
    #
    def generate_dossier_(self):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    def generate_dossier(self):
        dossier = self.generate_dossier_()
        if len(dossier) > 0:
            self.dossier_ = dossier

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

    def generate(self, options):
        self.generate_dossier()
        if self.dossier_ is not None:
            self.update_files_in_review_directory()

            now        = datetime.datetime.now()
            timestamp  = datetime.datetime.strftime(now, "%Y.%m.%d.%H.%M.%S")
            review_dir = os.path.join(options.arg_review_dir,
                                      options.arg_review_name)
            notes_file = os.path.join(options.arg_review_name,
                                      "notes-%s.text" % (timestamp))

            # Create a JSON dictionary that contains information about the
            # files written to the review directory.  This is used by the
            # 'view-review' program to display the review file-selection
            # menu.
            #
            info = {
                'root'  : self.review_dir_,
                'base'  : self.review_base_dir_,
                'modi'  : self.review_modi_dir_,
                'notes' : notes_file,
                'files' : [ ]
            }
            for f in self.dossier_:
                assert(f.modi_file_info_ is not None)
                assert(f.base_file_info_ is not None)

                finfo = {
                    'action'        : f.action(),
                    'modi_rel_path' : f.modi_file_info_.rel_path_,
                    'base_rel_path' : f.base_file_info_.rel_path_,
                }
                info['files'].append(finfo)

            fname = os.path.join(self.review_dir_, "diff.json")
            with open(fname, "w") as fp:
                json.dump(info, fp, indent = 2)
