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

from collections import deque
import functools
from itertools import (imap, ifilter, chain, izip, takewhile, product,
                       starmap)
from operator import attrgetter
import re

from chrono.model.direction import Direction
from chrono.model.moveable import PlayerClone, Crate
from chrono.model.field import (parse_field, Position, Wall, Field, Gate, Button,
                                StartLocation, GoalLocation)

ACTITVATION_REGEX = re.compile(
  r'^button\s+\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*->\s*(\S+)\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*$'
)

def solution2actions(sol, naive_replay=True):
    """Transform a solution in "solution format" to actions

    @param sol The solution in the "solution format".  Spaces and periods
    are ignored.
    @param naive_replay Assume that the consumer of the solution is just
    naively proccessing the reply and insert "skip-turn"s as needed for
    jumps to finish.
    @return An iterable sequence of actions.
    """

    space = lambda x: not x[0].isspace() and x[0] != "."
    def _s2actions(x):
        if x == "N": return "move-up"
        if x == "E": return "move-right"
        if x == "S": return "move-down"
        if x == "W": return "move-left"
        if x == "H": return "skip-turn"
        if x == "T": return "enter-time-machine"
        raise ValueError("Unknown command %s" % x)

    turn_gen = imap(_s2actions, ifilter(space, sol))
    if not naive_replay:
        return turn_gen
    def _gen_robust_solution(gen):
        """Generates a more robust solution

        It inserts "fake" skip-turn actions into the solution to ensure
        even naive replayers will play the solution correctly.
        """
        cl = 0
        ml = 0
        for act in gen:
            cl += 1
            yield act
            if act == "enter-time-machine":
                while cl < ml:
                    cl += 1
                    yield "skip-turn"
                if cl > ml:
                    ml = cl
                cl = 0

    return _gen_robust_solution(turn_gen)

def _line_reader(fd):
    it = iter(fd)
    for line in fd:
        line = line.rstrip("\r\n")
        if line != "" and line.strip() == "":
            raise IOError("White-space only line (%s:%d)" % (fname, lineno))
        yield line

class GameError(Exception):
    pass

class UnsolvableError(GameError):
    pass

class TimeParadoxError(UnsolvableError):
    pass

class GameEvent(object):
    def __init__(self, event_type, source=None, success=True):
        self._event_type = event_type
        self._source = source
        self._success = success

    @property
    def event_type(self):
        return self._event_type

    @property
    def source(self):
        return self._source

    @property
    def success(self):
        return self._success

class EditorEvent(object):
    def __init__(self, event_type, source=None, target=None):
        self._event_type = event_type
        self._source = source
        self._target = target

    @property
    def event_type(self):
        return self._event_type

    @property
    def source(self):
        return self._source

    @property
    def target(self):
        return self._target

