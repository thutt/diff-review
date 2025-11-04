# Copyright (c) 2025  Logic MAGICIANS Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
class TextRun(object):
    def __init__(self, start, n_chars, changed):
        self.start_   = start
        self.len_     = n_chars
        self.changed_ = changed # Text is altered, or not altered in this run.

    def dump(self):
        print("%d:%d" % (self.start_, self.len_))

    def color(self):
        raise NotImplementedError("color is not defined.")

    def __str__(self):
        return "%s(%d, %d) " % (self.color(), self.start_, self.len_)


class TextRunNormal(TextRun):
    def __init__(self, start, n_chars):
        super().__init__(start, n_chars, False)

    def color(self):
        return "NORMAL"


class TextRunAdded(TextRun):
    def __init__(self, start, n_chars, changed):
        super().__init__(start, n_chars, changed)

    def color(self):
        return "ADD"


class TextRunDeleted(TextRun):
    def __init__(self, start, n_chars):
        super().__init__(start, n_chars, True)

    def color(self):
        return "DELETE"


class TextRunIntraline(TextRun):
    def __init__(self, start, n_chars):
        super().__init__(start, n_chars, True)

    def color(self):
        return "INTRALINE"


class TextRunUnknown(TextRun):
    def __init__(self, start, n_chars):
        super().__init__(start, n_chars, True)

    def color(self):
        return "UNKNOWN"        # Unknown meta marker on '? ' command.


class TextRunNotPresent(TextRun):
    def __init__(self, start, n_chars, changed):
        super().__init__(start, n_chars, changed)

    def color(self):
        return "NOTPRESENT"


class TextRunWhitespace(TextRun):
    def __init__(self, start, n_chars, changed):
        super().__init__(start, n_chars, changed)

    def color(self):
        return "WS"


class TextRunTrailingWhitespace(TextRun):
    def __init__(self, start, n_chars, changed):
        super().__init__(start, n_chars, changed)

    def color(self):
        return "TRAILINGWS"

class TextRunTab(TextRun):
    def __init__(self, start, n_chars, changed):
        super().__init__(start, n_chars, changed)

    def color(self):
        return "TAB"


class Line(object):
    def __init__(self, line):
        assert(isinstance(line, str))
        self.line_      = line     # Text of source line.
        self.line_num_  = -1       # Not known on construction.
        self.runs_      = [ ]      # TextRun instances
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

    def add_runs(self, run_info):
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
        super().__init__("\n")
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


class DiffDesc(object):
    def __init__(self, verbose):
        self.verbose_  = verbose
        self.cl_       = CurrentLine()
        self.base_     = [ ]    # Lines in base file.
        self.modi_     = [ ]    # Lines in modi file.

    def add_base_line(self, line):
        self.base_.append(line)

    def add_modi_line(self, line):
        self.modi_.append(line)

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
        assert(len(self.base_) == len(self.modi_))
        ll = len(self.base_)

        # Write basic text to known files to validate with tkdiff.
        with open("/tmp/base", "w") as fp:
            idx = 0
            while idx < len(self.base_):
                base = self.base_[idx].line_
                fp.write(base)
                idx = idx + 1

        with open("/tmp/modi", "w") as fp:
            idx = 0
            while idx < len(self.modi_):
                modi = self.modi_[idx].line_
                fp.write(modi)
                idx = idx + 1

        idx = 0
        while idx < ll:
            base_type_ = type(self.base_[idx]).__name__
            base = self.base_[idx].line_.replace('\n', '')

            modi_type_ = type(self.modi_[idx]).__name__
            modi = self.modi_[idx].line_.replace('\n', '')

            if True:
                self.base_[idx].dump("base")
                self.modi_[idx].dump("modi")
            else:
                print("(%s) %s   |   (%s) %s" % (base_type_, base,
                                                 modi_type_, modi))
            idx = idx + 1
