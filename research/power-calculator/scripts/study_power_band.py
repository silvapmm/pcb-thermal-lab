"""!
@file study_power_band.py
@brief What band (best, nominal, worst) does inverse.power_band give on the example of docs/calculators.md section 1.1b, and does it hold the true power when the drawn board really differs?

@details The real board is the example board with U1 at 2 W, theta 6 K/W, psi_JT 2 K/W (as power_from_top_study.py). Part 1 prints the band for a reading at the board ring
         and at the top of the package, with the program's default uncertainties (copper 25 %, heat transfer 30 %, theta 20 %, psi_JT 30 %, reading 1 K): these are the
         numbers of the example table in docs/calculators.md 1.1b. Part 2 draws boards that differ from the real one (the cases of power_from_top_study.py) and says
         whether the true 2 W falls inside the band computed on the drawn board, i.e. whether the band is wide enough for the board errors a designer really makes.

Usage: .venv/bin/python research/power-calculator/scripts/study_power_band.py   (from the repository root; about 2 minutes)
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


def describe(out):
    """!
    @brief One line of the table: nominal, best, worst and what each source moves.
    @param out Result of power_band.
    @return str Markdown cells.
    """
    parts = ", ".join(f"{c['factor']} {c['low_w']:.2f}–{c['high_w']:.2f}" for c in out["contributions"])
    return f"{out['power_w']:.2f} W | {out['best_w']:.2f} W | {out['worst_w']:.2f} W | {parts}"


def main():
    """!
    @brief Print the band table and the coverage table.
    @return None.
    """
    real = top.true_board()
    res = simulate(real, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]
    row = heater_stats(res, real)[0]
    t_ring, t_top = row["t_ring"], row["t_junction"] - top.PSI_JT * top.P_TRUE
    print("Part 1: the band on the drawn board = the real board (default uncertainties of the program)\n")
    print("| Measured at | nominal | best case | worst case | what each source moves (W) |")
    print("| :-- | --: | --: | --: | :-- |")
    print(f"| board ring | {describe(power_band(real, 0, t_ring, point='ring', cell_mm=1.0))} |", flush=True)
    print(f"| top of the package | {describe(power_band(real, 0, t_top, point='top', cell_mm=1.0, psi_jt=top.PSI_JT))} |", flush=True)

    print("\nPart 2: is the true 2 W inside the band computed on a drawn board that differs from the real one? (top of the package)\n")
    print("| Drawn board | nominal (W) | best (W) | worst (W) | 2 W inside |")
    print("| :-- | --: | --: | --: | :-- |")
    cases = {}
    d = copy.deepcopy(real); d.zones[0].fill = 0.5; cases["top copper half filled (hatched)"] = d
    d = copy.deepcopy(real); d.board.copper_thickness = [17.5e-6] * 4; cases["copper 17.5 µm instead of 35 µm"] = d
    d = copy.deepcopy(real); d.vias = []; cases["no vias under the part"] = d
    d = copy.deepcopy(real); d.zones = [d.zones[0]]; cases["no inner planes"] = d
    for label, drawn in cases.items():
        out = power_band(drawn, 0, t_top, point="top", cell_mm=1.0, psi_jt=top.PSI_JT)
        inside = "yes" if out["best_w"] <= top.P_TRUE <= out["worst_w"] else "no"
        print(f"| {label} | {out['power_w']:.3f} | {out['best_w']:.3f} | {out['worst_w']:.3f} | {inside} |", flush=True)


if __name__ == "__main__":
    main()
