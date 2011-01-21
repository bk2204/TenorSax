import os.path
import tenorsax.sources.troff.stringlike

from xml.sax.xmlreader import AttributesNSImpl as Attributes

from tenorsax.sources.troff import log
from tenorsax.sources.troff.numeric import IntegerNumberRegister, FloatNumberRegister

class RequestImplementation(tenorsax.sources.troff.stringlike.StringNamespacedData):
    F_TERMINAL = 1
    F_NAME = 2
    F_NUMERIC = 4
    F_INCREMENTAL = 12
    F_CONDITIONAL = 16
    F_EXECUTABLE = 32
    def __init__(self, state):
        tenorsax.sources.troff.stringlike.StringNamespacedData.__init__(self, state)
        self.flags = 0
    def max_args(self):
        return 0
    def _arg_flags(self, i):
        return 0
    def arg_flags(self, i):
        try:
            return self._arg_flags(i)
        except IndexError:
            return 0
    #def long_last_arg(self):
    #    return self.flags & self.F_LONGLAST
    #def first_arg_is_name(self):
    #    return self.flags & self.F_NAMEARG
    def __str__(self):
        return ""

class XMLRequestImplementation(RequestImplementation):
    def _arg_flags(self, i):
        return 0
    def _tuple_from_qname(self, qname):
        prefix = None
        localname = None
        uri = None
        res = qname.split(':')
        if len(res) == 1:
            prefix = ""
            localname = res[0]
        else:
            (prefix, localname) = res
            uri = self.state.mapping[prefix]
        return (prefix, uri, localname, qname)

class RequestImpl_als(RequestImplementation):
    def _arg_flags(self, i):
        return (self.F_NAME, self.F_NAME)[i]
    def max_args(self):
        return 2
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) < 2:
            return
        self.state.requests[args[1]] = self.state.requests[args[0]]

class RequestImpl_br(RequestImplementation):
    def execute(self, callinfo):
        if callinfo.brk:
            self.state.ch.endBlock(force=True)
            self.state.ch.startBlock()

class RequestImpl_do(RequestImplementation):
    def execute(self, callinfo):
        from tenorsax.sources.troff.parse import Invocable
        req = Invocable(self.state, *callinfo.args)
        try:
            macro = self.state.requests[req.name](self.state)
            macro.preparse()
            macro.execute(req)
            macro.postparse()
        except KeyError:
            pass
    def preparse(self):
        self.state.push_flags(self.state.get_flags() | self.state.F_EXTNAME)
    def postparse(self):
        self.state.pop_flags()

class RequestImpl_de(RequestImplementation):
    def _arg_flags(self, i):
        return (self.F_NAME, self.F_NAME)[i]
    def max_args(self):
        return 2
    def execute(self, callinfo):
        args = callinfo.args
        # FIXME: what to do in this case?
        if len(args) == 0:
            return
        elif len(args) == 1:
            self.state.set_copy_mode(args[0], "")
        else:
            self.state.set_copy_mode(args[0], args[1])

class RequestImpl_ds(RequestImplementation):
    def _arg_flags(self, i):
        return (self.F_NAME, self.F_TERMINAL)[i]
    def max_args(self):
        return 2
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) == 0:
            return
        elif len(args) == 1:
            args.append("")
        self.state.requests[args[0]] = tenorsax.sources.troff.stringlike.StringData(self.state, args[1])

class RequestImpl_el(RequestImplementation):
    def _arg_flags(self, i):
        return (self.F_EXECUTABLE,)[i]
    def max_args(self):
        return 1
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) == 0:
            return
        test = not self.state.conditionals.pop()
        if test:
            return (args[0], None)

class RequestImpl_end(XMLRequestImplementation):
    def _arg_flags(self, i):
        return 0
    def max_args(self):
        return 1
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) < 1:
            return
        try:
            element = self._tuple_from_qname(args[0])
            self.state.ch.endElementNS((element[1], element[2]), element[3])
        except:
            pass

class RequestImpl_ie(RequestImplementation):
    def _arg_flags(self, i):
        return (self.F_CONDITIONAL, self.F_EXECUTABLE)[i]
    def max_args(self):
        return 2
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) == 0:
            return
        self.state.conditionals.append(args[0])
        if args[0]:
            return (args[1], None)

