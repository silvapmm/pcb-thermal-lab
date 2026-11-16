#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file conftest.py
@brief Runs the tests of this folder against the program with the Lumped first link of 2.7.1, the one its copies of the network were made from, or against an older program.
@details From 2.8.0 (fix/lumped-edge-first-link, item M3 of the 2.8.0 table) the program reads the first link of the Lumped network with the mirror images of the board
         sides; the copies in lib/ predate it. `lumped.IMAGE_MAX_CELLS = 0` is the program's own fallback (the plain first link for every footprint), so "the program" of
         these tests is the network of 2.7.1 again. `PCBT_LUMPED_FIRST_LINK=2.8.0` runs the program as it ships (the equality tests then fail by design).
         Tests that patch the program's source text (STALE) cannot apply to 2.8.0 and are skipped there; `PCBT_PROGRAM_TREE=<folder>` imports an extracted older program
         instead (`git archive v2.7.1 pcbthermal | tar -x -C <folder>`), where they run. README, section 'Obsolete since 2.8.0'.
"""

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
TREE = os.environ.get("PCBT_PROGRAM_TREE")          # A folder holding an extracted older program (git archive v2.7.1 pcbthermal | tar -x -C <folder>), imported first
if TREE:
    sys.path.insert(0, os.path.abspath(TREE))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from pcbthermal import lumped                                                # noqa: E402

NEW_LUMPED = hasattr(lumped, "IMAGE_MAX_CELLS")      # The Lumped of 2.8.0 (first link with the images, part read-out); absent in v2.7.1
STALE = ()                                           # Tests of a copy of the program's source text that cannot apply to the 2.8.0 program (skipped there, run them on v2.7.1)
STALE_REASON = ""
PINNED = ()                                          # Tests that compare with numbers frozen from an old commit; they fail on every later program (also on v2.7.1)
PINNED_REASON = ""

FIRST_LINK = os.environ.get("PCBT_LUMPED_FIRST_LINK", "2.7.1")


def pytest_collection_modifyitems(config, items):
    """!
    @brief Skip, on the program of 2.8.0, the tests listed in STALE (they run when PCBT_PROGRAM_TREE points at an older program), and the tests listed in PINNED unless PCBT_RUN_PINNED=1.
    @param config The pytest configuration.
    @param items The collected test items.
    """
    run_pinned = os.environ.get("PCBT_RUN_PINNED") == "1"
    for item in items:
        if NEW_LUMPED and (item.originalname in STALE or item.name in STALE):
            item.add_marker(pytest.mark.skip(reason="stale since 2.8.0: " + STALE_REASON))
        elif not run_pinned and (item.originalname in PINNED or item.name in PINNED):
            item.add_marker(pytest.mark.skip(reason="pinned to an old commit, failing before 2.8.0 too: " + PINNED_REASON + " (PCBT_RUN_PINNED=1 runs it)"))


@pytest.fixture(autouse=True)
def lumped_first_link_of_2_7_1():
    """!
    @brief Set the plain first link of 2.7.1 for every test of the folder (unless PCBT_LUMPED_FIRST_LINK=2.8.0) and restore the program's value after it.
    @return None (a generator fixture).
    """
    if not NEW_LUMPED:                               # An older program has the plain link already
        yield
        return
    saved = lumped.IMAGE_MAX_CELLS
    if FIRST_LINK == "2.7.1":
        lumped.IMAGE_MAX_CELLS = 0
    yield
    lumped.IMAGE_MAX_CELLS = saved
