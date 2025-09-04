# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
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
        options.scm = drgit.Git(options)
    else:
        drutil.fatal("Uhandled SCM instantiation.")

    drutil.mktree(options.review_dir)
    drutil.mktree(options.review_base_dir)
    drutil.mktree(options.review_modi_dir)

    return options


def report(options):
    print("\ndiff-review:  %s\n"  % (os.path.join(options.arg_review_dir,
                                                  options.arg_review_name)))

    action_width = 0;
    for f in options.scm.dossier_:
        action_width = max(action_width, len(f.action()))

    for f in options.scm.dossier_:
        print("  %*s   %s" % (action_width, f.action(), f.curr_rel_path_))
    
    print("\nTkDiff:  view-review -R %s  -r %s" % (options.arg_review_dir,
                                                   options.arg_review_name))
    print("\n")


def main():
    try:
        options = process_command_line()

        options.scm.generate(options)

        report(options)

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