class RequestImpl_if(RequestImplementation):
    def _arg_flags(self, i):
        return (self.F_CONDITIONAL, self.F_EXECUTABLE)[i]
    def max_args(self):
        return 2
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) == 0:
            return
        if args[0]:
            return (args[1], None)

class RequestImpl_ig(RequestImplementation):
    def _arg_flags(self, i):
        return (self.F_NAME,)[i]
    def max_args(self):
        return 1
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) == 0:
            self.state.set_copy_mode(None, "")
        else:
            self.state.set_copy_mode(None, args[0])

class RequestImpl_namespace(RequestImplementation):
    def _arg_flags(self, i):
        return 0
    def max_args(self):
        return 2
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) != 2:
            return
        self.state.mapping[args[0]] = args[1]

class NumberRegisterRequestImplementation(RequestImplementation):
    def _arg_flags(self, i):
        return (self.F_NAME, self.F_INCREMENTAL, self.F_NUMERIC)[i]
    def max_args(self):
        return 3
    @classmethod
    def _value(klass, cur, diff):
        try:
            if diff[0] in "+-":
                return cur + klass.func(float(diff))
            return klass.func(float(diff))
        except:
            return cur
    def execute(self, callinfo):
        args = callinfo.args
        diff = 0
        inc = 0
        if len(args) == 0:
            return
        name = args[0]
        if len(args) >= 2:
            diff = args[1]
        try:
            if len(args) >= 3:
                inc = self.func(float(args[2]))
        except:
            inc = 0
        curval = 0
        if name in self.state.numregs:
            # We don't use value() here because it will autoincrement.  We don't
            # want that.
            curval = self.state.numregs[name].val
        self.store(name, curval, diff, inc)

class RequestImpl_nr(NumberRegisterRequestImplementation):
    func = staticmethod(int)
    def store(self, name, curval, diff, inc):
        self.state.numregs[name] = IntegerNumberRegister(self.state, name,
                self._value(curval, diff), inc, "0")

class RequestImpl_nrf(NumberRegisterRequestImplementation):
    func = staticmethod(float)
    def store(self, name, curval, diff, inc):
        self.state.numregs[name] = FloatNumberRegister(self.state, name,
                self._value(curval, diff), inc, "0")

class RequestImpl_rm(RequestImplementation):
    def _arg_flags(self, i):
        return (self.F_NAME,)[i]
    def max_args(self):
        return 1
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) < 1:
            return
        del self.state.requests[args[0]]

class RequestImpl_rn(RequestImplementation):
    def _arg_flags(self, i):
        return (self.F_NAME, self.F_NAME)[i]
    def max_args(self):
        return 2
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) < 2:
            return
        self.state.requests[args[1]] = self.state.requests[args[0]]
        del self.state.requests[args[0]]

class RequestImpl_so(RequestImplementation):
    def _arg_flags(self, i):
        return 0
    def max_args(self):
        return 1
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) == 0:
            return
        s = ""
        if args[0].startswith("/"):
            path = args[0]
        else:
            d = os.path.dirname(self.state.filename)
            path = os.path.join(d, args[0])
        log("path", path)
        s += '.do tenorsax filename "' + path + '"\n'
        with open(path) as fp:
            s += "".join(fp.readlines())
        s += '.do tenorsax filename "' + self.state.filename + '"\n'
        return (s, None)

class RequestImpl_start(XMLRequestImplementation):
    def max_args(self):
        return 1024
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) < 1:
            return
        try:
            attrs = {}
            qnames = {}
            element = self._tuple_from_qname(args[0])
            for i in args[1:]:
                item = i.split("=", 2)
                attr = self._tuple_from_qname(item[0])
                attrs[(attr[1], attr[2])] = item[1]
                qnames[attr[3]] = item[1]
            self.state.ch.startElementNS((element[1], element[2]), element[3],
                    Attributes(attrs, qnames))
        except:
            pass

class RequestImpl_tenorsax(RequestImplementation):
    def _arg_flags(self, i):
        return 0
    def max_args(self):
        return 2
    @staticmethod
    def _get_boolean(s):
        try:
            val = int(s)
        except ValueError:
            if s.lower() in ("on", "enable", "enabled", "true", "yes"):
                val = True
            else:
                val = False
        return bool(val)
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) < 2:
            return
        if args[0] == "ext":
            self.state.flags[0] = ~0 if self._get_boolean(args[1]) else 0
        elif args[0] == "filename":
            self.state.filename = args[1]
        elif args[0] == "trace":
            self.state.trace = int(args[1])
