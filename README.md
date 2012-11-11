ChronoShift
===========

ChronoShift is simple turn-based puzzle game, taking ideas from
[chronotron] [1] and [Sokoban] [2].

This is a school project and thus we cannot accept ideas or
contributions before we have turned in our project "mid" December
2012.  After that, I will happily accept ideas and patches.

[1]: http://www.kongregate.com/games/Scarybug/chronotron "chronotron"
[2]: http://en.wikipedia.org/wiki/Sokoban "Sokoban"

Instructions (Playing)
======================

To play a level you "simply" run:

 $ ./demo.py path/to/level

Example:

 $ ./demo.py levels/tutorial01.txt

(Default) Keymappings are:

 * WASD (or arrow keys) for moving
 * Space to skip a turn
 * Enter for entering the time machine
   (active clone must be on the time machine)
   - A time-jump "finishes" when the last clone enters the time
     machine!
 * F2 for printing the actions taken (in "solution format").
   - One line per clone.

Keep in mind that trying to do an _illegal_ move will count as an
action!

All valid actions are carried "simultaneously".

The goal is to obtain the goal (shown as a house atm) and return to
start (the highlighted bluish ground).  The solution must be
determistic and not cause time-paradoxes!

Time-paradox and non-determinism
--------------------------------

There are two ways to fail a level.  One is trying to cause
non-determinism and the other one is to cause a time-paradox.

Non-determinism can appear if two different actions in the same turn
are valid on their own, but both cannot occur.  This can happen if two
clones are trying to push the same crate in ortogonal directions
(Parallel directions are "safe").  Note that the game reports these
errors as a time-paradox.

Time-paradoxes occur if your "past self" cannot get back to the time
machine.  If it does not get back to time machine, it could not have
become the "current self" that (indirectly) prevented it from reaching
the time machine (and so on).

Finally, the solution may not cause a clone or crate to end its turn
on a closed gate.  Nor can a clone or a crate share the same field at
the end of a turn.

Interacting with the game world
-------------------------------

There are a few different elements in the game world that can be used
to obtain the goal (or get in your way):

 * field
   - A field is just a square on the game world.  A crate or 1+
     clone(s) may be on it.
   - Represented by the "dirt" (or "stone-road") tiles
 * wall
   - Impassible for both crates and clones.
   - Represented by the "grass" tiles
 * gate
   - A gate is either open (behaves like a field) or closed (behaves
     like a wall). Its state can be toggled by buttons.
   - Represented by the blue circle.  The closed gate will have a
     white center and an open gate will be all blue.
 * button
   - A button modifies the state of gates.  As long as a crate or 1+
     clones are on it, the button is "activated".  Otherwise it is
     deactivated.
   - Represented by a green circle.
 * crate
   - A pushable wall.  It is pushed by the same rules as Sokoban.
   - Represented by the crate.
 * time machine
   - The time machine is the start location.
   - Represented by a bluish field tile.
 * goal
   - The field you have to obtain.
   - Represented by a house (will disappear when obtained)

A couple of hints:

 * Buttons can affect multiple gates.
 * Two (or more) buttons can control the same gate.
 * Two buttons controlling the same gate will cancel each other out if
   both are activated.
   - This rule is generalized as "even" number of activated buttons
     cancels out each other.
 * Crates do not have to be pushed back to start.

Scoring
-------

Like some Sokoban games, you are scored by the number of moves you
make.  So a lower score is better (i.e. more efficient) than a high.

The scoring rules are:

 * 1 point per move or skipped turn by the "current" clone.
   - Entering the time machine counts as a move.
 * 1 point per skipped turn while the current clone is outside the time machine.
   - 0 points per skipped turn while the current clone is inside the time machine.
 * 1 point for every clone crated (after the first).


Instructions (Installing/Setup)
===============================

There is no real installation proceedure at this time.  The following dependencies
are known:

 * python 2.7
   - 2.5+ probably works, provided "argparse" is available
 * pygame

The Debian/Ubuntu packages for these are:

 * python2.7
   - Debian/Wheezy or "recent" Ubuntu the package "python" will be enough.
 * python-pygame
 * python (>= 2.7) | python2.7 | python-argparse

Note: Even if you have python2.7, your /usr/bin/python may point to python2.6.  If
so, replace:

  $ ./demo.py path/to/level

with

  $ python2.7 ./demo.py path/to/level


Level format
============

Writing a level can be done in a simple level enter.  The format is:

 * First line must be "2D SuperFun!" (case-sensitive and all).
 * Line 2 up to the first empty line is the representation of the Map
   (in ASCII).  Every line must have same width and there must be all
   around the map.  The following glyphs are available:

   * '+' is a wall
   * ' ' (i.e. space) is a field
   * '-' is a closed gate
   * '_' is an open gate
   * 'b' is a button
   * 'B' is a button that can only be activated by a crate (not implemented atm)
   * 'c' is a field with a crate on top of it
   * 'S' is the start/time machine location
   * 'G' is the goal field

 * After the reprentation comes the section for connecting buttons
   with gates.  This section can be omitted if it is not needed _and_
   no section follows it.  These following rules are supported:

   * "nothing"
     - Useful if no rules are needed, but a section follows this section.
   * "button (x1, y1) -> gate (x2, y2)"
     - Connects a button at (x1, y1) with the gate on (x2, y2).  The
       top left corner of the representation is (0, 0).

 * The last section is the "level" metadata.  It uses the syntax for Debian control
   files (similar to mail-headers) and consists of at most one paragraph.  It can
   be omitted if not needed.  The following fields are have a meaning.

   * Description
     - A short human readable description of the level.  It may be
       presented before the level is played.
   * Solution
     - A solution to the level (see below).  This is also used for
       testing the game.


Solution format
---------------

The solution field of maps (if present) consists of a number of
"1-letter" encoding of the actions.  Spaces (and the mandatory " ."
for empty lines) are ignored.  The encoding are as the following:

 * "N"
   - "move up"  (mnemonic: "move North")
 * "E"
   - "move right"  (mnemonic: "move East")
 * "S"
   - "move down"  (mnemonic: "move South")
 * "W"
   - "move left"  (mnemonic: "move West")
 * "H"
   - "skip turn"  (mnemonic: "Hold position")
 * "T"
   - "enter time machine"  (mnemonic: "Time machine")
   - Next action is then intended for next the clone.

For readability, solutions are usually formatted with "one line" per
clone.

