#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_real_boards.py
@brief The gap subdivision on three windows of a real board (the Stormduino drawn as polygons), after the simple boards: n nodes in every cell or only in the cells that show laminate, against the fine independent reference.
@details Question: do the lessons of the designed boards (a thick-gap board with bare laminate around the copper is cool in the FVM; n = 3 or 4 nodes remove most of it, at the cell size where the in-plane error is
         positive) hold on a real layout? The windows, the board data and the fine reference (0.125 mm, 2 sub-slabs per gap, `reference_rise` of research/zone-union/lib/reference.py) are those of
         research/bare-spot-under-source/scripts/study_real_stormduino.py, imported as they are (read only); the Stormduino must have been fetched by research/gerber-import/scripts/fetch_boards.py
         (found in this worktree or in the main checkout; nothing downloaded is committed). Two-layer 1.6 mm board, 35 um copper, isotropic laminate 0.3 W/mK, 6 x 6 mm part of 1 W, h = 10 / 10 W/m2K.
         The reference is cached in out/real_reference.json. Cells 1 and 0.5 mm; rows: the program, n = 2, 3, 4, 6, 8 in every cell, in the bare cells plus a margin of a gap thickness, and the same with the half-layer correction of the copper-free node.
         Output: the table on the screen and baseline/real_boards.csv.
         Usage: .venv/bin/python research/gap-subdivision/scripts/study_real_boards.py   (from the repository root; the reference takes several minutes per window the first time).
"""

import csv
import json
import sys

import _bootstrap as BS
import gapnodes as G

BARE = BS.REPO / "research" / "bare-spot-under-source" / "scripts"
ZU = BS.REPO / "research" / "zone-union"
for extra in (str(BARE), str(ZU / "lib"), str(ZU / "scripts"), str(BS.REPO / "tests" / "helpers")):
    if extra not in sys.path:
        sys.path.append(extra)

import study_real_stormduino as SRS                                         # noqa: E402  (windows(), read only)

CELLS = (1.0, 0.5)
NS = (2, 3, 4, 6, 8)


def reference(wins):
    """!
    @brief The fine reference of every window (cached).
    @param wins List of (key, Problem, polygons).
    @return dict key -> {"0.25": {...}, "0.125": {...}} with the peak (max) and mean.
    """
    path = BS.OUT / "real_reference.json"
    res = json.loads(path.read_text()) if path.exists() else {}
    import reference as ref
    for key, p, polys in wins:
        if key in res:
            continue
        res[key] = {}
        for dx in (0.25, 0.125):
            r = ref.reference_rise(p, polys, dx, k_lam=0.3, n_gap=2)
            res[key][str(dx)] = {"max": float(r["max"]), "mean": float(r["mean"])}
            print(key, dx, res[key][str(dx)], flush=True)
        path.write_text(json.dumps(res))
    return res


def main():
    """!
    @brief Run the windows and write the table.
    @return None.
    """
    wins = SRS.windows()
    refs = reference(wins)
    rows = []
    for key, p, _ in wins:
        amb = p.board.ambient
        fine = refs[key]["0.125"]["max"]
        for cell in CELLS:
            base = G.run(p, cell, 1, "none")
            # The 3D solver on the program's own cell fill (8 sub-slabs per gap): the through-thickness error alone, the pattern inside the cell being the program's scalar fill
            net = G.LY.network(p, cell)
            cf = SRS.cell_fill_solver(p, net, cell)["max"]
            line = f"{key:12s} cell {cell:3.1f} fine ref {fine:8.2f} K, cell-fill solver {cf:8.2f} K  program {base['peak']:8.2f} (fine {100 * (base['peak'] / fine - 1):+6.1f}, z {100 * (base['peak'] / cf - 1):+6.1f} %)"
            rows.append({"window": key, "cell_mm": cell, "variant": "program", "n": 1, "peak_K": round(base["peak"], 3), "ref_K": round(fine, 3), "cellfill_K": round(cf, 3), "unknowns": base["unknowns"]})
            for where, half in (("all", False), ("bare", False), ("bare", True)):
                vals = []
                tag = where + ("+half" if half else "")
                for n in NS:
                    r = G.run(p, cell, n, where, half_layer=half)
                    vals.append(r["peak"])
                    rows.append({"window": key, "cell_mm": cell, "variant": tag, "n": n, "peak_K": round(r["peak"], 3), "ref_K": round(fine, 3), "cellfill_K": round(cf, 3), "unknowns": r["unknowns"]})
                line += f" | {tag} fine: " + " ".join(f"{100 * (v / fine - 1):+6.1f}" for v in vals) + " z: " + " ".join(f"{100 * (v / cf - 1):+6.1f}" for v in vals)
            print(line, flush=True)
    with open(BS.BASELINE / "real_boards.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)


if __name__ == "__main__":
    main()
