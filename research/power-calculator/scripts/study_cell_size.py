#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cell_size.py
@brief Do the datasheet rows of calculator_validation.py depend on the cell size, and how much does the JEDEC row depend on how the test board is read?

@details The rows of README 4.1 are computed at 0.5 mm. This study repeats them at 1, 0.5, 0.35 and 0.25 mm (computed convection and radiation, as the validation):
         the CSD17308Q3 board, the JEDEC 2s2p board with the 9 thermal vias and without them. It then repeats the JEDEC row with the bottom layer read as a
         74.2 x 74.2 mm plane of 70 um (the copper column of ROHM 64AN113E table 2 as its text extracts; JESD51-7 itself was not read), to show how much the
         agreement depends on that reading.

Usage: .venv/bin/python research/power-calculator/scripts/study_cell_size.py   (from the repository root; about 15 minutes)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)

import calculator_validation as cv                                          # noqa: E402

CELLS = (1.0, 0.5, 0.35, 0.25)


def model_theta_ja(board, theta_ja, cell_mm):
    """!
    @brief The model's RθJA on a datasheet board: the datasheet RθJA divided by the power the calculator returns for 1 W.
    @param board Problem.
    @param theta_ja Datasheet RθJA in K/W.
    @param cell_mm Cell size in mm.
    @return float K/W.
    """
    return theta_ja / cv.recovered(board, theta_ja, cell_mm)["power_w"]


def jedec_with_bottom_plane():
    """!
    @brief The JEDEC board of calculator_validation.py with a 74.2 mm plane of 70 um on the bottom layer as well.
    @return Problem.
    """
    p = cv.jedec_2s2p_board()
    cx, cy = 57.15, 38.1
    p.add_zone(4, rect=(cx - 37.1, cy - 37.1, cx + 37.1, cy + 37.1))
    return p


def main():
    """!
    @brief Print the model RθJA of every row at every cell size.
    @return None.
    """
    print("Model RθJA (K/W) against the cell size, computed convection and radiation\n")
    print("| Board | datasheet | " + " | ".join(f"{c:g} mm" for c in CELLS) + " |")
    print("| :-- | --: | " + " | ".join("--:" for _ in CELLS) + " |")
    for label, make, ref in (("CSD17308Q3, 1 in² pad", cv.csd17308q3_board, 46.0),
                             ("JEDEC 2s2p, 9 thermal vias", cv.jedec_2s2p_board, 32.5),
                             ("JEDEC 2s2p, no thermal vias", lambda: cv.jedec_2s2p_board(vias=False), None)):
        vals = [model_theta_ja(make(), 32.5 if ref is None else ref, c) for c in CELLS]
        print(f"| {label} | {'-' if ref is None else f'{ref:g}'} | " + " | ".join(f"{v:.1f}" for v in vals) + " |", flush=True)
    v = model_theta_ja(jedec_with_bottom_plane(), 32.5, 0.5)
    print(f"\nJEDEC 2s2p with 9 vias and a 74.2 mm plane of 70 um on the bottom too, 0.5 mm: model RθJA {v:.1f} K/W "
          f"(calculator error {100 * (32.5 / v - 1):+.1f} %)")


if __name__ == "__main__":
    main()
