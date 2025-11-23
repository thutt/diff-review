# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import datetime
import difflib
import diff_desc
import dumpir

def read_file(afr, path):
    lines = afr.read(path)
    result = lines.splitlines()
    # The returned list strings will NOT have '\n' at the end.
    # Blank lines will be zero length.
    return result


def create_difflib(afr, base, modi):
    base_l = read_file(afr, base)
    modi_l = read_file(afr, modi)
    return (difflib.SequenceMatcher(None, base_l, modi_l),
            base_l,
            modi_l)


def decode_opinfo(label, opc, base_l, b_beg, b_end, modi_l, m_beg, m_end):
    assert(opc in ('replace', 'delete', 'insert', 'equal'))
    print("%10s: %8s  beg: [%d, %d)  mod: [%d, %d)" %
          (label, opc, b_beg, b_end, m_beg, m_end))

    if opc == "replace":
        # Nothing can be asserted here.
        print("replace:")
        for l in base_l:
            print("  %s" % (l))
        for l in modi_l:
            print("  %s" % (l))
    elif opc == "delete":
        assert((m_end - m_beg) == 0) # No lines in modified file.
    elif opc == "insert":
            assert((b_end - b_beg) == 0) # No lines in base file.
    elif opc == "equal":
        assert((b_end - b_beg) == (m_end - m_beg)) # Equal number of lines.

    if False:
        for l in base_l:
            print("  base: %s" % (l))

        print("")
        for l in modi_l:
            print("  modi: %s" % (l))


def add_equal_line_region(desc, base_l, modi_l):
    assert(len(base_l) == len(modi_l))

    for l_idx in range(0, len(base_l)):
        # Cannot use same descriptor for equal lines because line
        # number will be incremented wrong.
        b_desc = diff_desc.Line(base_l[l_idx])
        m_desc = diff_desc.Line(modi_l[l_idx])

        b_desc.runs_tabs_ += diff_desc.find_tab_runs(b_desc,
                                                     0, len(b_desc.line_))
        m_desc.runs_tabs_ += diff_desc.find_tab_runs(m_desc,
                                                     0, len(m_desc.line_))
        b_desc.runs_tws_  += diff_desc.find_trailing_whitespace(b_desc)
        m_desc.runs_tws_  += diff_desc.find_trailing_whitespace(m_desc)

        desc.cache_base(b_desc)
        desc.cache_modi(m_desc)
        desc.flush(0, False, None)

def add_deleted_line_region(desc, base_l):
    for l_idx in range(0, len(base_l)):
        l_desc             = diff_desc.Line(base_l[l_idx])
        l_desc.runs_tabs_ += diff_desc.find_tab_runs(l_desc,
                                                     0, len(l_desc.line_))
        l_desc.runs_tws_  += diff_desc.find_trailing_whitespace(l_desc)

        desc.cache_base(l_desc)
        desc.cache_modi(diff_desc.NotPresentDelete())
        desc.flush(0, False, None)


def add_inserted_line_region(desc, modi_l):
    for l_idx in range(0, len(modi_l)):
        l_desc = diff_desc.Line(modi_l[l_idx])
        l_desc.runs_tabs_ += diff_desc.find_tab_runs(l_desc,
                                                     0, len(l_desc.line_))
        l_desc.runs_tws_  += diff_desc.find_trailing_whitespace(l_desc)
        desc.cache_base(diff_desc.NotPresentAdd())
        desc.cache_modi(l_desc)
        desc.flush(0, False, None)


