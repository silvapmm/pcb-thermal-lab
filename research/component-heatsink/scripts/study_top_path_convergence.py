"""!
@file study_top_path_convergence.py
@brief Does the fixed-point loop of the program's top path (api._solve_with_tc) reach the operating point on every board? The loop against the exact root of the same equation and against the junction-node prototype.

@details The loop solves the board with P_b, reads the hottest board point under the part T_max(P_b), and sets P_b <- P - p_top with
         p_top = (T_max - T_amb + P theta) / (R_top + theta) (analysis.part_split). Linearising T_max - T_amb = R_b P_b, the map is
         P_b <- P - (R_b P_b + P theta) / (R_top + theta), whose slope is -R_b / (R_top + theta): the plain iteration converges only when the
         board's own resistance under the part R_b is smaller than R_top + theta, and slowly when the ratio is close to 1. On a small pad R_b is
         large (100 K/W on an 8 mm pad) and the iteration oscillates and grows.
         The exact operating point is the root of g(P_b) = P_b - P + p_top(P_b), which is monotone in P_b; it is found here by Brent's method with
         the program's own board solve (simulate with no top path, power P_b, computed h), so it is the answer the loop should give with the same
         model and the same worst-case convention. The node prototype (package_prototype.py, uniform conductance under the footprint) is an
         independent network, 1.3 to 3.4 K cooler by its convention (README 4.10).
         Nothing in pcbthermal/ is changed; the measured defect and a proposed correction are in INTEGRATION.md.

Usage: .venv/bin/python research/component-heatsink/scripts/study_top_path_convergence.py   (from the repository root; about 4 minutes)
"""

import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)

from scipy.optimize import brentq                                     # noqa: E402

import component_study as cs                                          # noqa: E402
from pcbthermal import SolverOptions, simulate                        # noqa: E402
from pcbthermal.analysis import part_split                            # noqa: E402

OPTS = SolverOptions(models=("fvm",), cell_mm=0.5)
INTERFACE = 0.5          # K cm2/W, default paste
THETA_SA = 12.0          # K/W, clip-on heatsink


def with_top(part, pad):
    """!
    @brief The board of component_study.py with the part's theta and a top path (theta_JC(top) + default paste + 12 K/W).
    @param part Entry of component_study.PARTS.
    @param pad Pad side in mm.
    @return Problem.
    """
    p = cs.part_board(part, pad)
    h = p.heaters[0]
    h.power, h.theta, h.theta_jc_top, h.interface, h.theta_sa = part["p"], part["th"], part["thtop"], INTERFACE, THETA_SA
    return p


def board_tmax(problem, p_board):
    """!
    @brief Hottest board point under the part when the board receives p_board (no top path, computed h).
    @param problem Problem with a top path (copied, not modified).
    @param p_board Power into the board in W.
    @return Temperature in degC.
    """
    q = copy.deepcopy(problem)
    h = q.heaters[0]
    h.power, h.theta_sa = p_board, 0.0                   # theta_sa = 0 switches the top path (and the loop) off
    return simulate(q, OPTS).heater_rows()[0]["t_max"]


def exact(problem):
    """!
    @brief Operating point of the top path with the program's board model, by Brent's method on P_b.
    @param problem Problem with a top path.
    @return Tuple (Tj in degC, top share, number of board solves).
    """
    h = problem.heaters[0]
    amb, power = problem.board.ambient, h.power
    calls = []

    def g(pb):
        tmax = board_tmax(problem, pb)
        calls.append(1)
        _, p_top = part_split(h, tmax, power, amb)
        return pb - (power - p_top)

    pb = brentq(g, 1e-6 * power, power, xtol=1e-6 * power)
    tmax = board_tmax(problem, pb)
    tj, p_top = part_split(h, tmax, power, amb)
    return tj, p_top / power, len(calls) + 1


def main():
    """!
    @brief Print the table: program loop, exact root and node prototype for the four chips on an 8 mm and a 25 mm pad.
    """
    print(f"Top path theta_JC(top) + {INTERFACE} K cm2/W paste + {THETA_SA:g} K/W heatsink; computed h, FVM at 0.5 mm")
    print("| Part | Pad | R_b / (R_top + theta) | Program Tj [degC] | Program top share | Loop iterations | Settled | Exact Tj [degC] | Exact top share | Program minus exact [K] | Node prototype Tj [degC] |")
    print("| :-- | --: | --: | --: | --: | --: | :-- | --: | --: | --: | --: |")
    for name, part in cs.PARTS.items():
        if name.startswith("Res"):
            continue
        for pad in (8.0, 25.0):
            p = with_top(part, pad)
            h = p.heaters[0]
            r_b = (board_tmax(p, part["p"]) - p.board.ambient) / part["p"]      # Board resistance under the part, secant over the whole power
            ratio = r_b / (h.top_resistance() + h.theta)
            res = simulate(p, OPTS)
            row, r = res.heater_rows()[0], res.results["fvm"]
            settled = not any("did not settle" in w for w in r.warnings)
            tj, share, _ = exact(p)
            node = cs.run(part, pad, top=h.top_resistance())
            print(f"| {name} | {max(pad, part['w'] + 1, part['h'] + 1):g} mm | {ratio:.2f} | {row['t_junction']:.1f} | {100 * row['power_top_w'] / row['power_w']:.0f} % | "
                  f"{r.extras['power_tc_iterations']:.0f} | {'yes' if settled else 'NO'} | {tj:.1f} | {100 * share:.0f} % | {row['t_junction'] - tj:+.1f} | {node['t2']:.1f} |", flush=True)


if __name__ == "__main__":
    main()
