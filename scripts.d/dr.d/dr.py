# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import datetime
import os
import sys
import traceback

import drgit
import dropts
import drutil

def process_command_line():
    parser  = dropts.configure_parser()
    options = parser.parse_args()

    options.review_dir = os.path.join(options.arg_review_dir,
                                      options.arg_review_name)
    options.review_base_dir = os.path.join(options.review_dir, "base.d")
    options.review_modi_dir = os.path.join(options.review_dir, "modi.d")

    if options.arg_scm == "git":
        if options.arg_change_id is None:
            options.scm = drgit.GitStaged(options)
        else:
            options.scm = drgit.GitCommitted(options)
    else:
        drutil.fatal("Uhandled SCM instantiation.")

    drutil.mktree(options.review_dir)
    drutil.mktree(options.review_base_dir)
    drutil.mktree(options.review_modi_dir)

    return options


def report(options, changed_info, elapsed_time):
    if options.scm.dossier_ is not None:
        print("\ndiff-review:  %s\n"  % (os.path.join(options.arg_review_dir,
                                                      options.arg_review_name)))

        action_width = 0;
        for f in options.scm.dossier_:
            action_width = max(action_width, len(f.action()))

        for f in options.scm.dossier_:
            print("  %*s   %s" % (action_width, f.action(),
                                  f.modi_file_info_.rel_path_))

        print("\n"
              "Changes:  %s" % (changed_info))
        print("Viewer :  vrt -R %s -r %s" %
              (options.arg_review_dir, options.arg_review_name))
        print("Viewer :  vr -R %s -r %s" %
              (options.arg_review_dir, options.arg_review_name))
        print("Elapsed:  %s" % (elapsed_time))
    else:
        if options.arg_change_id is None:
            print("No uncommitted changes in client to review.")
        else:
            print("No files found in provided change ID.")
    print("\n")


def main():
    try:
        beg     = datetime.datetime.now()
        options = process_command_line()
        options.scm.generate(options)
        changed_info = options.scm.get_changed_info()
        end     = datetime.datetime.now()
        elapsed = end - beg

        report(options, changed_info, elapsed)

    except KeyboardInterrupt:
        return 0

    except NotImplementedError as exc:
        print("")
        print(traceback.format_exc())
        return 1;

    except drutil.FatalError as exc:
        print("fatal: %s" % (exc))
        return 1

    except Exception as e:
        print("internal error: unexpected exception\n%s" % str(e))
        print("")
        print(traceback.format_exc())

        return 1


if __name__ == "__main__":
    sys.exit(main())
