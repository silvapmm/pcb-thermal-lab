#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file _bootstrap.py
@brief Puts the import paths of research/paper-case-studies in order; every script imports it first (`import _bootstrap`), so scripts run from any folder.
@details Order: the own `lib`, the `lib` of gerber-real-boards (its `ref3d.py` is the independent anisotropic 3D reference and imports nothing from the program), the `lib` of
         lumped-zones-adoption (its `shen_case.py` has Shen's equations and the axisymmetric solver of the via unit cell), the repository root (the program, read only).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
OUT = HERE / "out"
FIGURES = HERE / "figures"
for extra in (str(HERE.parent / "lumped-zones-adoption" / "lib"), str(HERE.parent / "gerber-real-boards" / "lib"), str(HERE / "lib")):
    if extra not in sys.path:
        sys.path.insert(0, extra)           # inserted one by one, so the own lib ends up first
if str(REPO) not in sys.path:
    sys.path.append(str(REPO))
OUT.mkdir(exist_ok=True)
