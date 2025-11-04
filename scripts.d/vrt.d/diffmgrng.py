# Copyright (c) 2025  Logic MAGICIANS Software (Taylor Hutt).
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
        result = fp.read().replace("\r\n", "\n").replace("\r", "\n")

    # The returned list strings will NOT have '\n' at the end.
    return result.splitlines()


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


def make_run(opc, r_beg, r_len):
    if opc == 0:                # TextRunNormal
        return diff_desc.TextRunNormal(r_beg, r_len)
    elif opc == 1:              # TextRunAdded
        return diff_desc.TextRunAdded(r_beg, r_len, True)
    else:                       # TextRunDeleted
        assert(opc == 2)
        return diff_desc.TextRunDeleted(r_beg, r_len)


def create_line_desc(opc, line):
    assert(isinstance(line, str))

    l_desc   = diff_desc.Line(line)
    l_rstrip = line.rstrip()             # To avoid trailing tabs.
    n_spaces = len(line) - len(l_rstrip) # Count trailing (' ', '\t').

    r_idx = 0
    r_beg = r_idx
    r_end = r_idx
    while r_idx < len(l_rstrip):
        ch = l_rstrip[r_idx]
        if ch != '\t':
            r_end = r_idx
            r_idx = r_idx + 1
        else:
            # End current run, if one exists, and start a tab run.
            r_len = r_end - r_beg
            if r_len > 0:
                run = make_run(opc, r_beg, r_len)
                l_desc.runs_.append(run)

            tab_beg  = r_idx
            tab_end  = r_idx
            assert(l_rstrip[r_idx] == '\t')
            while (l_rstrip[tab_end] == '\t' and r_end < len(l_rstrip)):
                tab_end = tab_end + 1

            run = diff_desc.TextRunTab(tab_beg, tab_end - tab_beg, True)
            l_desc.runs_.append(run)
            r_beg = tab_end
            r_end = tab_end

            assert(r_beg > r_idx)
            r_idx = r_beg

    if r_beg != r_end:      # Residual run.
        r_len = r_end - r_beg
        run = make_run(opc, r_beg, r_len)
        l_desc.runs_.append(run)

    if n_spaces > 0:        # Add trailing space annotation.
        run = diff_desc.TextRunTrailingWhitespace(len(line) - n_spaces,
                                                  n_spaces, False)
        l_desc.runs_.append(run)

    l_desc.dump("create_line_desc")

    return l_desc


def add_equal_line_region(desc, base_l, modi_l):
    assert(len(base_l) == len(modi_l))

    for l_idx in range(0, len(base_l)):
        l_desc = create_line_desc(0, base_l[l_idx])
        l_desc.uncolored_ = len(l_desc.runs_) == 1
        desc.cache_base(l_desc)
        desc.cache_modi(l_desc)
        desc.flush(0, False, None)

def add_deleted_line_region(desc, base_l):
    for l_idx in range(0, len(base_l)):
        l_desc = create_line_desc(2, base_l[l_idx])
        desc.cache_base(l_desc)
        desc.cache_modi(NPD)
        desc.flush(0, False, None)


def add_inserted_line_region(desc, modi_l):
    for l_idx in range(0, len(modi_l)):
        l_desc = create_line_desc(1, modi_l[l_idx])
        l_desc.add_run_added_line()
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
        desc.cache_base(l_base)
        desc.cache_modi(l_modi)

        matcher = difflib.SequenceMatcher(None, base_l[k], modi_l[k])
        for opinfo in matcher.get_opcodes():
            opc   = opinfo[0]  # inv: ('replace', 'delete', 'insert', 'equal').
            b_beg = opinfo[1]  # base begin index.
            b_end = opinfo[2]  # base end index.
            m_beg = opinfo[3]  # modi begin index.
            m_end = opinfo[4]  # modi end index.

            if opc == "replace":
                # Intraline change.
                b_run = diff_desc.TextRunIntraline(b_beg, b_end - b_beg)
                m_run = diff_desc.TextRunIntraline(m_beg, m_end - m_beg)
                l_base.runs_.append(b_run)
                l_modi.runs_.append(m_run)

            elif opc == "delete":
                assert((m_end - m_beg) == 0) # Characters deleted.
                b_run = diff_desc.TextRunDeleted(b_beg, b_end - b_beg)
                l_base.runs_.append(b_run)
            elif opc == "insert":
                assert((b_end - b_beg) == 0) # Characters added.
                m_run = diff_desc.TextRunAdded(m_beg, m_end - m_beg, True)
                l_modi.runs_.append(m_run)
            elif opc == "equal":
                assert((b_end - b_beg) == (m_end - m_beg)) # Equal run
                b_run = diff_desc.TextRunNormal(b_beg, b_end - b_beg)
                m_run = diff_desc.TextRunNormal(m_beg, m_end - m_beg)
                l_base.runs_.append(b_run)
                l_modi.runs_.append(m_run)

        desc.flush(0, False, None)

    if len_base < len_modi:
        # These are all line insertions in the modified file.
        assert(l_changed <= len_modi)
        for k in range(l_changed, len_modi):
            l_modi = diff_desc.Line(modi_l[k])
            m_run  = diff_desc.TextRunAdded(0, len(modi_l[k]), True)
            l_modi.runs_.append(m_run)
            desc.cache_base(NPA)
            desc.cache_modi(l_modi)
            desc.flush(0, False, None)

    elif len_base > len_modi:
        # These are all line deletions from the modified file.
        assert(l_changed <= len_base)
        for k in range(l_changed, len_base):
            l_base = diff_desc.Line(base_l[k])
            b_run  = diff_desc.TextRunDeleted(0, len(base_l[k]))
            l_base.runs_.append(b_run)
            desc.cache_modi(NPD)
            desc.cache_base(l_base)
            desc.flush(0, False, None)
    else:
        pass                    # NOP; no residual lines.



def create_diff_descriptor(verbose, base, modi):
    beg   = datetime.datetime.now()
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

    end   = datetime.datetime.now()
    print("create_diff_descriptor: %s: %s" % (end - beg, base))
    return desc
