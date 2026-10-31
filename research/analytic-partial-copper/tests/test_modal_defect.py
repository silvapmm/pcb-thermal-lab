#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_modal_defect.py
@brief Tests of the copy of the modal solution (equals the program), of the candidate on uniform boards (equals the program), against the FVM with the same nodes, the energy balance and the reference.
"""

import os
import sys
from dataclasses import replace

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "lib"))

import defect as D                                                           # noqa: E402
import modal as M                                                            # noqa: E402
import pads as P                                                             # noqa: E402
from pcbthermal import SolverOptions, laminate, simulate                     # noqa: E402

SMALL = dict(size=24.0, source=4.0, h_top=10.0, h_bottom=15.0)


def test_modal_copy_equals_the_program():
    """!
    @brief The copy with the program's sheet conductances gives the program's Analytic peak to round-off, on a one-layer and a two-layer pad board.
    @return None.
    """
    for layers in (1, 2):
        bd = P.Pad(layers=layers, pad=8.0, **SMALL)
        p = P.problem(bd)
        pr, sh = M.program_sheet(p, 1.0)
        prog = simulate(p, SolverOptions(models=("analytic",), cell_mm=1.0)).results["analytic"].t_max - p.board.ambient
        assert abs(M.solve(pr, sh)["max"] / prog - 1.0) < 1e-9


def test_candidate_equals_the_program_on_uniform_boards():
    """!
    @brief On a board with copper everywhere the candidate has no defect and gives the program's Analytic result (two layers, one node per gap).
    @return None.
    """
    bd = P.Pad(layers=2, pad=None, **SMALL)
    p = P.problem(bd)
    prog = simulate(p, SolverOptions(models=("analytic",), cell_mm=1.0)).results["analytic"].t_max - p.board.ambient
    r = D.solve(p, n_sub=1, tile_mm=1.0, cell_mm=1.0)
    assert r["tiles"] == 0
    assert abs(r["max"] / prog - 1.0) < 1e-9


def test_candidate_follows_the_fvm_with_the_same_nodes():
    """!
    @brief On a one-layer pad board the candidate with n laminate nodes is within 1.5 % of the program's FVM with the same n (set in memory), the two being the same layered model.
    @return None.
    """
    bd = P.Pad(layers=1, pad=8.0, **SMALL)
    p = P.problem(bd)
    keep = laminate.LAMINATE_NODES
    try:
        for n in (1, 2, 4):
            laminate.LAMINATE_NODES = n
            fvm = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"].t_max - p.board.ambient
            cand = D.solve(p, n_sub=n, tile_mm=0.5, cell_mm=0.5, n_terms=200)["max"]
            assert abs(cand / fvm - 1.0) < 0.015, (n, cand, fvm)
    finally:
        laminate.LAMINATE_NODES = keep


def test_candidate_conserves_energy():
    """!
    @brief The heat leaving through the two faces equals the power (mean of the face fields times the films, 0.5 %).
    @return None.
    """
    bd = P.Pad(layers=2, pad=8.0, **SMALL)
    p = P.problem(bd)
    r = D.solve(p, n_sub=2, tile_mm=1.0, cell_mm=0.5, n_terms=200)
    T = r["T"]
    area = (bd.size * 1e-3) ** 2
    out = area * (bd.h_top * T[0].mean() + bd.h_bottom * T[-1].mean())
    assert abs(out / bd.power - 1.0) < 5e-3


def test_candidate_beats_the_program_on_a_pad():
    """!
    @brief On a 10 mm pad of the small board the candidate with 4 nodes is closer to the resolved reference than the program's Analytic, and within 5 %.
    @return None.
    """
    bd = replace(P.Pad(layers=1, pad=10.0, **SMALL))
    p = P.problem(bd)
    ref = P.reference(bd, 0.5, 0.25, p=p)
    assert abs(ref["balance"] - 1.0) < 1e-9
    prog = P.program_rise(bd, "analytic", 0.5, p)
    cand = D.solve(p, n_sub=4, tile_mm=0.5, cell_mm=0.5)["max"]
    assert abs(cand / ref["peak"] - 1.0) < 0.05
    assert abs(cand / ref["peak"] - 1.0) < abs(prog / ref["peak"] - 1.0)


def test_tile_rule_and_size_limit():
    """!
    @brief The tile follows the part (side / 6, at most 1 mm) and a tile system above the limit is refused.
    @return None.
    """
    assert abs(D.tile_for(P.problem(P.Pad(layers=1, pad=8.0, size=24.0, source=6.0))) - 1.0) < 1e-12
    assert abs(D.tile_for(P.problem(P.Pad(layers=1, pad=8.0, size=24.0, source=3.0))) - 0.5) < 1e-12
    assert abs(D.tile_for(P.problem(P.Pad(layers=1, pad=8.0, size=24.0, source=12.0))) - 1.0) < 1e-12
    p = P.problem(P.Pad(layers=1, pad=8.0, **SMALL))
    try:
        D.solve(p, n_sub=1, tile_mm=0.5, max_unknowns=10)
    except ValueError:
        return
    raise AssertionError("a tile system above the limit must be refused")


def test_three_tiles_across_the_part_overshoot():
    """!
    @brief The measured limit of the tile (README 5.4): with the part three tiles across the candidate with four laminate nodes is far hotter than with six tiles across.
    @return None.
    """
    p = P.problem(P.Pad(layers=1, pad=20.0))                  # the 60 mm board of the baseline, 6 mm part
    coarse = D.solve(p, n_sub=4, tile_mm=2.0)["max"]
    fine = D.solve(p, n_sub=4, tile_mm=1.0)["max"]
    assert coarse > 1.10 * fine                                # measured +19 % (66.0 K against 55.5 K, README 5.4)


def test_reference_converges_with_the_cell():
    """!
    @brief The reference changes by less than 2 % between 0.5 and 0.25 mm cells and by less between 0.25 and 0.125.
    @return None.
    """
    bd = P.Pad(layers=1, pad=8.0, **SMALL)
    p = P.problem(bd)
    v = [P.reference(bd, 0.5, dx, p=p)["peak"] for dx in (0.5, 0.25, 0.125)]
    assert abs(v[1] / v[0] - 1.0) < 0.02
    assert abs(v[2] / v[1] - 1.0) < abs(v[1] / v[0] - 1.0) + 1e-3
    assert np.isfinite(v).all()


def test_candidate_refuses_what_it_does_not_model():
    """!
    @brief Review regression: a board with a via, a heatsink or an outline is refused (the first version dropped them silently and returned a result without them).
    @return None.
    """
    def base():
        """!
        @brief A fresh one-layer pad board of the small size.
        @return Problem.
        """
        return P.problem(P.Pad(layers=1, pad=8.0, **SMALL))

    with_via = base()
    with_via.add_via(12.0, 12.0, diameter=0.3)
    with_sink = base()
    with_sink.add_heatsink(1, 50.0, rect=(2.0, 2.0, 6.0, 6.0))
    with_outline = base()
    with_outline.set_outline([(0.0, 0.0), (24.0, 0.0), (24.0, 24.0), (0.0, 20.0)])
    for p in (with_via, with_sink, with_outline):
        try:
            D.solve(p, n_sub=1, tile_mm=1.0, n_terms=60)
        except ValueError:
            continue
        raise AssertionError("the candidate must refuse a via, a heatsink or an outline")


def test_copper_edge_inside_a_tile_runs_cool():
    """!
    @brief Review finding (a limit, pinned): a pad edge in the middle of a tile makes the candidate cooler than the FVM with the same nodes, because the partly covered tile conducts like
           copper. 24 mm board, 4 mm part, two laminate nodes, 1 mm tiles: an 8 mm pad (edges on tile edges) follows the FVM at 0.25 mm within 1 %; an 8.5 mm pad (edges a quarter of
           a tile off) is several percent cool (measured -6.8 %; -3.3 % with 0.5 mm tiles).
    @return None.
    """
    keep = laminate.LAMINATE_NODES
    errs = {}
    try:
        laminate.LAMINATE_NODES = 2
        for pad in (8.0, 8.5):
            p = P.problem(P.Pad(layers=1, pad=pad, **SMALL))
            fvm = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.25)).results["fvm"].t_max - p.board.ambient
            errs[pad] = D.solve(p, n_sub=2, tile_mm=1.0, cell_mm=0.25)["max"] / fvm - 1.0
    finally:
        laminate.LAMINATE_NODES = keep
    assert abs(errs[8.0]) < 0.01, errs
    assert errs[8.5] < -0.04, errs
