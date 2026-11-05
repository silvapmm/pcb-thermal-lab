#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_vertical_plate.py
@brief Study S3 "vertical plate with two strip sources" (Lee and Yovanovich 1989, with the measurements of Zinnes 1969): is the independent conjugate solver of this folder equal to the
       paper's own numerical curves, and how far are the program's five models, which use ONE mean coefficient per face, from the conjugate solution (local convection coefficient, conduction
       along the plate, radiation) on the same plate?
@details Inputs (page 265 of the paper, read from the page image): height L = 96.52 mm, half thickness t = 1.143 mm, strip l = 5.08 mm, heat flux entering the front face under a strip
         q_p = 3875 W/m2 (half of the generation of the symmetric plate, p 264), k_s = 1.032 W/mK (glass, emissivity 0.387) or 28.38 W/mK (ceramic, 0.366), air at 298 K, nu = 15.614e-6 m2/s,
         k_f = 0.0258 W/mK, Pr = 0.72, surroundings 298 K. The strips are centred at L/4 and 3L/4 (Fig. 4, and the peaks of Figs. 5 and 6 at 0.25 L to 0.27 L and 0.75 L to 0.77 L).
         Part R (reproduction): `lib/vertical_plate.py` (boundary layer marching + one-dimensional plate) against the curves of the paper's own model read from Figs. 5 and 6 (values read from the
         plot: "plot", +-2 K) and the thermocouple points of Zinnes (plot); its own checks (similarity solution, energy balance) are the tests.
         Part P (the program): the plate as a board of height 96.52 mm and width 20.32 mm (the problem is two-dimensional: strips across the whole width, adiabatic sides), two layers of the
         plate's own conductivity (copper conductivity set to k_s, FR-4 in plane and through to k_s: a homogeneous plate) of 2.286 mm in all, a heater of 3875 W/m2 x l x width on each face
         (the symmetric plate, so the through-plate conduction is solved instead of assumed), vertical orientation, computed coefficients (natural forms general and laminar), emissivity as
         printed, ambient 25 degC; models fvm, fdm, solid3d, analytic, lumped at cells of 0.508 and 0.254 mm. Compared: the mean and the maximum temperature of the strips and the maximum of the
         plate, in K above ambient, against the conjugate solution; and the energy balance. A diagnostic run with the FVM and the uniform coefficient that the conjugate solution itself implies
         (total heat over the integral of the excess temperature) separates the effect of the uniform coefficient from the effect of the correlation.
         Success criteria (written before the run): R1 the solver within 5 % of the paper's curve at the peaks, the valley and the ends of the four curves (glass 2 and ceramic 2; the second peak of
         the glass, which the plot puts 6 % off, is reported); P1 the models within 10 % of the strip-mean rise of the conjugate solution for the ceramic plate and within 20 % for the glass (the
         uniform coefficient cannot follow the 95 K peaks), the sign of the error reported.
         Run (from the repository root): .venv/bin/python research/paper-case-studies/scripts/study_vertical_plate.py [--dry-run] [--no-program]
