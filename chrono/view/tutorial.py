from textwrap import dedent

from pgu import gui

from chrono.view.text import ROTextArea

CTRL_TUTORIAL = dedent("""\
Actions:
 * move around (default: the arrow keys or "wasd")
 * "do nothing" (default: Space)
 * enter the time machine (default: Enter)
   - Can only be done on top of the time machine (start)
 * "F2" can be used to save your current moves to a file.
   - It can also be used to set the solution for the
     current level (see the editor help for more info).

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

EDITOR_TUTORIAL = dedent("""\
It is possible to create your own levels by accessing the
editor.  Choose "Edit-mode" to enter the editor.

"New/Resize Map" can be used to create a new "empty" map or
resize the current one.  Resizing can be done with "relative"
sizes by prefixing them with "+" or "-".  A size of "0" is
also assumed to be relative (and means "keep current size").

"Play level" can be used to play the level in its current
state.  It is useful for play testing and can also be used
to record the solution.  Simply play the level to completion,
hit "F2" and pick "Solution".

"Save level" saves the level to a file.

Below the 3 named buttons are a series of buttons.  These
are "brush" modes that can be used to insert the given field.
Click the type of field you want to insert and you can start
to "paint" that kind of field on the map.

NB: Some fields are "singletons" (e.g. the goal field).
Attempting to paint a second of those fields results in the
first one disappearing.

Finally, it is possibly to connect fields and alter starting
states.  To do this, make sure that the "none" brush is
selected.  Then right-click on the field you want to change
or connect.
  Once selected, it will be hilighted in green and hilighting
is locked on to that field (and its related ones if any).  Now
you can left-click on the field itself to change it starting
state (if the field supports it) or left-click on another field
to connect them (if those two fields can be connected).

Buttons can connect to gates and gates are (at the time of
writing) the only field with different starting states.

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
            ("Editor", "editor", EDITOR_TUTORIAL),
        ]

        for tlabel, key, text in tlist:
            tut = ROTextArea(value=text, compute_size=1, min_size=(width, height))
            tool = gui.Tool(self.group, gui.Label(tlabel), key)
            tutorials[key] = tut
            t.td(tool)
            tool.rect.w, tool.rect.h = tool.resize()

        t.tr()
        # Set the first page as active...
        self.group.value = tlist[0][1]
        w = gui.ScrollArea(tutorials[tlist[0][1]],
                           width=width, height=height)
        t.td(w, colspan=len(tutorials))

        def switch_tutorial():
            w.clear()
            w.widget = tutorials[self.group.value]
            w.set_vertical_scroll(0)
            w.resize()

        self.group.connect(gui.CHANGE, switch_tutorial)

        t.tr()
        cl = gui.Button("Close")
        t.td(cl, col=len(tutorials)-1)
        cl.connect(gui.CLICK, self.close)

        self.body = t
        t.resize()
        super(Tutorial, self).__init__(self.title, self.body)

