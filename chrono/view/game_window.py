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
import Queue

from pgu import gui

from chrono.model.direction import Direction
from chrono.model.field import Position

from chrono.view.sprites import (
        make_background, SortedUpdates, Sprite, PlayerSprite,
        Shadow, MAP_TILE_WIDTH, MAP_TILE_HEIGHT,
        GATE_CLOSED, GATE_OPEN, MoveableSprite, gpos2lpos
    )
from chrono.view.tile_cache import TileCache

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

    pg.K_F2: 'print-actions',
}

class GameWindow(gui.Widget):
    """The main game object."""

    def __init__(self, **params):
        params['width'] = 300
        params['height'] = 300
        params['focusable'] = True
        super(GameWindow, self).__init__(**params)
        self.surface = pygame.Surface((300, 300))
        self.surface.fill((0, 0, 0))
        self.shadows = pygame.sprite.RenderUpdates()
        self.sprites = SortedUpdates()
        self.overlays = pygame.sprite.RenderUpdates()
        self._tileset = "tileset"
        self._sprite_cache = TileCache(32, 32)
        self._map_cache = TileCache(MAP_TILE_WIDTH, MAP_TILE_HEIGHT)
        self._clones = {}
        self._gates = {}
        self._crates = {}
        self.mhilight = None
        self.ohilights = []
        self.game_over = False
        self.active_animation = False
        self._gevent_queue = Queue.Queue()
        self.level = None
        self._action2handler = {
            'move-up': self._perform_move,
            'move-down': self._perform_move,
            'move-left': self._perform_move,
            'move-right': self._perform_move,
            'skip-turn': self._perform_move,
            'enter-time-machine': self._perform_move,
            'print-actions': self._print_actions,
        }
        self._event_handler = {
            'move-up': functools.partial(self._move, Direction.NORTH),
            'move-down': functools.partial(self._move, Direction.SOUTH),
            'move-left': functools.partial(self._move, Direction.WEST),
            'move-right': functools.partial(self._move, Direction.EAST),
            'player-clone': self._player_clone,
            'field-acitvated': self._field_state_change,
            'field-deacitvated': self._field_state_change,
            'time-paradox': self._time_paradox,
            'game-complete': self._game_complete,
            'end-of-turn': self._end_of_turn,
            'goal-obtained': lambda *x: self.goal.kill(),
            'reset-crate': self._reset_crate,
        }
        self._controls = DEFAULT_CONTROLS

    @property
    def controls(self):
        return self._controls.copy()

    @controls.setter
    def controls(self, cmap):
        self._controls = cmap.copy()

    def use_level(self, level):
        """Set the level as the current one."""

        self.shadows = pygame.sprite.RenderUpdates()
        self.sprites = SortedUpdates()
        self.overlays = pygame.sprite.RenderUpdates()
        self.level = level
        self._clones = {}
        self._gates = {}

        level.add_event_listener(self._gevent_queue.put)

        # Populate the game with the level's objects
        if 1:
            sprite = Sprite(level.goal_location.position, self._sprite_cache['house'])
            self.goal = sprite
            self.sprites.add(sprite)

        # Render the level map
        background, overlays = make_background(level,
                                               map_cache=self._map_cache,
                                               tileset=self._tileset)
        self.surface.blit(background, (0,0))

        for field in level.iter_fields():
            # Crates looks best in 32x32, gates and buttons in 24x16
            #   - if its "on top of" a field 32x32 usually looks best.
            #   - if it is (like) a field, 24x16 is usually better
            # - use sprite_cache and map_cache accordingly.
            sprite = None
            crate = level.get_crate_at(field.position)
            if crate:
                c_sprite = MoveableSprite(field.position, self._sprite_cache['crate'], c_depth=1)
                self._crates[crate] = c_sprite
                self.sprites.add(c_sprite)
            if field.symbol == '-' or field.symbol == '_':
                sprite = Sprite(field.position, self._map_cache['gate'], c_depth=-2)
                self._gates[field.position] = sprite
                if field.symbol == '-':
                    sprite.state = GATE_CLOSED
            if field.symbol == 'b':
                sprite = Sprite(field.position, self._map_cache['button'], c_depth=-2)
            if sprite:
                self.sprites.add(sprite)

        if 1:
            # Highlight the start location
            image = pygame.Surface((MAP_TILE_WIDTH, MAP_TILE_HEIGHT))
            image.fill(pygame.Color("blue"))
            image.set_alpha(0x80)
            self.sprites.add(Sprite(level.start_location.position, ((image,),), c_depth=-1))
            mhilight = pygame.Surface((MAP_TILE_WIDTH, MAP_TILE_HEIGHT))
            mhilight.fill(pygame.Color("red"))
            mhilight.set_alpha(0x80)
            s = Sprite(level.start_location.position, ((mhilight,),), c_depth=-1)
            self.sprites.add(s)
            self.mhilight = s

        # Add the overlays for the level map
        for (x, y), image in overlays.iteritems():
            overlay = pygame.sprite.Sprite(self.overlays)
            overlay.image = image
            overlay.rect = image.get_rect().move(Position(x*MAP_TILE_WIDTH,(y-1) * MAP_TILE_HEIGHT))


        level.start()
        self.repaint()

    def event(self, e):
        if not self.level:
            return
        if e.type == pg.KEYDOWN:
            if not self.active_animation:
                self.pressed_key = e.key
                action = self._controls.get(e.key, None)
                if action:
                    self._action2handler[action](action)
                    return True
        elif e.type == pg.MOUSEMOTION:
            corr = (self.rect.x - MAP_TILE_WIDTH/2,
                    self.rect.y - MAP_TILE_HEIGHT)
            mpos = pygame.mouse.get_pos()
            lpos = gpos2lpos(mpos, c=corr)
            self._handle_mouse(lpos)
            return True

    def _move(self, d, event):
        """Start walking in specified direction."""

        actor = None
        if event.source in self._crates:
            actor = self._crates[event.source]
        else:
            actor = self._clones[event.source]

        if d == Direction.NO_ACT or not event.success:
            actor.animation = actor.do_nothing_animation()
            return
        pos = actor.pos
        target = pos.dir_pos(d)
        actor.direction = d
        actor.animation = actor.walk_animation()
        self.repaint()

    def _field_state_change(self, event):
        src_pos = event.source.position
        if src_pos in self._gates:
            nstate = GATE_CLOSED
            if event.source.can_enter:
                nstate = GATE_OPEN
            self._gates[src_pos].state = nstate
            self.repaint()

    def _player_clone(self, event):
        sprite = PlayerSprite(event.source, self._sprite_cache['player'])
        self._clones[event.source] = sprite
        self.sprites.add(sprite)
        self.shadows.add(Shadow(sprite, self._sprite_cache["shadow"][0][0]))
        self.repaint()

    def _print_actions(self, _):
        def _action2sf(container):
            actions = {
                'move-up': 'N',
                'move-right': 'E',
                'move-down': 'S',
                'move-left': 'W',
                'skip-turn': 'H',
                'enter-time-machine': 'T',
            }
            it = iter(container)
            while 1:
                a = next(it)
                b = next(it, None)
                if b is None:
                    yield actions[a]
                    break
                yield actions[a] + actions[b] + ' '

        for clone in self.level.iter_clones():
            print " %s" % ("".join(_action2sf(clone)))

    def process_game_events(self):
        if self._gevent_queue.empty():
            # if the game event queue is empty just skip the code below.
            return
        try:
            while 1:
                e = self._gevent_queue.get_nowait()
                print "Event: %s" % e.event_type
                if e.event_type not in self._event_handler:
                    continue
                self._event_handler[e.event_type](e)
        except Queue.Empty:
            pass # expected

    def _perform_move(self, move):
        if self.level:
            self.level.perform_move(move)

    def _time_paradox(self, e):
        self.game_over = True
        print "TIME PARADOX: %s" % (e.reason)
        self.repaint()

    def _reset_crate(self, event):
        self._crates[event.source].pos = event.source.position
        self.repaint()

    def _end_of_turn(self, _):
        self.repaint()

    def _game_complete(self, _):
        self.game_over = True
        self.repaint()
        print "Your score is: %d" % self.level.score

    def _handle_mouse(self, lpos):
        if not self.mhilight or lpos == self.mhilight.pos:
            return
        if (lpos[0] < self.level.width and
               lpos[1] < self.level.height):
            self.mhilight.pos = lpos
            field = self.level.get_field(lpos)
            other = None
            if field.is_activation_source:
                other = field.iter_activation_targets()
            if field.is_activation_target:
                other = field.iter_activation_sources()
            if self.ohilights:
                for old in self.ohilights:
                    old.kill()
                self.ohilights = []
            if other:
                for o in other:
                    hilight = pygame.Surface((MAP_TILE_WIDTH, MAP_TILE_HEIGHT))
                    hilight.fill(pygame.Color("yellow"))
                    hilight.set_alpha(0x80)
                    s = Sprite(o.position, ((hilight,),), c_depth=-1)
                    self.sprites.add(s)
                    self.ohilights.append(s)
            self.repaint()


    def paint(self, s):
        # Draw the whole screen initially
        s.blit(self.surface, (0, 0))
        if self.level:
            self.overlays.draw(s)
            self.update(s)

    def update(self, s):
        if not self.level:
            return

        # Don't clear shadows and overlays, only sprites.
        self.sprites.clear(s, self.surface)

        self.sprites.update()
        has_animation = lambda x: self._clones[x].animation is not None
        self.active_animation = any(itertools.ifilter(has_animation,
                                                      self._clones))
        self.shadows.update()

        # Don't add shadows to dirty rectangles, as they already fit inside
        # sprite rectangles.
        self.shadows.draw(s)
        dirty = self.sprites.draw(s)
        # Don't add ovelays to dirty rectangles, only the places where
        # sprites are need to be updated, and those are already dirty.
        self.overlays.draw(s)
        # Update the dirty areas of the screen
        # pygame.display.update(dirty)

        return dirty

