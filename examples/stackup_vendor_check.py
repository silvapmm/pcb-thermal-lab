"""!
@file stackup_vendor_check.py
@brief How much does the maximum temperature of the example board change between the program's typical stack-ups and the published ones of fabricators?

@details Published layer tables (JLCPCB, PCBWay, OSH Park, AdvancedPCB, Bittele 7pcb and PCBGOGO pages, 2026-10-22) are entered layer by layer and the example board is solved with the FVM at 2 mm.
         The program's own templates (`pcbthermal/data/stackups.json`) are the reference rows. Results are in `docs/validation.md` section 14.

Usage: python examples/stackup_vendor_check.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import copy
from pcbthermal import simulate, SolverOptions
from pcbthermal.examples import example_board
from pcbthermal.model import Dielectric
def board(n, cu, gaps):
    """!
    @brief The example board reshaped to n layers with the given copper and dielectric thicknesses.
    @param n Number of copper layers.
    @param cu Copper thickness per layer in micrometres.
    @param gaps Dielectric thickness per gap in micrometres.
    @return Problem.
    """
    p = example_board(); b = p.board
    b.layers = n
    # Use the program's own reshaping, then override
    p.zones=[z for z in p.zones if z.layer in (0,n-1)]
    for h in p.heaters: h.layer=min(h.layer,n-1)
    for s in p.heatsinks: s.layer=0 if s.layer==0 else n-1
    b.copper_thickness=[c*1e-6 for c in cu]
    b.dielectrics=[Dielectric(g*1e-6) for g in gaps]
    b.thickness=b.total_thickness()
    return p
def t(p):
    """!
    @brief Maximum FVM temperature of a problem.
    @param p Problem.
    @return Temperature in degC.
    """
    return simulate(p,SolverOptions(models=("fvm",),cell_mm=2.0)).results["fvm"].t_max
def tmpl(n):
    """!
    @brief The example board with the program's typical stack-up of n layers.
    @param n Number of copper layers.
    @return Problem.
    """
    p=example_board(); p.board.layers=n; p.zones=[z for z in p.zones if z.layer in (0,n-1)]
    for h in p.heaters: h.layer=min(h.layer,n-1)
    for s in p.heatsinks: s.layer=0 if s.layer==0 else n-1
    p.board.dielectrics=[]; p.board.apply_template()
    return p
def main():
    """!
    @brief Print the maximum temperature for every stack-up.
    """
    mil = 25.4                                              # micrometres per mil (thousandth of an inch)
    for name, p in [
            ("4L program (= JLC04161H-7628)", tmpl(4)),
            ("4L OSH Park (FR408HR, 43.2 / 17.5 um copper, 2113 prepreg 199.9, core 990.6)", board(4, [43.2, 17.5, 17.5, 43.2], [199.9, 990.6, 199.9])),
            ("4L AdvancedPCB sample (1 oz, 2116 x2 per side, core 39 mil)", board(4, [34.3] * 4, [9.3 * mil, 39 * mil, 9.8 * mil])),
            ("4L Bittele 7pcb (1 oz, 2116 x2 0.0091 in, core 0.037 in)", board(4, [35.6] * 4, [9.1 * mil, 37 * mil, 9.1 * mil])),
            ("4L PCBGOGO (18 -> 35 um outer, 1 oz inner, PP 0.11, core 1.2)", board(4, [35] * 4, [110, 1200, 110])),
            ("4L PCBWay (1 oz inner, core 1030, PP 190)", board(4, [35, 35, 35, 35], [190, 1030, 190])),
            ("6L program", tmpl(6)),
            ("6L JLC06161H-3313 exact", board(6, [35, 15.2, 15.2, 15.2, 15.2, 35], [99.4, 550, 108.8, 550, 99.4])),
            ("6L Bittele 7pcb (1 oz; 0.0081 / 0.013 / 0.0091 / 0.013 / 0.0081 in)", board(6, [35.6] * 6, [8.1 * mil, 13 * mil, 9.1 * mil, 13 * mil, 8.1 * mil])),
            ("6L PCBGOGO (PP 0.11, cores 0.6, 1 oz)", board(6, [35] * 6, [110, 600, 110, 600, 110])),
            ("6L PCBWay old blog (110/530/110/530/110)", board(6, [35] * 6, [110, 530, 110, 530, 110])),
            ("8L program", tmpl(8)),
            ("8L Bittele 7pcb (1080x2 / 0.009 / 7628 / 0.0051 / 7628 / 0.009 / 1080x2)",
             board(8, [35.6] * 8, [5.9 * mil, 9 * mil, 7.3 * mil, 5.1 * mil, 7.3 * mil, 9 * mil, 5.9 * mil])),
            ("8L PCBGOGO (PP 0.18, cores 0.2, 1 oz)", board(8, [35] * 8, [180, 200, 180, 200, 180, 200, 180])),
            ("8L PCBWay old blog (175/130 alternating)", board(8, [35] * 8, [175, 130, 175, 130, 175, 130, 175])),
        ]:
        print(f"{name:80s} total {p.board.total_thickness()*1000:.3f} mm  Tmax {t(p):.2f}")


if __name__ == "__main__":
    main()
