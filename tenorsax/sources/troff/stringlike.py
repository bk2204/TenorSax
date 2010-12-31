class StringNamespacedData:
    def __init__(self, state):
        self.state = state
    def max_args(self):
        return 0
    def preparse(self):
        pass
    def postparse(self):
        pass
    def long_last_arg(self):
        return False
    def first_arg_is_name(self):
        return False

class StringData(StringNamespacedData):
    """Represents a string in the request table.
    
    Because an object of this type must be present in the request table (because
    otherwise there would be no way to store the data), the special call method
    is implemented so that it looks like a normal constructor for a request.
    """
    def __init__(self, state, data):
        StringNamespacedData.__init__(self, state)
        self.data = data
    def __call__(self, state):
        self.state = state
        return self
    def execute(self, callinfo):
        self.state.ch.characters(str(self.data))
    def __str__(self):
        return str(self.data)

class MacroData(StringNamespacedData):
    """Represents a macro in the request table.
   
    This is implemented very similarly to StringData, and most of the same
    comments apply.
    """
    def __init__(self, state, data):
        StringNamespacedData.__init__(self, state)
        self.data = data
    def __call__(self, state):
        self.state = state
        return self
    def execute(self, callinfo):
        return (str(self.data), callinfo)
    def __str__(self):
        return str(self.data)
