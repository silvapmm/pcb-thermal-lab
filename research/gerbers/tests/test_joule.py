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
