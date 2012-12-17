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

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
if 1:
    # If an embedded variant of pgu is there, make it available
    dvcs = os.path.join(ROOT_DIR, "pgu-vcs")
    dver = os.path.join(ROOT_DIR, "pgu-0.18")
    if os.path.exists(dvcs):
        print "Using embedded pgu-vcs"
        if "DISABLE_PGU_WORKAROUNDS" not in os.environ:
            os.environ["DISABLE_PGU_WORKAROUNDS"] = "1"
        sys.path.insert(0, dvcs)
    elif os.path.exists(dver):
        print "Using embedded pgu (%s)" % (os.path.basename(dver))
        sys.path.insert(0, dver)

from pgu import gui

from chrono.model.campaign import JikibanCampaign
from chrono.model.field import Position
from chrono.model.level import EditableLevel, Level, solution2actions
from chrono.ctrl.controller import PlayKeyController
from chrono.ctrl.mouse_ctrl import EditMouseController, MouseController
from chrono.ctrl.diag import (MessageDialog, SelectFileDialog, NewLevelDialog,
                              simple_file_filter)
from chrono.ctrl.pgu_diag import EnhancedFileDialog
from chrono.view.game_window import GameWindow
from chrono.view.tutorial import Tutorial

LVL_FILTER = simple_file_filter(lambda x: x.endswith(".txt"))
LSF_FILTER = simple_file_filter(lambda x: x.endswith(".lsf"))

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

            self.set_text("Score: %.3f, Turn %d/%d, Time-line: %d" % nscore)

    def reset_score(self):
        self.score = (0, 1, 1, 1)

    def update_score(self, lvl, *args):
        # turn is 0-index'ed, but it is better presented as 1-index'ed.
        t = lvl.turn
        start_score = 100
        cost = lvl.score
        if cost > 449:
            result = 1.0/(cost - 449)
        elif cost:
                           #     x
                           # ---------, x in [0, 1.5k]
                           #     2k
            p = cost/500.0
            drop = (2 - p)/5.0
            result = start_score - cost * drop
        else:
            result = start_score

        self.score = (result, t[0] + 1, t[1] + 1, lvl.number_of_clones)

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
              ("goal", "coingoal", 0, 0)]

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

    from_left += hint.rect.w + spacer

    play_s = gui.Button("Play Solution")
    play_s.connect(gui.CLICK, app.play_solution, None)
    c.add(play_s, from_left, from_top)
    play_s.rect.w, play_s.rect.h = play_s.resize()

    from_left = spacer
    from_top += play_s.rect.h + spacer

    l = gui.Label("Auto finish time-jump: ")
    c.add(l, from_left, from_top)
    l.rect.w, l.rect.h = l.resize()

    from_left += l.rect.w + spacer

    cbox = app.skip_till_time_jump
    c.add(cbox, from_left, from_top)
    cbox.rect.w, cbox.rect.h = cbox.resize()

    from_left += cbox.rect.w + spacer

    sl = gui.Label("Disable audio: ")
    c.add(sl, from_left, from_top)
    sl.rect.w, sl.rect.h = sl.resize()

    from_left += sl.rect.w + spacer

    mcb = gui.Switch(value=app.muted)
    def _toggle_sounds():
        app.muted = mcb.value
        if app.muted:
            pygame.mixer.stop()
        else:
            app.play_sound("background", loops = -1, volume = 1.0/3)

    mcb.connect(gui.CHANGE, _toggle_sounds)
    c.add(mcb, from_left, from_top)
    mcb.rect.w, mcb.rect.h = mcb.resize()

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

        self._audio = {}
        self.muted = False

        self._mode = "play"
        self._game_state = "stopped"
        self._finish_event = None
        self.campaign = JikibanCampaign()
        self.campaign_lvl_no = -1
        self.fcounter = 0
        self.score = ScoreTracker()
        self.edit_level = None
        self.level = None
        self.auto_play = None
        self.group = None
        self.skip_till_time_jump = gui.Switch(value=False)
        self.skip_till_time_jump.connect(gui.CHANGE, self.toggle_auto_finish)
        self.game_window = GameWindow(resource_dirs=[ROOT_DIR])
        self.ctrl_widget = self.widget
        self.ctrl_widget.game_window = self.game_window
        self.play_ctrl = PlayKeyController(view=self.game_window)
        self.play_mctrl = MouseController(self.game_window)
        self.edit_ctrl = None
        self.edit_mctrl = EditMouseController(self.game_window)

        level_dir  = os.path.join(ROOT_DIR, "levels")
        self.open_campaign_d = EnhancedFileDialog(title_txt="Start Campaign",
                                                  button_txt="Start Campaign",
                                                  path=level_dir,
                                                  path_filter=LSF_FILTER)
        self.open_lvl_d = EnhancedFileDialog(title_txt="Play Level",
                                             button_txt="Play",
                                             path=level_dir,
                                             path_filter=LVL_FILTER)
        self.new_lvl_d = NewLevelDialog()
        self.open_campaign_d.connect(gui.CHANGE, self.load_campaign_action)
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
        self._audio["time-paradox"]  = pygame.mixer.Sound("sound/123921__silencer1337__machinefail.wav")
        self._audio["game-complete"] = pygame.mixer.Sound("sound/90138__pierrecartoons1979__win1.wav")
        self._audio["background"] = pygame.mixer.Sound("sound/POL-sand-and-water-short_repeat.wav")

        self.play_sound("background", loops = -1, volume = 1.0/3)

        menus = gui.Menus([
                ('File/Load campaign', self.open_campaign_d.open, None),
                ('File/Load level', self.open_lvl_d.open, None),
                ('File/Quit', self.quit, None),
                ('Fun/Change theme', self.change_theme, None),
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

        self.group = gui.Group(name='ctrl-mode', value=self._mode)

        print "Mode: %s" % self._mode

        play_mode = gui.Tool(self.group, gui.Label("Play-mode"), "play")
        edit_mode = gui.Tool(self.group, gui.Label("Edit-mode"), "edit")

        c.add(play_mode, spacer, from_top)
        play_mode.rect.w, play_mode.rect.h = play_mode.resize()

        c.add(edit_mode, 2 * spacer + play_mode.rect.w, from_top)
        edit_mode.rect.w, edit_mode.rect.h = edit_mode.resize()

        from_top += play_mode.rect.h + spacer

        # edit-mode has no key ctrl, so always init this to play_ctrl
        self.ctrl_widget.key_ctrl = self.play_ctrl

        if app.mode == "play":
            w = gui.ScrollArea(play_ctrls)
            self.ctrl_widget.mouse_ctrl = self.play_mctrl
            self.ctrl_widget.mouse_ctrl.active = True
        else:
            w = gui.ScrollArea(edit_ctrls)
            self.ctrl_widget.mouse_ctrl = self.edit_mctrl
            self.ctrl_widget.mouse_ctrl.active = True


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
        if self.group:
            self.group.value = val
        else:
            self._mode = val

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
        self.load_level(self.open_lvl_d.value)

    def next_level(self):
        if self.campaign_lvl_no != -1:
            self.campaign_lvl_no += 1
            if self.campaign_lvl_no < len(self.campaign):
                self.load_level(self.campaign[self.campaign_lvl_no])

    def game_event(self, ge):
        if (ge.event_type != "time-jump" and ge.event_type != "end-of-turn" and
              ge.event_type != "game-complete" and ge.event_type != "time-paradox"):
            return

        # FIXME: If the player types fast (i.e. "enqueues a lot of
        # moves", we will receive these events _waaaaay_ ahead of the
        # animation.  Generally we are here before the animation triggering
        # this event has even started (sort of okay for time-paradox)
        if ge.event_type == "game-complete":
            self._game_state = "complete"
            self._finish_event = ge
        elif ge.event_type == "time-paradox":
            self._game_state = "time-paradox"
            self._finish_event = ge

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

    def load_campaign_action(self):
        return self.load_campaign(self.open_campaign_d.value)

    def load_campaign(self, fname):
        self.auto_play = None
        campaign = JikibanCampaign()
        try:
            campaign.load_campaign(fname)
        except IOError as e:
            self._show_error(str(e), "Cannot load campaign")
            return
        if len(campaign) < 1:
            self._show_error("The campaign does not have any levels in it",
                             "Empty campaign")
            return

        self.campaign = campaign
        self.campaign_lvl_no = 0
        self.load_level(campaign[0])

    def load_level(self, fname):
        self.auto_play = None
        edit_level = EditableLevel()
        try:
            edit_level.load_level(fname)
        except IOError as e:
            self._show_error(str(e), "Cannot load map")
            return

        self._game_state = "stopped"
        self.edit_level = edit_level
        self.level = Level()
        self.level.add_event_listener(self.game_event)
        self.play_ctrl.level = self.level
        self.play_ctrl.edit_level = edit_level
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
        self._game_state = "running"
        self.level.start()

    def _show_error(self, body_msg, title_msg):
        MessageDialog(body_msg, title_msg).open()

    def play_solution(self, *args):
        if not self.level:
            return

        self.skip_till_time_jump.value = False

        sol = self.level.get_metadata_raw("solution")
        if not sol:
            msg = "Solution for %s is not available" % self.level.name
            self._show_error(msg, "No solution available!")
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
        trans = None

        if edit_level is None:
            can_rel = False
            edit_level = EditableLevel()

        def _compute_value(name, s):
            res = 0
            if s and (s[0] == "+" or s[0] == "-" or s == "0"):
                # +x or -x or 0 is assumed to be relative (the latter being
                # short for "+0")
                if not can_rel:
                    raise ValueError("Cannot do relative size based on non-existent map: %s=%s" \
                                         % (name, s))
                if name == "width":
                    return edit_level.width + int(s)
                return edit_level.height + int(s)
            else:
                return int(s.lstrip("="))

        try:
            width = _compute_value("width", res["width"].value)
            height = _compute_value("height", res["height"].value)
            clear = res["clear"].value
            if not clear:
                trans = Position(int(res["trans-width"].value),
                                 int(res["trans-height"].value))
        except (TypeError, ValueError) as e:
            self._show_error(str(e), "Cannot create map")
            return

        edit_level.new_map(width, height, translate=trans)

        self.edit_level = edit_level
        self.play_ctrl.edit_level = edit_level
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
                d = MessageDialog(h, title="Hint")
                d.open();
            else:
                d = MessageDialog("No hint available", title="Sorry")
                d.open();

    def save_level(self, *args):
        if not self.edit_level:
            return
        d = self.edit_level.name
        # Keep SelectFileDialog here because that dialog makes it
        # easier to reuse the file name (which is a way of making
        # the lack of "save" vs "save as" less painful).
        sld = SelectFileDialog("Save", "Save", "Save level", default_file=d,
                               path_filter=LVL_FILTER)
        sld.connect(gui.CHANGE, self.write_level, sld)
        sld.open()

    def write_level(self, dialog):
        try:
            name = dialog.value['fname'].value
            self.edit_level.print_lvl(name)
            self.edit_level.name = name
            MessageDialog("Saved level to %s" % os.path.basename(name),
                          "Level saved").open()
        except IOError as e:
            self._show_error(str(e), "Cannot save map")

    def play_edit_level(self, *args):
        if not self.edit_level:
            return
        level = Level()
        try:
            level.init_from_level(self.edit_level)
        except ValueError as e:
            self._show_error(str(e), "Cannot play map")
            return
        self.mode = "play"
        self._game_state = "stopped"
        self._finish_event = None
        self.level = level
        self.level.add_event_listener(self.game_event)
        self.play_ctrl.level = self.level
        self.game_window.use_level(self.level, grid=False)
        sc = functools.partial(self.score.update_score, self.level)
        self.level.add_event_listener(sc)
        self._game_state = "running"
        self.level.start()

    def play_sound(self, sound, loops = 0, volume = 1):
        if sound not in self._audio:
            # Emit this even if we are muted (for error finding)
            print "W: Unknown sound %s" % sound
            return
        if self.muted:
            return
        self._audio[sound].set_volume(volume)
        self._audio[sound].play(loops)

    def open_tutorial(self, *args):
        t = Tutorial()
        t.open()

    def loop(self):
        self.game_window.process_game_events()
        if not self.game_window.pending_animation:
            # No pending animation - is the game finished?
            if self._game_state == "complete":
                self._game_state = "stopped" # do this only once!
                self._finish_event = None
                print "Your score is: %d" % self.level.score
                self.play_sound("game-complete")
                self.auto_play = None
                self._finish_event = None
                self.next_level()
            elif self._game_state == "time-paradox":
                ge = self._finish_event
                self._finish_event = None
                self._game_state = "stopped" # do this only once!
                self.play_sound("time-paradox")
                self.auto_play = None
                self._show_error(ge.reason, "Time paradox or non-determinism")

            # The fcounter is to give a slight delay to auto-playing
            # (else every move happens as fast as possible...)
            self.fcounter = (self.fcounter + 1) % 4
            if not self.fcounter:
                if self.auto_play and self.mode == "play":
                    act = next(self.auto_play, None)
                    if not act:
                        self.auto_play = None
                    else:
                        self.level.perform_move(act)
        else:
            self.fcounter = 0
        super(Application, self).loop()

    def change_theme(self, *args):
        theme = self.game_window.tileset
        if theme == "tileset":
            theme = "snowytileset"
        else:
            theme = "tileset"
        self.game_window.tileset = theme

if __name__ == "__main__":
    def_campaign = os.path.join(ROOT_DIR, "levels", "campaign.lsf")
    app = Application()
    parser = argparse.ArgumentParser(description="Play ChronoShift levels")
    parser.add_argument('--play-solution', action="store_true", dest="play_solution",
                        default=False, help="Auto-play the solution (level-only)")
    parser.add_argument('--muted', action="store_true", default=False,
                        help="Disable sounds")
    parser.add_argument('--editor', action="store_true", default=False,
                        help="Start up in editor mode")

    parser.add_argument('level', action="store", default=def_campaign, nargs="?",
                        help="The level or campaign to play")
    args = parser.parse_args()

    app.muted = args.muted
    if args.editor:
        app.mode = "edit"
    else:
        app.mode = "play"

    if args.level:
        # Load the level - we have to wait for the init event before
        if args.level.endswith(".lsf"):
            app.connect(gui.INIT, lambda *x: app.load_campaign(args.level))
        else:
            app.connect(gui.INIT, lambda *x: app.load_level(args.level), None)
        if args.play_solution:
            app.connect(gui.INIT, app.play_solution)
    if not args.play_solution:
        def _set(): # lambda statements cannot have assignments, so...
            app.skip_till_time_jump.value = True
        app.connect(gui.INIT, _set)
    app.run(delay=67) # 15 fps =~ 67 ms delay
