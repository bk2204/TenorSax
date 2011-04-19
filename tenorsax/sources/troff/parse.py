import decimal
import io
import os
import string
import sys
import xml.sax.xmlreader

from xml.sax.xmlreader import AttributesNSImpl as Attributes

import tenorsax.sources.troff.requests
import tenorsax.sources.troff.stringlike

from tenorsax.util import *

class Environment:
    def __init__(self):
        self.cc = '.'
        self.c2 = "'"
        self.ec = '\\'
        self.fill = True

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
        self.text = ""
    def delay(self):
        return 0
    def executable(self):
        """Return True if this escape delimits a block of code."""
        return False
    @staticmethod
    def _escape(c):
        if c == '"':
            return '""'
        elif c == "\n":
            return "\\\n"
        else:
            return c
    @staticmethod
    def _gen_name(name):
        if len(name) == 1:
            return name
        elif len(name) == 2:
            return "(" + name
        else:
            return "[" + name + "]"

class StringEscape(Escape):
    def __init__(self, state, name):
        super().__init__(state, name)
        self.state = state
        self.name = name
    def __str__(self):
        try:
            s = self._escape(str(self.state.requests[self.name](self.state)))
            log("esc", self.name, "==", s)
            return s
        except Exception as e:
            return ""

class ConditionalEscape(Escape):
    def __init__(self, state, is_start):
        self.state = state
        self.is_start = is_start
    def executable(self):
        return True
    def __str__(self):
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

class Comment(Escape):
    def __init__(self, state, data):
        self.state = state
        self.data = data
    def __str__(self):
        return ""

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
        res = None
        try:
            res = self.state.requests[self.name](self.state).execute(self)
        except KeyError:
            trace(self.state, TRACE_UNDEF, "request", self.name,
                "is not defined")
        except Exception:
            pass
        if res is not None:
            (s, callinfo) = res
            args = None
            if callinfo is not None:
                args = [callinfo.name]
                args.extend(callinfo.args)
            lp.inject(s, args)
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

