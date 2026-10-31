#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file paths.py
@brief The folders of this investigation and the places where the (git-ignored) Gerber data can be found, so that scripts and tests agree wherever they are run from.
@details ROOT is research/via-real-board and REPO the repository root. The downloaded boards live in the git-ignored `data/` of `research/gerber-import`; in an isolated worktree that
         folder is empty, so `gerber_data()` also looks in the main checkout (found through `git rev-parse --git-common-dir`) and in the environment variable PCBT_GERBER_DATA.
         Nothing of a third party is copied into this folder: the studies read the files in place.
"""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]           # research/via-real-board
REPO = ROOT.parents[1]                               # repository root (to import pcbthermal)
OUT = ROOT / "out"                                   # results of the studies (git-ignored)
FIGURES = ROOT / "figures"                           # the pictures (committed)
POINT_VIA = ROOT.parent / "point-via-convergence"    # the treatment under test
SOR_VIA = ROOT.parent / "sor-with-via-couplings"     # the block SOR prototype
SOLID_VER = ROOT.parent / "solid3d-verification"     # the independent 3D solver
GERBER_IMPORT = ROOT.parent / "gerber-import"        # the reader of the Gerber and Excellon files


def gerber_data():
    """!
    @brief The folder that holds the downloaded boards (one sub-folder per board, see `gerber-import/scripts/fetch_boards.py`).
    @details Order: the environment variable PCBT_GERBER_DATA, the `data/` of this worktree's gerber-import, the same folder of the main checkout of the repository.
    @return Path of the first folder that exists; the worktree's own folder when none does (a fetch then writes there).
    """
    env = os.environ.get("PCBT_GERBER_DATA")
    if env and Path(env).is_dir():
        return Path(env)
    own = GERBER_IMPORT / "data"
    if own.is_dir() and any(own.iterdir()):
        return own
    try:
        common = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--git-common-dir"], capture_output=True, text=True, check=True).stdout.strip()
        main = (Path(common) if Path(common).is_absolute() else (REPO / common)).resolve().parent
        other = main / "research" / "gerber-import" / "data"
        if other.is_dir():
            return other
    except (OSError, subprocess.CalledProcessError):
        pass
    return own
