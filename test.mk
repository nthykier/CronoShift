#!/usr/bin/make -f

PLAYABLE_MAPS := $(wildcard tutorial*.txt)
SOLVABLE_TESTS := $(wildcard tests/solvable/*)

check: $(SOLVABLE_TESTS) $(PLAYABLE_MAPS)
	./check-level.py --solvable $(SOLVABLE_TESTS)
	./check-level.py --solvable $(PLAYABLE_MAPS)

