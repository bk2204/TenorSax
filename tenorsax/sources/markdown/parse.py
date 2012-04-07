#-
# Copyright © 2011–2012 brian m. carlson
# Copyright © 2002–2010 Stuart Rackham
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
import tenorsax.sources
import xml.sax.xmlreader

from tenorsax.util import *
from tenorsax.sources import FancyTextParser, Quote, QuoteParser

class MarkdownStateError(Exception):
    pass

class MarkdownStateConstants:
    START = 1
    PARA_START = 2
    IN_PARA = 3
    TEXT_LINE = 4
    HEADER_LINE = 5
    IN_HEADER = 6

class MarkdownParser(FancyTextParser):
    TITLE_CHARS = "=-"
    def __init__(self, ch = None):
        super().__init__(ch)
        self.data = []
        self.level = 0
        self.inlines = []
    def _handle_title_line(self, line):
        log("start of line is title char", line[0])
        try:
            prev_line = self.data.pop()
        except IndexError:
            return None
        l = len(prev_line)
        # Allow give or take two characters.
        pat = r"{0}{1}{3},{4}{2}$".format("\\" + line[0], "{", "}",
                l - 2, l + 2)
        m = re.match(pat, line)
        if m is None:
            self.data.append(prev_line)
            self.data.append(line)
            return None
        else:
            idx = self.TITLE_CHARS.index(line[0])
            self._start_section(idx, prev_line, line)
            return idx
    @staticmethod
    def _preprocess_for_tagging(text):
        return text
    def _process_text(self, text):
        text = self._preprocess_for_tagging(text)
        self._process_tags(text)
    def _flush_text(self):
        self._process_text(''.join(self.data))
        self.data = []
    def _flush(self):
        self._flush_text()
        if self.state == MarkdownStateConstants.IN_PARA:
            while len(self.inlines):
                self._end_element("inline")
                self.inlines.pop()
            self._end_element("para")
            self.state = MarkdownStateConstants.PARA_START
        self.ch.ignorableWhitespace("\n")
    def _parse_style(self, line):
        mo = re.match(r"^\[(.*)\]$", line)
        if mo is None:
            return None
        return re.split(r",\s*", mo.group(1))
    def _get_line_type(self, line):
        if re.match("^\s*$", line):
            return "blank"
        elif self._parse_style(line):
            return "block-style"
        else:
            return None
    def _next_line(self):
        try:
            return self.lines.pop(0)
        except IndexError:
            raise StopIteration
    def _do_state_machine(self):
        k = MarkdownStateConstants
        line = self._next_line()
        self.state = k.START
        while True:
            linetype = self._get_line_type(line)
            if self.state == k.START:
                if linetype == "block-style":
                    raise NotImplementedError
                elif line[0] in "#":
                    # One-line titles.
                    m = re.match(r"(#{1,5})\s+(.*\S*)(\s+#+)?\s*$", line)
                    if m is None:
                        self.state = k.TEXT_LINE
                        self._generate_metadata(self.metadata)
                        self.data.append(line)
                    else:
                        l = len(m.group(1))
                        self._start_section(l, m.group(2))
                else:
                    self.state = k.HEADER_LINE
                    self.data.append(line)
            elif self.state == k.HEADER_LINE:
                if linetype == "blank":
                    self._generate_metadata(self.metadata)
                    self._flush()
                    self.state = k.PARA_START
                elif line[0] in self.TITLE_CHARS:
                    level = self._handle_title_line(line)
                    log("section title in header line")
                    if level != 0:
                        self.state = k.PARA_START
                else:
                    self._start_para()
                    self.data.append(line)
                    self.state = k.IN_PARA
            elif self.state == k.IN_HEADER:
                if linetype == "blank":
                    self._generate_metadata(self.metadata)
                    self._flush()
                    self.state = k.PARA_START
            elif self.state == k.TEXT_LINE or self.state == k.IN_PARA:
                if linetype == "block-style":
                    raise NotImplementedError
                elif line[0] in self.TITLE_CHARS:
                    self._handle_title_line(line)
                    log("section title in text line")
                elif linetype == "blank":
                    if self.state == k.IN_PARA:
                        self._flush()
                    self.state = k.PARA_START
                else:
                    self.data.append(line)
            elif self.state == k.PARA_START:
                self._flush()
                if linetype == "block-style":
                    raise NotImplementedError
                elif linetype == "blank":
                    pass
                else:
                    self.data.append(line)
                self._start_para()
                self.state = k.IN_PARA
            else:
                raise NotImplementedError
            line = self._next_line()
            log("next line; current state:", self.state)
    def _start_para(self, type_ = None):
        if self.state == MarkdownStateConstants.IN_PARA:
            raise MarkdownStateError("Only one para at a time, please")
        self.ch.ignorableWhitespace("\n")
        self._start_element("para")
        log("start_para: state is", self.state)
    def _start_section(self, level, title, line = None):
        title = chomp(title)
        if self.state == MarkdownStateConstants.IN_PARA:
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
    def parse(self, source):
        self.ch.startDocument()
        self.ch.startPrefixMapping(self.PREFIX, self.NS)
        self._start_element("root")
        self.ch.ignorableWhitespace("\n")
        self.lines = [l for l in source]
        try:
            self._do_state_machine()
        except StopIteration:
            pass
        self._flush()
        while self.level > 0:
            self._end_element("section")
            self.level -= 1
        self._end_element("root")
        self.ch.endPrefixMapping(self.PREFIX)
        self.ch.endDocument()

def create_parser():
    return MarkdownParser()
