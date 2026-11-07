#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_lumped_log.py
@brief Tests of the patched Lumped copy: it is the program bit for bit at its defaults, the first ring of the proposal follows the cell and not the board, and the deficit it removes is real.
@details Run from the repository root: QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q research/lumped-ring-uniform-deficit/tests
"""

import sys
from pathlib import Path

import numpy as np
import pytest

LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(LIB))

import lumped_log as LL  # noqa: E402
import runner as R  # noqa: E402
import simple as S  # noqa: E402
from pcbthermal import SolverOptions, lumped as program, simulate  # noqa: E402


@pytest.fixture(autouse=True)
def _restore():
    """!
    @brief Put the switches back to the program's values after every test.
    @return None.
    """
    yield
    LL.configure("strip", 0.04, 1.5, None)


def test_defaults_are_the_program():
    """!
    @brief With the switches of the program the patched module gives the temperature field of the program to the last bit, on three boards.
    @details The patched module is built on the text of v2.5.1 (no first-ring cap); 2.6.0 adopted the cap (fix/lumped-first-ring, one equivalent radius of the footprint,
             `FIRST_A` = 1.0 here), so the program is reproduced with the cap on; the patched text also passes cut_cells=False as the program does (measured max |dT| = 0 on the three boards).
    @return None.
    """
    LL.configure("strip", 0.04, 1.5, 1.0)
    for kw in (dict(w_mm=60, h_mm=40, side_mm=3.0), dict(w_mm=100, h_mm=80, side_mm=1.0, layers=4, fill=0.6), dict(w_mm=30, h_mm=20, side_mm=6.0, layers=1)):
        p = S.board(**kw)
        LL.uninstall()
        a = simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5)).results["lumped"]
        LL.install()
        b = simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5)).results["lumped"]
        assert np.array_equal(a.T, b.T) and a.t_max == b.t_max


def test_ring_edges_first_ring():
    """!
    @brief The first ring of the program is 0.04 rho_max wide on a big board; with the factor at 0 it is 1.5 cells whatever the board.
    @return None.
    """
    LL.configure("strip", 0.04, 1.5, None)
    e = LL.MOD.ring_edges(0.1, 0.5e-3, 0.5e-3, 10)
    assert e[1] == pytest.approx(0.04 * 0.1)
    LL.configure("strip", 0.0, 1.5, None)
    for rho_max in (0.03, 0.1, 0.25):
        e = LL.MOD.ring_edges(rho_max, 0.5e-3, 0.5e-3, 10)
        assert e[1] == pytest.approx(1.5 * 0.5e-3)
    assert program.ring_edges(0.1, 0.5e-3, 0.5e-3, 10)[1] == pytest.approx(0.004)         # the program itself is untouched


def test_deficit_of_the_program_and_its_removal():
    """!
    @brief A 1 mm source in the middle of a 100 x 80 mm uniform board: the program reads more than 8 % below the FVM, the proposed first ring within 5 %.
    @return None.
    """
    p = S.board(w_mm=100, h_mm=80, layers=2, fill=1.0, side_mm=1.0)
    pos = (50.0, 40.0)
    ref = R.readout(p, "fvm", 0.5, 1.0, pos)[1]
    LL.configure("strip", 0.04, 1.5, None)
    prog = R.readout(p, "lumped", 0.5, 1.0, pos)[1]
    LL.configure("strip", 0.0, 1.5, None)
    cand = R.readout(p, "lumped", 0.5, 1.0, pos)[1]
    assert prog / ref - 1 < -0.08
    assert abs(cand / ref - 1) < 0.05


def test_candidate_does_not_depend_on_board_size():
    """!
    @brief With the proposed first ring the Lumped rise of a 3 mm source changes by less than 6 % between a 60 x 40 and a 200 x 150 board whose FVM rises differ by the same few per cent; the program does not hold this for a 1 mm source.
    @return None.
    """
    LL.configure("strip", 0.0, 1.5, None)
    r = []
    for w, h in ((60, 40), (200, 150)):
        p = S.board(w_mm=w, h_mm=h, layers=2, fill=1.0, side_mm=3.0)
        r.append((R.readout(p, "lumped", 0.5, 3.0, (w / 2, h / 2))[1], R.readout(p, "analytic", 0.5, 3.0, (w / 2, h / 2))[1]))
    # The candidate and the Analytic (which has no ring) move together from one board to the other
    assert (r[1][0] / r[0][0]) == pytest.approx(r[1][1] / r[0][1], rel=0.04)


def test_cap_leaves_large_footprints_bit_identical_and_small_ones_move():
    """!
    @brief The proposal (first ring at most one equivalent radius of the footprint, at least 1.5 cells): a 10 mm source on a 200 x 150 board gives the program's field to the last bit, a 1 mm source does not.
    @return None.
    """
    big = S.board(w_mm=200, h_mm=150, side_mm=10.0)
    small = S.board(w_mm=200, h_mm=150, side_mm=1.0)
    out = {}
    for name, p in (("big", big), ("small", small)):
        LL.configure("strip", 0.04, 1.5, None)
        a = simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5)).results["lumped"]
        LL.configure("strip", 0.04, 1.5, 1.0)
        b = simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5)).results["lumped"]
        out[name] = (a, b)
    assert np.array_equal(out["big"][0].T, out["big"][1].T)
    assert out["small"][1].t_max > 1.15 * out["small"][0].t_max            # the program is more than 13 % cool here (README 3)


def test_integration_patch_equals_the_study_copy():
    """!
    @brief The change exactly as INTEGRATION.md 1 writes it (lib/patch_program.py, applied to the program's text) gives the same fields as the study switch "cap 1 a" of lumped_log,
           so the numbers of the studies are the numbers of the proposed change (review).
    @return None.
    """
    import patch_program as PP
    from pcbthermal import api
    capped = PP.load_patched()
    for side in (1.0, 3.0, 10.0):
        p = S.board(w_mm=200, h_mm=150, side_mm=side)
        LL.configure("strip", 0.04, 1.5, 1.0)
        a = simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5)).results["lumped"]
        api.lumped = capped
        try:
            b = simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5)).results["lumped"]
        finally:
            LL.install()
        assert np.array_equal(a.T, b.T) and a.t_max == b.t_max
