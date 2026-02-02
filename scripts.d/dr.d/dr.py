# Copyright (c) 2025, 2026  Logic Magicians Software (Taylor Hutt).
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


def report(options, changed_info, elapsed_time):
    if options.scm.dossier_ is not None:
        print("\ndiff-review:  %s\n"  % (os.path.join(options.arg_review_dir,
                                                      options.arg_review_name)))

        action_width = 0;
        for f in options.scm.dossier_:
            action_width = max(action_width, len(f.action()))

        for f in options.scm.dossier_:
            action       = f.action()
            display_path = f.modi_file_info_.display_path()
            if action == "delete":
                # Modified file info references the 'empty_file', and
                # that's not the right name to display.
                #
                display_path = f.base_file_info_.display_path()

            print("  %*s   %s" % (action_width, action, display_path))

        dossier = options.scm.get_dossier_pathname()
        dossier_dir = os.path.dirname(dossier)
        if options.arg_url_review_directory is not None:
            url_dossier_dir = os.path.join(options.arg_url_review_directory,
                                           options.arg_review_name)
        else:
            url_dossier_dir = os.path.dirname(dossier)

        if not url_dossier_dir.startswith('/'):
            # Add separator after url-port, only if not already
            # present.
            url_dossier_dir = "/" + url_dossier_dir

        if options.arg_url_https:
            protocol = "https"
        else:
            protocol = "http"

        print("\n"
              "Changes:  %s" % (changed_info))
        print("Viewer :  vrt --diff-dir '%s'" % (dossier_dir))
        print("Viewer :  vrt --diff-url %s://%s:%s%s" %
              (protocol, options.arg_url_server,
               options.arg_url_port, url_dossier_dir))
        print("Elapsed:  %s" % (elapsed_time))
    else:
        if dropts.uncommitted_review(options):
            print("No uncommitted changes in client to review.")
        else:
            print("No files found in provided change ID.")
    print("\n")


def append_changes_to_dossier(options):
    scm     = options.scm
    dossier = scm.get_dossier_pathname()

    for chg_id in options.arg_change_append_id:
        beg = datetime.datetime.now()
        scm.generate(options, chg_id)
        scm.write_dossier(chg_id)
        end          = datetime.datetime.now()
        changed_info = scm.get_changed_info(chg_id)
        elapsed      = end - beg
        report(options, changed_info, elapsed)


def main():
    try:
        options = dropts.process_command_line()
        scm     = options.scm

        if dropts.uncommitted_review(options):
            beg = datetime.datetime.now()
            scm.generate(options, None)
            if scm.dossier_ is not None:
                scm.write_dossier(None)
            end          = datetime.datetime.now()
            changed_info = scm.get_changed_info(None)
            elapsed      = end - beg
            report(options, changed_info, elapsed)
        else:
            if options.arg_change_id is not None:
                beg = datetime.datetime.now()
                scm.generate(options, options.arg_change_id)
                scm.write_dossier(options.arg_change_id)
                end          = datetime.datetime.now()
                changed_info = scm.get_changed_info(options.arg_change_id)
                elapsed      = end - beg
                report(options, changed_info, elapsed)
            else:
                append_changes_to_dossier(options)

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
