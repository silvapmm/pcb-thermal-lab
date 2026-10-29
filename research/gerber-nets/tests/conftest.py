#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file conftest.py
@brief Puts the modules and the studies of this investigation (phase 3) and of the phases it depends on (gerber-import) on the import path, and the repository root last (to import pcbthermal).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
for extra in (
    str(HERE.parent / "gerber-import" / "lib"),
    str(HERE.parent / "gerber-import" / "scripts"),
    str(HERE / "scripts"),
    str(HERE / "lib"),
):
    while extra in sys.path:                           # move it to the front even when Python already put it there (the script's own folder): same-named modules of
        sys.path.remove(extra)                         # gerber-import (make_figures, paths, ...) must not shadow the ones of this folder
    sys.path.insert(0, extra)
REPO = str(HERE.parents[1])
if REPO not in sys.path:
    sys.path.append(REPO)
