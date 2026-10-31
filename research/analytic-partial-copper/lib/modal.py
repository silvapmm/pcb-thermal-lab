#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file modal.py
@brief A copy of the uniform modal (cosine series) solution of the Analytic model with the sheet conductance, the fin length and the modes given from outside, to separate the causes of its error on partial copper.

@details The program's `analytic.solve_steady` for a board with no vias and no heatsinks is the solution of L coupled fin equations by cosine modes, one tridiagonal L x L system per
         mode. This copy does the same from numbers the caller chooses (`S`, the lateral sheet conductance of every layer in W/K, the surface films, the vertical conductances of the gaps)
         and reads the geometry (board size, heater rectangle, gaps, films) from the program's Problem through its own helpers (read only). It reproduces `analytic.solve_steady` to
         round-off when it is given the program's S (tests/test_modal.py), so a change of S, of the number of modes or of the sampling is the only difference between a variant and the program.
         It never edits the program.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pcbthermal import analytic, laminate                                     # noqa: E402


def program_sheet(problem, cell_mm=0.5):
    """!
    @brief The sheet data that the program's Analytic model uses for a problem (after the one-layer series film).
    @param problem A Problem (no vias or heatsinks).
    @param cell_mm Cell size in mm of the sampling grid.
    @return Tuple (problem as the Analytic sees it, dict from analytic._effective_sheet).
    """
    prob = laminate.series_bottom_problem(problem)
    return prob, analytic._effective_sheet(prob, cell_mm)


def solve(problem, sh, S=None, n_terms=300, h_bottom=None):
    """!
    @brief The uniform modal solution with chosen sheet conductances.
    @param problem A Problem as the Analytic sees it (`program_sheet`).
    @param sh Dict from analytic._effective_sheet.
    @param S Lateral sheet conductance of every layer in W/K (None: the program's).
    @param n_terms Cosine modes per direction.
    @param h_bottom Film of the bottom face in W/m2K (None: the board's).
    @return dict with T (L, ny, nx) rise over the ambient, max (K), a_mn.
    """
    b, W, H, L = sh["b"], sh["W"], sh["H"], sh["L"]
    S = sh["S"] if S is None else np.asarray(S, dtype=float)
    h_l = np.zeros(L)
    h_l[0] += b.h_top
    h_l[L - 1] += b.h_bottom if h_bottom is None else h_bottom
    g = sh["g_diel"]
    M = N = n_terms
    q = np.zeros((M, N, L))
    for ht, unit in zip(problem.heaters, analytic._heater_unit_sources(problem, M, N)):
        q += ht.power * unit
    k2 = ((np.arange(M) * np.pi / W) ** 2)[:, None] + ((np.arange(N) * np.pi / H) ** 2)[None, :]
    A = np.zeros((M, N, L, L))
    for l in range(L):
        A[:, :, l, l] = S[l] * k2 + h_l[l]
        if l > 0:
            A[:, :, l, l] += g[l - 1]
            A[:, :, l, l - 1] -= g[l - 1]
        if l < L - 1:
            A[:, :, l, l] += g[l]
            A[:, :, l, l + 1] -= g[l]
    a = np.einsum("mnlk,mnk->mnl", np.linalg.inv(A), q)
    cx = np.cos(np.outer(sh["xs"], np.arange(M) * np.pi / W))
    cy = np.cos(np.outer(sh["ys"], np.arange(N) * np.pi / H))
    T = np.stack([cy @ a[:, :, l].T @ cx.T for l in range(L)])
    return {"T": T, "max": float(T.max()), "a_mn": a}


def sheet_from_fill(sh, fill):
    """!
    @brief The program's formula for the sheet conductance of every layer from a copper fill.
    @param sh Dict from analytic._effective_sheet.
    @param fill Copper fill of every layer (0 to 1), array (L,).
    @return Array (L,) in W/K.
    """
    m, tc, slab, k_lam = sh["m"], sh["tc"], sh["slab"], sh["k_lam"]
    fill = np.asarray(fill, dtype=float)
    return fill * m.k_copper * tc + k_lam * (slab - fill * tc)
