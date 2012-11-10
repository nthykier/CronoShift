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
from direction import Direction
import functools
from itertools import imap, ifilter, chain
from operator import attrgetter
import re

from moveable import PlayerClone, Crate
from field import parse_field, Position

ACTITVATION_REGEX = re.compile(
  r'^button\s+\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*->\s*(\S+)\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*$'
)

class GameError(Exception):
    pass

class TimeParadoxError(GameError):
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

class Level(object):

    def __init__(self):
        self._name = None
        self._width = 0
        self._height = 0
        self._lvl = []
        self._metadata = {}
        self._start_location = None
        self._goal_location = None
        self._handlers = set()

        self._time_paradox = False
        self._score = 0 # The score (lower is better)
        self._turn_no = 0 # The current turn
        self._turn_max = 0 # The max number of turns
        self._got_goal = False # Whether the goal was reached
        self._player_active = False # Is the current player controllable ?
        self._player = None # current player
        self._clones = [] # clones (in order of appearance)
        self._actions = [] # actions done by current player (i.e. clone)
        self._crates = {} # location of crates

        # memory variables
        self._crates_orig = {} # Original location of crates

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

    @property
    def score(self):
        return self._score

    @property
    def turn(self):
        return (self._turn_no, self._turn_max)

    @property
    def number_of_clones(self):
        return len(self._clones)

    def get_metadata_raw(self, fname, default=None):
        return self._metadata.get(fname, default)

    def get_field(self, p):
        return self._lvl[p.x][p.y]

    def get_crate_at(self, p):
        if p in self._crates:
            return self._crates[p]
        return None

    def load_level(self, fname, infd=None, verbose=1):
        self._name = fname
        if infd is not None:
            fd = iter(infd)
        else:
            fd = iter(open(fname))
        header = next(fd)
        lines = list()
        width = -1
        lineno = 1;
        if header.rstrip("\r\n") != "2D SuperFun!":
            print "header is %s" % header
            raise IOError("Bad header of %s" % fname)
        for line in fd:
            line = line.rstrip("\r\n")
            lineno += 1
            if line == "":
                break;
            if line.strip() == "":
                raise IOError("White-space only line (%s:%d)" % (fname, lineno))
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
                    self._crates_orig[pos] = Crate(pos)
                obj._set_position(pos)

        self._lvl = zip(*transposed_lvl)
        self._crates = self._crates_orig.copy()
        self._width = len(self._lvl)
        self._height = len(self._lvl[0])

        for line in fd:
            line = line.rstrip("\r\n")
            lineno += 1
            if line == "":
                break;
            if line.strip() == "":
                raise IOError("White-space only line (%s:%d)" % (fname, lineno))
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

        for line in fd:
            line = line.rstrip("\r\n")
            lineno += 1
            if line == "":
                break;
            if line.strip() == "":
                raise IOError("White-space only line (%s:%d)" % (fname, lineno))
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
        self._emit_event(GameEvent('player-clone', source=self._player))


    def perform_move(self, action):
        if self._time_paradox:
            return
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
            'enter-time-machine': self._enter_time_machine,
        }
        return act2f[action](action)

    def _move(self, direction, action):
        if direction != Direction.NO_ACT and not self._player_active:
            return # ignore movement if the player is not active
        self._actions.append(action)
        return True

    def _enter_time_machine(self, action):
        if self._player.position != self._start_location.position:
            # Ignore unless the player is on the start position
            return

        if self._player_active:
            self._actions.append(action)
            self._player_active = False
        return True

    def _do_end_of_turn(self):
        entered = set()
        left = set()
        unchanged = set()
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
                    if not self.get_field(ct).can_enter or self.get_crate_at(ct):
                        # Crate cannot be moved, push fails.
                        succ = False

                if succ and self.get_field(target).can_enter:
                    # Do the action if possible
                    if crate:
                        entered.add(ct)
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
            self._changed_targets(activated, deactivated)

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


        if not self._got_goal and self.goal_location.position in entered:
            self._got_goal = True
            self._emit_event(GameEvent("goal-obtained"))

        if self._player_active:
            # active moves cost one
            self._score += 1

        if self._player_active or self._turn_no < self._turn_max:
            self._turn_no += 1
            if self._turn_max < self._turn_no:
                self._turn_max = self._turn_no
            self._emit_event(GameEvent("end-of-turn"))
        else:
            self._turn_no = 0

            self._emit_event(GameEvent("end-of-turn"))

            if self._got_goal:
                self._emit_event(GameEvent("game-complete"))
            else:
                # cloning cost one (unless we already paid for this move)
                if not self._player_active:
                    self._score += 1
                self._player_active = True
                self._actions = []
                self._player = PlayerClone(self.start_location.position, self._actions)
                self._clones.append(self._player)
                # De-activate fields with crates on them
                self._changed_targets([], self._crates)
                self._crates = self._crates_orig.copy()
                for p in self._crates:
                    self._crates[p].position = p
                    self._emit_event(GameEvent("reset-crate", source=self._crates[p]))
                self._emit_event(GameEvent("time-jump"))
                self._emit_event(GameEvent('player-clone', source=self._player))

    def _emit_event(self, event):
        for handler in self._handlers:
            handler(event)

    def add_event_listener(self, handler):
        self._handlers.add(handler)

    def remove_event_listener(self, handler):
        self._handlers.remove(handler)

    def show_field(self, position):
        x, y = position
        fstr = "%" + str(x+1) + "s"
        line = "".join(row[y].symbol for row in self._lvl)
        print fstr % "v"
        print line
        print fstr % "^"

    def check_lvl(self, verbose=1):
        if verbose:
            print "Checking %s ..." % self.name
        first = lambda x: next(iter(x), None)
        solution = self._metadata.get("solution", None)
        for field in self.iter_fields():
            if field.is_activation_source and \
                    first(field.iter_activation_targets()) is None:
                if verbose:
                    self.show_field(field.position)
                print "W: lvl %s: activator (%s) at %s has no targets" \
                      % (self.name, field.symbol, str(field.position))
            if field.is_activation_target and \
                    first(field.iter_activation_sources()) is None:
                if verbose:
                    self.show_field(field.position)
                print "W: lvl %s: activable (%s) at %s has no sources" \
                      % (self.name, field.symbol, str(field.position))
        if solution is not None:
            space = lambda x: not x[0].isspace() and x[0] != "."
            def _s2actions(x):
                if x == "N": return "move-up"
                if x == "E": return "move-right"
                if x == "S": return "move-down"
                if x == "W": return "move-left"
                if x == "H": return "skip-turn"
                if x == "T": return "enter-time-machine"
                raise ValueError("Unknown command %s" % x)

            events = []

            def event_handler(e):
                if e.event_type == "game-complete" or e.event_type == "time-paradox":
                    events.append(e)

            self.add_event_listener(event_handler)

            self.start()
            for action in imap(_s2actions, ifilter(space, solution)):
                if events and  events[0].event_type == "game-complete":
                    print "W: lvl %s: Solution found in jump %d" \
                        % (self.name, self.number_of_clones)
                    break
                self.perform_move(action)
                if events and events[0].event_type == "time-paradox":
                    print "E: lvl %s: Time-paradox in time-jump %d (%s)" \
                        % (self.name, self.number_of_clones, events[0].reason)
                    break

            self.remove_event_listener(event_handler)

            if not events:
                print "E: lvl %s: Solution does not obtain goal" % self.name

    def print_lvl(self, fname, fd=None):
        if fd is None:
            with open(fname, "w") as outfd:
                return self.print_lvl(fname, outfd)
        else:
            rules = 0
            fd.write("2D SuperFun!\n")
            for line in self._lvl:
                fd.write("".join(imap(attrgetter("symbol"), line)))
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


    def can_enter(self, frompos, destpos):
        return self.get_field(destpos).can_enter

    def iter_fields(self):
        for row in self._lvl:
            for field in row:
                yield field

    def _changed_targets(self, activated, deactivated):
        changed_targets = set()
        is_source = attrgetter("is_activation_source")
        it = chain(deactivated, activated)

        for f in ifilter(is_source, imap(self.get_field, it)):
            for t in f.iter_activation_targets():
                if t in changed_targets:
                    changed_targets.discard(t)
                else:
                    changed_targets.add(t)
            if f in deactivated:
                self._emit_event(GameEvent("field-deactivated", source=f))
            else:
                self._emit_event(GameEvent("field-activated", source=f))

        for target in changed_targets:
            target.toogle_activation()
            et = "field-deacitvated"
            if target.activated:
                et = "field-activated"
            self._emit_event(GameEvent(et, source=target))

    def _move_clone(self, clone, dest_pos, action):
        clone.position = dest_pos
        self._emit_event(GameEvent(action, source=clone))

        if not self.get_field(dest_pos).can_enter:
            self._time_paradox_event("Clone is on an unreachable field at end of turn: %s" \
                                         % str(dest_pos))
            raise TimeParadoxError
        # we cannot check if a crate is on top of the clone here (reliably at least)
        # because the clone may move before it is mow'ed down (rather than moving into
        # a box).  So we wait till moves have been done.

    def _move_clone_w_crate(self, clone, crate, clone_dest_pos, crate_dest_pos, action):
        # Move the crate first...

        taken = crate_dest_pos in self._crates
        crate.position = clone_dest_pos
        del self._crates[clone_dest_pos]
        self._crates[crate_dest_pos] = crate

        self._emit_event(GameEvent(action, source=crate))
        self._move_clone(clone, clone_dest_pos, action)

        if taken or not self.get_field(clone_dest_pos).can_enter:
            reason = "Two crates colided at %s" % str(clone_dest_pos)
            if not taken:
                reason = "Crate is on an unreachable field at end of turn: %s" \
                    % str(clone_dest_pos)
            self._time_paradox_event(reason)
            raise TimeParadoxError
