# Copyright (c) 2025  Logic Magicians Software.
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
import os
import subprocess

class FatalError(Exception):
    def __init__(self, msg):
        self.msg = msg

def fatal(msg):
    raise FatalError(msg)


def mktree(p):
    if not os.path.exists(p):
        os.makedirs(p)


def execute(cmd):
    assert(isinstance(cmd, list))
    assert(os.path.exists(cmd[0]))

    p = subprocess.Popen(cmd,
                         shell    = False,
                         encoding = "ASCII",
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

    # stdout block becomes a list of lines.  For Windows, delete
    # carriage-return so that regexes will match '$' correctly.
    #
    return (stdout.replace("\r", "").split("\n"),
            stderr.replace("\r", "").split("\n"),
            rc)
