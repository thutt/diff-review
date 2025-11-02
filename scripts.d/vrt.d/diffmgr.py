# Copyright (c) 2025  Logic MAGICIANS Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import difflib
import diff_desc

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
    desc  = diff_desc.DiffDesc(verbose)
    NPA   = diff_desc.NotPresentAdd()        # Only one instance needed.
    NPD   = diff_desc.NotPresentDelete()     # Only one instance needed.
    marks = ""

    # Turn diffs create_difflib() generator into useful structure.
    diffs = list(create_difflib(base, modi))
    idx   = 0

    if verbose:
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

        if verbose:
            print("cmd: '%2s'  '%s'" % (cmd, l[:-1]))

        if (base_file_op or modi_file_op):
            line = diff_desc.Line(l)

            # Check if next line is a command to show
            # intraline differences.
            if idx + 1 < len(diffs):
                (nxt_cmd, marks) = line_fields(diffs[idx + 1])
                if verbose:
                    print("nxt: '%2s'  '%s'" % (nxt_cmd, marks[:-1]))

                if nxt_cmd == "? ":
                    # This line describes the different runs of text
                    # from the previous line.  It is is filled with
                    # characters from:
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
            b = diff_desc.Line(l)
            b.add_run_unchanged()
            desc.cache_base(b)

            m = diff_desc.Line(l)
            m.add_run_unchanged()
            desc.cache_modi(m)
        else:
            assert(meta_file_op) # In neither file.
            raise NotImplementedError("Internal error: stray '? ' "
                                      "command encountered.")

        if (desc.cl_.base_ is not None and
            desc.cl_.modi_ is not None):
            desc.flush(idx, intraline, marks)

    # If last line has a base or modi, fill the other one out and flush.
    if desc.cl_.base_ is not None or desc.cl_.modi_ is not None:
        if desc.cl_.base_ is None:
            desc.cache_base(NPA)

        if desc.cl_.modi_ is None:
            desc.cache_modi(NPD)
        desc.flush(idx, intraline, marks)

    return desc
