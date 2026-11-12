#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_real_boards.py
@brief Question 1: how much does the full-contact rule of the vias of an imported board (the program today) differ from a rim test read from the masks, on real boards?
@details For each board of the local library (never committed, numbers only) the board is imported as the program does (`ImportSession`), the vias are the plated holes, and for the
         parts with the most vias under or around them 1 W is put in the part (one at a time). The FVM (and the FDM at the first cell) is run twice at every cell: the program as it is
         (`viawell.rim_copper_shares` returns 1.0 on every layer for imported copper) and with `lib/rimmask.py` installed (48 samples on the drill circle looked up in the mask).
         Printed: the share of the (via, layer) pairs of the board whose rim touches no copper (share 0) and the mean share, and for each part the hottest rise of the two runs.
         Not verified: a physical board; the parts' powers are 1 W each (a comparison, not a prediction); a board without parts (gi-storm, gi-alleg) is judged only by its via statistics.
         Run (from the repository root): .venv/bin/python research/imported-via-rim/scripts/study_real_boards.py <board> <cells mm comma list> [n_parts] [fdm]
         with the library as PCBT_REAL_BOARDS (the folder `real` of the boards library, each with `gerber/`).
"""

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
import rimmask                                                  # noqa: E402  (also puts the repository root on the path)
from pcbthermal import api, viawell                             # noqa: E402
from pcbthermal.gui.import_session import ImportSession        # noqa: E402

REACH = float(os.environ.get("PCBT_REACH_MM", "0.5"))
REAL = Path(os.environ.get("PCBT_REAL_BOARDS", "pcb-library/real"))


def session(board, cell):
    """!
    @brief Import session of a library board (the JLC placement file is switched off where two exist).
    @param board Folder name in the library.
    @param cell Cell in mm.
    @return ImportSession.
    """
    sx = ImportSession()
    sx.set_files(str(REAL / board / "gerber"))
    for i, f in enumerate(sx.files):
        if f.name == "cpl_jlc.csv":
            sx.set_use(i, False)
    sx.load()
    sx.cell_mm = cell
    return sx


def via_stats(prob):
    """!
    @brief Statistics of the rim shares read from the masks.
    @param prob Problem with imported copper.
    @return dict with the number of vias, the share of (via, layer) pairs with share 0, with share below 1 and the mean share, per layer.
    """
    L = prob.board.layers
    zi = viawell._zone_index(prob, L)
    sh = np.array([rimmask.rim_shares_masks(prob, v, L, zi) for v in prob.vias]).reshape(-1, L)
    return {"vias": len(prob.vias), "zero_per_layer": [float((sh[:, l] <= 0).mean()) for l in range(L)] if len(sh) else [],
            "below1_per_layer": [float((sh[:, l] < 1).mean()) for l in range(L)] if len(sh) else [],
            "mean_per_layer": [float(sh[:, l].mean()) for l in range(L)] if len(sh) else []}


def candidates(sx, prob, n):
    """!
    @brief The parts with the most vias within their box (grown by 3 mm).
    @param sx ImportSession.
    @param prob Problem with the vias.
    @param n Number of parts.
    @return list of designators.
    """
    vx = np.array([[v.x, v.y] for v in prob.vias]).reshape(-1, 2)
    # The parts are in the Gerber frame, the vias and the heaters in the board frame: give every part 1 W, build, and read the heater polygons (board frame, m)
    for p in sx.parts():
        sx.set_part(p.designator, power=1.0)
    pr = sx.build_problem()
    score = []
    for h in pr.heaters:
        poly = np.asarray(h.polygon, float)
        lo, hi = poly.min(0) - 3e-3, poly.max(0) + 3e-3
        k = int(((vx >= lo) & (vx <= hi)).all(1).sum())
        score.append((k, h.name))
    for p in sx.parts():
        sx.set_part(p.designator, power=0.0)
    score.sort(reverse=True)
    return [d for k, d in score[:n] if k > 0]


def main(argv):
    """!
    @brief Run the comparison.
    @param argv board, cells, number of parts, optional 'fdm'.
    @return int exit code.
    """
    board, cells = argv[1], [float(c) for c in argv[2].split(",")]
    n = int(argv[3]) if len(argv) > 3 else 3
    use_fdm = len(argv) > 4 and argv[4] == "fdm"
    out = {"board": board, "runs": []}
    sx = session(board, cells[0])
    prob0 = sx.build_problem()
    st = via_stats(prob0)
    print(board, "layers", prob0.board.layers, "vias", st["vias"], "rim share 0 per layer", [round(x, 3) for x in st["zero_per_layer"]],
          "share<1", [round(x, 3) for x in st["below1_per_layer"]], flush=True)
    out["via_stats"] = st
    des = candidates(sx, prob0, n)
    for ci, cell in enumerate(cells):
        for d in des:
            s2 = session(board, cell)
            s2.set_part(d, power=1.0)
            prob = s2.build_problem()
            if not prob.heaters:
                continue
            row = {"cell": cell, "part": d}
            for m in (("fvm", "fdm") if use_fdm and ci == 0 else ("fvm",)):
                res = {}
                for label in ("today", "mask rim"):
                    if label == "mask rim":
                        rimmask.install(0.5, REACH)                 # ray test: copper continuous from the drill circle out to REACH
                    else:
                        rimmask.uninstall()
                    t0 = time.time()
                    r = api.simulate(prob, api.SolverOptions(models=(m,), cell_mm=cell)).results[m]
                    res[label] = r.t_max - prob.board.ambient
                    res[label + " s"] = time.time() - t0
                rimmask.uninstall()
                row[m] = res
                print("%-8s cell %.2f %-4s %-5s today %.3f K  mask rim %.3f K  (%+.1f %%)  %.0fs" % (board, cell, m, d, res["today"], res["mask rim"],
                      100 * (res["mask rim"] / res["today"] - 1), res["today s"] + res["mask rim s"]), flush=True)
            out["runs"].append(row)
    (HERE.parent / "out").mkdir(exist_ok=True)
    json.dump(out, open(HERE.parent / "out" / f"real_{board}.json", "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
