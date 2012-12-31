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

from chrono.model.direction import Direction
from chrono.model.position import Position

class Moveable(object):

    def __init__(self, position, is_player, is_crate):
        self._is_player = is_player
        self._is_box = is_crate
        self.position = position
        self._target = None

    def move_direction(self, direction):
        self._position = self._position.dir_pos(direction)

    @property
    def is_crate(self):
        return self._is_crate

    @property
    def is_clone(self):
        return self._is_player
        
    @property
    def target(self):
        return self._target
    
    @target.setter
    def target(self,value):
        self._target = value

class PlayerClone(Moveable):

    def __init__(self, position, actions):
        super(PlayerClone, self).__init__(position, True, False)
        self._actions = actions

    def __len__(self):
        return len(self._actions)

    def __getitem__(self, i):
        return self._actions[i]

    def __iter__(self):
        return iter(self._actions)

class Crate(Moveable):

    def __init__(self,position):
        super(Crate, self).__init__(position, False, True)
