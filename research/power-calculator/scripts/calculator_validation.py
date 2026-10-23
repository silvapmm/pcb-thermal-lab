"""!
@file calculator_validation.py
@brief Validation of the power calculator against datasheets: the datasheet's own board, built in the program, must give the datasheet's thermal resistance.

@details A datasheet gives RθJA for a stated board, so on that board the calculator must return the power that produced a junction temperature Tj = Ta + RθJA·P.
         Two cases:
         (1) **TI CSD17308Q3** (SON 3.3 x 3.3 mm power MOSFET): 38.1 x 38.1 mm (1.5 in), 1.52 mm FR-4, 2 oz (71 µm) copper, a 1 in² copper pad on the top, still air.
             Datasheet: RθJC 4.5 K/W (junction to the drain pad), RθJA typical 46 and maximum 58 K/W.
         (2) **A JEDEC JESD51-7 2s2p board with an exposed-pad QFN** (TI TPS7A47-like, the package data are assumed: 5 x 5 mm body, exposed pad 3.15 mm, 9 thermal vias of 0.3 mm at
             1.2 mm pitch under it as in JESD51-5, θJC(bot) 1.7 K/W). Board of ROHM application note 64AN113E (JESD51-3/5/7/9/10): 114.3 x 76.2 x 1.6 mm, 70 µm top and bottom
             traces, two 74.2 x 74.2 mm planes of 35 µm; the bottom and top traces are not drawn (a few percent of copper). Datasheet RθJA 32.5 K/W.
         The heat transfer coefficients are computed (natural convection and radiation, horizontal board).

Usage: python research/power-calculator/scripts/calculator_validation.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pcbthermal import Problem                                            # noqa: E402
from pcbthermal.inverse import power_from_temperature                     # noqa: E402


def csd17308q3_board(pad_mm=25.4):
    """!
    @brief The datasheet test board of the TI CSD17308Q3 with the part as a heater of its 3.3 mm footprint.
    @param pad_mm Side of the square copper pad in mm (25.4 mm is 1 in²).
    @return Problem (computed heat transfer coefficients).
    """
    p = Problem.new(38.1, 38.1, 2)
    b = p.board
    b.thickness, b.copper_thickness, b.h_side, b.h_mode = 1.52e-3, [71e-6, 71e-6], None, "computed"
    c = 19.05
    p.add_zone(1, rect=(c - pad_mm / 2, c - pad_mm / 2, c + pad_mm / 2, c + pad_mm / 2))
    p.add_heater(1, 1.0, rect=(c - 1.65, c - 1.65, c + 1.65, c + 1.65), name="Q1", theta=4.5)
    return p


def jedec_2s2p_board(vias=True, theta=1.7, pad_mm=3.15):
    """!
    @brief A JESD51-7 2s2p board with an exposed-pad package at its centre (assumed package, see the module description).
    @param vias True for the 3 x 3 thermal vias of the JESD51-5 pattern under the pad.
    @param theta Junction-to-pad (bottom) resistance in K/W.
    @param pad_mm Side of the exposed pad in mm.
    @return Problem (computed heat transfer coefficients).
    """
    p = Problem.new(114.3, 76.2, 4)
    b = p.board
    b.thickness, b.copper_thickness, b.h_side, b.h_mode = 1.6e-3, [70e-6, 35e-6, 35e-6, 70e-6], None, "computed"
    cx, cy = 57.15, 38.1
    for layer in (2, 3):
        p.add_zone(layer, rect=(cx - 37.1, cy - 37.1, cx + 37.1, cy + 37.1))
    p.add_zone(1, rect=(cx - pad_mm / 2 - 0.5, cy - pad_mm / 2 - 0.5, cx + pad_mm / 2 + 0.5, cy + pad_mm / 2 + 0.5))      # The land of the pad
    p.add_heater(1, 1.0, rect=(cx - pad_mm / 2, cy - pad_mm / 2, cx + pad_mm / 2, cy + pad_mm / 2), name="U1", theta=theta)
    if vias:
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                p.add_via(cx + 1.2 * i, cy + 1.2 * j, 0.3)
    return p


def recovered(board, theta_ja, cell_mm, power=1.0, point="junction", psi_jt=0.0):
    """!
    @brief Power the calculator returns when the part dissipates `power` and the datasheet's RθJA is exact.
    @param board Problem of the datasheet board.
    @param theta_ja Datasheet RθJA in K/W.
    @param cell_mm Cell size in mm.
    @param power True power in W.
    @param point Measurement point of the calculator.
    @param psi_jt Datasheet ψJT in K/W for the point "top".
    @return Dict from power_from_temperature.
    """
    amb = board.board.ambient
    tj = amb + theta_ja * power
    measured = tj - psi_jt * power if point == "top" else tj
    return power_from_temperature(board, 0, measured, point=point, cell_mm=cell_mm, psi_jt=psi_jt)


def main():
    """!
    @brief Print the validation table.
    """
    rows = (("TI CSD17308Q3, 1 in² 2 oz pad, RθJA typical 46 K/W", csd17308q3_board(), 46.0, 0.5, "junction", 0.0),
            ("TI CSD17308Q3, same board, RθJA maximum 58 K/W (a limit, not a typical)", csd17308q3_board(), 58.0, 0.5, "junction", 0.0),
            ("JEDEC 2s2p, exposed-pad QFN with 9 vias (TPS7A47-like), RθJA 32.5 K/W", jedec_2s2p_board(), 32.5, 0.5, "junction", 0.0),
            ("the same, measured on the top with ψJT 0.3 K/W (TPS7A47)", jedec_2s2p_board(), 32.5, 0.5, "top", 0.3))
    print("| Case | datasheet RθJA (K/W) | model RθJA (K/W) | power the calculator returns for 1 W | error |")
    print("| :-- | --: | --: | --: | --: |")
    for label, board, theta_ja, cell, point, psi in rows:
        out = recovered(board, theta_ja, cell, point=point, psi_jt=psi)
        model_theta = theta_ja / out["power_w"]
        print(f"| {label} | {theta_ja:g} | {model_theta:.1f} | {out['power_w']:.3f} W | {100 * (out['power_w'] - 1.0):+.1f} % |", flush=True)


if __name__ == "__main__":
    main()
