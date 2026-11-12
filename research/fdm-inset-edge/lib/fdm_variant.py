#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fdm_variant.py
@brief Experimental copies of `pcbthermal/fdm.py` with switches, built from the program's own source text (the program is not edited).
@details `load(**switches)` reads `pcbthermal/fdm.py`, applies the text patches of the chosen switches and returns a module object with the same API (`Network`, `solve_steady`).
         Switches (all default off, so `load()` is the program bit for bit, which `tests/test_variant.py` checks):
         * `face_fill`: the in-plane sheet of a copper-layer face is built from the copper fill of the CELLS that the face runs through (the cell between two nodes is uniform along
           the face, so no mean of two nodal values is needed), instead of the harmonic mean of the two nodal fills (a node whose control volume is cut by a copper edge reads a
           half-copper sheet, and the copper edge is smeared over a cell). The nodal fill still carries capacity, vertical links, the top film and the sources.
         * `no_film_lam`: switch off the edge film on the laminate nodes (ablation, not a model).
         * `no_film_cu`: switch off the edge film on the copper nodes (ablation).
         * `edge_full_volume`: ablation of the half control volume of the edge nodes is NOT offered (it would change the grid); see README 3.
         * `arith_cover`: use the arithmetic mean at the faces of nodes cut by the outline only (the program's harmonic mean already keeps the cover weighted link).
"""

import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SRC = os.path.join(ROOT, "pcbthermal", "fdm.py")

HELPER = '''

def _face_sheets(net, S, ncov, L, tc, k_lam, m, fx, fy):
    """!
    @brief Face sheets of the copper layers from the copper fill of the cells the faces run through (experimental variant).
    @param net The network being built (holds the nodal fill and `_cell_fill`).
    @param S Sheet conductance of the nodes after the laminate rule (W/K), (layers, ny, nx).
    @param ncov Outline cover of the nodes.
    @param L Copper layers.
    @param tc Copper thickness (L, 1, 1).
    @param k_lam Laminate conductivity (L, 1, 1).
    @param m Materials.
    @param fx Face array in x as the program makes it (layers, ny, nx - 1).
    @param fy Face array in y (layers, ny - 1, nx).
    @return Tuple (fx, fy) with the copper layers replaced.
    """
    cf = net._cell_fill                                                     # (L, cells_y, cells_x)
    B = (m.k_copper - k_lam) * tc                                           # Physical sheet gained by copper (W/K)
    with np.errstate(divide="ignore", invalid="ignore"):
        A = np.where(ncov[None] > 0, (S[:L] - B * ncov[None] * net.fill) / ncov[None], 0.0)    # Physical sheet with no copper (laminate part) of every node
    cfx = np.pad(cf, ((0, 0), (1, 1), (0, 0)), mode="edge")
    ffx = 0.5 * (cfx[:, :-1, :] + cfx[:, 1:, :])                            # (L, ny, nx - 1)
    cfy = np.pad(cf, ((0, 0), (0, 0), (1, 1)), mode="edge")
    ffy = 0.5 * (cfy[:, :, :-1] + cfy[:, :, 1:])                            # (L, ny - 1, nx)
    cvx = 0.5 * (ncov[:, :-1] + ncov[:, 1:])[None]
    cvy = 0.5 * (ncov[:-1, :] + ncov[1:, :])[None]
    fx = fx.copy()
    fy = fy.copy()
    fx[:L] = (0.5 * (A[:, :, :-1] + A[:, :, 1:]) + B * ffx) * cvx
    fy[:L] = (0.5 * (A[:, :-1, :] + A[:, 1:, :]) + B * ffy) * cvy
    return fx, fy
'''


def source(face_fill=False, no_film_lam=False, no_film_cu=False):
    """!
    @brief The patched source text.
    @param face_fill Faces from the cell fill.
    @param no_film_lam Edge film off on the laminate nodes.
    @param no_film_cu Edge film off on the copper nodes.
    @return str.
    """
    s = open(SRC).read()
    if face_fill:
        a = "            fill = np.stack([_node_average(cell_fill[k]) for k in range(L)])\n"
        assert a in s
        s = s.replace(a, a + "            self._cell_fill = cell_fill\n")
        b = "        # Imported copper: the face conductances of the sheet"
        assert b in s
        s = s.replace(b, "        if sampling == 'area' and rule is not None:\n            fx, fy = _face_sheets(self, S, ncov, L, tc, k_lam, m, fx, fy)\n" + b)
        s = s.replace("\n\ndef _inside(", HELPER + "\n\ndef _inside(", 1)
    if no_film_lam:
        a = "                self.g_side[L + k] = ly[\"g_side\"]\n        elif NL:"
        assert a in s
        s = s.replace(a, "                self.g_side[L + k] = 0.0 * ly[\"g_side\"]\n        elif NL:")
    if no_film_cu:
        a = "            self.g_bottom[:L], self.g_side[:L] = rule.g_bottom, rule.g_side\n"
        assert a in s
        s = s.replace(a, "            self.g_bottom[:L], self.g_side[:L] = rule.g_bottom, 0.0 * rule.g_side\n")
    return s


def load(**switches):
    """!
    @brief Build the variant module.
    @param switches See `source`.
    @return Module with `Network` and `solve_steady`.
    """
    import pcbthermal
    name = "pcbthermal._fdm_variant_%d" % abs(hash(tuple(sorted(switches.items()))))
    mod = types.ModuleType(name)
    mod.__package__ = "pcbthermal"
    mod.__file__ = SRC
    sys.modules[name] = mod
    exec(compile(source(**switches), SRC, "exec"), mod.__dict__)
    assert pcbthermal
    return mod
