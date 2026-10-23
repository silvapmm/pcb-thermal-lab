"""!
@file top_path_study.py
@brief The top path of a part (junction-to-case, interface and heatsink on the package) in the program against the junction-node prototype, on the four chips of component_study.py.

@details The program splits the power with a fixed-point loop around any model (analysis.part_split): Tj = T_max under the footprint + P_board theta, P_board = P - (Tj - T_amb) / R_top.
         The prototype (package_prototype.py) joins a junction node to the footprint cells with a uniform conductance 1/theta, which is about 3 K below the worst-case convention without a heatsink.

Usage: python research/component-heatsink/top_path_study.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

import component_study as cs                                          # noqa: E402
from pcbthermal import SolverOptions, simulate                        # noqa: E402

THETA_SA = 12.0          # K/W, clip-on heatsink on top of the package
INTERFACE = 0.5          # K cm2/W, default paste


def main():
    """!
    @brief Print the table: Tj of the program (worst-case convention) and of the node prototype with the same top path, and the heat taken by the top.
    """
    print(f"Top path: theta_JC(top) of the part + {INTERFACE} K cm2/W paste + {THETA_SA} K/W heatsink; pad 25 mm, computed h, FVM at 0.5 mm")
    print("| Part | Tj without top path | Tj program | Top share program | Tj node prototype | Top share prototype |")
    print("| :-- | --: | --: | --: | --: | --: |")
    for name, part in cs.PARTS.items():
        if name.startswith("Res"):
            continue
        p = cs.part_board(part, 25.0)
        h = p.heaters[0]
        h.power, h.theta = part["p"], part["th"]
        base = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5)).heater_rows()[0]["t_junction"]
        h.theta_jc_top, h.interface, h.theta_sa = part["thtop"], INTERFACE, THETA_SA
        row = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5)).heater_rows()[0]
        area_cm2 = part["w"] * part["h"] / 100.0
        node = cs.run(part, 25.0, top=part["thtop"] + INTERFACE / area_cm2 + THETA_SA)
        print(f"| {name} | {base:.1f} | {row['t_junction']:.1f} | {100 * row['power_top_w'] / row['power_w']:.0f} % | "
              f"{node['t2']:.1f} | {100 * node['share']:.0f} % |", flush=True)


if __name__ == "__main__":
    main()
