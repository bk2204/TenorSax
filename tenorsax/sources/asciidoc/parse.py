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

def chomp(line):
    if line[-1] == "\n":
        return line[:-1]
    return line

class AsciiDocStateError(Exception):
    pass

class AsciiDocStateConstants:
    START = 0
    TEXT_LINE = 1
    PARA_START = 2
    IN_PARA = 3

class Quote:
    def __init__(self, lq, rq, tag, unconstrained=False):
        self.lq = lq
        self.rq = rq
        self.tag = tag
        self.simple = not unconstrained

class AsciiDocParser(xml.sax.xmlreader.XMLReader):
    NS = "http://ns.crustytoothpaste.net/text-markup"
    PREFIX = "_tmarkup"
    def __init__(self, ch = None):
        self.dh = None
        self.enth = None
        self.eh = None
        self.ch = ch
        self.state = AsciiDocStateConstants.START
        self.level = 0
        self.data = []
        self.inlines = []
    @staticmethod
    def _inline_tag(start, end):
        tagmap = {
            "'": "emphasis",
            "_": "emphasis",
            "*": "strong",
            "+": "monospace",
            "`": "monospace",
            "#": "null"
        }
        if start != end:
            raise NotImplementedError
        return tagmap[start]
    @staticmethod
    def _process_quotes(text):
        """Process any quotes in this text and replace them with tags."""
        tags = [
            Quote("**", "**", "strong", True),
            Quote("*", "*", "strong"),
            Quote("``", "''", "quote"),
            Quote("'", "'", "emphasis"),
            Quote("`", "'", "quote"),
            Quote("+++", "+++", "span", True),
            Quote("$$", "$$", "span", True),
            Quote("++", "++", "monospace", True),
            Quote("+", "+", "monospace"),
            Quote("__", "__", "emphasis", True),
            Quote("_", "_", "emphasis"),
            Quote("##", "##", "span", True),
            Quote("#", "#", "span"),
            Quote("^", "^", "superscript", True),
            Quote("~", "~", "subscript", True)
        ]
        for q in tags:
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
    @staticmethod
    def _preprocess_for_tagging(text):
        """Converts angle brackets into tags."""
        def repl(mo):
            if mo.group(0) == "<":
                return "<c-u003c/>"
            else:
                return "<c-u003e/>"
        return re.sub(r"[<>]", repl, text)
    def _process_text(self, text):
        text = self._preprocess_for_tagging(text)
        text = self._process_quotes(text)
        self._process_tags(text)
    def _handle_line(self, line):
        TITLE_CHARS = "=-~^+"
        k = AsciiDocStateConstants
        # A single line comment, not a comment block.
        if line.startswith("//") and line[2] != "/":
            return
        if self.state == k.START:
            if line[0] == "[":
                raise NotImplementedError
            elif line[0] in "=":
                m = re.match(r"(={1,5})\s+(.*\S*)\s+\1\s*$", line)
                if m is None:
                    self.state = k.TEXT_LINE
                    self._process_text(line)
                else:
                    l = len(m.group(1))
                    self._start_section(l, m.group(2))
            else:
                self.state = k.TEXT_LINE
                self.data.append(line)
        elif self.state == k.TEXT_LINE or self.state == k.IN_PARA:
            if line[0] == "[":
                raise NotImplementedError
            elif line[0] in TITLE_CHARS:
                log("start of line is title char", line[0])
                prev_line = self.data.pop()
                l = len(prev_line)
                pat = r"{0}{1}{3},{4}{2}$".format("\\" + line[0], "{", "}",
                        l - 2, l + 2)
                m = re.match(pat, line)
                if m is None:
                    self._process_text(prev_line)
                    self.data.append(line)
                else:
                    self._start_section(TITLE_CHARS.index(line[0]), prev_line,
                            line)
            elif re.match("^\s*$", line):
                if self.state == k.IN_PARA:
                    self._flush()
                self.state = k.PARA_START
            else:
                if len(self.data):
                    self._process_text(self.data.pop())
                self.data.append(line)
        elif self.state == k.PARA_START:
            self._flush()
            if line[0] == "[":
                raise NotImplementedError
            elif re.match("^\s*$", line):
                return
            else:
                self.data.append(line)
            self._start_para()
            self.state = k.IN_PARA
        else:
            raise NotImplementedError
    def _flush_text(self):
        while len(self.data):
            self._process_text(self.data.pop())
    def _flush(self):
        self._flush_text()
        if self.state == AsciiDocStateConstants.IN_PARA:
            while len(self.inlines):
                self._end_element("inline")
                self.inlines.pop()
            self._end_element("para")
            self.state = AsciiDocStateConstants.PARA_START
        self.ch.ignorableWhitespace("\n")
    def _start_para(self, type_ = None):
        if self.state == AsciiDocStateConstants.IN_PARA:
            raise AsciiDocStateError("Only one para at a time, please")
        self.ch.ignorableWhitespace("\n")
        self._start_element("para")
        log("start_para: state is", self.state)
    def _start_section(self, level, title, line = None):
        title = chomp(title)
        if self.state == AsciiDocStateConstants.IN_PARA:
            self._flush()
        if level == 0:
            if self.level == 0:
                # Don't create a new element here because we already have a root
                # element.
                self._start_element("title")
                self._process_text(title)
                self._end_element("title")
            else:
                # Just start a paragraph, since we can't have more than one
                # root element.
                self._start_para()
                self._process_text(title)
                if line is not None:
                    self._process_text(line)
        elif level == self.level:
            self._end_element("section")
            self._start_element("section")
            self._start_element("title")
            self._process_text(title)
            self._end_element("title")
        elif level < self.level:
            while level < self.level:
                self._end_element("section")
                self.level -= 1
            self._end_element("section")
            self._start_element("section")
            self._start_element("title")
            self._process_text(title)
            self._end_element("title")
        else:
            while level > self.level:
                self.level += 1
                self._start_element("section")
                self._start_element("title")
                if level == self.level:
                    self._process_text(title)
                self._end_element("title")
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
    def parse(self, source):
        self.ch.startDocument()
        self.ch.startPrefixMapping(self.PREFIX, self.NS)
        self._start_element("root")
        self.ch.ignorableWhitespace("\n")
        for line in source:
            self._handle_line(line)
        self._flush()
        while self.level > 0:
            self._end_element("section")
            self.level -= 1
        self._end_element("root")
        self.ch.endPrefixMapping(self.PREFIX)
        self.ch.endDocument()
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

def create_parser():
    return AsciiDocParser()
