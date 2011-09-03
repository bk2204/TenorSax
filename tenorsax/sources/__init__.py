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

class FancyTextParser(xml.sax.xmlreader.XMLReader):
    NS = "http://ns.crustytoothpaste.net/text-markup"
    PREFIX = "_tmarkup"
    def __init__(self, ch=None):
        self.ch = ch
        self.dh = None
        self.enth = None
        self.eh = None
    def _start_element(self, name, attrs = {}):
        if len(attrs):
            # Each item has (ns, localname, qname, value).
            attritems = {}
            qnameitems = {}
            for ak, av in attrs.items():
                if type(ak) is list or type(ak) is tuple:
                    attritems[(ak[0], ak[1])] = av
                    qnameitems[ak[2]] = av
                else:
                    attritems[(None, ak)] = av
                    qnameitems[ak] = av
            a = xml.sax.xmlreader.AttributesNSImpl(attritems, qnameitems)
        else:
            a = xml.sax.xmlreader.AttributesNSImpl({}, {})
        self.ch.startElementNS((self.NS, name), self.PREFIX + ":" + name, a)
    def _end_element(self, name):
        self.ch.endElementNS((self.NS, name), self.PREFIX + ":" + name)
    def _process_tags(self, text):
        """Emits a tagged text to the ContentHandler."""
        reo = re.compile(r"<(/?)(\w)-([^/>]+)(/?)>")
        pos = 0
        while True:
            mo = reo.search(text, pos)
            if not mo:
                break
            is_end = mo.group(1) == "/"
            tagtype = mo.group(2)
            tagname = mo.group(3)
            is_sc = mo.group(4) == "/"
            self.ch.characters(text[pos:mo.start()])
            if tagtype == "c":
                self.ch.characters(chr(int(tagname[1:], 16)))
            elif tagtype in "i":
                if not is_sc and not is_end:
                    self._start_element("inline", {"type": tagname})
                elif not is_sc:
                    self._end_element("inline")
            pos = mo.end()
        self.ch.characters(text[pos:])
    def getContentHandler(self):
        return self.ch
    def setContentHandler(self, handler):
        self.ch = handler
    def getDTDHandler(self):
        return self.dh
    def setDTDHandler(self, handler):
        self.dh = handler
    def getEntityResolver(self):
        return self.enth
    def setEntityResolver(self, handler):
        self.enth = handler
    def getErrorHandler(self):
        return self.eh
    def setErrorHandler(self, handler):
        self.eh = handler
