#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_inner_copper_1oz.py
@brief How much hotter is the example board with the program's 0.5 oz (15.2 um) inner copper than with 1 oz (35 um) inner copper, for every typical stack-up template?

@details Question (maintainer, in the review): the templates of `pcbthermal/data/stackups.json` use 15.2 um inner copper, most published fabricator tables
         use 1 oz (about 35 um); with a full plane on every inner layer that is 5 to 8 K. This study repeats the templates of 2, 4, 6, 8, 10 and 12 layers with
         the inner copper changed and compares the maximum temperature, with the board built as in `stackup_vendor_check.py` (top copper on layer 1, the bottom
         plane of the example on the LAST layer, heaters, vias and heatsink, a full plane on every inner layer).
         Variants of the inner copper (outer copper stays 35 um):
         * as shipped: 15.2 um;
         * 35 um, dielectrics unchanged: the board gets thicker by (35 - 15.2) um per inner layer;
         * 35 um, same total thickness: every dielectric is scaled by one factor so that copper + dielectrics add up to the shipped total
           (the extra copper is taken out of the resin, prepreg and core thinned in proportion);
         * 17.5 um (a true 0.5 oz base foil, dielectrics unchanged).
         The FVM (2 mm) is run for every row; the 3D solid (2 mm) is run for the 4 and 6-layer templates only (it takes minutes on the thicker boards).
         Results are in `research/stackup/README.md` section 4.5.

Usage: python research/stackup/scripts/study_inner_copper_1oz.py [--no-3d]   (from the repository root; about 1 minute with --no-3d, about 3 minutes with the 3D solid)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pcbthermal import simulate, SolverOptions
from pcbthermal.examples import example_board
from stackup_vendor_check import reshape

LAYERS = (2, 4, 6, 8, 10, 12)
SOLID_LAYERS = (4, 6)            # layer counts for which the 3D solid is run (time)


def template_board(n):
    """!
    @brief The example board reshaped to n layers, with the program's template and a full plane on every inner layer.
    @param n Number of copper layers.
    @return Problem.
    """
    p = reshape(example_board(), n, planes=True)
    p.board.dielectrics = []
    p.board.apply_template()
    return p


def variant(n, inner_um, keep_thickness):
    """!
    @brief The template board with another inner copper thickness.
    @param n Number of copper layers.
    @param inner_um Inner copper thickness in micrometres (the outer layers keep 35 um).
    @param keep_thickness True to scale every dielectric by one factor so that the total board thickness stays the shipped one; False to leave the dielectrics unchanged.
    @return Problem.
    """
    p = template_board(n)
    b = p.board
    total0 = b.total_thickness()                                   # shipped total thickness in m
    for l in range(1, n - 1):
        b.copper_thickness[l] = inner_um * 1e-6
    if keep_thickness and b.dielectrics:
        cu = sum(b.copper_thickness)
        di = sum(d.thickness for d in b.dielectrics)
        f = (total0 - cu) / di                                     # the resin takes up the extra copper
        for d in b.dielectrics:
            d.thickness *= f
    b.thickness = b.total_thickness()
    return p


def tmax(p, model):
    """!
    @brief Maximum temperature of one model.
    @param p Problem.
    @param model Model key, "fvm" or "solid3d".
    @return float Temperature in degC.
    """
    return simulate(p, SolverOptions(models=(model,), cell_mm=2.0)).results[model].t_max


def main():
    """!
    @brief Print the table of the maximum temperature for every template and inner copper variant.
    @return None.
    """
    with_3d = "--no-3d" not in sys.argv
    amb = example_board().board.ambient
    variants = [("shipped 15.2", 15.2, False), ("35, dielectrics unchanged", 35.0, False),
                ("35, same thickness", 35.0, True), ("17.5, dielectrics unchanged", 17.5, False)]
    for model in ("fvm",) + (("solid3d",) if with_3d else ()):
        print(f"\nModel {model}: Tmax in degC (ambient {amb:.0f}), difference to the shipped template in K and in % of its rise")
        print("| Layers | Variant | Total (mm) | Tmax (degC) | Difference (K) | Difference (% of the rise) |")
        print("| :-- | :-- | --: | --: | --: | --: |")
        for n in LAYERS:
            if model == "solid3d" and n not in SOLID_LAYERS:
                continue
            ref = None
            for name, um, keep in variants:
                if n == 2 and um != 15.2:
                    continue                                       # a 2-layer board has no inner copper: nothing to change
                p = variant(n, um, keep)
                t = tmax(p, model)
                if ref is None:
                    ref = t
                print(f"| {n} | {name} | {p.board.total_thickness()*1000:.3f} | {t:.2f} | {t-ref:+.2f} | {100*(t-ref)/(ref-amb):+.1f} |", flush=True)


if __name__ == "__main__":
    main()
