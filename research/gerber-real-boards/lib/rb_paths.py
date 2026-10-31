#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file rb_paths.py
@brief The folders of the investigation "real boards" (found from this file, so scripts, tests and modules agree wherever they are run from).
@details ROOT is research/gerber-real-boards; DATA holds the downloaded open boards (git-ignored, filled by scripts/fetch_boards.py), OUT the results and caches of the studies
         (git-ignored), FIGURES the committed pictures. The module is named rb_paths because research/gerber-import/lib and research/gerber-models/lib both have a module called paths.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]           # research/gerber-real-boards
REPO = ROOT.parents[1]                               # repository root (to import pcbthermal)
DATA = ROOT / "data"                                 # downloaded open boards (git-ignored)
OUT = ROOT / "out"                                   # results and caches of the studies (git-ignored)
FIGURES = ROOT / "figures"                           # the pictures (committed)
