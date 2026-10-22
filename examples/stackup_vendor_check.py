"""!
@file stackup_vendor_check.py
@brief How much does the maximum temperature of the example board change between the program's typical stack-ups and the published ones of fabricators?

@details Published layer tables (JLCPCB impedance page, PCBWay stack-up pages, 2026-10-22) are entered layer by layer and the example board is solved with the FVM at 2 mm.
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
    for name, p in [
 ("4L program (= JLC04161H-7628)",tmpl(4)),
 ("4L PCBWay 1 oz inner, core 1030, PP 190",board(4,[35,35,35,35],[190,1030,190])),
 ("4L Weller-like core 930, PP 1080+7628",board(4,[35,15.2,15.2,35],[77+210,930,77+210])),
 ("6L program",tmpl(6)),
 ("6L JLC06161H-3313 exact",board(6,[35,15.2,15.2,15.2,15.2,35],[99.4,550,108.8,550,99.4])),
 ("6L PCBWay old (110/530/110/530/110, 35 um inner)",board(6,[35,35,35,35,35,35],[110,530,110,530,110])),
 ("8L program",tmpl(8)),
 ("8L PCBWay old (175/130 alt., 35 um inner)",board(8,[35]*8,[175,130,175,130,175,130,175])),
]:
        print(f"{name:55s} total {p.board.total_thickness()*1000:.3f} mm  Tmax {t(p):.2f}")


if __name__ == "__main__":
    main()
