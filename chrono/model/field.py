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

from chrono.model.position import Position
from chrono.model.direction import Direction

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

    def accepts_target(self, target):
        """Query if this field accepts another one as a target

        If a field accepts another one as target, it implies that a
        call to add_activation_target will generally be successful.

        Returns True if this field accepts the target as a field target.
        Returns False otherwise.  Fields that do not accepts targets in
        general will return False for all other fields.
        """
        if not self.is_activation_source:
            return False
        if not target.is_activation_target:
            return False
        return True

    def add_activation_target(self, target):
        if not self.is_activation_source:
            raise NotImplementedError("%s is not an activation source" % self.symbol)
        if not self.accepts_target(target):
            raise ValueError("%s does not accept %s as target" % (self.symbol, target.symbol))

        self._targets.add(target)
        target._add_source(self)

    def remove_activation_target(self, target):
        if not self.is_activation_source:
            raise NotImplementedError("%s is not an activation source" % self.symbol)
        # skip the accepts_target here; we permit removal of
        # "unaccepted" targets.  It shouldn't happen, but if it does
        # the resulting state is probably better than the initial one.

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

    def toggle_activation(self, level=None):
        """Toggles the activation of this field

        returns True if the state of the field changes (some don't
        change every time), or False otherwise.

        For sources, it will (automatically) dispatch a toggle_activation
        for each of its targets.  For targets the state is simply changed.
        """
        self._activated = not self._activated
        if self.is_activation_source:
            for t in self._targets:
                t.toggle_activation(level)
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
            self.toggle_activation(None)
            return True
        return False

    def copy(self):
        other = type(self)(self.symbol)
        other._sources = set()
        other._targets = set()
        other._activated = self._activated
        other._pos = self._pos
        return other

    def on_heartbeat(self):
        return False

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

    def toggle_activation(self, level=None):
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

    def toggle_activation(self, level=None):
        if self.activated:
            return False
        return super(OneTimeButton, self).toggle_activation(level)

    def reset_to_init_state(self):
        if self.activated:
            for target in self._targets:
                target.toggle_activation()
            self._activated = False
            return True
        return False

class OneTimePassage(Field):

    stepped_on = False

    def __init__(self, *args, **kwords):
        super(OneTimePassage, self).__init__(*args, **kwords)
        self._is_source = True

    def toggle_activation(self, level=None):
        self.stepped_on = True
        return False

    def reset_to_init_state(self):
        self.stepped_on = False
        if self.activated:
            self._activated = False
            return True
        return False


    def on_heartbeat(self):
        if self.activated:
            return False
        if self.stepped_on:
            self._activated = True
            return True
        return False

    @property
    def can_enter(self):
        return not self.activated

class Pallet(Button):

    def toggle_activation(self, level):
        if not level is None and level.get_crate_at(self.position) is not None:
            #doesn't work crates haven't been moved at this point
            return super(Pallet, self).toggle_activation(level)
        activated = False
        return False

class StartLocation(Field):
    pass

class GoalLocation(Field):
    pass

_SYMBOL2FIELD = {
    '+': Wall,
    '-': Gate,
    '_': Gate,
    ' ': Field,
    'c': Field, # crates are always on top of a "field"
    'b': Button,
#    'B': <reserved>
    'o': OneTimeButton,
    'p': OneTimePassage,
    'P': Pallet,
    'S': StartLocation,
    'G': GoalLocation,
}

def parse_field(symbol):
    constructor = _SYMBOL2FIELD.get(symbol, None)
    if constructor:
        return constructor(symbol)
    raise IOError("Unknown symbol %s" % symbol)
