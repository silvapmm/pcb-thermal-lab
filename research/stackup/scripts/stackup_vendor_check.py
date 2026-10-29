#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file stackup_vendor_check.py
@brief How much does the maximum temperature of the example board change between the program's typical stack-ups and the published ones of fabricators?

@details Published layer tables (JLCPCB, PCBWay, OSH Park, AdvancedPCB, Bittele 7pcb and PCBGOGO pages) are entered layer by layer and the example board is solved with the FVM at 2 mm.
         The program's own templates (`pcbthermal/data/stackups.json`) are the reference rows. Results are in `docs/validation.md` section 14 and `research/stackup/README.md` section 4.3.
         The example board keeps its top copper, its bottom plane (moved to the last layer), heaters, vias and heatsink; a second column adds a full plane on every inner layer.

Usage: python research/stackup/scripts/stackup_vendor_check.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import copy
from pcbthermal import simulate, SolverOptions
from pcbthermal.examples import example_board
from pcbthermal.model import Dielectric
def reshape(p, n, planes=False):
    """!
    @brief Reshape the 4-layer example board to n layers: the top copper stays on layer 1, the bottom plane goes to layer n, the heaters and the heatsink follow.
    @details The inner planes of the example (layers 2 and 3) are dropped by default, so that the comparison is of the dielectric split and of the outer copper
             only (the inner copper of the tables then plays no part); with planes=True the full plane is put on every inner layer.
             Before the review the zones were kept only when their layer was 0 or n - 1, which lost the bottom plane (layer index 3) on every board
             with more than four layers: the 6 and 8-layer rows were boards with no bottom copper (about 21 K hotter).
    @param p Example problem (modified in place).
    @param n Number of copper layers.
    @param planes True to put the full plane on every inner layer.
    @return Problem.
    """
    top = [z for z in p.zones if z.layer == 0]
    bottom = [z for z in p.zones if z.layer == 3]                       # "plane L4", the bottom of the example board
    inner = [copy.deepcopy(z) for z in p.zones if z.layer == 1][:1]   # one full plane, copied to every inner layer when asked
    for z in bottom:
        z.layer = n - 1
    zones = top + bottom
    if planes:
        for l in range(1, n - 1):
            z = copy.deepcopy(inner[0]); z.layer = l
            zones.append(z)
    p.zones = zones
    p.board.layers = n
    for h in p.heaters: h.layer = min(h.layer, n - 1)
    for s in p.heatsinks: s.layer = 0 if s.layer == 0 else n - 1
    return p


def board(n, cu, gaps, planes=False):
    """!
    @brief The example board reshaped to n layers with the given copper and dielectric thicknesses.
    @param n Number of copper layers.
    @param cu Copper thickness per layer in micrometres.
    @param gaps Dielectric thickness per gap in micrometres.
    @param planes True to put a full plane on every inner layer (see reshape).
    @return Problem.
    """
    p = reshape(example_board(), n, planes); b = p.board
    b.copper_thickness = [c * 1e-6 for c in cu]
    b.dielectrics = [Dielectric(g * 1e-6) for g in gaps]
    b.thickness = b.total_thickness()
    return p


def t(p):
    """!
    @brief Maximum FVM temperature of a problem.
    @param p Problem.
    @return Temperature in degC.
    """
    return simulate(p,SolverOptions(models=("fvm",),cell_mm=2.0)).results["fvm"].t_max
def tmpl(n, planes=False):
    """!
    @brief The example board with the program's typical stack-up of n layers.
    @param n Number of copper layers.
    @param planes True to put a full plane on every inner layer (see reshape).
    @return Problem.
    """
    p = reshape(example_board(), n, planes)
    p.board.dielectrics = []; p.board.apply_template()
    return p