def calculate(n1, op, n2):
    """Evaluate a binary numeric expression."""
    # NB: this does not use eval even where it might be shorter or cleaner to
    # avoid any sort of arbitrary code execution.
    if op == '+':
        return n1 + n2
    elif op == '-':
        return n1 - n2
    elif op == '*':
        return n1 * n2
    elif op == '/':
        return n1 // n2
    elif op == '%':
        return n1 % n2
    elif op == '&':
        return int(bool(n1 and n2))
    elif op == ':':
        return int(bool(n1 or n2))
    elif op == '<':
        return int(n1 < n2)
    elif op == '<=':
        return int(n1 <= n2)
    elif op == '>':
        return int(n1 > n2)
    elif op == '>=':
        return int(n1 >= n2)
    elif op == '=' or op == '==':
        return int(n1 == n2)
    elif op == '<>':
        return int(n1 != n2)
    elif op == '<?':
        return min(n1, n2)
    elif op == '>?':
        return max(n1, n2)
    else:
        raise ValueError("undefined operation")

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
    IN_EXECUTABLE = 18
    IN_CONDITIONAL = 19
    IN_REQNAMEDELAY = 20

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
        try:
            return self.curreq.arg_flags(len(self.items)-1) & self.curreq.F_TERMINAL
        except AttributeError:
            return False
    def _cur_is_name_arg(self):
        try:
            return self.curreq.arg_flags(len(self.items)-1) & self.curreq.F_NAME
        except AttributeError:
            return False
    def _cur_is_numeric(self):
        try:
            return self.curreq.arg_flags(len(self.items)-1) & self.curreq.F_NUMERIC
        except AttributeError:
            return False
    def _cur_is_incremental(self):
        try:
            return self.curreq.arg_flags(len(self.items)-1) & self.curreq.F_INCREMENTAL
        except AttributeError:
            return False
    def _cur_is_executable(self):
        try:
            return self.curreq.arg_flags(len(self.items)-1) & self.curreq.F_EXECUTABLE
        except AttributeError:
            return False
    def _cur_is_conditional(self):
        try:
            return self.curreq.arg_flags(len(self.items)-1) & self.curreq.F_CONDITIONAL
        except AttributeError:
            return False
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
                log("chartrap", len(self.chartrap), "sprung")
                self.chartrap.pop()
                self.state.macroargs.pop()
        return c
    def inject(self, more, args=None):
        s = str(more)
        self.data = "".join([s, self.data])
        if args is not None:
            self.chartrap.append(len(s))
            self.state.macroargs.append(args)
            log("inserting trap", len(self.chartrap), "for", len(s))
            log("trap", len(self.chartrap), "is", len(args), args)
        elif len(self.chartrap) != 0:
            log("expanding trap", len(self.chartrap), "by", len(s))
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
    def _parse_numeric(self, pstate, c, nparens=0, inc=False):
        """Parse a numerical expression and return its value."""
        k = LineParserStateConstants
        val = 0
        curval = 0
        stk = []
        delay = False
        stnum = True
        nctxt = ""
        op = None
        npstate = pstate
        incchar = ""
        if inc and c in "+-":
            incchar = c
            c = self._next_character()
        while True:
            if c == '\n':
                npstate = k.EOL
                break
            elif c == '(':
                (npstate, val) = self._parse_numeric(pstate,
                        self._next_character(), nparens+1, inc)
                if npstate != pstate:
                    break
            elif c == ')':
                if op is not None:
                    val = calculate(val, op, curval)
                npstate = pstate
                break
            elif c == self.state.env[0].ec and not delay:
                esc = self._parse_escape()
                self.inject(esc)
                if esc.delay():
                    delay = True
            elif c.isspace():
                if nparens == 0:
                    pstate = k.SEPARATOR
                    break
            elif c in "0123456789.":
                nctxt += c
            elif c in "+-":
                if len(nctxt) == 0:
                    nctxt += c
                else:
                    try:
                        curval = decimal.Decimal(nctxt)
                    except ValueError:
                        curval = 0
                    nctxt = ""
                    stk.append(curval)
                    if len(stk) == 2:
                        val = calculate(stk[0], op, stk[1])
                        stk = []
                    op = c
            elif c in "*/%&:":
                log("nctxt", nctxt)
                try:
                    curval = decimal.Decimal(nctxt)
                except ValueError:
                    curval = 0
                nctxt = ""
                stk.append(curval)
                if len(stk) == 2:
                    val = calculate(stk[0], op, stk[1])
                    stk = []
                op = c
            elif c in "<>=":
                try:
                    curval = decimal.Decimal(nctxt)
                except ValueError:
                    curval = 0
                nctxt = ""
                stk.append(curval)
                if len(stk) == 2:
                    val = calculate(stk[0], op, stk[1])
                    stk = []
                op = c
                c = self._next_character()
                s = op + c
                if s in ["==", "<>", "<?", ">?", "<=", ">="]:
                    op = s
                else:
                    # don't read another character
                    continue
            c = self._next_character()
            # FIXME: this is broken
            delay = False
        try:
            curval = decimal.Decimal(nctxt)
        except:
            curval = 0
        stk.append(curval)
        if len(stk) == 2:
            val = calculate(stk[0], op, stk[1])
        elif op is not None or len(nctxt) != 0:
            val = stk[0]
        if nparens == 0:
            self.items.append(incchar + str(val))
        return (npstate, val)

    def _parse_escape_and_copy_text(self, copy=False):
        """Parse an escape and return it and all its component characters.

        This function works just like _parse_escape (and in fact calls it), with
        the exception that it returns a 2-tuple, the first being the escape
        object and the second being the text that makes up the complete escape,
        including the original escape character (which is not passed to the
        function).
        """
        nc = self._next_character
        text = self.state.env[0].ec
        def func(text):
            c = nc()
            text += c
            return c
        self._next_character = lambda: func(text)
        try:
            esc = self._parse_escape(copy)
        finally:
            self._next_character = nc
        return (esc, text)
    def _parse_escape(self, copy=False):
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
        elif c in '#"':
            x = self._peek_next_character()
            while x != "\n":
                self._next_character()
                s += x
                x = self._peek_next_character()
            if c == "#":
                self._next_character()
                s += x
            return Comment(self.state, s)
        elif c == "$":
            try:
                s = self._parse_escape_name()
                log("escape name is", s)
                n = int(s)
                log("nmacroargs", len(self.state.macroargs))
                log("nmacroargs set", len(self.state.macroargs[-1]))
                return CharacterEscape(self.state, self.state.macroargs[-1][n])
            except Exception as e:
                pass
        else:
            if copy:
                return DelayedEscape(self.state, self.state.env[0].ec + c)
            else:
                if c == "f":
                    # FIXME: implement correctly
                    self._parse_escape_name()
                    return CharacterEscape(self.state, "")
                elif c in "{}":
                    return ConditionalEscape(self.state, c == "{")
        return CharacterEscape(self.state, "")

    def _parse_conditional(self, pstate, c):
        k = LineParserStateConstants
        negation = False
        delay = False
        if c == "!":
            negation = True
            c = self._next_character()
        if c == self.state.env[0].ec:
            esc = self._parse_escape()
            self.inject(esc)
            if esc.delay():
                delay = True
            c = self._next_character()
        log("condchar", c)
        if c in "0123456789(+-":
            (pstate, result) = self._parse_numeric(pstate, c)
            self.items.pop()
            result = decimal.Decimal(result)
        else:
            sep = c
            nsep = 1
            strs = []
            cur_s = ""
            log("separator", sep)
            while True:
                c = self._next_character()
                if c == self.state.env[0].ec:
                    if delay:
                        delay = False
                    else:
                        esc = self._parse_escape()
                        self.inject(esc)
                        if esc.delay:
                            delay = True
                elif c == sep:
                    nsep += 1
                    strs.append(cur_s)
                    cur_s = ""
                    if nsep == 3:
                        break
                elif c == "\n":
                    return (k.EOL, None)
                else:
                    cur_s += c
                delay = False
            log("strings", strs[0], strs[1])
            result = strs[0] == strs[1]
            pstate = k.SEPARATOR
        log("conditional result", result)
        result = result > 0
        if negation:
            result = not result
        log("result", result)
        self.items.append(result)
        return (pstate, result)

    def parse(self):
        env = self.state.env[0]
        ctxt = ""
        name = ""
        self.items = []
        kind = None
        k = LineParserStateConstants
        pstate = k.START
        nbraces = 0
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
                    if not env.fill:
                        ctxt += "\n"
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
            elif pstate == k.IN_REQNAME or pstate == k.IN_REQNAMEDELAY:
                if c == "\n":
                    self._set_request_name(name)
                    pstate = k.EOL
                elif c == env.ec:
                    esc = self._parse_escape()
                    self.inject(esc)
                    if esc.delay():
                        kind = CharacterData
                        pstate = k.IN_REQNAMEDELAY
                    else:
                        pstate = k.IN_REQNAME
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
                elif self._cur_is_conditional():
                    pstate = self._parse_conditional(pstate, c)[0]
                elif c == env.ec:
                    esc = self._parse_escape()
                    log("sep escape is", str(esc))
                    self.inject(esc)
                    if esc.delay():
                        kind = CharacterData
                        pstate = k.IN_ARGDELAY
                    elif esc.executable() and esc.is_start:
                        pstate = k.IN_EXECUTABLE
                        nbraces += 1
                    else:
                        pstate = k.IN_ARG
                elif c.isspace():
                    pass
                elif self._cur_is_executable():
                    ctxt += c
                    pstate = k.IN_EXECUTABLE
                elif self._cur_is_numeric():
                    inc = self._cur_is_incremental
                    pstate = self._parse_numeric(pstate, c, inc=inc)[0]
                elif c == '"':
                    pstate = k.IN_QUOTEDARG
                else:
                    log("in separator", c)
                    pstate = k.IN_ARG
                    ctxt += c
            elif pstate == k.IN_EXECUTABLE:
                if c == env.ec:
                    (esc, text) = self._parse_escape_and_copy_text()
                    if esc.executable():
                        if esc.is_start:
                            nbraces += 1
                        else:
                            nbraces -= 1
                            if nbraces == 0:
                                ctxt += "\n"
                                pstate = k.EOL
                    else:
                        ctxt += text
                elif c == "\n":
                    ctxt += "\n"
                    if nbraces == 0:
                        pstate = k.EOL
                else:
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
                elif self._cur_is_numeric():
                    inc = self._cur_is_incremental
                    pstate = self._parse_numeric(pstate, c, inc=inc)[0]
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
            elif pstate == k.IN_QUOTEDARG or pstate == k.IN_QUOTEDARGDELAY:
                if c == "\n":
                    pstate = k.EOL
                elif c == env.ec and pstate == k.IN_QUOTEDARG:
                    esc = self._parse_escape()
                    self.inject(esc)
                    if esc.delay():
                        kind = CharacterData
                        pstate = k.IN_QUOTEDARGDELAY
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
                    ctxt = c if c != " " else ""
            elif pstate == k.IN_TEXT:
                if c == "\n":
                    ctxt += " " if env.fill else "\n"
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
                    ctxt += " " if env.fill else "\n"
                    pstate = k.EOL
                else:
                    ctxt += c
                    pstate = k.IN_TEXT
            elif pstate == k.IN_COPY or pstate == k.IN_COPYDELAY:
                # FIXME: Handle pecularities of copy mode
                if c == env.ec and pstate == k.IN_COPY:
                    esc = self._parse_escape(copy=True)
                    self.inject(esc)
                    if esc.delay():
                        pstate = k.IN_COPYDELAY
                else:
                    ctxt += c
                    pstate = k.IN_COPY
                if ctxt.endswith(self.state.copy_until):
                    s = ctxt[:-len(self.state.copy_until)] + "\n"
                    mdata = tenorsax.sources.troff.stringlike.MacroData(self.state, s)
                    if self.state.copy_to is not None:
                        self.state.requests[self.state.copy_to] = mdata
                    self.state.set_copy_mode(None, None)
                    pstate = k.FLUSHLINE
            elif pstate == k.FLUSHLINE:
                # FIXME: interpret continuations and increments
                if c == "\n":
                    pstate = k.EOL
            if pstate == k.EOL:
                log("eol ctxt", ctxt)
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

