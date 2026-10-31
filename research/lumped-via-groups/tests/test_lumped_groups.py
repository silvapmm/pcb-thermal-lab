#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_lumped_groups.py
@brief Tests of the via-group investigation: the independent axisymmetric solver, the closed forms of the zone network, the copies of the Lumped model and a small board against the fine-grid reference.
@details Run: `.venv/bin/python -m pytest research/lumped-via-groups/tests -q` from the repository root.
"""

import contextlib
import math
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(FOLDER, "lib"))
sys.path.insert(0, os.path.join(FOLDER, "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(FOLDER), "lumped-analytic-vias", "lib"))

import axisym_cell as ax                                                    # noqa: E402
import constriction as cr                                                   # noqa: E402
import lumped_groups as lg                                                  # noqa: E402
import lumped_patch as lp                                                   # noqa: E402
import lumped_zones as lz                                                   # noqa: E402
import refs                                                                 # noqa: E402
import study_cell_link as scl                                               # noqa: E402


def test_axisym_homogeneous_and_mixture():
    """!
    @brief A cell of one material is a 1D conductor, and an isothermal-top cell follows the rule of mixtures.
    @return None.
    """
    p, a, length = 100e-6, 30e-6, 200e-6
    assert ax.unit_cell_resistance(a, p, length, 10.0, 10.0, h_top=1e12) == pytest.approx(length / (p * p * 10.0), rel=1e-6)
    phi = math.pi * a * a / (p * p)
    r = ax.unit_cell_resistance(a, p, length, 400.0, 1.0, h_top=1e13)
    assert r == pytest.approx(length / (p * p * (phi * 400.0 + (1 - phi))), rel=1e-4)


def test_fish_microspreading_published_case():
    """!
    @brief The thick-substrate microspreading resistance of Fish (2017): 1240 K/W for a 60 um copper via at 100 um pitch in glass; this solver within 3 %.
    @return None.
    """
    p, a, length = 100e-6, 30e-6, 500e-6
    phi = math.pi * a * a / (p * p)
    r = ax.unit_cell_resistance(a, p, length, 400.0, 1.0, h_top=None)
    r_msp = r - length / (p * p * (phi * 400.0 + (1 - phi)))
    assert r_msp == pytest.approx(1240.0, rel=0.03)


def test_cell_link_against_closed_forms():
    """!
    @brief The finite-difference cell problem agrees with the lossy closed form everywhere and with the lossless Krogh form when the loss is small.
    @return None.
    """
    S, a = 0.0136, 5.6e-3
    for rho in (0.3, 0.6):
        for x in (0.05, 1.0, 2.0):
            g = S * (x / a) ** 2
            ex = scl.exact_link(S, g, rho * a, a)
            assert cr.cell_with_loss(S, g, rho * a, a, 1.0)["R_c"] == pytest.approx(ex, rel=3e-3)
            if x < 0.1:
                assert cr.krogh(S, a, rho * a) == pytest.approx(ex, rel=3e-3)


def test_annulus_out_resistance_by_integration():
    """!
    @brief The mean-to-outer-wall resistance of a heated annulus equals the numerical integral of its profile.
    @return None.
    """
    S, r_c, a = 0.0136, 2.0e-3, 5.0e-3
    r = np.linspace(r_c, a, 20001)
    # q = 1 W/m2: T(r) - T(a) = integral from r to a of I(s) / (2 pi S s) ds, I(s) = pi (s^2 - r_c^2)
    integrand = math.pi * (r * r - r_c * r_c) / (2 * math.pi * S * r)
    t = np.concatenate([[0.0], np.cumsum(0.5 * (integrand[1:] + integrand[:-1]) * np.diff(r))])
    t = t[-1] - t
    mean = np.trapezoid(t * 2 * math.pi * r, r) / (math.pi * (a * a - r_c * r_c))
    assert lz.annulus_out_resistance(S, r_c, a) == pytest.approx(mean / (math.pi * (a * a - r_c * r_c)), rel=1e-4)


def test_annulus_excess_limits():
    """!
    @brief With all the heat leaving through the outer wall the hottest point is the inner wall; no net generation gives no excess.
    @return None.
    """
    S, r_c, a = 0.0136, 2.0e-3, 5.0e-3
    assert lz.annulus_excess(S, r_c, a, 0.0, 0.0) == 0.0
    assert lz.annulus_excess(S, r_c, a, -1.0, 0.5) == 0.0
    ex = lz.annulus_excess(S, r_c, a, 0.0, 1.0)
    # inner wall minus area mean by direct integration of the same profile
    r = np.linspace(r_c, a, 20001)
    dT = -(1.0 - (a * a - r * r) / (a * a - r_c * r_c)) / (2 * math.pi * S * r)
    t = np.concatenate([[0.0], np.cumsum(0.5 * (dT[1:] + dT[:-1]) * np.diff(r))])
    t = t - t[-1]
    mean = np.trapezoid(t * 2 * math.pi * r, r) / (math.pi * (a * a - r_c * r_c))
    assert ex == pytest.approx(t.max() - mean, rel=2e-3)
    assert t.argmax() == 0


def test_groups_copy_equals_the_patch_of_the_earlier_investigation():
    """!
    @brief `lumped_groups.patched(macro="all")` is the same model as `lumped_patch.patched("krogh", cell="nn", cluster=True)`.
    @return None.
    """
    import harness as hz
    import program_cases as pc
    pc.load_libraries()
    p = refs.make_problem(dict(layers=4, n=3, pitch=1.0, fill=385.0, side=20.0, src=8.0))
    q0 = hz.no_vias(p)
    e1 = hz.effect(p, "lumped", lambda: lg.patched(macro="all"), 0.5, q0)
    e2 = hz.effect(p, "lumped", lambda: lp.patched("krogh", cell="nn", cluster=True), 0.5, q0)
    assert e1 == pytest.approx(e2, rel=1e-9)


def test_zone_model_without_vias_is_the_program():
    """!
    @brief On a board without vias the zoned Lumped model reproduces the program bit by bit.
    @return None.
    """
    import harness as hz
    import program_cases as pc
    pc.load_libraries()
    p = hz.no_vias(refs.make_problem(dict(layers=4, n=3, pitch=1.0, fill=385.0, side=20.0, src=8.0)))
    t0 = pc.max_rise(p, "lumped", 0.5)
    with lz.patched():
        t1 = pc.max_rise(p, "lumped", 0.5)
    assert t1 == pytest.approx(t0, abs=1e-12)


def test_zone_model_energy_balance_and_restore():
    """!
    @brief The zoned network closes its energy balance (all the power leaves through the films) and the program is restored afterwards.
    @return None.
    """
    from pcbthermal import lumped
    import program_cases as pc
    pc.load_libraries()
    p = refs.make_problem(dict(layers=4, n=5, pitch=1.0, fill=385.0, side=20.0, src=8.0))
    before = lumped._heater_network
    with lz.patched():
        r = lumped.solve_steady(p, 10, 0.5)
        assert lz.LAST["frac_c"] < 1.0
        assert r.residual < 1e-9
        out = r.power_out
        assert out["top"] + out["bottom"] + out["sides"] + out["heatsinks"] == pytest.approx(p.total_power(), rel=1e-9)
    assert lumped._heater_network is before


def test_zone_model_against_the_fine_grid_reference_on_a_small_board():
    """!
    @brief A 3 x 3 array under a 10 mm source on a 20 mm board: the zone model within 10 % of the fine-grid layered reference where the earlier group term is 15 % or more off.
    @return None.
    """
    import harness as hz
    import program_cases as pc
    pc.load_libraries()
    spec = dict(layers=4, n=3, pitch=1.0, fill=385.0, side=20.0, src=10.0)
    p = refs.make_problem(spec)
    ref = hz.reference_uniform(p, 1.0 / 16)[0]
    q0 = hz.no_vias(p)
    e_zone = hz.effect(p, "lumped", lambda: lz.patched(), 0.5, q0)
    e_grp = hz.effect(p, "lumped", lambda: lg.patched(macro="all"), 0.5, q0)
    assert abs(e_zone / ref - 1.0) < 0.10
    assert abs(e_grp / ref - 1.0) > 0.10


def test_rim_minus_mean_by_integration():
    """!
    @brief The rim-to-mean resistance of the Krogh cell equals the numerical integral of its profile.
    @return None.
    """
    S, a, R = 0.0136, 0.12e-3, 1.9e-3
    r = np.linspace(a, R, 40001)
    # T(r) - T(a) per watt taken by the via: (R^2 ln(r/a) - (r^2 - a^2)/2) / (2 pi S (R^2 - a^2))
    t = (R * R * np.log(r / a) - (r * r - a * a) / 2.0) / (2.0 * math.pi * S * (R * R - a * a))
    mean = np.trapezoid(t * 2 * math.pi * r, r) / (math.pi * (R * R - a * a))
    assert lz.rim_minus_mean(S, R, a) == pytest.approx(t[-1] - mean, rel=1e-4)
    assert cr.krogh(S, R, a) == pytest.approx(mean, rel=1e-4)


def test_core_internal_resistance_raises_the_core_temperature_difference():
    """!
    @brief The core-internal resistance Q / (8 pi S) lengthens the A-C link: with it the via effect of a dense array is smaller (the model is hotter).
    @return None.
    """
    import harness as hz
    import program_cases as pc
    pc.load_libraries()
    p = refs.make_problem(dict(layers=4, n=5, pitch=1.0, fill=385.0, side=20.0, src=10.0))
    q0 = hz.no_vias(p)
    e0 = hz.effect(p, "lumped", lambda: lz.patched(geometry="disc", core_int=0.0, peak="annulus"), 0.5, q0)
    e1 = hz.effect(p, "lumped", lambda: lz.patched(geometry="disc", core_int=1.0, peak="annulus"), 0.5, q0)
    assert e1 < e0


def test_micro_peak_is_positive_and_small():
    """!
    @brief With the micro peak the maximum is higher than without it, by less than one kelvin on a 3 W board.
    @return None.
    """
    import program_cases as pc
    pc.load_libraries()
    p = refs.make_problem(dict(layers=4, n=3, pitch=2.0, fill=0.0, side=20.0, src=6.0))
    with lz.patched(micro_peak=False):
        t0 = pc.max_rise(p, "lumped", 0.5)
    with lz.patched(micro_peak=True):
        t1 = pc.max_rise(p, "lumped", 0.5)
    assert 0.0 < t1 - t0 < 1.0


def test_mutual_potentials_equal_krogh_plus_core_internal():
    """!
    @brief For concentric discs the logarithmic-potential link of the real shapes equals the Krogh resistance of the annulus plus Q / (8 pi S) of the core (within 0.5 %).
    @return None.
    """
    dx = 0.2e-3
    n = int(24e-3 / dx)
    y, x = np.mgrid[0:n, 0:n]
    r = np.hypot((x + 0.5) * dx - 12e-3, (y + 0.5) * dx - 12e-3)
    wc = (r < 3.4e-3).astype(float)
    wa = ((r >= 3.4e-3) & (r < 5.6e-3)).astype(float)
    a_eq = math.sqrt((wa.sum() + wc.sum()) * dx * dx / math.pi)
    rc_eq = math.sqrt(wc.sum() * dx * dx / math.pi)
    pot = lz.mutual_potentials(wa, wc, dx, dx) / (2.0 * math.pi)
    assert pot == pytest.approx(cr.krogh(1.0, a_eq, rc_eq) + 1.0 / (8.0 * math.pi), rel=5e-3)


def test_potential_excess_matches_the_annulus_for_concentric_discs():
    """!
    @brief The lossless potential peak of concentric discs (2400 cells in A, so 700 are kept) agrees with the closed form of the annulus within 3 % with the block decimation.
    @details Regression of the review: the strided decimation of the researcher (every step-th cell in row order) put the peak 17 % above the closed form here (the earlier
             test allowed 25 % and its docstring said 10 %); with every cell it is within 0.2 %.
    @return None.
    """
    dx = 0.2e-3
    n = int(24e-3 / dx)
    y, x = np.mgrid[0:n, 0:n]
    r = np.hypot((x + 0.5) * dx - 12e-3, (y + 0.5) * dx - 12e-3)
    wc = (r < 3.4e-3).astype(float)
    wa = ((r >= 3.4e-3) & (r < 5.6e-3)).astype(float)
    S = 0.0136
    a_eq = math.sqrt((wa.sum() + wc.sum()) * dx * dx / math.pi)
    rc_eq = math.sqrt(wc.sum() * dx * dx / math.pi)
    # the closed form has no far-field sink: the heat q_out leaves at the outer wall; the potential form puts it at infinity, which only adds a constant
    ex_ann = lz.annulus_excess(S, rc_eq, a_eq, 0.3, 0.7)
    assert lz.potential_excess(wa, wc, 0.3, 0.7, S, dx, dx, decimation="block") == pytest.approx(ex_ann, rel=0.03)
    assert lz.potential_excess(wa, wc, 0.3, 0.7, S, dx, dx, max_cells=10 ** 5) == pytest.approx(ex_ann, rel=0.005)
    # the strided decimation is biased upwards (kept to document the defect)
    assert lz.potential_excess(wa, wc, 0.3, 0.7, S, dx, dx, decimation="stride") > 1.1 * ex_ann


def test_potential_excess_lossy_is_smaller():
    """!
    @brief A vertical loss flattens the profile: the peak with the K0 kernel is smaller than the lossless one.
    @return None.
    """
    dx = 0.25e-3
    n = int(24e-3 / dx)
    y, x = np.mgrid[0:n, 0:n]
    r = np.hypot((x + 0.5) * dx - 12e-3, (y + 0.5) * dx - 12e-3)
    wc = (r < 3.0e-3).astype(float)
    wa = ((r >= 3.0e-3) & (r < 7.0e-3)).astype(float)
    S = 0.0136
    e0 = lz.potential_excess(wa, wc, 0.2, 0.8, S, dx, dx)
    e1 = lz.potential_excess(wa, wc, 0.2, 0.8, S, dx, dx, lam=3e-3)
    assert 0 < e1 < e0


def test_zone_model_with_vias_that_conduct_nothing_stays_near_the_program():
    """!
    @brief Regression of the review: vias that conduct nothing (plating 1e-12 m, open) have no effect, so the zone model must stay near the program without vias.
    @details A sparse 3 x 3 array at 3 mm under a 12 mm source on a 20 mm board: the core is hotter than the rest of the footprint, and the researcher's version took the core
             mean as its peak, 4.2 % of the rise below the program; with the bump of a hot core (`core_peak`) the offset is 0.8 %.
    @return None.
    """
    import harness as hz
    import program_cases as pc
    pc.load_libraries()
    p = refs.make_problem(dict(layers=4, n=3, pitch=3.0, fill=0.0, side=20.0, src=12.0))
    p.board.via_plating = 1e-12
    t0 = pc.max_rise(hz.no_vias(p), "lumped", 0.5)
    with lz.patched():
        t_new = pc.max_rise(p, "lumped", 0.5)
    with lz.patched(core_peak=False, decimation="stride"):
        t_old = pc.max_rise(p, "lumped", 0.5)
    assert abs(t0 - t_new) < 0.015 * t0
    assert t0 - t_old > 0.03 * t0
