#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_causes.py
@brief Separates the causes of the error of the Analytic model on boards with a copper pad: the truncation of the series, the weighted fill of the uniform sheet, and the structure of the model (one node per copper layer, the laminate of a one-layer board as a film).
@details Question: of the shortfall (or excess) of the Analytic against the resolved 3D solution on a pad board, how much belongs to each candidate cause?
         For every board of study_baseline.py (the references are read from its cache):
         * (a) the copy of the modal solution (lib/modal.py) with the program's sheet conductances equals `analytic.solve_steady`;
         * (b) the number of modes (300 -> 600) and the sampling cell (0.5 -> 0.25 mm) move the peak by less than ...: the series has no pad edge to truncate, the pad enters only through the fill;
         * (c) the fill of the copper layer that reproduces the reference (f*) against the program's weighted fill and the plain area fraction of the pad;
         * (d) the **structure with the copper exact**: the program's FVM with one node per copper layer and, for a one-layer board, one laminate node whose laminate is a film in series with the
           bottom film (the Analytic's structure; the laminate nodes of laminate.py switched off in memory), i.e. what a perfect treatment of the pad would give with the nodes the Analytic has;
         * (e) the decomposition: (Analytic - structure) is the cost of the uniform sheet, (structure - reference) the cost of the nodes;
         * (f) whether the input warning of the program fired and its spread value; (g) the same physical board entered as one layer and as two layers with a bare second one.
         Writes data/causes.csv. Usage: .venv/bin/python research/analytic-partial-copper/scripts/study_causes.py   (from the repository root; run study_baseline.py first; about 10 minutes).
"""

import csv
import re

import numpy as np
from scipy.optimize import brentq

import _bootstrap as BS
import modal as M
import pads as P
from pcbthermal import SolverOptions, laminate, simulate
from study_baseline import board


def analytic_info(bd, p):
    """!
    @brief The program's Analytic result: peak rise, the weighted fill and the warnings.
    @param bd A Pad.
    @param p The Problem.
    @return dict.
    """
    res = simulate(p, SolverOptions(models=("analytic",), cell_mm=0.5)).results["analytic"]
    spread = [float(x) for w in res.warnings for x in re.findall(r"spread ([0-9.]+)", w)]
    return {"peak": float(res.t_max - p.board.ambient), "warned": bool(spread), "spread": spread[0] if spread else 0.0}


def structure_fvm(bd, p):
    """!
    @brief The FVM with the nodes of the Analytic: one node per copper layer, a one-layer board with the laminate as a film in series (laminate nodes switched off in memory).
    @param bd A Pad.
    @param p The Problem.
    @return Rise in K.
    """
    if bd.layers > 1:
        return P.program_rise(bd, "fvm", 0.5, p)
    keep = laminate.LAMINATE_NODES
    try:
        ps = laminate.series_bottom_problem(p)
        laminate.LAMINATE_NODES = 0
        return float(simulate(ps, SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"].t_max - p.board.ambient)
    finally:
        laminate.LAMINATE_NODES = keep


def one_board(bd, ref):
    """!
    @brief All the cause measurements of one board.
    @param bd A Pad.
    @param ref Reference peak in K.
    @return dict.
    """
    p = P.problem(bd)
    pr, sh = M.program_sheet(p, 0.5)
    info = analytic_info(bd, p)
    cp = M.solve(pr, sh)["max"]
    out = {"layers": bd.layers, "second": bd.second, "pad_mm": bd.pad or 0.0, "ref_K": ref, "analytic_K": info["peak"], "parity_rel": abs(cp / info["peak"] - 1.0),
           "warned": info["warned"], "spread": info["spread"]}
    # (b) series truncation and sampling
    pr2, sh2 = M.program_sheet(p, 0.25)
    out["modes600_rel"] = M.solve(pr, sh, n_terms=600)["max"] / cp - 1.0
    out["cell025_rel"] = M.solve(pr2, sh2)["max"] / cp - 1.0
    # (c) fills
    out["fill_weighted"] = float(sh["fill"][0])
    out["fill_area"] = ((bd.pad or bd.size) / bd.size) ** 2

    def err(x):
        fl = sh["fill"].copy()
        fl[0] = x
        return M.solve(pr, sh, M.sheet_from_fill(sh, fl), n_terms=150)["max"] - ref

    try:
        out["fill_fitted"] = float(brentq(err, 0.0, 1.0, xtol=1e-4))
    except ValueError:
        out["fill_fitted"] = float("nan")
    # (d) and (e)
    out["structure_K"] = structure_fvm(bd, p)
    out["cost_sheet_pct"] = 100.0 * (out["analytic_K"] - out["structure_K"]) / ref
    out["cost_nodes_pct"] = 100.0 * (out["structure_K"] - ref) / ref
    out["analytic_pct"] = 100.0 * (out["analytic_K"] / ref - 1.0)
    return out


def compute():
    """!
    @brief Run the cause measurements on the boards of the baseline.
    @return list of dict rows.
    """
    base = BS.cached("baseline", lambda: (_ for _ in ()).throw(RuntimeError("run study_baseline.py first")))
    rows = []
    for r in base:
        if r["pad_mm"] == 0.0:
            continue                                         # the cause study is about partial copper
        bd = board(r["layers"], r["second"], r["pad_mm"])
        rows.append(one_board(bd, r["ref_K"]))
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
    return rows


def main():
    """!
    @brief Run the study and write data/causes.csv.
    @return None.
    """
    rows = BS.cached("causes", compute)
    with open(BS.DATA / "causes.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("\nlayers second pad | ref | analytic % | cost of the sheet % | cost of the nodes % | fill weighted/area/fitted | warned")
    for r in rows:
        print(f"{r['layers']} {r['second']:5s} {r['pad_mm']:4.0f} | {r['ref_K']:6.1f} | {r['analytic_pct']:+6.1f} | {r['cost_sheet_pct']:+6.1f} | {r['cost_nodes_pct']:+6.1f} | "
              f"{r['fill_weighted']:.3f} {r['fill_area']:.3f} {r['fill_fitted']:.3f} | {r['warned']} {r['spread']:.2f}")
    print("max parity:", max(r["parity_rel"] for r in rows), " modes600:", max(abs(r["modes600_rel"]) for r in rows), " cell:", max(abs(r["cell025_rel"]) for r in rows))
    one = {r["pad_mm"]: r for r in rows if r["layers"] == 1}
    two = {r["pad_mm"]: r for r in rows if r["layers"] == 2 and r["second"] == "empty"}
    print("same physical board, one layer vs two with a bare second (Analytic K):", {k: (round(one[k]["analytic_K"], 1), round(two[k]["analytic_K"], 1)) for k in one if k in two})


if __name__ == "__main__":
    main()
