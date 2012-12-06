from pgu import gui

class ROTextArea(gui.TextArea):
    """Read-only TextArea"""

    def __init__(self, *args, **params):
        params["focusable"] = False
        super(ROTextArea, self).__init__(*args, **params)

    def event(self, e):
        if e.type == gui.KEYDOWN or e.type == gui.MOUSEBUTTONDOWN:
            # Workaround to avoid changing color when clicked on.
            # (focusable apparently does not mean a lot...)
            self.blur()
            return False
        return super(ROTextArea, self).event(e)

