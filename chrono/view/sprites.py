"""
Taken (with modification) from:
  https://bitbucket.org/thesheep/qq/src/1090d7e5537f/qq.py?at=default

@copyright: 2008, 2009 Radomir Dopieralski <qq@sheep.art.pl>
@license: BSD
                           BSD LICENSE

Copyright (c) 2008, 2009, Radomir Dopieralski
All rights reserved. 

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

import pygame
import operator
import functools

from chrono.model.position import Position
from chrono.model.direction import Direction
from chrono.view.translation import lpos2gpos, gpos2lpos

class SortedUpdates(pygame.sprite.RenderUpdates):
    """A sprite group that sorts them by depth."""

    def sprites(self):
        """The list of sprites in the group, sorted by depth."""

        return sorted(self.spritedict.keys(), key=operator.attrgetter("depth"))

class Shadow(pygame.sprite.Sprite):
    """Sprite for shadows."""

    def __init__(self, owner, sprite, pos=None):
        pygame.sprite.Sprite.__init__(self)
        self.image = sprite.copy()
        self.image.set_alpha(64)
        self.rect = self.image.get_rect()
        self.owner = owner
        if pos:
            self.rect.midbottom = lpos2gpos(pos)

    def update(self, *args):
        """Make the shadow follow its owner."""

        if self.owner:
            self.rect.midbottom = self.owner.rect.midbottom

class Sprite(pygame.sprite.Sprite):
    """Sprite for animated items and base class for Player."""

    def __init__(self, pos, frames, c_pos=None, c_depth=None):
        super(Sprite, self).__init__()
        self.frames = frames
        self._c_pos = c_pos if c_pos else Position(0, 0)
        self._c_depth = c_depth if c_depth else 0
        self.image = self.frames[0][0]
        self.rect = self.image.get_rect()
        self.animation = self.stand_animation()
        self.pos = pos
        self._state = 0

    @property
    def pos(self):
        """Check the current position of the sprite on the map."""

        return gpos2lpos(self.rect.midbottom, self._c_pos)

    @pos.setter
    def pos(self, pos):
        """Set the position and depth of the sprite on the map."""

        self.rect.midbottom = lpos2gpos(pos, self._c_pos)
        self.depth = self.rect.midbottom[1] + self._c_depth

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        self.image = self.frames[new_state][0]
        self._state = new_state

    def move(self, pos):
        """Change the position of the sprite on screen."""

        self.rect.move_ip(pos[0], pos[1])
        self.depth = self.rect.midbottom[1]

    def stand_animation(self):
        """The default animation."""

        while True:
            # Change to next frame every two ticks
            for frame in self.frames[self.state]:
                self.image = frame
                yield None
                yield None

    def update(self, *args):
        """Run the current animation."""

        self.animation.next()

class TimeSprite(Sprite):
    """Display the clock"""

    def __init__(self, *args, **kwords):
        super(TimeSprite,self).__init__(*args, **kwords)
        self.animation = None

    def time_jump_animation(self):
        for frame in range(len(self.frames[0])):
            self.image = self.frames[0][frame]
            yield None
            yield None

    def update(self, *args):
        """Run the current animation."""

        if self.animation:
            try:
                self.animation.next()
            except StopIteration:
                self.animation = None
        else:
            self.kill()


class MoveableSprite(Sprite):
    """ Display and animate the moveable objects."""
    def __init__(self, pos, frames, c_pos=None, c_depth=None):
        Sprite.__init__(self, pos, frames, c_pos=c_pos, c_depth=c_depth)
        self.direction = 0
        self.animation = None

    def do_nothing_animation(self):
        """Fake animation for timing purposes"""

        # This animation is hardcoded for 4 frames and 16x24 map tiles
        for frame in range(4):
            yield None
            yield None

    def walk_animation(self):
        """Animation for the player walking."""

        # This animation is hardcoded for 4 frames and 16x24 map tiles
        d = self.direction
        dpos = Direction.dir_update(d)
        for frame in range(4):
            if d < len(self.frames) and frame < len(self.frames[d]):
                self.image = self.frames[d][frame]
            else:
                self.image = self.frames[0][0]
            yield None
            self.move(Position(3*dpos.x, 2*dpos.y))
            yield None
            self.move(Position(3*dpos.x, 2*dpos.y))

    def update(self, *args):
        """Run the current animation or just stand there if no animation set."""

        if self.animation is None:
            if self.direction < len(self.frames):
                self.image = self.frames[self.direction][0]
            else:
                self.image = self.frames[0][0]
        else:
            try:
                self.animation.next()
            except StopIteration:
                self.animation = None

class PlayerSprite(MoveableSprite):
    """ Display and animate the player character."""

    def __init__(self, player, frames):
        MoveableSprite.__init__(self, player.position, frames)
        self.direction = Direction.EAST
        self.image = self.frames[self.direction][0]
