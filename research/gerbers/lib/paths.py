"""!
@file paths.py
@brief The folders of the Gerber research, found from this file so that scripts, tests and modules agree wherever they are run from.
@details ROOT is research/gerbers, REPO the repository root. DATA (downloaded boards and the synthetic files), OUT (caches and logs) are git-ignored; FIGURES is committed.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]           # research/gerbers
REPO = ROOT.parents[1]                               # repository root (to import pcbthermal)
DATA = ROOT / "data"                                 # downloaded boards, conformance files, synthetic files (git-ignored)
OUT = ROOT / "out"                                   # caches and results of the studies (git-ignored)
FIGURES = ROOT / "figures"                           # the pictures (committed)
