#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fem_thin_copper_source.py
@brief A part on an outer copper layer of any thickness enters the finite-element model through its face (fix of the 2.8.0 defect: on 35 um copper the volumetric source read half of the surface term).
@details Cases: a one-dimensional board (the exact term q t / (2 k)), a 4 x 4 mm part against the independent finite volumes of `tests/helpers/layered3d.py`, the column of the
         tree before the fix (development db6244b1, measured numbers), the energy balance, the unit load of the transient, and the steady limit of the transient.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))
import layered3d as L3                                         # noqa: E402

from pcbthermal import analysis, fem, femmesh                  # noqa: E402
from pcbthermal.api import SolverOptions, simulate             # noqa: E402
from pcbthermal.model import Materials, Problem                # noqa: E402

K_LAM = 0.3


def board(full):
    """!
    @brief The board of the study of the fix: 20 x 20 mm, two layers of 35 um copper on 1.6 mm, insulated top and sides, a film of 10 W/m2K below.
    @param full True: a 4 W part over the whole top face (one-dimensional); False: a 1 W part of 4 x 4 mm at the centre.
    @return Problem.
    """
    p = Problem.new(20.0, 20.0, layers=2, thickness_mm=1.6, copper_um=35, ambient=25.0, h_top=1e-6, h_bottom=10.0, h_side=None,
                    materials=Materials(k_fr4_through=K_LAM, k_fr4_inplane=K_LAM))
    p.add_full_copper(layers=None)
    if full:
        p.add_heater(1, 4.0, rect=(0.0, 0.0, 20.0, 20.0), name="S")
    else:
        p.add_heater(1, 1.0, rect=(8.0, 8.0, 12.0, 12.0), name="S")
    return p


def term_and_column(p, cell=2.0):
    """!
    @brief The FEM column maximum under the part and the surface minus column term.
    @param p Problem.
    @param cell Plan cell in mm.
    @return tuple (column in degC, term in K, SteadyResult).
    """
    r = simulate(p, SolverOptions(models=("fem",), cell_mm=cell)).results["fem"]
    col = analysis.heater_stats(r, p)[0]["t_max"]
    surf = analysis.surface_stats(r, p.heaters[0].polygon, 0, p.board.outline)[0]
    return col, surf - col, r


def test_a_thin_copper_part_is_a_face_flux():
    """!
    @brief The mesh of a 35 um board carries the part as a face flux labelled 'source' and no volumetric source.
    @return None.
    """
    mesh = femmesh.build(board(False), 2.0, 3, 2.0)
    assert any(f.get("label") == "source" for f in mesh.model.faces)
    assert mesh.heater_flux[0] is not None and mesh.heater_q[0] is None
    assert not mesh.model.q.any()


def test_one_dimensional_board_reads_the_exact_term():
    """!
    @brief A part over the whole face of an insulated board: every watt crosses the 35 um copper, so surface minus column is q t / (2 k), to 1e-6 relative at every cell.
    @return None.
    """
    p = board(True)
    bound = 4.0 / 400e-6 * 35e-6 / (2.0 * p.board.materials.k_copper)
    for cell in (5.0, 2.0):
        _, term, r = term_and_column(p, cell)
        assert term == pytest.approx(bound, rel=1e-6)
        assert abs(r.balance_error) < 1e-9 and r.power_in == pytest.approx(4.0, rel=1e-9)   # the energy balance stays exact


def test_part_of_4_mm_agrees_with_the_independent_solver_and_not_with_the_old_volume_source():
    """!
    @brief The 4 x 4 mm, 1 W part: the independent 3D finite volumes (8 sub-slabs in the copper) give a term of 2.00 mK (0.70 of q t / 2k); the FEM, with one element through the
           copper, reads 1.35 mK at 2 mm (0.48) and 1.58 mK at 0.5 mm (0.55): within 0.6 to 1.05 of the reference; the 2.8.0 volume source read 0.12 to 0.16 mK.
    @return None.
    """
    p = board(False)
    k = p.board.materials.k_copper
    ref = L3.solve(1e-3, 20, 20, [(35e-6, k, 8), (1.53e-3, K_LAM, 4), (35e-6, k, 2)], (8e-3, 8e-3, 12e-3, 12e-3), 1.0, 0.0, 10.0)
    dz = np.array(ref["dz"])
    col_map = np.tensordot(dz[:8] / dz[:8].sum(), ref["T"][:8], axes=(0, 0))
    m = ref["mask_source"]
    ref_term = float(ref["surface_top"][m].max() - col_map[m].max())
    assert ref_term == pytest.approx(1.995e-3, rel=2e-3)                           # the number of the study (tree development db6244b1)
    _, term, _ = term_and_column(p, 2.0)
    assert 0.6 * ref_term <= term <= 1.05 * ref_term
    assert term > 8.0 * 1.17e-4                                                    # the term of the volumetric source of 2.8.0 on this board (measured)


def test_the_column_moves_by_less_than_a_milli_kelvin():
    """!
    @brief The column under the part against the numbers of the tree before the fix (development db6244b1, cell 2 mm): 1076.001026 degC one-dimensional, 299.588221 degC for the 4 mm part.
    @return None.
    """
    for full, before in ((True, 1076.001026), (False, 299.588221)):
        col, _, r = term_and_column(board(full))
        assert abs(col - before) < 1e-3
        assert abs(r.balance_error) < 1e-9


