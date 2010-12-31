from tenorsax.sources.troff import log

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
        return self.val
    def __call__(self, state):
        self.state = state
        return self
    def __str__(self):
        return str(self.val)

class IntegerNumberRegister(NumberRegister):
    func = staticmethod(int)

class FloatNumberRegister(NumberRegister):
    func = staticmethod(float)
