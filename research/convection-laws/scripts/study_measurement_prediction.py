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
Usage: .venv/bin/python research/convection-laws/scripts/study_measurement_prediction.py [--vias]   (about 2 minutes; --vias: only the via-count table of part 4)
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


def board(kind, power, orientation="horizontal", flipped=False, mult=1.0, nv=3):
    """!
    @brief One of the three test boards.
    @param kind "A" (full copper), "B" (20 mm pad) or "C" (pad and 3 x 3 vias).
    @param power Heater power in W.
    @param orientation "horizontal" or "vertical".
    @param flipped True: the heater sits on the layer that looks down (layer 2 is the heater layer, the board is turned over).
    @param mult Convection multiplier (Board.h_calibration).
    @param nv Vias per side of the square array of board C.
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
        half = 1.3 * (nv - 1) / 2.0                  # the array spans (nv - 1) pitches of 1.3 mm about the heater centre (50, 40)
        p.add_via_array((50 - half, 40 - half, 50 + half, 40 + half), nv, nv, diameter=0.3)
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


def vias_part():
    """!
    @brief Power that gives a 35 K rise on board C for 3 x 3, 5 x 5 and 6 x 6 vias, against the pad alone (B): how visible is the via effect?
    @return dict.
    """
    res = {}
    pb = power_for("B", 35.0)
    res["B"] = pb
    for nv in (3, 5, 6):
        pw = 1.0
        for _ in range(3):
            pw *= (35.0 / run(board("C", pw, nv=nv), "program")["rise"]) ** 1.15
        res[f"C{nv}"] = pw
        print(f"vias {nv} x {nv}: {pw:.3f} W for 35 K (pad alone {pb:.3f} W): {100 * (pw / pb - 1):+.1f} % power", flush=True)
    return res


def isolated_face(power, level, up, eps=0.07, c_back=1.0, w=0.100, h=0.080):
    """!
    @brief Uniform-temperature plate (board D: bright copper face, film heater and foam on the back) in steady state, one exposed face up or down, solved with the program's convection functions only (no board solver).
    @details P = A dT [h_conv(dT) + h_rad(dT) + c_back] with the exposed face looking up or down and the program's air properties; the edges (1.6 mm) and the plate's own gradients are ignored.
    @param power Electrical power in W.
    @param level Key of laws.PAIRS.
    @param up True if the exposed face looks up.
    @param eps Emissivity of the exposed face.
    @param c_back Conductance of the foam and back loss per unit area in W/m2K.
    @param w Plate width in m.
    @param h Plate height in m.
    @return dict with the rise (K) and the coefficients of the exposed face.
    """
    from pcbthermal import convection
    area, length = w * h, w * h / (2 * (w + h))
    dt = 20.0
    with laws.C.use_horizontal(*laws.PAIRS[level]):
        for _ in range(60):                                       # fixed-point on the rise
            hc, _ra = convection.h_natural_horizontal(22.0 + dt, 22.0, length, up)
            hr = convection.h_radiation(22.0 + dt, 22.0, eps)
            dt = power / (area * (hc + hr + c_back))
    return {"rise": dt, "h_conv": hc, "h_rad": hr}


def both_faces(power, level, factor_up=1.0, eps=0.9, w=0.100, h=0.080):
    """!
    @brief Uniform plate with BOTH faces open to the air (a film heater under a thin board of full copper): the rise from P = A dT [h_up + h_down + 2 h_rad], the program's functions, no board solver.
    @param power Electrical power in W.
    @param level Key of laws.PAIRS.
    @param factor_up Multiplier on the convection of the face up (0.6 = the coupling of the faces that the 2D plate of README section 5 suggests; a hypothesis, not a result).
    @param eps Emissivity of both faces.
    @param w Plate width in m.
    @param h Plate height in m.
    @return Rise in K.
    """
    from pcbthermal import convection
    area, length = w * h, w * h / (2 * (w + h))
    dt = 20.0
    with laws.C.use_horizontal(*laws.PAIRS[level]):
        for _ in range(60):
            hu, _ = convection.h_natural_horizontal(22.0 + dt, 22.0, length, True)
            hd, _ = convection.h_natural_horizontal(22.0 + dt, 22.0, length, False)
            hr = convection.h_radiation(22.0 + dt, 22.0, eps)
            dt = power / (area * (factor_up * hu + hd + 2 * hr))
    return dt


def main():
    """!
    @brief Run the parts and print them.
    @return None.
    """
    if "--faces" in sys.argv:
        res = {}
        print("board D (exposed bright face, back foam c = 1.0 W/m2K): rise (K) with the face up and down, and the differential conductance inferred from P/(A dT)")
        for pw in (2.0, 4.0, 8.0):
            for lv in ("program", "RH+GL", "RH+FI", "Jaffer"):
                u, d = isolated_face(pw, lv, True), isolated_face(pw, lv, False)
                g_u, g_d = pw / (0.1 * 0.08 * u["rise"]), pw / (0.1 * 0.08 * d["rise"])
                res[f"{pw}|{lv}"] = {"up": u, "down": d, "diff": g_u - g_d}
                print(f"P {pw:4.1f} W {lv:8s} up {u['rise']:6.2f} K  down {d['rise']:6.2f} K  up/down {u['rise'] / d['rise']:.3f}  (P/(A dT))_up - (P/(A dT))_down {g_u - g_d:5.2f} W/m2K", flush=True)
        print("\nsensitivity of the up/down ratio of the rises to the back loss c (P = 4 W) and to the emissivity of the exposed face")
        for c in (0.5, 1.0, 2.0):
            for eps in (0.05, 0.10):
                row = {lv: isolated_face(4.0, lv, True, eps=eps, c_back=c)["rise"] / isolated_face(4.0, lv, False, eps=eps, c_back=c)["rise"] for lv in ("program", "RH+GL", "RH+FI", "Jaffer")}
                res[f"c{c}|eps{eps}"] = row
                print(f"c {c:3.1f} eps {eps:4.2f}: " + "  ".join(f"{k} {v:.3f}" for k, v in row.items()), flush=True)
        print("\nuniform plate with both faces open (emissivity 0.9, film heater under a thin full-copper board): rise in K")
        for pw in (3.0, 6.0, 12.0):
            row = {lv: both_faces(pw, lv) for lv in ("program", "RH+GL", "RH+FI", "Jaffer")}
            row["program, up x0.6"] = both_faces(pw, "program", 0.6)
            res[f"both|{pw}"] = row
            print(f"P {pw:5.1f} W: " + "  ".join(f"{k} {v:6.2f}" for k, v in row.items()) + f"   (up x0.6)/program {row['program, up x0.6'] / row['program']:.3f}", flush=True)
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, "measurement_faces.json"), "w") as fh:
            json.dump(res, fh, indent=1)
        return
    if "--vias" in sys.argv:
        os.makedirs(OUT, exist_ok=True)
        with open(os.path.join(OUT, "measurement_vias.json"), "w") as fh:
            json.dump(vias_part(), fh, indent=1)
        return
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
