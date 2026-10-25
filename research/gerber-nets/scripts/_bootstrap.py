"""!
@file _bootstrap.py
@brief Puts the import paths of this investigation (phase 3) in order; every script imports it first (`import _bootstrap`), so scripts run from any folder.
@details The own `lib` comes first, then the `lib` and `scripts` of the phases it depends on (gerber-import); the repository root is appended last, so a patched copy of the program given in PYTHONPATH wins over it.
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
    sys.path.append(REPO)                              # the repository root, to import pcbthermal when no other copy is given
