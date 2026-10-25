"""!
@file test_pdn.py
@brief The electrical prototype (pdn.py): a strip against its squares, the energy balance with a link, and floating copper (no current, no heat).
"""

import numpy as np

import pdn

RS = 0.01                                           # ohm per square


def strip():
    """!
    @brief A 20 x 2 pixel strip with 2-pixel-wide terminals at its two ends.
    @return tuple (mask, terminals dict).
    """
    m = np.zeros((2, 22), bool)
    m[:, :] = True
    a, b = np.zeros_like(m), np.zeros_like(m)
    a[:, 0] = True
    b[:, -1] = True
    return m, {"a": a, "b": b}


def test_strip_resistance_equals_its_squares():
    """!
    @brief A strip of 21 squares of length with 2 squares of width: R = Rs * length / width.
    @return None.
    """
    m, t = strip()
    r = pdn.solve(m, RS, t, [("vsource", "a", 1.0), ("isink", "b", 0.5)])
    drop = 1.0 - float(np.nanmean(r["V"][t["b"]]))
    assert abs(drop / 0.5 - RS * 21.0 / 2.0) / (RS * 21.0 / 2.0) < 0.02


def test_energy_balance_with_a_link_and_floating_copper():
    """!
    @brief Two strips joined by a 0.1 ohm link plus a floating block: source power = copper + link + load, floating copper carries nothing.
    @return None.
    """
    m = np.zeros((6, 30), bool)
    m[0:2, 0:12] = True
    m[0:2, 16:30] = True
    m[4:6, 0:10] = True                              # floating block
    t = {"vin": np.zeros_like(m), "pa": np.zeros_like(m), "pb": np.zeros_like(m), "load": np.zeros_like(m)}
    t["vin"][0:2, 0] = True
    t["pa"][0:2, 11] = True
    t["pb"][0:2, 16] = True
    t["load"][0:2, 29] = True
    r = pdn.solve(m, RS, t, [("vsource", "vin", 5.0), ("link", "pa", "pb", 0.1), ("isink", "load", 2.0)])
    assert abs(r["p_source"] - r["p_copper"] - r["p_links"] - r["p_sinks"]) < 1e-3 * r["p_source"]
    assert abs(r["p_links"] - 0.1 * 2.0 ** 2) < 1e-3                  # the link carries the whole current
    assert r["q"][4:6, 0:10].sum() == 0.0 and np.isnan(r["V"][4:6, 0:10]).all()


def test_a_sink_on_a_piece_without_a_source_is_refused():
    """!
    @brief A current sink on a piece that no voltage source reaches is refused (it was silently dropped before the review).
    @return None.
    """
    import pytest
    m = np.zeros((4, 30), bool)
    m[:, 0:12] = True
    m[:, 16:30] = True
    t = {"vin": np.zeros_like(m), "far": np.zeros_like(m)}
    t["vin"][:, 0] = True
    t["far"][:, 29] = True
    with pytest.raises(ValueError):
        pdn.solve(m, RS, t, [("vsource", "vin", 5.0), ("isink", "far", 1.0)])
