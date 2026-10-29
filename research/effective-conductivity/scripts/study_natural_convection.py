#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_natural_convection.py
@brief The natural convection of a vertical plate in the program (Churchill and Chu, general form) against the laminar form of the same paper, over the Rayleigh numbers of a board, and the effect on h.
@details The program uses the general correlation Nu = (0.825 + 0.387 Ra^(1/6) / [1 + (0.492/Pr)^(9/16)]^(8/27))^2 for the whole range. The same authors give, for Ra below 1e9, a laminar form
         Nu = 0.68 + 0.670 Ra^(1/4) / [1 + (0.492/Pr)^(9/16)]^(4/9) that textbooks recommend for laminar flow. Neither paper was opened (see the bibliography); both forms are taken from the
         formulas quoted in the compilation of sources and reproduced here, and the general form is checked against the worked example of the `ht` library (Pr = 0.69, Grashof number 2.63e9, so Ra = Gr Pr = 1.815e9: Nu = 147.16; the library takes the Grashof number as its argument).
         The study compares the two forms over Ra, and shows what the choice does to h_top of a vertical board of 50, 100 and 200 mm height at temperature rises of 10 to 80 K, using the air
         properties of the program. Run: .venv/bin/python research/effective-conductivity/scripts/study_natural_convection.py (from the repository root; a few seconds).
"""

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from pcbthermal import convection as cv                        # noqa: E402


def nu_general(ra, pr):
    """!
    @brief General Churchill and Chu correlation for an isothermal vertical plate.
    @param ra Rayleigh number.
    @param pr Prandtl number.
    @return float Mean Nusselt number.
    """
    return (0.825 + 0.387 * ra ** (1.0 / 6.0) / (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (8.0 / 27.0)) ** 2


def nu_laminar(ra, pr):
    """!
    @brief Laminar form of Churchill and Chu (Ra below 1e9).
    @param ra Rayleigh number.
    @param pr Prandtl number.
    @return float Mean Nusselt number.
    """
    return 0.68 + 0.670 * ra ** 0.25 / (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (4.0 / 9.0)


def main():
    """!
    @brief Print the tables and write out/natural_convection.json for the figures.
    @return None.
    """
    out = {"example": nu_general(2.63e9 * 0.69, 0.69)}
    print(f"Worked example of the library `ht` (Pr 0.69, Grashof 2.63e9, Ra = Gr Pr): general form gives {out['example']:.2f} (library: 147.16)")
    ras = np.logspace(3, 12, 37)
    out["ratio"] = [(float(r), float(nu_laminar(r, 0.71) / nu_general(r, 0.71) - 1.0)) for r in ras]
    print("\n| Ra | laminar form / general form - 1 (Pr 0.71) |")
    print("| --: | --: |")
    for r in (1e4, 1e5, 1e6, 1e7, 1e8, 1e9):
        print(f"| {r:.0e} | {100 * (nu_laminar(r, 0.71) / nu_general(r, 0.71) - 1):+.1f} % |")
    print("\n| board height (mm) | rise (K) | Ra | h general (program) | h laminar | difference |")
    print("| --: | --: | --: | --: | --: | --: |")
    rows = []
    for height in (0.05, 0.1, 0.2):
        for dt in (10.0, 30.0, 60.0, 80.0):
            ta = 25.0
            h_prog, ra = cv.h_natural_vertical(ta + dt, ta, height)
            props = cv.air_properties(ta + dt / 2)
            h_lam = nu_laminar(ra, props["pr"]) * props["k"] / height
            rows.append({"height_mm": height * 1e3, "dt": dt, "ra": ra, "h_general": h_prog, "h_laminar": h_lam})
            print(f"| {height * 1e3:g} | {dt:g} | {ra:.2g} | {h_prog:.2f} | {h_lam:.2f} | {100 * (h_lam / h_prog - 1):+.1f} % |")
    out["h"] = rows
    (HERE.parent / "out").mkdir(exist_ok=True)
    (HERE.parent / "out" / "natural_convection.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
