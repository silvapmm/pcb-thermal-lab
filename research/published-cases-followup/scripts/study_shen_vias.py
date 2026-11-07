#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_shen_vias.py
@brief Item 4: the via array of Shen, Wang, Blaabjerg, Zhao and Long (IEEE Trans. Power Electron. 35(1), 2020, pp. 882-900): the published numbers of section II (equations 5 to 7, the optimal diameter, the +44 % and +23 %
       and the 47 / 89.5 / 46.4 % reductions, the 5.6 mm board of Fig. 17) reproduced from the equations, an independent axisymmetric unit-cell solver, and the program's via model (FVM, FDM, 3D solid; Lumped and
       Analytic reported) on the same via arrays.
@details Part A: the closed forms (equation 5 for Pattern I, its simplification 6, the optimal diameter 7) against the numbers printed in the text of page 7 (manuscript numbering) and in section IV (120.3 K/W without
         vias, 1.86 K/W with 12 x 12 vias of 0.25 mm). Part B: equation 4 (parallel paths, no lateral flow in the layers) against the axisymmetric unit cell of `research/lumped-zones-adoption/lib/shen_case.py`
         (imports nothing of the program) for a sweep of the diameter and of the filler. Part C: the program on the array board (n x n vias on the pitch phi + s, the board exactly n pitches wide with insulated edges,
         full copper on four layers of 70 um, a uniform flux over the whole top, the bottom film so large that the bottom is the ambient): the array resistance R = (mean top temperature) / P against the unit cell;
         cells of pitch / 3 and pitch / 2. Run from the repository root: .venv/bin/python research/published-cases-followup/scripts/study_shen_vias.py [--no-program] (about 3 minutes, under 1 GB).
