#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file _bootband.py
@brief Import paths of research/laminate-edge-band: its own lib first, then the case library and the independent 3D solver of analytic-edge-spatial (read only), then the repository root.
@details Every script of the folder imports it first (`import _bootband`). The program is imported from this tree, never edited.
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = Path(os.environ.get("LAMEDGE_TREE", HERE.parents[1]))      # the tree whose pcbthermal is measured (default: this one; LAMEDGE_TREE=<worktree> for another)
OUT = Path(os.environ.get("LAMEDGE_OUT", HERE / "out"))
FIGURES = HERE / "figures"
R = HERE.parent
for extra in (R / "analytic-edge-spatial" / "lib", HERE / "lib"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))
if str(REPO) in sys.path:
    sys.path.remove(str(REPO))
sys.path.insert(0, str(REPO))                 # this tree's pcbthermal before any installed copy
OUT.mkdir(exist_ok=True)
import pcbthermal  # noqa: E402,F401  (imported now, so that a later sys.path change in a library cannot swap the tree)
