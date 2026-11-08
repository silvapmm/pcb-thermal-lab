#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_via_contact_geometry.py
@brief Tests of the libraries of via-contact-geometry: the axisymmetric cell against the series circuit, the barrel patch, the rim share and the bit-identity of the contact coupling on full copper.
"""

import math

import numpy as np

import axicell as AX
import barrel as BA
import contact as CT
from pcbthermal import Problem, fvm, viawell


def test_axicell_without_via_is_the_series_circuit():
    """!
    @brief No via: R = sum(t / k) / pitch^2 (uniform flux, isothermal bottom, planes continuous), to the discretisation.
    @return None.
    """
    stack = AX.equal_gap_stack(4, 1.6e-3, 70e-6)
    pitch = 0.45e-3
    r = AX.unit_cell(pitch, 0.25e-3, 0.026, stack, no_via=True)
    exact = sum(t / (393.0 if cu else 0.29) for t, cu in stack) / pitch ** 2
    assert abs(r / exact - 1.0) < 1e-3


def test_axicell_reproduces_the_shen_stack_of_published_cases_followup():
    """!
    @brief The cell on the stack of research/published-cases-followup 6.4 (4 x 70 um, 1.6 mm, drill 0.25 mm, air, pitch 0.45 mm) gives the 207.52 K/W that study prints.
    @return None.
    """
    r = AX.unit_cell(0.45e-3, 0.25e-3, 0.026, AX.equal_gap_stack(4, 1.6e-3, 70e-6))
    assert abs(r - 207.52) < 0.01


def test_axicell_via_lowers_resistance_and_converges():
    """!
    @brief A copper-plated via lowers R; the answer changes by under 0.5 % when the radial and vertical grids are refined.
    @return None.
    """
    stack = AX.equal_gap_stack(4, 1.0e-3, 35e-6)
    r_no = AX.unit_cell(0.5e-3, 0.3e-3, 0.026, stack, no_via=True)
    r1 = AX.unit_cell(0.5e-3, 0.3e-3, 0.026, stack)
    r2 = AX.unit_cell(0.5e-3, 0.3e-3, 0.026, stack, nr_out=96, nr_barrel=12, nr_hole=12, nz_cu=6, nz_gap=24)
    assert r1 < r_no
    assert abs(r2 / r1 - 1.0) < 5e-3


def test_axicell_limit_of_a_perfect_barrel_is_the_plane_stack():
    """!
    @brief With k_fill = k_cu and thick plating the via is a solid copper rod: R falls below the hollow barrel and stays positive.
    @return None.
    """
    stack = AX.equal_gap_stack(2, 0.5e-3, 35e-6)
    hollow = AX.unit_cell(0.5e-3, 0.3e-3, 0.026, stack)
    solid = AX.unit_cell(0.5e-3, 0.3e-3, 393.0, stack)
    assert 0 < solid < hollow


def test_barrel_patch_scales_the_gap_conductance_and_restores():
    """!
    @brief The patch changes the program's via coupling only inside the with-block and by the factor d / (d + a t).
    @return None.
    """
    def lone():
        p = Problem.new(2.0, 2.0, 2, 1.0, 70.0, h_top=10.0, h_bottom=10.0, h_side=0.0)
        for layer in (1, 2):
            p.add_zone(layer, rect=(0, 0, 2, 2))
        p.add_heater(1, 1.0, rect=(0.5, 0.5, 1.5, 1.5))
        p.add_via(1.0, 1.0, 0.3)
        return p

    base = fvm.solve_steady(lone(), 0.25).t_max
    orig = viawell.build
    with BA.patched(0.5):
        assert viawell.build is not orig
        t5 = fvm.solve_steady(lone(), 0.25).t_max
    assert viawell.build is orig
    assert t5 > base                                                           # a longer barrel conducts less: hotter
    assert fvm.solve_steady(lone(), 0.25).t_max == base                       # restored, bit for bit
    with BA.patched(0.0):
        assert fvm.solve_steady(lone(), 0.25).t_max == base                   # a = 0 is the program


def test_rim_share_of_the_copper_cases():
    """!
    @brief Rim share f: 1 on full copper, 0.25 at the corner of a quadrant, 0.5 on an edge through the centre, 0 outside the copper.
    @return None.
    """
    def board(rect):
        p = Problem.new(10.0, 10.0, 2, 1.6, 35.0)
        p.add_zone(1, rect=rect)
        p.add_via(5.0, 5.0, 0.3)
        return p

    v = lambda p: p.vias[0]                                                    # noqa: E731
    p = board((0, 0, 10, 10))
    assert CT.rim_copper_share(p, v(p), 0) == 1.0
    p = board((1, 1, 5, 5))
    assert abs(CT.rim_copper_share(p, v(p), 0) - 0.25) < 1e-9
    p = board((0, 0, 5, 10))
    assert abs(CT.rim_copper_share(p, v(p), 0) - 0.5) < 1e-9
    p = board((1, 1, 4.7, 9))
    assert CT.rim_copper_share(p, v(p), 0) == 0.0
    assert CT.rim_copper_share(p, v(p), 1) == 0.0                              # a layer with no zone has no copper


def test_contact_coupling_is_bit_identical_on_full_copper():
    """!
    @brief A via on uniform full copper in every layer is built by the program's own code: the field is identical.
    @return None.
    """
    def lone():
        p = Problem.new(10.0, 10.0, 2, 1.6, 35.0, h_top=50.0, h_bottom=50.0, h_side=0.0)
        for layer in (1, 2):
            p.add_zone(layer, rect=(0, 0, 10, 10))
        p.add_heater(1, 0.5, rect=(4.5, 4.5, 5.5, 5.5))
        p.add_via(5.0, 5.0, 0.3)
        return p

    a = fvm.solve_steady(lone(), 0.5).t_max
    with CT.patched("contact"):
        b = fvm.solve_steady(lone(), 0.5).t_max
    assert a == b


def test_contact_uncouples_a_layer_with_no_contact_and_is_conservative():
    """!
    @brief A via 0.3 mm outside the copper edge of the top layer: the contact coupling lets the part read hotter than the program (safe side) and no colder than the board without the via.
    @return None.
    """
    def case(with_via):
        p = Problem.new(10.0, 10.0, 2, 1.6, 35.0, h_top=50.0, h_bottom=50.0, h_side=None)
        p.add_zone(2, rect=(0, 0, 10, 10))
        p.add_zone(1, rect=(1, 1, 4.7, 9))
        p.add_heater(1, 0.5, rect=(2.7, 4, 4.7, 6))
        if with_via:
            p.add_via(5.0, 5.0, 0.3)
        return p

    base = fvm.solve_steady(case(False), 0.5).t_max
    prog = fvm.solve_steady(case(True), 0.5).t_max
    with CT.patched("contact"):
        cont = fvm.solve_steady(case(True), 0.5).t_max
    assert cont >= prog                                                       # the program over-reads the via here
    assert cont <= base + 1e-9                                                # the via never heats the board
    assert math.isfinite(cont) and not np.isnan(cont)
