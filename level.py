from operator import attrgetter
from itertools import imap
import re

from moveable import PlayerClone
from field import parse_field, Position

ACTITVATION_REGEX = re.compile(
  r'^button\s+\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*->\s*(\S+)\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*$'
)

class Level(object):

    def __init__(self):
        self._name = None
        self._lvl = []
        self._extra = {}
        self._start_location = None
        self._goal_location = None

    @property
    def name(self):
        return self._name

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
                clones.append(PlayerClone(self._start_location.position,
                                          filter(space, clone))
                              )
            limit = max(imap(len, clones))
            activated = {}
            got_goal = False
            stop = False
            for turn in xrange(limit):
                left = set()
                entered = set()
                for (cno, clone) in enumerate(clones):
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
                    if clone.position == self._goal_location.position:
                        got_goal = True
                    if not f.can_enter:
                        if verbose:
                            self.show_field(clone.position)
                        print "E: lvl %s: clone %d is at %s which is not enterable (at end of turn %d)" \
                            % (self.name, cno, str(clone.position), turn + 1)
                        stop = True
                        break
                if stop:
                    break;

            if not stop:
                for (cno, clone) in enumerate(clones):
                    if clone.position != self._start_location.position:
                        if verbose:
                            self.show_field(clone.position)
                        print "E: lvl %s: clone %d ends at %s and not at start" \
                            % (self.name, cno, str(clone.position))

                if not got_goal:
                    print "E: lvl %s: Solution does not obtain goal" % self.name
                    
    def get_field(self, p):
        return self._lvl[p.x][p.y]

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

    def iter_fields(self):
        for row in self._lvl:
            for field in row:
                yield field
