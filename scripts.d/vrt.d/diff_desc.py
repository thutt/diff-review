# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
class TextRun(object):
    def __init__(self, kind, start, n_chars, changed):
        self.start_   = start
        self.len_     = n_chars
        self.changed_ = changed # Text is altered, or not altered in this run.
        self.kind_    = kind    # Identifies the class type.

    def dump(self):
        print("%d:%d" % (self.start_, self.len_))

    def color(self):
        raise NotImplementedError("color is not defined.")

    def __str__(self):
        return "%s(%d, %d) " % (self.color(), self.start_, self.len_)


class TextRunNormal(TextRun):
    def __init__(self, start, n_chars):
        super().__init__(0, start, n_chars, False)

    def color(self):
        return "NORMAL"


class TextRunAdded(TextRun):
    def __init__(self, start, n_chars, changed):
        super().__init__(1, start, n_chars, changed)

    def color(self):
        return "ADD"


class TextRunDeleted(TextRun):
    def __init__(self, start, n_chars):
        super().__init__(2, start, n_chars, True)

    def color(self):
        return "DELETE"


class TextRunIntraline(TextRun):
    def __init__(self, start, n_chars):
        super().__init__(3, start, n_chars, True)

    def color(self):
        return "INTRALINE"


class TextRunWhitespace(TextRun):
    def __init__(self, start, n_chars, changed):
        super().__init__(4, start, n_chars, changed)

    def color(self):
        return "WS"


class TextRunTrailingWhitespace(TextRun):
    def __init__(self, start, n_chars, changed):
        super().__init__(5, start, n_chars, changed)

    def color(self):
        return "TRAILINGWS"

class TextRunTab(TextRun):
    def __init__(self, start, n_chars, changed):
        super().__init__(6, start, n_chars, changed)

    def color(self):
        return "TAB"


class TextRunNotPresent(TextRun):
    def __init__(self, start, n_chars, changed):
        super().__init__(7, start, n_chars, changed)

    def color(self):
        return "NOTPRESENT"


class TextRunUnknown(TextRun):  # XXX Remove with diffmgr.
    def __init__(self, start, n_chars):
        super().__init__(8, start, n_chars, True)

    def color(self):
        return "UNKNOWN"        # Unknown meta marker on '? ' command.


class Line(object):
    def __init__(self, line):
        assert(isinstance(line, str))
        self.line_      = line     # Text of source line.
        self.line_num_  = -1       # Not known on construction.
        self.runs_      = [ ]      # TextRun instances
        self.region_    = None     # Containing RegionDesc
        self.uncolored_ = False    # Indicates if there are colors on this line.
                                   #
                                   #   Only unmodified lines w/o
                                   #   trailing whitespace or tabs
                                   #   will have this set.  The
                                   #   'unmodified lines' are in
                                   #   'equal' line regions produced
                                   #   by difflib.SequenceMatcher().

    def dump(self, hdr):
        print("%5s  %s" % (hdr, self.line_))

        rdisp = "[ "
        for r in self.runs_:
            rdisp += str(r)
        rdisp += " ]"
        print(rdisp)

    def add_parent_region(self, region):
        self.region_ = region

    def show_line_number(self):
        return True

    def set_line_number(self, line_num):
        self.line_num_ = line_num

    def add_run_not_present_coverage(self):
        run = TextRunNotPresent(0, len(self.line_), False)
        self.runs_.append(run)

    def add_run_unchanged(self):
        run = TextRunNormal(0, len(self.line_))
        self.runs_.append(run)

    def add_run_added_line(self):
        run = TextRunAdded(0, len(self.line_), True)
        self.runs_.append(run)

    def add_run_deleted_line(self):
        run = TextRunDeleted(0, len(self.line_))
        self.runs_.append(run)

    def add_runs(self, run_info): # XXX diffmgr only
        assert(run_info is not None)
        assert(run_info[len(run_info) - 1] == '\n')

        run_info = run_info.replace('\n', '')
        assert(len(run_info) <= len(self.line_))

        # Remove line ending of 'run_info' so residual run math
        # works out below.

        idx = 0
        # This finds blocks of any consecutive character.  ' ' is
        # used to indicate no change.
        #
        # The following character set is known to be used:
        #    { '-', '^' }.
        while idx < len(run_info):
            ch   = run_info[idx]
            run_same   = ch == ' '
            run_delete = ch == '-'
            run_change = ch == '^'
            run_add    = ch == '+'
            # else, unknown character

            jdx = idx + 1
            while jdx < len(run_info) and ch == run_info[jdx]:
                jdx = jdx + 1

            if run_same:
                run = TextRunNormal(idx, jdx - idx)
            elif run_delete:
                run = TextRunDeleted(idx, jdx - idx)
                pass
            elif run_change:
                run = TextRunIntraline(idx, jdx - idx)
                pass
            elif run_add:
                run = TextRunAdded(idx, jdx - idx, True)
            else:
                run = TextRunUnknown(idx, jdx - idx)
            self.runs_.append(run)
            idx = jdx

        if len(run_info) < len(self.line_):
            # Fill out last part of line.
            ril = len(run_info)
            ll  = len(self.line_)
            run = TextRunNormal(ril, ll - ril)
            self.runs_.append(run)

    def kind(self):
        return "LINE"


