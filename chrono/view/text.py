from pgu import gui

class ROTextArea(gui.TextArea):
    """Read-only TextArea"""

    def __init__(self, *args, **params):
        params["focusable"] = False
        super(ROTextArea, self).__init__(*args, **params)
        if params.get('compute_size', 0):
            text = self.value
            font = self.font
            w, h = (0, 0)
            min_size = params.get('min_size', (0, 0))
            # Compute the proper size for this text...
            for line in text.split("\n"):
                nw, nh = font.size(line)
                w = max(nw, w)
                h += nh
            # add height for an extra line.  Not sure if the font.size
            # ought to be multiplied with (e.g.) 1.1 or the code above
            # is just "off-by-one-height".  Anyhow, this fixes a hidden
            # line in the Editor tutorial, so \o/
            h += nh
            w = max(w, min_size[0])
            h = max(h, min_size[1])
            self.resize(width=w, height=h)

    def event(self, e):
        if e.type == gui.KEYDOWN or e.type == gui.MOUSEBUTTONDOWN:
            # Workaround to avoid changing color when clicked on.
            # (focusable apparently does not mean a lot...)
            self.blur()
            return False
        return super(ROTextArea, self).event(e)

    def resize(self, width=None, height=None):
        # Default resizing is made of utter fail for TextArea...
        if width is not None:
            self.style.width = width
            self.rect.w = width
        if height is not None:
            self.style.height = height
            self.rect.h = height
        return super(ROTextArea, self).resize(width=width, height=height)
