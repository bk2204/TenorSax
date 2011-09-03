#-
# Copyright © 2011 brian m. carlson
# Copyright © 2002-2010 Stuart Rackham
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License, dated June 1991.
# 
# this program is distributed in the hope that it will be useful,
# but without any warranty; without even the implied warranty of
# merchantability or fitness for a particular purpose.  see the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

#-
# Part of the parser in this file has been taken from AsciiDoc 8.6.5.

import re
import xml.sax.xmlreader

from tenorsax.util import *

class Quote:
    """Specifies information about a set of quotation marks."""
    def __init__(self, lq, rq, tag, unconstrained=False):
        self.lq = lq
        self.rq = rq
        self.tag = tag
        self.simple = not unconstrained

class QuoteParser:
    """Transforms quotes in text into a tagged format."""
    def __init__(self, quotes):
        """Create a new quote parser.

        quotes is a sequence of Quotes to be recognized, with priority given to
        elements earlier in the list.
        """
        self._quotes = quotes

    def parse(self, text):
        """Process any quotes in this text and replace them with tags."""
        for q in self._quotes:
            lq = q.lq
            rq = q.rq
            tag = q.tag
            if not q.simple:
                # Unconstrained quotes can appear anywhere.
                reo = re.compile(r'(?msu)(^|.)(\[(?P<attrlist>[^[\]]+?)\])?' +
                        r'(?:' + re.escape(lq) + r')' +
                        r'(?P<content>.+?)(?:'+re.escape(rq)+r')')
            else:
                # The text within constrained quotes must be bounded by white
                # space.  Non-word (\W) characters are allowed at boundaries to
                # accomodate enveloping quotes and punctuation e.g. a='x',
                # ('x'), 'x', ['x'].
                reo = re.compile(r'(?msu)(^|[^\w;:}])' +
                    r'(\[(?P<attrlist>[^[\]]+?)\])?' +
                    r'(?:' + re.escape(lq) + r')' +
                    r'(?P<content>\S|\S.*?\S)(?:'+re.escape(rq)+r')(?=\W|$)')
            pos = 0
            while True:
                mo = reo.search(text, pos)
                if not mo:
                    break
                if text[mo.start()] == '\\':
                    # Delete leading backslash.
                    text = text[:mo.start()] + text[mo.start()+1:]
                    # Skip past start of match.
                    pos = mo.start() + 1
                else:
                    attrlist = {}
                    #parse_attributes(mo.group('attrlist'), attrlist)
                    stag = ''.join(["<i-", tag, ">"])
                    etag = ''.join(["</i-", tag, ">"])
                    s = mo.group(1) + stag + mo.group('content') + etag
                    text = text[:mo.start()] + s + text[mo.end():]
                    pos = mo.start() + len(s)
        return text