class NotPresent(Line):         # Line doesn't exist in this file.
    def __init__(self):
        super().__init__("")
        self.add_run_not_present_coverage()

    def show_line_number(self):
        return False

    def kind(self):
        raise NotImplementedError("This should not be directly instantiated.")


class NotPresentAdd(NotPresent):
    def __init__(self):
        super().__init__()

    def kind(self):
        return "NotPresentAdd"


class NotPresentDelete(NotPresent):
    def __init__(self):
        super().__init__()

    def kind(self):
        return "NotPresentDelete"


class CurrentLine(object):
    def __init__(self):
        self.base_      = None
        self.base_line_ = 1     # Increment on flush.
        self.modi_      = None
        self.modi_line_ = 1     # Increment on flush.


# 
class RegionDesc(object):
    UNKNOWN = -1                # Uninitialized
    EQUAL   = 0                 # Unchanged line.
    DELETE  = 1                 # Deleted line (base file only)
    ADD     = 2                 # Added line (modi file only)
    CHANGE  = 3                 # Changed line.

    def __init__(self, kind, r_beg, r_len):
        if kind == "equal":
            kind = self.EQUAL
        elif kind == "delete":
            kind = self.DELETE
        elif kind == "insert":
            kind = self.ADD
        else:
            assert(kind == "replace")
            kind = self.CHANGE

        self.kind_ = kind
        self.beg_  = r_beg
        self.len_  = r_len

    def __str__(self):
        names = [ "eql", "del", "add", "chg" ]
        # Lines are numbered from one; make the region human readable.
        beg = self.beg_ + 1
        return "%s: [%d, %d)" % (names[self.kind_], beg, beg + self.len_)


#  Describes lines that are present in the file.
class LineInfoDesc(object):
    def __init__(self):
        self.regions_           = [ ]     # List of Region
        self.lines_             = [ ]     # List of Line
        self.n_changed_regions_ = 0       # Not EQUAL RegionDesc.

    def add_region(self, kind, r_beg, r_len):
        r = RegionDesc(kind, r_beg, r_len)
        self.regions_.append(r)
        if r.kind_ != RegionDesc.EQUAL:
            self.n_changed_regions_ += 1

    def add_line(self, line):
        self.lines_.append(line)
        idx = len(self.regions_) - 1 # Index to most recently opened region.
        line.add_parent_region(self.regions_[idx])

