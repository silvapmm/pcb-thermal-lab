#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file _bootstrap.py
@brief Puts the import paths of research/gap-subdivision in order; every script imports it first, so scripts run from any folder.
@details The own `lib` first, the lib of research/bare-spot-under-source (the layered copy of the program's FVM with sub-gaps and the resolved 3D solver), the repository root (the program,
         imported and never edited) and research/ (diagram_kit). OUT is the git-ignored folder of caches; BASELINE is the committed folder of the machine-readable baseline.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
OUT = HERE / "out"
FIGURES = HERE / "figures"
BASELINE = HERE / "baseline"
for extra in (str(HERE / "lib"), str(REPO / "research" / "bare-spot-under-source" / "lib"), str(REPO), str(HERE.parent)):
    if extra not in sys.path:
        sys.path.insert(0, extra)
OUT.mkdir(exist_ok=True)
BASELINE.mkdir(exist_ok=True)
