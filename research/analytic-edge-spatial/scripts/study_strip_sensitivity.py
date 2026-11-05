#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_strip_sensitivity.py
@brief How much do the tile size and the number of modes matter to the strips-as-heatsinks treatment of the edge, and what does the Robin basis cost against it?

@details 30 x 20 and 100 x 80 mm, 2 layers of 1.6 and 3.2 mm, h_side 50 and 200, a 10 mm 2 W part at the centre and in a corner (16 boards). The strips treatment with the edge
         tiles of 1, 2.5 and 5 mm and 64 or 150 modes in the Green function of the tiles, and the Robin basis, against the FVM at 0.5 mm: the error of the hottest rise and the time.
         It shows why the first prototype (tiles of the program's 2.5 to 5 mm, 64 modes) left errors of 1 to 11 % that a fine ring does not have.

         Run from the repository root: .venv/bin/python research/analytic-edge-spatial/scripts/study_strip_sensitivity.py  (about 5 minutes)
"""

import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import analytic_edge as ae   # noqa: E402
import cases                 # noqa: E402


def main():
    """!
    @brief Run the 16 boards and print the summary per variant.
    @return int 0.
    """
    variants = [("strips 5 mm, 64 modes", dict(edge="strips", strip_mm=5.0, strip_modes=64)), ("strips 2.5 mm, 64 modes", dict(edge="strips", strip_mm=2.5, strip_modes=64)),
                ("strips 2.5 mm, 150 modes", dict(edge="strips", strip_mm=2.5, strip_modes=150)), ("strips 1 mm, 64 modes", dict(edge="strips", strip_mm=1.0, strip_modes=64)),
                ("strips 1 mm, 150 modes", dict(edge="strips", strip_mm=1.0, strip_modes=150)), ("robin", dict(edge="robin"))]
    errs = {v[0]: [] for v in variants}
    tms = {v[0]: [] for v in variants}
    for (w, h) in ((30, 20), (100, 80)):
        for t in (1.6, 3.2):
            for hs in (50.0, 200.0):
                for pos in ("centre", "corner"):
                    p, _ = cases.board(w, h, 2, t, hs, pos)
                    f05 = cases.rise(p, "fvm", 0.5)
                    line = []
                    for name, kw in variants:
                        t0 = time.time()
                        e = ae.solve(p, 1.0, **kw)["t_max"] - cases.T0
                        tms[name].append(time.time() - t0)
                        errs[name].append(100 * (e / f05 - 1))
                        line.append(f"{errs[name][-1]:+6.2f}")
                    print(f"{w}x{h} t{t} hs{hs:4.0f} {pos:6s} | " + " ".join(line) + " %", flush=True)
    print("\nvariant                    mean |err|  max |err|  signed range         mean time")
    for name, _ in variants:
        e = np.array(errs[name])
        print(f"{name:26s} {np.abs(e).mean():8.2f} % {np.abs(e).max():8.2f} %  {e.min():+6.2f} to {e.max():+6.2f} %  {np.mean(tms[name]):6.2f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
