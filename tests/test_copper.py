"""!
@file test_copper.py
@brief The copper of an outer layer dissipates and spreads heat by itself (no element needed); how it compares with a heatsink.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research" / "solid3d-verification" / "scripts"))
import copper_dissipation as cd                                       # noqa: E402
from pcbthermal import fdm, fvm                                       # noqa: E402


def test_a_larger_outer_pad_cools_more_and_saturates():
    t = [fvm.solve_steady(cd.board(w), 1.0).t_max for w in (None, 20, 40, 60, 80)]
    assert all(a > b for a, b in zip(t, t[1:]))                        # Each step of copper cools
    assert (t[3] - t[4]) < 0.2 * (t[0] - t[1])                         # The gain per extra copper shrinks (saturation)
    f = [fdm.solve_steady(cd.board(w), 1.0).t_max for w in (None, 40, 80)]
    assert f[0] > f[1] > f[2]


def test_every_cell_of_the_outer_face_loses_heat_over_copper_and_laminate():
    p = cd.board(40)
    r = fvm.solve_steady(p, 1.0)
    b = p.board
    top = float((b.h_top * (r.T[0] - b.ambient) * r.dx * r.dy).sum())
    assert top == pytest.approx(r.power_out["top"], rel=1e-9)         # The whole face, pad and bare laminate alike
    w_pad, w_rest = cd.face_split(p)
    assert w_pad > 0 and w_rest > 0 and w_pad + w_rest == pytest.approx(top, rel=1e-9)
    assert w_rest > 0.2 * w_pad                                       # The copper carried heat out beyond its edge to the laminate


def test_copper_spreads_so_a_heatsink_works_better_on_copper_than_on_bare_laminate():
    pad = fvm.solve_steady(cd.board(40, 30.0), 1.0).t_max             # Copper pad plus heatsink over it
    pad_only = fvm.solve_steady(cd.board(40), 1.0).t_max
    bare = cd.board(None)
    bare.add_heatsink(1, 30.0, rect=(30, 20, 70, 60))
    laminate = fvm.solve_steady(bare, 1.0).t_max                       # Same heatsink, no copper to spread in
    assert pad < pad_only and pad < laminate
    assert laminate - pad > 50.0                                       # The copper under the heatsink is what makes it work
    more = fvm.solve_steady(cd.board(40, 100.0), 1.0).t_max
    assert more < pad                                                   # A better heatsink on the same copper cools more
