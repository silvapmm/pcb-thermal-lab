"""!
@file paths.py
@brief The folders of this investigation (phase 2 of the Gerber research), found from this file so that scripts, tests and modules agree wherever they are run from.
@details ROOT is research/gerber-models, REPO the repository root. DATA is shared by the three phases and lives in research/gerber-import/data (downloaded boards, conformance and synthetic files; git-ignored);
         OUT (caches and results of the studies, git-ignored) and FIGURES (committed) belong to this folder.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]           # research/gerber-models
REPO = ROOT.parents[1]                               # repository root (to import pcbthermal)
DATA = ROOT.parent / "gerber-import" / "data"        # downloaded boards, conformance files, synthetic files (git-ignored, shared by the three phases)
OUT = ROOT / "out"                                   # caches and results of the studies (git-ignored)
FIGURES = ROOT / "figures"                           # the pictures (committed)
