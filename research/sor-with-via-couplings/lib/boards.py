#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file boards.py
@brief Helpers of the SOR-with-vias studies: networks of the program with a via treatment (built on in-memory copies), boards without vias, a scaled via part and a hand-made toy.
@details The boards come from `research/point-via-convergence/lib/program_cases.py` (the simple ones first: unit cell, lone via, row, 3 x 3 array).
         `net_for` builds the program's `fvm.Network` inside `program_patch.patched`; the files of the program are not edited.
"""

import copy
import math
import os
import sys
import types

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "point-via-convergence", "lib"))
sys.path.insert(0, HERE)

import program_cases as pc                                                  # noqa: E402,F401
import program_patch as pp                                                  # noqa: E402
import sorvia as sv                                                         # noqa: E402
from pcbthermal import fvm                                                  # noqa: E402

ETA = math.exp(-0.25)                                                       # the radius of the treatment `mw_disc@eta` of the point-via study


def net_for(problem, cell_mm, treatment="mw_disc"):
    """!
    @brief The FVM network of a problem with a via treatment installed on the copies.
    @param problem A Problem.
    @param cell_mm Target cell size in mm.
    @param treatment Key of `program_patch.TREATMENTS` ("point" is the program's own).
    @return fvm.Network (the matrix is assembled; `_via_blocks` is set for the mean-potential treatments).
    """
    nx = max(int(round(problem.board.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(problem.board.height * 1000.0 / cell_mm)), 2)
    with pp.patched(treatment, eta=ETA):
        return fvm.Network(problem, nx, ny)


def without_vias(problem):
    """!
    @brief A copy of a problem with no vias (the reference for the number of sweeps of the stencil alone).
    @param problem A Problem.
    @return Problem.
    """
    p = copy.deepcopy(problem)
    p.vias = []
    return p


def scaled(net, s):
    """!
    @brief A light copy of a network whose via part K_via is multiplied by s (to sweep the stiffness of the via at fixed geometry).
    @param net A network built with a mean-potential treatment.
    @param s Factor on K_via = sum B^T G B (1 = the network itself).
    @return types.SimpleNamespace with the attributes the solvers use (K, Q, S, gz, extra_links, dx, dy, nl, ny, nx, n_board, _harmonic, _via_blocks).
    """
    Kfull = sv.via_operator(net)[0]
    out = types.SimpleNamespace(**{k: getattr(net, k) for k in ("Q", "S", "gz", "extra_links", "dx", "dy", "nl", "ny", "nx", "n_board", "_via_blocks")})
    out._harmonic = net._harmonic
    out.K = (net.K + (s - 1.0) * Kfull).tocsc()
    return out


def toy_two_layers(gx=2.0, gz=3.0, gv=5.0, ga=0.5, q=1.0):
    """!
    @brief Hand-made 2 layers x 2 cells toy: one via spans both cells, footprint weights (1/2, 1/2), barrel conductance gv between the layer means.
    @details Unknowns (top a, top b, bottom a, bottom b). Stencil: gx between the cells of a layer, gz between layers in a cell, ga from the bottom cells to the ambient.
             Via part: gv u u^T with u = (1/2, 1/2, -1/2, -1/2). Source q in top cell a only.
    @param gx In-plane conductance between the two cells in W/K.
    @param gz Vertical conductance in W/K.
    @param gv Barrel conductance in W/K.
    @param ga Conductance of each bottom cell to the ambient in W/K.
    @param q Power in the top cell a in W.
    @return dict with K (4 x 4 dense), Kst (the matrix the program's SOR iterates: diagonal of K and stencil off-diagonals), Kv (via part), rhs.
    """
    S = np.array([[gx + gz, -gx, -gz, 0.0], [-gx, gx + gz, 0.0, -gz], [-gz, 0.0, gx + gz + ga, -gx], [0.0, -gz, -gx, gx + gz + ga]])
    u = np.array([0.5, 0.5, -0.5, -0.5])
    Kv = gv * np.outer(u, u)
    K = S + Kv
    Kst = S + np.diag(np.diag(Kv))
    return {"K": K, "Kst": Kst, "Kv": Kv, "rhs": np.array([q, 0.0, 0.0, 0.0])}
