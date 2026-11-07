#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_horizontal_plate_h.py
@brief Tests of the horizontal-plate investigation: the correlations against the program and the limits printed in the sources, and the 2D / axisymmetric solver against conduction, its energy balance, the direction of the flow and the isolated faces.
@details Run: .venv/bin/python -m pytest -q research/horizontal-plate-h/tests (about a minute; the solver cases use coarse grids).
"""

import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import correlations as C                                  # noqa: E402
import plate_h2d as ph                                    # noqa: E402
from pcbthermal import convection                         # noqa: E402

COARSE = dict(n_in=24, n_out=16, n_up=30, n_dn=22, dy0=8e-3, dx_tip=2e-2)


def test_program_levels_are_the_program():
    """!
    @brief The levels `program_up` and `current_down` (the 2.6.0 lower-face law, 0.475 Ra^(1/5); `program_down` is the 2.5.x 0.27 Ra^(1/4) of the study) give the program's own h_natural_horizontal for several sizes and temperatures.
    @return None.
    """
    for length in (0.01, 0.025, 0.05):
        for ts in (30.0, 50.0, 80.0):
            for up in (True, False):
                h, ra = convection.h_natural_horizontal(ts, 20.0, length, up)
                nu = float((C.program_up if up else C.current_down)(ra))
                k = convection.air_properties(0.5 * (ts + 20.0))["k"]
                assert h == pytest.approx(nu * k / length, rel=1e-12)


def test_program_branch_change_at_1e7():
    """!
    @brief The 0.54 Ra^(1/4) and 0.15 Ra^(1/3) branches meet within 12 % at Ra = 1e7 (the textbook discontinuity of the correlation).
    @return None.
    """
    lo, hi = float(C.program_up(1e7)), float(C.program_up(1.0000001e7))
    assert hi / lo == pytest.approx(0.15 * 1e7 ** (1 / 3) / (0.54 * 1e7 ** 0.25), rel=1e-5)
    assert 1.0 < hi / lo < 1.12


def test_schulenberg_limits_as_printed():
    """!
    @brief Schulenberg's strip and disc formulas reduce to 0.544 and 0.619 at large Prandtl numbers (equations 87 and 89 of KfK 3713), and the strip's small-Prandtl limit is 0.571 (equation 43).
    @return None.
    """
    # Pr -> infinity at fixed Ra: Nu / Ra^(1/5) -> a / b^(1/3)
    assert 0.571 / 1.156 ** (1 / 3) == pytest.approx(0.544, abs=1e-3)
    assert 0.631 / 1.56 ** (1 / 3) == pytest.approx(0.544, abs=1e-3)
    assert 0.705 / 1.48 ** (1 / 3) == pytest.approx(0.619, abs=1e-3)
    # The function itself at a Prandtl number so large that Pr^(1/5) / (b Pr^(3/5))^(1/3) = b^(-1/3) holds
    pr = 1e12
    assert float(C.schulenberg_strip(1.0, pr=pr)) == pytest.approx(0.544, abs=2e-3)


def test_jaffer_shape_scaling():
    """!
    @brief The shape form of Jaffer's downward formula is the strip form with Ra scaled by q^3 and Nu divided by q; q = 1 is the strip.
    @return None.
    """
    ra = np.array([1e2, 1e4, 1e6])
    assert np.allclose(C.jaffer_down_shape(ra, 1.0), C.jaffer_down(ra))
    assert np.allclose(C.jaffer_down_shape(ra, 2.0), C.jaffer_down(8 * ra) / 2.0)


def test_use_horizontal_restores_the_program():
    """!
    @brief The context manager replaces the program's function inside and restores it outside, also on an error.
    @return None.
    """
    original = convection.h_natural_horizontal
    with C.use_horizontal(lambda ra: 1.0, lambda ra: 2.0):
        h_up, ra = convection.h_natural_horizontal(50.0, 20.0, 0.025, True)
        h_dn, _ = convection.h_natural_horizontal(50.0, 20.0, 0.025, False)
        k = convection.air_properties(35.0)["k"]
        assert h_up == pytest.approx(1.0 * k / 0.025) and h_dn == pytest.approx(2.0 * k / 0.025)
    assert convection.h_natural_horizontal is original
    with pytest.raises(RuntimeError):
        with C.use_horizontal(lambda ra: 1.0, lambda ra: 1.0):
            raise RuntimeError
    assert convection.h_natural_horizontal is original


def test_conduction_limit_strip_is_symmetric_and_balanced():
    """!
    @brief At a Rayleigh number near zero the two faces of the strip transfer the same heat within 15 % and the heat leaving the domain equals the heat leaving the plate within 15 %.
    @return None.
    """
    m = ph.HorizontalStrip(1e-2, 0.71, **COARSE)
    m.relax = 0.15
    r = m.run(max_steps=20000, check=1000, dt=2e-3)             # the far field of a conduction problem relaxes slowly: not converged to 2e-5 but to 1e-3 per 1000 steps
    assert r["nu_up"] == pytest.approx(r["nu_down"], rel=0.15)  # the domain is taller above (7) than below (3.5): a few % of difference is the box, not the physics
    assert 0.85 < m.energy_balance() < 1.15


def test_conduction_limit_disc_between_open_space_and_truncated_domain():
    """!
    @brief The conduction Nusselt number of the disc (Nu_R, both faces equal) lies between the open-space value 4/pi and the value of an outer sphere at 5 R (the domain is a box of that size): 1.27 < Nu_R < 1.75.
    @return None.
    """
    m = ph.HorizontalStrip(1e-2, 0.71, axisym=True, **COARSE)
    m.relax = 0.15
    r = m.run(max_steps=20000, check=1000, dt=2e-3)
    assert 4 / np.pi < r["nu_up"] < 1.75
    assert r["nu_up"] == pytest.approx(r["nu_down"], rel=0.15)
    assert 0.85 < m.energy_balance() < 1.15


def test_flow_direction_and_the_two_faces():
    """!
    @brief At Ra = 1e3 the air above the plate moves towards the centre and rises there, below it moves outwards; the lower face has the larger Nu when both faces are hot (the thick layer at the centre of the upper face).
    @return None.
    """
    m = ph.HorizontalStrip(1e3, 0.71, **COARSE)
    m.relax = 0.15
    r = m.run(max_steps=30000, check=1000, dt=1e-3)
    assert r["converged"]
    u, v = m.velocities()
    i = int(np.argmin(abs(m.x - 0.5)))
    jt, jb = int(np.argmin(abs(m.y - 0.3))), int(np.argmin(abs(m.y + 0.3)))
    assert u[i, jt] < 0.0 < u[i, jb]
    assert v[1, int(np.argmin(abs(m.y - 1.0)))] > 0.0
    assert r["nu_down"] > r["nu_up"] > 0.0


def test_isolated_faces_have_no_flux_on_the_insulated_side():
    """!
    @brief With the lower face insulated its Nusselt number is zero and the upper face is hotter-coupled than with both faces hot (the air under the plate is not warmed).
    @return None.
    """
    both = ph.HorizontalStrip(1e3, 0.71, **COARSE); both.relax = 0.15
    rb = both.run(max_steps=30000, check=1000, dt=1e-3)
    up = ph.HorizontalStrip(1e3, 0.71, hot_down=False, **COARSE); up.relax = 0.15
    ru = up.run(max_steps=30000, check=1000, dt=1e-3)
    assert ru["nu_down"] == 0.0
    assert ru["nu_up"] > rb["nu_up"]
    dn = ph.HorizontalStrip(1e3, 0.71, hot_up=False, **COARSE); dn.relax = 0.15
    rd = dn.run(max_steps=30000, check=1000, dt=1e-3)
    assert rd["nu_up"] == 0.0 and rd["nu_down"] > 0.0


def test_grid_refinement_changes_nu_little():
    """!
    @brief The coarse and the base grid agree on Nu of the strip at Ra = 1e3 within 3 %.
    @return None.
    """
    res = []
    for grid in (COARSE, dict(n_in=48, n_out=32, n_up=60, n_dn=44, dy0=5e-3, dx_tip=1e-2)):
        m = ph.HorizontalStrip(1e3, 0.71, hot_up=False, **grid)
        m.relax = 0.15
        res.append(m.run(max_steps=30000, check=1000, dt=1e-3)["nu_down"])
    assert res[0] == pytest.approx(res[1], rel=0.03)


def test_jaffer_down_is_equation_56_with_the_unified_prandtl_function():
    """!
    @brief Regression (review): Jaffer's equation 56 scales Ra by Xi_all of equation 54 ([1 + (0.5/Pr)^sqrt(1/3)]^sqrt(3), 2.813 at Pr 0.71), not by Xi_R of equation 51 (Schulenberg's strip, 2.633), which the first version used (1.1 to 1.3 % high).
    @return None.
    """
    assert C.xi_all(0.71) == pytest.approx(2.8126, abs=1e-3)
    assert C.xi_r(0.71) == pytest.approx(2.6332, abs=1e-3)
    for ra in (1e3, 1e5):
        assert float(C.jaffer_down(ra)) == pytest.approx(0.341 + 0.550 * (ra / C.xi_all(0.71)) ** 0.2, rel=1e-12)
        assert float(C.jaffer_down(ra)) < 0.341 + 0.550 * (ra / C.xi_r(0.71)) ** 0.2


def test_lienhard_forms_and_their_lengths():
    """!
    @brief The forms printed by Lienhard on their own lengths: Fujii and Imura (8.38) on the width W of a two-dimensional plate (a long strip has W = 2 A/P), Kadambi and Drake (8.39) on the diameter (D = 4 A/P), Raithby and Hollands (8.37a/b) with the correction below Nu 10.
    @details The review of `research/theory-sources` found 8.38 evaluated on A/P there (the plate inflated by 30 to 80 %); here the width is explicit. A long strip on its half width must agree with Schulenberg's strip within 5 % on the Ra^(1/5) coefficient (0.4396 against 0.4274).
    @return None.
    """
    ra = 3e5
    w = 2.0                                                       # a long strip: W = 2 a, A/P = a
    nu_w = 0.58 * (w ** 3 * ra) ** 0.2                            # 8.38 on the width
    assert float(C.fujii_imura_down(ra, w)) == pytest.approx(nu_w / w, rel=1e-12)
    assert float(C.fujii_imura_down(1.0, 2.0)) == pytest.approx(float(C.schulenberg_strip(1.0)), rel=0.05)
    nu_d = 0.82 * (64.0 * ra) ** 0.2 * 0.71 ** 0.034              # 8.39 on the diameter, D = 4 A/P
    assert float(C.kadambi_drake_down(ra)) == pytest.approx(nu_d / 4.0, rel=1e-12)
    nu = 0.560 * 1e4 ** 0.25 / (1 + (0.492 / 0.71) ** (9 / 16)) ** (4 / 9)
    assert nu < 10.0 and float(C.raithby_hollands_up(1e4)) == pytest.approx(1.4 / np.log(1 + 1.4 / nu), rel=1e-12)
    big = 0.560 * 1e6 ** 0.25 / (1 + (0.492 / 0.71) ** (9 / 16)) ** (4 / 9)
    assert big > 10.0 and float(C.raithby_hollands_up(1e6)) == pytest.approx(big, rel=1e-12)


def test_published_upper_faces_bracket_the_program():
    """!
    @brief Over the boards' range (Ra of A/P 1e3 to 5e5) Jaffer's upper face is above the program's and Raithby and Hollands' is at most 1 % above it and up to 20 % below: the program is neither the lowest nor the highest published level, so it is not shown to be conservative.
    @return None.
    """
    ra = np.logspace(3, np.log10(5e5), 40)
    assert np.all(C.jaffer_up(ra) > C.program_up(ra))
    rh = C.raithby_hollands_up(ra) / C.program_up(ra)
    assert rh.max() < 1.01 and rh.min() < 0.82


def test_solver_centre_of_the_lower_face_is_schulenbergs_local_value():
    """!
    @brief Regression (review): Schulenberg's equations 92 and 94 are the LOCAL Nusselt number at the stagnation point of the centre (KfK 3713 pages 31, 32 and 36), not the plate mean;
           the solver's local Nu at the centre of the isolated lower face reproduces them (strip within 6 %, disc within 3 % on the coarse grid; 0 to 4 % on the base grid), while its plate mean is 25 % or more above them.
    @return None.
    """
    m = ph.HorizontalStrip(1e3, 0.71, hot_up=False, **COARSE); m.relax = 0.15
    r = m.run(max_steps=30000, check=1000, dt=1e-3)
    _, _, nd = m.nusselt_local()
    assert nd[0] == pytest.approx(float(C.schulenberg_strip(1e3)), rel=0.06)
    assert r["nu_down"] > 1.25 * float(C.schulenberg_strip(1e3))
    d = ph.HorizontalStrip(8e3, 0.71, hot_up=False, axisym=True, **COARSE); d.relax = 0.15
    d.run(max_steps=30000, check=1000, dt=1e-3)
    _, _, ndd = d.nusselt_local()
    assert ndd[0] == pytest.approx(2.0 * float(C.schulenberg_disc(1e3)), rel=0.03)    # Nu_R at the centre; schulenberg_disc returns Nu of A/P = R/2


def test_heat_through_boxes_of_the_disc_agree():
    """!
    @brief The heat crossing three boxes around the disc agrees within 5 % from box to box (the field is nearly conservative) and exceeds the wall-gradient heat (the singular flux at the edge of a zero-thickness plate is under-resolved): the energy balance of the disc is a wall error, not a field error.
    @return None.
    """
    d = ph.HorizontalStrip(8e3, 0.71, hot_up=False, axisym=True, **COARSE); d.relax = 0.15
    d.run(max_steps=30000, check=1000, dt=1e-3)
    boxes = [d.heat_through_box(*b) for b in ((1.5, 1.0, -0.5), (2.0, 2.0, -1.0), (3.0, 4.0, -2.0))]
    assert max(boxes) / min(boxes) < 1.05
    assert min(boxes) > 1.0
