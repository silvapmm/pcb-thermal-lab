#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_references.py
@brief Tests of the graded 3D solver and of the gap-node copy: the solver against the exact series and the energy balance, one node equals the program, more nodes converge to the references.
"""

import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "lib"))

import boards as B                                                           # noqa: E402
import gapnodes as G                                                         # noqa: E402

SMALL = dict(layers=2, gap=0.8, size=12.0, source=2.0, h_top=10.0, h_bottom=10.0)


def test_graded_solver_matches_the_exact_series():
    """!
    @brief On a uniform board the converged graded solver equals the exact series within 0.1 % and conserves energy to 1e-9.
    @return None.
    """
    bd = B.Board("u", **SMALL)
    ref = B.exact_peak(bd, 0.5)
    g = B.graded_peak(bd, 0.5, scales=(2.0, 1.414, 1.0))
    assert abs(g["peak"] / ref - 1) < 1e-3
    assert abs(g["balance"] - 1) < 1e-9


def test_one_node_is_the_program_and_more_nodes_converge():
    """!
    @brief n = 1 gives the program's FVM peak (1e-9 relative), and on a pad board the error against the same-cell 3D reference falls as n grows to under 1 point at n = 8.
    @return None.
    """
    bd = B.Board("p", pad=6.0, pad_layers=(0,), **SMALL)
    p = B.problem(bd)
    prog = B.program_peak(bd, "fvm", 0.5, p)
    assert abs(G.run(p, 0.5, 1, "all")["peak"] / prog - 1) < 1e-9
    # The reference on the same in-plane grid isolates the through-thickness discretisation
    ref = B.samecell_peak(bd, 0.5, 32, p)
    errs = [abs(G.run(p, 0.5, n, "all")["peak"] / ref - 1) for n in (1, 2, 4, 8)]
    assert errs[0] > errs[1] > errs[2] > errs[3]
    assert errs[3] < 0.01


def test_uniform_board_is_untouched_by_bare_cell_refinement():
    """!
    @brief With copper in every cell no cell is flagged "bare": the copy returns the program's number for any n (bit for bit).
    @return None.
    """
    bd = B.Board("u", **SMALL)
    p = B.problem(bd)
    one = G.run(p, 0.5, 1, "none")["peak"]
    assert G.run(p, 0.5, 6, "bare")["peak"] == one
