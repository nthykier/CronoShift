"""
This file contains a copy-waste of the "FileDialog" from pgu(-0.18).
It is therefore same copyright / license as the original content
 (pgu/gui/dialog.py)

Changes are copyright: 2012, Niels Thykier <niels@thykier.net>
And may be distributed under the same terms as pgu (LGPL-2.1)

"""

import os

from pgu import gui
import pgu.gui.pguglobals as pgug

class EnhancedFileDialog(gui.Dialog):
    """An enhanced variant of the PGU 0.18 FileDialog


    Mostly copy-waste from the original "FileDialog" class
    """

    def __init__(self, title_txt="File Browser", button_txt="Okay",
                 path=None, filter_func=None, cls="dialog"):
        """EnhancedFileDialog constructor

        Keyword arguments:
            title_txt -- Set the title
            button_txt -- Set the "confirm" button text
            path -- initial directory (defaults to os.getcwd())
            filter_func -- filter function to hide some elements.
                           Only accepted files/dirs are listed (and "..")

        """
        self.filter_func = filter_func
        cls1 = "filedialog"
        if not path:
            self.curdir = os.getcwd()
        else:
            self.curdir = path
        self.dir_img = gui.Image(
            pgug.app.theme.get(cls1+".folder", "", 'image'))
        td_style = {'padding_left': 4,
                    'padding_right': 4,
                    'padding_top': 2,
                    'padding_bottom': 2}
        self.title = gui.Label(title_txt, cls=cls+".title.label")
        self.body = gui.Table()
        self.list = gui.List(width=350, height=150)
        self.input_dir = gui.Input()
        self.input_file = gui.Input()
        self._list_dir()
        self.button_ok = gui.Button(button_txt)
        button_cancel = gui.Button("Cancel")
        self.body.tr()
        self.body.td(gui.Label("Folder"), style=td_style, align=-1)
        self.body.td(self.input_dir, style=td_style)
        self.body.tr()
        self.body.td(self.list, colspan=5, style=td_style)
        self.list.connect(gui.CHANGE, self._item_select_changed)
        self.button_ok.connect(gui.CLICK, self._button_okay_clicked)
        button_cancel.connect(gui.CLICK, self.close)
        self.body.tr()
        self.body.td(gui.Label("File"), style=td_style, align=-1)
        self.body.td(self.input_file, style=td_style)
        self.body.td(self.button_ok, style=td_style)
        self.body.td(button_cancel, style=td_style)
        self.value = None
        super(EnhancedFileDialog, self).__init__(self.title, self.body)

    def _list_dir(self):
        self.input_dir.value = self.curdir
        self.input_dir.pos = len(self.curdir)
        self.input_dir.vpos = 0
        dirs = []
        files = []
        try:
            contents = os.listdir(self.curdir)
            filt = self.filter_func
            for i in contents:
                fullpath = os.path.join(self.curdir, i)
                if filt and not filt:
                    continue
                if os.path.isdir(fullpath):
                    dirs.append(i)
                else:
                    files.append(i)
        except:
            self.input_file.value = "Cannot read contents of %s" % self.curdir 

        self.list.add("..", image=self.dir_img, value="..")
        dirs.sort()
        
        files.sort()
        for i in dirs:
            self.list.add(i,image=self.dir_img,value=i)
        for i in files:
            self.list.add(i,value=i)
        self.list.set_vertical_scroll(0)


    def _item_select_changed(self):
        self.input_file.value = self.list.value
        fname = os.path.abspath(os.path.join(self.curdir, self.input_file.value))
        if os.path.isdir(fname):
            self.input_file.value = ""
            self.curdir = fname
            self.list.clear()
            self._list_dir()


    def _button_okay_clicked(self):
        if self.input_dir.value != self.curdir:
            if os.path.isdir(self.input_dir.value):
                self.input_file.value = ""
                self.curdir = os.path.abspath(self.input_dir.value)
                self.list.clear()
                self._list_dir()
        else:
            self.value = os.path.join(self.curdir, self.input_file.value)
            self.send(gui.CHANGE)
            self.close()
