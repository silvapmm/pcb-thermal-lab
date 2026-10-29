#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file conftest.py
@brief Puts the solver and the studies of this investigation on the import path, and the repository root last (to import pcbthermal).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
for extra in (str(HERE / "scripts"), str(HERE / "lib")):
    if extra not in sys.path:
        sys.path.insert(0, extra)
REPO = str(HERE.parents[1])
if REPO not in sys.path:
    sys.path.append(REPO)
