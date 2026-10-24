"""!
@file block_contact_study.py
@brief Research on heatsinks larger than their contact: the plate model against a published spreading-resistance example, a big block touching the board only in a patch, and the effect of a temperature-dependent power.

@details 1. A plate with a small uniform source and a uniform film coefficient, against the numerical example of Seri Lee (Electronics Cooling,
            "Calculating spreading resistance in heat sinks", 1998): aluminium 100 x 100 x 1.3 mm, k = 200 W/mK, catalogue resistance R0 = 1.0 K/W, source 25 x 25 mm,
            maximum constriction resistance Rc = 0.66 K/W (total 1.66 K/W).
         2. A 40 x 40 x 3 mm aluminium block under the MOSFET board whose contact with the board is only a patch (prototype: the contact conductance of
            the block layer is masked, the rest of the block faces an air gap).
         3. The same MOSFET with Rds(on) rising with temperature (power = P0 (1 + alpha (Tj - 25))).

Usage: python research/component-heatsink/scripts/block_contact_study.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)

import numpy as np                                                    # noqa: E402
import scipy.sparse as sp                                             # noqa: E402
import scipy.sparse.linalg as spla                                    # noqa: E402

import component_study as cs                                          # noqa: E402
from pcbthermal import SolverOptions, blocks, simulate               # noqa: E402


def plate_check(n=100, side=100.0, t_mm=1.3, k=200.0, r0=1.0, src=25.0):
    """!
    @brief Maximum minus mean surface temperature of a plate with a centred square source, per watt, by finite differences on the plan (thin plate: k t lateral conductance).
    @param n Cells per side.
    @param side Plate side in mm.
    @param t_mm Plate thickness in mm.
    @param k Conductivity in W/mK.
    @param r0 Catalogue resistance in K/W (film coefficient h = 1/(r0 A)).
    @param src Side of the square source in mm.
    @return Tuple (maximum constriction resistance in K/W, total maximum resistance in K/W).
    """
    d = side * 1e-3 / n
    h = 1.0 / (r0 * (side * 1e-3) ** 2)
    g = k * t_mm * 1e-3                                    # Lateral conductance of a square cell (W/K)
    idx = np.arange(n * n).reshape(n, n)
    rows = np.concatenate([idx[:, :-1].ravel(), idx[:-1].ravel()])
    cols = np.concatenate([idx[:, 1:].ravel(), idx[1:].ravel()])
    off = sp.coo_matrix((np.full(rows.size, g), (rows, cols)), shape=(n * n, n * n))
    off = off + off.T
    K = sp.diags(np.asarray(off.sum(axis=1)).ravel() + h * d * d) - off
    q = np.zeros((n, n))
    lo, hi = int(round((side - src) / 2 / (side / n))), int(round((side + src) / 2 / (side / n)))
    q[lo:hi, lo:hi] = 1.0 / ((hi - lo) ** 2)               # One watt over the source
    theta = spla.spsolve(K.tocsc(), q.ravel()).reshape(n, n)
    mean = float((theta * h * d * d).sum())                # Equals r0 times the power
    return float(theta.max() - mean), float(theta.max())


def patch_study():
    """!
    @brief MOSFET 2 W, 40 x 40 x 3 mm aluminium block under the board (default interface 5 K cm2/W), contact limited to a centred square patch.
    @return List of (patch side in mm or None, Tj in degC).
    """
    part = cs.PARTS["MOSFET CSD17308Q3 (SON 3.3x3.3)"]
    original = blocks.extra_layers
    out = []
    for patch in (None, 25.0, 12.0, 6.0, 0.0):
        def masked(problem, cover, area, fill, dx, dy, patch=patch):
            layers = original(problem, cover, area, fill, dx, dy)
            if patch is not None:
                c = problem.board.width / 2.0
                poly = np.array([[c - patch / 2e3, c - patch / 2e3], [c + patch / 2e3, c - patch / 2e3],
                                 [c + patch / 2e3, c + patch / 2e3], [c - patch / 2e3, c + patch / 2e3]]) if patch > 0 else None
                for ly in layers:
                    mask = np.clip(cover(poly, 4) / np.maximum(ly["cov"], 1e-12), 0.0, 1.0) if poly is not None else 0.0
                    ly["g_link"] = ly["g_link"] * mask
            return layers
        blocks.extra_layers = masked
        try:
            p = cs.part_board(part, 25.0)
            p.add_heatsink(2, 0.0, rect=(10, 10, 50, 50), thickness_mm=3.0, contact_r=5.0e-4)
            s = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5))
            out.append((patch, s.results["fvm"].t_max + part["p"] * part["th"]))
        finally:
            blocks.extra_layers = original
    return out


def air_gap_coefficient(gap_mm, eps_board=0.9, eps_block=0.1, t_mean_k=330.0, k_air=0.028):
    """!
    @brief Coefficient of heat exchange across a thin air gap between the board and a block that does not touch it: conduction of the still air plus radiation between parallel plates.
    @details Valid while the Rayleigh number of the gap stays below 1708 (Nusselt number 1: no convection in the gap), which holds for gaps up to about 7 mm at a 60 K difference.
    @param gap_mm Gap in mm.
    @param eps_board Emissivity of the board face.
    @param eps_block Emissivity of the block (0.1 bare aluminium, 0.8 anodised).
    @param t_mean_k Mean temperature of the gap in K.
    @param k_air Conductivity of air at about 55 degC in W/mK.
    @return Coefficient in W/m2K.
    """
    sigma = 5.670374e-8
    h_rad = 4.0 * sigma * t_mean_k ** 3 / (1.0 / eps_board + 1.0 / eps_block - 1.0)
    return k_air / (gap_mm * 1e-3) + h_rad


def patch_gap_study():
    """!
    @brief The block-and-patch study with an air gap outside the contact patch (conduction and radiation across it) instead of an insulated board face.
    @return Dict {gap_mm: [(patch side or 0, Tj)]}.
    """
    part = cs.PARTS["MOSFET CSD17308Q3 (SON 3.3x3.3)"]
    original = blocks.extra_layers
    out = {}
    for gap in (None, 0.5, 1.0, 2.0, 5.0):
        out[gap] = []
        for patch in (25.0, 12.0, 6.0, 0.0):
            def masked(problem, cover, area, fill, dx, dy, patch=patch, gap=gap):
                layers = original(problem, cover, area, fill, dx, dy)
                c = problem.board.width / 2.0
                poly = np.array([[c - patch / 2e3, c - patch / 2e3], [c + patch / 2e3, c - patch / 2e3],
                                 [c + patch / 2e3, c + patch / 2e3], [c - patch / 2e3, c + patch / 2e3]]) if patch > 0 else None
                for ly in layers:
                    mask = np.clip(cover(poly, 4) / np.maximum(ly["cov"], 1e-12), 0.0, 1.0) if poly is not None else 0.0
                    g_gap = 0.0 if gap is None else area * ly["cov"] * (1.0 - mask) * air_gap_coefficient(gap)
                    ly["g_link"] = ly["g_link"] * mask + g_gap
                return layers
            blocks.extra_layers = masked
            try:
                p = cs.part_board(part, 25.0)
                p.add_heatsink(2, 0.0, rect=(10, 10, 50, 50), thickness_mm=3.0, contact_r=5.0e-4)
                s = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5))
                out[gap].append((patch, s.results["fvm"].t_max + part["p"] * part["th"]))
            finally:
                blocks.extra_layers = original
    return out


def tempco_study(alpha_list=(0.0, 0.0033, 0.005, 0.0067)):
    """!
    @brief Tj of the MOSFET when its power grows with the junction temperature, P = P0 (1 + alpha (Tj - 25)), linear board (constant h), iterated.
    @param alpha_list Temperature coefficients in 1/K.
    @return List of (alpha, Tj, power) or (alpha, None, None) when it runs away.
    """
    part = cs.PARTS["MOSFET CSD17308Q3 (SON 3.3x3.3)"]
    r = cs.run(part, 25.0)
    r_tot = (r["t1"] - 25.0) / part["p"]                    # K/W from the junction to ambient at the nominal point (computed h kept constant)
    out = []
    for a in alpha_list:
        tj, p = 25.0, part["p"]
        for _ in range(200):
            p = part["p"] * (1.0 + a * (tj - 25.0))
            tj_new = 25.0 + p * r_tot
            if tj_new > 400.0:
                tj = None
                break
            if abs(tj_new - tj) < 1e-6:
                tj = tj_new
                break
            tj = tj_new
        out.append((a, tj, p if tj else None))
    return out


def main():
    """!
    @brief Print the three studies.
    """
    rc, tot = plate_check()
    print(f"1. Plate against Lee et al.: maximum constriction resistance {rc:.2f} K/W (paper 0.66), total {tot:.2f} K/W (paper 1.66)")
    print("\n2. MOSFET 2 W, Al block 40 x 40 x 3 mm under the board, contact only in a centred patch (default interface 5 K cm2/W)")
    print("| Contact patch | Tj [degC] |\n| :-- | --: |")
    for patch, tj in patch_study():
        print(f"| {'whole block (40 x 40)' if patch is None else 'none' if patch == 0 else f'{patch:g} x {patch:g} mm'} | {tj:.1f} |", flush=True)
    print("\n2b. The same with an air gap outside the patch (conduction + radiation; gap in mm, block bare aluminium, emissivity 0.1)")
    study = patch_gap_study()
    print("| Gap outside the contact | patch 25 mm | 12 mm | 6 mm | none |\n| :-- | --: | --: | --: | --: |")
    for gap, rows in study.items():
        print(f"| {'insulated (board face hidden, as above)' if gap is None else f'{gap:g} mm  (h = {air_gap_coefficient(gap):.0f} W/m2K)'} | " + " | ".join(f"{t:.1f}" for _, t in rows) + " |", flush=True)
    print("\n3. MOSFET 2 W (at 25 C) with the power rising with temperature (pad 25 mm, no top path)")
    print("| alpha [%/K] | Tj [degC] | power at Tj [W] |\n| --: | --: | --: |")
    for a, tj, p in tempco_study():
        print(f"| {100 * a:.2f} | {'runaway' if tj is None else f'{tj:.1f}'} | {'-' if p is None else f'{p:.2f}'} |")


if __name__ == "__main__":
    main()
