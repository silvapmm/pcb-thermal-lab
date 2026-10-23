"""!
@file power_from_top_study.py
@brief How well can the power of a part be found from a temperature measured on top of its package, and how much does it depend on the board?

@details The "measurement" is made on a known board: the example board with U1 dissipating 2 W, theta = 6 K/W and psi_JT = 2 K/W, so the top of the package reads
         T_top = T_board,max + (theta - psi_JT) P above ambient. The power is then recovered with `inverse.power_from_temperature(point="top")` on boards that differ from the
         real one by what a designer really does not know: the copper of the top layer, its thickness, the inner planes, the vias, the heat transfer coefficients, and by what a
         measurement gets wrong: the temperature itself (a thermocouple or an infrared emissivity error) and the datasheet parameters theta and psi_JT. The datasheet shortcut
         P = (T_top - T_amb) / (theta_JA - psi_JT) is shown for a theta_JA that is 30 % off the real board (a JEDEC board is not your board).
         Error = recovered power / 2 W - 1.

Usage: python research/power-calculator/power_from_top_study.py
"""

import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pcbthermal import SolverOptions, simulate                            # noqa: E402
from pcbthermal.examples import example_board                             # noqa: E402
from pcbthermal.inverse import power_from_temperature                     # noqa: E402

P_TRUE, THETA, PSI_JT = 2.0, 6.0, 2.0


def true_board():
    """!
    @brief The real board: the example with U1 at 2 W and U2 off.
    @return Problem.
    """
    p = example_board()
    p.heaters[0].power, p.heaters[0].theta = P_TRUE, THETA
    p.heaters[1].power = 0.0
    p.heaters[1].theta = 0.0
    return p


def recovered(drawn, t_top, psi=PSI_JT):
    """!
    @brief Power found from the top temperature on a drawn board.
    @param drawn Problem the designer believes is the real one.
    @param t_top Measured temperature of the top of the package in degC.
    @param psi psi_JT used, K/W.
    @return Power in watts.
    """
    return power_from_temperature(drawn, 0, t_top, point="top", cell_mm=1.0, psi_jt=psi)["power_w"]


def main():
    """!
    @brief Print the table of recovered powers.
    """
    real = true_board()
    res = simulate(real, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]
    from pcbthermal.analysis import heater_stats
    row = heater_stats(res, real)[0]
    t_top = row["t_junction"] - PSI_JT * P_TRUE
    theta_ja = (row["t_junction"] - real.board.ambient) / P_TRUE
    print(f"Real board: U1 {P_TRUE} W, theta {THETA} K/W, psi_JT {PSI_JT} K/W: Tj {row['t_junction']:.1f} degC, top {t_top:.1f} degC, "
          f"theta_JA of this board {theta_ja:.1f} K/W\n")
    print("| What is different between the drawn board and the real one | recovered power (W) | error |")
    print("| :-- | --: | --: |")

    def line(label, p_found):
        print(f"| {label} | {p_found:.3f} | {100 * (p_found / P_TRUE - 1):+.1f} % |", flush=True)

    line("nothing (the drawn board is the real one)", recovered(real, t_top))
    cases = {}
    d = copy.deepcopy(real); d.zones[0].fill = 0.5; cases["top copper half filled (hatched)"] = d
    d = copy.deepcopy(real); d.board.copper_thickness = [17.5e-6] * 4; cases["copper 17.5 µm instead of 35 µm on every layer"] = d
    d = copy.deepcopy(real); d.zones = [d.zones[0]]; cases["no inner planes (only the top copper)"] = d
    d = copy.deepcopy(real); d.zones = d.zones[1:]; cases["no top copper pad (inner planes only)"] = d
    d = copy.deepcopy(real); d.vias = []; cases["no vias under the part"] = d
    d = copy.deepcopy(real); d.board.h_top *= 1.3; d.board.h_bottom *= 1.3; cases["heat transfer coefficients +30 %"] = d
    d = copy.deepcopy(real); d.board.h_top *= 0.7; d.board.h_bottom *= 0.7; cases["heat transfer coefficients -30 %"] = d
    d = copy.deepcopy(real); d.heaters[0].theta = THETA * 1.2; cases["theta +20 % (datasheet number)"] = d
    d = copy.deepcopy(real); d.heaters[0].theta = THETA * 0.8; cases["theta -20 %"] = d
    for label, drawn in cases.items():
        line(label, recovered(drawn, t_top))
    line("psi_JT 1 K/W instead of 2 (datasheet board is not yours)", recovered(real, t_top, 1.0))
    line("psi_JT 3 K/W instead of 2", recovered(real, t_top, 3.0))
    line("measured top temperature 3 K too low (IR emissivity or probe)", recovered(real, t_top - 3.0))
    line("measured top temperature 3 K too high", recovered(real, t_top + 3.0))
    amb = real.board.ambient
    for f in (0.7, 1.3):
        line(f"datasheet shortcut P = (T_top - T_amb)/(theta_JA - psi_JT) with theta_JA {int((f - 1) * 100):+d} % off", (t_top - amb) / (f * theta_ja - PSI_JT))


if __name__ == "__main__":
    main()
