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

import functools
import itertools
import pygame
import pygame.locals as pg

from direction import Direction
from field import Position
from sprites import (VisualLevel, SortedUpdates, Sprite, PlayerSprite,
                     Shadow, MAP_TILE_WIDTH, MAP_TILE_HEIGHT)
from tile_cache import TileCache

DEFAULT_CONTROLS = {
    pg.K_UP: 'move-up',
    pg.K_w: 'move-up',

    pg.K_DOWN: 'move-down',
    pg.K_s: 'move-down',

    pg.K_RIGHT: 'move-right',
    pg.K_d: 'move-right',

    pg.K_LEFT: 'move-left',
    pg.K_a: 'move-left',

    pg.K_SPACE: 'skip-turn',
    pg.K_RETURN: 'enter-time-machine',

    pg.K_ESCAPE: 'quit-game',
}

class Game(object):
    """The main game object."""

    def __init__(self, log_level):
        self.screen = pygame.display.get_surface()
        self.pressed_key = None
        self.game_over = False
        self.shadows = pygame.sprite.RenderUpdates()
        self.sprites = SortedUpdates()
        self.overlays = pygame.sprite.RenderUpdates()
        self._tileset = "tileset"
        self._tile_cache = TileCache(32, 32)
        self.use_level(log_level)
        self._action2handler = {
            'move-up': self._game_action,
            'move-down': self._game_action,
            'move-left': self._game_action,
            'move-right': self._game_action,
            'skip-turn': self._game_action,
            'enter-time-machine': self._game_action,
            'quit-game': self._quit
        }
        self._event_handler = {
            'move-up': functools.partial(self._move, Direction.NORTH),
            'move-down': functools.partial(self._move, Direction.SOUTH),
            'move-left': functools.partial(self._move, Direction.WEST),
            'move-right': functools.partial(self._move, Direction.EAST)
        }
        self._controls = DEFAULT_CONTROLS


    @property
    def controls(self):
        return self._controls.copy()

    def set_controls(self, cmap):
        self._controls = cmap

    def use_level(self, log_level):
        """Set the level as the current one."""

        self.shadows = pygame.sprite.RenderUpdates()
        self.sprites = SortedUpdates()
        self.overlays = pygame.sprite.RenderUpdates()
        self.log_level = log_level
        self.level = VisualLevel(log_level, tile_cache=self._tile_cache,
                                 tileset=self._tileset)

        def event_handler(event):
            pygame.event.post(pygame.event.Event(pg.USEREVENT, code=lambda:event))

        log_level.add_event_listener(event_handler)

        # Populate the game with the level's objects
        for field in log_level.iter_fields():
            sprite = None
            shadow = True
            if field.symbol == 'S':
                sprite = PlayerSprite(field, self._tile_cache['player'])
                self.player = sprite
                spos_shadow = Sprite(field.position, self._tile_cache["shadow"],
                                     correction=(0, MAP_TILE_HEIGHT/4))
                self.shadows.add(spos_shadow)
            if field.symbol == 'G':
                sprite = Sprite(field.position, self._tile_cache['house'])
                self.goal = sprite
                shadow = False
            if sprite:
                self.sprites.add(sprite)
                if shadow:
                    self.shadows.add(Shadow(sprite, self._tile_cache["shadow"][0][0]))

        # Render the level map
        self.background, overlays = self.level.render()

        if 1:
            image = pygame.Surface((MAP_TILE_WIDTH, MAP_TILE_HEIGHT))
            image.fill(pygame.Color("red"))
            image.set_alpha(0x80)
            c = image.copy()
            c.set_alpha(0x00)
            s = Sprite(Position(2,2), ((image, c),), correction=(0, MAP_TILE_HEIGHT/4))
            self.sprites.add(s)

        # Add the overlays for the level map
        for (x, y), image in overlays.iteritems():
            overlay = pygame.sprite.Sprite(self.overlays)
            overlay.image = image
            overlay.rect = image.get_rect().move(Position(x*MAP_TILE_WIDTH,(y-1) * MAP_TILE_HEIGHT))

    def control(self):
        """Handle the controls of the game."""

        keys = pygame.key.get_pressed()

        def pressed(key):
            """Check if the specified key is pressed."""

            return self.pressed_key == key or keys[key]

        if self.pressed_key is not None:
            action = self._controls.get(self.pressed_key, None)
            if action:
                self._action2handler[action](action)
        else:
            for k in itertools.ifilter(pressed, self._controls):
                action = self._controls[k]
                self._action2handler[action](action)
                break

        self.pressed_key = None

    def _game_action(self, action):
        self.log_level.perform_move(action)

    def _move(self, d, event):
        """Start walking in specified direction."""

        if d == Direction.NO_ACT or not event.success:
            self.player.animation = self.player.do_nothing_animation()
            return
        pos = self.player.pos
        target = pos.dir_pos(d)
        if self.log_level.can_enter(pos, target):
            self.player.direction = d
            self.player.animation = self.player.walk_animation()
            if target == self.log_level.goal_location.position:
                self.goal.kill()


    def _quit(self, _):
        self.game_over = True

    def main(self):
        """Run the main loop."""

        clock = pygame.time.Clock()
        # Draw the whole screen initially
        self.screen.blit(self.background, (0, 0))
        self.overlays.draw(self.screen)
        pygame.display.flip()

        # The main game loop
        while not self.game_over:
            # Don't clear shadows and overlays, only sprites.
            self.sprites.clear(self.screen, self.background)
            self.sprites.update()
            # If the player's animation is finished, check for keypresses
            if self.player.animation is None:
                self.control()
                self.player.update()
            self.shadows.update()
            # Don't add shadows to dirty rectangles, as they already fit inside
            # sprite rectangles.
            self.shadows.draw(self.screen)
            dirty = self.sprites.draw(self.screen)
            # Don't add ovelays to dirty rectangles, only the places where
            # sprites are need to be updated, and those are already dirty.
            self.overlays.draw(self.screen)
            # Update the dirty areas of the screen
            pygame.display.update(dirty)
            # Wait for one tick of the game clock
            clock.tick(15)
            # Process pygame events
            for event in pygame.event.get():
                if event.type == pg.QUIT:
                    self.game_over = True
                elif event.type == pg.KEYDOWN:
                    self.pressed_key = event.key
                elif event.type == pg.USEREVENT:
                    e = event.code()
                    print "Event: %s" % e.event_type
                    if e.event_type not in self._event_handler:
                        continue
                    self._event_handler[e.event_type](e)

