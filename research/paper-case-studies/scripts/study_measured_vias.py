#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_measured_vias.py
@brief Study S1 "measured vias": do the program's models agree with the only MEASURED via results we hold, the through-plane conductivity of Soleymani Koohbanani (2016, Fig. 33) and the
       top-case temperatures of Shen and others (2020, Table II)? Written and checked only; not yet run (the runs wait for a quiet machine).
@details Question: how far are the five models from measured through-plane via cases, once the measurement itself has been checked by an independent solver?
         Independent reference: the closed form of the thesis (equations 28 and 29, a parallel sum, exact for isothermal faces) and an axisymmetric unit-cell solver (`lib/axisym_cell.py`,
         nothing of the program); for Shen's boards `shen_case.unit_cell` (research/lumped-zones-adoption/lib, also nothing of the program).
         Parts (run them with --parts A,B,C,D, default all):
           A  the reference against itself: closed form against the solver (isothermal faces, no foil: they must agree to 1e-6), the effect of a 35 um foil, of the thickness (0.8, 1.6, 3.2 mm)
              and of the boundary condition (isothermal faces of the test bed against a uniform top flux, the only condition the program can impose).
           B  the measurement against the reference: the four arrangements of Fig. 33 (plot values) against equations 28 and 29 over the samples of each group, with the thesis's own 13 %.
           C  the program (fvm, fdm, solid3d, analytic, lumped) on a periodic patch of 6 x 6 cells of each of the nine samples (heater over the whole top, foil on both faces, the bottom held by
              h = 1e6) against the solver with the same condition, and translated to the test bed by the solver's own boundary-condition ratio.
           D  Shen's Table II as DIFFERENCES only (the heatsink, the TIM and the array extent are not in the text read): the contrast of the via resistance between rows, program and
              reference against psi_ta (1 + theta_jt / theta_ta); theta_ta and the pad side are swept, not read.
         Success and failure criteria (written before any run; see README 3):
           B1 closed form = solver to 1e-6 (else a code defect, stop).
           B2 per arrangement, the plotted measurement lies within 15 % of the nearest value of equations 28/29 over the group (13 % of the thesis plus the plot reading); a group that fails is
              "not usable as a reference" and is reported, not hidden.
           C1 for a usable group: fvm and fdm within 5 %, solid3d within 8 %, analytic within 10 % of the solver's node-to-node resistance with the same boundary condition (lumped: reported, 25 %
              as the alarm); the error of fvm and fdm must not grow when the cell is halved.
           C2 the program value translated to the test bed within 20 % of the measurement for the usable groups.
           D1 signs of the contrasts with |measured| >= 0.4 degC/W reproduced by the reference and by fvm/fdm; the solder-against-air and Pattern II against Pattern I contrasts within a factor
              2 of the measured ones for every swept theta_ta and pad side; otherwise Table II is "not informative at this level" and is not quoted in validation.md.
         Declared cost: parts A and B seconds, under 0.2 GB; part C about 5 to 10 minutes and at most 2 GB (cells 0.05 mm and above, 6 x 6 cells); part D about 10 minutes, at most 1.5 GB.
         Run (from the repository root): .venv/bin/python research/paper-case-studies/scripts/study_measured_vias.py [--parts A,B,C,D] [--dry-run] [--quick]
