#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_real_stormduino.py
@brief Q4: the bare-spot error and the treatments on three windows of a real board (the Stormduino drawn as polygons, as in research/zone-union), against the independent solver run on the program's own cell fill and against the fine reference.
@details Question answered: on a real board, where the hottest cell under the part has no copper, how much of the error of the FVM is the layered idealisation (solver on the cell fill versus FVM) and how much do more laminate nodes and the vertical correction remove?
         Windows, board data and the fine reference are those of research/zone-union (scripts/study_real_board.py, lib/real_board.py, lib/reference.py: used as they are, read only; they need the
         Stormduino fetched by research/gerber-import/scripts/fetch_boards.py, found in this worktree or in the main checkout). Two-layer 1.6 mm board, 35 um copper, isotropic laminate 0.3 W/mK as in that study,
         6 x 6 mm part of 1 W on the top layer, h = 10 W/m2K on both faces. The program's own cell fill (4 x 4 samples, per-point union) is read from fvm.Network. The "cell-fill solver" is lib/resolved3d.py
         on that fill (copper slab conductivity k_lam + f (k_cu - k_lam), the gap in 8 slabs), peak of the surface under the part.
         Run from the repository root: .venv/bin/python research/bare-spot-under-source/scripts/study_real_stormduino.py [reference|treat]; out/real_board_*.json.
"""

import _bootstrap  # noqa: F401  (import paths)

import json
import sys
from pathlib import Path

import numpy as np

from _bootstrap import HERE, OUT

ZU = HERE.parent / "zone-union"
# Appended, not inserted first: zone-union/lib has a module `cases` too and ours must win
for extra in (str(ZU / "lib"), str(ZU / "scripts"), str(HERE.parents[1] / "tests" / "helpers")):
    if extra not in sys.path:
        sys.path.append(extra)

import cases as C                                                           # noqa: E402
import layered as LY                                                        # noqa: E402
import resolved3d as r3                                                     # noqa: E402
import treatments as TR                                                     # noqa: E402

CELLS = (1.0, 0.5)
TREATS = [{"kind": "none"}, {"kind": "vert"}] + [{"kind": "nodes", "n": n, "vert": True} for n in (2, 3, 4, 6)]


def windows():
    """!
    @brief The three windows and their Problems, from the zone-union study.
    @return list of (key, Problem, polygons-by-layer in m).
    """
    import real_board
    import study_real_board as srb
    objs, wins = srb.windows()
    out = []
    for x0, y0, _ in wins:
        w = real_board.window(objs, x0, y0, srb.SIZE)
        out.append((f"x={x0:.0f} y={y0:.0f}", srb.build(w, None), {k: [q * 1e-3 for q in v] for k, v in w.items()}))
    return out


def cell_fill_solver(p, net, cell):
    """!
    @brief The independent solver on the program's own cell fill: peak and mean of the surface under the part.
    @param p Problem.
    @param net fvm.Network of the problem at this cell.
    @param cell Cell in mm.
    @return dict with max, mean, fill_hot (copper fill of the hottest cell under the part).
    """
    nb = C.board_numbers(p)
    kl, kc = nb["k_gap_xy"][0], nb["k_cu"]
    n = net.nx
    slabs = [(nb["t_cu"][0], kl + net.fill[0] * (kc - kl), kl + net.fill[0] * (kc - kl), 1), (nb["gaps"][0], kl, nb["k_gap_z"][0], 8),
             (nb["t_cu"][1], kl + net.fill[1] * (kc - kl), kl + net.fill[1] * (kc - kl), 1)]
    h = p.heaters[0]
    x0, y0 = h.polygon.min(axis=0)
    x1, y1 = h.polygon.max(axis=0)
    r = r3.solve(cell * 1e-3, n, net.ny, slabs, (x0, y0, x1, y1), h.power, nb["h_top"], nb["h_bottom"])
    hot = np.unravel_index(np.where(r["mask"], r["surf"], -np.inf).argmax(), r["surf"].shape)
    return {"max": r["max"], "mean": r["mean"], "fill_hot": float(net.fill[0][hot])}


def reference():
    """!
    @brief The fine reference of each window (0.25 mm, 2 slabs per gap, as zone-union 8.2/8.3) and a 0.125 mm check.
    @return None (writes out/real_board_reference.json).
    """
    import reference as ref
    res = {}
    for key, p, polys in windows():
        res[key] = {}
        for dx in (0.25, 0.125):
            r = ref.reference_rise(p, polys, dx, k_lam=0.3, n_gap=2)
            res[key][str(dx)] = {"max": float(r["max"]), "mean": float(r["mean"])}
            print(key, dx, res[key][str(dx)], flush=True)
    json.dump(res, open(OUT / "real_board_reference.json", "w"), indent=1)


def treat():
    """!
    @brief The FVM of the program and the treatments against the cell-fill solver and the fine reference.
    @return None (writes out/real_board_treat.json and .txt).
    """
    refs = json.load(open(OUT / "real_board_reference.json"))
    res, lines = {}, []
    for key, p, polys in windows():
        gaps, kz, kxy = LY.gap_data(p)
        res[key] = {}
        for cell in CELLS:
            net = LY.network(p, cell)
            cf = cell_fill_solver(p, net, cell)
            row = {"cell_fill_solver": cf, "treat": {}}
            for t in TREATS:
                r = TR.run(p, net, t, gaps, kz, kxy)
                row["treat"][json.dumps(t)] = r
            res[key][str(cell)] = row
            fine = refs[key]["0.125"]["max"]
            for t, r in row["treat"].items():
                lines.append(f"{key:<12} cell {cell:>3} fill_hot {cf['fill_hot']:.2f} {t:<45} peak {r['peak']:7.2f}  vs cell-fill solver {100 * (r['peak'] / cf['max'] - 1):+6.1f}%  vs fine ref {100 * (r['peak'] / fine - 1):+6.1f}%  unknowns {r['unknowns']}")
            lines.append(f"{key:<12} cell {cell:>3} cell-fill solver {cf['max']:7.2f} (vs fine ref 0.125: {100 * (cf['max'] / fine - 1):+6.1f}%)")
            print("\n".join(lines[-len(TREATS) - 1:]), flush=True)
    json.dump(res, open(OUT / "real_board_treat.json", "w"), indent=1)
    Path(OUT / "real_board_treat.txt").write_text("\n".join(lines))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "treat"
    if what == "reference":
        reference()
    elif what == "treat":
        treat()
