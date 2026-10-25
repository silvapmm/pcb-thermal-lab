"""!
@file study_block_against_fem.py
@brief Does the metal block of the FVM and FDM (a heatsink with a thickness) follow an independent 3D finite-element solid?

@details Reproduces the metal-block table of README section 4.2, which no script printed before the review. Board of tests/test_blocks.py:
         100 x 80 mm, 2 layers, full top copper, 5 W on a 10 x 10 mm heater at the centre, a copper pad on the bottom (30 x 30 mm unless stated) and an
         aluminium block (k 204 W/mK) under it (60 x 60 mm, 3 mm, interface 5 K cm2/W unless stated). The 3D finite-element solid of fem3d_validation.py
         (scikit-fem) models the interface as a slab of 1 W/mK and thickness R'' and the block as a slab below the board whose side faces lose heat too.
         FVM and FDM at 1 mm cells, the program's 3D solid (finite volumes) at 1 mm as well; error on the rise against the FEM.

Usage: .venv/bin/python research/solid3d-verification/scripts/study_block_against_fem.py   (from the repository root; needs scikit-fem; about 1 minute)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)

import fem3d_validation as f3                                          # noqa: E402
from pcbthermal import Problem, fdm, fvm, solid3d                       # noqa: E402


def board(block=True, pad=(35, 25, 65, 55), rect=(20, 10, 80, 70), h_extra=0.0, thickness=3.0, **kw):
    """!
    @brief The board of the block table (the same as tests/test_blocks.py).
    @param block True to add the block.
    @param pad Bottom copper rectangle in mm.
    @param rect Block rectangle in mm.
    @param h_extra Extra coefficient of the block in W/m2K.
    @param thickness Block thickness in mm.
    @param kw Further arguments of Problem.add_heatsink (k, contact_r).
    @return Problem.
    """
    p = Problem.new(100, 80, 2).add_zone(1, rect=(0, 0, 100, 80))
    if pad:
        p.add_zone(2, rect=pad)
    p.add_heater(1, 5.0, rect=(45, 35, 55, 45))
    if block:
        p.add_heatsink(2, h_extra, rect=rect, thickness_mm=thickness, **kw)
    return p


CASES = (("no block (bottom pad only)", dict(block=False)),
         ("Al 3 mm, gap pad 5 K cm²/W", dict(contact_r=5e-4)),
         ("same, finned (extra h 60 W/m²K)", dict(contact_r=5e-4, h_extra=60.0)),
         ("same, worse interface (20 K cm²/W)", dict(contact_r=2e-3)),
         ("Al 1 mm", dict(contact_r=5e-4, thickness=1.0)),
         ("Cu 3 mm", dict(contact_r=5e-4, k=385.0, rho_cp=3.45e6)),
         ("Al 3 mm 40 × 40 over a 50 × 50 mm pad", dict(contact_r=5e-4, pad=(25, 15, 75, 65), rect=(30, 20, 70, 60))),
         ("Al 3 mm 30 × 30 exactly over the pad", dict(contact_r=5e-4, rect=(35, 25, 65, 55))))


def main():
    """!
    @brief Print the block table (maximum temperature in degC and the error on the rise against the FEM).
    @return None.
    """
    print("| Case | 3D FEM [°C] | FVM | FDM | 3D solid (FV) |")
    print("| :-- | --: | --: | --: | --: |")
    for name, kw in CASES:
        p = board(**kw)
        ref = f3.solve_fem(p, 1.0)["t_max"]
        cells = []
        for r in (fvm.solve_steady(p, 1.0), fdm.solve_steady(p, 1.0), solid3d.solve_steady(p, 1.0)):
            cells.append(f"{r.t_max:.1f} ({100 * (r.t_max - 25) / (ref - 25) - 100:+.1f} %)")
        print(f"| {name} | {ref:.1f} | " + " | ".join(cells) + " |", flush=True)


if __name__ == "__main__":
    main()