def main():
    """!
    @brief Print the maximum temperature for every stack-up.
    """
    mil = 25.4                                              # micrometres per mil (thousandth of an inch)
    rows = [
            ("4L program (= JLC04161H-7628)", lambda pl: tmpl(4, pl)),
            ("4L OSH Park (FR408HR, 43.2 / 17.5 um copper, 2113 prepreg 199.9, core 990.6)", lambda pl: board(4, [43.2, 17.5, 17.5, 43.2], [199.9, 990.6, 199.9], pl)),
            ("4L AdvancedPCB sample (1 oz, 2116 x2 per side, core 39 mil)", lambda pl: board(4, [34.3] * 4, [9.3 * mil, 39 * mil, 9.8 * mil], pl)),
            ("4L Bittele 7pcb (1 oz, 2116 x2 0.0091 in, core 0.037 in)", lambda pl: board(4, [35.6] * 4, [9.1 * mil, 37 * mil, 9.1 * mil], pl)),
            ("4L PCBGOGO (18 -> 35 um outer, 1 oz inner, PP 0.11, core 1.2)", lambda pl: board(4, [35] * 4, [110, 1200, 110], pl)),
            ("4L PCBWay (1 oz inner, core 1030, PP 190)", lambda pl: board(4, [35, 35, 35, 35], [190, 1030, 190], pl)),
            ("6L program", lambda pl: tmpl(6, pl)),
            ("6L JLC06161H-3313 exact", lambda pl: board(6, [35, 15.2, 15.2, 15.2, 15.2, 35], [99.4, 550, 108.8, 550, 99.4], pl)),
            ("6L Bittele 7pcb (1 oz; 0.0081 / 0.013 / 0.0091 / 0.013 / 0.0081 in)", lambda pl: board(6, [35.6] * 6, [8.1 * mil, 13 * mil, 9.1 * mil, 13 * mil, 8.1 * mil], pl)),
            ("6L PCBGOGO (PP 0.11, cores 0.6, 1 oz)", lambda pl: board(6, [35] * 6, [110, 600, 110, 600, 110], pl)),
            ("6L PCBWay old blog (110/530/110/530/110)", lambda pl: board(6, [35] * 6, [110, 530, 110, 530, 110], pl)),
            ("8L program", lambda pl: tmpl(8, pl)),
            ("8L Bittele 7pcb (1080x2 / 0.009 / 7628 / 0.0051 / 7628 / 0.009 / 1080x2)",
             lambda pl: board(8, [35.6] * 8, [5.9 * mil, 9 * mil, 7.3 * mil, 5.1 * mil, 7.3 * mil, 9 * mil, 5.9 * mil], pl)),
            ("8L PCBGOGO (PP 0.18, cores 0.2, 1 oz)", lambda pl: board(8, [35] * 8, [180, 200, 180, 200, 180, 200, 180], pl)),
            ("8L PCBWay old blog (175/130 alternating)", lambda pl: board(8, [35] * 8, [175, 130, 175, 130, 175, 130, 175], pl)),
        ]
    # First column: outer copper only (the comparison of the dielectric split); second: a full plane on every inner layer (the inner copper of each table counts)
    print("Tmax in degC; 'Tmax' = top copper and bottom plane only, 'planes' = also a full plane on every inner layer")
    for name, make in rows:
        p = make(False)
        print(f"{name:80s} total {p.board.total_thickness()*1000:.3f} mm  Tmax {t(p):.2f}  planes {t(make(True)):.2f}", flush=True)
    # The outer copper of OSH Park against its dielectrics: which of the two moves the temperature
    print()
    print(f"OSH Park dielectrics with 35 um outer copper (17.5 inner): Tmax {t(board(4, [35, 17.5, 17.5, 35], [199.9, 990.6, 199.9])):.2f}")
    print(f"JLC04161H-7628 dielectrics with 43.2 um outer copper:        Tmax {t(board(4, [43.2, 15.2, 15.2, 43.2], [210.4, 1065, 210.4])):.2f}")


if __name__ == "__main__":
    main()
