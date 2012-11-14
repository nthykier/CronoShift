#!/usr/bin/python

import argparse
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

from chrono.model.level import Level
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

class Application(gui.Desktop):

    def __init__(self, **params):
        super(Application, self).__init__(**params)
        self.connect(gui.QUIT, self.quit, None)

        c = gui.Container(width=640,height=480)
        spacer = 8

        self.open_lvl_d = OpenLevelDialog()
        self.open_lvl_d.connect(gui.CHANGE, self.action_open_lvl, None)

        menus = gui.Menus([
                ('File/Load', self.open_lvl_d.open, None),
                ('File/Quit', self.quit, None),
        ])
        c.add(menus, 0, 0)
        menus.rect.w, menus.rect.h = menus.resize()
        self.game_window = game_window = GameWindow()
        c.add(game_window, spacer, menus.rect.bottom + spacer)
        game_window.rect.w, game_window.rect.h = game_window.resize()

        self.widget = c

    def action_open_lvl(self,value):
        self.open_lvl_d.close()
        fname = self.open_lvl_d.value['fname']
        level = Level()
        level.load_level(fname.value)
        self.game_window.use_level(level)

app = Application()
app.run(delay=67) # 15 fps =~ 67 ms delay
