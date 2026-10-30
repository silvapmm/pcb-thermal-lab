#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file _bootstrap.py
@brief Puts the import paths of research/bare-spot-under-source in order; every script imports it first, so scripts run from any folder.
@details The own `lib` first, the repository root (the program, imported and never edited) and research/ (diagram_kit). OUT is the git-ignored folder of caches and results.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
OUT = HERE / "out"
FIGURES = HERE / "figures"
for extra in (str(HERE / "lib"), str(REPO), str(HERE.parent)):
    if extra not in sys.path:
        sys.path.insert(0, extra)
OUT.mkdir(exist_ok=True)
