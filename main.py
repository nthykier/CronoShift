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
import itertools
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

from chrono.model.field import Position
from chrono.model.level import EditableLevel, Level, solution2actions
from chrono.ctrl.controller import PlayKeyController
from chrono.ctrl.mouse_ctrl import EditMouseController, MouseController
from chrono.ctrl.diag import ErrorDialog
from chrono.view.game_window import GameWindow
from chrono.view.tutorial import Tutorial

class SelectLevelDialog(gui.Dialog):
    def __init__(self, text, confirm_text, title, **params):
        title = gui.Label(title)

        t = gui.Table()

        self.value = gui.Form()
        self.li = gui.Input(name="fname")
        d = params.get('default_level', None)
        if d is not None:
            self.li.value = d
        bb = gui.Button("...")
        bb.connect(gui.CLICK, self.open_file_browser, None)

        t.tr()
        t.td(gui.Label(text +": "))
        t.td(self.li,colspan=3)
        t.td(bb)

        t.tr()
        e = gui.Button(confirm_text)
        e.connect(gui.CLICK,self.confirm)
        t.td(e,colspan=2)

        e = gui.Button("Cancel")
        e.connect(gui.CLICK,self.close,None)
        t.td(e,colspan=2)

        gui.Dialog.__init__(self,title,t)

    def confirm(self):
        self.close()
        self.send(gui.CHANGE)

    def open_file_browser(self, *arg):
        d = gui.FileDialog()
        d.connect(gui.CHANGE, self.handle_file_browser_closed, d)
        d.open()

    def handle_file_browser_closed(self, dlg):
        if dlg.value:
            self.li.value = dlg.value

