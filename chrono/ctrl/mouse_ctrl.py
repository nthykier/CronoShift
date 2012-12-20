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

import pygame
import pygame.locals as pg

from chrono.model.position import Position
from chrono.view.sprites import gpos2lpos, MAP_TILE_WIDTH, MAP_TILE_HEIGHT

class MouseController(object):
    def __init__(self, game_window, level=None):
        self._active = False
        self.game_window = game_window
        self.last_pos = Position(0, 0)
        self.cur_pos = Position(0, 0)
        self.mouse_hilight = None
        self.mouse_rel_hilight = []
        self._level = level

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, lvl):
        old = self._level
        self._level = lvl
        self._new_level(old, lvl)
        if lvl and self.active and not self.mouse_hilight:
            self.mouse_hilight = self.game_window.make_hilight(self.cur_pos, color="red")

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, nval):
        self._active = nval
        if nval and self.level:
            self._restore_hilights()
        elif not nval and self.mouse_hilight:
            self.mouse_hilight.kill()
            self._remove_all_related_hilights()

    def _new_level(self, old_lvl, new_lvl):
        pass

    def _restore_hilights(self):
        self.mouse_hilight = self.game_window.make_hilight(self.cur_pos, color="red")
        self._hilight_related(self.cur_pos)

    def _remove_all_related_hilights(self):
        if self.mouse_rel_hilight:
            for o in self.mouse_rel_hilight:
                o.kill()
            self.mouse_rel_hilight = []

    def get_field_position(self, gpos):
        """Determine the logical position at a given graphical position

        Returns a position valid inside the current level (model) or None
        """
        if not self.level:
            return None

        corr = (self.game_window.rect.x - MAP_TILE_WIDTH/2,
                self.game_window.rect.y - MAP_TILE_HEIGHT)
        lpos = gpos2lpos(gpos, c=corr)
        if (0 <= lpos[0] < self.level.width and
                0 <= lpos[1] < self.level.height):
            return lpos
        return None

    def new_position(self, gpos, update_hilight=True):
        """Determine if the mouse pointer's position caused it to enter
        a new field

        Returns None if gpos is in the same field as the last time
        otherwise returns the position of the (logical) field beneath
        gpos.
        """
        npos = self.get_field_position(gpos)
        if npos is None:
            return None
        if self.cur_pos != npos:
            self.last_pos = self.cur_pos
            self.cur_pos = npos
            if update_hilight and self.mouse_hilight:
                self.mouse_hilight.pos = npos
                self.game_window.repaint()
            return npos
        return None

    def _hilight_related(self, lpos):
        field = self.level.get_field(lpos)
        other = None
        if field.is_activation_source:
            other = field.iter_activation_targets()
        if field.is_activation_target:
            other = field.iter_activation_sources()
        if self.mouse_rel_hilight:
            for old in self.mouse_rel_hilight:
                old.kill()
            self.mouse_rel_hilight = []
        if other:
            for o in other:
                s = self.game_window.make_hilight(o.position)
                self.mouse_rel_hilight.append(s)

    def event(self, e):
        if e.type == pg.MOUSEMOTION:
            npos = self.new_position(e.pos)
            if npos:
                self._hilight_related(npos)
                return True
            return False

class EditMouseController(MouseController):

    def __init__(self, game_window, level=None):
        super(EditMouseController, self).__init__(game_window, level=level)
        self.active_pos = None
        self._brush_mode = "none"
        self.field_tool = "field"
        self._src_hilight = None

    @property
    def brush_mode(self):
        return self._brush_mode

    @brush_mode.setter
    def brush_mode(self, nval):
        self._brush_mode = nval
        if nval != "none":
            self.active_pos = None

    def _edit_event(self, evt):
        if self._brush_mode != "none":
            # not hiligthing anything, we don't care
            return
        if evt.event_type != "field-connected" and evt.event_type != "field-disconnected":
            # We only care for those two events...
            return
        # figure out what hilight appears/disappears (if any)
        hipos = None
        marked = self.active_pos
        if marked is None:
            # regular "mouse-over" hilight
            marked = self.cur_pos

        if marked == evt.source.position:
            # source field is "marked", so target will change
            hipos = evt.target.position
        elif marked == evt.target.position:
            # target field is "marked", so source will change
            hipos = evt.source.position

        if not hipos:
            # None of them are "marked", so no hilighting will change
            return

        if evt.event_type == "field-connected":
            hilight = self.game_window.make_hilight(hipos)
            self.mouse_rel_hilight.append(hilight)
        else:
            nhilight = []
            for hilight in self.mouse_rel_hilight:
                if hilight.pos == hipos:
                    hilight.kill()
                else:
                    nhilight.append(hilight)
            self.mouse_rel_hilight = nhilight


    def _new_level(self, old_lvl, new_lvl):
        if old_lvl:
            old_lvl.remove_event_listener(self._edit_event)
        if new_lvl:
            new_lvl.add_event_listener(self._edit_event)


    def _restore_hilights(self):
        super(EditMouseController, self)._restore_hilights()
        if self.active_pos:
            self._src_hilight = self.game_window.make_hilight(self.active_pos, color="green")
            self._hilight_related(self.active_pos)

    def _remove_all_related_hilights(self):
        super(EditMouseController, self)._remove_all_related_hilights()
        if self._src_hilight:
            self._src_hilight.kill()

    def _right_click(self, lpos):
        if self.active_pos is None or self.active_pos != lpos:
            # Click once to activate/mark
            f = self.level.get_field(lpos)
            if self.active_pos:
                self.active_pos = None
                self._remove_all_related_hilights()
            if not (f.is_activation_source or f.is_activation_target):
                return True
            self.active_pos = lpos
            self._src_hilight = self.game_window.make_hilight(lpos, color="green")
            self._hilight_related(lpos)
            return True
        if self.active_pos == lpos:
            # Click twice to deactivate/unmark
            self.active_pos = None
            self._src_hilight.kill()
            return True

    def _left_click(self, lpos):
        if not self.active_pos:
            return
        source = self.level.get_field(self.active_pos)
        if self.active_pos == lpos:
            # Click on marked => attempt to change its initial state
            self.level.perform_change("set-initial-state", lpos, not source.activated)
            return True
        target = self.level.get_field(lpos)

        if not (target.is_activation_source or target.is_activation_target):
            return True

        if ((source.is_activation_source and target.is_activation_source) or
                (source.is_activation_target and target.is_activation_target)):
            # same kind (i.e both targets or both sources) - ignore
            return True

        if source.is_activation_target and target.is_activation_source:
            # swap
            source, target = target, source
        self.level.perform_change("toggle-connection", source.position, target.position)
        return True

    def _paint(self, lpos):
        if self.brush_mode == "field-brush":
            self.level.perform_change(self.field_tool, lpos)

    def event(self, e):
        if e.type == pg.MOUSEBUTTONDOWN:
            lpos = self.get_field_position(e.pos)
            if lpos is None:
                return False
            if self.brush_mode == "none":
                if e.button == 3: # right-click
                    return self._right_click(lpos)
                if e.button == 1: # right-click
                    return self._left_click(lpos)
                return False
            if e.button != 1: # left-click only atm
                return False
            self._paint(lpos)
            return True
        elif e.type == pg.MOUSEMOTION:
            npos = self.new_position(e.pos)
            if npos:
                pressed = pygame.mouse.get_pressed()
                if self.brush_mode == "none":
                    if self.active_pos is None:
                        self._hilight_related(npos)
                elif pressed[0]:
                    self._paint(npos)
                return True
