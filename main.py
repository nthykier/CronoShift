#!/usr/bin/python
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

import argparse
import functools
import os
import pygame
import sys

if 1:
    # If pgu-0.16 is there, make it available
    d = os.path.join(os.path.dirname(os.path.realpath(__file__)), "pgu-0.18")
    if os.path.exists(d):
        print "Using embedded pgu"
        sys.path.insert(0, d)

from pgu import gui

from chrono.model.level import EditableLevel, Level, solution2actions
from chrono.ctrl.controller import PlayKeyController
from chrono.ctrl.mouse_ctrl import EditMouseController, MouseController
from chrono.view.game_window import GameWindow

class OpenLevelDialog(gui.Dialog):
    def __init__(self,**params):
        title = gui.Label("Open Level")

        t = gui.Table()

        self.value = gui.Form()
        self.li = gui.Input(name="fname")
        bb = gui.Button("...")
        bb.connect(gui.CLICK, self.open_file_browser, None)

        t.tr()
        t.td(gui.Label("Open: "))
        t.td(self.li,colspan=3)
        t.td(bb)

        t.tr()
        e = gui.Button("Play")
        e.connect(gui.CLICK,self.send,gui.CHANGE)
        t.td(e,colspan=2)

        e = gui.Button("Cancel")
        e.connect(gui.CLICK,self.close,None)
        t.td(e,colspan=2)

        gui.Dialog.__init__(self,title,t)

    def open_file_browser(self, *arg):
        d = gui.FileDialog()
        d.connect(gui.CHANGE, self.handle_file_browser_closed, d)
        d.open()

    def handle_file_browser_closed(self, dlg):
        if dlg.value:
            self.li.value = dlg.value

class NewLevelDialog(gui.Dialog):
    def __init__(self,**params):
        title = gui.Label("New Level")

        t = gui.Table()

        self.value = gui.Form()
#        self.input_name = gui.Input(name="name", value="untitled")
        self.input_width = gui.Input(name="width", value=10)
        self.input_height = gui.Input(name="height", value=10)

#        t.tr()
#        t.td(gui.Label("Name: "))
#        t.td(self.input_name,colspan=3)

        t.tr()
        t.td(gui.Label("Width: "))
        t.td(self.input_width)
        t.td(gui.Label("Height: "))
        t.td(self.input_height)

        t.tr()
        e = gui.Button("Create")
        e.connect(gui.CLICK,self.send,gui.CHANGE)
        t.td(e,colspan=2)

        e = gui.Button("Cancel")
        e.connect(gui.CLICK,self.close,None)
        t.td(e,colspan=2)

        gui.Dialog.__init__(self,title,t)


class ScoreTracker(gui.Label):

    def __init__(self):
        super(ScoreTracker, self).__init__()
        self._score = None
        self.reset_score()

    @property
    def score(self):
        return self._score

    @score.setter
    def score(self, nscore):
        if self._score != nscore:
            self._score = nscore
            self.set_text("Score: %d, Turn %d/%d, Clone: %d" % nscore)


    def reset_score(self):
        self.score = (0, 1, 1, 1)

    def update_score(self, lvl, *args):
        # turn is 0-index'ed, but it is better presented as 1-index'ed.
        t = lvl.turn
        self.score = (lvl.score, t[0] + 1, t[1] + 1, lvl.number_of_clones)

class TileIcon(gui.Widget):

    def __init__(self, image, **kwords):
        self.surface = image
        kwords.setdefault("x", 1)
        kwords.setdefault("y", 1)
        kwords.setdefault("width", image.get_rect().w + 2)
        kwords.setdefault("height", image.get_rect().h + 2)
        super(TileIcon, self).__init__(**kwords)

    def paint(self, s):
        s.blit(self.surface,  (0, 0))

