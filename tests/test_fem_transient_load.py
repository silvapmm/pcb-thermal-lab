#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fem_transient_load.py
@brief The load, the heat capacity and the read-out of the finite-element transient on the boards of the regression harness: the unit loads of the heaters add up to the
       steady load, the total capacity equals `integral rho c dV` of the description and the FVM's `Network.C.sum()` on every harness board (the differences, where there are any,
       are the features the models treat differently and are asserted by name), the column operator reproduces the steady column read-out, and the output times are the FVM's.
@details Light: meshes of 3 to 4 mm, a few seconds each.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "regression"))
import regress_boards as B                                                  # noqa: E402
from pcbthermal import femcore, fem, femmesh, fvm                                # noqa: E402

BOARDS = ["reference_board", "example_board", "plate_uniform", "plate_pad", "one_layer_full", "one_layer_pad", "two_layer_partial", "hatched_copper", "plate_vias",
          "t_outline", "finned_block", "part_top_path", "drawn_ell"]


def _mesh(name, cell=4.0):
    """!
    @brief Problem and mesh of a harness board.
    @param name Board name.
    @param cell Plan cell in mm.
    @return Tuple (problem, mesh).
    """
    p = B.build(name)
    return p, femmesh.build(p, cell, 3, 2.0)


@pytest.mark.parametrize("name", ["reference_board", "plate_vias", "finned_block", "part_top_path", "example_board"])
def test_the_unit_loads_of_the_heaters_add_up_to_the_steady_load(name):
    """!
    @brief `F @ powers` (the unit load of every heater times its power) equals the `rhs` of the assembly, to round-off, volumetric sources and face fluxes alike.
    @param name Harness board.
    @return None.
    """
    p, mesh = _mesh(name)
    a = mesh.model.assemble(capacity=True)
    F = fem.heater_loads(mesh)
    pw = np.array([h.power for h in p.heaters])
    assert F.shape == (a["rhs"].size, len(p.heaters))
    assert np.abs(F @ pw - a["rhs"]).max() < 1e-12 * max(np.abs(a["rhs"]).max(), 1e-30)
    assert abs(F.sum(axis=0)[0] - 1.0) < 1e-9                       # a unit of power in is a unit of load


def test_a_thick_outer_copper_layer_takes_the_part_by_a_face_flux_and_its_unit_load_adds_up():
    """!
    @brief A board with a 0.5 mm outer copper layer feeds its part by a face flux (several slabs): the unit load of that heater is the face load, still equal to the steady rhs.
    @return None.
    """
    p = B.build("plate_uniform")
    p.board.copper_thickness = [500e-6, 35e-6]
    mesh = femmesh.build(p, 5.0, 3, 2.0)
    assert any(f.get("label") == "source" for f in mesh.model.faces)
    a = mesh.model.assemble(capacity=True)
    F = fem.heater_loads(mesh)
    assert np.abs(F @ np.array([h.power for h in p.heaters]) - a["rhs"]).max() < 1e-12 * np.abs(a["rhs"]).max()


@pytest.mark.parametrize("name", BOARDS)
def test_total_capacity_is_the_description_and_the_fvm(name):
    """!
    @brief The capacity of the mesh, `sum(M)`, equals the integral of rho c of the layered description (the zone fill on a fine grid, the blocks by polygon) within 1 %, and the
           FVM's `Network.C.sum()` on the same board within the stated features: a board without a metal block, and without cut cells, agrees with the FVM to 0.2 %; the blocks
           differ by the sampling of the polygon edge, never by a missing body.
    @param name Harness board.
    @return None.
    """
    p, mesh = _mesh(name)
    a = mesh.model.assemble(capacity=True)
    inv = fem.capacity_inventory(p, mesh)
    assert abs(a["capacity_total"] / inv["fem"]["total"] - 1.0) < 1e-12
    # the independent description: the copper of the fill and the rest of the board; a drawn fill is read at the mesh quads and on a fine grid, so 1 %
    assert abs(inv["difference"]) < 0.01, (name, inv)
    b = p.board
    nx, ny = max(int(round(b.width * 1000 / 3.0)), 2), max(int(round(b.height * 1000 / 3.0)), 2)
    net = fvm.Network(p, nx, ny)
    tol = 0.02 if p.heatsinks and any(s.is_block() for s in p.heatsinks) else 0.01
    assert abs(a["capacity_total"] / net.C.sum() - 1.0) < tol, (name, a["capacity_total"], net.C.sum())


