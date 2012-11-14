#!/usr/bin/python

import argparse
import os
import pygame
import sys

if 1:
    # If pgu-0.16 is there, make it available
    d = os.path.join(os.path.dirname(os.path.realpath(__file__)), "pgu-0.18")
    if os.path.exists(d):
        print "Using embedded pgu"
        sys.path.insert(0, d)

from chrono.model.level import Level, solution2actions

from chrono.view.game_window import GameWindow

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Show ChronoShift levels")
    parser.add_argument('--play-solution', action="store_const", dest="solution",
                        const=True, default=False, help="Play the solution of the level")
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

    g = GameWindow(level)
    if args.solution:
        sol = level.get_metadata_raw("solution")
        if not sol:
            print "%s has no solution" % level.name
            sys.exit(1)
        g.auto_play = solution2actions(sol)
    g.main()
