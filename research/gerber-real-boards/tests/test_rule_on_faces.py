#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_rule_on_faces.py
@brief Tests of the face mapping with the laminate rule on (lib/rule_study.py, lib/synth.py): nothing to map on solid copper, the moved laminate is zero without absent copper, the naive faces double count, and the faces built on the reduced sheet beat the fill fraction against the 3D reference on a small stripe board.
"""

import numpy as np

import boardrun
import rule_study as rs
import synth

SIDE, CELL, HEATER = 6.0, 0.6, 2.4
CENTRE = (3.0, 3.0)


def _solid_board(layers=2):
    """!
    @brief A board of solid copper on every layer (SIDE mm, no holes).
    @param layers 2 or 4.
    @return faces.ImportedBoard.
    """
    ib = synth.synthetic_board("stripes", "2solid", CELL, side=SIDE)
    m = synth.pattern("solid", SIDE)[::-1].copy()
    ib.layers = [{"name": f"L{i}", "binary": m, "coverage": m.astype(float)} for i in range(layers)]
    return ib


def test_nothing_moves_on_solid_copper():
    """!@brief With copper in every cell the rule moves no laminate (dS = 0) and every mapping gives the fill-fraction answer. @return None."""
    ib = _solid_board()
    p = boardrun.make_problem(ib, CENTRE, HEATER, 1.0, h_face=rs.H_FACE)
    _, dS, flagged = rs.moved_laminate(ib, p)
    assert all(np.abs(d).max() == 0.0 for d in dS) and flagged == [0]
    t_today = boardrun.heater_stats(rs.solve_variant(ib, p, "today_on"), ib.cell, CENTRE, HEATER)[0]
    for v in ("flow_on", "lambda_on", "flow_naive"):
        t = boardrun.heater_stats(rs.solve_variant(ib, p, v), ib.cell, CENTRE, HEATER)[0]
        assert abs(t / t_today - 1) < 2e-3, (v, t, t_today)


def test_moved_laminate_positive_beside_absent_copper():
    """!@brief On a striped board the rule moves laminate out of the copper node in the flagged cells (dS > 0 somewhere, never negative). @return None."""
    ib = synth.synthetic_board("stripes", "2solid", CELL, side=SIDE)
    p = boardrun.make_problem(ib, CENTRE, HEATER, 1.0, h_face=rs.H_FACE)
    _, dS, flagged = rs.moved_laminate(ib, p)
    assert dS[0].min() >= 0.0 and dS[0].max() > 0.0
    assert flagged[0] > 0


def test_naive_faces_double_count_and_reduced_faces_do_not():
    """!@brief On a striped board, against the 3D reference: the faces built on the reduced sheet are closer than the earlier faces on the network with the rule on (which count the laminate twice) and than the fill fraction. @return None."""
    ib = synth.synthetic_board("stripes", "2solid", CELL, side=SIDE)
    r = rs.run_case(ib, CENTRE, HEATER, 4, ["today_on", "flow_naive", "flow_on"])
    e = {k: abs(v) for k, v in r["error"].items()}
    assert e["flow_on"] < e["flow_naive"] < e["today_on"] + 1.0, e
    assert e["flow_on"] < e["today_on"], e
    assert e["flow_on"] < 5.0, e
