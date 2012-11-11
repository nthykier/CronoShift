#!/usr/bin/python

import argparse
import pygame
import sys

from level import Level
from game import Game

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Show ChronoShift levels")
#    parser.add_argument('--verbose', '-v', action="store_const", dest="verbose",
#                        const=False, help="Be verbose in the output")
    parser.add_argument('level', type=str, nargs='+',
                        help="The level files to check")
    args = parser.parse_args()

    if args.level is None or len(args.level) != 1:
        print "No level or too many levels"
        sys.exit(1)

    pygame.init()

    level = Level()
    level.load_level(args.level[0])

    pygame.display.set_mode((424, 320))

    Game(level).main()
