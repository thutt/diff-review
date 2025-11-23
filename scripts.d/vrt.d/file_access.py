# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#


class FileAccess(object):
    def __init__(self, root):
        self.root_ = root

    def read(self, pathname):
        raise NotImplementedError("read() is not defined.")
        
