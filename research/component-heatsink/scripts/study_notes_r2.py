#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_notes_r2.py
@brief Reproduce the two sets of numbers of NOTES.md R2 that no other script printed: the metal block with fins (metals and thickness) and the "perfect contact" table.

@details Question: how much do the block metal and thickness matter when the block has fins (extra h 60 W/m2K on its face), and below which interface
         resistance per area R'' does a contact count as perfect (change of Tj smaller than 0.05 K)?
         Part: MOSFET CSD17308Q3 (2 W, 3.3 x 3.3 mm), 25 mm pads, 60 x 60 mm board; block 30 x 30 mm under the board.
         A: block with fins (FVM, computed h; Tj = T_max under the footprint + P * theta), by metal at 6 mm and by thickness in aluminium, default paste 0.5 K cm2/W.
         B: the same without fins (the 98 degC of R2), for comparison.
         C: Tj change against R'' = 0 for the top heatsink chain (12 K/W + theta_JC(top) + R''/A, junction node of chain_study.py) and for the block under the board
            (3 mm aluminium, same junction node, board faces at constant h).
         Results are printed only; compare with NOTES.md R2.

Usage: python research/component-heatsink/scripts/study_notes_r2.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)

import component_study as cs                                          # noqa: E402
import chain_study as ch                                              # noqa: E402
import heatsink_study as hs                                           # noqa: E402
from pcbthermal import SolverOptions, simulate                        # noqa: E402

PART = cs.PARTS["MOSFET CSD17308Q3 (SON 3.3x3.3)"]
FIN_H = 60.0                                                          # Extra coefficient of the finned block face in W/m2K
R_VALUES = (0.0, 0.001, 0.01, 0.03, 0.1, 0.3, 0.5, 1.0, 5.0)         # Interface resistances per area in K cm2/W


def block_tj(metal, thickness_mm, r_kcm2w=0.5, h_extra=0.0):
    """!
    @brief Tj of the MOSFET with a 30 x 30 mm block under the board.
    @param metal Key of heatsink_study.METALS.
    @param thickness_mm Block thickness in mm.
    @param r_kcm2w Interface resistance per area in K cm2/W.
    @param h_extra Extra heat transfer coefficient of the block face in W/m2K (fins).
    @return Junction temperature in degC.
    """
    k, rc = hs.METALS[metal]
    p = cs.part_board(PART, 25.0)
    # Same rectangle as heatsink_study.block_study (30 x 30 mm centred on the 60 mm board)
    p.add_heatsink(2, h_extra, rect=(15, 15, 45, 45), thickness_mm=thickness_mm, k=k, rho_cp=rc, contact_r=r_kcm2w * 1e-4, name=metal)
    s = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5))
    return s.results["fvm"].t_max + PART["p"] * PART["th"]


def part_a_b():
    """!
    @brief Print the fin and thickness numbers (with and without fins).
    """
    base = cs.run(PART, 25.0)["t1"]
    print(f"Bare board, MOSFET 2 W, pad 25 mm: Tj = {base:.1f} degC")
    for label, hx in (("with fins (extra h 60 W/m2K)", FIN_H), ("no fins", 0.0)):
        print(f"\nBlock 30 x 30 mm, paste 0.5 K cm2/W, {label}")
        print("| Metal (6 mm) | Tj [degC] |\n| :-- | --: |")
        for m in hs.METALS:
            print(f"| {m} | {block_tj(m, 6.0, 0.5, hx):.1f} |", flush=True)
        print("| Aluminium thickness [mm] | Tj [degC] |\n| :-- | --: |")
        for t in (1.0, 3.0, 6.0):
            print(f"| {t:g} | {block_tj('aluminium', t, 0.5, hx):.1f} |", flush=True)


def part_c():
    """!
    @brief Print the Tj change against R'' = 0 for the top chain and for the block under the board.
    """
    h = cs.run(PART, 25.0)["h"]
    area_cm2 = PART["w"] * PART["h"] / 100.0
    top0 = ch.chain(PART, h, PART["th"], PART["thtop"] + 12.0)["tj"]
    blk0 = ch.chain(PART, h, PART["th"], None, (3.0, 0.0, 30.0))["tj"]
    print(f"\nPerfect contact (R'' = 0): top chain Tj = {top0:.2f}, block Tj = {blk0:.2f} degC (constant h = {h[0]:.1f} / {h[1]:.1f})")
    print("| R'' [K cm2/W] | Top chain: dTj | Block under the board: dTj |\n| --: | --: | --: |")
    for r in R_VALUES[1:]:
        top = ch.chain(PART, h, PART["th"], PART["thtop"] + r / area_cm2 + 12.0)["tj"] - top0
        blk = ch.chain(PART, h, PART["th"], None, (3.0, r, 30.0))["tj"] - blk0
        print(f"| {r:g} | {top:+.2f} | {blk:+.2f} |", flush=True)


if __name__ == "__main__":
    part_a_b()
    part_c()
