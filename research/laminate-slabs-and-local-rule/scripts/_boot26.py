#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file _boot26.py
@brief Import paths of research/laminate-slabs-and-local-rule: its own lib first, then the libraries and scripts of paper-case-studies, analytic-edge-spatial and laminate-nodes (read only), then the repository root.
@details Every script of the folder imports it first (`import _boot26`). The program is imported, never edited.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
OUT = HERE / "out"
FIGURES = HERE / "figures"
R = HERE.parent
for extra in (R / "paper-case-studies" / "scripts", R / "paper-case-studies" / "lib", R / "gerber-real-boards" / "lib", R / "lumped-zones-adoption" / "lib",
              R / "analytic-edge-spatial" / "lib", HERE / "lib"):      # (laminate-nodes has its own, different ref3d.py: not on the path)
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))        # inserted one by one: the own lib ends up first
if str(REPO) not in sys.path:
    sys.path.append(str(REPO))
OUT.mkdir(exist_ok=True)
