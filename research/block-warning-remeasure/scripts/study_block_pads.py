#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_block_pads.py
@brief Where does 'the Lumped and Analytic metal block is within about 5 % of the FVM' hold? A plate joined to the board through one or several pads, swept.

@details Synthetic boards of ours (100 x 80 mm, two layers, full top copper, 1.5 mm aluminium plate (204 W/mK) on the bottom face, a bottom copper pad and a 6 mm part
         on the top face over each pad, 5 W in total, 3 : 1 : 1 : 1 by default). The FVM at the given cell is the reference; the Lumped and the Analytic (block as a ring layer and as a tile graph) are compared with it on
         (a) the block temperature (mean and maximum), (b) the temperature of each part, (c) the heat that enters the block (FVM and the models that report it).
         Error = (model - FVM) / FVM rise above ambient, in percent.
         The temperature of a part is the hottest value under its footprint. For the FVM and the Analytic that is the hottest value of their field; the Lumped paints its
         footprint with the ring-0 node (no peak term), so its part is ALSO read with its own peak (node + peak_extra + the other heaters at the centroid, the formula of
         lumped.solve_steady, columns `lumped_part_own` and `lumped_spread_own`); the field reading (`lumped_part_max`, `lumped_spread`) is kept for the record of the first
         pass, whose -8 to -17 % compared two different quantities (README 7).
         Sweeps (one factor at a time around a base case, plus the full grid of pad count x interface): pad count 1, 2, 4; pad side (area per pad);
         interface resistance; block size relative to the board; h on the block free face (h_extra).
         Usage (from the repository root, light: one process, coarse cell):
             .venv/bin/python research/block-warning-remeasure/scripts/study_block_pads.py [--cell-mm 1.0] [--set base|pads|interface|size|h|all] [--csv out/x.csv]
