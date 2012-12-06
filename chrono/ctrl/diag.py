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

from pgu import gui

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


