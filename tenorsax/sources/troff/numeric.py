import decimal

from tenorsax.util import log

class NumberRegister:
    def __init__(self, state, name, val, increment, fmt):
        self.state = state
        self.name = name
        self.val = self.func(val)
        self.inc = self.func(increment)
        self.fmt = fmt
    def increment(self):
        self.val += self.inc
    def decrement(self):
        self.val -= self.inc
    def value(self, inc=0):
        if inc == -1:
            self.decrement()
        elif inc == 1:
            self.increment()
        return str(self)
    def __call__(self, state):
        self.state = state
        return self
    def __str__(self):
        return str(self.val)

class IntegerNumberRegister(NumberRegister):
    func = staticmethod(int)

class FloatNumberRegister(NumberRegister):
    func = staticmethod(decimal.Decimal)
    def __str__(self):
        if self.val.to_integral_value() == self.val:
            # We have no digits after the decimal point, so add a trailing .0.
            # We could also do this with a with statement and
            # decimal.localcontext().
            return str(self.val) + ".0"
        return str(self.val)

class SpecialNumberRegister(NumberRegister):
    def __init__(self, state, name, callback):
        self.state = state
        self.name = name
        self.callback = callback
    def increment(self):
        pass
    def decrement(self):
        pass
    def value(self, inc=0):
        return str(self)
    def __call__(self, state):
        self.state = state
        return self
    def __str__(self):
        return str(self.callback(self))

def initialize_registers(state):
    regs = {}
    regs[".$"] = SpecialNumberRegister(state, ".$", lambda x:
            len(x.state.macroargs[-1])-1 if len(x.state.macroargs) else 0)
    return regs
