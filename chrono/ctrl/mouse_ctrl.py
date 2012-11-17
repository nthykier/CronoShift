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

from chrono.model.field import Position
from chrono.view.sprites import gpos2lpos, MAP_TILE_WIDTH, MAP_TILE_HEIGHT

class MouseController(object):
    def __init__(self, game_window, level=None):
        self.game_window = game_window
        self.level = level
        self.last_pos = Position(0, 0)
        self.cur_pos = Position(0, 0)

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
            if update_hilight:
                self.game_window.mhilight.position = npos
            return npos
        return None

    def _update_hilight(self, npos):
        self.game_window._handle_mouse(npos)

    def event(self, e):
        if e.type == pg.MOUSEMOTION:
            npos = self.new_position(e.pos)
            if npos:
                self._update_hilight(npos)
                return True
            return False

class EditMouseController(MouseController):

    def __init__(self, game_window, level=None):
        super(EditMouseController, self).__init__(game_window, level=level)
        self.brush_mode = "none"
        self.field_tool = "field"

    def _paint(self, lpos):
        if self.brush_mode == "field-brush":
            self.level.perform_change(self.field_tool, lpos)

    def event(self, e):
        if e.type == pg.MOUSEBUTTONDOWN:
            lpos = self.get_field_position(e.pos)
            if lpos is None:
                return False
            if self.brush_mode == "none":
                return False
            self._paint(lpos)
            return True
        if e.type == pg.MOUSEMOTION:
            npos = self.new_position(e.pos)
            if npos:
                pressed = pygame.mouse.get_pressed()
                if self.brush_mode == "none":
                    self._update_hilight(npos)
                elif pressed[0]:
                    self._paint(npos)
                return True
