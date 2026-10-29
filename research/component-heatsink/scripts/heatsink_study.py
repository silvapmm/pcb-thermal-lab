#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file heatsink_study.py
@brief Heatsinks and thermal interface materials on the parts of component_study.py: a top heatsink with different pastes and pads, and a metal block under the board with different metals and interfaces.

@details Typical interface values (sources in NOTES.md, R2): grease 7 to 20 um bond line at best and 0.05 to 0.1 K cm2/W in the laboratory (Dow Corning), 25 to 100 um and 1 to 5 W/mK in practice;
         gap pads 1 to 6 W/mK and 0.5 to 1.2 mm; the presets below are assumed typical values, always editable.

Usage: python research/component-heatsink/scripts/heatsink_study.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)

import component_study as cs                                          # noqa: E402
from pcbthermal import SolverOptions, simulate                        # noqa: E402

# name: (conductivity W/mK, thickness mm) -> resistance per area t/k in K cm2/W
TIMS = {"good paste (1.5 W/mK apparent, 50 um)": (1.5, 0.05), "paste, typical default (2 W/mK, 100 um)": (2.0, 0.10),
        "soft gap pad (3 W/mK, 0.5 mm)": (3.0, 0.5), "gap pad (1 W/mK, 0.5 mm)": (1.0, 0.5), "hard gap pad (1 W/mK, 1 mm)": (1.0, 1.0)}
# metal: (k W/mK, rho cp J/m3K)
METALS = {"aluminium": (204.0, 2.44e6), "copper": (386.0, 3.45e6), "brass": (111.0, 2.91e6), "carbon steel": (54.0, 3.85e6), "stainless 304": (14.4, 3.69e6)}
AMB = 25.0


def r_area(k, t_mm):
    """!
    @brief Interface resistance per area.
    @param k Conductivity in W/mK.
    @param t_mm Thickness in mm.
    @return Resistance in K cm2/W.
    """
    return t_mm * 1e-3 / k * 1e4


def top_study():
    """!
    @brief Tj with a 12 K/W heatsink on top of the package and different interface materials, junction-node model of package_prototype.py (README 4.3).
    """
    print("E. Heatsink on top of the package (12 K/W), different interface materials (pad 25 mm)")
    print("| Part | no heatsink | " + " | ".join(f"{n} [{r_area(*v):.2f} K cm2/W]" for n, v in TIMS.items()) + " |")
    print("| :-- |" + " --: |" * (1 + len(TIMS)))
    for name, part in cs.PARTS.items():
        if name.startswith("Res"):
            continue
        area_cm2 = part["w"] * part["h"] / 100.0
        base = cs.run(part, 25.0)["t1"]
        cells = []
        for v in TIMS.values():
            r_top = part["thtop"] + r_area(*v) / area_cm2 + 12.0
            r = cs.run(part, 25.0, top=r_top)
            cells.append(f"{r['t2']:.1f} ({100 * r['share']:.0f} %)")
        print(f"| {name} | {base:.1f} | " + " | ".join(cells) + " |", flush=True)


def block_study(part_name="MOSFET CSD17308Q3 (SON 3.3x3.3)"):
    """!
    @brief Tj of one part with a 3 mm metal block (30 x 30 mm) under the board, for every metal and interface (FVM).
    @param part_name Key of component_study.PARTS.
    """
    part = cs.PARTS[part_name]
    print(f"\nF. {part_name}, {part['p']:g} W, 3 mm block 30 x 30 mm under the board: Tj [degC] by metal (rows) and interface (columns); block face in natural convection")
    print("| Metal | no block | " + " | ".join(f"{n} [{r_area(*v):.2f}]" for n, v in TIMS.items()) + " |")
    print("| :-- |" + " --: |" * (1 + len(TIMS)))
    base = cs.run(part, 25.0)["t1"]
    for metal, (k, rc) in METALS.items():
        cells = []
        for v in TIMS.values():
            p = cs.part_board(part, 25.0)
            p.add_heatsink(2, 0.0, rect=(15, 15, 45, 45), thickness_mm=3.0, k=k, rho_cp=rc, contact_r=r_area(*v) * 1e-4, name=metal)
            s = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5))
            t_max = s.results["fvm"].t_max
            cells.append(f"{t_max + part['p'] * part['th']:.1f}")
        print(f"| {metal} | {base:.1f} | " + " | ".join(cells) + " |", flush=True)


if __name__ == "__main__":
    top_study()
    block_study()
