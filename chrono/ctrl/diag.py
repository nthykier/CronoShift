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

import functools
import os

from pgu import gui

from chrono.ctrl.pgu_diag import EnhancedFileDialog

def simple_file_filter(f):
    """Create a filter that only filters out files

    Returns a new filter function that accepts all dirs and
    any file that the given function accepts.
    """
    def filt(f, x):
        return os.path.isdir(x) or f(x)

    return functools.partial(filt, f)

class MessageDialog(gui.Dialog):
    def __init__(self, msg, title):
        self.title = gui.Label(title)
        self.body = gui.Table()
        button_ok = gui.Button("Ok")
        # Handle multiple messages (works only because the text is
        # not changed)
        for line in msg.split("\n"):
            self.body.tr()
            self.body.td(gui.Label(line))
        self.body.tr()
        self.body.td(button_ok)
        button_ok.connect(gui.CLICK, self.close)

        super(MessageDialog, self).__init__(self.title, self.body)

class ConfirmDialog(gui.Dialog):

    def __init__(self, msg, title="Are you certain?"):
        self.title = gui.Label(title)
        self.body = gui.Table()
        button_ok = gui.Button("Confirm")
        button_no = gui.Button("Cancel")
        # Handle multiple messages (works only because the text is
        # not changed)
        # - colspan + col is used to set the buttons (approximately)
        #   in the middle
        for line in msg.split("\n"):
            self.body.tr()
            self.body.td(gui.Label(line), colspan=8)
        self.body.tr()
        self.body.td(button_ok, col=3)
        self.body.td(button_no, col=4)
        button_no.connect(gui.CLICK, self.close)
        button_ok.connect(gui.CLICK, self._confirm)

        super(ConfirmDialog, self).__init__(self.title, self.body)

    def _confirm(self, *args):
        self.send(gui.CHANGE)
        self.close()

class SelectFileDialog(gui.Dialog):
    def __init__(self, text, confirm_text, title, path_filter=None, **params):
        title = gui.Label(title)

        t = gui.Table()

        self.path_filter = path_filter
        self.value = gui.Form()
        self.li = gui.Input(name="fname")
        d = params.get('default_file', None)
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
        path = None
        if self.li.value:
            f = self.li.value
            if os.path.isdir(f):
                path =f
            else:
                path = os.path.dirname(f)
        d = EnhancedFileDialog(path=path, path_filter=self.path_filter)
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

class OptionsDialog(gui.Dialog):
    """A simple "options" dialog presenting the user with a set of options

    Example:

      options = [
          # label,    action value
          ("Pikachu", "pikachu"),
          ("Charmander", "charmander"),
          ("Squirtle", "squirtle"),
          ("Bulbasaur", "bulbasaur"),
      ]
      msg = "Pick which pokemon you want to call in"
      odiag = OptionsDialog(msg, "Choose a Pokemon", options, self._pokemon)
      odiag.open()

    If the action value is None, the button is assumed to be a
    "Cancel" button.  In this case, the handler will /not/ be called
    (the dialog will simply just close when the button is clicked).
    All buttons must have a label (except if the action value is None,
    then the label will default to "Cancel".

    Buttons will added in the order they appear (from left to right).

    If the handler is None, the actions are assumed to be callables and
    will be invoked with no arguments (functools.partial may be useful
    here).
    """

    def __init__(self, msg, title, options, handler=None, **params):
        self.title = gui.Label(title)
        self.body = gui.Table()
        self.handler = handler

        cols = max(len(options), 8)
        col_no = 0
        if len(options) < cols:
            # Put buttons in the middle
            #  (8 - 5) // 2 = 1 (use col 1, 2, .., 6)
            col_no = (cols - len(options)) // 2

        for line in msg.split("\n"):
            self.body.tr()
            self.body.td(gui.Label(line), colspan=cols)

        self.body.tr()

        for label, action in options:
            l = label
            if label is None and action is None:
                label = "Cancel"
            elif label is None:
                raise TypeError("Label missing")
            but = gui.Button(label)
            if action is not None:
                but.connect(gui.CLICK, self._click, action)
            else:
                but.connect(gui.CLICK, self.close)
            self.body.td(but, col=col_no)
            col_no += 1

        super(OptionsDialog, self).__init__(self.title, self.body)

    def _click(self, action):
        if self.handler is None:
            action()
        else:
            self.handler(action)
        self.close()
