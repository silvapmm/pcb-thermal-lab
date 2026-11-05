#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file paths.py
@brief Import paths of this investigation: its own lib, the independent reference of research/via-real-board and research/point-via-convergence, and the repository root.
@details Every script and test imports it first. The repository root is appended last so that a copy of the program given in PYTHONPATH wins.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]                  # research/via-edge-image
RESEARCH = HERE.parent
for extra in (RESEARCH / "via-real-board" / "lib", RESEARCH / "point-via-convergence" / "lib", HERE / "lib"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))
REPO = str(RESEARCH.parent)
if REPO not in sys.path:
    sys.path.append(REPO)
