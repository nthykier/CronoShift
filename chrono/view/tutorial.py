from textwrap import dedent

from pgu import gui

class ROTextArea(gui.TextArea):
    """Read-only TextArea"""

    def event(self, e):
        if e.type == gui.KEYDOWN:
            return False
        return super(ROTextArea, self).event(e)

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
    return ROTextArea(value=msg, width=width, height=height)

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
    return ROTextArea(value=msg, width=width, height=height)

def make_world_tutorial(width, height):
    msg = dedent("""\
Some fields (e.g. buttons) react to being "stepped on"
and will trigger other fields (e.g. open/close a gate).

Multiple buttons can control the same gate.  Every 2
button will cancel out each other.  The same button
can also control multiple gates.

Crates can be pushed around like in Sokoban.  That is,
you can push a crate by walking into it.  This will
push it in the same direction as you walked.  The crate
must be able to enter the field it is being pushed onto.

Crates can be used to activate fields by pushing it onto
the field.
""")
    return ROTextArea(value=msg, width=width, height=height)

class Tutorial(gui.Dialog):

    def __init__(self, **params):
        self.title = gui.Label("Tutorial")
        self.group = gui.Group(name="page", value="ctrl")
        from_left = from_top = spacer = 8
        width, height = (500, 300)
        t = gui.Table()
        t.tr()
        tutorials = {}

        ctrl_tut = make_ctrl_tutorial(width, height)
        ctrl_tool = gui.Tool(self.group, gui.Label("Controls"), "ctrl")
        tutorials['ctrl'] = ctrl_tut

        t.td(ctrl_tool)
        ctrl_tool.rect.w, ctrl_tool.rect.h = ctrl_tool.resize()

        from_left += spacer + ctrl_tool.rect.w

        rules_tut = make_rules_tutorial(width, height)
        rules_tool = gui.Tool(self.group, gui.Label("Rules"), "rules")
        tutorials['rules'] = rules_tut

        t.td(rules_tool)
        rules_tool.rect.w, rules_tool.rect.h = rules_tool.resize()

        from_left += spacer + rules_tool.rect.w

        world_tut = make_world_tutorial(width, height)
        world_tool = gui.Tool(self.group, gui.Label("World"), "world")
        tutorials['world'] = world_tut

        t.td(world_tool)
        world_tool.rect.w, world_tool.rect.h = world_tool.resize()

        from_top += spacer + world_tool.rect.h

        t.tr()
        w = gui.ScrollArea(ctrl_tut)
        t.td(w, colspan=len(tutorials))

        def switch_tutorial():
            w.widget = tutorials[self.group.value]

        self.group.connect(gui.CHANGE, switch_tutorial)

        t.tr()
        cl = gui.Button("Close")
        t.td(cl, col=len(tutorials)-1)
        cl.connect(gui.CLICK, self.close)

        self.body = t
        t.resize()
        super(Tutorial, self).__init__(self.title, self.body)
