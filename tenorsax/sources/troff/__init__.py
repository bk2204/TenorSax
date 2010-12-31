#!/usr/bin/python3

import os
import sys

def log(*args):
    if "XML2ROFF_VERBOSE" in os.environ:
        print(*args, file=sys.stderr)
