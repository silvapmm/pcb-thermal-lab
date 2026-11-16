#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_thin_copper_check.py
@brief Review check: on 35 um copper, is the true surface-minus-mean of the top copper under a heater of the size of the harness boards' heaters in the milli-kelvin range, and how does it compare with the bound q'' t / 2k that README 4.1 quotes?
@details Three simplified stacks (full 35 um copper / 1.53 mm FR-4 k 0.3 / 35 um copper, 50 x 50 mm, film 10 W/m2K on both faces) carry the heater flux of three harness
         boards (example_board 1.5 W on 6 x 6 mm, plate_pad 5 W on 8 x 8 mm, part_top_path 3 W on 6 x 6 mm) in the independent solver tests/helpers/layered3d.py (4 sub-slabs per
         copper layer). Prints the surface, the surface minus the copper-layer mean and the bounds q'' t / 3k and q'' t / 2k.
         Usage: .venv/bin/python research/readout-conventions/scripts/study_thin_copper_check.py   (about 10 s, under 0.5 GB)
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests", "helpers"))
import layered3d as L                                          # noqa: E402

W = 50e-3
DX = 0.5e-3
T_CU = 35e-6
K_CU = 385.0
CASES = [("example_board flux, 1.5 W on 6 mm", 1.5, 6e-3), ("plate_pad flux, 5 W on 8 mm", 5.0, 8e-3), ("part_top_path flux, 3 W on 6 mm", 3.0, 6e-3)]


def main():
    """!
    @brief Run the three stacks and print one line each.
    @return None.
    """
    n = int(round(W / DX))
    c = W / 2
    j = n // 2
    sl = (slice(j - 1, j + 1), slice(j - 1, j + 1))              # the four cells around the centre
    for name, p, a in CASES:
        r = L.solve(DX, n, n, [(T_CU, K_CU, 4), (1.53e-3, 0.3, 8), (T_CU, K_CU, 4)], (c - a / 2, c - a / 2, c + a / 2, c + a / 2), p, 10.0, 10.0)
        dz = np.array(r["dz"])
        w = dz[:4] / dz[:4].sum()                                # weights of the top copper sub-slabs
        col = np.tensordot(w, np.array(r["T"])[:4], axes=(0, 0))
        s, m = float(r["surface_top"][sl].mean()), float(col[sl].mean())
        q = p / a**2
        print(f"{name:36s} surface {s:8.3f} K  surface - mean {1e3 * (s - m):6.3f} mK  q''t/3k {1e3 * q * T_CU / (3 * K_CU):6.3f}  q''t/2k {1e3 * q * T_CU / (2 * K_CU):6.3f} mK"
              f"  ratio to the bound {(s - m) / (q * T_CU / (2 * K_CU)):.3f}")


if __name__ == "__main__":
    main()