class BaseLevel(object):

    def __init__(self):
        self._name = None
        self._width = 0
        self._height = 0
        self._lvl = []
        self._metadata = {}
        self._start_location = None
        self._goal_location = None
        self._handlers = set()

        self._crates = {}

    @property
    def name(self):
        return self._name

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def start_location(self):
        return self._start_location

    @property
    def goal_location(self):
        return self._goal_location

    def get_metadata_raw(self, fname, default=None):
        return self._metadata.get(fname, default)

    def get_field(self, p):
        return self._lvl[p.x][p.y]

    def get_crate_at(self, p):
        if p in self._crates:
            return self._crates[p]
        return None

    def can_enter(self, frompos, destpos):
        return self.get_field(destpos).can_enter

    def iter_fields(self):
        for row in self._lvl:
            for field in row:
                yield field

    def _emit_event(self, event):
        for handler in self._handlers:
            handler(event)

    def add_event_listener(self, handler):
        self._handlers.add(handler)

    def remove_event_listener(self, handler):
        self._handlers.remove(handler)

    def init_from_level(self, other):
        self._width = other.width
        self._height = other.height
        self._start_location = other.start_location
        self._goal_location = other.goal_location
        self._metadata = other._metadata.copy()
        self._crates = other._crates.copy()
        self._lvl = [list(imap(lambda f: f.copy(), c)) for c in other._lvl]
        other2self = lambda x: self.get_field(x.position)
        for of in other.iter_fields():
            mf = self.get_field(of.position)
            if of.is_activation_source:
                for mt in imap(other2self, of.iter_activation_targets()):
                    mf.add_activation_target(mt)

    def load_level(self, fname, infd=None, verbose=1):
        self._name = fname
        if infd is not None:
            lineiter = enumerate(_line_reader(infd), 1)
        else:
            lineiter = enumerate(_line_reader(open(fname)), 1)
        (_, header) = next(lineiter, (1, ""))
        lines = list()
        width = -1
        non_empty_line = lambda x: x[1] != ""
        if header != "2D SuperFun!":
            print "header is %s" % header
            raise IOError("Bad header of %s" % fname)
        for lineno, line in takewhile(non_empty_line, lineiter):
            if len(line) != width:
                if width == -1:
                    width = len(line)
                else:
                    raise IOError("Inconsistent width %d != %d (%s:%d)" %
                                   (len(line), width, fname, lineno))
            if line.lstrip()[0] != '+' or line.rstrip()[-1] != '+':
                raise IOError("Wall missing on left or right side (%s:%d)" % (fname, lineno))
            lines.append(line)

        transposed_lvl = [map(parse_field, x) for x in lines]
        for (j, line) in enumerate(transposed_lvl):
            for (i, obj) in enumerate(line):
                pos = Position(i, j)
                if obj.symbol == "S":
                    if self._start_location is not None:
                        raise IOError("Two start locations %s and %s (%s:%d)" \
                                          % (str(pos), str(self._start_location.position),
                                             fname, lineno))
                    self._start_location = obj
                if obj.symbol == "G":
                    if self._goal_location is not None:
                        raise IOError("Two goal locations %s and %s (%s:%d)" \
                                          % (str(pos), str(self._goal_location.position),
                                             fname, lineno))
                    self._goal_location = obj
                if lines[j][i] == "c":
                    self._crates[pos] = Crate(pos)
                obj._set_position(pos)

        self._lvl = zip(*transposed_lvl)
        self._width = len(self._lvl)
        self._height = len(self._lvl[0])

        for lineno, line in takewhile(non_empty_line, lineiter):
            if line == "nothing": # ignore
                continue
            if not line.startswith("button "):
                raise IOError("Unknown activation rule (%s:%d)" % (fname, lineno))
            match = ACTITVATION_REGEX.match(line)
            if not match:
                raise IOError("Cannot parse button rule (%s:%d)" % (fname, lineno))
            bx, by, tfname, tx, ty = match.groups()
            bx, by, tx, ty = imap(int, (bx, by, tx, ty))
            button = self._lvl[bx][by]
            target = self._lvl[tx][ty]
            if tfname != "gate":
                raise IOError("buttons can only activate gates (%s:%d)" % (fname, lineno))
            if not button.is_activation_source:
                raise IOError("(%d, %d) is not a button (%s:%d)" % (bx, by, fname, lineno))
            if not target.is_activation_target:
                raise IOError("(%d, %d) is not a activable field (%s:%d)" % (tx, ty, fname, lineno))
            button.add_activation_target(target)

        field = None
        value = None

        for lineno, line in takewhile(non_empty_line, lineiter):
            if line[0] == " ":
                if field is None:
                    raise IOError("Continuation line before field (%s:%d)" %
                                  (fname, lineno))
                if len(line) == 1 or (line[1] == "." and len(line) > 2):
                    raise IOError("Bad continuation line (%s:%d)" \
                                      % (fname, lineno))
                value += "\n" + line
                continue
            if ":" not in line:
                raise IOError("Expected field, not no colon (%s:%d)" %
                              (fname, lineno))
            if field is not None:
                self._metadata[field] = value
            field, value = line.split(":", 1)
            field = field.lower()
            if " " in field:
                raise IOError("Bad field name (%s:%d)" % (fname, lineno))
            value = value.strip()
        if field is not None:
            self._metadata[field] = value

    def print_lvl(self, fname, fd=None):
        if fd is None:
            with open(fname, "w") as outfd:
                return self.print_lvl(fname, outfd)
        else:
            rules = 0
            fd.write("2D SuperFun!\n")
            sym = lambda x: (self.get_crate_at(x.position) and "c") or x.symbol
            for line in izip(*self._lvl):
                fd.write("".join(imap(sym, line)))
                fd.write("\n")

            fd.write("\n")

            for field in self.iter_fields():
                if field.symbol != "b" and field.symbol != "B":
                    continue
                fieldname = "button"
                tfieldname = "gate"
                for target in field.iter_activation_targets():
                    ftuple = (fieldname, str(field.position),
                              tfieldname, str(target.position))
                    fd.write("%s %s -> %s %s\n" % ftuple)
                    rules += 1

            if not rules and self._metadata:
                fd.write("nothing\n")
            fd.write("\n")
            for key in sorted(self._metadata.iterkeys()):
                fd.write("%s: %s\n" % (key, self._metadata[key]))

