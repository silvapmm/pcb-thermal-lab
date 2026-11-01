#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_via_array_sources.py
@brief The via-array unit cell of Shen and others (2019, equations 2 to 7) and Gezala and others (2025, equations 1 to 5): the claims of the papers reproduced, then the program's models on the closest board.
@details Part 1 evaluates the three parallel vertical paths of a via unit (filler, barrel, copper and FR4 layers) with the printed equations and reproduces the numbers that Shen and others print
         for the optimum diameter and the penalty of other diameters (s = 0.2 mm, plating 25 um, Table I conductivities). Part 2 builds the closest representable board of the program (a 5.6 mm square
         of four copper layers, 12 x 12 vias of 0.25 mm on a 0.45 mm pitch, the heater over the whole board, an almost isothermal bottom face) and compares the top-to-bottom resistance of the
         models with the unit-cell sum of the paper. The paper's cell has no lateral spreading beyond the unit, no constriction and no via footprint on the grid, so the comparison measures what
         those terms add. The review added the reference that models the same board as the program (the barrel over the dielectric gaps only, since the full planes join it, plus the
         closed-form constriction of the heat in the top and bottom planes): the paper's unit sum is not that reference (it is 9 % high on the barrel length and has no constriction). Run: .venv/bin/python research/theory-sources/scripts/study_via_array_sources.py (from the repository root; about 1 minute, under 1 GB).
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

K_CU, K_SOLDER, K_FR4, K_AIR = 393.0, 57.3, 0.29, 0.026       # Shen and others, Table I (through-plane FR4 0.29, in-plane 0.81)
T_PTH = 25e-6                                                  # via plating, m (page 5: 25 um is the standard)


def unit_resistance(phi, s, k_fill, t=1.6e-3, n_cu=4, t_cu=35e-6, pattern=1):
    """!
    @brief Vertical resistance of one via unit, the three paths in parallel (Shen equations 2 and 3, Gezala equations 1 to 4).
    @param phi Via diameter in m.
    @param s Edge-to-edge spacing in m.
    @param k_fill Conductivity of the filler in W/mK.
    @param t Board thickness in m.
    @param n_cu Number of copper layers.
    @param t_cu Copper thickness of each layer in m.
    @param pattern 1 for the square unit (phi + s)^2, 2 for the staggered unit sqrt(3) (phi + s)^2 / 2.
    @return float Resistance of the unit in K/W.
    """
    cell = (phi + s) ** 2 if pattern == 1 else np.sqrt(3.0) * (phi + s) ** 2 / 2.0
    r_fill = t / (k_fill * np.pi * (phi / 2 - T_PTH) ** 2)
    r_barrel = t / (K_CU * np.pi * T_PTH * (phi - T_PTH))
    # the laminate path: copper and FR4 layers in series through the thickness, over the cell area less the via disc
    r_lam = (n_cu * t_cu / K_CU + (t - n_cu * t_cu) / K_FR4) / (cell - np.pi * phi ** 2 / 4)
    return 1.0 / (1.0 / r_fill + 1.0 / r_barrel + 1.0 / r_lam)


def normalised(phi, s, k_fill, pattern=1, **kw):
    """!
    @brief The unit resistance normalised to an FR4 block of the same footprint and thickness (Shen equation 5).
    @param phi Via diameter in m.
    @param s Spacing in m.
    @param k_fill Filler conductivity in W/mK.
    @param pattern 1 or 2.
    @param kw Other arguments of unit_resistance (t, n_cu, t_cu).
    @return float Normalised resistance.
    """
    t = kw.get("t", 1.6e-3)
    cell = (phi + s) ** 2 if pattern == 1 else np.sqrt(3.0) * (phi + s) ** 2 / 2.0
    return unit_resistance(phi, s, k_fill, pattern=pattern, **kw) / (t / (K_FR4 * cell))