def test_unit_load_of_a_thin_copper_part_adds_up_to_the_steady_load():
    """!
    @brief `F @ powers` equals the steady `rhs` (to round-off) when the part is a face flux on 35 um copper, and the load carries the whole watt.
    @return None.
    """
    p = board(False)
    mesh = femmesh.build(p, 2.0, 3, 2.0)
    a = mesh.model.assemble(capacity=True)
    F = fem.heater_loads(mesh)
    assert np.abs(F @ np.array([h.power for h in p.heaters]) - a["rhs"]).max() < 1e-12 * np.abs(a["rhs"]).max()
    assert F.sum(axis=0)[0] == pytest.approx(1.0, abs=1e-9)


def test_the_transient_reaches_the_steady_column_on_thin_copper():
    """!
    @brief The power step of the FEM, run long, ends on the steady column of the same part (the same face load in both): within 1e-3 of the rise, and the capacity is not touched by the fix.
    @return None.
    """
    p = board(False)
    tr = fem.solve_transient(p, t_end=40000.0, n_out=20, cell_mm=2.0)
    st = fem.solve_steady(p, cell_mm=2.0)
    rise = st.t_max - st.ambient
    assert abs(tr.t_max[-1] - st.t_max) < 1e-3 * rise
    assert abs(tr.steady_t_max - st.t_max) < 1e-6 * rise


def test_a_bottom_layer_part_enters_through_the_bottom_face():
    """!
    @brief A part over the whole BOTTOM face of a one-dimensional board (layer 2 of 2, 35 um): the load is a face flux on the bottom face of the lowest copper slab, so
           q_dn leaves by the bottom film straight from the face and q_up crosses the bottom copper, the gap and the top copper: q_dn = q B / (1/h_bottom + B),
           B = 1/h_top + d/k_z + 2 t/k (the mirror of the closed form of tests/test_fem_model.py); the bottom surface minus the bottom column is q_up t / (2 k) and the top
           surface minus the top column is -q_up t / (2 k), to 1e-6 relative (added by the review: no board of the study had a part on the bottom layer).
    @return None.
    """
    p = Problem.new(20.0, 20.0, layers=2, thickness_mm=1.6, copper_um=35, ambient=25.0, h_top=30.0, h_bottom=12.0, h_side=None)
    p.add_full_copper(layers=None)
    P = 4.0
    p.add_heater(2, P, rect=(0.0, 0.0, 20.0, 20.0), name="B")
    mesh = femmesh.build(p, 5.0, 3, 2.0)
    assert mesh.heater_flux[0] is not None and mesh.heater_q[0] is None and not mesh.model.q.any()
    b = p.board
    k, t, d, kz = b.materials.k_copper, b.copper_thickness[1], b.gap_thicknesses()[0], b.gap_properties()[0][0]
    q = P / 4e-4
    B = 1.0 / b.h_top + d / kz + 2.0 * t / k
    q_dn = q * B / (1.0 / b.h_bottom + B)
    q_up = q - q_dn
    r = fem.solve_steady(p, cell_mm=5.0)
    assert abs(r.balance_error) < 1e-9 and r.power_in == pytest.approx(P, rel=1e-9)
    assert np.allclose(r.arrays["T_surface"][1], 25.0 + q_dn / b.h_bottom, rtol=1e-6, atol=0)
    assert np.allclose(r.arrays["T_surface"][0], 25.0 + q_up / b.h_top, rtol=1e-6, atol=0)
    term = q_up * t / (2.0 * k)
    assert float((r.arrays["T_surface"][1] - r.T[1]).mean()) == pytest.approx(term, rel=1e-6)
    assert float((r.arrays["T_surface"][0] - r.T[0]).mean()) == pytest.approx(-term, rel=1e-6)
    # The heat leaves by the bottom film mostly (the part sits on that face): the paths match the closed form
    assert r.power_out["bottom"] == pytest.approx(q_dn * 4e-4, rel=1e-6) and r.power_out["top"] == pytest.approx(q_up * 4e-4, rel=1e-6)


def test_an_interior_layer_part_keeps_the_volumetric_source():
    """!
    @brief A part on layer 2 of a four-layer board has no face to load: it stays a volumetric source in its copper slab (no 'source' face), and the power is exact.
    @return None.
    """
    p = Problem.new(20.0, 20.0, layers=4, thickness_mm=1.6, copper_um=35, ambient=25.0, h_top=10.0, h_bottom=10.0, h_side=None)
    p.add_full_copper(layers=None)
    p.add_heater(2, 2.0, rect=(8.0, 8.0, 12.0, 12.0), name="I")
    mesh = femmesh.build(p, 2.0, 3, 2.0)
    assert mesh.heater_flux[0] is None and mesh.heater_q[0] is not None
    assert not any(f.get("label") == "source" for f in mesh.model.faces)
    assert float(fem.heater_loads(mesh).sum()) == pytest.approx(1.0, rel=1e-12)
    r = fem.solve_steady(p, cell_mm=2.0)
    assert abs(r.balance_error) < 1e-9 and r.power_in == pytest.approx(2.0, rel=1e-9)
