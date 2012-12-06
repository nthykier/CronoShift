from textwrap import dedent

from pgu import gui

from chrono.view.text import ROTextArea

CTRL_TUTORIAL = dedent("""\
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

RULES_TUTORIAL = dedent("""\
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

WORLD_TUTORIAL = dedent("""\
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

class Tutorial(gui.Dialog):

    def __init__(self, **params):
        self.title = gui.Label("Tutorial")
        self.group = gui.Group(name="page", value="")
        width, height = (500, 300)
        t = gui.Table()
        t.tr()
        tutorials = {}
        tlist = [
            ("Controls", "ctrl", CTRL_TUTORIAL),
            ("Rules", "rules", RULES_TUTORIAL),
            ("World", "world", WORLD_TUTORIAL),
        ]

        for tlabel, key, text in tlist:
            tut = ROTextArea(value=text, width=width, height=height)
            tool = gui.Tool(self.group, gui.Label(tlabel), key)
            tutorials[key] = tut
            t.td(tool)
            tool.rect.w, tool.rect.h = tool.resize()

        t.tr()
        # add scroll area with a dummy element (will be replaced)
        # below
        w = gui.ScrollArea(gui.Label("placeholder"))
        t.td(w, colspan=len(tutorials))

        def switch_tutorial():
            w.widget = tutorials[self.group.value]

        self.group.connect(gui.CHANGE, switch_tutorial)
        # Set the first page as active...
        self.group.value = tlist[0][1]

        t.tr()
        cl = gui.Button("Close")
        t.td(cl, col=len(tutorials)-1)
        cl.connect(gui.CLICK, self.close)

        self.body = t
        t.resize()
        super(Tutorial, self).__init__(self.title, self.body)

