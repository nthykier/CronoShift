#!/usr/bin/python
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

import argparse
import sys

from chrono.model.level import Level, TimeParadoxError

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check ChronoShift levels")
    parser.add_argument('--verbose', '-v', action="store_const", dest="verbose",
                        const=True, default=False, help="Be verbose in the output")
    parser.add_argument('--solvable', action="store_const", dest="solvable",
                        const=True, default=False, help="Fail if a level is not solvable")
    parser.add_argument('--test-time-paradox', action="store_const", dest="timeparadox",
                        const=True, default=False,
                        help="Fail unless a solution leads to a time-paradox")
    parser.add_argument('levels', type=str, nargs='+',
                        help="The level files to check")
    args = parser.parse_args()

    require_solution = args.solvable or args.timeparadox

    for lvlfile in args.levels:
        lvl = Level()
        lvl.load_level(lvlfile)
        try:
            lvl.check_lvl(verbose=args.verbose, require_solution=require_solution)
            if args.timeparadox:
                print "E: lvl %s: Expected time-paradox, but non occured" % lvl.name
                sys.exit(1)
        except TimeParadoxError, e:
            if not args.timeparadox:
                print " ".join(e.args)
                sys.exit(1)