class StackItem:
    pass

class ElementStackItem(StackItem):
    def __init__(self, name, qname):
        self.name = name
        self.qname = qname
    def end(self, ch):
        ch.endElementNS(self.name, self.qname)
    def __repr__(self):
        return "ElementStackItem " + repr(self.name) + " " + self.qname

class PrefixStackItem(StackItem):
    def __init__(self, prefix):
        self.prefix = prefix
    def end(self, ch):
        ch.endPrefixMapping(self.prefix)
    def __repr__(self):
        return "PrefixStackItem " + self.prefix

class ContentHandlerWrapper:
    NS_TROFF = "http://ns.crustytoothpaste.net/troff"
    def __init__(self, ch, state):
        self.ch = ch
        self.stack = []
        self.state = state
    def __getattr__(self, name):
        return getattr(self.ch, name)
    def endDocument(self):
        for i in reversed(self.stack):
            i.end(self.ch)
        self.ch.endDocument()
    def startPrefixMapping(self, prefix, uri):
        self.stack.append(PrefixStackItem(prefix))
        self.ch.startPrefixMapping(prefix, uri)
    def endPrefixMapping(self, prefix):
        self.stack.pop().end(self.ch)
    def startElementNS(self, name, qname, attrs):
        if ':' in qname:
            self.startPrefixMapping(qname.split(':')[0], name[0])
        self.stack.append(ElementStackItem(name, qname))
        self.ch.startElementNS(name, qname, attrs)
    def endElementNS(self, name, qname):
        self.stack.pop().end(self.ch)
        while len(self.stack) > 0 and hasattr(self.stack[-1], "prefix"):
            self.stack.pop().end(self.ch)
    def startBlock(self, attrs=None):
        self.startTroffElement("block", attrs)
    def endBlock(self, force=False):
        if len(self.stack) == 0:
            return
        if force:
            tos = self.stack[-1]
            while hasattr(tos, "qname") and tos.qname != "_troff:block":
                tos.end(self)
                if len(self.stack) == 0:
                    return
                tos = self.stack[-1]
        self.endTroffElement("block")
        self.ignorableWhitespace("\n")
    def startTroffElement(self, localname, attrs=None):
        if attrs is None:
            attrs = Attributes({}, {})
        for p, u in self.state.mapping.items():
            self.startPrefixMapping(p, u)
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
        self.mapping = {
                "xml": "http://www.w3.org/XML/1998/namespace"
        }
        self.filename = ""
        self.trace = 0
        self.conditionals = []
    def _initialize_requests(self):
        for k, v in tenorsax.sources.troff.requests.__dict__.items():
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
        self.state.ch = ContentHandlerWrapper(ch, self.state)
    def _set_up(self):
        self.state.ch.startDocument()
        self.state.ch.startTroffElement("main")
        self.state.ch.startBlock()
    def _tear_down(self):
        self.state.ch.endDocument()
    def parse(self, finput):
        try:
            s = ""
            for line in finput:
                if finput.isfirstline():
                    s += '.do tenorsax filename "' + finput.filename() + '"\n'
                s += line
            self.lp.inject(s)
        except AttributeError:
            self.lp.inject(finput)
        self._set_up()
        for item in self.lp.parse():
            log(item, type(item))
            item.invoke(self.lp)
        self._tear_down()
 
def create_parser():
    return TroffParser()