def part1():
    """!
    @brief Reproduce the optimum diameters and the penalties printed by Shen and others (pages 6 and 7).
    @return dict of the printed numbers for the tests.
    """
    s = 0.2e-3
    # the grid starts at 0.052 mm: at phi = 2 x plating the filler bore has no area (the filler path is then open)
    phis = np.linspace(0.052e-3, 1.5e-3, 2897)
    out = {}
    print("Part 1: Shen and others (2019), s = 0.2 mm, plating 25 um, 4 layers of 35 um, t = 1.6 mm")
    for name, kf, paper_opt, paper_pen_phi, paper_pen in (("air", K_AIR, 0.25, 0.8, 44.0), ("solder", K_SOLDER, 0.8, 0.2, 23.0)):
        v = np.array([normalised(p, s, kf) for p in phis])
        i = int(v.argmin())
        pen = 100 * (normalised(paper_pen_phi * 1e-3, s, kf) / v[i] - 1)
        r2 = normalised(phis[i], s, kf, pattern=2) / normalised(phis[i], s, kf, pattern=1)
        print(f"  {name:6s} optimum phi {phis[i] * 1e3:.3f} mm (paper about {paper_opt}); phi = {paper_pen_phi} mm costs +{pen:.1f} % (paper +{paper_pen:.0f} %); pattern II / pattern I {r2:.4f} (paper 0.866)")
        out[name] = (phis[i] * 1e3, pen, r2)
    # the three designs of the references the paper quotes (air filled, square pattern, s as the references give it), against the optimum of each pattern:
    # the paper compares with "the proposed optimal trajectories (see Fig. 4)", which include the staggered pattern II of Fig. 4(c) (review: the
    # printed 47 / 89.5 / 46.4 % are those of the pattern II optimum, the pattern I optimum gives 39 / 88 / 38.5 %)
    best = {pat: min(normalised(p, s, K_AIR, pattern=pat) for p in phis) for pat in (1, 2)}
    for phi, ss, paper in ((0.3e-3, 0.34e-3, 47.0), (0.2e-3, 1.0e-3, 89.5), (0.33e-3, 0.34e-3, 46.4)):
        red = {pat: 100 * (1 - best[pat] / normalised(phi, ss, K_AIR)) for pat in (1, 2)}
        print(f"  reference design phi {phi * 1e3:.2f} mm s {ss * 1e3:.2f} mm: the optimum (phi 0.25, s 0.2) lowers the resistance by {red[1]:.1f} % (pattern I) "
              f"or {red[2]:.1f} % (pattern II) (paper {paper} %)")
        out[f"ref{phi}"] = red[1]
        out[f"ref{phi}_II"] = red[2]
    return out


def series_of_gaps(side, pitch, phi, nv, n_cu=4, t=1.6e-3, t_cu=35e-6):
    """!
    @brief Independent reference of part 2 (added by the review): the one-dimensional resistance with the barrel counted over the dielectric gaps only.
    @details With a full copper plane on every layer, the copper of a plane joins the barrel over its own thickness, so the barrel conducts in series with
             the planes only across the n_cu - 1 dielectric gaps (t - n_cu t_cu in all); in each gap the barrels and the FR4 are in parallel. Shen's unit
             counts the barrel over the whole thickness t and puts the copper layers in series with the FR4 only (no contact between barrel and planes).
    @param side Board side in mm.
    @param pitch Via pitch in mm.
    @param phi Via diameter in mm.
    @param nv Vias per side.
    @param n_cu Number of copper layers.
    @param t Board thickness in m.
    @param t_cu Copper thickness of a layer in m.
    @return float Resistance in K/W.
    """
    d = t - n_cu * t_cu
    g_bar = nv * nv * K_CU * np.pi * T_PTH * (phi * 1e-3 - T_PTH) / d
    g_fr4 = K_FR4 * ((side * 1e-3) ** 2 - nv * nv * np.pi * (phi * 1e-3) ** 2 / 4) / d
    return 1.0 / (g_bar + g_fr4)


