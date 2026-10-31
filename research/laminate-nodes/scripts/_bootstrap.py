#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file _bootstrap.py
@brief Puts the import paths of research/laminate-nodes in order; every script imports it first (`import _bootstrap`), so scripts run from any folder.
@details Order: the own `lib`, then the `lib` of the two folders whose references and copies are reused as they are (bare-spot-under-source: the resolved 3D solver and the
         closed forms; gap-subdivision: the exact series and the graded pad solver), then the repository root (the program, read only). A patched copy of the program in
         PYTHONPATH wins over the root. `gerber_out()` finds the folder of the 42 real windows of the Gerber research (git-ignored, it lives in the main checkout; the environment
         variable LAMNODES_GERBER_OUT overrides the search when this folder is run from a worktree that has no copy of it).
"""

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
OUT = HERE / "out"
FIGURES = HERE / "figures"
for extra in (str(HERE / "lib"), str(HERE.parent / "bare-spot-under-source" / "lib"), str(HERE.parent / "gap-subdivision" / "lib"), str(HERE.parent)):
    if extra not in sys.path:
        sys.path.insert(0, extra)
if str(REPO) not in sys.path:
    sys.path.append(str(REPO))
OUT.mkdir(exist_ok=True)


def gerber_out():
    """!
    @brief Folder `research/gerber-import/out` that holds `windows_native.npz` (the 42 real windows of 36 mm at 0.1 mm pixels).
    @details Looked for in the environment variable LAMNODES_GERBER_OUT, in this checkout and in the main checkout (the parent of `.claude/worktrees/<agent>` when this folder
             is in a worktree).
    @return pathlib.Path, or None when the file is not found.
    """
    cands = []
    if os.environ.get("LAMNODES_GERBER_OUT"):
        cands.append(Path(os.environ["LAMNODES_GERBER_OUT"]))
    cands.append(HERE.parent / "gerber-import" / "out")
    for parent in HERE.parents:
        if parent.name == "worktrees" and parent.parent.name == ".claude":
            cands.append(parent.parent.parent / "research" / "gerber-import" / "out")
    for c in cands:
        if (c / "windows_native.npz").exists():
            return c
    return None
