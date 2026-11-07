#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_frozen_models.py
@brief Review check: how far would the barrel rule d + 0.5 t_cu move the frozen records of the Lumped and the Analytic (their vias use the same k_cu A / d) and the times to 63 %?
@details The rule is installed for every model at once by scaling `Via.thermal_area` by d / (d + a t_cu) (the mean gap and copper thickness of the board; the five via boards
         of the harness have equal gaps, so this is the rule of lib/barrel.py for the FVM and FDM, which the script checks against out/frozen.json). The 3D solid draws the
         barrel through the copper slabs, so the rule does not apply to it and it is not run. Steady maximum at 2, 1 and 0.5 mm through the harness (`run_one`, the
         records of the frozen test) and the time to 63 % of every part (`t63`, the harness's transient). Nothing of the program is edited; the patch is removed on exit.
         Run from the repository root: `.venv/bin/python research/via-contact-geometry/scripts/study_frozen_models.py`; writes out/frozen_models.json.
"""

import contextlib
import json
import logging
import sys

import _bootstrap  # noqa: F401
import numpy as np

import regress_boards as B
import regress_harness as H
from pcbthermal import model as M

logging.disable(logging.WARNING)
_ORIG = M.Via.thermal_area


@contextlib.contextmanager
def barrel_rule(problem, a):
    """!
    @brief Scale the barrel cross-section of every via of every model by d / (d + a t_cu) for the duration of a with-block.
    @param problem The Problem (its board gives the gap and the copper thickness).
    @param a Extra length per gap in copper thicknesses.
    @return context manager.
    """
    b = problem.board
    t = np.asarray(b.copper_thickness, dtype=float)
    d = float(np.mean(b.gap_thicknesses()))
    scale = d / (d + a * float(t.mean()))

    def area(self, plating, k_copper):
        """!
        @brief The scaled thermal area.
        @param plating Plating in m.
        @param k_copper Copper conductivity in W/mK.
        @return float m^2.
        """
        return scale * _ORIG(self, plating, k_copper)

    M.Via.thermal_area = area
    try:
        yield scale
    finally:
        M.Via.thermal_area = _ORIG


def main():
    """!
    @brief Run and print.
    @return None.
    """
    rows = {}
    for name in B.board_names():
        p = B.build(name)
        if not p.vias:
            continue
        for model in ("fvm", "fdm", "lumped", "analytic"):
            for cell in (2.0, 1.0, 0.5):
                base = H.run_one(B.build(name), name, model, cell)
                with barrel_rule(p, 0.5) as s:
                    new = H.run_one(B.build(name), name, model, cell)
                if base["status"] != "ok" or new["status"] != "ok":
                    print(f"{name:20s} {model:8s} {cell:4.1f} {base['status']} {new['status']}")
                    continue
                dt = new["t_max"] - base["t_max"]
                rows[f"{name}|{model}|{cell}"] = dict(scale=s, base=base["t_max"], shift=dt, rise=base["t_max"] - base["ambient"])
                print(f"{name:20s} {model:8s} {cell:4.1f} scale {s:.4f} t_max {base['t_max']:9.3f} shift {dt:+8.4f} K ({100 * dt / (base['t_max'] - base['ambient']):+.3f} % of the rise)", flush=True)
            t0 = H.t63(B.build(name), model)
            with barrel_rule(p, 0.5):
                t1 = H.t63(B.build(name), model)
            for q0, q1 in zip(t0["parts"], t1["parts"]):
                if q0["t63_s"] and q1["t63_s"]:
                    rel = 100.0 * (q1["t63_s"] / q0["t63_s"] - 1.0)
                    rows[f"{name}|{model}|t63|{q0['name']}"] = dict(base=q0["t63_s"], new=q1["t63_s"], rel=rel)
                    print(f"{name:20s} {model:8s} t63 {q0['name']:12s} {q0['t63_s']:9.3f} s -> {q1['t63_s']:9.3f} s ({rel:+.3f} %)", flush=True)
    with open(_bootstrap.OUT / "frozen_models.json", "w") as fh:
        json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    sys.exit(main())
