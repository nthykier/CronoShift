#!/usr/bin/python
import argparse
import sys

from level import Level, TimeParadoxError

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