def make_edit_ctrls(app, width, height):
    c = gui.Container(width=width, height=height)
    spacer = 8
    from_left = spacer
    from_top = spacer

    new_map = gui.Button("New map")
    c.add(new_map, from_left, from_top)
    new_map.connect(gui.CLICK, app.new_lvl_d.open, None)
    new_map.rect.w, new_map.rect.h = new_map.resize()

    from_left += new_map.rect.w + spacer

    play_lvl = gui.Button("Play Level")
    c.add(play_lvl, from_left, from_top)
    play_lvl.connect(gui.CLICK, app.play_edit_level, None)
    play_lvl.rect.w, play_lvl.rect.h = play_lvl.resize()

    from_left += play_lvl.rect.w + spacer

    write_lvl = gui.Button("Write Level")
    c.add(write_lvl, from_left, from_top)
    write_lvl.connect(gui.CLICK, app.write_level, None)
    write_lvl.rect.w, write_lvl.rect.h = write_lvl.resize()

    from_top += write_lvl.rect.h + spacer

    from_left = spacer

    fields = [("none", None, 0, 0), ("field", "tileset", 0, 3),
              ("wall", "tileset", 0, 0), ("gate", "gate", 0, 0),
              ("button", "button", 0, 0)]

    group = gui.Group(name="tile", value=fields[0][0])

    for name, sprite, x, y in fields:
        if sprite:
            w = TileIcon(app.game_window.map_cache[sprite][x][y])
        else:
            w = gui.Label(name)
        w.rect.w, w.rect.h = w.resize()
        tool = gui.Tool(group, w, name)
        tool.connect(gui.CLICK, app.chg_edit_mode, name)
        c.add(tool, from_left, from_top)
        tool.rect.w, tool.rect.h = tool.resize()
        from_left += tool.rect.w + spacer

    return c

def make_game_ctrls(app, width, height):
    c = gui.Container(width=width, height=height)
    spacer = 8
    from_left = spacer

    play_s = gui.Button("Play Solution")
    play_s.connect(gui.CLICK, app.play_solution, None)
    c.add(play_s, from_left, spacer)
    play_s.rect.w, play_s.rect.h = play_s.resize()

    from_left += play_s.rect.w + spacer

    reset_tj = gui.Button("Reset clone")
    reset_tj.connect(gui.CLICK, app.reset_clone, None)
    c.add(reset_tj, from_left, spacer)
    reset_tj.rect.w, reset_tj.rect.h = reset_tj.resize()

    from_left += reset_tj.rect.w + spacer

    reset_lvl = gui.Button("Reset level")
    reset_lvl.connect(gui.CLICK, app.reset_level, None)
    c.add(reset_lvl, from_left, spacer)

    return c

