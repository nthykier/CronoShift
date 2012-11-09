from direction import Direction
from field import Position

class Moveable(object):

    def __init__(self, position, is_player, is_crate):
        self._is_player = is_player
        self._is_box = is_crate
        self._position = position

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos

    def move_direction(self, direction):
        self._position = self._position.dir_pos(direction)

    @property
    def is_crate(self):
        return self._is_crate

    @property
    def is_clone(self):
        return self._is_player

class Player(Moveable):
    def __init__(self, position):
        super(Player, self).__init__(position, True, False)

class PlayerClone(Moveable):

    def __init__(self, position, actions):
        super(PlayerClone, self).__init__(position, True, False)
        self._actions = actions

    def __len__(self):
        return len(self._actions)

    def __getitem__(self, i):
        return self._actions[i]

    def do_action(self, lvl, turn):
        act = "H"
        x, y = self.position
        if turn < len(self._path):
            act = self._action[turn]
        p = self.position - Direction.act_update(act)
        field = lvl.get_field(p)
        if field.can_enter:
            self._position = p

class Crate(Moveable):

    def __init__(self,position):
        super(Crate, self).__init__(position, False, True)
