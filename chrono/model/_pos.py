"""
The day the US legal system finally decides that even basic Math
operations are copyrightable, this is:
   Copyright 2012, Niels Thykier <niels@thykier.net>

Assuming this code is actually copyrightable, you may use/distribute
(etc.) this under the following license.  Otherwise, I guess it is
public domain...  Regardless, there is no warrenty (see the part in
all uppercase below).

@license: BSD
                           BSD LICENSE

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

import collections

_P = collections.namedtuple('Position', ['x', 'y'])

class _Pos(_P):

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