class NewLevelDialog(gui.Dialog):
    def __init__(self,**params):
        title = gui.Label("New/Resize Level")

        t = gui.Table()

        self.value = gui.Form()
        self.input_width = gui.Input(name="width", value="10", size=3)
        self.input_height = gui.Input(name="height", value="10", size=3)
        self.input_clear = gui.Switch(value=True)
        self.value.add(self.input_clear, name="clear", value=True)
        self.input_trans_width = gui.Input(name="trans-width", value="0", size=3)
        self.input_trans_height = gui.Input(name="trans-height", value="0", size=3)

        t.tr()
        t.td(gui.Label("Size: "))
        t.td(self.input_width)
        t.td(gui.Label("x"))
        t.td(self.input_height)

        t.tr()
        t.td(gui.Label("Clear map: "))
        t.td(self.input_clear)

        t.tr()
        t.td(gui.Label("Translation: "))
        t.td(self.input_trans_width)
        t.td(gui.Label("x"))
        t.td(self.input_trans_height)

        t.tr()
        t.td(gui.Label("(relative to top left corner)"))

        t.tr()

        crlabel = gui.Label("Create")
        e = gui.Button(crlabel)
        e.connect(gui.CLICK,self.send,gui.CHANGE)
        def _rename():
            if self.input_clear.value:
                crlabel.set_text("Create")
            else:
                crlabel.set_text("Resize")

        self.input_clear.connect(gui.CHANGE, _rename)
        t.td(e, colspan=2)

        e = gui.Button("Cancel")
        e.connect(gui.CLICK,self.close,None)
        t.td(e, colspan=2)

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

    new_map = gui.Button("New/resize map")
    c.add(new_map, from_left, from_top)
    new_map.connect(gui.CLICK, app.new_lvl_d.open, None)
    new_map.rect.w, new_map.rect.h = new_map.resize()

    from_left += new_map.rect.w + spacer

    play_lvl = gui.Button("Play Level")
    c.add(play_lvl, from_left, from_top)
    play_lvl.connect(gui.CLICK, app.play_edit_level, None)
    play_lvl.rect.w, play_lvl.rect.h = play_lvl.resize()

    from_left += play_lvl.rect.w + spacer

    write_lvl = gui.Button("Save Level")
    c.add(write_lvl, from_left, from_top)
    write_lvl.connect(gui.CLICK, app.save_level, None)
    write_lvl.rect.w, write_lvl.rect.h = write_lvl.resize()

    from_top += write_lvl.rect.h + spacer

    from_left = spacer

    fields = [("none", None, 0, 0), ("field", "tileset", 0, 3),
              ("wall", "tileset", 0, 0), ("gate", "campfiregate", 0, 0),
              ("button", "stonebutton", 0, 0), ("onetimebutton", "onetimebutton", 0, 0),
              ("onetimepassage", "onetimepassage", 0, 0),
              ("crate",  None, 0, 0), ("start", "timemachine", 0, 0),
              ("goal", None, 0, 0)]

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
    from_top = spacer
    from_left = spacer

    enter_tm = gui.Button("Enter time machine")
    enter_tm.connect(gui.CLICK, app.play_ctrl.perform_move,
                     "enter-time-machine")
    c.add(enter_tm, from_left, from_top)
    enter_tm.rect.w, enter_tm.rect.h = enter_tm.resize()

    from_left += enter_tm.rect.w + spacer

    play_s = gui.Button("Play Solution")
    play_s.connect(gui.CLICK, app.play_solution, None)
    c.add(play_s, from_left, from_top)
    play_s.rect.w, play_s.rect.h = play_s.resize()

    from_left += play_s.rect.w + spacer

    reset_tj = gui.Button("Reset clone")
    reset_tj.connect(gui.CLICK, app.reset_clone, None)
    c.add(reset_tj, from_left, from_top)
    reset_tj.rect.w, reset_tj.rect.h = reset_tj.resize()

    from_left += reset_tj.rect.w + spacer

    reset_lvl = gui.Button("Reset level")
    reset_lvl.connect(gui.CLICK, app.reset_level, None)
    c.add(reset_lvl, from_left, from_top)
    reset_lvl.rect.w, reset_lvl.rect.h = reset_lvl.resize()

    from_left += reset_lvl.rect.w + spacer

    hint = gui.Button("Show hint")
    hint.connect(gui.CLICK, app.show_hint)
    c.add(hint, from_left, from_top)
    hint.rect.w, hint.rect.h = hint.resize()

    from_left = spacer
    from_top += reset_lvl.rect.h + spacer

    l = gui.Label("Auto finish time-jump: ")
    c.add(l, from_left, from_top)
    l.rect.w, l.rect.h = l.resize()

    from_left += l.rect.w + spacer

    cbox = app.skip_till_time_jump
    c.add(cbox, from_left, from_top)
    cbox.rect.w, cbox.rect.h = cbox.resize()

    return c

class CTRLWidget(gui.Container):
    """Hack to work around <...> focus/update handling"""

    key_ctrl = None
    mouse_ctrl = None
    game_window = None

    def update(self,s):
        # Always run updates on the game window
        self.game_window.reupdate()
        return super(CTRLWidget, self).update(s)

    def event(self, e):
        # Arrow keys are by default used for moving focus between
        # widgets, so give our key-handler higher priority than
        # that...
        if self.key_ctrl and self.key_ctrl.event(e):
            return True
        if super(CTRLWidget, self).event(e):
            return True
        if self.mouse_ctrl and self.mouse_ctrl.event(e):
            return True
        return False

