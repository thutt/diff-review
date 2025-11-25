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

        if os.path.exists(pathname):
            if os.access(pathname, os.R_OK):
                with open(pathname, "r") as fp:
                    return fp.read()
            else:
                result = [
                    "The file: ",
                    "",
                    "   '%s'" % (pathname),
                    "",
                    "is not readable by your account."
                ]
            return '\n'.join(result)
        else:
            result = [
                "The file: ",
                "",
                "   '%s'" % (pathname),
                "",
                "does not exist."
            ]
            return '\n'.join(result)
