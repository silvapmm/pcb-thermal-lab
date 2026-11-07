#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file _bootstrap.py
@brief Paths for the scripts of this folder: the own lib, the lib of via-partial-copper (the variants of the via logic), the repository root (the program, read only).
@details Sets a private PCBTHERMAL_CONFIG so that the user's preferences never change a number, and the offscreen Qt platform.
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
OUT = HERE / "out"
FIGURES = HERE / "figures"
os.environ.setdefault("PCBTHERMAL_CONFIG", "/tmp/pcbthermal-config-via-contact")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
for extra in (str(HERE / "lib"), str(HERE.parent / "via-partial-copper" / "lib"), str(REPO / "tests" / "regression")):
    if extra not in sys.path:
        sys.path.insert(0, extra)
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
OUT.mkdir(exist_ok=True)