class Level(BaseLevel):

    def __init__(self):
        super(Level, self).__init__()

        self._time_paradox = False
        self._score = 0 # The score (lower is better)
        self._turn_no = 0 # The current turn
        self._turn_max = 0 # The max number of turns
        self._got_goal = False # Whether the goal was reached
        self._player_active = False # Is the current player controllable ?
        self._player = None # current player
        self._clones = [] # clones (in order of appearance)
        self._actions = [] # actions done by current player (i.e. clone)
        self._crates_orig = {} # memory variables
        self._sources = []


    @property
    def score(self):
        return self._score

    @property
    def turn(self):
        return (self._turn_no, self._turn_max)

    @property
    def number_of_clones(self):
        return len(self._clones)

    @property
    def active_player(self):
        """Returns the current clone if the "current self" is currently controllable

        If the "current self" is outside the time-machine and there has
        not been a time-paradox (etc.).
        """
        if self._time_paradox or not self._player_active:
            return None
        return self._player

    def load_level(self, *args, **kwords):
        super(Level, self).load_level(*args, **kwords)
        self._crates_orig = self._crates.copy()
        is_source = attrgetter("is_activation_source")
        all_pos = starmap(Position, product(xrange(self._width), xrange(self._height)))
        self._sources = list(ifilter(is_source, imap(self.get_field, all_pos)))

    def init_from_level(self, other, *args, **kwords):
        if not other.start_location:
            raise ValueError("Missing start location")
        if not other.goal_location:
            raise ValueError("Missing goal location")
        super(Level, self).init_from_level(other,*args, **kwords)
        self._crates_orig = self._crates.copy()
        is_source = attrgetter("is_activation_source")
        all_pos = starmap(Position, product(xrange(self._width), xrange(self._height)))
        self._sources = list(ifilter(is_source, imap(self.get_field, all_pos)))

    def start(self):
        self._score = 0
        self._turn_no = 0
        self._turn_max = 0
        self._time_paradox = False
        self._actions = []
        self._player = PlayerClone(self.start_location.position, self._actions)
        self._player_active = True
        self._clones = [self._player]
        self._crates = self._crates_orig.copy()
        self._emit_event(GameEvent('add-player-clone', source=self._player))


    def perform_move(self, action):
        if self._do_action(action):
            self._do_end_of_turn()

    def _time_paradox_event(self, msg):
        self._time_paradox = True
        e = GameEvent("time-paradox")
        e.reason = msg
        self._emit_event(e)

    def _do_action(self, action):
        act2f = {
            'move-up': functools.partial(self._move, Direction.NORTH),
            'move-down': functools.partial(self._move, Direction.SOUTH),
            'move-left': functools.partial(self._move, Direction.WEST),
            'move-right': functools.partial(self._move, Direction.EAST),
            'skip-turn': functools.partial(self._move, Direction.NO_ACT),
            'reset-time-jump': self._reset_action,
            'reset-level': self._reset_action,
            'enter-time-machine': self._enter_time_machine,
        }
        return act2f[action](action)

    def _move(self, direction, action):
        if self._time_paradox:
            return False

        if direction != Direction.NO_ACT and not self._player_active:
            return False # ignore movement if the player is not active
        if self._player_active:
            self._actions.append(action)
        return True

    def _enter_time_machine(self, action):
        if self._time_paradox:
            return False

        if self._player.position != self._start_location.position:
            # Ignore unless the player is on the start position
            return False

        if not self._player_active:
            return False
        self._actions.append(action)
        return True

    def _do_end_of_turn(self):
        entered = set()
        left = set()
        unchanged = set()
        clone_positions = frozenset(c.position for c in self._clones)
        # Enqueue events (except paradoxes, which we just trigger as soon as we discover them)
        equeue = []
        def make_event(*a, **kw):
            equeue.append(functools.partial(self._emit_event, GameEvent(*a, **kw)))

        for cno, clone in ifilter(lambda x: self._turn_no < len(x[1]), enumerate(self._clones)):
            action = clone[self._turn_no]
            if action == 'enter-time-machine':
                if clone.position != self.start_location.position:
                    self._time_paradox_event("Clone does not make it back to start")
                    return
                make_event(action)
                continue
            if action.startswith("move-"):
                d = Direction.act2dir(action)
                pos = clone.position
                target = pos.dir_pos(d)
                crate = self.get_crate_at(target)
                ct = None
                act = None
                succ = True
                if crate:
                    ct = target.dir_pos(d)
                    if (not self.get_field(ct).can_enter or self.get_crate_at(ct)
                            or ct in clone_positions):
                        # Crate cannot be moved, push fails.
                        succ = False

                if succ and self.get_field(target).can_enter:
                    # Do the action if possible
                    if crate:
                        entered.add(ct)
                        unchanged.add(target)
                    else:
                        entered.add(target)
                    left.add(pos)
                else:
                    succ = False
                    unchanged.add(pos)

                if succ:
                    if crate:
                        act = functools.partial(self._move_clone_w_crate, clone, crate,
                                                target, ct, action)
                    else:
                        act = functools.partial(self._move_clone, clone, target, action)
                    equeue.append(act)
                else:
                    # Failed
                    make_event(action, source=clone, success=False)
            else:
                unchanged.add(clone.position)
                make_event(action, source=clone)

        if entered or left:
            deactivated = left - entered - unchanged
            activated = entered - left - unchanged
            is_source = attrgetter("is_activation_source")
            it = chain(deactivated, activated)
            self._changed_targets(ifilter(is_source, imap(self.get_field, it)))

        try:
            for act in equeue:
                act()
        except TimeParadoxError:
            return

        for clone in self._clones:
            if self.get_crate_at(clone.position):
                self._time_paradox_event("Clone and crate on the same field %s [Non-Determinism]" \
                                             % str(clone.position))
                return
            if not self.get_field(clone.position).can_enter:
                self._time_paradox_event("Clone is on an unreachable field at end of turn: %s" \
                                         % str(clone.position))
                return

        if not self._got_goal and self.goal_location.position in entered:
            self._got_goal = True
            self._emit_event(GameEvent("goal-obtained"))

        if self._player_active:
            # active moves cost one
            self._score += 1
            if self._player[-1] == 'enter-time-machine':
                self._player_active = False

        if self._player_active or self._turn_no < self._turn_max:
            self._turn_no += 1
            if self._turn_max < self._turn_no:
                self._turn_max = self._turn_no
            self._emit_event(GameEvent("end-of-turn"))
        else:

            if self._got_goal:
                self._emit_event(GameEvent("game-complete"))
            else:
                # cloning cost one
                self._turn_no = 0
                self._score += 1
                self._emit_event(GameEvent("end-of-turn"))

                self._player_active = True
                self._actions = []
                self._player = PlayerClone(self.start_location.position, self._actions)
                self._clones.append(self._player)
                self._reset_movables(clones=False)
                self._emit_event(GameEvent("time-jump"))
                self._emit_event(GameEvent('add-player-clone', source=self._player))

    def _reset_action(self, action):
        self._time_paradox = False
        self._reset_movables()
        self._turn_no = 0
        if action == "reset-time-jump":
            # Remove the latest clone
            self._clones.pop()
            self._emit_event(GameEvent('remove-player-clone', source=self._player))
        elif action == "reset-level":
            for c in self._clones:
                self._emit_event(GameEvent('remove-player-clone', source=c))
            self._clones = []

        if self._clones:
            if len(self._actions) == self._turn_max:
                # -1 for the "enter-time-machine" action
                self._turn_max = len(max(self._clones, key=len)) - 1
            self._score -= len(self._actions)
        else:
            # reseting all clones or the first clone
            self._turn_max = 0
            self._score = 0

        if self._got_goal:
            self._emit_event(GameEvent('goal-lost'))
            self._got_goal = False

        # We always reset by removing a clone (or all clones), so we
        # have insert a clone to replace the removed one (or insert
        # the new "first" clone).
        self._active_player = True
        self._actions = []

        self._player = PlayerClone(self.start_location.position, self._actions)
        self._clones.append(self._player)
        self._emit_event(GameEvent('add-player-clone', source=self._player))

    def _reset_movables(self, clones=True):
        """Reset all movables to their start positions

        NB: if the clones are known to be at their starting position (e.g.
        because it is the end of a time-jump with no time-paradoxes), the
        optional variable "clones" can be set to false.
        """
        # De-activate all sources
        self._changed_targets(self._sources, reset=True)
        self._crates = self._crates_orig.copy()
        # Move crates back to start...
        for p in self._crates:
            self._crates[p].position = p
            self._emit_event(GameEvent("jump-moveable", source=self._crates[p]))
        if clones:
            for c in self._clones:
                c.position = self.start_location.position
                self._emit_event(GameEvent("jump-moveable", source=c))

    def check_lvl(self, verbose=False, require_solution=False):
        if verbose:
            print "Checking %s ..." % self.name
        first = lambda x: next(iter(x), None)
        solution = self._metadata.get("solution", None)
        for field in self.iter_fields():
            if field.is_activation_source and \
                    first(field.iter_activation_targets()) is None:
                print "W: lvl %s: activator (%s) at %s has no targets" \
                      % (self.name, field.symbol, str(field.position))
            if field.is_activation_target and \
                    first(field.iter_activation_sources()) is None:
                print "W: lvl %s: activable (%s) at %s has no sources" \
                      % (self.name, field.symbol, str(field.position))
        if require_solution and solution is None:
            raise UnsolvableError("No solution for %s" % self.name)
        if solution is not None:

            events = []
            wait_for_timejump = False

            def event_handler(e):
                if wait_for_timejump and e.event_type == "time-jump":
                    events.append(e)
                if e.event_type == "game-complete" or e.event_type == "time-paradox":
                    events.append(e)

            self.add_event_listener(event_handler)

            self.start()
            for action in solution2actions(solution):
                if events and events[0].event_type == "game-complete":
                    print "W: lvl %s: Solution found in jump %d" \
                        % (self.name, self.number_of_clones)
                    break
                self.perform_move(action)
                if events and events[0].event_type == "time-paradox":
                    raise TimeParadoxError("E: lvl %s: Time-paradox in time-jump %d (%s)" \
                        % (self.name, self.number_of_clones, events[0].reason))
                    break

            if not self._player_active:
                # The last clone may do less actions than earlier one
                wait_for_timejump = True
                while not events:
                    # Wait for the current time-jump to finish...
                    self.perform_move("skip-turn")

            self.remove_event_listener(event_handler)

            if not events:
                raise UnsolvableError("E: lvl %s: Solution does not obtain goal" % self.name)

    def iter_clones(self):
        return (c for c in self._clones)

    def _changed_targets(self, sources, reset=False):
        changed_targets = set()
        change_func = lambda x: x.toggle_activation()
        if reset:
            change_func = lambda x: x.reset_to_init_state()

        for f in ifilter(change_func, sources):
            for t in f.iter_activation_targets():
                if t in changed_targets:
                    changed_targets.discard(t)
                else:
                    changed_targets.add(t)
            if f.activated:
                self._emit_event(GameEvent("field-activated", source=f))
            else:
                self._emit_event(GameEvent("field-deactivated", source=f))

        for target in changed_targets:
            # targets have already been activated/deactivated at this point.
            et = "field-deactivated"
            if target.activated:
                et = "field-activated"
            self._emit_event(GameEvent(et, source=target))


    def _move_clone(self, clone, dest_pos, action):
        clone.position = dest_pos
        self._emit_event(GameEvent(action, source=clone))

        # we cannot check if a crate is on top of the clone here (reliably at least)
        # because the clone may move before it is mow'ed down (rather than moving into
        # a box).  So we wait till moves have been done.
        # - We also defer checking if a clone is now stuck in a gate (etc.)

    def _move_clone_w_crate(self, clone, crate, clone_dest_pos, crate_dest_pos, action):
        # Move the crate first...

        taken = False
        if clone_dest_pos not in self._crates:
            ocrate = self._crates.get(crate_dest_pos, None)
            if not ocrate or ocrate != crate:
                self._time_paradox_event("Crate on %s was moved in two different directions" \
                                             % str(clone_dest_pos))
                raise TimeParadoxError
            crate = None
        else:
            taken = crate_dest_pos in self._crates
            crate.position = clone_dest_pos
            del self._crates[clone_dest_pos]
            self._crates[crate_dest_pos] = crate

        if crate: # Move the crate if still present
            self._emit_event(GameEvent(action, source=crate))

        self._move_clone(clone, clone_dest_pos, action)

        if not crate:
            # The check below is already done, if another clone moved the box for us
            return

        if taken or not self.get_field(clone_dest_pos).can_enter:
            reason = "Two crates colided at %s" % str(clone_dest_pos)
            if not taken:
                reason = "Crate is on an unreachable field at end of turn: %s" \
                    % str(clone_dest_pos)
            self._time_paradox_event(reason)
            raise TimeParadoxError

