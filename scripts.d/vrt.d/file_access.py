# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#


class FileAccess(object):
    def __init__(self, root):
        self.root_ = root

    def read(self, pathname):
        lines = self.read_(pathname)

        # Convert all line endings to a single '\n'.
        lines = lines.replace("\r\n", "\n") # Convert Windows files to Linux.
        lines = lines.replace("\r", "\n")   # Convert Mac files to Linux.
        result = lines.splitlines()

        # The returned list of strings will NOT have '\n' at the end.
        # Blank lines will be zero length.
        return result

    def read_(self, pathname):
        raise NotImplementedError("%s.read_() is not defined." %
                                  (self.__class__.__name__))
