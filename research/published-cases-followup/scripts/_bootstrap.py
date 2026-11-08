#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file _bootstrap.py
@brief Puts the import paths of research/published-cases-followup in order; every script imports it first (`import _bootstrap`), so the scripts run from any folder.
@details Order: the own `lib`, the `lib` of effective-conductivity (its `layered3d.py` is the independent 3D solver, imports nothing from the program), the repository root (the program, read only).
         Sets a private PCBTHERMAL_CONFIG so that the user's preferences never change a number.
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
OUT = HERE / "out"
FIGURES = HERE / "figures"
os.environ.setdefault("PCBTHERMAL_CONFIG", "/tmp/pcbthermal-config-published-cases")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
for extra in (str(HERE.parent / "effective-conductivity" / "lib"), str(HERE / "lib")):
    if extra not in sys.path:
        sys.path.insert(0, extra)
if str(REPO) not in sys.path:
    sys.path.append(str(REPO))
OUT.mkdir(exist_ok=True)
