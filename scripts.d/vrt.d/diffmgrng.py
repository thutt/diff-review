# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import datetime
import difflib
import diff_desc

global NPD
global NPA
NPA   = diff_desc.NotPresentAdd()        # Only one instance needed.
NPD   = diff_desc.NotPresentDelete()     # Only one instance needed.


def read_file(path):
    with open(path, "r") as fp:
        # Convert all line endings to a single '\n'.
        lines = fp.read()

    lines = lines.replace("\r\n", "\n") # Convert Windows files to Linux.
    lines = lines.replace("\r", "\n")   # Convert Mac files to Linux.

    result = lines.splitlines()
    # The returned list strings will NOT have '\n' at the end.
    # Blank lines will be zero length.
    return result


def create_difflib(base, modi):
    base_l = read_file(base)
    modi_l = read_file(modi)
    return (difflib.SequenceMatcher(None, base_l, modi_l),
            base_l,
            modi_l)


def line_fields(line):          # XXX remove
    return (line[0:2], line[2:])


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


def create_line_desc(opc, line):
    assert(isinstance(line, str))

    l_desc = diff_desc.Line(line)
    r_beg  = 0
    r_end  = len(line)
    r_len  = r_end - r_beg

    # Make a single run that covers the whole line.  finalize_runs()
    # will be invoked to add TAB and TRAILING_WS runs when the line is
    # cached.
    #
    run = diff_desc.make_text_run(opc, r_beg, r_len)
    run = diff_desc.amend_run_with_tab(l_desc, run)


    l_desc.runs_ = run
    return l_desc


def add_equal_line_region(desc, base_l, modi_l):
    assert(len(base_l) == len(modi_l))

    for l_idx in range(0, len(base_l)):
        l_desc = create_line_desc(0, base_l[l_idx])
        desc.cache_base(l_desc)
        desc.cache_modi(l_desc)
        desc.flush(0, False, None)
        l_desc.uncolored_ = len(l_desc.runs_) == 1

def add_deleted_line_region(desc, base_l):
    for l_idx in range(0, len(base_l)):
        l_desc = create_line_desc(2, base_l[l_idx])
        desc.cache_base(l_desc)
        desc.cache_modi(NPD)
        desc.flush(0, False, None)


def add_inserted_line_region(desc, modi_l):
    for l_idx in range(0, len(modi_l)):
        l_desc = create_line_desc(1, modi_l[l_idx])
        desc.cache_base(NPA)
        desc.cache_modi(l_desc)
        desc.flush(0, False, None)


def add_replaced_line_region(desc, base_l, modi_l):
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
        for opinfo in matcher.get_opcodes():
            opc   = opinfo[0]  # inv: ('replace', 'delete', 'insert', 'equal').
            b_beg = opinfo[1]  # base begin index.
            b_end = opinfo[2]  # base end index.
            m_beg = opinfo[3]  # modi begin index.
            m_end = opinfo[4]  # modi end index.

            # The runs that are created here can be split by
            # finalize_runs() when the line is cached.
            #
            if opc == "replace":
                # Intraline change.
                b_run = diff_desc.TextRunIntraline(b_beg, b_end - b_beg)
                b_run = diff_desc.amend_run_with_tab(l_base, b_run)
                m_run = diff_desc.TextRunIntraline(m_beg, m_end - m_beg)
                m_run = diff_desc.amend_run_with_tab(l_modi, m_run)
                l_base.runs_ += b_run
                l_modi.runs_ += m_run
            elif opc == "delete":
                assert((m_end - m_beg) == 0) # Characters deleted.
                b_run = diff_desc.TextRunDeleted(b_beg, b_end - b_beg)
                b_run = diff_desc.amend_run_with_tab(l_base, b_run)
                l_base.runs_ += b_run
            elif opc == "insert":
                assert((b_end - b_beg) == 0) # Characters added.
                m_run = diff_desc.TextRunAdded(m_beg, m_end - m_beg, True)
                m_run = diff_desc.amend_run_with_tab(l_modi, m_run)
                l_modi.runs_ += m_run
            elif opc == "equal":
                assert((b_end - b_beg) == (m_end - m_beg)) # Equal run
                b_run = diff_desc.TextRunNormal(b_beg, b_end - b_beg)
                b_run = diff_desc.amend_run_with_tab(l_base, b_run)
                m_run = diff_desc.TextRunNormal(m_beg, m_end - m_beg)
                m_run = diff_desc.amend_run_with_tab(l_modi, m_run)
                l_base.runs_ += b_run
                l_modi.runs_ += m_run

        desc.cache_base(l_base)
        desc.cache_modi(l_modi)
        desc.flush(0, False, None)

    if len_base < len_modi:
        # These are all line insertions in the modified file.
        assert(l_changed <= len_modi)
        for k in range(l_changed, len_modi):
            l_modi = diff_desc.Line(modi_l[k])
            m_run  = diff_desc.TextRunAdded(0, len(modi_l[k]), True)
            m_run  = diff_desc.amend_run_with_tab(l_modi, m_run)
            l_modi.runs_ += m_run
            desc.cache_base(NPA)
            desc.cache_modi(l_modi)
            desc.flush(0, False, None)

    elif len_base > len_modi:
        # These are all line deletions from the modified file.
        assert(l_changed <= len_base)
        for k in range(l_changed, len_base):
            l_base = diff_desc.Line(base_l[k])
            b_run  = diff_desc.TextRunDeleted(0, len(base_l[k]))
            b_run  = diff_desc.amend_run_with_tab(l_base, b_run)
            l_base.runs_ += b_run
            desc.cache_modi(NPD)
            desc.cache_base(l_base)
            desc.flush(0, False, None)
    else:
        pass                    # NOP; no residual lines.



def create_diff_descriptor(verbose, base, modi):
    if False:
        beg = datetime.datetime.now()
    desc  = diff_desc.DiffDesc(verbose)
    marks = ""

    # Turn diffs create_difflib() generator into useful structure.
    (matcher, base_l, modi_l) = create_difflib(base, modi)

    # Examines the file as a whole.
    for opinfo in matcher.get_opcodes():
        opc   = opinfo[0]  # inv: ('replace', 'delete', 'insert', 'equal').
        b_beg = opinfo[1]  # base begin index.
        b_end = opinfo[2]  # base end index.
        m_beg = opinfo[3]  # modi begin index.
        m_end = opinfo[4]  # modi end index.

        assert(opc in ('replace', 'delete', 'insert', 'equal'))
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
                                     modi_l[m_beg:m_end])

    if False:
        end = datetime.datetime.now()
        print("create_diff_descriptor: %s: %s" % (end - beg, base))
    return desc
