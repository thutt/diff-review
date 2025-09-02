# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import inspect
import os

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

    def __init__(self, scm_path, base_dir, modi_dir, cid, relative_pathname):
        assert((cid is None) or
               isinstance(cid, str)) # Change identifier

        self.scm_path_ = scm_path
        self.base_dir_ = base_dir
        self.modi_dir_ = modi_dir
        self.rel_path_ = relative_pathname
        self.revision_ = cid

    def action(self):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    def copy_file(self, review_base_dir, review_modi_dir):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    # previous_revision:
    #
    #   Returns the change id, on the same branch, at which
    #   self.rel_path_ was last revised.  If there is no previous
    #   revision, None is returned.
    #
    def previous_revision_id(self):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    # copy_previous_revision:
    #
    #   Copies the previous version of the file from the SCM to the
    #   directory indicated by 'dest_dir'.
    #
    # pre: os.path.exists(dest_dir)
    #
    def copy_previous_revision(self, dest_dir):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    # copy_current_revision:
    #
    #   Copies the current version of the file from the SCM to the
    #   directory indicated by 'dest_dir'.
    #
    # pre: os.path.exists(dest_dir)
    #
    def copy_current_revision(self, dest_dir):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))


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
        self.dossier_         = None

        if options.arg_scm == "git":
            self.scm_path_ = options.arg_git_path
        else:
            drutil.fatal("Unhandled path to SCM tool.")


    def generate_dossier_(self):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))

    def copy_files(self):
        for change in self.dossier_:
            change.copy_file(self.review_base_dir_, self.review_modi_dir_)

    def generate(self, options):
        self.generate_dossier_()
        self.copy_files()
            