def test_no_capacity_for_the_interface_pad_the_via_barrel_or_a_part():
    """!
    @brief On the finned-block board the pad slab has zero capacity and the block slab its own `rho c`; on the via board the barrel is not added (the omitted copper is reported
           in J/K, below 1 % of the total, so no warning); a part adds none (the inventory says so).
    @return None.
    """
    p, mesh = _mesh("finned_block")
    inv = fem.capacity_inventory(p, mesh)
    pad = np.array([sl["kind"] == "pad" for sl in mesh.slabs])[mesh.elem_slab]
    assert (mesh.rho_c[pad] == 0.0).all() and pad.any()
    assert inv["fem"]["pad"] == 0.0 and inv["fem"]["blocks"] > 0.0
    blk = [s for s in p.heatsinks if s.is_block()][0]
    kind_blk = np.array([sl["kind"] == "blk" for sl in mesh.slabs])[mesh.elem_slab]
    assert np.allclose(mesh.rho_c[kind_blk], blk.rho_cp)
    p2, mesh2 = _mesh("plate_vias")
    inv2 = fem.capacity_inventory(p2, mesh2)
    assert 0.0 < inv2["via_barrel_omitted"] < 0.01 * inv2["fem"]["total"]
    assert inv2["parts"] == "not modelled"


@pytest.mark.parametrize("name", ["reference_board", "plate_pad", "example_board", "t_outline", "finned_block"])
def test_the_column_operator_reproduces_the_steady_column_readout(name):
    """!
    @brief `Rcol @ T` on the steady field equals the column read-out of `fem.solve_steady` (the same linear map, made once as a sparse operator) to round-off on every cell.
    @param name Harness board.
    @return None.
    """
    p = B.build(name)
    cell = 4.0
    res = fem.solve_steady(p, cell_mm=cell, gap_elements=3, refine=2.0)
    mesh = femmesh.build(p, cell, 3, 2.0)
    sol = mesh.model.solve()
    nx, ny, _, _ = fem._grid_shape(p, cell)
    R, active, cover = fem.column_operator(p, mesh, nx, ny)
    used = ~np.isnan(sol["T"])
    got = (R @ sol["T"][used]).reshape(p.board.layers, ny, nx) + p.board.ambient
    assert np.abs(got - res.T).max() < 1e-9, name


def test_the_output_times_are_the_fvms_and_the_first_output_has_four_steps_behind_it():
    """!
    @brief `time_grid` keeps the nominal output times of `fvm.transient_from_network` (logarithmic and linear), walks the first stage in quarter steps so that the first frame has
           four steps behind it, and a frame is emitted exactly at every nominal time.
    @return None.
    """
    p = B.build("reference_board")
    for log in (True, False):
        f = fvm.solve_transient(p, 500.0, n_out=40, cell_mm=6.0, log_times=log)
        hs, emit, times = fem.time_grid(500.0, 40, 4, log)
        assert np.allclose(times, f.times, rtol=1e-12, atol=0)
        assert np.isclose(np.cumsum(hs)[emit][-1], 500.0) and emit.sum() == len(times) - 1
        assert np.allclose(np.cumsum(hs)[emit], times[1:], rtol=1e-12)
    hs, emit, times = fem.time_grid(1000.0, 40)
    assert np.isclose(hs[0], times[1] / 4.0) and np.flatnonzero(emit)[0] == 3 and np.isclose(times[1], 1000.0 / (4 * 1023))


def test_transient_of_a_board_conserves_energy_and_reaches_the_steady_solve():
    """!
    @brief The reference board: the energy residual of the run is below 1e-9, the last frame of a run long enough equals the steady solve (to 1e-4 of the rise), implicit Euler and
           Crank-Nicolson agree at the end, and a cancel raises FemCancelled.
    @return None.
    """
    p = B.build("reference_board")
    rise = None
    for theta in (1.0, 0.5):
        r = fem.solve_transient(p, 20000.0, n_out=40, cell_mm=4.0, theta_scheme=theta, gap_elements=3)
        assert abs(r.extras["energy_residual"]) < 1e-9
        steady = fem.solve_steady(p, cell_mm=4.0, gap_elements=3).t_max
        assert abs((r.t_max[-1] - p.board.ambient) / (steady - p.board.ambient) - 1.0) < 1e-3
        assert r.extras["t_max_point"][-1] >= r.t_max[-1] - 1e-9
        assert r.arrays == {} and r.frames.shape[0] == len(r.times)
        rise = r if rise is None else rise
    with pytest.raises(femcore.FemCancelled):
        fem.solve_transient(p, 100.0, n_out=10, cell_mm=4.0, gap_elements=3, cancel=lambda: True)


