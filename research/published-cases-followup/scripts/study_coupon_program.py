#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_coupon_program.py
@brief Item 2: the coupon of Culham and Yovanovich (1998) (50 x 50 mm, FR-4 / Cu / FR-4 / Cu / FR-4, a concentric source, h = 5 W/m2K on both faces, insulated sides): the program's five models on the
       paper's base stack and on its case 2, as a solid-body resistance and as an effective conductivity, against the independent solver and against the published numbers.
@details The earlier study (`research/effective-conductivity`, 4.5) could run the program only on Cu / FR-4 / Cu (case 2), because the layered models have copper on the outer faces. The base stack of the
         paper (FR-4 0.5263 mm on both outer faces) IS representable: a 4-layer board whose two outer "copper" layers are left undrawn (36 um of laminate, nothing in them) with the advanced stack-up
         gaps chosen so that the distances from the top face to the copper planes are the paper's (`g_outer = 0.5263 + 0.0178 - 0.0360 - 0.0178 mm`). The source heats the outer slot (the face temperature is
         what `analysis.heater_stats` reports). The program applies the film under the source too (the paper insulates the source area), so the independent solver is run in BOTH conditions: its paper-condition
         value is the one to compare with the publication, its program-condition value the one to compare with the program.
         Metric: R_solid = (mean source - mean wall) / Q, the wall being the film-cooled faces; k_e is the conductivity of the single layer of the same thickness, films and source that has the same R_solid
         (bisection, the paper's definition, equation 11). Published: k_e = 8.28 W/mK for the base stack (text, p. 462), 11.6 W/mK for case 2 (plot), cross-plane 0.42 at epsilon = 1 (text).
         Run from the repository root: .venv/bin/python research/published-cases-followup/scripts/study_coupon_program.py (about 4 minutes, under 1 GB).
"""

import json
import sys

import _bootstrap
import numpy as np

import layered3d as L3

OUT = _bootstrap.OUT
H, POWER, W = 5.0, 2.5, 50e-3
T_CU, T_FR4 = 35.6e-6, 0.5263e-3
K_CU, K_FR4 = 400.0, 0.4
SLOT = 36e-6
SIDES_MM = (6.0, 16.0, 25.0, 36.0, 50.0)                        # edges on the cells (1 mm; the 25 mm source needs 0.5 mm cells)
MODELS = ("fvm", "fdm", "solid3d", "lumped", "analytic")
PAPER_PRINTED = {"base_text": 8.28, "case2_plot": 11.6, "eps1_text": 0.42}


def slabs_for(stack, n_sub=4):
    """!
    @brief The slabs of the independent solver for a stack name.
    @param stack "base" (FR-4 / Cu / FR-4 / Cu / FR-4) or "case2" (Cu / FR-4 x 3 / Cu).
    @param n_sub Sub-slabs of every FR-4 layer.
    @return list of (thickness, conductivity, sub-slabs) from the top.
    """
    if stack == "base":
        return [(T_FR4, K_FR4, n_sub), (T_CU, K_CU, 1), (T_FR4, K_FR4, n_sub), (T_CU, K_CU, 1), (T_FR4, K_FR4, n_sub)]
    return [(T_CU, K_CU, 1), (3 * T_FR4, K_FR4, 3 * n_sub), (T_CU, K_CU, 1)]


def solver_rsolid(stack, side_mm, film_under, dx=1e-3, n_sub=4):
    """!
    @brief R_solid of the independent solver.
    @param stack Stack name.
    @param side_mm Source side in mm.
    @param film_under True: the film also acts under the source.
    @param dx Cell in m.
    @param n_sub Sub-slabs per FR-4 layer.
    @return float K/W.
    """
    n = int(round(W / dx))
    c, s = W / 2, side_mm * 1e-3
    res = L3.solve(dx, n, n, slabs_for(stack, n_sub), (c - s / 2, c - s / 2, c + s / 2, c + s / 2), POWER, H, H, film_under_source=film_under)
    return (res["mean_source"] - res["mean_wall"]) / POWER


def k_effective(r_solid, side_mm, film_under, dx=1e-3, n_sub=4, total=None):
    """!
    @brief Conductivity of the single layer (same thickness, films, source) that has the solid-body resistance r_solid (bisection on log k, the paper's definition).
    @param r_solid Target resistance in K/W.
    @param side_mm Source side in mm.
    @param film_under True: the film also acts under the source.
    @param dx Cell in m.
    @param n_sub Sub-slabs.
    @param total Thickness of the block in m (default: the stack of the base case, 1.62 mm).
    @return float W/mK.
    """
    total = total or (3 * T_FR4 + 2 * T_CU)
    n = int(round(W / dx))
    c, s = W / 2, side_mm * 1e-3
    lo, hi = np.log(0.05), np.log(2000.0)
    for _ in range(22):
        m = 0.5 * (lo + hi)
        res = L3.solve(dx, n, n, [(total, float(np.exp(m)), n_sub)], (c - s / 2, c - s / 2, c + s / 2, c + s / 2), POWER, H, H, film_under_source=film_under)
        r = (res["mean_source"] - res["mean_wall"]) / POWER
        lo, hi = (m, hi) if r > r_solid else (lo, m)
    return float(np.exp(0.5 * (lo + hi)))


def program_problem(stack, side_mm):
    """!
    @brief The coupon as a program Problem.
    @param stack "base" or "case2".
    @param side_mm Source side in mm.
    @return pcbthermal.model.Problem.
    """
    from pcbthermal import Problem
    from pcbthermal.model import Dielectric, Materials
    mat = Materials(k_copper=K_CU, k_fr4_through=K_FR4, k_fr4_inplane=K_FR4)
    c, s = 25.0, side_mm
    if stack == "case2":
        p = Problem.new(50.0, 50.0, layers=2, thickness_mm=(2 * T_CU + 3 * T_FR4) * 1e3, copper_um=T_CU * 1e6, ambient=0.0, h_top=H, h_bottom=H, h_side=None, materials=mat)
        p.add_full_copper()
    else:
        g_out = (T_FR4 + T_CU / 2 - SLOT - T_CU / 2)              # top face -> plane centre = slot + gap + half copper
        p = Problem.new(50.0, 50.0, layers=4, thickness_mm=2.0, copper_um=T_CU * 1e6, ambient=0.0, h_top=H, h_bottom=H, h_side=None, materials=mat)
        p.board.copper_thickness = [SLOT, T_CU, T_CU, SLOT]
        mk = lambda t: Dielectric(thickness=t, name="FR-4 coupon", k_through=K_FR4, k_inplane=K_FR4)
        p.board.dielectrics = [mk(g_out), mk(T_FR4), mk(g_out)]
        p.board.thickness = float(sum(p.board.copper_thickness) + g_out * 2 + T_FR4)
        for layer in (2, 3):
            p.add_zone(layer, rect=(0.0, 0.0, 50.0, 50.0))
    p.add_heater(1, POWER, rect=(c - s / 2, c - s / 2, c + s / 2, c + s / 2), name="U")
    return p


def program_rsolid(stack, side_mm, model, cell_mm=1.0, n_diel=None):
    """!
    @brief R_solid of one model of the program, defined as in the solver (film-cooled faces: the whole top and the whole bottom).
    @param stack "base" or "case2".
    @param side_mm Source side in mm.
    @param model Model key.
    @param cell_mm Cell in mm.
    @param n_diel Slabs per gap of the 3D solid (None: default).
    @return float K/W, NaN when the model refuses.
    """
    from pcbthermal import SolverOptions, simulate, analysis, solid3d
    p = program_problem(stack, side_mm)
    try:
        if model == "solid3d" and n_diel:
            res = solid3d.solve_steady(p, cell_mm=cell_mm, n_diel=n_diel)
        else:
            res = simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm)).results[model]
        T = np.asarray(res.T)
        t_src = analysis.heater_stats(res, p)[0]["t_mean"] - p.board.ambient
        walls = 0.5 * (T[0].mean() + T[-1].mean()) - p.board.ambient
        return float((t_src - walls) / POWER)
    except Exception as exc:
        print(f"  [{model}] {type(exc).__name__}: {str(exc)[:100]}", file=sys.stderr)
        return float("nan")


def main():
    """!
    @brief Run the study and write out/coupon_program.json.
    @return None.
    """
    res = {}
    for stack in ("case2", "base"):
        print(f"\n=== stack {stack} ===")
        print("   side  eps  | solver R_s (paper cond.)  k_e | solver R_s (film under)  k_e | " + " | ".join(f"{m} R_s (k_e, err %)" for m in MODELS))
        rows = []
        for side in SIDES_MM:
            eps = side * side / 2500.0
            dx = 0.5e-3 if side % 2 else 1e-3                       # the program's cell is the solver's cell
            r_paper = solver_rsolid(stack, side, False, dx)
            ke_paper = k_effective(r_paper, side, False, dx)
            r_film = solver_rsolid(stack, side, True, dx)
            ke_film = k_effective(r_film, side, True, dx)
            line = f"  {side:5.1f} {eps:5.3f} | {r_paper:9.3f} {ke_paper:7.2f} | {r_film:9.3f} {ke_film:7.2f} |"
            row = {"side": side, "eps": eps, "solver_paper": [r_paper, ke_paper], "solver_film": [r_film, ke_film], "models": {}}
            for m in MODELS:
                r = program_rsolid(stack, side, m, dx * 1e3)
                ke = k_effective(r, side, True, dx) if np.isfinite(r) else float("nan")
                row["models"][m] = [r, ke, 100 * (r / r_film - 1)]
                line += f" {r:8.3f} ({ke:5.2f}, {100 * (r / r_film - 1):+5.2f}) |"
            rows.append(row)
            print(line)
        res[stack] = rows
    print("\nPublished: base stack k_e = 8.28 W/mK at 25 mm (text); case 2 about 11.6 (plot, 25 mm); cross-plane 0.42 at epsilon = 1 (text).")
    (OUT / "coupon_program.json").write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
