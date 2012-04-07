#!/usr/bin/python3

import os
import sys

# The request in question is not defined.
TRACE_UNDEF = 1

def log(*args):
    if "TENORSAX_DEBUG" in os.environ:
        print(*args, file=sys.stderr)

def trace(state, bit, *args):
    """Print a message to standard error if bit is set in state.trace."""
    if state.trace & bit:
        print(*args, file=sys.stderr)

def chomp(line):
    if line[-1] == "\n":
        return line[:-1]
    return line
