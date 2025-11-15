# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
class TextRun(object):
    def __init__(self, kind, start, n_chars):
        self.start_   = start
        self.len_     = n_chars
        self.kind_    = kind    # Identifies the class type.

    def dump(self):
        print("%d:%d" % (self.start_, self.len_))

    def color(self):
        raise NotImplementedError("color is not defined.")

    def __str__(self):
        return "%s(%d, %d) " % (self.color(), self.start_, self.len_)


class TextRunNormal(TextRun):
    def __init__(self, start, n_chars):
        super().__init__(0, start, n_chars)

    def color(self):
        return "NORMAL"


class TextRunAdded(TextRun):
    def __init__(self, start, n_chars):
        super().__init__(1, start, n_chars)

    def color(self):
        return "ADD"


class TextRunDeleted(TextRun):
    def __init__(self, start, n_chars):
        super().__init__(2, start, n_chars)

    def color(self):
        return "DELETE"


class TextRunIntraline(TextRun):
    def __init__(self, start, n_chars):
        super().__init__(3, start, n_chars)

    def color(self):
        return "INTRALINE"


class TextRunTrailingWhitespace(TextRun):
    def __init__(self, start, n_chars):
        super().__init__(4, start, n_chars)

    def color(self):
        return "TRAILINGWS"

class TextRunTab(TextRun):
    def __init__(self, start, n_chars):
        super().__init__(5, start, n_chars)

    def color(self):
        return "TAB"


class TextRunNotPresent(TextRun):
    def __init__(self, start, n_chars):
        super().__init__(6, start, n_chars)

    def color(self):
        return "NOTPRESENT"


class TextRunUnknown(TextRun):  # XXX Remove with diffmgr.
    def __init__(self, start, n_chars):
        super().__init__(7, start, n_chars)

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

    def kind(self):
        return "LINE"


class NotPresent(Line):         # Line doesn't exist in this file.
    def __init__(self):
        super().__init__("")
        run = TextRunNotPresent(0, len(self.line_))
        self.runs_.append(run)

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

# RegionDesc describes a region of lines.  They region can be 'equal',
# 'delete', 'add', or 'change'.  This is used to provide background
# color for blocks of lines.
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
        self.regions_           = [ ]     # List of RegionDesc
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
    def __init__(self, verbose, intraline_percent):
        self.verbose_           = verbose
        self.intraline_percent_ = intraline_percent
        self.cl_                = CurrentLine()
        self.base_              = LineInfoDesc()    # Lines in base file.
        self.modi_              = LineInfoDesc()    # Lines in modi file.

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
            n_spaces   = l_line - l_rline
            last       = line.runs_[last_idx]
            orig_len   = last.len_
            last.len_ -= n_spaces
            tws        = TextRunTrailingWhitespace(last.start_ + last.len_,
                                                   n_spaces)

            assert(orig_len == last.len_ + tws.len_)
            if last.len_ == 0:
                # The last run is completely replaced with TWS.
                line.runs_[last_idx] = tws
            else:
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

            t_run = TextRunTab(r_beg, r_end - r_beg)
            tab_runs.append(t_run)

    return tab_runs


def make_text_run(kind, r_beg, r_len):
    if kind == 0:               # TextRunNormal
        run = TextRunNormal(r_beg, r_len)
    elif kind == 1:             # TextRunAdded
        run = TextRunAdded(r_beg, r_len)
    elif kind == 2:             # TextRunDeleted
        run = TextRunDeleted(r_beg, r_len)
    elif kind == 3:             # TextRunIntraline
        run = TextRunIntraline(r_beg, r_len)
    elif kind == 4:             # TextRunTrailingWhitespace
        run = TextRunTrailingWhitespace(r_beg, r_len)
    elif kind == 5:             # TextRunTab
        run = TextRunTab(r_beg, r_len)
    elif kind == 6:             # TextRunNotPresent
        run = TextRunNotPresentx(r_beg, r_len)
    else:                       # TextRunUnknown
        assert(kind == 7)
        run = diff_desc.TextRunUnknown(r_beg, r_len)

    return run


# split_run: Splits 'run' at 'split_idx'
#
#  split_idx is 0-based and relative to 'run'.
#
# Returns split original run and new run
#
def split_run(run, split_idx):
    assert(run.start_ + run.len_  >= split_idx) # Big enough to split?
    assert(0         <= split_idx and
           split_idx <  run.start_ + run.len_) # 'split_idx' in bounds?

    if split_idx == run.start_:
        # Split at beginning.
        # No split, just return (None, run).
        #
        n_run = run
        run   = None
    elif split_idx == run.start_ + run.len_:
        # Split at end.
        # No split, just return (run, None).
        #
        n_run = None
    else:
        orig_len = run.len_
        n_beg    = split_idx
        run.len_ = n_beg - run.start_
        n_len    = orig_len - run.len_
        n_run    = make_text_run(run.kind_, n_beg, n_len)

        # NOTE: It is possible to split at index 0.
        #       Leaving 'run' with size 0.
        assert(run.len_ + n_run.len_ == orig_len)
    return (run, n_run)


# Amends a single run by adding in TAB runs where needed.
# The result will be a list of runs.
#
def amend_run_with_tab(line, m_run):
    DEBUG = False

    assert(isinstance(line, Line))
    result = [ ]
    t_runs = compute_tab_runs(line, m_run)

    if DEBUG and len(t_runs) > 0:
        print("LINE: %s" % (line.line_))
        print("RUN : %s" % (m_run))
        for t in t_runs:
            print("TABS: %s" % (t))

    orig_start  = m_run.start_
    orig_length = m_run.len_
    if len(t_runs) > 0:
        # Tab runs are 0-based, but they are actually relative to
        # 'm_run'.  The start of 'm_run' must be added to the start of
        # 't' to get proper offsets.
        for t in t_runs:
            assert(m_run is not None)
            (m_run, n_run) = split_run(m_run, orig_start + t.start_)

            if m_run is None:
                # Split at beginning.
                assert(n_run is not None)

                n_run.len_   = n_run.len_ - t.len_
                n_run.start_ = n_run.start_ + t.len_
                result       = result + [ t ]
                m_run        = n_run
                if m_run.len_ == 0: # Entire run has been replaced.
                    m_run = None
            elif n_run is None:
                # Split at end.
                # Processing a single run, so this will be then end of the tabs.
                #
                assert(m_run is not None)
                m_run.len_ = m_run.len_ - t.len_
                m_run      = None    # Sentinel end.
            else:
                # Split in middle.
                assert(m_run.len_ > 0 and n_run.len_ > 0)
                n_run.len_     = n_run.len_ - t.len_
                n_run.start_   = n_run.start_ + t.len_
                result         = result + [ m_run, t ]
                m_run          = n_run

        if m_run is not None:
            result.append(m_run)
    else:
        result = [ m_run ]

    final_length = 0
    for r in result:
        final_length += r.len_

    assert(final_length == orig_length)

    if DEBUG and len(t_runs) > 0:
        for r in result:
            print("RES: %s" % (r))

    return result
