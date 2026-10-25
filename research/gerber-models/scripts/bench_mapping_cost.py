"""!
@file bench_mapping_cost.py
@brief What do the mappings cost on a board-sized layer? Time and peak memory of the bounds (lambda) and of the flow-based faces for 0.5 to 8 million pixels.
@details A random two-phase mask (60 % copper, grains of a few pixels) at 0.1 mm, 1 mm cells; the cost is per layer and is paid once at import (the result can be cached with the project).
         Run: .venv/bin/python research/gerber-models/scripts/bench_mapping_cost.py (from the repository root) (about 2 minutes).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

import resource
import sys
import time

import numpy as np
from scipy import ndimage

import conduction as cd


def mask(h, w, seed=0):
    """!
    @brief A random mask with grains of about 3 pixels and 60 % copper.
    @param h Rows.
    @param w Columns.
    @param seed Seed.
    @return Boolean array.
    """
    r = ndimage.gaussian_filter(np.random.default_rng(seed).random((h, w)), 1.5)
    return r > np.quantile(r, 0.4)


def main():
    """!
    @brief Time each mapping for several layer sizes.
    @return None.
    """
    print(f"{'layer (mm)':>12s}{'pixels':>12s}{'lambda s':>10s}{'dual s':>10s}{'cell problem s':>16s}{'peak MB':>9s}")
    for h_mm, w_mm in ((40, 50), (60, 80), (100, 80), (100, 160)):
        h, w = int(h_mm / 0.1), int(w_mm / 0.1)
        S = cd.sheet_of(mask(h, w))
        n = 10
        blk = cd.cell_blocks(S, n)
        t = time.time(); cd.map_lambda(blk, 0.5); t_lam = time.time() - t
        t = time.time(); cd.dual_faces(S, n, 0); t_dual = time.time() - t
        t = time.time(); cd.map_cell_problem(blk); t_cell = time.time() - t
        print(f"{h_mm:6d} x {w_mm:<4d}{h * w:12,d}{t_lam:10.2f}{t_dual:10.1f}{t_cell:16.1f}{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024 if sys.platform == "darwin" else 1024):9.0f}", flush=True)


if __name__ == "__main__":
    main()
