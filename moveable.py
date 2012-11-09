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

    @property
    def is_crate(self):
        return self._is_crate

    @property
    def is_clone(self):
        return self._is_player

class PlayerClone(Moveable):

    def __init__(self, position, path):
        super(PlayerClone, self).__init__(position, True, False)
        self._path = path

    def __len__(self):
        return len(self._path)

    def do_action(self, lvl, turn):
        act = "H"
        x, y = self.position
        if turn < len(self._path):
            act = self._path[turn]
        p = self.position - Direction.act_update(act)
        field = lvl.get_field(p)
        if field.can_enter:
            self._position = p

class Crate(Moveable):

    def __init__(self,position):
        super(Crate, self).__init__(position, False, True)
