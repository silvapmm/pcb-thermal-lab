#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_convection_laws.py
@brief Tests of the investigation research/convection-laws: the solver of lib/mac2d.py against closed forms and the cavity benchmark, and the law tables against the numbers read from the sources.
@details Run: .venv/bin/python -m pytest -q research/convection-laws/tests   (about 40 s; the cavity runs at Ra 1e3 on 32 and 64 cells).
"""

import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import laws  # noqa: E402
import mac2d  # noqa: E402


def test_graded_faces_end_points_and_monotone():
    """!
    @brief The graded grid starts at 0, ends at the sum of the lengths and grows in the requested direction.
    @return None.
    """
    f = mac2d.graded([(1.0, 10, 0.9), (2.0, 10, 1.2)])
    assert f[0] == 0.0 and f[-1] == pytest.approx(3.0)
    w = np.diff(f)
    assert np.all(w > 0) and w[0] > w[9] and w[19] > w[10]


def test_pure_conduction_is_exact():
    """!
    @brief With Ra = 0 the hot-wall Nusselt number of the cavity is 1 (a linear profile) and no flow develops.
    @return None.
    """
    f = np.linspace(0, 1, 21)
    box = mac2d.Box(f, f, 0.0)
    box.run(t_end=10.0, tol=1e-10)
    assert (box.wall_gradient("W") * box.dy).sum() == pytest.approx(1.0, abs=1e-6)
    assert np.abs(box.u).max() < 1e-9


@pytest.mark.parametrize("n,tol", [(32, 0.01), (64, 0.004)])
def test_cavity_ra1e3_against_de_vahl_davis(n, tol):
    """!
    @brief The mean hot-wall Nusselt number of the cavity at Ra = 1e3 is 1.118 (de Vahl Davis 1983), and the two walls carry the same heat.
    @param n Cells per side.
    @param tol Relative tolerance.
    @return None.
    """
    f = np.linspace(0, 1, n + 1)
    box = mac2d.Box(f, f, 1e3)
    box.run(t_end=30.0, tol=1e-9)
    nh = (box.wall_gradient("W") * box.dy).sum()
    nc = -(box.wall_gradient("E") * box.dy).sum()
    assert nh == pytest.approx(1.118, rel=tol)
    assert nc == pytest.approx(nh, rel=1e-3)


def test_plate_energy_balance_at_low_rayleigh():
    """!
    @brief A plate in a cold box: the heat leaving the two faces equals the heat reaching the cold walls (within the first-order wall gradients), at Ra = 100.
    @return None.
    """
    xf = mac2d.graded([(1.0, 16, 0.94), (2.0, 12, 1.12)])
    yb = mac2d.graded([(2.0, 14, 0.92)])
    ya = mac2d.graded([(3.0, 18, 1.08)])
    yf = np.concatenate([yb - 2.0, ya[1:]])
    yf[len(yb) - 1] = 0.0
    box = mac2d.Box(xf, yf, 100.0, west=("sym", None), east=("wall", 0.0), south=("wall", 0.0), north=("wall", 0.0), plate=(1.0, 1.0))
    box.run(t_end=20.0, tol=1e-8)
    nu_u, nu_d, _, _ = box.plate_nusselt()
    assert box.converged
    assert sum(box.heat_into_walls().values()) / (nu_u + nu_d) == pytest.approx(1.0, abs=0.08)
    assert nu_u > 0.5 and nu_d > 0.5            # both faces carry heat (the sign of the flux is right)


def test_laws_against_values_read_in_lienhard():
    """!
    @brief Raithby-Hollands at Pr 0.71 and the program's law against the values of README section 3 (computed from the printed equations).
    @return None.
    """
    assert float(laws.C.program_up(1e3)) == pytest.approx(3.037, abs=0.001)
    assert float(laws.C.raithby_hollands_up(1e3)) == pytest.approx(3.064, abs=0.005)
    assert float(laws.C.program_up(3e2)) / float(laws.C.raithby_hollands_up(3e2)) == pytest.approx(0.93, abs=0.005)      # -7 % in the evidence file
    assert float(laws.C.program_up(1e5)) / float(laws.C.raithby_hollands_up(1e5)) == pytest.approx(1.15, abs=0.005)     # +15 %
    assert float(laws.C.program_down(1e3)) / float(laws.goldstein_lau_down(1e3)) == pytest.approx(0.80, abs=0.005)      # -20 %
