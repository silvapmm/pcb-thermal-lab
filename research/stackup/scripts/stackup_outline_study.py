"""!
@file stackup_outline_study.py
@brief Validation tables of the advanced stack-up and of the board outline: every model on several stacks and several board shapes.

@details Stack-up: a 4-layer 60 x 40 mm board with full copper on every layer, vias under a 6 x 6 mm heater of 3 W, natural convection typed (12 W/m2K both faces).
         Outline: the same board with an L, T, round and chamfered shape; the 3D solid is the independent check of the FVM.
         The tables are the ones of docs/validation.md section 12.

Usage: python research/stackup/scripts/stackup_outline_study.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

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


def sensitivity():
    """!
    @brief Print the sensitivity of the hottest point to the uncertain numbers of a stack-up (the 4-layer typical stack-up, FVM at 1 mm).
    """
    from pcbthermal.model import combine_sheets                                  # noqa: E402

    def run(modify):
        p = board("same")
        p.board.apply_template()                                                 # The typical 4-layer stack-up (35 / 15.2 / 15.2 / 35, prepreg 210 / core 1065 / prepreg 210)
        modify(p.board)
        return rises(p, ("fvm",))["fvm"]

    base = run(lambda b: None)
    print(f"C. Sensitivity of the rise of the hottest point to the stack-up numbers (typical 4-layer stack-up, base rise {base:.1f} K)")
    print("| Change | Rise [K] | Change in the rise |")
    print("| :-- | --: | --: |")

    def scale_k(f):
        def m(b):
            for d in b.dielectrics:
                d.k_through *= f
        return m

    def scale_t(f):
        def m(b):
            for d in b.dielectrics:
                d.thickness *= f
            b.thickness = b.total_thickness()
        return m

    def prepreg_low(b):                                                          # Resin-rich prepreg at 0.25 W/mK, cores at 0.35 W/mK (the spread of the published values)
        for i, d in enumerate(b.dielectrics):
            d.k_through = 0.25 if i in (0, 2) else 0.35

    def copper(f):
        def m(b):
            b.copper_thickness = [c * f for c in b.copper_thickness]
        return m

    cases = (("dielectric k through -30 % (0.21 W/mK)", scale_k(0.7)), ("dielectric k through +30 % (0.39 W/mK)", scale_k(1.3)),
             ("all dielectric thicknesses -10 % (fabricator tolerance)", scale_t(0.9)), ("all dielectric thicknesses +10 %", scale_t(1.1)),
             ("prepreg 0.25 and core 0.35 W/mK", prepreg_low), ("finished copper 15 % thinner (etch and plating spread)", copper(0.85)),
             ("finished copper 15 % thicker", copper(1.15)))
    for name, f in cases:
        r = run(f)
        print(f"| {name} | {r:.1f} | {100 * (r / base - 1):+.1f} % |", flush=True)

    def run_novias(modify):
        p = board("same")
        p.board.apply_template()
        p.vias = []                                                              # the same board without the nine vias under the part
        modify(p.board)
        return rises(p, ("fvm",))["fvm"]

    b0 = run_novias(lambda b: None)
    lo, hi = run_novias(scale_k(0.7)), run_novias(scale_k(1.3))
    print(f"\nWithout the vias under the part: base rise {b0:.1f} K; dielectric k through -30 % / +30 %: {100 * (lo / b0 - 1):+.1f} % / {100 * (hi / b0 - 1):+.1f} %")
    d = combine_sheets([{"thickness_um": 105, "material": "FR-4 (standard)"}, {"thickness_um": 105, "material": "FR-4 (standard)"}])
    print(f"\nTwo plies of 105 µm of the same prepreg are one gap of {d.thickness * 1e6:.0f} µm with k through {d.k_through:.2f} W/mK: the plies matter only through their total pressed thickness and, when their materials differ, through the series formula.")


def main():
    """!
    @brief Print the tables.
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
    print()
    sensitivity()
