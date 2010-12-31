import tenorsax.sources.troff.stringlike

from tenorsax.sources.troff import log
from tenorsax.sources.troff.numeric import IntegerNumberRegister, FloatNumberRegister

class RequestImplementation(tenorsax.sources.troff.stringlike.StringNamespacedData):
    F_LONGLAST = 1
    F_NAMEARG = 2
    def __init__(self, state):
        tenorsax.sources.troff.stringlike.StringNamespacedData.__init__(self, state)
        self.flags = 0
    def max_args(self):
        return 0
    def long_last_arg(self):
        return self.flags & self.F_LONGLAST
    def first_arg_is_name(self):
        return self.flags & self.F_NAMEARG
    def __str__(self):
        return ""

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
    def __init__(self, state):
        RequestImplementation.__init__(self, state)
        self.flags = self.F_NAMEARG
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
    def __init__(self, state):
        RequestImplementation.__init__(self, state)
        self.flags = self.F_LONGLAST | self.F_NAMEARG
    def max_args(self):
        return 2
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) == 0:
            return
        elif len(args) == 1:
            args.append("")
        self.state.requests[args[0]] = tenorsax.sources.troff.stringlike.StringData(self.state, args[1])

class RequestImpl_ig(RequestImplementation):
    flags = 0
    def __init__(self, state):
        RequestImplementation.__init__(self, state)
    def max_args(self):
        return 1
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) == 0:
            self.state.set_copy_mode(None, "")
        else:
            self.state.set_copy_mode(None, args[0])

class NumberRegisterRequestImplementation(RequestImplementation):
    flags = 0
    def max_args(self):
        return 3
    @classmethod
    def _value(klass, cur, diff):
        try:
            if diff[0] in "+-":
                return cur + klass.func(diff)
            return klass.func(diff)
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
                inc = self.func(args[2])
        except:
            inc = 0
        curval = 0
        if name in self.state.numregs:
            # We don't use value() here because it will autoincrement.  We don't
            # want that.
            curval = self.state.numregs[name].val
        log("curval", curval)
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
    flags = RequestImplementation.F_NAMEARG
    def __init__(self, state):
        RequestImplementation.__init__(self, state)
    def max_args(self):
        return 1
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) < 1:
            return
        del self.state.requests[args[0]]

class RequestImpl_rn(RequestImplementation):
    flags = RequestImplementation.F_NAMEARG
    def __init__(self, state):
        RequestImplementation.__init__(self, state)
    def max_args(self):
        return 2
    def execute(self, callinfo):
        args = callinfo.args
        if len(args) < 2:
            return
        self.state.requests[args[1]] = self.state.requests[args[0]]
