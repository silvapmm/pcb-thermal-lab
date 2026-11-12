#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_solid_harness.py
@brief How much would the slab rule of item C (n = clip(ceil(d / 0.2 mm), 4, 16) slabs per gap; here the uniform n of the thickest gap) move the 3D solid on the boards of the frozen-numbers harness?
@details Boards of tests/regression/regress_boards.py, 3D solid at 2 mm with n_diel = 4 (the program) and with the rule's number for the thickest gap; hottest temperature and unknowns. Boards
         with metal blocks are run too (the solid supports them). Run (repository root, light): .venv/bin/python research/laminate-slabs-and-local-rule/scripts/study_solid_harness.py
"""

import sys

import _boot26

sys.path.insert(0, str(_boot26.REPO / "tests" / "regression"))
import regress_boards as RB                                    # noqa: E402
from study_solid_slices import rule_slabs                       # noqa: E402


def main():
    """!
    @brief Print the table.
    @return None
    """
    from pcbthermal import solid3d
    print("board | gaps (mm) | n rule | T 4 slabs | T rule | dT K | unknowns x")
    for name in RB.board_names():
        p = RB.build(name, str(_boot26.REPO / "examples"))
        b = p.board
        gaps = [float(g) for g in b.gap_thicknesses()] if b.layers > 1 else [float(b.slab_thicknesses()[0] - b.copper_thickness[0])]
        n = max(rule_slabs(g) for g in gaps)
        try:
            u4 = solid3d.unknowns(p, 2.0, 4)[0]
            t4 = solid3d.solve_steady(p, 2.0, 4).t_max
            un = solid3d.unknowns(p, 2.0, n)[0]
            tn = solid3d.solve_steady(p, 2.0, n).t_max
        except Exception as e:
            print(f"{name:22s} {type(e).__name__}: {str(e)[:70]}")
            continue
        print(f"{name:22s} {[round(g * 1e3, 2) for g in gaps]} | {n:2d} | {t4:8.3f} | {tn:8.3f} | {tn - t4:+7.3f} | {un / u4:4.2f}", flush=True)


if __name__ == "__main__":
    main()