def plane_constriction(pitch, phi, a, t_cu=35e-6, h_bottom=1.0e6, side=5.6):
    """!
    @brief Closed-form constriction of the heat in the top and bottom planes on its way into and out of one barrel (added by the review).
    @details Top: a uniform flux over the circular cell of the same area as the unit (radius R) drained by an isothermal circle of radius a in a sheet
             of conductance S: dT = Q / (2 pi S) [R^4 / (R^2 - a^2)^2 ln(R / a) - (3 R^2 - a^2) / (4 (R^2 - a^2))] (mean of the cell minus the circle).
             Bottom: the barrel end as an isothermal circle feeding a fin of the plane on the film h_bottom, K0(x) / (2 pi S x K1(x)), x = a / lambda,
             lambda = sqrt(S / h), minus the mean rise Q_total / (h A) that the read-out subtracts.
    @param pitch Via pitch in mm.
    @param phi Via diameter in mm (unused: the radius of the sink is a).
    @param a Radius of the isothermal sink in m (the drill radius, or 0.78 times it for the program's target radius).
    @param t_cu Copper thickness in m.
    @param h_bottom Film coefficient of the bottom face in W/m2K.
    @param side Board side in mm.
    @return Tuple (top, bottom) of temperature drops in K per watt of the board, for 144 vias.
    """
    from scipy.special import k0, k1
    s_sheet = K_CU * t_cu
    q = 1.0 / 144.0
    r = pitch * 1e-3 / np.sqrt(np.pi)
    r2, a2 = r * r, a * a
    top = q / (2 * np.pi * s_sheet) * (r2 * r2 / (r2 - a2) ** 2 * np.log(r / a) - (3 * r2 - a2) / (4 * (r2 - a2)))
    x = a / np.sqrt(s_sheet / h_bottom)
    bottom = q * k0(x) / (2 * np.pi * s_sheet * x * k1(x)) - 1.0 / (h_bottom * (side * 1e-3) ** 2)
    return top, bottom


def part2():
    """!
    @brief The closest board of the program: a 5.6 mm square with 12 x 12 vias, resistance from the top copper to the bottom copper.
    @return dict model -> resistance in K/W, plus the unit-cell sum.
    """
    from pcbthermal import Problem, SolverOptions, simulate
    from pcbthermal.model import Materials

    side, pitch, phi, nv = 5.6, 0.45, 0.25, 12
    mat = Materials(k_copper=K_CU, k_fr4_through=K_FR4, k_fr4_inplane=0.81)
    ref = nv * nv
    r_cells = unit_resistance(phi * 1e-3, (pitch - phi) * 1e-3, K_AIR) / ref
    print(f"\nPart 2: {nv} x {nv} open vias of {phi} mm at {pitch} mm pitch on a {side} mm square, 4 layers of 35 um, 1.6 mm; unit-cell sum of the paper {r_cells:.4f} K/W")
    r_gaps = series_of_gaps(side, pitch, phi, nv)
    print(f"  review: barrel over the three dielectric gaps only (1.46 mm), barrels and FR4 in parallel in each gap: {r_gaps:.4f} K/W")
    for a in (phi / 2 * 1e-3, 0.78 * phi / 2 * 1e-3):
        top, bottom = plane_constriction(pitch, phi, a)
        print(f"  review: plus the closed-form constriction in the planes (sink radius {a * 1e3:.4f} mm): top {top:.4f} + bottom {bottom:.4f} K/W -> {r_gaps + top + bottom:.4f} K/W")
    out = {"paper_cells": r_cells, "gaps": r_gaps}
    for cell in (0.2, 0.1, 0.05):
        # the review added 0.05 mm for the FVM only (grid convergence of the reference model; the 3D solid would exceed its size limit)
        for m in (("fvm", "fdm", "solid3d", "analytic", "lumped") if cell > 0.06 else ("fvm",)):
            # a 1 W heater over the whole top face, the bottom face held by a very large coefficient, no other loss
            p = Problem.new(side, side, layers=4, thickness_mm=1.6, copper_um=35.0, ambient=0.0, h_top=0.0, h_bottom=1.0e6, h_side=0.0, materials=mat)
            p.board.via_plating = T_PTH
            p.add_full_copper()
            p.add_heater(1, 1.0, rect=(0.0, 0.0, side, side), name="U")
            off = (side - (nv - 1) * pitch) / 2
            p.add_via_array((off - pitch / 2, off - pitch / 2, side - off + pitch / 2, side - off + pitch / 2), nv, nv, diameter=phi)
            try:
                res = simulate(p, SolverOptions(models=(m,), cell_mm=cell)).results[m]
                T = np.asarray(res.T)
                r = float(T[0].mean() - T[-1].mean())
            except Exception as exc:                          # a model that refuses the board is reported, not hidden
                print(f"  {m} cell {cell}: {type(exc).__name__}: {exc}")
                r = float("nan")
            print(f"  {m:9s} cell {cell:4.2f} mm: top minus bottom copper {r:.4f} K/W")
            out[(m, cell)] = r
    return out


def main():
    """!
    @brief Run both parts and print the tables.
    @return None.
    """
    part1()
    part2()


if __name__ == "__main__":
    main()
