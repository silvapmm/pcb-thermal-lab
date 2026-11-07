#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_rotated_square.py
@brief Tests of the investigation: the axisymmetric reference against closed forms, the cut-cell geometry, the variants of the 3D solid against the program (identical where they must be) and the invariance of the answer under a shift and a turn of the board.
"""

import math
import os
import sys

import numpy as np
from scipy.special import i0, i1, k0, k1

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "lib"))

import axisym3d   # noqa: E402
import cutcell    # noqa: E402
import rotsq      # noqa: E402
from pcbthermal import Problem, geometry   # noqa: E402


def test_axisym_single_slab_matches_the_bessel_solution():
    """!
    @brief A thin plate with the same film on both faces and a disc source: modified Bessel functions give the rise inside and outside the source.
    @return None.
    """
    k, t, h, a, big_r, power = 385.0, 35e-6, 10.0, 0.01, 0.4, 3.0
    m = math.sqrt(2.0 * h / (k * t))
    q = power / (math.pi * a * a)
    got = axisym3d.solve_disc(big_r, a, power, [(t, k, k)], h, h, 0.0, n_rings=8000)
    # The film acts on both faces and the source is a flux on the top face, so the plate sees q on the disc and 2 h theta of loss
    centre = q / (2.0 * h) * (1.0 - a * m * k1(m * a) * i0(0.0))
    assert abs(got["theta"][0, 0] - centre) < 2e-3 * centre
    r = got["r"][np.argmin(abs(got["r"] - 0.03))]
    outside = q / (2.0 * h) * a * m * i1(m * a) * k0(m * r)
    assert abs(got["theta"][0, np.argmin(abs(got["r"] - 0.03))] - outside) < 1e-2 * outside + 1e-6


def test_axisym_energy_balance_and_series_circuit():
    """!
    @brief The heat to the faces and the rim adds up to the power, and a source over the whole face with an insulated rim is the one-dimensional series circuit.
    @return None.
    """
    p = rotsq.disc_board(40.0, 3.0, 300.0)
    res = axisym3d.solve_disc(0.02, 0.003, 2.0, axisym3d.slabs_of(p), p.board.h_top, p.board.h_bottom, 300.0, n_rings=1500)
    assert abs(res["heat_top"] + res["heat_bottom"] + res["heat_rim"] - 2.0) < 1e-9
    assert res["residual"] < 1e-9
    slabs = axisym3d.slabs_of(p)
    full = axisym3d.solve_disc(0.02, 0.02, 2.0, slabs, 10.0, 25.0, 0.0, n_rings=50)
    area = math.pi * 0.02 ** 2
    # Series chain from the top copper to the bottom face (heat splits between the top film and the path down)
    r_down = sum(dz / kz for dz, _, kz in slabs[1:-1]) + 0.5 * slabs[0][0] / slabs[0][2] + 0.5 * slabs[-1][0] / slabs[-1][2]
    r_down += 1.0 / 25.0
    # theta_top: flux q = (theta_top)(h_top + 1 / r_down); top-slab centre is the node, its half slab sits in series with the film
    q = 2.0 / area
    g_top = 1.0 / (1.0 / 10.0 + slabs[0][0] / (2.0 * slabs[0][2]))
    assert abs(full["t_top_max"] - q / (g_top + 1.0 / r_down)) < 1e-6 * full["t_top_max"]


def test_cut_geometry_of_a_half_cut_column():
    """!
    @brief An outline through the middle of a column of cells: cover 0.5, centroid a quarter of a cell from the edge, apertures 1 along the cut and 0 across it.
    @return None.
    """
    dx = 1e-3
    poly = np.array([[0.0, 0.0], [5.5e-3, 0.0], [5.5e-3, 8e-3], [0.0, 8e-3]])
    g = cutcell.cut_geometry(poly, 8, 8, dx, dx)
    assert np.allclose(g["cover"][:, 5], 0.5) and np.allclose(g["cover"][:, :5], 1.0) and np.allclose(g["cover"][:, 6:], 0.0)
    assert np.allclose(g["xc"][:, 5], 5.25e-3, atol=1e-5)
    assert np.allclose(g["ax"][:, 4], 1.0) and np.allclose(g["ax"][:, 5], 0.0)    # the face between columns 4 and 5 is board; between 5 and 6 it is not
    # Faces between rows: full board in the whole columns, half the face (the board half) in the cut column, none beyond
    assert np.allclose(g["ay"][:, :5], 1.0) and np.allclose(g["ay"][:, 5], 0.5) and np.allclose(g["ay"][:, 6:], 0.0)


def test_cut_cover_adds_up_to_the_area_of_a_turned_square():
    """!
    @brief The cover of the cut-cell geometry adds up to the area of the turned square (to the sampling accuracy).
    @return None.
    """
    poly = np.array(rotsq.turned_square(20.0, 27.0, (15.0, 15.0))) / 1000.0
    g = cutcell.cut_geometry(poly, 60, 60, 0.5e-3, 0.5e-3)
    assert abs(g["cover"].sum() * 0.25e-6 - geometry.polygon_area(poly)) < 2e-3 * geometry.polygon_area(poly)


def test_variant_modules_are_built_from_the_source_and_the_program_is_unchanged():
    """!
    @brief Every variant is built (each replaced expression is found once) and the program's own module is untouched.
    @return None.
    """
    import pcbthermal.solid3d as program
    for name in rotsq.VARIANTS:
        mod = rotsq.variant_solid3d(name)
        assert hasattr(mod, "Solid") and hasattr(mod, "solve_steady")
    # "program" is the 2.5.x module (read from the tag v2.5.1: 2.6.0 changed solid3d.py); "current" is the live one
    assert rotsq.variant_solid3d("current") is program
    assert rotsq.variant_solid3d("program") is not program
    assert rotsq.variant_solid3d("cutcell") is not program


def test_cutcell_copy_is_identical_to_the_program_on_a_rectangle():
    """!
    @brief Without an outline the copy takes the program's rectangular branch: the same temperature field to the last digit.
    @return None.
    """
    p = Problem.new(24.0, 24.0, 2, h_side=300.0).add_full_copper()
    p.add_heater(1, 1.5, rect=(10, 10, 14, 14), name="U")
    a = rotsq.variant_solid3d("program").solve_steady(p, cell_mm=1.0)
    b = rotsq.variant_solid3d("cutcell").solve_steady(p, cell_mm=1.0)
    assert np.array_equal(a.T, b.T)


def test_cutcell_copy_closes_the_energy_balance_on_a_turned_square():
    """!
    @brief The heat to the air through the faces and the edge equals the power on a square turned by 33 degrees (no heat leaks into the cells off the board).
    @return None.
    """
    p = rotsq.board(33, 2000.0, side_mm=20.0, box_mm=30.0, part_mm=3.0, part_angle_deg=33.0)
    r = rotsq.variant_solid3d("cutcell").solve_steady(p, cell_mm=0.5)
    assert abs(sum(r.power_out.values()) / r.power_in - 1.0) < 1e-9


def test_shift_invariance_is_restored_by_the_cut_cells():
    """!
    @brief A 20 mm square at 2000 W/m2K edge coefficient moved by half a cell: the program changes the answer by several kelvin, the copy by under half a kelvin.
    @return None.
    """
    prog, cut = rotsq.variant_solid3d("program"), rotsq.variant_solid3d("cutcell")
    c = 0.5
    base, moved = rotsq.board(0, 2000.0, 20.0, 30.0, 3.0), rotsq.board(0, 2000.0, 20.0, 30.0, 3.0, shift_mm=(0.5 * c, 0.5 * c))
    d_prog = prog.solve_steady(moved, cell_mm=c).t_max - prog.solve_steady(base, cell_mm=c).t_max
    d_cut = cut.solve_steady(moved, cell_mm=c).t_max - cut.solve_steady(base, cell_mm=c).t_max
    assert d_prog > 3.0
    assert abs(d_cut) < 0.5


def test_disc_cutcell_is_closer_to_the_axisymmetric_reference_than_the_program():
    """!
    @brief On a round board (every edge cell cut) at 1000 W/m2K the copy is within 1 % of the (r, z) reference and the program is not.
    @return None.
    """
    p = rotsq.disc_board(40.0, 3.0, 1000.0)
    ref = axisym3d.solve_disc(0.02, 0.003, 2.0, axisym3d.slabs_of(p), p.board.h_top, p.board.h_bottom, 1000.0, n_rings=2000)["t_top_max"]
    amb = p.board.ambient
    prog = rotsq.variant_solid3d("program").solve_steady(p, cell_mm=1.0).t_max - amb
    cut = rotsq.variant_solid3d("cutcell").solve_steady(p, cell_mm=1.0).t_max - amb
    assert abs(cut - ref) < 0.01 * ref
    assert abs(prog - ref) > 0.03 * ref


# --- Added by the review: an independent reference for the square and the footprint of a turned part

def test_square_reference_is_the_program_rectangle_on_cells_the_edge_does_not_cut():
    """!
    @brief The independent quarter-board solver (`lib/square3d.py`, nothing of the program) and the program's rectangular 3D branch are the same
           discretisation when no cell is cut: equal to rounding, so the ladder of the independent solver extrapolates the program's own continuum.
    @return None.
    """
    import square3d
    from pcbthermal import solid3d
    p = Problem.new(20.0, 20.0, 2, h_side=2000.0).add_full_copper()
    p.add_heater(1, 2.0, rect=(8, 8, 12, 12), name="U")
    b = p.board
    # The independent solver has one slab per gap and layer, as the 2.5.x program (read from the tag v2.5.1): equal to rounding. The 2.6.0 solid (feature/solid3d-slabs-by-thickness)
    # cuts the gap into slabs by thickness and reads 61.107 K where the 2.5.x one and this solver read 61.619 K (-0.83 %); that difference is the slab item, stated here.
    prog = rotsq.variant_solid3d("program").solve_steady(p, cell_mm=1.0).t_max - b.ambient
    assert abs(solid3d.solve_steady(p, cell_mm=1.0).t_max - b.ambient - prog) / prog < 0.012
    ref = square3d.solve_quarter(0.02, 0.004, 2.0, axisym3d.slabs_of(p), b.h_top, b.h_bottom, 2000.0, 10)
    assert abs(ref["t_centre"] - prog) < 1e-9 * prog
    assert abs(ref["balance"] - 1.0) < 1e-9


def test_square_reference_series_circuit_and_second_order():
    """!
    @brief With insulated sides and the power over the whole face the quarter solver is the one-dimensional series circuit; with a part it
           converges as the square of the cell (the Richardson step of the study is justified).
    @return None.
    """
    import square3d
    p = rotsq.board(0, 0.0, side_mm=20.0, box_mm=30.0, part_mm=3.0)
    slabs = axisym3d.slabs_of(p)
    full = square3d.solve_quarter(0.02, 0.02, 2.0, slabs, 10.0, 25.0, 0.0, 4)
    r_down = sum(dz / kz for dz, _, kz in slabs[1:-1]) + 0.5 * slabs[0][0] / slabs[0][2] + 0.5 * slabs[-1][0] / slabs[-1][2] + 1.0 / 25.0
    g_top = 1.0 / (1.0 / 10.0 + slabs[0][0] / (2.0 * slabs[0][2]))
    assert abs(full["t_centre"] - (2.0 / 0.02 ** 2) / (g_top + 1.0 / r_down)) < 1e-6 * full["t_centre"]   # direct solve of a stiff matrix (copper beside films)
    t = [square3d.solve_quarter(0.02, 0.004, 2.0, slabs, 10.0, 15.0, 2000.0, n)["t_centre"] for n in (10, 20, 40)]
    ratio = (t[0] - t[1]) / (t[1] - t[2])
    assert 3.0 < ratio < 5.0


def test_footprint_of_a_part_turned_45_degrees_is_short_on_4_by_4_samples():
    """!
    @brief The 3D solid samples the footprint of a part on 4 x 4 points per cell (the FVM on 8 x 8): a 3 mm part turned by 45 degrees keeps
           only 97.4 % of its area at 0.25 mm cells, which pushes power to the centre (+0.23 K on the 20 mm board of README 4, README 9.3).
    @return None.
    """
    poly = np.array(rotsq.turned_square(3.0, 45.0, (10.0, 10.0))) / 1000.0
    area = geometry.polygon_area(poly)
    c4 = geometry.coverage_fraction(poly, 80, 80, 0.25e-3, 0.25e-3, 4).sum() * 0.0625e-6
    c8 = geometry.coverage_fraction(poly, 80, 80, 0.25e-3, 0.25e-3, 8).sum() * 0.0625e-6
    assert c4 < 0.98 * area
    assert abs(c8 - area) < abs(c4 - area)
    # since 2.4.5 the program samples the footprint 8 x 8 itself (the old 4 x 4 line is gone)
    assert geometry.BOARD_SAMPLES == 8
    assert rotsq.VARIANTS["program_src8"] == []
