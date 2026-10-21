"""!
@file stackup_outline_study.py
@brief Validation tables of the advanced stack-up and of the board outline: every model on several stacks and several board shapes.

@details Stack-up: a 4-layer 60 x 40 mm board with full copper on every layer, vias under a 6 x 6 mm heater of 3 W, natural convection typed (12 W/m2K both faces).
         Outline: the same board with an L, T, round and chamfered shape; the 3D solid is the independent check of the FVM.
         The tables are the ones of docs/validation.md section 12.

Usage: python examples/stackup_outline_study.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np                                                    # noqa: E402

from pcbthermal import Problem, SolverOptions, simulate               # noqa: E402

MODELS = ("fvm", "fdm", "solid3d", "lumped", "analytic")
STACKS = {
    "simple, equal FR-4 gaps": None,
    "advanced, the same gaps": "same",
    "thin prepreg 0.1 mm top and bottom, 0.7 mm core": [(0.10, 0.3, 0.9), (0.70, 0.3, 0.9), (0.10, 0.3, 0.9)],
    "prepreg 0.1 mm, metal-core dielectric 1 mm (2 W/mK)": [(0.10, 0.3, 0.9), (1.00, 2.0, 2.0), (0.10, 0.3, 0.9)],
    "polyimide flex 0.1 mm gaps (0.15 W/mK)": [(0.10, 0.15, 0.15), (0.10, 0.15, 0.15), (0.10, 0.15, 0.15)],
    "alumina core 0.6 mm (24 W/mK)": [(0.10, 0.3, 0.9), (0.60, 24.0, 24.0), (0.10, 0.3, 0.9)],
}


def board(stack=None, outline=None, copper=(35, 35, 35, 35)):
    """!
    @brief The study board.
    @param stack None (simple), "same" or a list of (thickness mm, k through, k in-plane) per gap.
    @param outline Outline polygon in mm or None.
    @param copper Copper thickness of the four layers in micrometres.
    @return Problem.
    """
    p = Problem.new(60, 40, 4, thickness_mm=1.6)
    p.board.h_mode, p.board.h_top, p.board.h_bottom = "manual", 12.0, 12.0
    for l in range(1, 5):
        p.add_zone(l, rect=(1, 1, 59, 39))
    p.add_heater(1, 3.0, rect=(27, 17, 33, 23), name="U1")
    for x in (28, 30, 32):
        for y in (18, 20, 22):
            p.add_via(x, y, 0.3)
    p.board.copper_thickness = [c * 1e-6 for c in copper]
    if stack is not None:
        p.board.make_advanced()
        if stack != "same":
            for d, (t, kz, kp) in zip(p.board.dielectrics, stack):
                d.thickness, d.k_through, d.k_inplane = t * 1e-3, kz, kp
            p.board.thickness = p.board.total_thickness()
    if outline is not None:
        p.set_outline(outline)
    return p


def rises(p, models, cell=1.0):
    """!
    @brief Maximum temperature rise of each model.
    @param p Problem.
    @param models Model keys.
    @param cell Cell size in mm.
    @return Dict model -> rise in kelvin.
    """
    out = {}
    for m in models:
        out[m] = simulate(p, SolverOptions(models=(m,), cell_mm=cell)).results[m].t_max - 25.0
    return out


def main():
    """!
    @brief Print the two tables.
    """
    print("A. Advanced stack-up: rise of the hottest point [K] (FVM) and the other models as a difference from the FVM [%]")
    print("| Stack | FVM | FDM | 3D solid | Lumped | Analytic |")
    print("| :-- | --: | --: | --: | --: | --: |")
    for name, st in STACKS.items():
        r = rises(board(st), MODELS)
        print(f"| {name} | {r['fvm']:.1f} | " + " | ".join(f"{100 * (r[m] / r['fvm'] - 1):+.1f} %" for m in MODELS[1:]) + " |", flush=True)
    heavy = rises(board(None, copper=(70, 35, 35, 70)), MODELS)
    light = rises(board(None, copper=(17.5, 17.5, 17.5, 17.5)), MODELS)
    print(f"| copper 70 / 35 / 35 / 70 µm | {heavy['fvm']:.1f} | " + " | ".join(f"{100 * (heavy[m] / heavy['fvm'] - 1):+.1f} %" for m in MODELS[1:]) + " |")
    print(f"| copper 17.5 µm on every layer | {light['fvm']:.1f} | " + " | ".join(f"{100 * (light[m] / light['fvm'] - 1):+.1f} %" for m in MODELS[1:]) + " |")
    print()
    shapes = {
        "rectangle (no outline)": None,
        "L shape": [[0, 0], [60, 0], [60, 20], [30, 20], [30, 40], [0, 40]],
        "T shape": [[0, 20], [20, 20], [20, 0], [40, 0], [40, 20], [60, 20], [60, 40], [0, 40]],
        "ellipse": [[30 + 30 * np.cos(t), 20 + 20 * np.sin(t)] for t in np.linspace(0, 2 * np.pi, 48, endpoint=False)],
        "chamfered corners (6 mm)": [[6, 0], [54, 0], [60, 6], [60, 34], [54, 40], [6, 40], [0, 34], [0, 6]],
    }
    print("B. Board outline: rise of the hottest point [K] with the FVM, and the FDM and the 3D solid as a difference from it [%]")
    print("| Shape | Board area | FVM | FDM | 3D solid |")
    print("| :-- | --: | --: | --: | --: |")
    for name, o in shapes.items():
        p = board(None, o)
        r = rises(p, ("fvm", "fdm", "solid3d"))
        print(f"| {name} | {p.board.board_area() * 1e6:.0f} mm² | {r['fvm']:.1f} | {100 * (r['fdm'] / r['fvm'] - 1):+.1f} % | {100 * (r['solid3d'] / r['fvm'] - 1):+.1f} % |", flush=True)


if __name__ == "__main__":
    main()
