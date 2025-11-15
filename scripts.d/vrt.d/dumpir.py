# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import os

import diff_desc

def dumplines(pathname, info):
    with open(pathname, "w") as fp:
        fp.write("Regions:\n")
        i = 0
        for rgn in info.regions_:
            rgn.ir_number_ = i
            fp.write("  %3d. %s\n" % (i, rgn))
            i += 1

        fp.write("\n\nLines:\n")
        for l in info.lines_:
            line_len = len(l.line_)

            fp.write("%-5d  <%s>\n" % (l.line_num_, l.line_))
            fp.write("  len: %d\n" % (line_len))
            if l.region_ is not None:
                fp.write("  rgn: %d  %s\n" % (l.region_.ir_number_,
                                              str(l.region_)))
            else:
                fp.write("  rgn: none\n")

            run = [ ]

            total_len  = 0
            last_start = 0
            last_len   = 0
            for r in l.runs_:
                errors = set()
                start_ = r.start_
                len_   = r.len_

                total_len += len_

                if len_ == 0:
                    errors.add("len")

                if start_ != last_start + last_len:
                    errors.add("start")
                last_start = start_
                last_len   = len_
                if len(errors) == 0:
                    run.append("%s" % (r))
                else:
                    run.append("%s <err>: %s" % (r, errors))

            if total_len == line_len:
                fp.write("  run: %s\n\n" % ("  ".join(run)))
            else:
                fp.write("  run: %s  <err>: total len\n\n" % ("  ".join(run)))

def dump(rootdir, base, modi, desc):
    assert(rootdir is not None)
    assert(os.path.exists(base))
    assert(os.path.exists(modi))
    assert(isinstance(desc, diff_desc.DiffDesc))

    
    base_n = os.path.join(rootdir, "dr-base.%s.text" % (os.path.basename(base)))
    modi_n = os.path.join(rootdir, "dr-modi.%s.text" % (os.path.basename(modi)))

    dumplines(base_n, desc.base_)
    dumplines(modi_n, desc.modi_)
