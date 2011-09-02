#-
# Copyright © 2011 brian m. carlson
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
    def _process_text(self, text):
        # FIXME: this does not handle pairs where the starting and ending marks
        # are not identical.  It also doesn't handle single quotation marks
        # because of contractions.
        pat = re.compile(r"(^|[^\\*+`#]*)([*+`#])([^*+`#]*)")
        mlst = pat.findall(text)
        for prev, mark, txt in mlst:
            self.ch.characters(prev)
            tag = self._inline_tag(mark, mark)
            if len(self.inlines) and self.inlines[-1][1] == mark:
                inline = self.inlines.pop()
                self._end_element("inline")
            else:
                self.inlines.append((tag, mark))
                self._start_element("inline", {"type": tag})
            self.ch.characters(txt)
        if len(mlst) == 0:
            self.ch.characters(text)
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
