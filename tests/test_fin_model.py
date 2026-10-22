"""!
@file test_fin_model.py
@brief The plate-fin model of the metal block against an independent 2D finite-volume solution of one fin, and the fin limits it states.
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples"))

import fin_validation as fv                                                     # noqa: E402


@pytest.mark.parametrize("k,h,t,height", [(204.0, 10.0, 1.5e-3, 15e-3), (204.0, 100.0, 1.0e-3, 30e-3), (386.0, 30.0, 1.5e-3, 15e-3),
                                          (50.0, 100.0, 1.0e-3, 30e-3), (14.0, 100.0, 1.5e-3, 15e-3)])
def test_fin_formula_matches_a_2d_solution(k, h, t, height):
    """The corrected-length fin formula of the program is within 0.2 % of a 2D conduction solution that keeps the transverse drop and the real convecting tip
    (the cases include efficiencies from 0.97 down to 0.5)."""
    q2d, qf = fv.fin_heat_2d(k, h, t, height, nx=8, ny=160), fv.fin_heat_formula(k, h, t, height)
    assert qf == pytest.approx(q2d, rel=2e-3)


def test_fin_formula_is_the_one_in_blocks():
    """blocks.fin_ratio uses the same expression, per unit of base area."""
    from pcbthermal.blocks import fin_ratio
    from tests.test_heatsink_part import board
    s = board((15.0, 1.5, 8.0)).heatsinks[0]
    h = 20.0
    t, pitch = s.fin_thickness, s.fin_pitch
    per_fin = fv.fin_heat_formula(s.k, h, t, s.fin_height) / h                  # 2 Hc eta, in m (per unit depth)
    assert fin_ratio(h, s) == pytest.approx((1 - t / pitch) + per_fin / pitch, rel=1e-12)


def test_efficiency_limits():
    """A short fin of a good conductor is isothermal (efficiency 1); a long thin fin of a poor conductor wastes most of its height."""
    q_short = fv.fin_heat_2d(386.0, 5.0, 2e-3, 5e-3, nx=6, ny=60)
    assert q_short == pytest.approx(5.0 * (2 * 5e-3 + 2e-3), rel=5e-3)           # h x (two faces + tip) x theta_b
    long_poor = fv.fin_heat_2d(14.0, 100.0, 1e-3, 30e-3, nx=6, ny=120)
    assert long_poor < 0.3 * 100.0 * (2 * 30e-3 + 1e-3)
