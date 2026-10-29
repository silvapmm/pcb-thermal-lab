"""!
@file study_small_pad_convergence.py
@brief Where is the converged temperature of a one-sided copper pad hardly larger than its heater, and how far are the two 3D models of README section 4.2 from it?

@details The board of copper_dissipation.py (100 x 80 mm, 2 layers, 5 W on a 10 x 10 mm heater, copper only on top: the heater's own 10 mm pad or a 20 mm
         pad, no vias). Part 1 (the board as it is, anisotropic FR-4 0.3 / 0.9 W/mK, edge coefficient 10 W/m2K): the program's 3D solid (finite volumes) and
         the finite-element solid of fem3d_validation.py at 1 and 0.5 mm, with 4 and 8 slabs (elements) per gap; these are the numbers quoted in README 4.2.
         Part 2 (the same board with isotropic FR-4 at 0.3 W/mK and no edge loss, so that the independent solver of lib/layered3d.py represents it too): the
         three 3D solvers at 1 and 0.5 mm (0.25 mm needs more memory than a direct solve of the independent solver can use on a laptop). The independent solver puts its maximum on a copper cell centre, the program's 3D solid too; the FEM on a node.

         The 0.5 mm columns with 8 slabs per gap have 320 000 unknowns, above the application's limit of 250 000 (solid3d.MAX_CELLS), so the script runs inside
         solid3d.size_limit; the limit of the application is not changed.

Usage: .venv/bin/python research/solid3d-verification/scripts/study_small_pad_convergence.py   (from the repository root; needs scikit-fem; about 6 minutes)
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import fem3d_validation as f3                                          # noqa: E402
import layered3d as L3                                                  # noqa: E402
from pcbthermal import Problem, solid3d                                 # noqa: E402
from pcbthermal.model import Materials                                  # noqa: E402

K_ISO = 0.3


def board(pad_mm, iso=False):
    """!
    @brief The board of copper_dissipation.py with a top copper pad centred on the heater.
    @param pad_mm Side of the top pad in mm (10 is the heater's own pad).
    @param iso True for isotropic FR-4 at 0.3 W/mK and no edge loss (part 2).
    @return Problem.
    """
    kw = dict(h_side=None, materials=Materials(k_fr4_through=K_ISO, k_fr4_inplane=K_ISO)) if iso else {}
    p = Problem.new(100, 80, 2, **kw)
    p.add_zone(1, rect=(50 - pad_mm / 2, 40 - pad_mm / 2, 50 + pad_mm / 2, 40 + pad_mm / 2))
    p.add_heater(1, 5.0, rect=(45, 35, 55, 45))
    return p


def independent(p, pad_mm, cell_mm, n_gap=8):
    """!
    @brief Maximum temperature of the board of part 2 in the independent 3D solver (copper slab patterned, laminate isotropic).
    @param p Problem of board(pad_mm, iso=True).
    @param pad_mm Side of the top pad in mm.
    @param cell_mm Cell size in mm.
    @param n_gap Sub-slabs across the dielectric gap.
    @return float Maximum temperature in degC (hottest copper cell centre).
    """
    b = p.board
    dx = cell_mm * 1e-3
    nx, ny = int(round(100 / cell_mm)), int(round(80 / cell_mm))
    xs, ys = (np.arange(nx) + 0.5) * cell_mm, (np.arange(ny) + 0.5) * cell_mm
    k_top = np.where((np.abs(xs[None, :] - 50.0) < pad_mm / 2) & (np.abs(ys[:, None] - 40.0) < pad_mm / 2), b.materials.k_copper, K_ISO)
    t_cu = b.copper_thickness[0]
    slabs = [(t_cu, k_top, 1), (b.dielectric_thickness(), K_ISO, n_gap), (t_cu, K_ISO, 1)]     # No copper on the bottom layer: its slab is laminate
    r = L3.solve(dx, nx, ny, slabs, (45e-3, 35e-3, 55e-3, 45e-3), 5.0, b.h_top, b.h_bottom, film_under_source=True)
    return float(r["cell_max_source"] + b.ambient)


def main():
    """!
    @brief Print the two convergence tables.
    @return None.
    """
    print("Part 1: the board of copper_dissipation.py, maximum temperature [degC]")
    print("| pad | model | 1 mm, 4 per gap | 0.5 mm, 4 per gap | 1 mm, 8 per gap | 0.5 mm, 8 per gap |")
    print("| :-- | :-- | --: | --: | --: | --: |")
    for pad in (10, 20):
        p = board(pad)
        fv = [solid3d.solve_steady(p, c, n_diel=n).t_max for n, c in ((4, 1.0), (4, 0.5), (8, 1.0), (8, 0.5))]
        fe = [f3.solve_fem(p, c, n_diel=n)["t_max"] for n, c in ((4, 1.0), (4, 0.5), (8, 1.0), (8, 0.5))]
        print(f"| {pad} mm | 3D solid (FV) | " + " | ".join(f"{v:.1f}" for v in fv) + " |")
        print(f"| {pad} mm | 3D FEM | " + " | ".join(f"{v:.1f}" for v in fe) + " |", flush=True)
    print("\nPart 2: isotropic FR-4 0.3 W/mK, no edge loss, 8 slabs per gap, maximum temperature [degC]", flush=True)
    print("| pad | model | 1 mm | 0.5 mm |")
    print("| :-- | :-- | --: | --: |")
    for pad in (10, 20):
        p = board(pad, iso=True)
        cells = (1.0, 0.5)
        rows = {"independent (lib/layered3d.py)": [independent(p, pad, c) for c in cells],
                "3D solid (FV)": [solid3d.solve_steady(p, c, n_diel=8).t_max for c in cells],
                "3D FEM": [f3.solve_fem(p, c, n_diel=8)["t_max"] for c in cells]}
        for name, vals in rows.items():
            print(f"| {pad} mm | {name} | " + " | ".join(f"{v:.1f}" for v in vals) + " |", flush=True)


if __name__ == "__main__":
    # The 0.5 mm columns with 8 slabs per gap have 320 000 unknowns, above the application's limit (solid3d.MAX_CELLS = 250 000); this offline study
    # accepts the longer direct solve, so it runs inside size_limit (the limit of the application is restored afterwards).
    with solid3d.size_limit(500_000):
        main()
