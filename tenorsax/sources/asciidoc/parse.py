import re
import xml.sax.xmlreader

from tenorsax.util import *

def chomp(line):
    if line[-1] == "\n":
        return line[:-1]
    return line

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
    def _process_text(self, text):
        self.ch.characters(text)
    def _handle_line(self, line):
        TITLE_CHARS = "=-~^+"
        k = AsciiDocStateConstants
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
                pat = r"{0}{1}{3},{4}{2}$".format(line[0], "{", "}", l - 2,
                        l + 2)
                m = re.match(pat, line)
                if m is None:
                    self._process_text(prev_line)
                    self.data.append(line)
                else:
                    self._start_section(TITLE_CHARS.index(line[0]), prev_line,
                            line)
                self.state = k.TEXT_LINE
            elif re.match("^\s*$", line):
                self.state = k.PARA_START
            else:
                if len(self.data):
                    self._process_text(self.data.pop())
                self.data.append(line)
        elif self.state == k.PARA_START:
            while len(self.data):
                self._process_text(self.data.pop())
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
    def _flush(self):
        while len(self.data):
            self._process_text(self.data.pop())
        if self.state == AsciiDocStateConstants.IN_PARA:
            self._end_element("para")
        self.ch.ignorableWhitespace("\n")
    def _start_para(self, type_ = None):
        self.ch.ignorableWhitespace("\n")
        self._start_element("para")
    def _start_section(self, level, title, line = None):
        title = chomp(title)
        if self.state == AsciiDocStateConstants.IN_PARA:
            self._end_element("para")
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
        if attrs:
            raise NotImplementedError
        self.ch.startElementNS((self.NS, name), self.PREFIX + ":" + name, attrs)
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