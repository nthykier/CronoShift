import collections
from operator import attrgetter

_P = collections.namedtuple('Position', ['x', 'y'])

class Position(_P):

    def __str__(self):
        # This looks better...
        return "(%d, %d)" % (self.x, self.y)

class Field(object):
    def __init__(self, symbol):
        self._symbol = symbol
        self._is_source = False
        self._is_target = False
        self._activated = False
        self._targets = set()
        self._sources = set()
        self._pos = None


    @property
    def position(self):
        return self._pos

    @property
    def symbol(self):
        return self._symbol

    @property
    def activated(self):
        return self._activated

    @property
    def can_enter(self):
        return True

    @property
    def is_activation_source(self):
        return self._is_source

    @property
    def is_activation_target(self):
        return self._is_target

    def add_activation_target(self, target):
        if not self.is_activation_source:
            raise NotImplementedError("%s is not an activation source" % self.symbol)
        if not target.is_activation_target:
            raise ValueError("%s is not an activation target" % self.symbol)

        self._targets.add(target)
        target._add_source(self)

    def _add_source(self, source):
        self._sources.add(source)

    def _set_position(self, pos):
        self._pos = pos

    def iter_activation_targets(self):
        # Technically we could just do return sorted(...), but this
        # way we force it to be an iterator and require the "iter()"
        # call.
        return (x for x in sorted(self._targets, key=attrgetter("position")))

    def iter_activation_sources(self):
        # Technically we could just do return sorted(...), but this
        # way we force it to be an iterator and require the "iter()"
        # call.
        return (x for x in sorted(self._sources, key=attrgetter("position")))

    def toogle_activation(self, newstate):
        pass

    def on_enter(self, obj):
        pass

    def activate(self):
        if not self._activated:
            self._activated = True
            self.toogle_activation(True)

    def deactivate(self):
        if self._activated:
            self._activated = False
            self.toogle_activation(False)

class Wall(Field):

    def __init__(self, symbol):
        super(Wall, self).__init__(symbol)

    @property
    def can_enter(self):
        return False

class Gate(Field):

    def __init__(self, symbol):
        super(Gate, self).__init__(symbol)
        self.closed = True
        self._is_target = True
        if symbol == "_":
            self.closed = False

    def toogle_activation(self, _):
        # invert our state
        self.closed = not self.closed

    @property
    def can_enter(self):
        return not self.closed

    @property
    def is_activation_target(self):
        return True

class Button(Field):

    def __init__(self, symbol):
        super(Button, self).__init__(symbol)
        self._is_source = True

    def toogle_activation(self, newstate):
        for target in self._targets:
            if newstate:
                target.activate()
            else:
                target.deactivate()

class StartLocation(Field):

    def __init__(self, symbol):
        super(StartLocation, self).__init__(symbol)

class GoalLocation(Field):

    def __init__(self, symbol):
        super(GoalLocation, self).__init__(symbol)

def parse_field(symbol):
    if symbol == "+":
        return Wall(symbol)
    if symbol == "-" or symbol == "_":
        return Gate(symbol)
    if symbol == " " or symbol == "c":
        # crates are always ontop of a "field"
        return Field(symbol)
    if symbol == "b" or symbol == "B":
        return Button(symbol)
    if symbol == "S":
        return StartLocation(symbol)
    if symbol == "G":
        return GoalLocation(symbol)
    raise IOError("Unknown symbol %s" % symbol)