class Application(gui.Desktop):

    def __init__(self, **params):
        super(Application, self).__init__(**params)
        self.connect(gui.QUIT, self.quit, None)

        self.widget = gui.Container(width=640,height=480)

        self._mode = "play"
        self.fcounter = 0
        self.score = ScoreTracker()
        self.edit_level = None
        self.level = None
        self.auto_play = None
        self.game_window = GameWindow()
        self.play_ctrl = PlayKeyController(view=self.game_window)
        self.play_mctrl = MouseController(self.game_window)
        self.edit_ctrl = None
        self.edit_mctrl = EditMouseController(self.game_window)

        self.ctrl = self.play_ctrl
        self.mctrl = self.play_mctrl
        self.open_lvl_d = OpenLevelDialog()
        self.new_lvl_d = NewLevelDialog()
        self.open_lvl_d.connect(gui.CHANGE, self.action_open_lvl, None)
        self.new_lvl_d.connect(gui.CHANGE, self.new_map, None)

    def init(self, *args, **kwords):
        super(Application, self).init(*args, **kwords)

        c = self.widget
        game_window = self.game_window
        spacer = 8
        from_top = 0
        from_left = spacer

        menus = gui.Menus([
                ('File/Load', self.open_lvl_d.open, None),
                ('File/Quit', self.quit, None),
        ])
        c.add(menus, 0, from_top)
        menus.rect.w, menus.rect.h = menus.resize()
        from_top += menus.rect.h + spacer

        c.add(game_window, spacer, from_top)
        game_window.rect.w, game_window.rect.h = game_window.resize()

        from_top += game_window.rect.h + spacer

        c.add(self.score, spacer, from_top)
        self.score.rect.w, self.score.rect.h = self.score.resize()
        from_top += self.score.rect.h + spacer


        play_ctrls = make_game_ctrls(self, width=640, height=480 - from_top)
        edit_ctrls = make_edit_ctrls(self, width=640, height=480 - from_top)

        self.group = gui.Group(name='ctrl-mode', value="play")

        play_mode_label = gui.Label("Play-mode")
        play_mode = gui.Tool(self.group, play_mode_label, "play")
        edit_mode = gui.Tool(self.group, gui.Label("Edit-mode"), "edit")

        c.add(play_mode, spacer, from_top)
        play_mode.rect.w, play_mode.rect.h = play_mode.resize()

        c.add(edit_mode, 2 * spacer + play_mode.rect.w, from_top)
        edit_mode.rect.w, edit_mode.rect.h = edit_mode.resize()

        from_top += play_mode.rect.h + spacer

        w = gui.ScrollArea(play_ctrls)

        def switch_mode():
            self._mode = self.group.value
            if self.mode == "play":
                w.widget = play_ctrls
                self.mctrl = self.play_mctrl
                self.ctrl = self.play_ctrl
                if self.level:
                    self.game_window.use_level(self.level)
            else:
                self.mctrl = self.edit_mctrl
                w.widget = edit_ctrls
                if self.edit_level:
                    self.game_window.use_level(self.edit_level)

            play_mode_label.focus()

        self.group.connect(gui.CHANGE, switch_mode)

        c.add(w, 0, from_top)
        w.rect.w, w.rect.h = w.resize()

        self.resize()
        self.repaint()

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, val):
        self.group.value = val

    def reset_clone(self, *args):
        if self.level:
            self.auto_play = None
            self.level.perform_move('reset-time-jump')

    def reset_level(self, *args):
        if self.level:
            self.auto_play = None
            self.level.perform_move('reset-level')

    def action_open_lvl(self,value):
        self.open_lvl_d.close()
        self.load_level(self.open_lvl_d.value['fname'].value)

    def load_level(self, fname):
        self.auto_play = None
        edit_level = EditableLevel()
        try:
            edit_level.load_level(fname)
        except IOError as e:
            self._show_error("Cannot load map", str(e))
            return

        self.edit_level = edit_level
        self.level = Level()
        self.play_ctrl.level = self.level
        self.play_mctrl.level = self.level
        self.edit_mctrl.level = edit_level
        sc = functools.partial(self.score.update_score, self.level)
        self.level.init_from_level(self.edit_level)
        lvl = self.edit_level
        if self.mode == "play":
            lvl = self.level
        self.game_window.use_level(lvl)
        self.level.add_event_listener(sc)
        self.level.start()

    def _show_error(self, title_msg, body_msg):
        c = gui.Container()
        c.add(gui.Label(body_msg), 8, 8)
        d = gui.Dialog(gui.Label(title_msg), c)
        d.open()

    def play_solution(self, *args):
        if not self.level:
            return

        sol = self.level.get_metadata_raw("solution")
        if not sol:
            print "%s has no solution" % level.name
            return
        self.reset_level()
        print "Playing solution"
        self.auto_play = solution2actions(sol)

    def new_map(self, *args):
        self.new_lvl_d.close()
        res = self.new_lvl_d.value

        edit_level = self.edit_level or EditableLevel()

        try:
            edit_level.new_map(int(res["width"].value), int(res["height"].value))
        except (TypeError, ValueError) as e:
            self._show_error("Cannot create map", str(e))
            return

        self.edit_level = edit_level
        self.edit_mctrl.level = edit_level
        self.game_window.use_level(edit_level)

    def chg_edit_mode(self, mode):
        if mode != "none":
            self.edit_mctrl.brush_mode = "field-brush"
            self.edit_mctrl.field_tool = mode
        else:
            self.edit_mctrl.brush_mode = "none"

    def write_level(self, *args):
        if not self.edit_level:
            return
        try:
            self.edit_level.print_lvl("<stdout>", sys.stdout)
        except IOError as e:
            self._show_error("Cannot save map", str(e))

    def play_edit_level(self, *args):
        if not self.edit_level:
            return
        level = Level()
        try:
            level.init_from_level(self.edit_level)
        except ValueError as e:
            self._show_error("Cannot play map", str(e))
            return
        self.mode = "play"
        self.level = level
        self.ctrl.level = self.level
        self.game_window.use_level(self.level)
        sc = functools.partial(self.score.update_score, self.level)
        self.level.add_event_listener(sc)
        self.level.start()

    def event(self, evt):
        if self.mctrl.event(evt) or self.ctrl.event(evt):
            self.game_window.focus()
            return True
        return super(Application, self).event(evt)

    def loop(self):
        self.game_window.process_game_events()
        self.fcounter = (self.fcounter + 1) % 15
        if not self.fcounter:
            # 15th frame
            if self.auto_play:
                act = next(self.auto_play, None)
                if not act:
                    self.auto_play = None
                    return
                self.level.perform_move(act)
                self.game_window.focus()
        super(Application, self).loop()

app = Application()
if len(sys.argv) > 1:
    # Load the level - we have to wait for the init event before
    app.connect(gui.INIT, lambda *x: app.load_level(sys.argv[1]), None)
app.run(delay=67) # 15 fps =~ 67 ms delay
