#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_symmetric_lu.py
@brief Tests of the symmetric-mode LU of the thermal matrices (`fvm.lu_factor`): equality with the default mode on random SPD graphs and on boards with vias, a metal block, an
       outline, laminate sub-gaps and imported copper; positive definiteness of the matrices; the fallback paths (asymmetric matrix, failing factorisation, bad residual);
       the speed of a via-dense plate (the case that made the default mode slow); the transient step matrices.
@details Speed and memory only: the temperatures must agree with the default mode to rounding (the tests use 1e-9 K).
"""

import logging
import time

import numpy as np
import pytest
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from pcbthermal import Problem, SolverOptions, copper, fvm, simulate


def _random_spd(n, seed):
    """!
    @brief A random sparse conductance matrix: a connected random graph Laplacian plus a positive diagonal (symmetric positive definite).
    @param n Number of nodes.
    @param seed Seed of the random generator.
    @return scipy.sparse.csc_matrix.
    """
    rng = np.random.default_rng(seed)
    a = sp.random(n, n, density=4.0 / n, random_state=rng, format="csr")
    a = a + a.T + sp.diags(np.ones(n - 1), 1) + sp.diags(np.ones(n - 1), -1)   # chain so that the graph is connected
    a.data[:] = 0.1 + np.abs(a.data)
    lap = sp.diags(np.asarray(a.sum(axis=1)).ravel()) - a
    return (lap + sp.diags(rng.uniform(0.01, 1.0, n))).tocsc()


@pytest.mark.parametrize("seed", range(5))
def test_random_spd_graphs_agree_with_the_default_mode(seed):
    """!
    @brief The symmetric factorisation solves a random SPD graph to the same answer as the default mode.
    @param seed Seed of the random matrix.
    @return None.
    """
    A = _random_spd(400, seed)
    b = np.random.default_rng(100 + seed).normal(size=400)
    x_sym = fvm.lu_factor(A).solve(b)
    x_def = spla.splu(A, permc_spec=fvm.ORDERING).solve(b)
    assert np.abs(x_sym - x_def).max() < 1e-10 * max(np.abs(x_def).max(), 1.0)


def _boards():
    """!
    @brief Small boards that exercise the matrix features: vias, a metal block, an outline, patterned copper (laminate sub-gaps) and imported copper.
    @return List of (name, Problem).
    """
    out = []
    p = Problem.new(30, 30, layers=2, thickness_mm=1.6, copper_um=35, h_top=10, h_bottom=15, h_side=10)
    p.add_full_copper()
    p.add_heater(1, 3.0, rect=(12, 12, 18, 18))
    p.add_via_array((11, 11, 19, 19), 8, 8, diameter=0.3)
    out.append(("vias", p))
    p = Problem.new(30, 30, layers=2, thickness_mm=1.6, copper_um=35, h_top=10, h_bottom=15, h_side=10)
    p.add_zone(1, rect=(5, 5, 25, 25), fill=1.0)
    p.add_zone(2, rect=(0, 0, 30, 30), fill=0.6)
    p.add_heater(1, 2.0, rect=(12, 12, 18, 18))
    p.add_via_array((13, 13, 17, 17), 5, 5, diameter=0.3)           # vias over partial copper: laminate sub-gaps and the via couplings together
    out.append(("patterned_vias", p))
    p = Problem.new(40, 30, layers=2, thickness_mm=1.6, copper_um=35, h_top=10, h_bottom=15, h_side=10)
    p.add_full_copper()
    p.add_heater(1, 2.0, rect=(8, 8, 14, 14))
    p.add_heatsink(2, 20.0, rect=(5, 5, 17, 17), thickness_mm=3.0)
    out.append(("block", p))
    p = Problem.new(40, 40, layers=2, thickness_mm=1.6, copper_um=35, h_top=10, h_bottom=15, h_side=10)
    p.add_full_copper()
    p.add_heater(1, 2.0, rect=(10, 10, 16, 16))
    p.set_outline([(0, 0), (40, 0), (40, 15), (15, 15), (15, 40), (0, 40)])
    out.append(("outline", p))
    p = Problem.new(12, 12, layers=2, thickness_mm=1.6, copper_um=35, h_top=10, h_bottom=10, h_side=None)
    p.add_heater(1, 1.0, rect=(3.6, 3.6, 8.4, 8.4))
    n = 120
    stripes = np.zeros((n, n), np.uint8)
    for j in range(0, n, 9):
        stripes[:, j:j + 4] = 255
    p.imported = copper.imported_from_rasters([stripes, np.full((n, n), 255, np.uint8)], 0.1, "faces", kind="coverage")
    out.append(("imported", p))
    return out


@pytest.mark.parametrize("model", ["fvm", "fdm"])
def test_boards_agree_with_the_default_mode(model, monkeypatch):
    """!
    @brief Steady temperatures with the symmetric mode equal those of the default mode to rounding on boards with vias, a block, an outline, laminate gaps and imported copper.
    @param model Model key, "fvm" or "fdm".
    @param monkeypatch pytest fixture.
    @return None.
    """
    for name, p in _boards():
        fields = {}
        for sym in (False, True):
            monkeypatch.setattr(fvm, "SYMMETRIC_LU", sym)
            fields[sym] = np.asarray(simulate(p, SolverOptions(models=(model,), cell_mm=1.0)).results[model].T, float)
        d = np.nanmax(np.abs(fields[True] - fields[False]))
        assert d < 1e-9, (name, d)


def test_thermal_matrices_are_symmetric_positive_definite():
    """!
    @brief The matrices K of the boards (via couplings, block, outline, gaps, imported copper) are symmetric with a positive diagonal and a positive smallest eigenvalue.
    @return None.
    """
    for name, p in _boards():
        cell = 2.0 if name != "imported" else 1.0
        nx, ny = int(round(p.board.width * 1000.0 / cell)), int(round(p.board.height * 1000.0 / cell))
        net = fvm.Network(p, nx, ny)
        K = net.K.tocsc()
        assert abs(K - K.T).max() <= 1e-12 * abs(K).max(), name
        assert K.diagonal().min() > 0.0, name
        lam = np.linalg.eigvalsh(K.toarray()).min() if K.shape[0] < 6000 else spla.eigsh(K, k=1, sigma=-1e-6, which="LM", return_eigenvectors=False)[0]
        assert lam > 0.0, (name, lam)


def test_fallback_when_the_matrix_is_not_symmetric(monkeypatch):
    """!
    @brief An asymmetric matrix is factorised in the default mode only (the symmetric mode is not tried) and solved correctly.
    @param monkeypatch pytest fixture.
    @return None.
    """
    real = spla.splu
    calls = []

    def spy(A, *args, **kw):
        """!
        @brief splu that records its keyword arguments.
        @param A Matrix.
        @param args Positional arguments.
        @param kw Keyword arguments.
        @return SuperLU object.
        """
        calls.append(kw)
        return real(A, *args, **kw)

    monkeypatch.setattr(fvm.spla, "splu", spy)
    A = (_random_spd(200, 1) + sp.diags(np.ones(199) * 0.3, 1)).tocsc()
    b = np.ones(200)
    x = fvm.lu_factor(A).solve(b)
    assert len(calls) == 1 and not calls[0].get("options")              # the symmetric mode is not even tried
    assert np.linalg.norm(A @ x - b) < 1e-10 * np.linalg.norm(b)


def test_fallback_when_the_symmetric_factorisation_fails(monkeypatch, caplog):
    """!
    @brief A symmetric-mode factorisation that raises is logged and replaced by the default factorisation.
    @param monkeypatch pytest fixture.
    @param caplog pytest fixture.
    @return None.
    """
    real = spla.splu
    calls = []

    def flaky(A, *args, **kw):
        """!
        @brief splu that fails when called with the symmetric options.
        @param A Matrix.
        @param args Positional arguments.
        @param kw Keyword arguments.
        @return SuperLU object.
        """
        calls.append(kw)
        if kw.get("options"):
            raise RuntimeError("forced failure")
        return real(A, *args, **kw)

    monkeypatch.setattr(fvm.spla, "splu", flaky)
    A = _random_spd(300, 2)
    b = np.arange(300, dtype=float)
    with caplog.at_level(logging.WARNING, logger="pcbthermal.fvm"):
        x = fvm.lu_factor(A).solve(b)
    assert len(calls) == 2 and "failed" in caplog.text
    assert np.linalg.norm(A @ x - b) < 1e-9 * np.linalg.norm(b)


def test_residual_guard_rejects_a_bad_symmetric_factor(monkeypatch, caplog):
    """!
    @brief When the probe solve of the symmetric factor is worse than the tolerance, the default factorisation is used and a warning is logged.
    @param monkeypatch pytest fixture.
    @param caplog pytest fixture.
    @return None.
    """
    monkeypatch.setattr(fvm, "SYMMETRIC_LU_TOLERANCE", -1.0)         # no residual can meet a negative tolerance
    A = _random_spd(300, 3)
    b = np.ones(300)
    with caplog.at_level(logging.WARNING, logger="pcbthermal.fvm"):
        x = fvm.lu_factor(A).solve(b)
    assert "residual" in caplog.text
    assert np.linalg.norm(A @ x - b) < 1e-9 * np.linalg.norm(b)


def test_transient_step_matrices_agree(monkeypatch):
    """!
    @brief The step responses (implicit steps with the capacities) are the same in both modes.
    @param monkeypatch pytest fixture.
    @return None.
    """
    from pcbthermal.api import step_response
    name, p = _boards()[0]
    out = {}
    for sym in (False, True):
        monkeypatch.setattr(fvm, "SYMMETRIC_LU", sym)
        sr = step_response(p, "fvm", SolverOptions(models=("fvm",), cell_mm=2.0))
        out[sym] = np.concatenate([np.ravel(np.asarray(z, float)) for z in sr.z])
    assert np.abs(out[True] - out[False]).max() < 1e-9


def test_via_dense_plate_is_fast():
    """!
    @brief Smoke test: a plate with a dense via array at a 0.5 mm cell solves in seconds.
    @details 60 mm plate, 30 x 30 vias in 40 mm at a 0.5 mm cell: about 0.5 s in BOTH modes (review: 0.46 s each; 40 x 40 vias 0.18 s each). The cases where the
             default mode is slow are larger (150 mm plates, 400 to 1 600 vias in 60 to 90 mm at 0.5 mm: 14 to 214 s against 1.2 to 4.6 s) and too heavy for the battery;
             that the symmetric mode is actually used is held by test_symmetric_mode_is_used_on_board_matrices.
    @return None.
    """
    p = Problem.new(60, 60, layers=2, thickness_mm=1.6, copper_um=35, h_top=10, h_bottom=15, h_side=10)
    p.add_full_copper()
    p.add_heater(1, 5.0, rect=(26, 26, 34, 34))
    p.add_via_array((10, 10, 50, 50), 30, 30, diameter=0.3)
    t0 = time.perf_counter()
    r = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"]
    assert time.perf_counter() - t0 < 20.0
    assert np.isfinite(r.t_max)


def test_symmetric_mode_is_used_on_board_matrices(monkeypatch):
    """!
    @brief On the board matrices the symmetric factor is the one kept (no fallback), it exchanged no row and all its pivots are positive (an LDL^T certificate that
           the matrix is positive definite, also with the positive off-diagonals of the via couplings).
    @param monkeypatch pytest fixture.
    @return None.
    """
    real = spla.splu
    calls = []

    def spy(A, *args, **kw):
        """!
        @brief splu that records its keyword arguments.
        @param A Matrix.
        @param args Positional arguments.
        @param kw Keyword arguments.
        @return SuperLU object.
        """
        calls.append(kw)
        return real(A, *args, **kw)

    monkeypatch.setattr(fvm.spla, "splu", spy)
    for name, p in _boards():
        net = fvm.Network(p, int(round(p.board.width * 1000.0)), int(round(p.board.height * 1000.0)))
        for A in (net.K, sp.diags(net.C.ravel() / 0.01) + 0.5 * net.K):
            calls.clear()
            lu = fvm.lu_factor(A)
            assert len(calls) == 1 and calls[0].get("options") == {"SymmetricMode": True}, name
            assert np.array_equal(lu.perm_r, lu.perm_c), name
            assert lu.U.diagonal().min() > 0.0, name


def test_probe_catches_a_breakdown_without_pivoting(caplog):
    """!
    @brief A symmetric matrix with a positive but tiny diagonal and large couplings breaks down without pivoting; the probe residual catches it and the default
           factorisation gives the right answer.
    @param caplog pytest fixture.
    @return None.
    """
    blk = np.array([[1e-14, 1.0], [1.0, 1e-14]])
    A = sp.csc_matrix(np.kron(np.eye(50), blk))                      # 50 independent 2 x 2 blocks
    b = np.arange(1.0, 101.0)
    with caplog.at_level(logging.WARNING, logger="pcbthermal.fvm"):
        x = fvm.lu_factor(A).solve(b)
    assert "residual" in caplog.text
    assert np.linalg.norm(A @ x - b) < 1e-12 * np.linalg.norm(b)
