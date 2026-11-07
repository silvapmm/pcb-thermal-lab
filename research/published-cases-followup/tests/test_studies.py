#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_studies.py
@brief The studies of this investigation on small cases: the program's models against the references on the strip cell, the coupon, the via unit and the plate, and the identity of the unit-cell variant with the original.
"""

import math

import numpy as np
import pytest

import layered3d as L3
import plate_series as PS
import series as S
import study_coupon_program as CP
import study_near_edge as NE
import study_shen_vias as SH
import study_table2_strip as T2


def test_unit_cell_variant_is_identical_to_the_original_without_the_switches():
    phi, pitch = 0.25e-3, 0.45e-3
    a = SH.SC.unit_cell(pitch=pitch, phi=phi, k_fill=SH.K_AIR)
    b = SH.VC.unit_cell(pitch, phi, SH.K_AIR)
    assert a == pytest.approx(b, rel=1e-12)
    assert SH.VC.unit_cell(pitch, phi, SH.K_AIR, planes_over_hole=True, flux_over_hole=True) < a      # more copper and more inlet: lower


def test_shen_optimal_diameters_and_the_published_increases():
    s = 0.2e-3
    assert SH.phi_opt(s, SH.K_AIR) == pytest.approx(0.25e-3, rel=5e-3)
    assert SH.phi_opt(s, SH.K_SOLDER) == pytest.approx(0.8e-3, rel=2e-2)
    up = SH.theta_n(0.8e-3, s, SH.K_AIR) / SH.theta_n(SH.phi_opt(s, SH.K_AIR), s, SH.K_AIR) - 1
    assert up == pytest.approx(0.44, abs=0.012)                  # printed +44 %
    up = SH.theta_n(0.2e-3, s, SH.K_SOLDER) / SH.theta_n(SH.phi_opt(s, SH.K_SOLDER), s, SH.K_SOLDER) - 1
    assert up == pytest.approx(0.23, abs=0.012)                  # printed +23 %
    assert SH.theta_n(0.25e-3, s, SH.K_AIR, pattern=2, simplified=True) / SH.theta_n(0.25e-3, s, SH.K_AIR, simplified=True) == pytest.approx(math.sqrt(3) / 2, rel=1e-12)


def test_shen_cfd_without_vias_implies_the_conductivity_035():
    a = SH.SC.SIDE ** 2
    r = (SH.T_BOARD - SH.N_CU * SH.T_CU) / (0.35 * a) + SH.N_CU * SH.T_CU / SH.K_CU / a
    assert r == pytest.approx(120.3, abs=0.1)


def test_program_on_the_strip_cell_thin_slab_against_equation_23():
    psi, _ = T2.psi_program("fvm", 0.2, 0.1, 2.0, 0.5)
    assert psi == pytest.approx(S.psi_finite(0.2, 0.1, 2.0), rel=0.03)
    psi_t, _ = T2.psi_program("fvm", 0.2, 3.0, 2.0, 0.5)
    assert psi_t < 0.7 * S.psi_finite(0.2, 3.0, 2.0)               # the documented limit: one node and at most four sub-gaps through a thick slab read it far too low


def test_coupon_program_matches_the_solver_on_the_base_stack():
    side = 26.0
    r_ref = CP.solver_rsolid("base", side, True, 1e-3)
    r_fvm = CP.program_rsolid("base", side, "fvm", 1.0)
    assert r_fvm == pytest.approx(r_ref, rel=0.01)
    r_ref2 = CP.solver_rsolid("case2", side, True, 1e-3)
    assert CP.program_rsolid("case2", side, "fvm", 1.0) == pytest.approx(r_ref2, rel=0.01)


def test_near_edge_fvm_and_analytic_against_the_exact_plate_and_the_published_corner():
    s = NE.series_rc(0.0, 0.0)[0]
    assert s == pytest.approx(2.27, abs=0.01)
    assert NE.program_rc(0.0, 0.0, "fvm", 1.0)[0] == pytest.approx(s, rel=0.01)
    assert NE.program_rc(0.0, 0.0, "analytic", 1.0)[0] == pytest.approx(s, rel=0.01)
    # the published correlation (Seri Lee) reads the corner 4.6 % above the exact thin plate
    assert abs(2.38 / s - 1) == pytest.approx(0.049, abs=0.01)


def test_square_cell_in_cartesian_3d_agrees_with_the_equal_area_disc():
    phi, pitch = 0.25e-3, 0.45e-3
    a = SH.SC.unit_cell(pitch=pitch, phi=phi, k_fill=SH.K_AIR)
    s = SH.CC.unit_cell(pitch, phi, SH.K_AIR, dx=pitch / 18)
    assert s == pytest.approx(a, rel=0.02)