class Application(gui.Desktop):

    def __init__(self, **params):
        super(Application, self).__init__(**params)
        self.connect(gui.QUIT, self.quit, None)

        self.widget = CTRLWidget(width=640,height=490)

        self._mode = "play"
        self.fcounter = 0
        self.score = ScoreTracker()
        self.edit_level = None
        self.level = None
        self.auto_play = None
        self.skip_till_time_jump = gui.Switch(value=False)
        self.skip_till_time_jump.connect(gui.CHANGE, self.toggle_auto_finish)
        self.game_window = GameWindow()
        self.ctrl_widget = self.widget
        self.ctrl_widget.game_window = self.game_window
        self.play_ctrl = PlayKeyController(view=self.game_window)
        self.play_mctrl = MouseController(self.game_window)
        self.edit_ctrl = None
        self.edit_mctrl = EditMouseController(self.game_window)

        self.ctrl_widget.key_ctrl = self.play_ctrl
        self.ctrl_widget.mouse_ctrl = self.play_mctrl
        self.ctrl_widget.mouse_ctrl.active = True
        self.open_lvl_d = SelectLevelDialog("Open", "Play", "Open level")
        self.new_lvl_d = NewLevelDialog()
        self.open_lvl_d.connect(gui.CHANGE, self.action_open_lvl)
        self.new_lvl_d.connect(gui.CHANGE, self.new_map)

    def init(self, *args, **kwords):
        super(Application, self).init(*args, **kwords)

        c = self.widget

        game_window = self.game_window
        spacer = 8
        from_top = 0
        from_left = spacer

        pygame.mixer.init()
        self.time_paradox_sound = pygame.mixer.Sound("sound/123921__silencer1337__machinefail.wav")
        self.win_sound          = pygame.mixer.Sound("sound/90138__pierrecartoons1979__win1.wav")

        menus = gui.Menus([
                ('File/Load', self.open_lvl_d.open, None),
                ('File/Quit', self.quit, None),
                ('Help/Tutorial', self.open_tutorial, None),
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


        play_ctrls = make_game_ctrls(self, width=640, height=490 - from_top)
        edit_ctrls = make_edit_ctrls(self, width=640, height=490 - from_top)

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
            self.ctrl_widget.mouse_ctrl.active = False
            if self.mode == "play":
                w.widget = play_ctrls
                self.ctrl_widget.mouse_ctrl = self.play_mctrl
                self.ctrl_widget.ctrl = self.play_ctrl
                if self.level:
                    self.game_window.use_level(self.level, grid=False)
            else:
                self.ctrl_widget.mouse_ctrl = self.edit_mctrl
                w.widget = edit_ctrls
                if self.edit_level:
                    self.game_window.use_level(self.edit_level, grid=True)

            self.ctrl_widget.mouse_ctrl.active = True

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
        if self.auto_play:
            return
        if self.level:
            self.level.perform_move('reset-time-jump')

    def reset_level(self, *args):
        if self.auto_play:
            return
        if self.level:
            self.level.perform_move('reset-level')

    def action_open_lvl(self):
        self.load_level(self.open_lvl_d.value['fname'].value)

    def game_event(self, ge):
        if (ge.event_type != "time-jump" and ge.event_type != "end-of-turn" and
              ge.event_type != "game-complete" and ge.event_type != "time-paradox"):
            return

        if ge.event_type == "game-complete":
            self.win_sound.play()
            self.auto_play = None
        elif ge.event_type == "time-paradox":
            self.time_paradox_sound.play()
            self.auto_play = None

        if not self.skip_till_time_jump.value:
            return
        if ge.event_type != "end-of-turn":
            self.auto_play = None
            return
        if self.level.active_player or self.auto_play:
            return
        self.fcounter = 0
        self.auto_play = itertools.repeat("skip-turn")

    def toggle_auto_finish(self, *args):
        nvalue = self.skip_till_time_jump.value
        if not nvalue:
            self.auto_play = None
        if nvalue and self.mode == "play" and not self.auto_play and self.level:
            if self.level.turn[0] > 0 and not self.level.active_player:
                self.fcounter = 0
                self.auto_play = itertools.repeat("skip-turn")

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
        self.level.add_event_listener(self.game_event)
        self.play_ctrl.level = self.level
        self.play_mctrl.level = self.level
        self.edit_mctrl.level = edit_level 
        sc = functools.partial(self.score.update_score, self.level)
        self.level.init_from_level(self.edit_level)
        lvl = self.edit_level
        grid = True
        if self.mode == "play":
            lvl = self.level
            grid = False
        self.game_window.use_level(lvl, grid=grid)
        self.level.add_event_listener(sc)
        self.level.start()

    def _show_error(self, title_msg, body_msg):
        ErrorDialog(body_msg, title_msg).open()

    def play_solution(self, *args):
        if not self.level:
            return

        self.skip_till_time_jump.value = False

        sol = self.level.get_metadata_raw("solution")
        if not sol:
            print "%s has no solution" % level.name
            return
        self.reset_level()
        print "Playing solution"
        self.auto_play = solution2actions(sol)
        self.fcounter = 0

    def new_map(self):
        self.new_lvl_d.close()
        res = self.new_lvl_d.value
        edit_level = self.edit_level
        can_rel = True
        if edit_level is None:
            can_rel = False
            edit_level = EditableLevel()

        def _compute_value(s):
            if s and (s[0] == "+" or s[0] == "-"):
                if not can_rel:
                    raise ValueError("Cannot do relative size based on non-existent map")
                return edit_level.width + int(s)
            return int(s.lstrip("="))

        try:
            width = _compute_value(res["width"].value)
            height = _compute_value(res["height"].value)
            clear = res["clear"].value
            trans = None
            if not clear:
                trans = Position(int(res["trans-width"].value),
                                 int(res["trans-height"].value))
            edit_level.new_map(width, height, translate=trans)
        except (TypeError, ValueError) as e:
            self._show_error("Cannot create map", str(e))
            return

        self.edit_level = edit_level
        self.edit_mctrl.level = edit_level
        self.game_window.use_level(edit_level, grid=True)

    def chg_edit_mode(self, mode):
        if mode != "none":
            self.edit_mctrl.brush_mode = "field-brush"
            self.edit_mctrl.field_tool = mode
        else:
            self.edit_mctrl.brush_mode = "none"

    def show_hint(self):
        if self.level:
            h = self.level.get_metadata_raw("description")
            if h is not None:
                d = ErrorDialog(h, title="Hint")
                d.open();
            else:
                d = ErrorDialog("No hint available", title="Sorry")
                d.open();

    def save_level(self, *args):
        if not self.edit_level:
            return
        d = self.edit_level.name
        sld = SelectLevelDialog("Save", "Save", "Save level", default_level=d)
        sld.connect(gui.CHANGE, self.write_level, sld)
        sld.open()

    def write_level(self, dialog):
        try:
            name = dialog.value['fname'].value
            self.edit_level.print_lvl(name)
            self.edit_level.name = name
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
        self.level.add_event_listener(self.game_event)
        self.play_ctrl.level = self.level
        self.game_window.use_level(self.level, grid=False)
        sc = functools.partial(self.score.update_score, self.level)
        self.level.add_event_listener(sc)
        self.level.start()

    def open_tutorial(self, *args):
        t = Tutorial()
        t.open()

    def loop(self):
        self.game_window.process_game_events()
        self.fcounter = (self.fcounter + 1) % 15
        if not self.fcounter:
            # 15th frame
            if self.auto_play and self.mode == "play":
                act = next(self.auto_play, None)
                if not act:
                    self.auto_play = None
                    return
                self.level.perform_move(act)
        super(Application, self).loop()

if __name__ == "__main__":
    app = Application()
    parser = argparse.ArgumentParser(description="Play ChronoShift levels")
    parser.add_argument('--play-solution', action="store_true", dest="play_solution",
                        default=False, help="Auto-play the solution")
    parser.add_argument('level', action="store", default=None, nargs="?",
                        help="The level files to check")
    args = parser.parse_args()

    if args.level:
        # Load the level - we have to wait for the init event before
        app.connect(gui.INIT, lambda *x: app.load_level(args.level), None)
        if args.play_solution:
            app.connect(gui.INIT, app.play_solution)
    if not args.play_solution:
        def _set(): # lambda statements cannot have assignments, so...
            app.skip_till_time_jump.value = True
        app.connect(gui.INIT, _set)
    app.run(delay=67) # 15 fps =~ 67 ms delay