"""

import argparse
import json
import math
import sys

import _bootstrap
import numpy as np

import axisym_cell as AC
import measured_data as MD

OUT = _bootstrap.OUT
T_ASSUMED_MM = 1.6               # the thesis does not state the board thickness (equations 28 and 29 do not depend on it without foil): assumed
FOIL_UM = 35.0                   # assumed copper foil on both faces (not stated); the variant without foil is part A
N_CELLS = 6                      # cells per side of the periodic patch of part C
SHEN_THETA_TA = (20.0, 30.0, 40.0)   # K/W, ASSUMED sweep (eq. 39 / Fig. 20 not read yet): the factor (1 + theta_jt / theta_ta) is 3.2, 2.5, 2.1
SHEN_PAD_SIDE_MM = (4.0, 5.6, 7.0)   # mm, ASSUMED sweep of the side of the via array (5.6 mm is the board of Fig. 17)


def cell_area_m2(kind, side_mm):
    """!
    @brief Plan area per via of an arrangement.
    @param kind "straight" (area u^2) or "staggered" (two vias in v^2, area v^2 / 2).
    @param side_mm The spacing u or v in mm.
    @return float Area in m2.
    """
    s = side_mm * 1e-3
    return s * s if kind == "straight" else s * s / 2.0


def part_a():
    """!
    @brief The reference against itself: closed form against the solver, the foil, the thickness and the boundary condition.
    @return dict of the rows printed.
    """
    rows = {"closed_vs_solver": [], "foil_and_bc": []}
    print("\nPart A.1 closed form (eq. 28/29) against the axisymmetric solver, isothermal faces, no foil (they must agree to 1e-6)")
    print("  sample  kind       cell mm  Do mm  Di mm   k_closed   k_solver   rel.diff")
    for s, (spacing, pitch, di, do, _) in MD.TABLE_9.items():
        kind = "straight" if pitch == spacing else "staggered"
        side = spacing
        kc = (AC.k_overall_straight if kind == "straight" else AC.k_overall_staggered)(side * 1e-3, do * 1e-3, di * 1e-3)
        ks = AC.unit_cell_k(cell_area_m2(kind, side), do * 1e-3, di * 1e-3, T_ASSUMED_MM * 1e-3)["k_eff"]
        rows["closed_vs_solver"].append((s, kind, side, kc, ks))
        print(f"  {s:6d}  {kind:9s}  {side:6.2f}  {do:5.2f}  {di:5.2f}  {kc:9.4f}  {ks:9.4f}  {abs(ks - kc) / kc:9.2e}")
    print("\nPart A.2 foil, thickness and boundary condition, sample 1 and sample 8 (k_eff in W/mK; r = node-to-node resistance of one via cell in K/W)")
    print("  sample  t mm  foil   bc          k_eff     r_nodes   k_eff / k_closed")
    for s in (1, 8):
        spacing, pitch, di, do, _ = MD.TABLE_9[s]
        kc = AC.k_overall_straight(spacing * 1e-3, do * 1e-3, di * 1e-3)
        for t in (0.8, 1.6, 3.2):
            for foil, bc in ((0.0, "isothermal"), (FOIL_UM * 1e-6, "isothermal"), (FOIL_UM * 1e-6, "flux")):
                r = AC.unit_cell_k(spacing * spacing * 1e-6, do * 1e-3, di * 1e-3, t * 1e-3, t_foil=foil, bc=bc)
                rows["foil_and_bc"].append((s, t, foil, bc, r["k_eff"], r["r_nodes"]))
                print(f"  {s:6d}  {t:4.1f}  {foil * 1e6:4.0f}  {bc:10s}  {r['k_eff']:8.3f}  {r['r_nodes']:8.2f}  {r['k_eff'] / kc:8.3f}")
    return rows


def part_b():
    """!
    @brief The measurement (plot) against the closed form over the samples of each arrangement, and the verdict B2.
    @return dict group -> (measured, lowest, highest of eq. 28/29, relative distance, verdict).
    """
    out = {}
    print("\nPart B  Fig. 33 measured markers (plot) against equations 28 and 29 over the samples of each arrangement")
    print("  group           measured (plot)   eq.28/29 over the samples (min .. max)   distance of the measurement to the range   B2 (15 %)")
    for g, (kind, side, samples, _x) in MD.ARRANGEMENTS.items():
        vals = []
        for s in samples:
            _sp, _pi, di, do, _ = MD.TABLE_9[s]
            vals.append((AC.k_overall_straight if kind == "straight" else AC.k_overall_staggered)(side * 1e-3, do * 1e-3, di * 1e-3))
        lo, hi = min(vals), max(vals)
        km = MD.FIG33_MEASURED[g][0]
        dist = 0.0 if lo <= km <= hi else min(abs(km - lo), abs(km - hi)) / km
        ok = dist <= 0.15
        out[g] = (km, lo, hi, dist, ok)
        print(f"  {g:14s}  {km:7.2f} +-{MD.FIG33_PLOT_UNCERTAINTY:.1f}      {lo:7.3f} .. {hi:7.3f}                      {dist * 100:8.1f} %                          {'usable' if ok else 'NOT USABLE'}")
    return out


def lattice(kind, cell_mm, n):
    """!
    @brief The via positions of a periodic patch of n x n cells.
    @param kind "straight" (one via at the centre of each cell) or "staggered" (two: at the corner and the centre of each cell of side v, i.e. rows offset by half the in-row spacing).
    @param cell_mm Side of the cell (u or v) in mm.
    @param n Cells per side.
    @return list of (x, y) in mm.
    """
    pts = []
    for i in range(n):
        for j in range(n):
            if kind == "straight":
                pts.append(((i + 0.5) * cell_mm, (j + 0.5) * cell_mm))
            else:
                pts.append(((i + 0.25) * cell_mm, (j + 0.25) * cell_mm))
                pts.append(((i + 0.75) * cell_mm, (j + 0.75) * cell_mm))
    return pts


def run_patch(model, kind, cell_mm, d_o_mm, d_i_mm, t_mm, foil_um, div, n=N_CELLS):
    """!
    @brief The program on the periodic patch: a heater over the whole top, foil on both faces (or none), the bottom held by h = 1e6, FR-4 isotropic 0.33, copper 385.
    @param model "fvm", "fdm", "solid3d", "analytic" or "lumped".
    @param kind "straight" or "staggered".
    @param cell_mm Side of the cell in mm.
    @param d_o_mm Drill (outer) diameter in mm.
    @param d_i_mm Inner diameter in mm (the plating is (d_o - d_i) / 2).
    @param t_mm Board thickness in mm.
    @param foil_um Copper thickness of both layers in um (the layers exist in the program even when the study speaks of "no foil": see the README, 3.3).
    @param div Cells of the grid per cell of the patch (grid size = cell_mm / div, not below 0.05 mm).
    @param n Cells per side.
    @return float Resistance in K/W between the mean temperatures of the two copper layers of the patch (1 W).
    """
    from pcbthermal import Problem, SolverOptions, simulate     # imported here: --dry-run and the closed-form parts need nothing of the program
    from pcbthermal.model import Materials
    side = n * cell_mm
    mat = Materials(k_copper=AC.K_CU, k_fr4_through=AC.K_FR4, k_fr4_inplane=AC.K_FR4)
    p = Problem.new(side, side, layers=2, thickness_mm=t_mm, copper_um=foil_um, ambient=0.0, h_top=0.0, h_bottom=1.0e6, h_side=0.0, materials=mat)
    p.board.via_plating = (d_o_mm - d_i_mm) / 2.0 * 1e-3
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(0.0, 0.0, side, side), name="U")
    for x, y in lattice(kind, cell_mm, n):
        p.add_via(x, y, diameter=d_o_mm)
    res = simulate(p, SolverOptions(models=(model,), cell_mm=max(cell_mm / div, 0.05))).results[model]
    T = np.asarray(res.T)
    return float(T[0].mean() - T[-1].mean())


def part_c(quick=False):
    """!
    @brief The five models on the nine samples against the solver with the same boundary condition, and translated to the test bed.
    @param quick True for one sample per arrangement and the models fvm and analytic only (a smoke run).
    @return list of rows.
    """
    rows = []
    models = ("fvm", "analytic") if quick else ("fvm", "fdm", "solid3d", "analytic", "lumped")
    print("\nPart C  the program on the periodic patch (6 x 6 cells, foil 35 um both faces, bottom h = 1e6, heater over the whole top)")
    print("  sample  model     grid mm  R_prog K/W  R_ref K/W (flux bc)  error %   k_iso/k_flux (solver)   k_eff translated W/mK   measured (plot) W/mK")
    for s, (spacing, pitch, di, do, _) in MD.TABLE_9.items():
        group = [g for g, v in MD.ARRANGEMENTS.items() if s in v[2]][0]
        if quick and s not in (1, 4, 7, 8):
            continue
        kind = MD.ARRANGEMENTS[group][0]
        area = cell_area_m2(kind, spacing)
        nv = N_CELLS * N_CELLS * (1 if kind == "straight" else 2)
        flux = AC.unit_cell_k(area, do * 1e-3, di * 1e-3, T_ASSUMED_MM * 1e-3, t_foil=FOIL_UM * 1e-6, bc="flux")
        iso = AC.unit_cell_k(area, do * 1e-3, di * 1e-3, T_ASSUMED_MM * 1e-3, t_foil=FOIL_UM * 1e-6, bc="isothermal")
        r_ref = flux["r_nodes"] / nv                                       # K/W of the patch
        ratio = iso["k_eff"] / flux["k_eff"]
        divs = (8, 16) if quick else (8, 16, 32)
        for m in models:
            for div in divs:
                if div == 32 and m not in ("fvm", "fdm"):
                    continue                                              # the finest grid only for the two layered finite-volume/difference models (memory)
                grid = max(spacing / div, 0.05)
                try:
                    r = run_patch(m, kind, spacing, do, di, T_ASSUMED_MM, FOIL_UM, div)
                except Exception as exc:                                  # a model that refuses the board is reported, not hidden
                    print(f"  {s:6d}  {m:8s}  {grid:7.3f}  refused: {type(exc).__name__}: {exc}")
                    continue
                k_prog = T_ASSUMED_MM * 1e-3 / (r * (N_CELLS * spacing * 1e-3) ** 2)      # W/mK: P t / (A_patch dT) with P = 1 W
                k_tr = k_prog * ratio
                km = MD.FIG33_MEASURED[group][0]
                rows.append({"sample": s, "model": m, "grid_mm": grid, "r_prog": r, "r_ref": r_ref, "err": r / r_ref - 1.0, "ratio": ratio, "k_translated": k_tr, "k_measured": km})
                print(f"  {s:6d}  {m:8s}  {grid:7.3f}  {r:10.4f}  {r_ref:19.4f}  {(r / r_ref - 1) * 100:7.1f}   {ratio:8.3f}             {k_tr:9.3f}               {km:6.2f}")
    return rows


def shen_array(pattern, phi_mm, pad_mm):
    """!
    @brief The via array of Shen's experiment as an exact periodic block: cells of the Pattern I or II lattice with s = 0.2 mm, as many as fit in the nominal pad side.
    @param pattern "I" (square lattice, pitch phi + s) or "II" (rows spaced sqrt(3)/2 pitch, alternate rows offset by half a pitch).
    @param phi_mm Via (drill) diameter in mm.
    @param pad_mm Nominal side of the array in mm.
    @return tuple (positions in mm, width in mm, height in mm, number of vias, area of one cell in m2).
    """
    p = phi_mm + 0.2
    row = p if pattern == "I" else math.sqrt(3.0) / 2.0 * p
    n, m = max(1, int(pad_mm / p)), max(1, int(pad_mm / row))
    pts = [(((i + 0.5) if pattern == "I" else (i + 0.25 + 0.5 * (j % 2))) * p, (j + 0.5) * row) for j in range(m) for i in range(n)]
    return pts, n * p, m * row, n * m, p * row * 1e-6


def run_shen_array(model, pattern, fill, phi_mm, pad_mm, div=8):
    """!
    @brief The program on Shen's via array: four copper layers of 70 um, 1.6 mm, a heater over the array, the bottom held by h = 1e6, Table I conductivities, plating 25 um.
    @param model "fvm", "fdm" or "solid3d".
    @param pattern "I" or "II".
    @param fill "solder" (57.3 W/mK core) or "air" (open barrel).
    @param phi_mm Via diameter in mm.
    @param pad_mm Nominal array side in mm.
    @param div Grid cells per pitch (grid not below 0.05 mm).
    @return float Resistance in K/W between the mean top and bottom copper temperatures, and the number of vias, as a tuple.
    """
    from pcbthermal import Problem, SolverOptions, simulate
    from pcbthermal.model import Materials
    pts, w, h, nv, _a = shen_array(pattern, phi_mm, pad_mm)
    mat = Materials(k_copper=393.0, k_fr4_through=0.29, k_fr4_inplane=0.81)
    p = Problem.new(w, h, layers=4, thickness_mm=1.6, copper_um=70.0, ambient=0.0, h_top=0.0, h_bottom=1.0e6, h_side=0.0, materials=mat)
    p.board.via_plating = 25e-6
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(0.0, 0.0, w, h), name="U")
    for x, y in pts:
        p.add_via(x, y, diameter=phi_mm, fill_k=57.3 if fill == "solder" else 0.0)
    res = simulate(p, SolverOptions(models=(model,), cell_mm=max((phi_mm + 0.2) / div, 0.05))).results[model]
    T = np.asarray(res.T)
    return float(T[0].mean() - T[-1].mean()), nv


def part_d(models=("fvm", "fdm")):
    """!
    @brief Shen's Table II as differences: the program and the reference via contrast against the measured contrasts, swept over theta_ta and the array side.
    @param models Program models of the table (the 3D solid is left out by default: memory).
    @return dict of the contrasts.
    """
    from shen_case import unit_cell            # the axisymmetric unit-cell solver of research/lumped-zones-adoption (imports nothing of the program)
    rows = {}
    print("\nPart D  Shen Table II: contrasts of psi_ta (measured) against the contrasts of the via resistance x 1 / (1 + theta_jt / theta_ta)")
    print("  NOTE theta_ta and the array side are ASSUMED sweeps (not read): the verdict D1 holds only if it is the same over the whole sweep")
    for pad in SHEN_PAD_SIDE_MM:
        res = {}
        for (pat, fill), data in MD.SHEN_TABLE_II.items():
            for phi in MD.SHEN_PHI_MM:
                _pts, _w, _h, nv, area = shen_array(pat, phi, pad)
                r_cell = unit_cell(pitch=math.sqrt(area), phi=phi * 1e-3, k_fill=57.3 if fill == "solder" else 0.026)
                res[(pat, fill, phi, "reference")] = r_cell / nv
                for m in models:
                    try:
                        res[(pat, fill, phi, m)] = run_shen_array(m, pat, fill, phi, pad)[0]
                    except Exception as exc:                          # reported, not hidden
                        print(f"  {m} {pat} {fill} phi {phi}: {type(exc).__name__}: {exc}")
        for th_ta in SHEN_THETA_TA:
            amp = 1.0 + MD.SHEN_THETA_JT / th_ta
            for who in ("reference",) + tuple(models):
                print(f"\n  array side {pad} mm, theta_ta {th_ta} K/W (factor {amp:.2f}), {who}")
                print("    contrast                                 measured d psi   d theta_via   predicted d psi")
                for phi_i, phi in enumerate(MD.SHEN_PHI_MM):
                    m_air_i = MD.SHEN_TABLE_II[("I", "air")][phi_i][1]
                    m_sol = MD.SHEN_TABLE_II[("I", "solder")][phi_i][1]
                    m_air_ii = MD.SHEN_TABLE_II[("II", "air")][phi_i][1]
                    for name, meas, a, b in ((f"air - solder, Pattern I, phi {phi}", m_air_i - m_sol, ("I", "air", phi, who), ("I", "solder", phi, who)),
                                             (f"Pattern I - Pattern II, air, phi {phi}", m_air_i - m_air_ii, ("I", "air", phi, who), ("II", "air", phi, who))):
                        if a in res and b in res:
                            d_th = res[a] - res[b]
                            rows[(pad, th_ta, who, name)] = (meas, d_th, d_th / amp)
                            print(f"    {name:40s}  {meas:8.2f}        {d_th:9.3f}      {d_th / amp:8.3f}")
    return rows


def plan(parts):
    """!
    @brief Print what the study would do (for --dry-run), with the declared cost.
    @param parts List of parts ("A", "B", "C", "D").
    @return None.
    """
    print("study_measured_vias: DRY RUN (nothing is solved)")
    print(f"  measured data: Fig. 33 has {len(MD.FIG33_MEASURED)} measured markers (plot) for {len(MD.TABLE_9)} samples in {len(MD.ARRANGEMENTS)} arrangements; Shen Table II has {sum(len(v) for v in MD.SHEN_TABLE_II.values())} cells")
    info = {"A": "closed form vs unit-cell solver (9 samples), foil/thickness/bc effects on samples 1 and 8; seconds, < 0.2 GB",
            "B": "the four plotted markers against eq. 28/29 over the samples of each group (criterion B2, 15 %); instant",
            "C": f"program (fvm, fdm, solid3d, analytic, lumped) on a {N_CELLS} x {N_CELLS} patch of each of the 9 samples at grids spacing/8, /16 (and /32 for fvm and fdm), vs the solver with the same bc; "
                 "about 5-10 min, <= 2 GB",
            "D": f"Shen Table II contrasts, array side {SHEN_PAD_SIDE_MM} mm x theta_ta {SHEN_THETA_TA} K/W (ASSUMED sweeps), reference unit cell per row; about 2 min for the reference "
                 "for fvm and fdm on 3 array sides x 12 rows x grid pitch/8 (the 3D solid is not in the default list); at most 1.5 GB. Fig. 16, 20 and 22 of the paper are still to be read "
                 "(README 4.4): until then theta_ta is a sweep"}
    for p in parts:
        print(f"  part {p}: {info[p]}")
    print("  outputs: research/paper-case-studies/out/study_measured_vias.json (git-ignored)")


def main(argv=None):
    """!
    @brief Entry point.
    @param argv Optional argument list.
    @return int Exit code.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--parts", default="A,B,C,D", help="comma list of A, B, C, D")
    ap.add_argument("--dry-run", action="store_true", help="print the plan and the declared cost, solve nothing")
    ap.add_argument("--quick", action="store_true", help="part C: one sample per arrangement, models fvm and analytic only")
    args = ap.parse_args(argv)
    parts = [p.strip().upper() for p in args.parts.split(",") if p.strip()]
    if args.dry_run:
        plan(parts)
        return 0
    result = {}
    if "A" in parts:
        result["A"] = part_a()
    if "B" in parts:
        result["B"] = part_b()
    if "C" in parts:
        result["C"] = part_c(args.quick)
    if "D" in parts:
        result["D"] = {f"{k}": v for k, v in part_d().items()}
    with open(OUT / "study_measured_vias.json", "w") as f:
        json.dump(result, f, indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
