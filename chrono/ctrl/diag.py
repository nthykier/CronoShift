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
        for line in msg.split("\n"):
            self.body.tr()
            self.body.td(gui.Label(line))
        self.body.tr()
        self.body.td(button_ok)
        self.body.td(button_no)
        button_no.connect(gui.CLICK, self.close)
        button_ok.connect(gui.CLICK, self._confirm)

        super(ConfirmDialog, self).__init__(self.title, self.body)

    def _confirm(self, *args):
        self.send(gui.CHANGE)
        self.close()
