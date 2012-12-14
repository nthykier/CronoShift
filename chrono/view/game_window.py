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
        GATE_CLOSED, GATE_OPEN, MoveableSprite, gpos2lpos,
        update_background
    )
from chrono.view.tile_cache import TileCache

def _kill_sprite(container, key):
    if key in container:
        container[key].kill()
        del container[key]

class GameWindow(gui.Widget):
    """The main game object."""

    def __init__(self, resource_dirs=None, **params):
        params['width'] = 450
        params['height'] = 300
        params['focusable'] = False
        super(GameWindow, self).__init__(**params)
        self.surface = pygame.Surface((450, 300))
        self.surface.fill((0, 0, 0))
        self.grid = False
        self.shadows = pygame.sprite.RenderUpdates()
        self.hilights = pygame.sprite.RenderUpdates()
        self.sprites = SortedUpdates()
        self.overlays = pygame.sprite.RenderUpdates()
        self.overlays_sprites = {}
        self.animated_background = pygame.sprite.RenderUpdates()
        self.animated_background_sprites = {}
        self._tileset = "tileset"
        self._sprite_cache = TileCache(32, 32, resource_dirs=resource_dirs)
        self.map_cache = TileCache(MAP_TILE_WIDTH, MAP_TILE_HEIGHT,
                                   resource_dirs=resource_dirs)
        self._clones = {}
        self._gates = {}
        self._crates = {}
        self._done = True
        self.active_animation = False
        self._gevent_seq = []
        self._gevent_queue = Queue.Queue()
        self.level = None
        self._event_handler = {
            # play
            'move-up': functools.partial(self._move, Direction.NORTH),
            'move-down': functools.partial(self._move, Direction.SOUTH),
            'move-left': functools.partial(self._move, Direction.WEST),
            'move-right': functools.partial(self._move, Direction.EAST),
            'add-player-clone': self._player_clone,
            'remove-player-clone': self._player_clone,
            'field-activated': self._field_state_change,
            'field-deactivated': self._field_state_change,
            'time-paradox': self._time_paradox,
            'game-complete': self._game_complete,
            'end-of-turn': self._end_of_turn,
            'goal-obtained': lambda *x: self.goal.kill(),
            'goal-lost': lambda *x: self.animated_background.add(self.goal),
            'jump-moveable': self._jump_moveable,

            # edit
            'new-map': self._new_map,
            'replace-tile': self._replace_tile,
            'remove-special-field': self._remove_special_field,
            'add-crate': self._add_remove_crate,
            'remove-crate': self._add_remove_crate,
        }

    @property
    def pending_animation(self):
        return (self.active_animation or not self._done
                or not self._gevent_queue.empty())

    def use_level(self, level, grid=None):
        """Set the level as the current one."""

        if grid is not None:
            self.grid = grid
        self.level = level
        self._gevent_seq = []
        self._gevent_queue = Queue.Queue()
        level.add_event_listener(self._new_event)
        self._new_map()

    def _new_event(self, e):
        self._gevent_seq.append(e)
        if e.event_type == "end-of-event-sequence":
            # flush
            self._gevent_queue.put(self._gevent_seq)
            self._gevent_seq = []

    def _new_map(self, *args):
        self.shadows = pygame.sprite.RenderUpdates()
        self.sprites = SortedUpdates()
        self.overlays = pygame.sprite.RenderUpdates()
        self.animated_background = pygame.sprite.RenderUpdates()
        self.overlays_sprites = {}
        self.animated_background_sprites = {}
        self._clones = {}
        self._gates = {}
        self._crates = {}

        level = self.level

        # Render the level map
        background, overlays = make_background(level,
                                               map_cache=self.map_cache,
                                               tileset=self._tileset,
                                               grid=self.grid)
        self.surface.fill((0, 0, 0))
        self.surface.blit(background, (0,0))

        for field in level.iter_fields():
            # Crates looks best in 32x32, gates and buttons in 24x16
            #   - if its "on top of" a field 32x32 usually looks best.
            #   - if it is (like) a field, 24x16 is usually better
            # - use sprite_cache and map_cache accordingly.
            crate = level.get_crate_at(field.position)
            if crate:
                self._add_crate(crate)
            self._init_field(field)

        self._add_overlay(overlays)

        try:
            iter_clones = level.iter_clones
        except AttributeError:
            # Not a playable map, no clones to place
            iter_clones = None

        if iter_clones:
            for clone in iter_clones():
                self._new_clone(clone)

        self.repaint()

    def _add_crate(self, crate):
        c_sprite = MoveableSprite(crate.position, self._sprite_cache['crate'], c_depth=1)
        self._crates[crate] = c_sprite
        self.sprites.add(c_sprite)

    def _add_remove_crate(self, evt):
        if evt.event_type == 'add-crate':
            self._add_crate(evt.source)
        else:
            _kill_sprite(self._crates, evt.source)

    def _init_field(self, field):
        ani_bg = None
        if field.symbol == '-' or field.symbol == '_':
            ani_bg = Sprite(field.position, self.map_cache['campfiregate'])
            self._gates[field.position] = ani_bg
            if field.symbol == '-':
                ani_bg.state = GATE_CLOSED
        if field.symbol == 'b':
            ani_bg = Sprite(field.position, self.map_cache['stonebutton'])
        if field.symbol == 'o':
            ani_bg = Sprite(field.position, self.map_cache['onetimebutton'])
        if field.symbol == 'p':
            ani_bg = Sprite(field.position, self.map_cache['onetimepassage'])
        if field.symbol == 'S':
            # Highlight the start location
            ani_bg = Sprite(field.position, self.map_cache['timemachine'])
        if field.symbol == 'G':
            ani_bg = Sprite(field.position, self.map_cache['coingoal'])
            self.goal = ani_bg
        if ani_bg:
            self.animated_background.add(ani_bg)
            self.animated_background_sprites[field.position] = ani_bg
        return

    def _add_overlay(self, overlays):
        # Add the overlays for the level map
        for (x, y), image in overlays.iteritems():
            overlay = pygame.sprite.Sprite(self.overlays)
            overlay.image = image.subsurface(0, 0, MAP_TILE_WIDTH, MAP_TILE_HEIGHT/2)
            overlay.rect = image.get_rect().move(Position(x*MAP_TILE_WIDTH,
                                                          y * MAP_TILE_HEIGHT - MAP_TILE_HEIGHT/2))
            self.overlays_sprites[Position(x,y)] = overlay

    def _remove_special_field(self, evt):
        f = evt.source
        _kill_sprite(self.animated_background_sprites, f.position)

    def _replace_tile(self, evt):
        f = evt.source

        # Kill the old animations on this field (if any)
        _kill_sprite(self._gates, f.position)
        _kill_sprite(self.animated_background_sprites, f.position)
        _kill_sprite(self.overlays_sprites, f.position)

        # Kill "nearby" overlays - they should only be "south", but mah
        for d in (Direction.NORTH, Direction.SOUTH, Direction.WEST, Direction.EAST):
            dpos = f.position.dir_pos(d)
            _kill_sprite(self.overlays_sprites, dpos)

        # FIXME: remove old overlay
        overlays = update_background(self.map_cache[self._tileset], self.surface, self.level, f,
                                     fixup=True, grid=self.grid)
        self._add_overlay(overlays)
        ani_bg = None

        self._init_field(f)
        self.repaint()

    def _move(self, d, event):
        """Start walking in specified direction."""

        actor = None
        if event.source in self._crates:
            actor = self._crates[event.source]
        else:
            actor = self._clones[event.source][0]

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
        if event.source.symbol == "b" or event.source.symbol == "o" or event.source.symbol == "p":
            b = self.animated_background_sprites[src_pos]
            if b:
                b.state = int(event.source.activated)

    def _new_clone(self, clone):
        sprite = PlayerSprite(clone, self._sprite_cache['player'])
        shadow = Shadow(sprite, self._sprite_cache["shadow"][0][0])
        self._clones[clone] = (sprite, shadow)
        self.sprites.add(sprite)
        self.shadows.add(shadow)

    def _player_clone(self, event):
        if event.event_type == "add-player-clone":
            self._new_clone(event.source)
        elif event.source in self._clones:
            csprite, shadow = self._clones[event.source]
            del self._clones[event.source]
            csprite.kill()
            shadow.kill()

        self.repaint()

    def process_game_events(self):
        if not self._done or self._gevent_queue.empty():
            # if the game event queue is empty just skip the code below.
            return
        try:
            seq = self._gevent_queue.get_nowait()
            print "Event seq [%s]" % (", ".join(x.event_type for x in seq))
            for e in seq:
                if e.event_type not in self._event_handler:
                    continue
                self._event_handler[e.event_type](e)
            self._done = False
        except Queue.Empty:
            pass # expected

    def _time_paradox(self, e):
        self.repaint()

    def _jump_moveable(self, event):
        actor = None
        if event.source in self._crates:
            actor = self._crates[event.source]
        elif event.source in self._clones:
            actor = self._clones[event.source][0]
        actor.pos = event.source.position
        self.repaint()

    def _end_of_turn(self, _):
        self.repaint()

    def _game_complete(self, _):
        self.repaint()

    def make_hilight(self, lpos, color="yellow"):
        hilight = pygame.Surface((MAP_TILE_WIDTH, MAP_TILE_HEIGHT))
        hilight.fill(pygame.Color(color))
        hilight.set_alpha(0x80)
        s = Sprite(lpos, ((hilight,),))
        self.hilights.add(s)
        return s


    def paint(self, s):
        # Draw the whole screen initially
        s.blit(self.surface, (0, 0))
        if self.level:
            self.update(s)

    def update(self, s):
        if not self.level:
            return

        # Don't clear shadows and overlays, only sprites.
        self.sprites.clear(s, self.surface)
        self.animated_background.clear(s, self.surface)
        self.hilights.clear(s, self.surface)

        self.sprites.update()
        self.animated_background.update()
        has_animation = lambda x: self._clones[x][0].animation is not None
        active_animation = any(itertools.ifilter(has_animation,
                                                 self._clones))
        if not self._done and not active_animation:
            self._done = True
            self.active_animation = False

        self.shadows.update()

        # Don't add shadows to dirty rectangles, as they already fit inside
        # sprite rectangles.
        self.shadows.draw(s)


        # Draw the "animated" background (gates).  These may be dirty even
        # if no actor approcated it (eg. via buttons)
        dirty = self.animated_background.draw(s)

        # Draw hilights on top of backgrounds...
        dirty.extend(self.hilights.draw(s))

        # Draw actors (and crates) on top of everything
        dirty.extend(self.sprites.draw(s))


        # Don't add ovelays to dirty rectangles, only the places where
        # sprites are need to be updated, and those are already dirty.
        self.overlays.draw(s)

        return dirty
