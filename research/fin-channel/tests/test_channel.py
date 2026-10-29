#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_channel.py
@brief Tests of the channel-effect investigation: the correlations and their limits, the optimum spacing, the independent numerical channel solver, the fin-array model and the in-memory patch of the program.

Run: .venv/bin/python -m pytest -q research/fin-channel/tests
"""

import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
sys.path.insert(0, os.path.join(ROOT, "research", "block-and-fins", "scripts"))

import channel as ch                                      # noqa: E402
import channel_bl as cb                                   # noqa: E402


def _nu(name, ra):
    """!
    @brief A correlation by name at Pr = 0.71.
    @param name Key of `channel.CORRELATIONS`.
    @param ra Channel Rayleigh number.
    @return Nu_b.
    """
    f = ch.CORRELATIONS[name]
    return f(ra, 0.71) if f is ch.nu_churchill else f(ra)


@pytest.mark.parametrize("name", list(ch.CORRELATIONS))
def test_fully_developed_limit(name):
    """!
    @brief Every correlation tends to Nu_b = Ra_b / 24 (parabolic flow between isothermal plates) as Ra_b tends to zero.
    @param name Correlation.
    @return None.
    """
    assert _nu(name, 1e-4) / 1e-4 == pytest.approx(1.0 / 24.0, rel=2e-3)


@pytest.mark.parametrize("name,const", [("Elenbaas", 35 ** 0.75 / 24), ("Bar-Cohen-Rohsenow", 0.59), ("Raithby-Hollands", 0.62)])
def test_boundary_layer_limit(name, const):
    """!
    @brief The large-Rayleigh limits of the correlations are their published constants (Elenbaas: 35^(3/4)/24 = 0.5996, 0.59, 0.62).
    @param name Correlation.
    @param const Expected Nu / Ra^(1/4).
    @return None.
    """
    assert _nu(name, 1e12) / 1e12 ** 0.25 == pytest.approx(const, rel=2e-3)


def test_optimum_constants_of_bar_cohen_rohsenow():
    """!
    @brief Maximising Nu_b / b^2 on equation 21 gives S_opt = 2.7156 L / Ra_L^(1/4), Ra_b = 54.4 and Nu_b = 1.308 (the values quoted from memory in the repository are 2.714 and 1.307).
    @return None.
    """
    k, ra_b, nu = ch.optimum_spacing_constants(ch.nu_bcr)
    assert k == pytest.approx(2.7156, abs=2e-3)
    assert ra_b == pytest.approx(54.4, abs=0.1)
    assert nu == pytest.approx(1.308, abs=2e-3)


def test_fin_efficiency_limits():
    """!
    @brief The fin efficiency tends to 1 for a short or highly conducting fin and to 1/(m Hc) for a long one.
    @return None.
    """
    assert ch.fin_efficiency(1.0, 1e6, 1e-3, 1e-2) == pytest.approx(1.0, abs=1e-6)
    m = math.sqrt(2 * 100.0 / (10.0 * 1e-3))
    assert ch.fin_efficiency(100.0, 10.0, 1e-3, 1.0) == pytest.approx(1.0 / (m * 1.0), rel=1e-6)


def test_array_without_channel_is_the_uniform_fin_formula():
    """!
    @brief With channel=False every face has the isolated-plate coefficient: the heat is h theta [(n-1) s L + 2 n eta Hc L] (the fin formula of the program per pitch, with the width n t + (n-1) s).
    @return None.
    """
    n, s, t, hgt, length, k, theta = 8, 0.006, 0.0015, 0.015, 0.04, 204.0, 40.0
    r = ch.array_heat(theta, n, s, t, hgt, length, k, channel=False)
    h = ch.h_plate_vertical(theta, length)
    eta = ch.fin_efficiency(h, k, t, hgt + 0.5 * t)
    expected = h * theta * ((n - 1) * s * length + 2 * n * eta * (hgt + 0.5 * t) * length)
    assert r["q"] == pytest.approx(expected, rel=1e-9)


def test_channel_gives_less_heat_than_plate_for_close_fins_and_not_for_wide_ones():
    """!
    @brief The channel model cuts the heat of close fins (3 mm) by a large factor and changes that of wide fins (45 mm) by less than 15 %.
    @return None.
    """
    for s, bound in ((0.003, 0.5), (0.045, None)):
        n = round((0.190 + s) / (s + 0.003))
        a = ch.array_heat(40.0, n, s, 0.003, 0.017, 0.15, 150.0, channel=False)["q"]
        b = ch.array_heat(40.0, n, s, 0.003, 0.017, 0.15, 150.0, channel=True)["q"]
        if bound:
            assert b < bound * a
        else:
            assert abs(b / a - 1) < 0.15


def test_numerical_channel_small_rayleigh_limit_and_envelope():
    """!
    @brief The independent marching solution reaches Nu_b = Ra_b/24 within 3 % at Ra_b = 1 and lies inside the envelope of the four correlations (widened by 10 %) from 1 to 1e3, with an energy balance within 5 %.
    @return None.
    """
    r = cb.solve(1.0, n_y=80, n_x=300, stretch=3.0)
    assert r["nu_b"] == pytest.approx(1.0 / 24.0, rel=0.03)
    for ra in (1.0, 10.0, 100.0, 1.0e3):
        r = cb.solve(ra, n_y=80, n_x=300, stretch=3.0)
        vals = [_nu(n, ra) for n in ch.CORRELATIONS]
        assert 0.9 * min(vals) <= r["nu_b"] <= 1.1 * max(vals)
        assert abs(r["energy_residual"]) < 0.05
        assert abs(r["q_exit"]) < 1e-9          # the shooting found the entrance speed that gives the ambient pressure at the exit


def test_numerical_channel_grid_convergence():
    """!
    @brief Doubling the grid changes the Nusselt number by less than 1 % at Ra_b = 100.
    @return None.
    """
    a = cb.solve(100.0, n_y=80, n_x=300, stretch=3.0)["nu_b"]
    b = cb.solve(100.0, n_y=160, n_x=600, stretch=3.0)["nu_b"]
    assert abs(a / b - 1) < 0.01


def test_patch_is_restored_and_effective_pitch_inverts():
    """!
    @brief `blocks.exposed_h` is the program's function again after the context, and the effective pitch gives back the target coefficient.
    @return None.
    """
    from pcbthermal import blocks
    import program_patch as pp
    from study_finned_block_all_models import board
    original = blocks.exposed_h
    p = board((15.0, 1.5, 8.0))
    with pp.channel_effect(40.0, 0.04):
        assert blocks.exposed_h is not original
    assert blocks.exposed_h is original
    s = p.heatsinks[0]
    target = 20.0
    pitch = pp.effective_pitch(s, 7.0, target)
    s.fin_pitch = pitch
    assert blocks.exposed_h(s, 7.0) == pytest.approx(target, rel=1e-9)
    with pytest.raises(ValueError):
        pp.effective_pitch(s, 7.0, 7.0)


def test_program_with_channel_effect_is_hotter_for_close_fins_and_equal_for_wide_ones():
    """!
    @brief On the 60 x 40 mm board with a finned block (FVM, 2 mm cells) the channel coefficient makes a 2.5 mm gap hotter by more than 20 % and changes a 20 mm gap by less than 5 %; the 3D solid gives the same sign.
    @return None.
    """
    import program_patch as pp
    from study_program_finned_block import case, solve_program_plate
    for gap, check in ((2.5, lambda d: d > 20.0), (20.0, lambda d: abs(d) < 5.0)):
        p = case(15.0, 1.5, gap + 1.5, 3.0)
        a = solve_program_plate(p, 0.040, "fvm", 2.0)
        b = pp.solve_channel(p, 0.040, "fvm", 2.0)
        assert check(100 * (b["rise"] / a["rise"] - 1))
    p = case(15.0, 1.5, 3.5 + 1.5, 3.0)
    a = solve_program_plate(p, 0.040, "solid3d", 2.0)
    b = pp.solve_channel(p, 0.040, "solid3d", 2.0)
    assert b["rise"] > 1.1 * a["rise"]


def test_phi_values_and_rule_threshold():
    """!
    @brief The channel fraction phi: 0.9 at Ra_b = 90.07 (the threshold of the proposed rule), 0.5 at 16.47, tends to 1 for open channels and equals Nu / (0.59 Ra^(1/4)) of the composite.
    @return None.
    """
    from scipy.optimize import brentq
    assert brentq(lambda r: ch.phi(r) - 0.9, 1.0, 1e4) == pytest.approx(90.07, abs=0.05)
    assert brentq(lambda r: ch.phi(r) - 0.5, 1.0, 1e4) == pytest.approx(16.47, abs=0.05)
    assert ch.phi(1e6) > 0.9999
    for ra in (3.0, 54.38, 500.0):
        assert ch.phi(ra) == pytest.approx(ch.nu_bcr(ra) / (0.59 * ra ** 0.25), rel=1e-12)


def test_rule_cases_of_the_integration_document():
    """!
    @brief The warning cases of INTEGRATION.md: Ra_b below 90 at a 5.5 mm gap (40 mm, 40 K) and at 6.5 mm for 100 mm and 20 K; above 90 at 6.5 mm (40 mm, 40 K) and at 20 mm.
    @return None.
    """
    assert ch.ra_channel(40.0, 0.0055, 0.040) < 90.0
    assert ch.ra_channel(40.0, 0.0065, 0.040) > 90.0
    assert ch.ra_channel(20.0, 0.0065, 0.100) < 90.0
    assert ch.ra_channel(10.0, 0.020, 0.200) > 90.0