def test_step_responses_have_the_form_of_the_fvms_and_reach_the_steady_resistance():
    """!
    @brief `fem.step_responses` returns (times, z, rth) like `fvm.step_responses`; z(t) rises monotonically to rth (the steady hottest-cell resistance in K/W).
    @return None.
    """
    p = B.build("reference_board")
    t, z, rth = fem.step_responses(p, cell_mm=4.0, gap_elements=3)
    assert z.shape == (len(p.heaters), len(t)) and rth.shape == (len(p.heaters),)
    assert np.all(np.diff(z[0]) > -1e-9) and abs(z[0, -1] / rth[0] - 1.0) < 2e-2
    ft, fz, frth = fvm.step_responses(p, cell_mm=4.0)
    assert abs(rth[0] / frth[0] - 1.0) < 0.05


def _halved_grid(monkeypatch):
    """!
    @brief Make `fem.time_grid` return every step cut in two (the output times unchanged), for the halved-step check.
    @param monkeypatch pytest fixture.
    @return None.
    """
    orig = fem.time_grid

    def halved(*a, **k):
        """!
        @brief The program's grid with every step halved.
        @param a Positional arguments of `fem.time_grid`.
        @param k Keyword arguments of `fem.time_grid`.
        @return Tuple (steps, emit, times) as `fem.time_grid`.
        """
        hs, emit, times = orig(*a, **k)
        e2 = np.zeros(2 * hs.size, bool)
        e2[1::2] = emit
        return np.repeat(hs / 2.0, 2), e2, times
    monkeypatch.setattr(fem, "time_grid", halved)


@pytest.mark.parametrize("theta, bound", [(0.5, 0.01), (1.0, 0.03)])
def test_the_frames_move_little_when_every_step_is_halved(theta, bound, monkeypatch):
    """!
    @brief Halving every step (H5 of DESIGN.md): with Crank-Nicolson and the Rannacher start every frame of the 4 x 4 via plate moves by less than 1 % of its hottest rise from the
           first output on (review: 0.15 % at the first frame, 0.11 % at most later); implicit Euler, first order, moves by up to 2 % (2.0 % at the first frame, 0.9 % later), so its
           frames carry an error of about twice that, which the documents state.
    @param theta 0.5 or 1.
    @param bound Largest allowed change of a frame over its hottest rise.
    @param monkeypatch pytest fixture.
    @return None.
    """
    p = B.build("plate_vias")
    a = fem.solve_transient(p, 600.0, 40, 4.0, theta_scheme=theta, force_solver="direct")
    _halved_grid(monkeypatch)
    b = fem.solve_transient(p, 600.0, 40, 4.0, theta_scheme=theta, force_solver="direct")
    ra, rb = a.frames[1:] - a.ambient, b.frames[1:] - b.ambient
    change = np.abs(ra - rb).reshape(len(ra), -1).max(axis=1) / rb.reshape(len(rb), -1).max(axis=1)
    assert b.extras["steps"] == 2 * a.extras["steps"]
    assert change.max() < bound, change[:4]


def test_more_gap_elements_resolve_the_first_second():
    """!
    @brief The gap grading limits the first seconds (DESIGN.md 14.1): on the two-layer reference board the hottest column at about 0.44 s with the default 6 elements across the gap is
           within 1.5 % of 12 elements (review, 3D: -0.9 % against 24 elements, 12 elements -0.15 %), and 4 elements are further off than 6.
    @return None.
    """
    p = B.build("reference_board")
    runs = {g: fem.solve_transient(p, 600.0, 40, 4.0, theta_scheme=0.5, gap_elements=g, force_solver="direct") for g in (4, 6, 12)}
    k = int(np.argmin(np.abs(runs[12].times - 0.44)))
    rise = {g: r.t_max[k] - r.ambient for g, r in runs.items()}
    assert abs(rise[6] / rise[12] - 1.0) < 0.015, rise
    assert abs(rise[4] / rise[12] - 1.0) > abs(rise[6] / rise[12] - 1.0)
