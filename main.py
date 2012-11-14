#!/usr/bin/python

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

from chrono.model.level import Level, solution2actions
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


class Application(gui.Desktop):

    def __init__(self, **params):
        super(Application, self).__init__(**params)
        self.connect(gui.QUIT, self.quit, None)

        c = gui.Container(width=640,height=480)
        spacer = 8
        from_top = 0

        self.fcounter = 0
        self.score = ScoreTracker()
        self.level = None
        self.auto_play = None
        self.open_lvl_d = OpenLevelDialog()
        self.open_lvl_d.connect(gui.CHANGE, self.action_open_lvl, None)

        menus = gui.Menus([
                ('File/Load', self.open_lvl_d.open, None),
                ('File/Quit', self.quit, None),
        ])
        c.add(menus, 0, from_top)
        menus.rect.w, menus.rect.h = menus.resize()
        from_top += menus.rect.h + spacer

        self.game_window = game_window = GameWindow()
        c.add(game_window, spacer, from_top)
        game_window.rect.w, game_window.rect.h = game_window.resize()

        from_top += game_window.rect.h + spacer

        c.add(self.score, spacer, from_top)
        self.score.rect.w, self.score.rect.h = self.score.resize()
        from_top += self.score.rect.h + spacer

        play_s = gui.Button("Play Solution")
        play_s.connect(gui.CLICK, self.play_solution, None)
        c.add(play_s, spacer, from_top)

        self.widget = c

    def action_open_lvl(self,value):
        self.open_lvl_d.close()
        self.load_level(self.open_lvl_d.value['fname'].value)

    def load_level(self, fname):
        self.level = Level()
        sc = functools.partial(self.score.update_score, self.level)
        self.level.load_level(fname)
        self.level.add_event_listener(sc)
        self.game_window.use_level(self.level)

    def play_solution(self, *args):
        if not self.level:
            return

        sol = self.level.get_metadata_raw("solution")
        if not sol:
            print "%s has no solution" % level.name
            return
        # FIXME: reset
        print "Playing solution"
        self.auto_play = solution2actions(sol)

    def event(self, evt):
        if self.game_window.event(evt):
            self.game_window.focus()
            return
        super(Application, self).event(evt)

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