def add_replaced_line_region(desc, base_l, modi_l, intraline_threshold):
    len_base  = len(base_l)
    len_modi  = len(modi_l)
    l_changed = min(len_base, len_modi) # Lines changed in both files.

    # Find intraline differences for each common line in the sequence.
    #
    # The remaining information is:
    #
    #   Whole line deletions if  len(base_l)  > len(modi_l).
    #   Whole line insertions if  len(base_l) < len(modi_l).

    for k in range(0, l_changed):
        l_base  = diff_desc.Line(base_l[k])
        l_modi  = diff_desc.Line(modi_l[k])
        matcher = difflib.SequenceMatcher(None, base_l[k], modi_l[k])
        match_ratio = matcher.ratio()
        if match_ratio < intraline_threshold:
            # Don't end up with crazy 'technicolor vomit' diffs when
            # the threshold to display intraline diffs is not met.
            # Instead, the lines are in a change block, with a
            # particular background.  Set them to normal text, and let
            # the background color do the work.
            l_base.runs_tabs_ += diff_desc.find_tab_runs(l_base, 0,
                                                         len(l_base.line_))
            l_base.runs_tws_  += diff_desc.find_trailing_whitespace(l_base)

            l_modi.runs_tabs_ += diff_desc.find_tab_runs(l_modi, 0,
                                                         len(l_modi.line_))
            l_modi.runs_tws_  += diff_desc.find_trailing_whitespace(l_modi)
        else:
            for opinfo in matcher.get_opcodes():
                opc   = opinfo[0]  # inv: ('replace', 'delete', 'insert', 'equal').
                b_beg = opinfo[1]  # base begin index.
                b_end = opinfo[2]  # base end index.
                m_beg = opinfo[3]  # modi begin index.
                m_end = opinfo[4]  # modi end index.

                if opc == "replace":
                    # Intraline change.
                    l_base.runs_intraline_ += [
                        diff_desc.TextRunIntraline(b_beg,
                                                   b_end - b_beg)
                    ]
                    l_base.runs_tabs_ += diff_desc.find_tab_runs(l_base, b_beg,
                                                                 b_end - b_beg)
                    l_base.runs_tws_  += diff_desc.find_trailing_whitespace(l_base)

                    l_modi.runs_intraline_ += [
                        diff_desc.TextRunIntraline(m_beg,
                                                   m_end - m_beg)
                    ]
                    l_modi.runs_tabs_ += diff_desc.find_tab_runs(l_modi, m_beg,
                                                                 m_end - m_beg)
                    l_modi.runs_tws_  += diff_desc.find_trailing_whitespace(l_modi)
                elif opc == "delete":
                    assert((m_end - m_beg) == 0) # Characters deleted.
                    r_len = b_end - b_beg
                    l_base.runs_deleted_ += [ 
                        diff_desc.TextRunDeleted(b_beg, r_len)
                    ]
                    l_base.runs_tabs_ += diff_desc.find_tab_runs(l_base,
                                                                 b_beg, r_len)
                    l_base.runs_tws_  += diff_desc.find_trailing_whitespace(l_base)
                elif opc == "insert":
                    assert((b_end - b_beg) == 0) # Characters added.
                    l_modi.runs_added_ += [
                        diff_desc.TextRunAdded(m_beg, m_end - m_beg)
                    ]
                    l_modi.runs_tabs_ += diff_desc.find_tab_runs(l_modi, m_beg,
                                                                 m_end - m_beg)
                    l_modi.runs_tws_  += diff_desc.find_trailing_whitespace(l_modi)
                elif opc == "equal":
                    assert((b_end - b_beg) == (m_end - m_beg)) # Equal run
                    l_base.runs_tabs_ += diff_desc.find_tab_runs(l_base, b_beg,
                                                                 b_end - b_beg)
                    l_base.runs_tws_  += diff_desc.find_trailing_whitespace(l_base)

                    l_modi.runs_tabs_ += diff_desc.find_tab_runs(l_modi, m_beg,
                                                                 m_end - m_beg)
                    l_modi.runs_tws_  += diff_desc.find_trailing_whitespace(l_modi)
        
        desc.cache_base(l_base)
        desc.cache_modi(l_modi)
        desc.flush(0, False, None)

    if len_base < len_modi:
        # These are all line insertions in the modified file.
        assert(l_changed <= len_modi)
        for k in range(l_changed, len_modi):
            l_modi             = diff_desc.Line(modi_l[k])
            l_modi.runs_tabs_ += diff_desc.find_tab_runs(l_modi,
                                                         0, len(modi_l[k]))
            l_modi.runs_tws_  += diff_desc.find_trailing_whitespace(l_modi)
            desc.cache_base(diff_desc.NotPresentAdd())
            desc.cache_modi(l_modi)
            desc.flush(0, False, None)
    elif len_base > len_modi:
        # These are all line deletions from the modified file.
        assert(l_changed <= len_base)
        for k in range(l_changed, len_base):
            l_base = diff_desc.Line(base_l[k])
            l_base.runs_tabs_ += diff_desc.find_tab_runs(l_base,
                                                         0, len(base_l[k]))
            l_base.runs_tws_  += diff_desc.find_trailing_whitespace(l_base)
            desc.cache_base(l_base)
            desc.cache_modi(diff_desc.NotPresentDelete())
            desc.flush(0, False, None)
    else:
        pass                    # NOP; no residual lines.



def create_diff_descriptor(afr, verbose, intraline_percent,
                           dump_ir, base, modi):
    if False:
        beg = datetime.datetime.now()
    desc  = diff_desc.DiffDesc(verbose, intraline_percent)
    marks = ""

    # Turn diffs create_difflib() generator into useful structure.
    (matcher, base_l, modi_l) = create_difflib(afr, base, modi)

    # Examines the file as a whole.
    for opinfo in matcher.get_opcodes():
        opc   = opinfo[0]  # inv: ('replace', 'delete', 'insert', 'equal').
        b_beg = opinfo[1]  # base begin index.
        b_end = opinfo[2]  # base end index.
        m_beg = opinfo[3]  # modi begin index.
        m_end = opinfo[4]  # modi end index.

        assert(opc in ('replace', 'delete', 'insert', 'equal'))
        desc.add_base_region(opc, b_beg, b_end - b_beg)
        desc.add_modi_region(opc, m_beg, m_end - m_beg)

        if opc == "equal":
            assert((b_end - b_beg) == (m_end - m_beg)) # Equal number of lines.
            add_equal_line_region(desc, base_l[b_beg:b_end], modi_l[m_beg:m_end])
        elif opc == "delete":
            assert((m_end - m_beg) == 0) # No lines in modified file.
            add_deleted_line_region(desc, base_l[b_beg:b_end])
        elif opc == "insert":
            assert((b_end - b_beg) == 0) # No lines in base file.
            add_inserted_line_region(desc, modi_l[m_beg:m_end])
        else:
            assert(opc == "replace")
            add_replaced_line_region(desc,
                                     base_l[b_beg:b_end],
                                     modi_l[m_beg:m_end],
                                     intraline_percent)

    if False:
        end = datetime.datetime.now()
        print("create_diff_descriptor: %s: %s" % (end - beg, base))

    if dump_ir is not None:
        dumpir.dump(dump_ir, base, modi, desc)

    return desc

