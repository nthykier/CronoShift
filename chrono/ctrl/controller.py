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

import pygame.locals as pg
from pgu import gui

from chrono.ctrl.diag import ConfirmDialog

DEFAULT_PLAY_CONTROLS = {
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
    pg.K_j: 'reset-time-jump',
}

class KeyController(object):

    def __init__(self, level=None, def_ctrl=None):
        self.level = level
        self.controls = def_ctrl

    def event(self, e):
        if not self.level:
            return False
        if e.type != pg.KEYDOWN:
            return False
        action = self._controls.get(e.key, None)
        if action:
            self._action2handler[action](action)
            return True
        return False

    @property
    def controls(self):
        return self._controls.copy()

    @controls.setter
    def controls(self, cmap):
        self._controls = cmap.copy()


class PlayKeyController(KeyController):

    def __init__(self, level=None, view=None, def_ctrl=None):
        if not def_ctrl:
            def_ctrl = DEFAULT_PLAY_CONTROLS
        super(PlayKeyController, self).__init__(level, def_ctrl=def_ctrl)
        self.view = view
        self.confirm_eot_on_start = True
        self._action2handler = {
            'move-up': self._perform_move,
            'move-down': self._perform_move,
            'move-left': self._perform_move,
            'move-right': self._perform_move,
            'skip-turn': self._perform_move,
            'enter-time-machine': self._perform_move,
            'reset-time-jump': self._perform_move,
            'print-actions': self._print_actions,
        }

    def event(self, e):
        if e.type != pg.KEYDOWN or not self.level:
            return False
        if self.view.active_animation:
            # Let the current animation finish first...
            return e.key in self._controls
        action = self._controls.get(e.key, None)
        if not action:
            return False
        if action == "enter-time-machine" and self.level.turn[0] < 1:
            diag = ConfirmDialog("Do you really want to end the current time-jump in turn %d?" \
                                     % self.level.turn[0])
            diag.connect(gui.CHANGE, self._action2handler[action], action)
            diag.open()
            return # Don't consume here or the dialog won't work
        if self.confirm_eot_on_start and action == "skip-turn":
            current_clone = self.level.active_player
            if current_clone is not None and current_clone.position == self.level.start_location.position:
                diag = ConfirmDialog("Do you really want to skip your time on the time machine?")
                diag.connect(gui.CHANGE, self._action2handler[action], action)
                diag.open()
                return # Don't consume here or the dialog won't work

        self._action2handler[action](action)
        return True


    def _perform_move(self, move):
        if self.level:
            self.level.perform_move(move)

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

