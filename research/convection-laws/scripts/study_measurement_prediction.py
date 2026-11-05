#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_measurement_prediction.py
@brief What the program predicts for the three test boards of docs/measurement-plan.md, how much the predictions differ between the horizontal laws, and how much a convection multiplier fitted on board A transfers to B and C.
@details Boards (100 x 80 mm, 1.6 mm FR-4, 35 um copper, 2 layers, 5 mm clearance of copper from the board edge is NOT used: copper reaches 1 mm from the edge): A full copper on both layers;
         B a 20 x 20 mm pad on both layers; C the pad plus a 3 x 3 array of 0.3 mm vias on a 1.2 mm pitch under the heater. The heater is one 8 x 8 mm part on the top layer at the centre
         (two 2512 resistors side by side are about 6.4 x 6.4 mm; the power is the electrical V*I). Computed h (natural convection and radiation, emissivity 0.9), FVM cell 1 mm, ambient 22 degC.
         Runs: (1) the powers that give a rise of about 35 K on each board with the program's laws; (2) the hottest rise and the mean face temperatures for horizontal (layer 1 up),
         horizontal flipped (layer 1 down) and vertical, for the program's laws and for the pair Raithby-Hollands + Goldstein-Lau; (3) the fit: the multiplier m (Board.h_calibration)
         that makes board A's rise equal to the rise of the "other law" model (a stand-in for a measurement), then the prediction error of B and C with that m (how a fitted multiplier
         transfers when the law is wrong in shape). The "measurement" here is a model, the table tells what the protocol can and cannot discriminate. Output: out/measurement_prediction.json.
Usage: .venv/bin/python research/convection-laws/scripts/study_measurement_prediction.py   (about 2 minutes)
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, ROOT)

import laws  # noqa: E402
from pcbthermal import api  # noqa: E402
from pcbthermal.model import Problem  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")


def board(kind, power, orientation="horizontal", flipped=False, mult=1.0):
    """!
    @brief One of the three test boards.
    @param kind "A" (full copper), "B" (20 mm pad) or "C" (pad and 3 x 3 vias).
    @param power Heater power in W.
    @param orientation "horizontal" or "vertical".
    @param flipped True: the heater sits on the layer that looks down (layer 2 is the heater layer, the board is turned over).
    @param mult Convection multiplier (Board.h_calibration).
    @return Problem.
    """
    p = Problem.new(100, 80, 2, thickness_mm=1.6, copper_um=35.0, name="test " + kind, ambient=22.0)
    if kind == "A":
        p.add_zone(1, rect=(1, 1, 99, 79))
        p.add_zone(2, rect=(1, 1, 99, 79))
    else:
        for layer in (1, 2):
            p.add_zone(layer, rect=(40, 30, 60, 50))
    layer = 2 if flipped else 1
    p.add_heater(layer, power, rect=(46, 36, 54, 44), name="R")
    if kind == "C":
        p.add_via_array((47.4, 37.4, 52.6, 42.6), 3, 3, diameter=0.3)
    b = p.board
    b.h_mode, b.orientation, b.h_calibration = "computed", orientation, mult
    return p


def run(p, level):
    """!
    @brief Solve with the FVM at a level of the horizontal laws.
    @param p Problem.
    @param level Key of laws.PAIRS.
    @return dict with the rise of the hottest point and of the heater layer, K.
    """
    with laws.C.use_horizontal(*laws.PAIRS[level]):
        sim = api.simulate(p, api.SolverOptions(models=("fvm",), cell_mm=1.0))
    r = sim.results["fvm"]
    return {"rise": float(r.delta_t), "t_max": float(r.t_max)}


def power_for(kind, target, level="program"):
    """!
    @brief Power giving a rise of `target` K by two secant steps (the rise is nearly proportional to the power).
    @param kind Board kind.
    @param target Wanted rise in K.
    @param level Level of the laws.
    @return Power in W.
    """
    pw = 1.0
    for _ in range(3):
        r = run(board(kind, pw), level)["rise"]
        pw *= (target / r) ** 1.15                       # the rise grows a little less than linearly, so the step is slightly over-corrected
    return pw


def main():
    """!
    @brief Run the three parts and print them.
    @return None.
    """
    out = {"powers": {}, "orient": {}, "fit": {}}
    for k in "ABC":
        out["powers"][k] = power_for(k, 35.0)
        print(f"board {k}: power for a 35 K rise with the program laws: {out['powers'][k]:.2f} W", flush=True)
    print("\nrise of the hottest point (K) at those powers; horizontal layer 1 up / flipped / vertical; levels program, RH+GL, RH+FI, Jaffer")
    for k in "ABC":
        for ori, flip in (("horizontal", False), ("horizontal", True), ("vertical", False)):
            row = {}
            for lv in ("program", "RH+GL", "RH+FI", "Jaffer"):
                row[lv] = run(board(k, out["powers"][k], ori, flip), lv)["rise"]
            out["orient"][f"{k}|{ori}|{'flipped' if flip else 'up'}"] = row
            print(f"{k} {ori:10s} {'flipped' if flip else 'up':8s} " + "  ".join(f"{lv} {v:6.2f}" for lv, v in row.items()) + f"   RH+GL/program {row['RH+GL'] / row['program']:.3f}", flush=True)
    print("\nfit of a multiplier on board A horizontal-up, with the 'true' model RH+GL, then used with the program laws on B and C")
    ta = run(board("A", out["powers"]["A"]), "RH+GL")["rise"]
    lo, hi = 0.6, 1.6
    for _ in range(25):
        mid = 0.5 * (lo + hi)
        if run(board("A", out["powers"]["A"], mult=mid), "program")["rise"] > ta:
            lo = mid
        else:
            hi = mid
    m = 0.5 * (lo + hi)
    print(f"multiplier that makes the program's A equal the RH+GL A: {m:.3f}")
    out["fit"]["m"] = m
    for k in "BC":
        for ori, flip in (("horizontal", False), ("horizontal", True), ("vertical", False)):
            truth = run(board(k, out["powers"][k], ori, flip), "RH+GL")["rise"]
            pred = run(board(k, out["powers"][k], ori, flip, mult=m), "program")["rise"]
            raw = run(board(k, out["powers"][k], ori, flip), "program")["rise"]
            out["fit"][f"{k}|{ori}|{'flipped' if flip else 'up'}"] = {"truth": truth, "pred_fitted": pred, "pred_raw": raw}
            print(f"{k} {ori:10s} {'flipped' if flip else 'up':8s} truth {truth:6.2f}  raw program {raw:6.2f} ({100 * (raw / truth - 1):+.1f} %)  fitted {pred:6.2f} ({100 * (pred / truth - 1):+.1f} %)", flush=True)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "measurement_prediction.json"), "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
