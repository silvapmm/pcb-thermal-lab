#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_frozen.py
@brief Which of the 17 frozen-regression boards (and the shipped examples) move under each candidate via treatment, and by how much (FVM and FDM, steady state).
@details For every board of tests/regression/regress_boards.py that has vias, and every variant of lib/viavariants.py, the maximum temperature of the FVM and the FDM at 2 and 1 mm
         is compared with the program as it is. `sheet` and `plane` hand footprints with uniform sheet conductance to the program's code, so a board whose footprints all sit on
         uniform copper must show a shift of exactly 0.0; `star` changes every via a little (it is a different coupling, calibrated to the same lone-via resistance).
         Also counts the vias whose footprint is not uniform in at least one layer ("partial" vias).
         Run from the repository root: `.venv/bin/python research/via-partial-copper/scripts/study_frozen.py`.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests", "regression"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import regress_boards as B                                                    # noqa: E402

import numpy as np                                                            # noqa: E402

from pcbthermal import fdm, fvm                                               # noqa: E402

import viavariants as vv                                                      # noqa: E402
from pcbthermal import viawell as vw                                          # noqa: E402


def partial_vias(problem, cell_mm):
    """!
    @brief Number of vias whose geometric footprint has a sheet conductance that is not uniform in some layer.
    @param problem Problem.
    @param cell_mm Cell size in mm.
    @return int.
    """
    net = fvm.Network(problem, max(int(round(problem.board.width * 1000 / cell_mm)), 2), max(int(round(problem.board.height * 1000 / cell_mm)), 2))
    if not problem.vias:
        return 0
    L = problem.board.layers
    cover = net.cover
    rel = [np.where(cover > 0, net.S[l] / np.where(cover > 0, cover, 1.0), 0.0) for l in range(L)]
    n = 0
    for v, share in zip(problem.vias, problem.via_board_shares()):
        if share <= 0:
            continue
        w, _, _ = vw.footprint(v.x, v.y, v.diameter / 2.0, net.dx, 0.0, cover, net.dy, 0.0)
        keys = list(w)
        if keys and any(np.ptp([rel[l][c] for c in keys]) > 1e-9 * max(rel[l][keys[0]], 1e-300) for l in range(L)):
            n += 1
    return n


def tmax(problem, model, cell):
    """!
    @brief Maximum temperature of a layered steady run.
    @param problem Problem.
    @param model "fvm" or "fdm".
    @param cell Cell in mm.
    @return float in degC.
    """
    r = (fvm.solve_steady if model == "fvm" else fdm.solve_steady)(problem, cell)
    return float(r.t_max)


def main():
    """!
    @brief Run and print.
    @return None.
    """
    rows = {}
    print(f"{'board':22s} {'vias':>5s} {'cell':>5s} {'partial':>7s} {'model':5s} {'current':>9s} {'d sheet':>9s} {'d plane':>9s} {'d star':>9s}")
    for name in B.board_names():
        p = B.build(name)
        if not p.vias:
            continue
        for cell in (2.0, 1.0, 0.5):
            npart = partial_vias(p, cell)
            for model in ("fvm", "fdm"):
                base = tmax(B.build(name), model, cell)
                d = {}
                for variant in ("sheet", "plane", "star"):
                    with vv.patched(variant):
                        d[variant] = tmax(B.build(name), model, cell) - base
                rows[f"{name}|{cell}|{model}"] = dict(vias=len(p.vias), partial=npart, base=base, **d)
                print(f"{name:22s} {len(p.vias):5d} {cell:5.1f} {npart:7d} {model:5s} {base:9.3f} {d['sheet']:9.4f} {d['plane']:9.4f} {d['star']:9.4f}", flush=True)
    os.makedirs(os.path.join(os.path.dirname(HERE), "out"), exist_ok=True)
    with open(os.path.join(os.path.dirname(HERE), "out", "frozen.json"), "w") as fh:
        json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    main()
