from direction import Direction
import functools
from itertools import imap, ifilter, chain
from operator import attrgetter
import re

from moveable import PlayerClone, Player
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
        self._extra = {}
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
        self._active_sources = {}

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
        return self._turn_no

    def get_field(self, p):
        return self._lvl[p.x][p.y]

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
                obj._set_position(pos)

        self._lvl = zip(*transposed_lvl)
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
                self._extra[field] = value
            field, value = line.split(":", 1)
            field = field.lower()
            if " " in field:
                raise IOError("Bad field name (%s:%d)" % (fname, lineno))
            value = value.strip()
        if field is not None:
            self._extra[field] = value

    def start(self):
        self._score = 0
        self._turn_no = 0
        self._turn_max = 0
        self._time_paradox = False
        self._actions = []
        self._player = PlayerClone(self.start_location.position, self._actions)
        self._player_active = True
        self._clones = [self._player]
        self._emit_event(GameEvent('player-clone', source=self._player))


    def perform_move(self, action):
        if self._time_paradox:
            return
        if self._do_action(action):
            self._do_end_of_turn()

    def _time_paradox_event(self):
        self._time_paradox = True
        self._emit_event(GameEvent("time-paradox"))

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
        changed_targets = set()
        for clone in ifilter(lambda x: self._turn_no < len(x), self._clones):
            action = clone[self.turn]
            if action == 'enter-time-machine':
                self._emit_event(GameEvent(action))
                continue
            if action.startswith("move-"):
                d = Direction.act2dir(action)
                pos = clone.position
                target = pos.dir_pos(d)
                succ = False
                # FIXME: handle crates
                if self.get_field(target).can_enter:
                    # Do the action if possible
                    clone.position = target
                    succ = True
                    entered.add(target)
                    left.add(pos)
                self._emit_event(GameEvent(action, source=clone, success=succ))
            else:
                self._emit_event(GameEvent(action, source=clone))

            if self.turn -1  == len(clone):
                if clone.position != self.start_location.position:
                    self._time_paradox_event()
                    return

        if not self._got_goal and self.goal_location.position in entered:
            self._got_goal = True
            self._emit_event(GameEvent("goal-obtained"))

        if entered or left:
            deactivated = left - entered
            activated = entered - left
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

        for clone in ifilter(lambda x: self._turn_no < len(x), self._clones):
            if not self.get_field(clone.position).can_enter:
                self._time_paradox_event()
                return

        if self._player_active:
            self._score += 1

        if self._player_active or self.turn < self._turn_max:
            self._turn_no += 1
            self._emit_event(GameEvent("end-of-turn"))
        else:
            if self._turn_max < self.turn:
                self._turn_max = self.turn
            self._turn_no = 0

            self._emit_event(GameEvent("end-of-turn"))

            if self._got_goal:
                self._emit_event(GameEvent("game-complete"))
            else:
                self._player_active = True
                self._actions = []
                self._player = PlayerClone(self.start_location.position, self._actions)
                self._clones.append(self._player)
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
        solution = self._extra.get("solution", None)
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
            clones = []
            space = lambda x: not x[0].isspace()
            for clone in solution.split("\n .\n"):
                clones.append(PlayerClone(self.start_location.position,
                                          filter(space, clone))
                              )
            limit = max(imap(len, clones))
            activated = {}
            got_goal = False
            timeparadox = False

            for jumpno in xrange(len(clones)):
                if got_goal:
                    print "W: lvl %s: Solution found in jump %d and not %d" \
                        % (self.name, jumpno, len(clones))
                    break
                try:
                    got_goal = self._check_timejump(clones, limit, jumpno,
                                                    verbose=verbose)
                except:
                    timeparadox = True
                    break

            if not timeparadox and not got_goal:
                print "E: lvl %s: Solution does not obtain goal" % self.name

    def _check_timejump(self, clones, turnlimit, jumpno, verbose=False):
        got_goal = False
        for turn in xrange(turnlimit):
            left = set()
            entered = set()

            # The jumpno determines the number of active clones
            for cno in xrange(jumpno+1):
                clone = clones[cno]
                spos = clone.position
                clone.do_action(self, turn)
                epos = clone.position
                if spos != epos:
                    left.add(spos)
                    entered.add(epos)
                    if verbose:
                        print "I: clone %d moves from %s to %s" \
                            % (cno, str(spos), str(epos))
            deactivated = left - entered
            activated = entered - left

            for dpos in deactivated:
                f = self.get_field(dpos)
                if not f.is_activation_source:
                    continue
                f.deactivate()
                if verbose:
                    print "I: %s at %s was deactivated" \
                        % (f.symbol, str(f.position))

            for apos in activated:
                f = self.get_field(apos)
                if not f.is_activation_source:
                    continue
                f.activate()
                if verbose:
                    print "I: %s at %s was activated" \
                        % (f.symbol, str(f.position))

            for (cno, clone) in enumerate(clones):
                f = self.get_field(clone.position)
                if clone.position == self.goal_location.position:
                    got_goal = True
                if not f.can_enter:
                    if verbose:
                        self.show_field(clone.position)
                    print "E: lvl %s: clone %d is at %s which is not enterable (at end of turn %d)" \
                        % (self.name, cno, str(clone.position), turn + 1)
                    raise TimeParadoxError

        for (cno, clone) in enumerate(clones):
            if clone.position != self.start_location.position:
                if verbose:
                    self.show_field(clone.position)
                print "E: lvl %s: clone %d ends at %s and not at start" \
                    % (self.name, cno, str(clone.position))
                raise TimeParadoxError

        return got_goal

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

            if not rules and self._extra:
                fd.write("nothing\n")
            fd.write("\n")
            for key in sorted(self._extra.iterkeys()):
                fd.write("%s: %s\n" % (key, self._extra[key]))


    def can_enter(self, frompos, destpos):
        return self.get_field(destpos).can_enter

    def iter_fields(self):
        for row in self._lvl:
            for field in row:
                yield field
