#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_rows.py
@brief The measured impact of the candidate on the baseline of research/gap-subdivision: its 52 pad boards (converged graded 3D reference) and its 44 uniform boards (exact series), the program's Analytic against the candidate with 1, 2 and 4 nodes through every gap.
@details Question: how many of the designed boards of the common baseline change, in which direction, and does a board with copper everywhere stay where it is? The reference values are the committed
         columns `ref_K` of research/gap-subdivision/baseline/pads.csv (graded 3D, limit fitted) and uniform.csv (exact series); the program's Analytic column is recomputed here (it must equal the
         committed `analytic_K`). The candidate is lib/defect.py with 1 mm tiles. Writes data/rows_pads.csv and data/rows_uniform.csv.
         Usage: .venv/bin/python research/analytic-partial-copper/scripts/study_rows.py   (from the repository root; about 10 minutes).
"""

import csv

import _bootstrap as BS
import boards as B
import defect as D
from pcbthermal import SolverOptions, simulate

BASELINE = BS.REPO / "research" / "gap-subdivision" / "baseline"


def read(name):
    """!
    @brief Read a committed baseline table.
    @param name File name in research/gap-subdivision/baseline.
    @return list of dict rows (strings).
    """
    with open(BASELINE / name) as fh:
        return list(csv.DictReader(fh))


def pad_board(r):
    """!
    @brief The Board of a row of pads.csv.
    @param r Row.
    @return boards.Board.
    """
    layers = int(r["layers"])
    last = layers - 1
    bottom = r["bottom"]
    kw = dict(pad_layers=(0,), empty_layers=())
    if bottom == "empty":
        kw["empty_layers"] = (last,)
    elif bottom == "pad":
        kw["pad_layers"] = tuple(range(layers))
    return B.Board(r["tag"], layers=layers, gap=float(r["gap_mm"]), copper=float(r["copper_um"]), size=float(r["size_mm"]), source=float(r["source_mm"]),
                   h_top=float(r["h_top"]), h_bottom=float(r["h_bottom"]), stack=r["stack"], pad=float(r["pad_mm"]), **kw)


def uniform_board(r):
    """!
    @brief The Board of a row of uniform.csv.
    @param r Row.
    @return boards.Board.
    """
    return B.Board(r["sweep"], layers=int(r["layers"]), gap=float(r["gap_mm"]), copper=float(r["copper_um"]), size=float(r["size_mm"]), source=float(r["source_mm"]),
                   h_top=float(r["h_top"]), h_bottom=float(r["h_bottom"]), stack=r["stack"])


def run(rows, make, ns):
    """!
    @brief The program's Analytic and the candidate on every row.
    @param rows Rows of a baseline table.
    @param make Function row -> Board.
    @param ns Nodes through the gap to run (the candidate).
    @return list of dict rows.
    """
    out = []
    for r in rows:
        bd = make(r)
        p = B.problem(bd)
        cell = float(r["cell_mm"])
        prog = simulate(p, SolverOptions(models=("analytic",), cell_mm=cell)).results["analytic"].t_max - p.board.ambient
        row = {"tag": r.get("tag", r["sweep"]), "layers": bd.layers, "ref_K": float(r["ref_K"]), "committed_K": float(r["analytic_K"]), "analytic_K": float(prog)}
        for n in ns:
            # More than 16 nodes make the modal matrices large (300 x 300 x nodes^2): skipped, written as NaN
            row[f"cand{n}_K"] = float("nan")
            if bd.layers + (bd.layers - 1) * (n - 1) <= 16:
                try:
                    row[f"cand{n}_K"] = D.solve(p, n_sub=n, tile_mm=D.tile_for(p), cell_mm=cell)["max"]
                except ValueError:
                    pass                                      # too many tiles for the dense system: no value
        print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
        out.append(row)
    return out


def main():
    """!
    @brief Run both tables and print the errors.
    @return None.
    """
    pads = BS.cached("rows_pads", lambda: run(read("pads.csv"), pad_board, (1, 2, 4)))
    uni = BS.cached("rows_uniform", lambda: run(read("uniform.csv"), uniform_board, (1, 2)))
    for name, rows in (("rows_pads", pads), ("rows_uniform", uni)):
        with open(BS.DATA / f"{name}.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    for name, rows in (("pads", pads), ("uniform", uni)):
        print(f"\n{name}: error against the reference (%): program | n=1 | n=2 | n=4")
        for r in rows:
            e = lambda k: 100 * (r[k] / r["ref_K"] - 1)
            tail = f" | {e('cand4_K'):+6.1f}" if "cand4_K" in r else ""
            print(f"{r['tag']:26s} L{r['layers']} ref {r['ref_K']:7.2f}  {e('analytic_K'):+7.1f} | {e('cand1_K'):+6.1f} | {e('cand2_K'):+6.1f}{tail}")
        print(" max |program - committed| / committed:", max(abs(r["analytic_K"] / r["committed_K"] - 1) for r in rows))


if __name__ == "__main__":
    main()
