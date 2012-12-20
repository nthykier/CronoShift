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
from chrono.model._pos import _Pos

class Direction(object):

    NORTH  = 0
    EAST   = 1
    SOUTH  = 2
    WEST   = 3
    NO_ACT = 4

    # (0, 0) is NW, (Width, Height) is SE
    NORTH_DIFF  = _Pos(0, -1)
    EAST_DIFF   = _Pos(1, 0)
    SOUTH_DIFF  = _Pos(0, 1)
    WEST_DIFF   = _Pos(-1, 0)
    NO_ACT_DIFF = _Pos(0, 0)

    _DIR_DIFF = (
        NORTH_DIFF,
        EAST_DIFF,
        SOUTH_DIFF,
        WEST_DIFF,
        NO_ACT_DIFF,
    )

    _ACT2DIR = {
        'N': NORTH,
        'E': EAST,
        'S': SOUTH,
        'W': WEST,
        'H': NO_ACT,
        'move-up': NORTH,
        'move-right': EAST,
        'move-down': SOUTH,
        'move-left': WEST,
    }
    @staticmethod
    def new_pos(pos, direction):
        return pos + Direction.dir_update(direction)

    @staticmethod
    def dir_update(direction):
        return Direction._DIR_DIFF[direction]

    @staticmethod
    def act2dir(act):
        return Direction._ACT2DIR[act]

    @staticmethod
    def act_update(act):
        return dir_update(act2dir(act))