class DiffDesc(object):
    def __init__(self, verbose):
        self.verbose_  = verbose
        self.cl_       = CurrentLine()
        self.base_     = LineInfoDesc()    # Lines in base file.
        self.modi_     = LineInfoDesc()    # Lines in modi file.

    def add_base_region(self, kind, r_beg, r_len):
        self.base_.add_region(kind, r_beg, r_len)

    def add_modi_region(self, kind, r_beg, r_len):
        self.modi_.add_region(kind, r_beg, r_len)

    def add_base_line(self, line):
        if False:
            line.dump("base")
        self.base_.add_line(line)

    def add_modi_line(self, line):
        if False:
            line.dump("modi")
        self.modi_.add_line(line)

    def cache_modi(self, line):
        assert(isinstance(line, Line))
        self.cl_.modi_ = line
        self.cl_.modi_.set_line_number(self.cl_.modi_line_)

    def cache_base(self, line):
        assert(isinstance(line, Line))
        self.cl_.base_ = line
        self.cl_.base_.set_line_number(self.cl_.base_line_)

    # Amends a line with no more than one TRAILINGWS run, if needed.
    def amend_line_with_tws(self, line):
        l_line   = len(line.line_)
        l_rline  = len(line.line_.rstrip())

        if l_line != l_rline:

            # There is traliing whitespace.
            # The last run needs to be split, and a TRAILINGWS run added.
            last_idx = len(line.runs_) - 1 # Last run.

            assert(l_line > l_rline)
            n_spaces = l_line - l_rline
            last       = line.runs_[last_idx]
            orig_len   = last.len_
            last.len_ -= n_spaces
            tws        = TextRunTrailingWhitespace(last.start_ + last.len_,
                                                   n_spaces, True)

            assert(orig_len == last.len_ + tws.len_)
            line.runs_.append(tws)

    def flush(self, idx, intraline, marks): # Flush a line.
        if self.verbose_:
            print("FLUSH: %d:  "
                  "  intraline: %s  base: %d  modi: %d\n"
                  "  base: %s\n"
                  "  modi: %s" %
                  (idx,
                   intraline,
                   self.cl_.base_line_, self.cl_.modi_line_,
                   self.cl_.base_.line_[:-1],
                   self.cl_.modi_.line_[:-1]))
            if intraline:
                print("  mark: %s" % (marks[:-1]))
            print("")

        self.amend_line_with_tws(self.cl_.base_)
        self.amend_line_with_tws(self.cl_.modi_)

        self.add_base_line(self.cl_.base_)
        if self.cl_.base_.show_line_number():
            self.cl_.base_line_ = self.cl_.base_line_ + 1

        self.add_modi_line(self.cl_.modi_)
        if self.cl_.modi_.show_line_number():
            self.cl_.modi_line_ = self.cl_.modi_line_ + 1


        self.cl_.base_ = None
        self.cl_.modi_ = None


    def dump(self):
        assert(len(self.base_.lines_) == len(self.modi_.lines_))
        ll = len(self.base_.lines_)

        # Write basic text to known files to validate with tkdiff.
        with open("/tmp/base", "w") as fp:
            idx = 0
            while idx < len(self.base_.lines_):
                base = self.base_.lines_[idx].line_
                fp.write(base)
                idx = idx + 1

        with open("/tmp/modi", "w") as fp:
            idx = 0
            while idx < len(self.modi_.lines_):
                modi = self.modi_.lines_[idx].line_
                fp.write(modi)
                idx = idx + 1

        idx = 0
        while idx < ll:
            base_type_ = type(self.base_.lines_[idx]).__name__
            base = self.base_.lines_[idx]

            modi_type_ = type(self.modi_.lines_[idx]).__name__
            modi = self.modi_.lines_[idx]

            if True:
                self.base_.lines_[idx].dump("base")
                self.modi_.lines_[idx].dump("modi")
            else:
                print("(%s) %s   |   (%s) %s" % (base_type_, base,
                                                 modi_type_, modi))
            idx = idx + 1


