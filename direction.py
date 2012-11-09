from position import Pos

class Direction(object):

    NORTH  = 0
    EAST   = 1
    SOUTH  = 2
    WEST   = 3
    NO_ACT = 4

    # (0, 0) is NW, (Width, Height) is SE
    NORTH_DIFF  = Pos(0, -1)
    EAST_DIFF   = Pos(1, 0)
    SOUTH_DIFF  = Pos(0, 1)
    WEST_DIFF   = Pos(-1, 0)
    NO_ACT_DIFF = Pos(0, 0)

    _DIR_DIFF = (
        NORTH_DIFF,
        EAST_DIFF,
        SOUTH_DIFF,
        WEST_DIFF,
        NO_ACT_DIFF,
    )

    _ACT2DIR = {
        'N': NORTH,
        'E': EAST,
        'S': SOUTH,
        'W': WEST,
        'H': NO_ACT,
        'move-up': NORTH,
        'move-right': EAST,
        'move-down': SOUTH,
        'move-left': WEST,
    }
    @staticmethod
    def new_pos(pos, direction):
        return pos + Direction.dir_update(direction)

    @staticmethod
    def dir_update(direction):
        return Direction._DIR_DIFF[direction]

    @staticmethod
    def act2dir(act):
        return Direction._ACT2DIR[act]

    @staticmethod
    def act_update(act):
        return dir_update(act2dir(act))
