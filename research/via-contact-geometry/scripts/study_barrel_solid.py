#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_barrel_solid.py
@brief Cross-check of the barrel deficit with a second view: the 3D solid of the program (real copper slabs, explicit barrel) against the axisymmetric cell, on unit-cell boards.
@details The same boards as scripts/study_barrel_length.py (one via, 1 W over the whole top, isothermal bottom, insulated sides) with four layers, in the 3D solid at a plan cell of
         pitch / 10 and 8 slabs per gap, next to the FVM with the program's barrel and with the rule a = 0.5. The 3D solid is a program model, so this is a consistency check of the
         trend (its barrel is a column of copper cells through the copper slabs), not an independent reference.
         Run from the repository root: `.venv/bin/python research/via-contact-geometry/scripts/study_barrel_solid.py`.
"""

import logging
import sys

import _bootstrap  # noqa: F401

import axicell as AX
import barrel as BA
import study_barrel_length as SB

logging.disable(logging.WARNING)


def solid_r(n_layers, t_board, t_cu, phi, pitch, kf, cell_div, n_diel=8):
    """!
    @brief R of the unit-cell board in the 3D solid.
    @param n_layers Copper layers.
    @param t_board Board thickness in m.
    @param t_cu Copper thickness in m.
    @param phi Drill in m.
    @param pitch Cell side in m.
    @param kf Filler conductivity in W/mK.
    @param cell_div Cells across the pitch.
    @param n_diel Slabs per dielectric gap.
    @return float K/W.
    """
    from pcbthermal import Problem, analysis, solid3d
    from pcbthermal.model import Materials
    side = pitch * 1e3
    p = Problem.new(side, side, n_layers, t_board * 1e3, t_cu * 1e6, ambient=0.0, h_top=0.0, h_bottom=1.0e7, h_side=0.0, via_plating=SB.T_PTH,
                    materials=Materials(k_copper=SB.K_CU, k_fr4_through=SB.K_Z, k_fr4_inplane=SB.K_R))
    for layer in range(1, n_layers + 1):
        p.add_zone(layer, rect=(0.0, 0.0, side, side))
    p.add_heater(1, 1.0, rect=(0.0, 0.0, side, side))
    p.add_via(side / 2, side / 2, phi * 1e3, fill_k=kf)
    res = solid3d.solve_steady(p, side / cell_div, n_diel=n_diel)
    return float(analysis.heater_stats(res, p)[0]["t_mean"])


def main():
    """!
    @brief Print the comparison.
    @return None.
    """
    phi, pitch, kf = 0.3e-3, 0.5e-3, 0.026
    print("4 layers, phi 0.3 mm, pitch 0.5 mm, air; error of R against the axisymmetric cell, per cent")
    print(f"{'t_cu um':>8s} {'gap mm':>7s} {'ref K/W':>9s} {'FVM a=0':>8s} {'FVM a=.5':>9s} {'3D solid':>9s}")
    for tcu, gap in ((18e-6, 0.2e-3), (35e-6, 0.2e-3), (70e-6, 0.2e-3), (70e-6, 0.44e-3), (105e-6, 0.2e-3), (105e-6, 0.44e-3)):
        tb = 4 * tcu + 3 * gap
        ref = AX.unit_cell(pitch, phi, kf, AX.equal_gap_stack(4, tb, tcu))
        f0 = SB.program_r(4, tb, tcu, phi, pitch, kf, "fvm", 8)
        with BA.patched(0.5):
            f5 = SB.program_r(4, tb, tcu, phi, pitch, kf, "fvm", 8)
        s3 = solid_r(4, tb, tcu, phi, pitch, kf, 10)
        print(f"{tcu * 1e6:8.0f} {gap * 1e3:7.2f} {ref:9.2f} {100 * (f0 / ref - 1):+8.1f} {100 * (f5 / ref - 1):+9.1f} {100 * (s3 / ref - 1):+9.1f}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
