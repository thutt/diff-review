# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import os

import file_access

class LocalFileAccess(file_access.FileAccess):
    def __init__(self, root):
        super().__init__(root)

    def read_(self, pathname):
        pathname = os.path.join(self.root_, pathname)

        with open(pathname, "r") as fp:
            lines = fp.read()

        return lines
