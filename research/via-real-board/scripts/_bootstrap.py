#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file _bootstrap.py
@brief Puts the import paths of this investigation in order; every script imports it first (`import _bootstrap`), so scripts run from any folder.
@details The own `lib` comes first, then the libraries of the studies it builds on (point-via-convergence, sor-with-via-couplings, solid3d-verification); the repository root is
         appended last so that a copy of the program given in PYTHONPATH wins over it.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]                  # research/via-real-board
for extra in (str(HERE.parent), str(HERE.parent / "solid3d-verification" / "lib"), str(HERE.parent / "sor-with-via-couplings" / "lib"),
              str(HERE.parent / "point-via-convergence" / "lib"), str(HERE.parent / "gerber-import" / "lib"), str(HERE / "lib")):
    if extra not in sys.path:
        sys.path.insert(0, extra)
REPO = str(HERE.parents[1])
if REPO not in sys.path:
    sys.path.append(REPO)                                   # the repository root, to import pcbthermal when no other copy is given
