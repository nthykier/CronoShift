"""
@copyright: 2012, Niels Thykier <niels@thykier.net>
@license:
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

 * Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.

 * Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in
   the documentation and/or other materials provided with the
   distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import operator

from chrono.model.position import Pos
from chrono.model.direction import Direction

class Position(Pos):

    def dir_pos(self, direction):
        return self + Direction.dir_update(direction)

class Field(object):
    def __init__(self, symbol, position=None):
        self._symbol = symbol
        self._is_source = False
        self._is_target = False
        self._activated = False
        self._targets = set()
        self._sources = set()
        self._pos = position
        self._init_state = False

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

    @property
    def x(self):
        return self._pos.x

    @property
    def y(self):
        return self._pos.y

    def add_activation_target(self, target):
        if not self.is_activation_source:
            raise NotImplementedError("%s is not an activation source" % self.symbol)
        if not target.is_activation_target:
            raise ValueError("%s is not an activation target" % self.symbol)

        self._targets.add(target)
        target._add_source(self)

    def remove_activation_target(self, target):
        if not self.is_activation_source:
            raise NotImplementedError("%s is not an activation source" % self.symbol)
        if not target.is_activation_target:
            raise ValueError("%s is not an activation target" % self.symbol)

        self._targets.remove(target)
        target._remove_source(self)

    def has_activation_target(self, target):
        return target in self._targets

    def _add_source(self, source):
        self._sources.add(source)

    def _remove_source(self, source):
        self._sources.remove(source)

    def _set_position(self, pos):
        self._pos = pos

    def iter_activation_targets(self):
        # Technically we could just do return sorted(...), but this
        # way we force it to be an iterator and require the "iter()"
        # call.
        return (x for x in sorted(self._targets, key=operator.attrgetter("position")))

    def iter_activation_sources(self):
        # Technically we could just do return sorted(...), but this
        # way we force it to be an iterator and require the "iter()"
        # call.
        return (x for x in sorted(self._sources, key=operator.attrgetter("position")))

    @property
    def is_wall(self):
        return False

    def toggle_activation(self):
        """Toggles the activation of this field

        returns True if the state of the field changes (some don't
        change every time), or False otherwise.

        For sources, it will (automatically) dispatch a toggle_activation
        for each of its targets.  For targets the state is simply changed.
        """
        self._activated = not self._activated
        if self.is_activation_source:
            for t in self._targets:
                t.toggle_activation()
        return True

    def reset_to_init_state(self):
        """[source-only] Called on time-jump or level/clone reset

        This is called (instead of toggle_activation) when the time-jump
        occurs and must reset the field to its original state.  If this
        changes the state of the field, it must return True.  Otherwise
        it must return False

        Default will invoke toggle_activation if activated != init_state.
        """

        if self._activated != self._init_state:
            self.toggle_activation()
            return True
        return False

    def copy(self):
        other = type(self)(self.symbol)
        other._sources = set()
        other._targets = set()
        other._activated = self._activated
        other._pos = self._pos
        return other

class Wall(Field):

    @property
    def is_wall(self):
        return True

    @property
    def can_enter(self):
        return False

class Gate(Field):
    """gate

    If activated, it is closed.  If deactivated, open.  (Think of it
    as a force field)"
    """

    def __init__(self, *args, **kwords):
        super(Gate, self).__init__(*args, **kwords)
        self._is_target = True
        if self.symbol == "-":
            self._init_state = self._activated = True

    def toggle_activation(self):
        self._activated = not self._activated
        if self._activated:
            self._symbol = '-'
        else:
            self._symbol = '_'
        return True

    @property
    def can_enter(self):
        return not self._activated

class Button(Field):

    def __init__(self, *args, **kwords):
        super(Button, self).__init__(*args, **kwords)
        self._is_source = True

class OneTimeButton(Button):

    def toggle_activation(self):
        if self.activated:
            return False
        return super(OneTimeButton, self).toggle_activation()

    def reset_to_init_state(self):
        if self.activated:
            for target in self._targets:
                target.toggle_activation()
            self._activated = False
            return True
        return False

class StartLocation(Field):
    pass

class GoalLocation(Field):
    pass

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
    if symbol == "o":
        return OneTimeButton(symbol)
    if symbol == "S":
        return StartLocation(symbol)
    if symbol == "G":
        return GoalLocation(symbol)
    raise IOError("Unknown symbol %s" % symbol)
