# Copyright (c) 2025  Logic Magicians Software (Taylor Hutt).
# All Rights Reserved.
# Licensed under Gnu GPL V3.
#
"""
Utility functions for diff_review

This module contains helper functions used across the diff viewer application.
"""
import sys
from PyQt6.QtCore import QtMsgType, qInstallMessageHandler


def fatal(msg):
    print("fatal: %s" % (msg))
    sys.exit(1)


def qt_message_handler(mode, context, message):
    """
    Custom Qt message handler to suppress XKB warnings and handle other Qt messages.
    
    Args:
        mode: QtMsgType indicating the severity of the message
        context: QMessageLogContext providing context information
        message: The actual message string
    """
    # Suppress XKB compose warnings
    if 'xkb' in message.lower() or 'compose' in message.lower():
        return
    
    # For other messages, print to stderr as normal
    if mode == QtMsgType.QtDebugMsg:
        print(f"Qt Debug: {message}", file=sys.stderr)
    elif mode == QtMsgType.QtWarningMsg:
        print(f"Qt Warning: {message}", file=sys.stderr)
    elif mode == QtMsgType.QtCriticalMsg:
        print(f"Qt Critical: {message}", file=sys.stderr)
    elif mode == QtMsgType.QtFatalMsg:
        print(f"Qt Fatal: {message}", file=sys.stderr)


def install_message_handler():
    """Install the custom Qt message handler."""
    qInstallMessageHandler(qt_message_handler)


def extract_display_path(filepath):
    """
    Extract the display path starting after base.d/ or modi.d/
    
    Args:
        filepath: The full file path
        
    Returns:
        The extracted display path, or the original path if no markers found
    """
    if 'base.d/' in filepath:
        idx = filepath.find('base.d/')
        return filepath[idx + len('base.d/'):]
    elif 'modi.d/' in filepath:
        idx = filepath.find('modi.d/')
        return filepath[idx + len('modi.d/'):]
    elif 'base.d' in filepath:
        idx = filepath.find('base.d')
        remaining = filepath[idx + len('base.d'):]
        return remaining.lstrip('/')
    elif 'modi.d' in filepath:
        idx = filepath.find('modi.d')
        remaining = filepath[idx + len('modi.d'):]
        return remaining.lstrip('/')
    else:
        return filepath
