# Copyright (c) 2025  Logic MAGICIANS Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import difflib

class TextRun(object):
    def __init__(self, start, n_chars, changed):
        self.start_   = start
        self.len_     = n_chars
        self.changed_ = changed # Text is altered, or not altered in this run.

    def dump(self):
        print("%d:%d" % (self.start_, self.len_))

    def color(self):
        raise NotImplementedError("color is not defined.")


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


class Line(object):
    def __init__(self, line):
        assert(isinstance(line, str))
        self.line_      = line     # Text of source line.
        self.line_num_  = -1       # Not known on construction.
        self.runs_      = [ ]      # TextRun instances

    def dump(self, hdr):
        print("%5s  %s" % (hdr, self.line_[:-1]))
        for r in self.runs_:
            r.dump()
        print(self.runs_)

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
                run = TextRunAdded(idx, jdx - idx, False)
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
        if False and self.verbose_:
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


def read_file(path):
    with open(path, "r") as fp:
        result = fp.readlines()
    return result


def create_difflib(base, modi):
    base_l = read_file(base)
    modi_l = read_file(modi)
    d = difflib.Differ()
    return d.compare(base_l, modi_l)


def line_fields(line):
    return (line[0:2], line[2:])


def create_diff_descriptor(verbose, base, modi):
    desc  = DiffDesc(verbose)
    NPA   = NotPresentAdd()        # Only one instance needed.
    NPD   = NotPresentDelete()     # Only one instance needed.
    marks = ""

    # Turn diffs create_difflib() generator into useful structure.
    diffs = list(create_difflib(base, modi))
    idx   = 0

    if False and verbose:
        print("Info:\n"
              "  Base: %s\n"
              "  Modi: %s\n"
              "  Regions: %d\n"
              "\n" % (base, modi, len(diffs)))

    # The lines of the two files are processed from line 1 to the end
    # of the file.  Either file can appear in the output first
    # (consider adding a new line to the top of modi).

    while idx < len(diffs):
        intraline = False
        # Each line begins with a 2 character command:
        #
        #  '- '  : Only in base.
        #
        #  '+ '  : Only in modi.
        #
        #  '  '  : Present in base.
        #          Present in modi.
        #
        #  '? '  : difflib change info for altered lines.
        #          { '-', '^', '+' } marks previous line.
        #          The lines ONLY follow a base- or modi-only line.
        #          Not present in base.
        #          Not present in modi.
        #
        (cmd, l) = line_fields(diffs[idx])
        base_file_op = cmd == "- " # Only in base file.
        modi_file_op = cmd == "+ " # Only in modi file.
        both_file_op = cmd == "  " # Present in both files.
        meta_file_op = cmd == "? " # Not in files.  difflib info.

        if False and verbose:
            print("cmd: '%2s'  '%s'" % (cmd, l[:-1]))

        if (base_file_op or modi_file_op):
            line = Line(l)

            # Check if next line is a command to show
            # intraline differences.
            if idx + 1 < len(diffs):
                (nxt_cmd, marks) = line_fields(diffs[idx + 1])
                if False and verbose:
                    print("nxt: '%2s'  '%s'" % (nxt_cmd, marks[:-1]))

                if nxt_cmd == "? ":
                    # This line describes the different runs of text
                    # its previous line..  It is is filled with characters from:
                    #
                    #    { ' ', '-', '+', '^' }
                    #
                    #  ' ': unchanged.
                    #  '-': deleted.
                    #  '+': added.
                    #  '^': changed.
                    #
                    line.add_runs(marks)
                    intraline = True
                    idx       = idx + 2 # Consume source line & meta-info line.

                    if base_file_op:
                        if desc.cl_.base_ is not None:
                            # Several base-only lines in a row.
                            # This is a deleted block.
                            assert(desc.cl_.modi_ is None)
                            desc.cache_modi(NPD)
                            desc.flush(idx, intraline, marks)

                        desc.cache_base(line)
                    else:
                        assert(modi_file_op)
                        assert(desc.cl_.modi_ is None)
                        desc.cache_modi(line)
                else:
                    # This 'line' is not followed by a '? ', and
                    # therefore only exists in 'base' or 'modi'.
                    idx = idx + 1
                    if base_file_op:
                        # This line only exists in 'base', and there
                        # is no intraline change information.
                        #
                        # 'line' must have been deleted from 'modi'.
                        #
                        if desc.cl_.base_ is not None:
                            assert(desc.cl_.modi_ is None)
                            desc.cache_modi(NPD)
                            desc.flush(idx, intraline, marks)

                        line.add_run_deleted_line()
                        desc.cache_base(line)
                    else:
                        # This line only exists in 'modi'.  It might
                        # have been added, but it could also be a
                        # modified version of a line from 'base'.
                        #
                        # A line truly added to 'modi' will have no
                        # corresponding 'base', while a modified
                        # source line will.
                        #
                        assert(modi_file_op)
                        line.add_run_added_line()
                        desc.cache_modi(line)

                        if desc.cl_.base_ is None:
                            # Truly added line.
                            desc.cache_base(NPA)
            else:
                # No more lines present in 'diffs'.
                # There isn't enough data to have a '? ' command.
                # There is no additional information about 'line'.
                #
                idx = idx + 1
                if base_file_op:
                    # A line that occurs only in 'base' was deleted in
                    # 'modi'.
                    line.add_run_deleted_line()
                    desc.cache_base(line)
                else:
                    # A line that occurs only in 'modi' was added in
                    # 'modi'.
                    assert(modi_file_op)
                    line.add_run_added_line()
                    desc.cache_modi(line)

        elif both_file_op:
            idx = idx + 1

            # Previous line was base-only.
            # This affects both lines.
            # The previous line must have been deleted from modi.
            if desc.cl_.base_ is not None:
                desc.cache_modi(NPD)
                desc.flush(idx, intraline, marks)

            # The same line is present in both files.
            # It must be unmodified.
            b = Line(l)
            b.add_run_unchanged()
            desc.cache_base(b)

            m = Line(l)
            m.add_run_unchanged()
            desc.cache_modi(m)
        else:
            assert(meta_file_op) # In neither file.
            raise NotImplementedError("Internal error: stray '? ' "
                                      "command encountered.")

        if (desc.cl_.base_ is not None and
            desc.cl_.modi_ is not None):
            desc.flush(idx, intraline, marks)

    return desc
