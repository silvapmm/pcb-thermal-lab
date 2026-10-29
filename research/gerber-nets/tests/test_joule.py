"""!
@file test_joule.py
@brief The current/Joule prototype against closed forms: a straight strip, strips in series and in parallel, and the conservation of the power.
"""

import numpy as np
import pytest

import joule

RS = 0.0005          # ohm per square (about 35 um copper)


def strip(rows, cols):
    """!
    @brief A full strip with the terminals on its first and last columns.
    @param rows Number of pixel rows (width).
    @param cols Number of pixel columns (length).
    @return Tuple (mask, source, sink).
    """
    m = np.ones((rows, cols), bool)
    s = np.zeros_like(m); k = np.zeros_like(m)
    s[:, 0] = True; k[:, -1] = True
    return m, s, k


def test_straight_strip_resistance_and_power():
    """!@brief R = Rs (L - 1) / W for the pixel strip between terminal columns, and the power is I^2 R. @return None."""
    m, s, k = strip(10, 50)
    r, v, q = joule.solve_net(m, RS, s, k, 2.0)
    assert r == pytest.approx(RS * 49 / 10, rel=1e-9)                       # 49 faces between the first and last column
    assert q.sum() == pytest.approx(4.0 * r, rel=1e-9)


def test_width_step_is_a_series_circuit():
    """!@brief A strip of width 10 and a strip of width 5 in series add their resistances. @return None."""
    m = np.zeros((10, 61), bool)
    m[:, :31] = True
    m[2:7, 30:] = True
    s = np.zeros_like(m); k = np.zeros_like(m)
    s[:, 0] = True; k[2:7, -1] = True
    r, v, q = joule.solve_net(m, RS, s, k, 1.0)
    assert r == pytest.approx(RS * (30 / 10 + 30 / 5), rel=0.03)            # the constriction adds a small spreading term
    assert q.sum() == pytest.approx(r, rel=1e-9)


def test_parallel_paths_and_cells_conserve_power():
    """!@brief Two equal strips in parallel give half the resistance; the cell sum keeps the total power. @return None."""
    m = np.zeros((20, 40), bool)
    m[0:5, :] = True; m[15:20, :] = True; m[:, 0] = True; m[:, -1] = True
    s = np.zeros_like(m); k = np.zeros_like(m)
    s[:, 0] = True; k[:, -1] = True
    r, v, q = joule.solve_net(m, RS, s, k, 3.0)
    assert q.sum() == pytest.approx(9.0 * r, rel=1e-9)
    assert joule.to_cells(q, 5).sum() == pytest.approx(q.sum(), rel=1e-12)


def test_unconnected_terminals_are_refused():
    """!@brief Terminals on two separate pieces of copper raise ValueError. @return None."""
    m = np.zeros((5, 20), bool)
    m[:, :8] = True; m[:, 12:] = True
    s = np.zeros_like(m); k = np.zeros_like(m)
    s[:, 0] = True; k[:, -1] = True
    with pytest.raises(ValueError):
        joule.solve_net(m, RS, s, k, 1.0)


def test_resistivity_of_copper_rises_with_temperature():
    """!@brief 20 C gives 1.68e-8 ohm m and 100 C gives about 31 % more. @return None."""
    assert joule.resistivity(20.0) == pytest.approx(1.68e-8)
    assert joule.resistivity(100.0) / joule.resistivity(20.0) == pytest.approx(1.314, rel=0.01)


def test_overlapping_terminals_are_refused():
    """!@brief Two terminals that share a pixel raise ValueError instead of dividing by zero. @return None."""
    m, s, k = strip(5, 10)
    k[:, 0] = True
    with pytest.raises(ValueError):
        joule.solve_net(m, RS, s, k, 1.0)


def test_nine_point_stencil_matches_the_straight_strip_and_fixes_a_tilted_one():
    """!@brief The nine-point stencil gives the same R for a straight strip and a much smaller error for a strip at 45 degrees than the five-point stencil. @return None."""
    m, s, k = strip(10, 50)
    r4, _, _ = joule.solve_net(m, RS, s, k, 1.0, stencil="4")
    r9, _, q9 = joule.solve_net(m, RS, s, k, 1.0, stencil="9")
    assert r9 == pytest.approx(r4, rel=0.05)                      # a pixel row at an insulated wall misses its diagonal links: about 1/(3 W) too resistive
    assert q9.sum() == pytest.approx(r9, rel=1e-9)
    n = 120
    yy, xx = np.mgrid[:n, :n]
    tilt = (np.abs(xx - yy) <= 6) & (xx + yy > 20) & (xx + yy < 2 * n - 20)       # a band at 45 degrees, 13 pixels wide across x
    src = tilt & (xx + yy <= 24)
    snk = tilt & (xx + yy >= 2 * n - 24)
    width = 13 / np.sqrt(2.0)
    length = (2 * n - 24 - 24) / np.sqrt(2.0)
    ideal = RS * length / width
    e4 = abs(joule.solve_net(tilt, RS, src, snk, 1.0, stencil="4")[0] / ideal - 1)
    e9 = abs(joule.solve_net(tilt, RS, src, snk, 1.0, stencil="9")[0] / ideal - 1)
    assert e9 < e4                                                  # better, but not exact: the walls of a narrow band still cost a few percent


def test_cell_sum_keeps_partial_cells():
    """!@brief A map whose size is not a multiple of the cell keeps all its heat (the last partial cells were cut off before the review). @return None."""
    q = np.ones((7, 9))
    cells = joule.to_cells(q, 2)
    assert cells.shape == (4, 5)
    assert cells.sum() == pytest.approx(63.0)
