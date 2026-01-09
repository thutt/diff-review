# Copyright (c) 2025, 2026  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import argparse
import PyQt6
import sys
import traceback

import cmdlineargs
import generate_viewer


def main():
    try:
        application = PyQt6.QtWidgets.QApplication(sys.argv)
        options = cmdlineargs.process_command_line()
        return generate_viewer.generate(options, options.arg_note)

    except KeyboardInterrupt:
        return 0

    except NotImplementedError as exc:
        print("")
        print(traceback.format_exc())
        return 1;

    except Exception as e:
        print("internal error: unexpected exception\n%s" % str(e))
        print("")
        print(traceback.format_exc())

        return 1


if __name__ == "__main__":
    sys.exit(main())
