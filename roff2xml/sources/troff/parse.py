import io
import os
import string
import sys
import xml.sax.xmlreader

from xml.sax.xmlreader import AttributesNSImpl as Attributes

import roff2xml.sources.troff.requests
import roff2xml.sources.troff.stringlike

from roff2xml.sources.troff import log

class Environment:
    def __init__(self):
        self.cc = '.'
        self.c2 = "'"
        self.ec = '\\'

class ParsingError(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason

class ParseObject:
    def invoke(self, lp):
        pass
    def postparse(self):
        pass

class JunkData(ParseObject):
    def __init__(self, state, *args):
        pass
    def __str__(self):
        return ""

class CharacterData(ParseObject):
    def __init__(self, state, *data):
        self.state = state
        self.data = "".join(data)
    def invoke(self, lp):
        self.state.ch.characters(self.data)
    def __str__(self):
        return self.data

class Escape(ParseObject):
    def __init__(self, state, name):
        self.state = state
        self.name = name
    def delay(self):
        return 0
    @staticmethod
    def _escape(c):
        if c == '"':
            return '""'
        elif c == "\n":
            return "\\\n"
        else:
            return c

class StringEscape(Escape):
    def __init__(self, state, name):
        self.state = state
        self.name = name
    def __str__(self):
        try:
            s = self._escape(str(self.state.requests[self.name](self.state)))
            log("esc", self.name, "==", s)
            return s
        except Exception as e:
            return ""

# FIXME: not implemented properly
class ArgumentEscape(Escape):
    def __init__(self, state, item):
        self.state = state
        self.item = item
    def __str__(self):
        try:
            return self._escape(str(self.state.requests[self.name](self.state)))
        except Exception as e:
            return ""

class NumericEscape(Escape):
    def __init__(self, state, name, increment):
        self.state = state
        self.name = name
        self.increment = increment
        self.reg = None
        self.val = None
    def __str__(self):
        try:
            if self.val is None:
                self.reg = self.state.numregs[self.name](self.state)
                self.val = self.reg.value(self.increment)
            log("reg", self.reg, self.increment)
            log("regv", self.val)
            s = str(self.val)
            log("regs", s)
            return s
        except Exception as e:
            log(e)
            return "0"

class DelayedEscape(Escape):
    def __init__(self, state, data):
        self.state = state
        self.data = data
    def delay(self):
        return 1
    def __str__(self):
        return self.data

class CharacterEscape(Escape):
    def __init__(self, state, data):
        self.state = state
        self.data = data
    def __str__(self):
        return self.data

class NumericNamespacedParseObject(ParseObject):
    pass

class StringNamespacedParseObject(ParseObject):
    def __init__(self, state, name, *args):
        self.state = state
        self.name = name
        self.args = args
        self.brk = True
    def invoke(self, lp):
        pass

class Macro(StringNamespacedParseObject):
    def __init__(self, state, name, *args):
        self.state = state
        self.name = name
        self.args = args
        self.brk = True

class Invocable(StringNamespacedParseObject):
    def invoke(self, lp):
        try:
            res = self.state.requests[self.name](self.state).execute(self)
            if res is not None:
                (s, callinfo) = res
                lp.inject(s, callinfo.args)
        except Exception as e:
            pass
    def postparse(self):
        try:
            self.state.requests[self.name](self.state).postparse()
        except Exception as e:
            pass
    def __str__(self):
        return "Invocable {}; break: {}; args: {}".format(self.name, self.brk,
                self.args)

class BreakingInvocable(Invocable):
    def __init__(self, *args):
        Invocable.__init__(self, *args)
        self.brk = True

class NonBreakingInvocable(Invocable):
    def __init__(self, *args):
        Invocable.__init__(self, *args)
        self.brk = False

class LineParserStateConstants:
    START = 0
    IN_REQNAME = 1
    SEPARATOR = 2
    IN_ARG = 3
    IN_QUOTEDARG = 4
    IN_DBLQUOTE = 5
    IN_TEXT = 6
    IN_ESCAPE = 7
    CONTINUATION = 8
    IN_COMMENT = 9
    EOL = 10
    EOF = 11
    IN_COPY = 12
    FLUSHLINE = 13
    IN_TEXTDELAY = 14
    IN_COPYDELAY = 15
    IN_ARGDELAY = 16
    IN_QUOTEDARGDELAY = 17

class LineParser:
    """Parses troff input line-by-line."""
    def __init__(self, state, line):
        self.state = state
        self.data = line
        self.chartrap = []
        self.request = False
        self.brk = False
        self.name = None
        self.curreq = None
    def append(self):
        self.items.append(self.ctxt)
        ctxt = ""
    def _set_request_name(self, reqname):
        self.items.append(reqname)
        try:
            self.curreq = self.state.requests[reqname](self.state)
            self.curreq.preparse()
        except KeyError:
            pass
    def _cur_is_long_last_arg(self):
        if self.curreq is None:
            return False
        if self.curreq.max_args() != len(self.items):
            return False
        return self.curreq.long_last_arg()
    def _cur_is_name_arg(self):
        if self.curreq is None:
            return False
        if len(self.items) != 1:
            return False
        return self.curreq.first_arg_is_name()
    def _peek_next_character(self):
        if len(self.data) == 0:
            raise StopIteration
        return self.data[0]
    def _next_character(self):
        c = self._peek_next_character()
        self.data = self.data[1:]
        if len(self.chartrap) != 0:
            self.chartrap[-1] -= 1
            if self.chartrap[-1] == 0:
                self.chartrap.pop()
                self.state.macroargs.pop()
        return c
    def inject(self, more, args=None):
        s = str(more)
        self.data = "".join([s, self.data])
        if args is not None:
            self.chartrap.append(len(s))
            self.state.macroargs.append(args)
        elif len(self.chartrap) != 0:
            self.chartrap[-1] += len(s)
    def _parse_escape_name(self):
        s = ""
        c = self._next_character()
        if c == "(":
            cnt = 0
            while cnt < 2:
                c = self._next_character()
                if c.isspace():
                    break
                elif c == self.state.env[0].ec:
                    esc = self._parse_escape()
                    self.inject(str(esc))
                else:
                    s += c
                    cnt += 1
            return s
        elif c == "[" and self.state.extended_names():
            c = self._next_character()
            while c != "]" and not c.isspace():
                if c == self.state.env[0].ec:
                    esc = self._parse_escape()
                    self.inject(str(esc))
                else:
                    s += c
                c = self._next_character()
            return s
        else:
            return c
    def _parse_escape(self):
        """Parse an escape and return it.

        Note that the first escape character is not passed to the function.
        """
        c = self._next_character()
        s = ""
        if c == self.state.env[0].ec:
            return DelayedEscape(self.state, self.state.env[0].ec)
        elif c == "*":
            return StringEscape(self.state, self._parse_escape_name())
        elif c == "n":
            inc = 0
            x = self._peek_next_character()
            if x in "+-":
                self._next_character()
                inc = -1 if x == "-" else 1
            return NumericEscape(self.state, self._parse_escape_name(), inc)
        elif c == "\n":
            return CharacterEscape(self.state, "")
        elif c == "f":
            # FIXME: implement correctly
            self._parse_escape_name()
            return CharacterEscape(self.state, "")
        elif c == "$":
            try:
                s = self._parse_escape_name()
                # FIXME: handle \$0 correctly.
                log("escape name is", s)
                n = int(s) - 1
                log("nmacroargs", len(self.state.macroargs))
                log("nmacroargs set", len(self.state.macroargs[-1]))
                return CharacterEscape(self.state, self.state.macroargs[-1][n])
            except Exception as e:
                pass
        return CharacterEscape(self.state, "")
    def parse(self):
        env = self.state.env[0]
        ctxt = ""
        name = ""
        self.items = []
        kind = None
        k = LineParserStateConstants
        pstate = k.START
        while True:
            c = self._next_character()
            if pstate == k.EOF:
                raise StopIteration
            if pstate == k.START:
                if self.state.copy_until is not None:
                    kind = JunkData
                    pstate = k.IN_COPY
                elif c == "\n":
                    kind = CharacterData
                    pstate = k.EOL
                elif c == env.cc:
                    kind = BreakingInvocable
                    pstate = k.IN_REQNAME
                elif c == env.c2:
                    kind = NonBreakingInvocable
                    pstate = k.IN_REQNAME
                elif c == env.ec:
                    esc = self._parse_escape()
                    log("escape is", str(esc))
                    self.inject(esc)
                    if esc.delay():
                        kind = CharacterData
                        pstate = k.IN_TEXTDELAY
                else:
                    kind = CharacterData
                    pstate = k.IN_TEXT
                    ctxt += c
            elif pstate == k.IN_REQNAME:
                if c == "\n":
                    self._set_request_name(name)
                    pstate = k.EOL
                elif c.isspace():
                    pstate = k.SEPARATOR
                    self._set_request_name(name)
                elif not self.state.extended_names() and len(name) == 2:
                    pstate = k.IN_ARG
                    self._set_request_name(name)
                    ctxt += c
                else:
                    name += c
            elif pstate == k.SEPARATOR:
                log("in separator", c)
                if c == "\n":
                    self.items.append(ctxt)
                    ctxt = ""
                    pstate = k.EOL
                elif c == env.ec:
                    esc = self._parse_escape()
                    log("sep escape is", str(esc))
                    self.inject(esc)
                    if esc.delay():
                        kind = CharacterData
                        pstate = k.IN_ARGDELAY
                    pstate = k.IN_ARG
                elif c.isspace():
                    pass
                elif c == '"':
                    pstate = k.IN_QUOTEDARG
                else:
                    log("in separator", c)
                    pstate = k.IN_ARG
                    ctxt += c
            elif pstate == k.IN_ARG or pstate == k.IN_ARGDELAY:
                log("in arg char is", c)
                if c == "\n":
                    self.items.append(ctxt)
                    ctxt = ""
                    pstate = k.EOL
                elif c == env.ec and pstate == k.IN_ARG:
                    esc = self._parse_escape()
                    log("arg escape is", str(esc))
                    self.inject(esc)
                    if esc.delay():
                        kind = CharacterData
                        pstate = k.IN_ARGDELAY
                elif self._cur_is_long_last_arg():
                    ctxt += c
                elif c.isspace():
                    self.items.append(ctxt)
                    ctxt = ""
                    log("in arg space", self.items)
                    pstate = k.SEPARATOR
                elif self._cur_is_name_arg() and not self.state.extended_names() and len(ctxt) == 2:
                    self.items.append(ctxt)
                    ctxt = c
                else:
                    ctxt += c
            elif pstate == k.IN_QUOTEDARG:
                if c == "\n":
                    pstate = k.EOL
                elif self._cur_is_long_last_arg():
                    ctxt += c
                elif c == '"':
                    pstate = k.IN_DBLQUOTE
                else:
                    ctxt += c
            elif pstate == k.IN_DBLQUOTE:
                if c == '"':
                    pstate = k.IN_QUOTEDARG
                    ctxt += c
                elif c == "\n":
                    pstate = k.EOL
                else:
                    pstate = k.SEPARATOR
                    self.items.append(ctxt)
                    ctxt = c
            elif pstate == k.IN_TEXT:
                if c == "\n":
                    ctxt += " "
                    pstate = k.EOL
                elif c == env.ec:
                    esc = self._parse_escape()
                    log("text escape is", str(esc))
                    self.inject(esc)
                    if esc.delay():
                        pstate = k.IN_TEXTDELAY
                else:
                    ctxt += c
            elif pstate == k.IN_TEXTDELAY:
                if c == "\n":
                    ctxt += "  "
                    pstate = k.EOL
                else:
                    ctxt += c
                    pstate = k.IN_TEXT
            elif pstate == k.IN_COPY or pstate == k.IN_COPYDELAY:
                # FIXME: Handle pecularities of copy mode
                if c == env.ec and pstate == k.IN_COPY:
                    esc = self._parse_escape()
                    self.inject(esc)
                    if esc.delay():
                        pstate = k.IN_COPYDELAY
                else:
                    ctxt += c
                    pstate = k.IN_COPY
                if ctxt.endswith(self.state.copy_until):
                    s = ctxt[:-len(self.state.copy_until)] + "\n"
                    mdata = roff2xml.sources.troff.stringlike.MacroData(self.state, s)
                    if self.state.copy_to is not None:
                        self.state.requests[self.state.copy_to] = mdata
                    self.state.set_copy_mode(None, None)
                    pstate = k.FLUSHLINE
            elif pstate == k.FLUSHLINE:
                # FIXME: interpret continuations and increments
                if c == "\n":
                    pstate = k.EOL
            if pstate == k.EOL:
                if ctxt:
                    self.items.append(ctxt)
                ctxt = ""
                if kind is None:
                    log(self.items)
                    raise ParsingError("unknown kind of data")
                result = kind(self.state, *self.items)
                more = (yield result)
                result.postparse()
                if more is not None:
                    self.inject(more)
                kind = None
                self.items = []
                self.curreq = None
                name = ""
                if self.state.copy_until is not None:
                    pstate = k.IN_COPY
                    kind = JunkData
                else:
                    pstate = k.START
    __iter__ = parse

class ContentHandlerWrapper:
    NS_TROFF = "http://ns.crustytoothpaste.net/troff"
    def __init__(self, ch):
        self.ch = ch
        self.stack = []
    def __getattr__(self, name):
        return getattr(self.ch, name)
    def startElementNS(self, name, qname, attrs):
        self.stack.append((name[0], name[1], qname))
        self.ch.startElementNS(name, qname, attrs)
    def endElementNS(self, name, qname):
        self.ch.endElementNS(name, qname)
        self.stack.pop()
    def startBlock(self, attrs=None):
        self.startTroffElement("block", attrs)
    def endBlock(self, force=False):
        if force:
            tos = self.stack[-1]
            while tos[2] != "_troff:block":
                self.endElementNS((tos[0], tos[1]), tos[2])
                tos = self.stack[-1]
        self.endTroffElement("block")
        self.ignorableWhitespace("\n")
    def startTroffElement(self, localname, attrs=None):
        if attrs is None:
            attrs = Attributes({}, {})
        self.startElementNS((self.NS_TROFF, localname), "_troff:"+localname,
                attrs)
    def endTroffElement(self, localname):
        self.endElementNS((self.NS_TROFF, localname), "_troff:"+localname)

class ParserState:
    F_EXTNAME = 1
    def __init__(self, env, flags):
        self.env = env
        self.flags = [flags]
        self.requests = {}
        self.numregs = {}
        self.nregs = {}
        self.copy_until = None
        self.copy_to = None
        self.macroargs = []
        self._initialize_requests()
    def _initialize_requests(self):
        for k, v in roff2xml.sources.troff.requests.__dict__.items():
            if k.startswith("RequestImpl_"):
                self.requests[k[12:]] = v
    def set_copy_mode(self, macro, ending):
        if ending is None:
            self.copy_to = None
            self.copy_until = None
            return
        if ending == "":
            ending = self.env[0].cc
        self.copy_until = "\n" + self.env[0].cc + ending
        self.copy_to = macro
    def push_flags(self, flags):
        self.flags.append(flags)
    def get_flags(self):
        return self.flags[-1]
    def pop_flags(self):
        return self.flags.pop()
    def extended_names(self):
        return self.get_flags() & self.F_EXTNAME

class TroffParser(xml.sax.xmlreader.IncrementalParser):
    def __init__(self):
        self.parser = Parser()
        self.dh = None
        self.enth = None
        self.eh = None
    def parse(self, source):
        pass
    def feed(self, data):
        self.parser.lp.inject(data)
    def close(self):
        pass
    def reset(self):
        pass
    def getContentHandler(self):
        return self.parser.state.ch
    def setContentHandler(self, handler):
        self.parser.state.ch = handler
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

class Parser:
    def __init__(self, ch):
        self.env = [Environment()]
        self.state = ParserState(self.env, 0)
        self.lp = LineParser(self.state, "")
        self.state.ch = ContentHandlerWrapper(ch)
    def _set_up(self):
        self.state.ch.startDocument()
        self.state.ch.startPrefixMapping("_troff", self.state.ch.NS_TROFF)
        self.state.ch.startTroffElement("main")
        self.state.ch.startBlock()
    def _tear_down(self):
        self.state.ch.endBlock(force=True)
        self.state.ch.endTroffElement("main")
        self.state.ch.endPrefixMapping("_troff")
        self.state.ch.ignorableWhitespace("\n")
        self.state.ch.endDocument()
    def parse(self, string):
        self.lp.inject(string)
        self._set_up()
        for item in self.lp.parse():
            log(item, type(item))
            item.invoke(self.lp)
        self._tear_down()
 
def create_parser():
    return TroffParser()
