#!/usr/bin/python3

import os
import sys

def log(*args):
    if "TENORSAX_DEBUG" in os.environ:
        print(*args, file=sys.stderr)
