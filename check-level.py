#!/usr/bin/python
import argparse

from level import Level

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check ChronoShift levels")
    parser.add_argument('--verbose', '-v', action="store_const", dest="verbose",
                        const=True, default=False, help="Be verbose in the output")
    parser.add_argument('--solvable', action="store_const", dest="solvable",
                        const=True, default=False, help="Fail if a level is not solvable")
    parser.add_argument('levels', type=str, nargs='+',
                        help="The level files to check")
    args = parser.parse_args()

    for lvlfile in args.levels:
        lvl = Level()
        lvl.load_level(lvlfile)
        lvl.check_lvl(verbose=args.verbose, solvable=args.solvable)
