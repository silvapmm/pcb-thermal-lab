#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file analytic_patch.py
@brief In-memory copy of the Analytic steady solution with a self-term of the tile Green function for the vias (the program's `analytic.py` is never edited).
@details In `analytic.solve_steady` the board is cut into tiles of 2.5 to 5 mm, every tile with a via gets the lumped conductance of its vias between the sheets, and the
         small system (I + G C) y = y0 gives the TILE-MEAN temperatures (G = modal response of the tile mean to a unit power injected uniformly in a tile). The via is then
         coupled between tile means: nothing in it knows that the barrel has a radius. The copy inserts, right after G is built, a diagonal term
             D[(tile, l), (tile, l)] = (1 / N) R_c(l) / (the number of vias of the tile)   (K/W per watt injected in the tile and sheet)
         so that the temperature the vias see is the one at their wall: y_wall = y_mean + D f. Options (`OPTIONS`):
         * `mode`  "off" (the program, bit for bit), "krogh" (R_cell = sqrt(A_tile / (pi N)), Krogh cell with the 3/4 of a uniform source), "tile" (the constant 1/4 of a point
                   sink read against the response of the tile to its own uniform injection, `constriction.tile_self`, with R = sqrt(A_tile / (pi N)));
         * `eta`   r_t / r_v.
         The tile of a via is the tile that holds its centre, as in the program. `spread` ("none" or "bilinear") optionally distributes the barrel conductance of a via over the
         four tiles whose centres surround it, which removes the dependence on the corner at which the via happens to sit (measured in the study).
@note Sheets that are not copper (S = laminate only) get the same formula: their S is the S of the effective sheet of the program.
"""

import contextlib
import inspect
import math
import os
import sys
import textwrap

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import constriction as cr                                                   # noqa: E402

OPTIONS = {"mode": "off", "eta": cr.ETA, "spread": "none"}


def _self_terms(G, active, tw, th, S, L, problem):
    """!
    @brief Add the self-terms of the vias to the tile response matrix.
    @param G (Nt*L, Nt*L) response of the tile means to the heat injected in the tiles (K/W).
    @param active (Nt, 2) array of (row, col) of the tiles of the system.
    @param tw Tile width in m.
    @param th Tile height in m.
    @param S (L,) sheet conductance of the layers in W/K.
    @param L Number of layers.
    @param problem The Problem.
    @return numpy.ndarray G plus the diagonal terms (a new array).
    """
    if OPTIONS["mode"] == "off" or not problem.vias:
        return G
    b = problem.board
    pos = {(int(r), int(c)): i for i, (r, c) in enumerate(active)}
    ntx = int(round(b.width / tw))
    nty = int(round(b.height / th))
    # Vias per tile and their mean radius
    count, rsum = {}, {}
    for v in problem.vias:
        c = min(max(int(v.x // tw), 0), ntx - 1)
        r = min(max(int(v.y // th), 0), nty - 1)
        count[(r, c)] = count.get((r, c), 0) + 1
        rsum[(r, c)] = rsum.get((r, c), 0.0) + v.diameter / 2.0
    G = G.copy()
    for key, n in count.items():
        if key not in pos:
            continue
        a = OPTIONS["eta"] * rsum[key] / n
        r_cell = math.sqrt(tw * th / (math.pi * n))
        for l in range(L):
            if S[l] <= 0:
                continue
            if OPTIONS["mode"] == "krogh":
                rc = cr.krogh(S[l], r_cell, a)
            else:
                rc = cr.tile_self(S[l], r_cell, a)
            i = pos[key] * L + l
            G[i, i] += rc / n                                               # per watt of the tile; n vias share the heat
    return G


_ANCHOR = "            G = Gm.reshape(Nt * L, Nt * L)\n"


def _compile_solver():
    """!
    @brief Compile the copy of `analytic.solve_steady` with the hook after the construction of G.
    @return The new function.
    @throws RuntimeError If the anchor is not found (the program changed).
    """
    from pcbthermal import analytic
    src = textwrap.dedent(inspect.getsource(analytic.solve_steady))
    pad = " " * 8                                                           # the anchor line after dedent has 12 - 4 = 8... checked below
    anchor = textwrap.dedent(_ANCHOR)
    k = src.find(anchor.strip())
    if k < 0:
        raise RuntimeError("anchor not found in analytic.solve_steady")
    line_start = src.rfind("\n", 0, k) + 1
    indent = src[line_start:k]
    end = src.find("\n", k) + 1
    src = src[:end] + indent + "G = _self_terms(G, active, tw, th, S, L, problem)\n" + src[end:]
    ns = {}
    exec(compile(src, "<patched analytic.solve_steady>", "exec"), analytic.__dict__, ns)
    analytic._self_terms = _self_terms
    return ns["solve_steady"]


@contextlib.contextmanager
def patched(mode="krogh", eta=cr.ETA, spread="none"):
    """!
    @brief Install the Analytic steady solution with the self-terms of the vias; restore the original on exit.
    @param mode "off", "krogh" or "tile".
    @param eta r_t / r_v.
    @param spread "none" (the tile that holds the centre) or "bilinear" (not implemented in the first version: reserved).
    @return Context manager.
    """
    from pcbthermal import analytic
    old = analytic.solve_steady
    old_opts = dict(OPTIONS)
    OPTIONS.update(mode=mode, eta=eta, spread=spread)
    try:
        analytic.solve_steady = _compile_solver()
        yield
    finally:
        analytic.solve_steady = old
        OPTIONS.clear()
        OPTIONS.update(old_opts)
        if hasattr(analytic, "_self_terms"):
            del analytic._self_terms
