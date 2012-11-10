"""
Taken (with modification) from:
  https://bitbucket.org/thesheep/qq/src/1090d7e5537f/qq.py?at=default

@copyright: 2008, 2009 Radomir Dopieralski <qq@sheep.art.pl>
            2012, Niels Thykier <niels@thykier.net>
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
                     Shadow, MAP_TILE_WIDTH, MAP_TILE_HEIGHT,
                     GATE_CLOSED, GATE_OPEN)
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

class ScoreTracker(pygame.sprite.Sprite):

    def __init__(self):
        super(ScoreTracker, self).__init__()
        self.font = pygame.font.Font(None, 20)
        self._score = None
        self.depth = 0
        self.reset_score()
        self.rect = self.image.get_rect()
        self.gpos_tf = (10, 300)


    @property
    def score(self):
        return self._score

    @score.setter
    def score(self, nscore):
        if self._score != nscore:
            self._score = nscore
            msg = "Score: %d, Turn %d, Clone: %d" % nscore
            self.image = self.font.render(msg, 0, (0x00, 0x00, 0x00), (0xff, 0xff, 0xff))

    @property
    def gpos_tf(self):
        """Check the current position of the sprite on the map."""

        return self.rect.topleft

    @gpos_tf.setter
    def gpos_tf(self, pos):
        """Set the position and depth of the sprite on the map."""

        self.rect.topleft = pos
        self.depth = self.rect.midbottom[1]


    def reset_score(self):
        self.score = (0, 1, 1)

    def update_score(self, lvl):
        # turn is 0-index'ed, but it is better presented as 1-index'ed.
        self.score = (lvl.score, lvl.turn + 1, lvl.number_of_clones)

    def update(self, *args):
        for frame in range(4):
            yield None
            yield None

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
        self._sprite_cache = TileCache(32, 32)
        self._map_cache = TileCache(MAP_TILE_WIDTH, MAP_TILE_HEIGHT)
        self._clones = {}
        self._gates = {}
        self._score = ScoreTracker()
        self.use_level(log_level)
        self._action2handler = {
            'move-up': self.log_level.perform_move,
            'move-down': self.log_level.perform_move,
            'move-left': self.log_level.perform_move,
            'move-right': self.log_level.perform_move,
            'skip-turn': self.log_level.perform_move,
            'enter-time-machine': self.log_level.perform_move,
            'quit-game': self._quit,
        }
        self._event_handler = {
            'move-up': functools.partial(self._move, Direction.NORTH),
            'move-down': functools.partial(self._move, Direction.SOUTH),
            'move-left': functools.partial(self._move, Direction.WEST),
            'move-right': functools.partial(self._move, Direction.EAST),
            'player-clone': self._player_clone,
            'field-acitvated': self._field_state_change,
            'field-deacitvated': self._field_state_change,
            'game-complete': self._game_complete,
            'end-of-turn': self._end_of_turn,
        }
        self._controls = DEFAULT_CONTROLS


    @property
    def controls(self):
        return self._controls.copy()

    @controls.setter
    def controls(self, cmap):
        self._controls = cmap.copy()

    def use_level(self, log_level):
        """Set the level as the current one."""

        self.shadows = pygame.sprite.RenderUpdates()
        self.sprites = SortedUpdates()
        self.overlays = pygame.sprite.RenderUpdates()
        self.log_level = log_level
        self._clones = {}
        self._gates = {}
        self.level = VisualLevel(log_level, map_cache=self._map_cache,
                                 tileset=self._tileset)

        def level_event_handler(event):
            pygame.event.post(pygame.event.Event(pg.USEREVENT, code=lambda:event))

        log_level.add_event_listener(level_event_handler)

        # Populate the game with the level's objects
        if 1:
            sprite = Sprite(log_level.goal_location.position, self._sprite_cache['house'])
            self.goal = sprite
            self.sprites.add(sprite)

        # Render the level map
        self.background, overlays = self.level.render()

        for field in log_level.iter_fields():
            # Use map-cache here for gates and buttons
            sprite = None
            if field.symbol == '-' or field.symbol == '_':
                sprite = Sprite(field.position, self._map_cache['gate'], c_depth=-1)
                self._gates[field.position] = sprite
                if field.symbol == '-':
                    sprite.state = GATE_CLOSED
            if field.symbol == 'b':
                sprite = Sprite(field.position, self._map_cache['button'], c_depth=-1)
            if sprite:
                self.sprites.add(sprite)

        if 1:
            # Highlight the start location
            image = pygame.Surface((MAP_TILE_WIDTH, MAP_TILE_HEIGHT))
            image.fill(pygame.Color("blue"))
            image.set_alpha(0x80)
            s = Sprite(log_level.start_location.position, ((image,),))
            self.sprites.add(s)

        # Add the overlays for the level map
        for (x, y), image in overlays.iteritems():
            overlay = pygame.sprite.Sprite(self.overlays)
            overlay.image = image
            overlay.rect = image.get_rect().move(Position(x*MAP_TILE_WIDTH,(y-1) * MAP_TILE_HEIGHT))


        self._score.reset_score()
        self.sprites.add(self._score)
        log_level.start()

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
        #else:
        #    for k in itertools.ifilter(pressed, self._controls):
        #        action = self._controls[k]
        #        self._action2handler[action](action)
        #        break

        self.pressed_key = None

    def _move(self, d, event):
        """Start walking in specified direction."""

        player = self._clones[event.source]

        if d == Direction.NO_ACT or not event.success:
            player.animation = player.do_nothing_animation()
            return
        pos = player.pos
        target = pos.dir_pos(d)
        player.direction = d
        player.animation = player.walk_animation()
        if target == self.log_level.goal_location.position:
            self.goal.kill()

    def _field_state_change(self, event):
        src_pos = event.source.position
        if src_pos in self._gates:
            nstate = GATE_CLOSED
            if event.source.can_enter:
                nstate = GATE_OPEN
            self._gates[src_pos].state = nstate

    def _player_clone(self, event):
        self._score.update_score(self.log_level)
        sprite = PlayerSprite(event.source, self._sprite_cache['player'])
        self._clones[event.source] = sprite
        self.sprites.add(sprite)
        self.shadows.add(Shadow(sprite, self._sprite_cache["shadow"][0][0]))

    def _quit(self, _):
        self.game_over = True

    def _end_of_turn(self, _):
        self._score.update_score(self.log_level)

    def _game_complete(self, _):
        self._score.update_score(self.log_level)
        print "Your score is: %d" % self.log_level.score

    def main(self):
        """Run the main loop."""

        clock = pygame.time.Clock()
        # Draw the whole screen initially
        self.screen.blit(self.background, (0, 0))
        self.overlays.draw(self.screen)
        pygame.display.flip()
        has_animation = lambda x: self._clones[x].animation is not None

        # The main game loop
        while not self.game_over:
            # Don't clear shadows and overlays, only sprites.
            self.sprites.clear(self.screen, self.background)
            self.sprites.update()
            # If the player's animation is finished, check for keypresses
            if not any(itertools.ifilter(has_animation, self._clones)):
                self.control()
                for k in self._clones:
                    self._clones[k].update()
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

