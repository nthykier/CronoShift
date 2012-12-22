"""
Taken (with modification) from:
  https://bitbucket.org/thesheep/qq/src/1090d7e5537f/qq.py?at=default

@copyright: 2008, 2009 Radomir Dopieralski <qq@sheep.art.pl>
            2012, Niels Thykier <niels@thykier.net>
@license: BSD
                           BSD LICENSE

Copyright (c) 2008, 2009, Radomir Dopieralski
All rights reserved. 

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

import pygame
import operator
import functools

from chrono.model.direction import Direction
from chrono.view.tile_cache import TileCache

from chrono.view.translation import MAP_TILE_WIDTH, MAP_TILE_HEIGHT

def update_background(tiles, background, level, field, fixup=False, grid=False, overlays=None):
    pos = field.position
    if overlays is None:
        overlays = {}
    def wall(pos):
        if 0 <= pos.x < level.width and 0 <= pos.y < level.height:
            return level.get_field(pos).is_wall
        return True

    wall_dir2 = lambda pos, d: wall(pos.dir_pos(d))
    wall_dir = functools.partial(wall_dir2, pos)

    if wall(pos):
        tile = 3, 3
        # Draw different tiles depending on neighbourhood
        if not wall_dir(Direction.SOUTH):
            if wall_dir(Direction.WEST) and wall_dir(Direction.EAST):
                tile = 1, 2
            elif wall_dir(Direction.EAST):
                tile = 0, 2
            elif wall_dir(Direction.WEST):
                tile = 2, 2
            else:
                tile = 3, 2
        else:
            south = pos.dir_pos(Direction.SOUTH)
            if wall_dir2(south, Direction.EAST) and wall_dir2(south, Direction.WEST):
                # Walls at SW, S and SE
                tile = 1, 1
            elif wall_dir2(south, Direction.EAST):
                # Walls at S and SE
                tile = 0, 1
            elif wall_dir2(south, Direction.WEST):
                # Walls at SW and S
                tile = 2, 1
            else:
                tile = 3, 1
        # Add overlays if the wall may be obscuring something
        if not wall_dir(Direction.NORTH):
            if wall_dir(Direction.EAST) and wall_dir(Direction.WEST):
                over = 1, 0
            elif wall_dir(Direction.EAST):
                over = 0, 0
            elif wall_dir(Direction.WEST):
                over = 2, 0
            else:
                over = 3, 0
            overlays[pos] = tiles[over[0]][over[1]]
    else:
        tile = 0, 3
    tile_image = tiles[tile[0]][tile[1]]
    background.blit(tile_image,
                    (field.x * MAP_TILE_WIDTH, field.y * MAP_TILE_HEIGHT))

    if fixup:
        for d in (Direction.NORTH, Direction.SOUTH, Direction.WEST, Direction.EAST):
            ff = level.get_field(field.position.dir_pos(d))
            update_background(tiles, background, level, ff, fixup=False, overlays=overlays)
        rect = background.get_rect()
        for x in range(MAP_TILE_WIDTH, level.width * MAP_TILE_WIDTH, MAP_TILE_WIDTH):
            pygame.draw.line(background, (0, 0, 0), (x, 0), (x, rect.h))
        for y in range(MAP_TILE_HEIGHT, level.height * MAP_TILE_HEIGHT, MAP_TILE_HEIGHT):
            pygame.draw.line(background, (0, 0, 0), (0, y), (rect.w, y))

    return overlays

def make_background(level, tileset=None, map_cache=None, grid=False):
    if tileset is None:
        tileset = "tileset" # default is literally "tileset"
    if map_cache is None:
        self._map_cache = TileCache(MAP_TILE_WIDTH, MAP_TILE_HEIGHT)
    tiles = map_cache[tileset]
    gates = {}
    image = pygame.Surface((level.width*MAP_TILE_WIDTH,
                            level.height*MAP_TILE_HEIGHT))
    overlays = {}
    ub = functools.partial(update_background, tiles, image, level, overlays=overlays, grid=False)

    for field in level.iter_fields():
        ub(field)

    if grid:
        rect = image.get_rect()
        for x in range(MAP_TILE_WIDTH, level.width * MAP_TILE_WIDTH, MAP_TILE_WIDTH):
            pygame.draw.line(image, (0, 0, 0), (x, 0), (x, rect.h))
        for y in range(MAP_TILE_HEIGHT, level.height * MAP_TILE_HEIGHT, MAP_TILE_HEIGHT):
            pygame.draw.line(image, (0, 0, 0), (0, y), (rect.w, y))

    return image, overlays
