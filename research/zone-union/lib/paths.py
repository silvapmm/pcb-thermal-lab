"""!
@file paths.py
@brief The folders of the zone-union investigation, found from this file so that scripts and tests agree wherever they are run from.
@details ROOT is research/zone-union, REPO the repository root; OUT (results, the variant of the program) is git-ignored; FIGURES is committed.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]           # research/zone-union
REPO = ROOT.parents[1]                               # repository root
LIB = ROOT / "lib"
OUT = ROOT / "out"                                   # caches, results and the variant of the program (git-ignored)
FIGURES = ROOT / "figures"                           # the pictures (committed)
SOLVER = REPO / "tests" / "helpers"                  # the independent 3D solver layered3d.py (imports nothing of the program)
