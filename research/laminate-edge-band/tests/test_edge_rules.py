#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_edge_rules.py
@brief Tests of lib/edge_rules.py: the efficiency against an independent finite-difference solution of the half-gap, the limits, and that no rule changes a board without an edge coefficient.
@details Run (repository root): .venv/bin/python -m pytest -q research/laminate-edge-band/tests
"""

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "lib"))
sys.path.insert(0, str(HERE.parents[1]))

import edge_rules as ER                      # noqa: E402
import halfgap_fd as HG                     # noqa: E402
from pcbthermal import Problem, SolverOptions, simulate   # noqa: E402


def fd_efficiency(h, d, kxy, kz):
    """!
    @brief Efficiency from the independent half-gap solver of lib/halfgap_fd.py.
    @param h Edge coefficient.
    @param d Gap thickness.
    @param kxy In-plane k.
    @param kz Through k.
    @return float
    """
    return HG.solve(h, d, kxy, kz)[3]


def test_eta_limits():
    """!
    @brief eta is 1 without an edge film and falls monotonically with h and with a thin... thick gap.
    @return None
    """
    assert ER.eta_laminate(0.0, 1e-3, 0.9, 0.3) == 1.0
    vals = [ER.eta_laminate(h, 1.6e-3, 0.9, 0.3) for h in (1, 10, 100, 1000, 1e4)]
    assert all(a > b for a, b in zip(vals, vals[1:]))
    assert vals[0] > 0.99 and vals[-1] < 0.35
    assert ER.eta_laminate(200, 3.2e-3, 0.9, 0.3) < ER.eta_laminate(200, 0.8e-3, 0.9, 0.3)


def test_eta_matches_finite_differences():
    """!
    @brief The closed-form eta against a separately written 2D finite-volume solution (within 1.5 %).
    @return None
    """
    for h, d in ((50.0, 1.6e-3), (200.0, 3.2e-3), (1000.0, 1.6e-3)):
        fd = fd_efficiency(h, d, 0.9, 0.3)
        assert abs(fd / ER.eta_laminate(h, d, 0.9, 0.3) - 1.0) < 0.015, (h, d, fd)


def board(hs):
    """!
    @brief A small two-layer full-copper board.
    @param hs Edge coefficient or None.
    @return Problem.
    """
    p = Problem.new(width_mm=20, height_mm=14, layers=2, thickness_mm=3.2, copper_um=35.0, ambient=25.0, h_top=10.0, h_bottom=10.0, h_side=hs)
    for l in (1, 2):
        p.add_zone(l, rect=(0, 0, 20, 14))
    p.add_heater(1, 1.0, rect=(0, 0, 4, 4))
    return p


def test_rules_are_inert_without_an_edge_coefficient():
    """!
    @brief With h_side None the band and eta rules give the number of the program bit for bit.
    @return None
    """
    p = board(None)
    ref = simulate(p, SolverOptions(cell_mm=1.0, models=("fvm",))).results["fvm"].t_max
    for kw in (dict(band_width=1.0), dict(eta_mode="exact"), dict(band_width="margin", eta_mode="exact")):
        with ER.rule(**kw):
            assert simulate(p, SolverOptions(cell_mm=1.0, models=("fvm",))).results["fvm"].t_max == ref


def test_band_adds_nodes_only_at_the_edge_and_warms_the_board():
    """!
    @brief The band raises the unknowns, and a board with an edge film reads hotter with it or with eta (less edge loss), never colder.
    @return None
    """
    from pcbthermal import fvm
    p = board(200.0)
    base = simulate(p, SolverOptions(cell_mm=1.0, models=("fvm",))).results["fvm"].t_max
    u0 = fvm.unknowns(p, 1.0)[0]
    for kw in (dict(band_width=1.0), dict(eta_mode="exact")):
        with ER.rule(**kw):
            t = simulate(p, SolverOptions(cell_mm=1.0, models=("fvm",))).results["fvm"].t_max
            assert t > base
    with ER.rule(band_width=1.0):
        assert fvm.unknowns(p, 1.0)[0] > u0


def _arrays(p, dx):
    """!
    @brief The arrays laminate.build wants for a full-copper board.
    @param p Problem.
    @param dx Cell in m.
    @return Tuple (board, fill, cell, cover, active, edge, S, C, gz, g_bottom, g_side).
    """
    b = p.board
    nx, ny = int(round(b.width / dx)), int(round(b.height / dx))
    L = b.layers
    fill = np.ones((L, ny, nx))
    cell = np.full((ny, nx), dx * dx)
    cover = np.ones((ny, nx))
    active = np.ones((ny, nx), dtype=bool)
    edge = np.zeros((ny, nx))
    edge[0, :] += dx
    edge[-1, :] += dx
    edge[:, 0] += dx
    edge[:, -1] += dx
    slab = np.asarray(b.slab_thicknesses())
    S = np.ones((L, ny, nx)) * slab[:, None, None]
    C = np.ones((L, ny, nx)) * slab[:, None, None]
    gz = np.ones((L - 1, ny, nx))
    g_side = float(b.h_side) * slab[:, None, None] * edge[None]
    return b, fill, cell, cover, active, edge, S, C, gz, np.zeros((L, ny, nx)), g_side


def test_half_cell_film_changes_only_the_laminate_share_of_flagged_cells():
    """!
    @brief With the half-cell film the total edge conductance of the cells of the band falls by (1 - f) h_s edge laminate, exactly, and nothing changes outside the band.
    @return None
    """
    import math
    from pcbthermal import laminate
    p = board(200.0)
    dx = 0.5e-3
    b, fill, cell, cover, active, edge, S, C, gz, gb, gs = _arrays(p, dx)
    plans = ER.make_plan_gaps(1.0)(b, fill, dx, active)
    flagged = plans[0].flagged
    assert flagged.any() and not flagged.all() and flagged[0, :].all()          # the band includes the border cells, not the whole board
    old = ER._ORIG["build"](b, fill, cell, cover, active, edge, S, C, gz, gb, gs, plans)
    new = ER.make_build(None, halfcell=True)(b, fill, cell, cover, active, edge, S, C, gz, gb, gs, plans)

    def total(res):
        """!
        @brief Edge conductance of a cell summed over its nodes.
        @param res LadderBuild.
        @return Array (ny, nx).
        """
        return res.g_side.sum(axis=0) + sum(layer["g_side"] for layer in res.layers)

    f = 1.0 / (1.0 + 200.0 * dx / (2.0 * float(b.gap_properties()[1][0])))
    lam = b.gap_thicknesses()[0]                                      # all of the gap's laminate belongs to flagged cells' nodes
    expect = np.where(flagged, total(old) - (1.0 - f) * 200.0 * lam * edge, total(old))
    assert np.allclose(total(new), expect, rtol=1e-12, atol=1e-15)
    assert math.isclose(f, 1.0 / (1.0 + 200.0 * dx / (2.0 * 0.9)))


def test_band_is_the_border_cells_plus_the_reach():
    """!
    @brief The band mask is the ring for width 0 and grows with the width; margin equals laminate.margin_cells.
    @return None
    """
    from pcbthermal import laminate
    p = board(200.0)
    dx = 0.5e-3
    b, fill, cell, cover, active, edge, *_ = _arrays(p, dx)
    d = float(b.gap_thicknesses()[0])
    ring = ER.band_mask(b, active, dx, d, 0.0)
    assert ring.sum() == 2 * (active.shape[0] + active.shape[1]) - 4
    w1 = ER.band_mask(b, active, dx, d, 1.0)
    w2 = ER.band_mask(b, active, dx, d, 2.0)
    assert ring.sum() < w1.sum() < w2.sum()
    m = ER.band_mask(b, active, dx, d, "margin")
    rows = np.where(m[:, active.shape[1] // 2])[0]
    assert rows[rows < active.shape[0] // 2].max() == laminate.margin_cells(d, dx)     # rows 0 .. margin from the border
