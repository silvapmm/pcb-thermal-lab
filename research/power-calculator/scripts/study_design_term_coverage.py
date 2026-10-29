#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_design_term_coverage.py
@brief Does the design-uncertainty term of inverse.power_band bring the true power inside the band when the drawn board differs from the real one?

@details This is the script behind the coverage table of docs/calculators.md section 1.1c. The real board is the example board with U1 at 2 W, theta 6 K/W, psi_JT 2 K/W
         (as power_from_top_study.py); its top-of-package temperature is "measured" on it, and the power is recovered on four drawn boards that differ from it (top copper half
         filled, copper 17.5 um instead of 35 um, no vias, no inner planes) with inverse.power_band at the design levels none (numbers only, the band before the design term),
         cad (drawn from the fabrication files), hand (the program default) and estimated. Every cell is the band worst/best case and whether the true 2 W falls inside it.
         A last block prints the example of docs/calculators.md 1.1b/1.1c (drawn board = real board) at the board ring and at the top at every level.
         Each band costs several tens of board solves at 1 mm cells.

Usage: .venv/bin/python research/power-calculator/scripts/study_design_term_coverage.py [levels]   (from the repository root; levels is a comma list, default none,cad,hand,estimated;
       about 10 minutes for the four levels)
"""

import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)

import power_from_top_study as top                                          # noqa: E402
from pcbthermal import SolverOptions, simulate                              # noqa: E402
from pcbthermal.analysis import heater_stats                                # noqa: E402
from pcbthermal.inverse import power_band                                   # noqa: E402


def drawn_boards(real):
    """!
    @brief The four wrongly drawn boards of power_from_top_study.py (part 2 of study_power_band.py).
    @param real Problem, the real board.
    @return dict Label -> Problem.
    """
    cases = {}
    d = copy.deepcopy(real); d.zones[0].fill = 0.5; cases["top copper half filled (hatched)"] = d
    d = copy.deepcopy(real); d.board.copper_thickness = [17.5e-6] * 4; cases["copper 17.5 µm instead of 35 µm"] = d
    d = copy.deepcopy(real); d.vias = []; cases["no vias under the part"] = d
    d = copy.deepcopy(real); d.zones = [d.zones[0]]; cases["no inner planes"] = d
    return cases


def main():
    """!
    @brief Print the coverage table and the example band at every level.
    @return None.
    """
    levels = (sys.argv[1] if len(sys.argv) > 1 else "none,cad,hand,estimated").split(",")
    real = top.true_board()
    res = simulate(real, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]
    row = heater_stats(res, real)[0]
    t_ring, t_top = row["t_ring"], row["t_junction"] - top.PSI_JT * top.P_TRUE
    print("Coverage of the true 2 W by the band, power recovered at the top of the package (best-worst W, in/OUT)\n")
    print("| Drawn board | nominal | " + " | ".join(levels) + " |")
    print("| :-- | --: | " + " | ".join(":--" for _ in levels) + " |")
    for label, drawn in drawn_boards(real).items():
        cells, nominal = [], None
        for lv in levels:
            out = power_band(drawn, 0, t_top, point="top", cell_mm=1.0, psi_jt=top.PSI_JT, uncertainty={"design_level": lv})
            nominal = out["power_w"]
            cells.append(f"{out['best_w']:.3f}–{out['worst_w']:.3f} {'in' if out['best_w'] <= top.P_TRUE <= out['worst_w'] else 'OUT'}")
        print(f"| {label} | {nominal:.3f} | " + " | ".join(cells) + " |", flush=True)
    print("\nThe example (drawn board = real board): nominal / best / worst in W\n")
    print("| Measured at | " + " | ".join(levels) + " |")
    print("| :-- | " + " | ".join(":--" for _ in levels) + " |")
    for point, kw, t in (("ring", {}, t_ring), ("top", {"psi_jt": top.PSI_JT}, t_top)):
        cells = []
        for lv in levels:
            out = power_band(real, 0, t, point=point, cell_mm=1.0, uncertainty={"design_level": lv}, **kw)
            cells.append(f"{out['power_w']:.2f} / {out['best_w']:.2f} / {out['worst_w']:.2f}")
        print(f"| {point} | " + " | ".join(cells) + " |", flush=True)


if __name__ == "__main__":
    main()
