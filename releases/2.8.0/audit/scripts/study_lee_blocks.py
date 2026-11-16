#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_lee_blocks.py
@brief Seri Lee's plate (Electronics Cooling, January 1998) run through the program's metal-block model (`pcbthermal/blocks.py`) in the FVM, FDM and 3D solid.
@details The article: an aluminium base 100 x 100 x 1.3 mm (k 200 W/mK), a 25 x 25 mm source at the centre, the middle of an edge or a corner, R0 = 1.0 K/W on the
         fin side; printed maximum constriction resistance Rc 0.66 / 1.29 / 2.38 K/W. Here the plate is a block covering a one-layer board whose copper (5 um,
         k 1) and laminate (k 0.05) carry no heat sideways, both board faces adiabatic, a contact resistance of 1e-9 m2K/W, and the film of the fin side on the
         exposed face of the block. The walls of a block take h_face + h_extra, while Lee's sides are insulated, so the film is given by plate fins of a tiny
         face coefficient whose fin ratio brings the exposed face to 100 W/m2K (walls 0.05 % of the film). Rc = maximum minus mean of the block temperature.
         Question answered: does the program's own plate model (not a re-implementation) reproduce the published plate? (audit of 2.8.0, REVIEW_A1.md).
         Run from the repository root: .venv/bin/python releases/2.8.0/audit/scripts/study_lee_blocks.py [fvm,fdm,solid3d] [2,1,0.5] (about 10 s for the FVM and FDM,
         1.8 GB for the 3D solid at 0.5 mm).
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from pcbthermal import blocks, fdm, fvm, solid3d  # noqa: E402
from pcbthermal.model import Materials, Problem  # noqa: E402

PAPER = {"centre": 0.66, "edge midpoint": 1.29, "corner": 2.38}   # Printed Rc in K/W
SERIES = {"centre": 0.6637, "edge midpoint": 1.2799, "corner": 2.2700}   # Exact thin plate, research/published-cases-followup 7
SIDE, SRC, H_FILM = 100.0, 25.0, 100.0                              # mm, mm, W/m2K (R0 = 1 K/W over 0.01 m2)


def source_rect(position):
    """!
    @brief The source rectangle of a position.
    @param position "centre", "edge midpoint" or "corner".
    @return Tuple (x0, y0, x1, y1) in mm.
    """
    c = (SIDE - SRC) / 2
    return {"centre": (c, c, c + SRC, c + SRC), "edge midpoint": (c, 0.0, c + SRC, SRC), "corner": (0.0, 0.0, SRC, SRC)}[position]


def build(position):
    """!
    @brief The plate as a block under a board that carries no heat sideways.
    @param position Source position name.
    @return Problem.
    """
    mat = Materials(k_copper=1.0, k_fr4_through=0.05, k_fr4_inplane=0.05)
    p = Problem.new(SIDE, SIDE, layers=1, thickness_mm=0.2, copper_um=5.0, h_top=0.0, h_bottom=0.0, h_side=None, materials=mat)
    p.add_zone(1, rect=(0, 0, SIDE, SIDE))
    p.add_heater(1, 1.0, rect=source_rect(position))
    p.add_heatsink(1, 0.0, rect=(0, 0, SIDE, SIDE), thickness_mm=1.3, k=200.0, contact_r=1e-9,
                   fin_height_mm=50.0, fin_thickness_mm=0.1, fin_pitch_mm=1.0)
    s = p.heatsinks[0]
    # Bisection on the face coefficient so that h_face x fin ratio = H_FILM on the exposed face (the walls keep only h_face)
    lo, hi = 1e-3, H_FILM
    for _ in range(200):
        mid = np.sqrt(lo * hi)
        lo, hi = (lo, mid) if blocks.exposed_h(s, mid) > H_FILM else (mid, hi)
    p.board.h_top = mid
    return p


def solve(problem, model, cell_mm):
    """!
    @brief Steady solve of one model.
    @param problem Problem.
    @param model "fvm", "fdm" or "solid3d".
    @param cell_mm Cell in mm.
    @return SteadyResult.
    """
    if model == "fvm":
        return fvm.solve_steady(problem, cell_mm=cell_mm)
    if model == "fdm":
        return fdm.solve_steady(problem, cell_mm=cell_mm)
    return solid3d.solve_steady(problem, cell_mm=cell_mm)


def main():
    """!
    @brief Print Rc and R0 for every position, model and cell.
    @return None.
    """
    models = sys.argv[1].split(",") if len(sys.argv) > 1 else ["fvm", "fdm"]
    cells = [float(c) for c in sys.argv[2].split(",")] if len(sys.argv) > 2 else [2.0, 1.0, 0.5]
    for cell in cells:
        for pos in PAPER:
            p = build(pos)
            out = []
            for m in models:
                T = np.asarray(solve(p, m, cell).arrays["block_T"])[0]
                rc = float(T.max() - T.mean())
                out.append(f"{m} Rc {rc:.4f} ({100 * (rc / PAPER[pos] - 1):+.1f} % printed, {100 * (rc / SERIES[pos] - 1):+.2f} % series) R0 {T.mean() - p.board.ambient:.4f}")
            print(f"cell {cell} mm, {pos:13s} printed {PAPER[pos]}: " + " | ".join(out), flush=True)


if __name__ == "__main__":
    main()