"""

import json
import math
import sys

import _bootstrap
import numpy as np

sys.path.insert(0, str(_bootstrap.HERE.parent / "lumped-zones-adoption" / "lib"))
import shen_case as SC            # noqa: E402  (the unit cell and the paper's formulas; imports nothing of the program at module level)
import via_cell as VC             # noqa: E402  (the same cell with the two switches of the program's idealisation)
import cart_cell as CC            # noqa: E402  (the SQUARE cell in Cartesian 3D: tests the equal-area disc of the axisymmetric cell)

OUT = _bootstrap.OUT
K_CU, K_FR4, K_FR4_IP, K_AIR, K_SOLDER = 393.0, 0.29, 0.81, 0.026, 57.3
T_PTH, T_BOARD, T_CU, N_CU = 25e-6, 1.6e-3, 70e-6, 4


def theta_n(phi, s, k_fill, t=T_BOARD, t_cu=T_CU, n_cu=N_CU, pattern=1, simplified=False):
    """!
    @brief The normalised via-array resistance, equation (5) (or its simplification, equation 6).
    @param phi Via diameter in m.
    @param s Via spacing in m.
    @param k_fill Filler conductivity in W/mK.
    @param t Board thickness in m.
    @param t_cu Copper thickness in m.
    @param n_cu Copper layers.
    @param pattern 1 or 2.
    @param simplified True: equation (6) (the copper and FR-4 layers dropped).
    @return float Theta_via / (t / (k_FR4 l w)) (dimensionless).
    """
    fill = math.pi * k_fill * (phi - 2 * T_PTH) ** 2
    barrel = 4 * math.pi * K_CU * T_PTH * (phi - T_PTH)
    keff = n_cu * t_cu / K_CU + (t - n_cu * t_cu) / K_FR4
    if pattern == 1:
        num = 4 * (s + phi) ** 2 * K_FR4
        layers = 0.0 if simplified else t * (4 * s * s + 8 * s * phi + (4 - math.pi) * phi * phi) / keff
    else:
        num = 2 * math.sqrt(3) * (s + phi) ** 2 * K_FR4
        layers = 0.0 if simplified else t * (2 * math.sqrt(3) * (s + phi) ** 2 - math.pi * phi * phi) / keff
    return num / (fill + barrel + layers)


def phi_opt(s, k_fill):
    """!
    @brief Equation (7), the optimal via diameter.
    @param s Via spacing in m.
    @param k_fill Filler conductivity in W/mK.
    @return float Diameter in m.
    """
    d = K_CU - k_fill
    return 2 * T_PTH * (s + 2 * T_PTH) * d / (2 * T_PTH * d - k_fill * s)


def part_a():
    """!
    @brief The closed-form numbers of the paper.
    @return dict.
    """
    out = {}
    print("\nA. Equations 5 to 7 against the numbers printed in section II (Table I conductivities, t_PTH = 25 um, s = 0.2 mm)")
    s = 0.2e-3
    for name, k in (("air", K_AIR), ("solder", K_SOLDER)):
        po = phi_opt(s, k)
        sweep = np.linspace(0.05e-3, 1.5e-3, 3000)
        num = sweep[np.argmin([theta_n(p, s, k) for p in sweep])]
        num6 = sweep[np.argmin([theta_n(p, s, k, simplified=True) for p in sweep])]
        out[name] = {"phi_opt_eq7": po, "phi_min_eq5": num, "phi_min_eq6": num6}
        print(f"   {name:7s} optimal diameter: equation 7 {po * 1e3:.3f} mm; minimum of equation 5 {num * 1e3:.3f} mm; of equation 6 {num6 * 1e3:.3f} mm   (printed: about 0.25 mm air, about 0.8 mm solder)")
    po_air, po_sol = out["air"]["phi_opt_eq7"], out["solder"]["phi_opt_eq7"]
    up_air = theta_n(0.8e-3, s, K_AIR) / theta_n(po_air, s, K_AIR) - 1
    up_sol = theta_n(0.2e-3, s, K_SOLDER) / theta_n(po_sol, s, K_SOLDER) - 1
    up_air6 = theta_n(0.8e-3, s, K_AIR, simplified=True) / theta_n(po_air, s, K_AIR, simplified=True) - 1
    up_sol6 = theta_n(0.2e-3, s, K_SOLDER, simplified=True) / theta_n(po_sol, s, K_SOLDER, simplified=True) - 1
    print(f"   air, phi 0.8 mm against the optimum: +{100 * up_air:.1f} % (eq 5), +{100 * up_air6:.1f} % (eq 6)   printed +44 %")
    print(f"   solder, phi 0.2 mm against the optimum: +{100 * up_sol:.1f} % (eq 5), +{100 * up_sol6:.1f} % (eq 6)   printed +23 %")
    out["increase"] = {"air_0.8": up_air, "solder_0.2": up_sol, "air_0.8_eq6": up_air6, "solder_0.2_eq6": up_sol6}
    print("   reductions of the thermal resistance of the optimal design (air, phi 0.25 mm, s 0.2 mm) against the designs of refs [15], [17], [18] (printed 47 %, 89.5 %, 46.4 %); the printed numbers are those of PATTERN II:")
    refs = {"[15] phi 0.3, s 0.34": (0.3e-3, 0.34e-3), "[17] phi 0.2, s 1.0": (0.2e-3, 1.0e-3), "[18] phi 0.33, s 0.34": (0.33e-3, 0.34e-3)}
    printed = (47.0, 89.5, 46.4)
    red = {}
    for (name, (p, ss)), pr in zip(refs.items(), printed):
        for pat in (1, 2):
            red[(name, f"eq 5, pattern {pat}")] = 1 - theta_n(po_air, s, K_AIR, pattern=pat) / theta_n(p, ss, K_AIR)
        print(f"     {name:24s} pattern I: {100 * red[(name, 'eq 5, pattern 1')]:5.1f} %   pattern II: {100 * red[(name, 'eq 5, pattern 2')]:5.1f} %   printed {pr} %")
    r62 = 1 - theta_n(0.8e-3, s, K_SOLDER, pattern=2) / theta_n(0.3e-3, 0.34e-3, K_AIR)
    print(f"   Fig. 18, section IV-A (page 14): 2.63 K/W for the design of [15] to 0.98 K/W (Pattern II, phi 0.8 mm, solder), 'up to 62 %' (2.63 -> 0.98 is {100 * (1 - 0.98 / 2.63):.1f} %); equation 5 gives {100 * r62:.1f} %")
    red[("[15] to PII 0.8 solder", "eq 5")] = r62
    out["reductions"] = {f"{k[0]}|{k[1]}": v for k, v in red.items()}
    # Pattern II is 86.6 % of Pattern I for the same area (printed)
    r2 = theta_n(0.25e-3, s, K_AIR, pattern=2, simplified=True) / theta_n(0.25e-3, s, K_AIR, simplified=True)
    print(f"   Pattern II / Pattern I (eq 6): {r2:.4f}   printed sqrt(3)/2 = 0.8660")
    print("   Fig. 17 board (5.6 x 5.6 mm, 1.6 mm, four layers of 70 um, 12 x 12 vias of 0.25 mm, s 0.2 mm; section IV, page 14):")
    r_arr = SC.shen_array_resistance()
    r_no = SC.shen_no_via_resistance()
    print(f"     equations (2)-(4): {r_arr:.3f} K/W (printed 1.82 'analytical' read from Fig. 18(a), plot; 1.86 K/W CFD text); no vias, 1D: {r_no:.1f} K/W (printed 120.3 K/W CFD)")
    a_board = SC.SIDE ** 2
    k_cfd = (T_BOARD - N_CU * T_CU) / ((120.3 - N_CU * T_CU / K_CU / a_board) * a_board)
    n_needed = SC.shen_unit_resistance() / 1.82
    r_k35 = SC.shen_array_resistance(k_fr4=0.35)
    print(f"     the printed 120.3 K/W without vias needs k_FR4(through) = {k_cfd:.3f} W/mK, not the 0.29 of Table I (0.35 gives {SC.shen_no_via_resistance(k_fr4=0.35):.1f} K/W); with 0.35 the array of equations 2-4 is {r_k35:.3f} K/W")
    print(f"     1.82 K/W (plot) would need {n_needed:.0f} via units of 0.25 mm (11 x 11 = 121 give {SC.shen_unit_resistance() / 121:.3f}, 11 x 12 = 132 give {SC.shen_unit_resistance() / 132:.3f}); the text read does not give the pad size")
    out["fig17"] = {"array_eq4": r_arr, "no_via_1d": r_no, "k_fr4_cfd_implied": k_cfd, "array_eq4_k035": r_k35, "units_for_1.82": n_needed}
    return out


def part_b():
    """!
    @brief Equation 4 against the axisymmetric unit cell, the cell with the program's idealisation, and the square cell in Cartesian 3D.
    @return dict with the rows of the axisymmetric comparison and of the square-cell check.
    """
    print("\nB. Equation 3 (parallel paths) against the independent axisymmetric unit cell, one via unit, K/W (array of N units: divide by N); the cell of the paper (hole through the planes, heat only on the solid top),")
    print("   with the copper planes continuous over the drill, and with that and the heat over the whole top (what a layered model does)")
    print("   phi mm  s mm  filler    eq.(3)   cell(paper)  eq/cell   cell(planes over hole)   cell(planes + flux over hole)")
    rows = []
    for phi in (0.15e-3, 0.25e-3, 0.45e-3, 0.8e-3):
        for kf, name in ((K_AIR, "air"), (K_SOLDER, "solder")):
            pitch = phi + 0.2e-3
            eq = SC.shen_unit_resistance(phi=phi, s=0.2e-3, k_fill=kf)
            cell = SC.unit_cell(pitch=pitch, phi=phi, k_fill=kf)
            c_pl = VC.unit_cell(pitch, phi, kf, planes_over_hole=True)
            c_id = VC.unit_cell(pitch, phi, kf, planes_over_hole=True, flux_over_hole=True)
            rows.append({"phi": phi, "filler": name, "eq3": eq, "cell": cell, "cell_planes": c_pl, "cell_ideal": c_id})
            print(f"   {phi * 1e3:5.2f}  0.20  {name:7s} {eq:9.2f}  {cell:10.2f}  {100 * (eq / cell - 1):+7.2f} %   {c_pl:10.2f} ({100 * (c_pl / cell - 1):+5.1f} %)    {c_id:10.2f} ({100 * (c_id / cell - 1):+5.1f} %)")
    print("   the equal-area disc against the square cell (Cartesian 3D finite volumes, cell = pitch / 36, partial volumes of barrel, filler and FR-4), one via unit, K/W:")
    print("   phi mm  filler    paper cell: axisymmetric  square    diff | planes + flux over hole: axisymmetric  square    diff")
    sq = []
    for phi, kf, name in ((0.25e-3, K_AIR, "air"), (0.45e-3, K_SOLDER, "solder")):
        pitch = phi + 0.2e-3
        a1 = SC.unit_cell(pitch=pitch, phi=phi, k_fill=kf)
        s1 = CC.unit_cell(pitch, phi, kf)
        a2 = VC.unit_cell(pitch, phi, kf, planes_over_hole=True, flux_over_hole=True)
        s2 = CC.unit_cell(pitch, phi, kf, planes_over_hole=True, flux_over_hole=True)
        sq.append({"phi": phi, "filler": name, "axi_paper": a1, "square_paper": s1, "axi_ideal": a2, "square_ideal": s2})
        print(f"   {phi * 1e3:5.2f}  {name:7s}  {a1:19.2f} {s1:10.2f} {100 * (s1 / a1 - 1):+6.2f} % |  {a2:29.2f} {s2:10.2f} {100 * (s2 / a2 - 1):+6.2f} %")
    return {"rows": rows, "square": sq}


def program_array(n, phi, kf, cell_mm, model, n_diel=None):
    """!
    @brief R = mean top temperature / power of an n x n via array board in one program model.
    @param n Vias per side.
    @param phi Via diameter in m.
    @param kf Filler conductivity in W/mK.
    @param cell_mm Cell in mm.
    @param model Model key.
    @param n_diel Slabs per gap of the 3D solid.
    @return float K/W (NaN when the model refuses the board).
    """
    from pcbthermal import Problem, SolverOptions, analysis, simulate, solid3d
    from pcbthermal.model import Materials
    pitch = (phi + 0.2e-3) * 1e3
    side = n * pitch
    p = Problem.new(side, side, N_CU, T_BOARD * 1e3, T_CU * 1e6, ambient=0.0, h_top=0.0, h_bottom=1.0e7, h_side=0.0, via_plating=T_PTH,
                    materials=Materials(k_copper=K_CU, k_fr4_through=K_FR4, k_fr4_inplane=K_FR4_IP))
    for layer in range(1, N_CU + 1):
        p.add_zone(layer, rect=(0.0, 0.0, side, side))
    p.add_heater(1, 1.0, rect=(0.0, 0.0, side, side))
    for i in range(n):
        for j in range(n):
            p.add_via((i + 0.5) * pitch, (j + 0.5) * pitch, phi * 1e3, fill_k=kf)
    try:
        if model == "solid3d" and n_diel:
            res = solid3d.solve_steady(p, cell_mm=cell_mm, n_diel=n_diel)
        else:
            res = simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm)).results[model]
        return float(analysis.heater_stats(res, p)[0]["t_mean"] - p.board.ambient)
    except Exception as exc:
        print(f"  [{model}] {type(exc).__name__}: {str(exc)[:100]}", file=sys.stderr)
        return float("nan")


def part_c():
    """!
    @brief The program's via arrays against the unit cell, the grid dependence of the fvm and the board without vias.
    @return dict with the rows, the grid sequence and the no-via check.
    """
    print("\nC. The program on the via-array boards (n x n vias, board n pitches wide, edges insulated): R = mean top temperature / 1 W, K/W; error (%) against the unit cell of the program's idealisation")
    variants = [("fvm", 3, None), ("fvm", 2, None), ("fdm", 3, None), ("solid3d", 3, None), ("solid3d", 3, 8), ("lumped", 3, None), ("analytic", 3, None)]
    print("   n  phi mm filler | cell(paper)/N | cell(ideal)/N | eq.(4) | " + " | ".join(f"{m}@p/{d}{'*' if nd else ''}" for m, d, nd in variants))
    rows = []
    for n, phi in ((8, 0.25e-3), (8, 0.45e-3), (8, 0.15e-3), (6, 0.8e-3)):
        for kf, name in ((K_AIR, "air"), (K_SOLDER, "solder")):
            pitch = phi + 0.2e-3
            ref_paper = SC.unit_cell(pitch=pitch, phi=phi, k_fill=kf) / (n * n)
            ref = VC.unit_cell(pitch, phi, kf, planes_over_hole=True, flux_over_hole=True) / (n * n)
            eq = SC.shen_unit_resistance(phi=phi, s=0.2e-3, k_fill=kf) / (n * n)
            line = f"  {n:2d} {phi * 1e3:5.2f} {name:7s} | {ref_paper:10.4f} | {ref:10.4f} | {eq:6.4f} |"
            row = {"n": n, "phi": phi, "filler": name, "unit_cell_paper": ref_paper, "unit_cell_ideal": ref, "eq4": eq, "models": {}}
            for m, div, nd in variants:
                v = program_array(n, phi, kf, pitch * 1e3 / div, m, nd)
                row["models"][f"{m}@p/{div}{'*' if nd else ''}"] = v
                line += f" {v:7.4f} ({100 * (v / ref - 1):+5.1f}) |"
            rows.append(row)
            print(line)
    print("   (* = solid3d with 8 slabs per gap; the model columns: R and, in brackets, the error against the cell with the planes continuous over the drill and the heat over the whole top)")
    n, phi = 8, 0.25e-3
    pitch = phi + 0.2e-3
    ref = VC.unit_cell(pitch, phi, K_AIR, planes_over_hole=True, flux_over_hole=True) / (n * n)
    print("   grid dependence of the fvm (8 x 8 vias of 0.25 mm, air): cell = pitch / d")
    grid = {}
    for d in (2, 3, 4, 6, 9):
        v = program_array(n, phi, K_AIR, pitch * 1e3 / d, "fvm")
        grid[d] = v
        print(f"     d = {d}: {v:.4f} K/W ({100 * (v / ref - 1):+.2f} %)")
    from pcbthermal import Problem, SolverOptions, analysis, simulate
    from pcbthermal.model import Materials
    side = n * pitch * 1e3
    p0 = Problem.new(side, side, N_CU, T_BOARD * 1e3, T_CU * 1e6, ambient=0.0, h_top=0.0, h_bottom=1.0e7, h_side=0.0, via_plating=T_PTH,
                     materials=Materials(k_copper=K_CU, k_fr4_through=K_FR4, k_fr4_inplane=K_FR4_IP))
    for layer in range(1, N_CU + 1):
        p0.add_zone(layer, rect=(0.0, 0.0, side, side))
    p0.add_heater(1, 1.0, rect=(0.0, 0.0, side, side))
    res = simulate(p0, SolverOptions(models=("fvm",), cell_mm=pitch * 1e3 / 3)).results["fvm"]
    t0 = analysis.heater_stats(res, p0)[0]["t_mean"]
    one_d = (N_CU * T_CU / K_CU + (T_BOARD - N_CU * T_CU) / K_FR4) / (side * 1e-3) ** 2
    print(f"   the same board without vias: program {t0:.3f} K/W, one-dimensional {one_d:.3f} K/W ({100 * (t0 / one_d - 1):+.3f} %)")
    return {"rows": rows, "grid": grid, "no_via": [t0, one_d]}


def main():
    """!
    @brief Run the parts and write out/shen_vias.json.
    @return None.
    """
    res = {"A": part_a(), "B": part_b()}
    if "--no-program" not in sys.argv:
        res["C"] = part_c()
    (OUT / "shen_vias.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