"""

import argparse
import json
import sys

import _bootstrap
import numpy as np

import vertical_plate as VP

OUT = _bootstrap.OUT
L_MM, T_HALF_MM, STRIP_MM, Q_P = 96.52, 1.143, 5.08, 3875.0
W_MM = 20.32                    # width of the board of the program (40 cells of 0.508 mm): the problem does not depend on it
CASES = {"glass": (1.032, 0.387), "ceramic": (28.38, 0.366)}
# values read from the plot, +-2 K: (z/L of the peak, rise at peak 1, peak 2, valley, left end), "present model" curve of Figs. 5 and 6 (plot)
PLOT_MODEL = {("glass", 0.0): (91.0, 98.0, 44.0, 20.0), ("glass", 0.387): (75.0, 89.0, 29.0, 13.0),
              ("ceramic", 0.0): (61.5, 65.0, 60.0, 57.0), ("ceramic", 0.366): (46.5, 48.0, 44.0, 42.0)}
# Zinnes' thermocouples (plot): (z/L, rise in K) at the emissivity of the plate
ZINNES = {"glass": [(0.11, 22.6), (0.26, 79.8), (0.51, 33.1), (0.77, 84.4)], "ceramic": [(0.09, 36.0), (0.24, 42.0), (0.50, 37.8), (0.75, 42.7)]}


def conjugate(name, eps):
    """!
    @brief The conjugate solution of the independent solver for one plate.
    @param name "glass" or "ceramic".
    @param eps Emissivity (0 for no radiation).
    @return dict of vertical_plate.solve_plate plus the derived rises.
    """
    ks, _ = CASES[name]
    fl = VP.Fluid()
    r = VP.solve_plate(L_MM * 1e-3, T_HALF_MM * 1e-3, ks, [(L_MM * 1e-3 / 4, STRIP_MM * 1e-3), (3 * L_MM * 1e-3 / 4, STRIP_MM * 1e-3)], Q_P, eps, fl, nz=386, relax=0.3, max_iter=600)
    r["rise"] = r["t_wall"] - fl.t_inf
    return r


def strip_stats(r, which):
    """!
    @brief Mean and maximum rise over one strip and the plate maximum.
    @param r Result of conjugate().
    @param which 0 or 1, the lower or the upper strip.
    @return tuple (mean, max over the strip, max over the plate) in K.
    """
    z = r["z"] / (L_MM * 1e-3)
    centre = (0.25, 0.75)[which]
    sel = np.abs(z - centre) <= STRIP_MM / L_MM / 2.0
    return float(r["rise"][sel].mean()), float(r["rise"][sel].max()), float(r["rise"].max())


def part_r():
    """!
    @brief Part R: the independent solver against the paper's curves.
    @return list of rows.
    """
    rows = []
    print("\nR  independent conjugate solver against the curves of Figs. 5 and 6 (plot values, +-2 K) and Zinnes' thermocouples (plot)")
    print("   plate     eps    peak1 (solver / plot)   peak2            valley           left end        heat in / out (W/m)   iterations")
    for name, (ks, eps_p) in CASES.items():
        for eps in (0.0, eps_p):
            r = conjugate(name, eps)
            th = r["rise"]
            z = r["z"] / (L_MM * 1e-3)
            n = len(th)
            p1, p2 = th[: n // 2].max(), th[n // 2:].max()
            valley = th[np.argmin(np.abs(z - 0.5))]
            end = th[0]
            ref = PLOT_MODEL[(name, eps)]
            row = {"plate": name, "eps": eps, "peak1": float(p1), "peak2": float(p2), "valley": float(valley), "left": float(end), "plot": ref,
                   "err_pct": [(a / b - 1) * 100 for a, b in zip((p1, p2, valley, end), ref)], "heat_in": r["heat_in"], "heat_out": r["heat_out"], "iterations": r["iterations"]}
            rows.append(row)
            print(f"   {name:8s} {eps:5.3f}   {p1:6.1f} / {ref[0]:5.1f} ({row['err_pct'][0]:+5.1f} %)  {p2:6.1f} / {ref[1]:5.1f} ({row['err_pct'][1]:+5.1f} %)  "
                  f"{valley:5.1f} / {ref[2]:5.1f} ({row['err_pct'][2]:+5.1f} %)  {end:5.1f} / {ref[3]:5.1f} ({row['err_pct'][3]:+5.1f} %)  {r['heat_in']:.2f} / {r['heat_out']:.2f}   {r['iterations']}")
        r = conjugate(name, eps_p)
        z = r["z"] / (L_MM * 1e-3)
        pts = ", ".join(f"z/L {zz:.2f}: {np.interp(zz, z, r['rise']):.1f} (Zinnes {v:.1f})" for zz, v in ZINNES[name])
        print(f"   thermocouples, {name}, solver against the plotted points: {pts}")
    return rows


def plate_problem(name, eps, cell_mm, natural_form="general", h_manual=None):
    """!
    @brief The plate as a board of the program.
    @param name "glass" or "ceramic".
    @param eps Emissivity of both faces.
    @param cell_mm Grid cell in mm (the strip is 10 cells of 0.508 mm).
    @param natural_form "general" or "laminar" (Board.natural_form).
    @param h_manual Uniform coefficient in W/m2K for both faces (manual mode), or None for the computed coefficients.
    @return Problem.
    """
    from pcbthermal import Problem
    from pcbthermal.model import Materials
    ks, _ = CASES[name]
    opts = dict(ambient=25.0, h_side=0.0, materials=Materials(k_copper=ks, k_fr4_through=ks, k_fr4_inplane=ks))
    if h_manual is None:
        opts.update(h_mode="computed", orientation="vertical", emissivity_top=eps, emissivity_bottom=eps, natural_form=natural_form, air_speed=0.0)
    else:
        opts.update(h_top=h_manual, h_bottom=h_manual)
    p = Problem.new(W_MM, L_MM, layers=2, thickness_mm=2.0 * T_HALF_MM, copper_um=35.0, name=f"lee_yovanovich_{name}", **opts)
    power = Q_P * STRIP_MM * 1e-3 * W_MM * 1e-3                       # W per strip per face (the whole face of a strip carries q_p)
    for layer in (1, 2):
        for zc in (L_MM / 4, 3 * L_MM / 4):
            p.add_heater(layer, power, rect=(0.0, zc - STRIP_MM / 2, W_MM, zc + STRIP_MM / 2), name=f"strip {zc:.0f} L{layer}")
    return p


def run_model(p, model, cell_mm):
    """!
    @brief Run one model on the plate and read the rises of the lower and upper strip of layer 1.
    @param p Problem from plate_problem().
    @param model "fvm", "fdm", "solid3d", "analytic" or "lumped".
    @param cell_mm Grid cell in mm.
    @return dict with the strip means and maxima (K above ambient), the board maximum and the heat balance or an "error" text.
    """
    from pcbthermal import SolverOptions, simulate, analysis
    try:
        res = simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm)).results[model]
    except Exception as exc:                       # a refusal or a failure is reported, not hidden
        return {"error": f"{type(exc).__name__}: {exc}"}
    hs = analysis.heater_stats(res, p)
    amb = p.board.ambient
    # heaters are ordered: layer 1 lower, layer 1 upper, layer 2 lower, layer 2 upper
    out = {"mean1": hs[0]["t_mean"] - amb, "max1": hs[0]["t_max"] - amb, "mean2": hs[1]["t_mean"] - amb, "max2": hs[1]["t_max"] - amb, "t_max": res.t_max - amb}
    return out


def part_p():
    """!
    @brief Part P: the program's models against the conjugate solution.
    @return list of rows.
    """
    rows = []
    print("\nP  the program on the plate (rises in K above ambient; strip mean / strip max); error of the strip mean against the conjugate solution")
    for name, (ks, eps_p) in CASES.items():
        r = conjugate(name, eps_p)
        ref = [strip_stats(r, 0), strip_stats(r, 1)]
        print(f"\n  {name} (k_s {ks}, eps {eps_p}): conjugate solution strip 1 mean {ref[0][0]:.2f} max {ref[0][1]:.2f}; strip 2 mean {ref[1][0]:.2f} max {ref[1][1]:.2f}; plate max {ref[0][2]:.2f}")
        # the uniform coefficient the conjugate solution itself implies: total heat over the integral of the excess temperature of both faces
        dz = L_MM * 1e-3 / len(r["z"])
        h_eff = float(np.sum(r["q_conv"] + r["q_rad"]) / np.sum(r["rise"]))
        print(f"  uniform coefficient implied by the conjugate solution: {h_eff:.2f} W/m2K (convection {np.sum(r['q_conv']) / np.sum(r['rise']):.2f} + radiation {np.sum(r['q_rad']) / np.sum(r['rise']):.2f})")
        jobs = []
        for cell in (0.508, 0.254):
            for form in ("general", "laminar"):
                for model in ("fvm", "fdm", "solid3d", "analytic", "lumped"):
                    if cell == 0.254 and model in ("solid3d",):
                        continue
                    jobs.append((model, cell, form, None))
        jobs.append(("fvm", 0.508, "general", h_eff))                  # diagnostic: the uniform coefficient of the conjugate solution
        print("  model     cell   form      h used          strip1 mean (err)       strip2 mean (err)    strip1 max   strip2 max   plate max")
        for model, cell, form, hm in jobs:
            p = plate_problem(name, eps_p, cell, form, hm)
            v = run_model(p, model, cell)
            tag = "h_eff" if hm else form
            if "error" in v:
                print(f"  {model:9s} {cell:5.3f}  {tag:8s}  refused: {v['error']}")
                continue
            e1 = (v["mean1"] / ref[0][0] - 1) * 100
            e2 = (v["mean2"] / ref[1][0] - 1) * 100
            rows.append({"plate": name, "model": model, "cell": cell, "form": tag, **v, "err1_pct": e1, "err2_pct": e2, "ref": ref})
            print(f"  {model:9s} {cell:5.3f}  {tag:8s}  {'computed' if hm is None else f'{hm:.2f}':9s}  {v['mean1']:8.2f} ({e1:+6.1f} %)  {v['mean2']:8.2f} ({e2:+6.1f} %)  {v['max1']:9.2f}  {v['max2']:9.2f}  {v['t_max']:8.2f}")
    return rows


def plan():
    """!
    @brief Print what the study does (for --dry-run).
    @return None.
    """
    print("study_vertical_plate: DRY RUN (nothing is solved)")
    print(f"  plate: L {L_MM} mm, half thickness {T_HALF_MM} mm, strips {STRIP_MM} mm at L/4 and 3L/4, q_p {Q_P} W/m2; cases {CASES}")
    print("  R: lib/vertical_plate.py (boundary layer marching, one-dimensional plate) against Figs. 5 and 6 (plot values) and Zinnes' thermocouples; about 1 minute")
    print("  P: five models at cells 0.508 and 0.254 mm, both natural forms, plus the uniform coefficient of the conjugate solution; about 3 minutes, under 1 GB")


def main(argv=None):
    """!
    @brief Entry point.
    @param argv Optional argument list.
    @return int Exit code.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--dry-run", action="store_true", help="print the plan, solve nothing")
    ap.add_argument("--no-program", action="store_true", help="only part R")
    args = ap.parse_args(argv)
    if args.dry_run:
        plan()
        return 0
    result = {"R": part_r()}
    if not args.no_program:
        result["P"] = part_p()
    with open(OUT / "study_vertical_plate.json", "w") as f:
        json.dump(result, f, indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
