#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_reproduce.py
@brief Reproduce the cold spot and the exaggerated via effect of the current program on clean partial-copper boards, against the 3D solid at fine cells.
@details For every case of lib/cases.py (edge, track, island, antipad, bare) and every cell size, runs the FVM, the FDM and the 3D solid with and without the via
         and prints: the maximum rise with the via, the via effect (rise without minus rise with), the local cold spot around the via and the minimum rise over the board.
         Run from the repository root: `.venv/bin/python research/via-partial-copper/scripts/study_reproduce.py [--quick]`.
         Light (a 16 x 16 mm board; the 3D solid at 0.125 mm is about 120 000 unknowns).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import cases                                                                  # noqa: E402


def main():
    """!
    @brief Print the table of the reproduction.
    @return None.
    """
    quick = "--quick" in sys.argv
    plan = [("edge", dict(delta=0.0)), ("edge", dict(delta=0.3)), ("edge", dict(delta=-0.3)), ("track", dict(width=0.4)), ("track", dict(width=1.0)),
            ("island", dict(side=1.2)), ("antipad", dict(hole=1.0)), ("antipad", dict(hole=1.0, land=0.6)), ("antipad", dict(hole=2.0)), ("bare", dict())]
    cells = [1.0, 0.5, 0.25] if quick else [1.0, 0.5, 0.25, 0.125]
    print(f"{'case':26s} {'model':8s} {'cell':>6s} {'rise via':>9s} {'no via':>9s} {'effect':>8s} {'cold spot':>10s} {'min rise':>9s} {'balance':>8s}")
    for name, kw in plan:
        label = name + "".join(f" {k}={v}" for k, v in kw.items())
        f = cases.CASES[name]
        for model in ("solid3d", "fvm", "fdm"):
            for cell in cells:
                if model == "solid3d" and cell > 0.5:
                    continue
                with_via, no_via = f(**kw), f(with_via=False, **kw)
                a, b = cases.run(with_via, model, cell), cases.run(no_via, model, cell)
                print(f"{label:26s} {model:8s} {cell:6.3f} {a['tmax']:9.3f} {b['tmax']:9.3f} {b['tmax'] - a['tmax']:8.3f} {a['cold']:10.3f} {a['tmin']:9.3f} {a['balance']:8.4f}", flush=True)


if __name__ == "__main__":
    main()
