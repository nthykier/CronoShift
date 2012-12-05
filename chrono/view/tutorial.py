from textwrap import dedent

from pgu import gui

def make_ctrl_tutorial(width, height):
    c = gui.Container(width=width, height=height)
    spacer = 8
    from_top = spacer

    msg = dedent("""\
Actions:
 * move around (default: the arrow keys or "wasd")
 * "do nothing" (default: Space)
 * enter the time machine (default: Enter)
   - Can only be done on top of the time machine (start)

""")


    for line in msg.split("\n"):
        ll = gui.Label(line)
        c.add(ll, spacer, from_top)
        ll.rect.w, ll.rect.h = ll.resize()
        from_top += ll.rect.h

    return c

class Tutorial(gui.Dialog):

    def __init__(self, **params):
        self.title = gui.Label("Tutorial")
        width, height = (300, 300)
        ctrl_tut = make_ctrl_tutorial(width, height)

        w = gui.ScrollArea(ctrl_tut)

        self.body = w
        super(Tutorial, self).__init__(self.title, self.body)
