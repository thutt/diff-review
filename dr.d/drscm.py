# Copyright (c) 2025  Logic Magicians Software.
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import inspect 

class SCM(object):
    # qualid: Produces a qualified identifier using the class
    #         instance name and the calling functions name.
    #
    # For internal use only.
    def qualid_(self):
        return "%s.%s" % (type(self).__name__,
                          inspect.stack()[1].function)

    def __init__(self):
        pass

    def dossier(self):
        raise NotImplementedError("%s: not implemented" % (self.qualid_()))
