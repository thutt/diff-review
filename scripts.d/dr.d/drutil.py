# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import inspect
import os
import subprocess

class FatalError(Exception):
    def __init__(self, msg):
        self.msg = msg

def fatal(msg):
    raise FatalError(msg)


def warning(msg):
    print("warning: %s" % (msg))


def TODO(msg):
    print("TODO: %s" % (msg))


def mktree(p):
    if not os.path.exists(p):
        os.makedirs(p)


def execute(verbose, cmd):
    assert(isinstance(cmd, list))
    assert(os.path.exists(cmd[0]))

    if verbose:
        print("EXEC: '%s'" % (' '.join(cmd)))

    p = subprocess.Popen(cmd,
                         shell    = False,
                         errors   = "replace",
                         stdin    = subprocess.PIPE,
                         stdout   = subprocess.PIPE,
                         stderr   = subprocess.PIPE)
    (stdout, stderr) = p.communicate(None)

    # None is returned when no pipe is attached to stdout/stderr.
    if stdout is None:
        stdout = ''
    if stderr is None:
        stderr = ''
    rc = p.returncode

    if len(stdout) > 0:
        stdout = stdout[:-1].replace("\r", "").split("\n")
    else:
        stdout = [ ]
    if len(stderr) > 0:
        stderr = stderr[:-1].replace("\r", "").split("\n"),
    else:
        stderr = [ ]


    # stdout block becomes a list of lines.  For Windows, delete
    # carriage-return so that regexes will match '$' correctly.
    #
    return (stdout, stderr, rc)


def qualid_():
    stack = inspect.stack()
    caller = stack[1]
    function = caller.function
    module   = os.path.basename(caller.filename).split('.')[0]
    return "%s.%s" % (module, function)

