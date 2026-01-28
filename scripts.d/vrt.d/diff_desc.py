# Copyright (c) 2025, 2026  Logic Magicians Software (Taylor Hutt).
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


class Line(object):
    def __init__(self, line):
        assert(isinstance(line, str))
        self.line_           = line     # Text of source line.
        self.line_num_       = -1       # Not known on construction.
        self.runs_added_     = [ ]      # TextRunAdded
        self.runs_deleted_   = [ ]      # TextRunDeleted
        self.runs_intraline_ = [ ]      # TextRunIntraline
        self.runs_tws_       = [ ]      # TextRunTrailingWhitespace
        self.runs_tabs_      = [ ]      # TextRunTab runs.
        self.region_         = None     # Containing RegionDesc

    def dump_runs(self, hdr, runs):
        rdisp = "%s[ " % (hdr)
        for r in runs:
            rdisp += str(r)
        rdisp += " ]"
        return rdisp

    def dump(self, hdr):
        print("%5s  %s" % (hdr, self.line_))
        runs = "%s %s %s %s %s" % (self.dump_runs("A", self.runs_added_),
                                   self.dump_runs("D", self.runs_deleted_),
                                   self.dump_runs("I", self.runs_intraline_),
                                   self.dump_runs("TWS", self.runs_tws_),
                                   self.dump_runs("T", self.runs_tabs_))

        print(runs)

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

    def modi_line_count(self):
        length = 0
        # The number of lines in the file is computed using the last region.
        for rgn in self.modi_.regions_:
            length = rgn.beg_ + rgn.len_
        return length

    def add_line_count(self):
        tot = 0
        for rgn in self.modi_.regions_:
            if rgn.kind_ == RegionDesc.ADD:
                tot += rgn.len_
        return tot

    def del_line_count(self):
        tot = 0
        for rgn in self.base_.regions_:
            if rgn.kind_ == RegionDesc.DELETE:
                tot += rgn.len_
        return tot

    def chg_line_count(self):
        tot = 0
        for rgn in self.modi_.regions_:
            if rgn.kind_ == RegionDesc.CHANGE:
                tot += rgn.len_
        return tot


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


def find_tab_runs(line, r_beg, r_len):
    assert(isinstance(line, Line))
    tab_runs = [ ]
    l_start  = r_beg  # Original r_beg to create TextRunTab.
    line     = line.line_[r_beg:r_beg + r_len]
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

            t_run = TextRunTab(l_start + r_beg, r_end - r_beg)
            tab_runs.append(t_run)

    return tab_runs


def find_trailing_whitespace(line):
    assert(isinstance(line, Line))

    idx = len(line.line_)
    beg = idx
    while idx > 0 and line.line_[idx - 1] in (' ', '\t'):
        beg = idx - 1
        idx -= 1

    if beg < len(line.line_):
        return [ TextRunTrailingWhitespace(beg, len(line.line_) - beg) ]
    else:
        return [ ]
