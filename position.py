import collections

_P = collections.namedtuple('Position', ['x', 'y'])

class Pos(_P):

    def __str__(self):
        # This looks better...
        return "(%d, %d)" % (self.x, self.y)

    def __add__(self, other):
        return type(self)(self.x + other.x, self.y + other.y)

    def __mul__(self, other):
        return type(self)(self.x * other.x, self.y * other.y)

    def __sub__(self, other):
        return type(self)(self.x - other.x, self.y - other.y)

    def __rsub__(self, other):
        return type(self)(other.x - self.x, other.y - self.y)

    # Associative
    __radd__ = __add__
    __rmul__ = __mul__