class EditableLevel(BaseLevel):

    def load_level(self, *args, **kwords):
        super(EditableLevel, self).load_level(*args, **kwords)
        # Ensure self._lvl is mutable
        self._lvl = map(list, self._lvl)

    def init_from_level(self, *args, **kwords):
        super(EditableLevel, self).init_from_level(*args, **kwords)
        # Ensure self._lvl is mutable
        self._lvl = map(list, self._lvl)

    def new_map(self, width, height, translate=None):
        if width < 3 or height < 3:
            raise ValueError("Width and height must both be at least 3")

        crates = {}
        lvl = []
        def _new_field(npos, t):
            if translate is not None:
                opos = npos - t
                if (0 < opos.x < self.width - 1) and (0 < opos.y < self.height - 1):
                    ofield = self.get_field(opos)
                    ofield._set_position(npos)
                    crate = self.get_crate_at(opos)
                    if crate:
                        crates[npos] = crate
                        crate.position = npos
                    return ofield
            return Wall("+", position=npos)

        for x in range(width):
            column = []
            lvl.append(column)
            for y in range(height):
                f = _new_field(Position(x, y), translate)
                column.append(f)

        if translate is None:
            # clear unless they are being translated.  In the latter case, they
            # have been properly moved.
            self._start_location = None
            self._goal_location = None
            # Keep old metadata on resize
            self._metadata = {}
            # Keep old name on resize
            self._name = "untitled"

        self._width = width
        self._height = height
        self._crates = crates
        self._lvl = lvl
        self._emit_event(EditorEvent("new-map"))

    def perform_change(self, ctype, position, *args, **kwargs):
        if ctype == "toggle-connection":
            self._handle_connection(position, *args)
        elif ctype == "set-initial-state":
            self._handle_set_state(position, *args)
        else:
            self._make_field(position, ctype)

    def _handle_set_state(self, position, new_state):
        field = self.get_field(position)
        if field.symbol != "-" and field.symbol != "_":
            # only gates have multiple starting states
            return
        if field.activated != new_state:
            field.toggle_activation()
            if new_state:
                et = "field-activated"
            else:
                et = "field-deactivated"
            self._emit_event(EditorEvent(et, source=field))

    def _handle_connection(self, src_pos, target_pos):
        source = self.get_field(src_pos)
        target = self.get_field(target_pos)
        if not source.is_activation_source:
            return
        if not target.is_activation_target:
            return
        if source.has_activation_target(target):
            source.remove_activation_target(target)
            self._emit_event(EditorEvent("field-disconnected", source=source, target=target))
        else:
            source.add_activation_target(target)
            self._emit_event(EditorEvent("field-connected", source=source, target=target))

    def _make_field(self, position, field):
        fields = {
        'field': functools.partial(Field, ' '),
        'wall': functools.partial(Wall, '+'),
        'crate': functools.partial(Field, ' '),
        'gate': functools.partial(Gate, '_'),
        'button': functools.partial(Button, 'b'),
        'start': functools.partial(StartLocation, 'S'),
        'goal': functools.partial(GoalLocation, 'G'),
        }

        if (not (0 < position.x < self.width - 1) or
                not (0 < position.y < self.height - 1)):
            # Ignore attempts to change the "outer" wall and anything
            # outside the level.
            return

        if field == "start" or field == "goal":
            # Only one start
            old = self.start_location
            if field == "goal":
                old = self.goal_location
            if old is not None:
                opos = old.position
                nf = Field(' ')
                nf._set_position(opos)
                self._lvl[opos.x][opos.y] = nf
                self._emit_event(EditorEvent("remove-special-field", source=old))

        oldcrate = self.get_crate_at(position)
        if oldcrate:
            del self._crates[position]
            self._emit_event(EditorEvent("remove-crate", source=oldcrate))

        f = fields[field]()
        f._set_position(position)
        # FIXME handle source and targets
        self._lvl[position.x][position.y] = f
        self._emit_event(EditorEvent("replace-tile", source=f))
        if field == 'crate':
            c = Crate(position)
            self._crates[position] = c
            self._emit_event(EditorEvent("add-crate", source=c))
        if field == "start":
            self._start_location = f
        if field == "goal":
            self._goal_location = f
