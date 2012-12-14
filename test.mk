#!/usr/bin/make -f

LVL_EXT := .txt
LSF_EXT := .lsf
CAMPAIGNS := $(wildcard levels/*$(LSF_EXT))
PLAYABLE_MAPS := $(wildcard levels/*$(LVL_EXT))
SOLVABLE_TESTS := $(wildcard tests/solvable/*$(LVL_EXT))
TIMEPARADOX_TESTS := $(wildcard tests/time-paradox/*$(LVL_EXT))

check: $(SOLVABLE_TESTS) $(PLAYABLE_MAPS) $(TIMEPARADOX_TESTS) $(CAMPAIGNS)
	./check-level.py --solvable $(SOLVABLE_TESTS)
	./check-level.py --solvable $(PLAYABLE_MAPS)
	./check-level.py --test-time-paradox $(TIMEPARADOX_TESTS)
	./check-campaign.py $(CAMPAIGNS)