def compute_tab_runs(line, m_run):
    tab_runs = [ ]
    line     = line.line_[m_run.start_:m_run.start_ + m_run.len_]
    tab_idxs = [i for i, c in enumerate(line) if c == '\t']

    # inv: tab_idxs contains all indicies in 'line' that are '\t'.
    #      It can be empty.
    t_idx = 0
    r_beg = t_idx
    r_end = 0
    if len(tab_idxs) > 0:
        while t_idx < len(tab_idxs):
            r_beg = tab_idxs[t_idx]
            r_end = r_beg + 1
            if t_idx + 1 < len(tab_idxs):
                if tab_idxs[t_idx + 1] == r_end:
                    # Multiple tabs.  Accumulate them.
                    t_idx += 1
                    while (t_idx < len(tab_idxs) and
                           tab_idxs[t_idx] == r_end):
                        r_end += 1
                        t_idx += 1
                else:
                    # Single tab.
                    t_idx += 1
            else:
                # End of line, or single tab.
                t_idx += 1

            t_run = TextRunTab(r_beg, r_end - r_beg, True)
            tab_runs.append(t_run)

    return tab_runs


def make_text_run(kind, r_beg, r_len):
    if kind == 0:               # TextRunNormal
        run = TextRunNormal(r_beg, r_len)
    elif kind == 1:             # TextRunAdded
        run = TextRunAdded(r_beg, r_len, True)
    elif kind == 2:             # TextRunDeleted
        run = TextRunDeleted(r_beg, r_len)
    elif kind == 3:             # TextRunIntraline
        run = TextRunIntraline(r_beg, r_len)
    elif kind == 4:             # TextRunWhitespace
        run = TextRunWhitespace(r_beg, r_len)
    elif kind == 5:             # TextRunTrailingWhitespace
        run = TextRunTrailingWhitespace(r_beg, r_len)
    elif kind == 6:             # TextRunTab
        run = TextRunTab(r_beg, r_len)
    elif kind == 7:             # TextRunNotPresentx
        run = TextRunNotPresentx(r_beg, r_len)
    else:                       # TextRunUnknown
        assert(kind == 8)
        run = diff_desc.TextRunUnknown(r_beg, r_len)

    return run


# Amends a single run by adding in TAB runs where needed.
# The result will be a list of runs.
#
def amend_run_with_tab(line, m_run):
    result = [ ]
    assert(isinstance(line, Line))
    t_runs = compute_tab_runs(line, m_run)

    orig_length = m_run.len_
    if len(t_runs) > 0:
        residual = True
        # Tab runs will be 0-based, but they are actually relative to m_run.
        for t in t_runs:
            if t.start_ + t.len_ == m_run.len_:
                # Split at the end.
                m_run.len_ -= t.len_
                t.start_ += m_run.start_
                if m_run.len_ > 0:
                    result.append(m_run)
                result.append(t)
                residual = False
                continue        # inv: end of elements in t_runs.

            if t.start_ > 0:    # Split in the middle of run?
                # m_run.start_ does not change.
                # The length shrinks.
                m_run_delta = t.start_ - m_run.start_
                n_len       = m_run.len_ - m_run_delta - t.len_
                m_run.len_  = m_run_delta
                assert(m_run.len_ > 0)

                n_run = make_text_run(m_run.kind_, t.start_ + t.len_,
                                      n_len)
                if m_run.len_ > 0:
                    result.append(m_run)
                result.append(t)
                # Length of 't' has not changed.

                m_run = n_run

                # Fall through to split at beginning of run to handle
                # 't' against new 'm_run'.

            if t.start_ + m_run.start_ == m_run.start_:
                # Split at the beginning.
                assert(m_run.len_ >= t.len_)
                t.start_     += m_run.start_
                m_run.start_ += t.len_
                m_run.len_   = m_run.len_ - t.len_
                result.append(t)

        if residual and m_run.len_ > 0:
            result.append(m_run)
    else:
        result = [ m_run ]

    final_length = 0
    for r in result:
        final_length += r.len_
    assert(final_length == orig_length)

    return result
