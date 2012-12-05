from textwrap import dedent

from pgu import gui

def _make_text_box(width, height, text):
    c = gui.Container(width=width, height=height)
    spacer = 8
    from_top = spacer

    for line in text.split("\n"):
        ll = gui.Label(line)
        c.add(ll, spacer, from_top)
        ll.rect.w, ll.rect.h = ll.resize()
        from_top += ll.rect.h

    return c

def make_ctrl_tutorial(width, height):
    msg = dedent("""\
Actions:
 * move around (default: the arrow keys or "wasd")
 * "do nothing" (default: Space)
 * enter the time machine (default: Enter)
   - Can only be done on top of the time machine (start)

When the mouse hovers over a field, it will hilight that
field and fields that is "connected" to that field (if any).
(e.g. when hovering over a gate, the button(s) activating
the gate will be hilighted).
""")
    return _make_text_box(width, height, msg)

def make_rules_tutorial(width, height):
    msg = dedent("""\
To win:
 * You must obtain the goal (gold coin).
 * You must always return to start.
 * Your solution must be determistic.

The source of non-determinism occurs from performing
two actions in the same turn that:
 * both appear to be a legal/valid move.
 * when performed simultaniously cause a contradiction.

Examples include:
 * Ending a turn in a closed gate.
 * Causing temporal paradoxes ("time-paradox").

""")
    return _make_text_box(width, height, msg)

class Tutorial(gui.Dialog):

    def __init__(self, **params):
        self.title = gui.Label("Tutorial")
        self.group = gui.Group(name="page", value="ctrl")
        from_left = from_top = spacer = 8
        width, height = (300, 300)
        c = gui.Container()
        tutorials = {}

        ctrl_tut = make_ctrl_tutorial(width, height)
        ctrl_tool = gui.Tool(self.group, gui.Label("Controls"), "ctrl")
        tutorials['ctrl'] = ctrl_tut

        c.add(ctrl_tool, from_left, from_top)
        ctrl_tool.rect.w, ctrl_tool.rect.h = ctrl_tool.resize()

        from_left += spacer + ctrl_tool.rect.w

        rules_tut = make_rules_tutorial(width, height)
        rules_tool = gui.Tool(self.group, gui.Label("Rules"), "rules")
        tutorials['rules'] = rules_tut

        c.add(rules_tool, from_left, from_top)
        rules_tool.rect.w, rules_tool.rect.h = rules_tool.resize()

        from_top += spacer + rules_tool.rect.h

        w = gui.ScrollArea(ctrl_tut)
        c.add(w, spacer, from_top)

        def switch_tutorial():
            w.widget = tutorials[self.group.value]

        self.group.connect(gui.CHANGE, switch_tutorial)

        self.body = c
        c.resize()
        super(Tutorial, self).__init__(self.title, self.body)