"""

import argparse
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pcbthermal import Problem, analytic, fvm, lumped                       # noqa: E402
from pcbthermal.analysis import heater_stats                                 # noqa: E402
from pcbthermal.geometry import polygon_centroid                             # noqa: E402

W, H, AMB = 100.0, 80.0, 25.0

# The networks the Lumped builds during one solve, captured by a wrapper of the module attribute in this process only (the program is not edited)
_CAPTURED = []
_ORIGINAL = lumped._heater_network


def _capture(*args, **kwargs):
    """!
    @brief Wrapper of lumped._heater_network that keeps every heater network of the current solve.
    @param args Positional arguments of lumped._heater_network.
    @param kwargs Keyword arguments of lumped._heater_network.
    @return The network dict of lumped._heater_network.
    """
    rn = _ORIGINAL(*args, **kwargs)
    _CAPTURED.append(rn)
    return rn


lumped._heater_network = _capture


def lumped_part_peaks(p, r):
    """!
    @brief The Lumped's own peak of every part, with the formula of lumped.solve_steady (own node + peak_extra + the other heaters read at the centroid).
    @param p Problem (every heater powered: one network per heater, in order).
    @param r SteadyResult of lumped.solve_steady for p, solved right after _CAPTURED was cleared.
    @return List of rises in K, one per heater.
    """
    ny, nx = r.T.shape[1:]
    nets = list(zip(p.heaters, _CAPTURED))
    out = []
    for hj, rj in nets:
        th = rj["theta"][hj.layer, 0] + rj["peak_extra"]
        cx, cy = polygon_centroid(hj.polygon)
        ij = (min(max(int(cy // r.dy), 0), ny - 1), min(max(int(cx // r.dx), 0), nx - 1))
        for hi, ri in nets:
            if ri is not rj:
                th += lumped._radial(ri, ri["dist"][ij], ri["theta"][hj.layer])
        out.append(float(th))
    return out


def pad_centres(n):
    """!
    @brief Centres of the pads on the 100 x 80 mm board.
    @param n Pad count (1, 2 or 4).
    @return List of (x, y) in mm.
    """
    if n == 1:
        return [(50.0, 40.0)]
    if n == 2:
        return [(30.0, 40.0), (70.0, 40.0)]
    return [(30.0, 25.0), (70.0, 25.0), (30.0, 55.0), (70.0, 55.0)]


def make(n_pads=2, pad=12.0, part=6.0, r_c=5e-4, block=(80.0, 60.0), thick=1.5, k=204.0, h_extra=0.0, power=5.0, unequal=True, with_block=True):
    """!
    @brief One synthetic board: top copper plane, a bottom copper pad under every part, a block joined to the bottom face.
    @param n_pads Number of pads (and parts).
    @param pad Pad side in mm.
    @param part Part side in mm (on the top face, over the pad).
    @param r_c Interface resistance block-to-copper in m2K/W.
    @param block Block width and height in mm, centred on the board.
    @param thick Block thickness in mm.
    @param k Block conductivity in W/mK.
    @param h_extra Extra coefficient on the block free face in W/m2K (0 = the face h of the board).
    @param power Total power in W, shared equally (or 3:1:1:1 / 3:1 when unequal, so that the sharing between pads is tested).
    @param unequal True for unequal part powers (first part carries three shares).
    @param with_block False for the control board with the block removed (the error of the models on the board alone).
    @return Problem.
    """
    p = Problem.new(W, H, 2).add_zone(1, rect=(0, 0, W, H))
    bx0, by0 = (W - block[0]) / 2, (H - block[1]) / 2
    shares = [3.0] + [1.0] * (n_pads - 1) if unequal else [1.0] * n_pads
    for (cx, cy), sh in zip(pad_centres(n_pads), shares):
        p.add_zone(2, rect=(cx - pad / 2, cy - pad / 2, cx + pad / 2, cy + pad / 2))
        p.add_heater(1, power * sh / sum(shares), rect=(cx - part / 2, cy - part / 2, cx + part / 2, cy + part / 2))
    if with_block:
        p.add_heatsink(2, h_extra, rect=(bx0, by0, bx0 + block[0], by0 + block[1]), thickness_mm=thick, k=k, contact_r=r_c)
    return p


def metrics(model, p, cell):
    """!
    @brief Block and part temperatures of one model on one problem.
    @param model 'fvm', 'lumped' or 'analytic'.
    @param p Problem.
    @param cell Cell in mm.
    @return dict: block_mean, block_max (K above ambient, nan if the model does not report), parts (list of part rises, hottest field value under the footprint),
            parts_own (the Lumped's own part peaks; the same as parts for the other models), t_max rise, w_block (nan if not reported).
    """
    mod = {"fvm": fvm, "lumped": lumped, "analytic": analytic}[model]
    _CAPTURED.clear()
    r = mod.solve_steady(p, cell_mm=cell)
    rows = heater_stats(r, p)
    ex = r.extras
    nan = float("nan")
    parts = [row["t_max"] - AMB for row in rows]
    own = lumped_part_peaks(p, r) if model == "lumped" else parts
    return {"block_mean": ex.get("block_bottom_mean", nan) - AMB, "block_max": ex.get("block_bottom_max", nan) - AMB,
            "parts": parts, "parts_own": own, "rise": r.t_max - AMB, "w_block": ex.get("block_bottom_w_to_block", nan)}


def compare(label, p, cell):
    """!
    @brief Error of the Lumped and Analytic against the FVM for one board.
    @param label Case label.
    @param p Problem.
    @param cell Cell in mm.
    @return dict with the FVM numbers and the errors (percent of the FVM rise) per model and per quantity.
    """
    ref = metrics("fvm", p, cell)
    out = {"label": label, "rise_fvm": ref["rise"], "block_fvm": ref["block_mean"], "w_block_fvm": ref["w_block"]}
    for m in ("lumped", "analytic"):
        v = metrics(m, p, cell)
        out[f"{m}_hot"] = (v["rise"] - ref["rise"]) / ref["rise"] * 100.0
        out[f"{m}_block_mean"] = (v["block_mean"] - ref["block_mean"]) / ref["rise"] * 100.0 if np.isfinite(v["block_mean"]) else float("nan")
        errs = [(a - b) / ref["rise"] * 100.0 for a, b in zip(v["parts"], ref["parts"])]
        out[f"{m}_part_max"] = max(errs, key=abs)
        # The spread between the hottest and the coolest part says how the heat is shared between the pads
        out[f"{m}_spread"] = ((max(v["parts"]) - min(v["parts"])) - (max(ref["parts"]) - min(ref["parts"]))) / ref["rise"] * 100.0
        if m == "lumped":
            errs_own = [(a - b) / ref["rise"] * 100.0 for a, b in zip(v["parts_own"], ref["parts"])]
            out["lumped_part_own"] = max(errs_own, key=abs)
            out["lumped_spread_own"] = ((max(v["parts_own"]) - min(v["parts_own"])) - (max(ref["parts"]) - min(ref["parts"]))) / ref["rise"] * 100.0
        out[f"{m}_w_block"] = (v["w_block"] - ref["w_block"]) / max(ref["w_block"], 1e-9) * 100.0 if np.isfinite(v["w_block"]) else float("nan")
    return out


def case_list(which):
    """!
    @brief The cases of a sweep set.
    @param which 'base', 'pads', 'interface', 'size', 'h' or 'all'.
    @return List of (label, Problem).
    """
    cs = []
    if which in ("base", "all"):
        cs.append(("base: 2 pads 12 mm, R''=5 Kcm2/W, block 80x60, h_extra 0", make()))
        cs.append(("control: base board, NO block", make(with_block=False)))
    if which in ("pads", "all"):
        for n in (1, 2, 4):
            cs.append((f"control: {n} pads, NO block", make(n_pads=n, with_block=False)))
        for n, pad in [(1, 12.0), (2, 12.0), (4, 12.0), (1, 25.0), (2, 25.0), (4, 25.0), (1, 8.0), (4, 8.0)]:
            cs.append((f"pads {n} x {pad:g} mm", make(n_pads=n, pad=pad)))
    if which in ("interface", "all"):
        for n in (1, 2, 4):
            for rc in (1e-5, 1e-4, 5e-4, 2e-3):
                cs.append((f"pads {n}, R''={rc * 1e4:g} Kcm2/W", make(n_pads=n, r_c=rc)))
    if which in ("size", "all"):
        for blk in [(40.0, 30.0), (60.0, 45.0), (80.0, 60.0), (100.0, 80.0)]:
            cs.append((f"2 pads, block {blk[0]:g}x{blk[1]:g}", make(block=blk)))
    if which in ("h", "all"):
        for he in (0.0, 10.0, 50.0, 200.0):
            cs.append((f"2 pads, h_extra {he:g}", make(h_extra=he)))
    return cs


def main():
    """!
    @brief Print the error table of the chosen sweep and optionally write it as CSV.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell-mm", type=float, default=1.0)
    ap.add_argument("--set", default="base")
    ap.add_argument("--csv", default="")
    a = ap.parse_args()
    rows = []
    keys = ["lumped_hot", "analytic_hot", "lumped_block_mean", "analytic_block_mean", "lumped_part_max", "lumped_part_own", "analytic_part_max",
            "lumped_spread", "lumped_spread_own", "analytic_spread"]
    print(f"cell {a.cell_mm:g} mm; errors in % of the FVM rise (model - FVM)")
    print("| Case | FVM rise K | block K | L hot | A hot | L block | A block | L part (field) | L part (own peak) | A part | L spread (field) | L spread (own peak) | A spread |")
    print("| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |")
    for label, p in case_list(a.set):
        o = compare(label, p, a.cell_mm)
        rows.append(o)
        print(f"| {label} | {o['rise_fvm']:.1f} | {o['block_fvm']:.1f} | " + " | ".join(f"{o[k]:+.1f}" for k in keys) + " |", flush=True)
    print("\nmax |error| per column: " + ", ".join(f"{k} {max([abs(r[k]) for r in rows if np.isfinite(r[k])] or [float('nan')]):.1f}" for k in keys))
    if a.csv:
        os.makedirs(os.path.dirname(a.csv) or ".", exist_ok=True)
        with open(a.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)


if __name__ == "__main__":
    main()
