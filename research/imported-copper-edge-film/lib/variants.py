#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file variants.py
@brief Candidate corrections of the edge film on boards with imported copper, built as copies on top of the program (the program is not edited): `use(...)` returns a context in which `fvm.Network` and `laminate.build` are the variants.
@details Switches (all default to the program as it is):
         * `film`: 'node' (the program: the edge film on the node of an imported outline board) or 'series' (the film in series with the conduction from the node to the closest
           outline point, as the drawn layers have it: `fvm.Network._cut_edge_film`); `alpha` scales that distance and `floor` replaces the 0.25 floor.
         * `grade`: sub-gaps of the laminate rule uniform (the program), graded toward the copper layers by the cosine rule z_k = d (1 - cos(pi k / n)) / 2 ('cos'), or the end
           sub-gaps a fraction `end` of the gap ('ends').
         The variant of `laminate.build` is the program's source with the uniform sub-gap `np.full(n, d / n)` and the demand `p.d / (2.0 * p.n)` replaced; nothing else changes.
"""

import contextlib
import inspect
import textwrap

import numpy as np

from pcbthermal import fvm, laminate

CFG = {"film": "node", "alpha": 1.0, "grade": "uniform", "end": 0.15, "floor": None}


def sub_gaps(d, n):
    """!
    @brief The sub-gap thicknesses of a gap of thickness d cut into n.
    @param d Gap thickness in m.
    @param n Number of sub-gaps.
    @return Array of n thicknesses summing to d.
    """
    if n <= 1 or CFG["grade"] == "uniform":
        return np.full(n, d / n)
    if CFG["grade"] == "cos":
        z = d * (1 - np.cos(np.pi * np.arange(n + 1) / n)) / 2
        return np.diff(z)
    if CFG["grade"] == "ends":
        a = CFG["end"]
        if n == 2:
            return np.full(2, d / 2)
        mid = (1 - 2 * a) / (n - 2)
        return d * np.array([a] + [mid] * (n - 2) + [a])
    raise ValueError(CFG["grade"])


_SRC = textwrap.dedent(inspect.getsource(laminate.build))
_SRC = _SRC.replace("s = np.full(n, d / n)", "s = SUB_GAPS(d, n)").replace("p.d / (2.0 * p.n)", "SUB_GAPS(p.d, p.n)[0] / 2.0")
_NS = dict(laminate.__dict__)
_NS["SUB_GAPS"] = sub_gaps
exec(compile(_SRC, "laminate_build_variant", "exec"), _NS)
_VARIANT_BUILD = _NS["build"]


class VariantNetwork(fvm.Network):
    """!
    @brief fvm.Network with the film switch.
    """

    @property
    def cut_edge(self):
        """!
        @brief Whether the edge film is put in series (the program turns it off for imported copper on an outline).
        @return bool.
        """
        return self._ce

    @cut_edge.setter
    def cut_edge(self, v):
        """!
        @brief Set the switch, overridden by the study's `film`.
        @param v The program's value.
        @return None.
        """
        self._ce = True if CFG["film"] != "node" else v

    def _cut_edge_film(self, g0):
        """!
        @brief The program's series film with d scaled by alpha, the floor of the study, or d measured from the centroid of the board part of the cell (film 'centroid').
        @param g0 Edge conductance before the series term.
        @return Conductance after it.
        """
        a = CFG["alpha"]
        if CFG["film"] == "centroid":
            return self._centroid_film(g0, a)
        if a == 1.0 and CFG["floor"] is None:
            return super()._cut_edge_film(g0)
        old = fvm.EDGE_FILM_FLOOR
        if CFG["floor"] is not None:
            fvm.EDGE_FILM_FLOOR = CFG["floor"]
        sd = fvm.signed_distance_to_outline
        try:
            fvm.signed_distance_to_outline = lambda o, x, y: a * sd(o, x, y)
            return super()._cut_edge_film(g0)
        finally:
            fvm.signed_distance_to_outline = sd
            fvm.EDGE_FILM_FLOOR = old


def _centroid_film_impl(self, g0, a):
    """!
    @brief Series film with the distance from the centroid of the board part of the cell to the outline (always on the board side), scaled by `a`.
    @param g0 Edge conductance of every node layer before the series term, W/K.
    @param a Scale of the distance.
    @return Conductance after the series term.
    """
    from pcbthermal.geometry import exact_coverage, signed_distance_to_outline
    b = self.problem.board
    L = self._edge_lengths()
    sp_ = self._physical_sheet()
    H = np.zeros_like(g0)
    np.divide(g0, L[None], out=H, where=L[None] > 0)
    n = 8
    cov = exact_coverage(b.outline, self.nx * n, self.ny * n, self.dx / n, self.dy / n).astype(float)
    xs = (np.arange(self.nx * n) + 0.5) * self.dx / n
    ys = (np.arange(self.ny * n) + 0.5) * self.dy / n
    cv = cov.reshape(self.ny, n, self.nx, n)
    w = cv.sum(axis=(1, 3))
    cx = (cv * xs.reshape(1, 1, self.nx, n)).sum(axis=(1, 3)) / np.maximum(w, 1e-12)
    cy = (cv * ys.reshape(self.ny, n, 1, 1)).sum(axis=(1, 3)) / np.maximum(w, 1e-12)
    d = np.zeros((self.ny, self.nx))
    cells = np.argwhere((L > 0) & (w > 0))
    d[cells[:, 0], cells[:, 1]] = signed_distance_to_outline(b.outline, cx[cells[:, 0], cells[:, 1]], cy[cells[:, 0], cells[:, 1]])
    d = np.maximum(d, 0.0) * a
    with np.errstate(divide="ignore", invalid="ignore"):
        fac = np.where(sp_ > 0, 1.0 + H * d[None] / sp_, 1.0)
    fac = np.where(H > 0, np.maximum(fac, fvm.EDGE_FILM_FLOOR), 1.0)
    return np.where((g0 > 0) & (L[None] > 0), H * L[None] / fac, g0)


VariantNetwork._centroid_film = _centroid_film_impl


@contextlib.contextmanager
def use(**kw):
    """!
    @brief Run with the variant network and laminate builder and the given switches.
    @param kw Keys of CFG to set (film, alpha, grade, end, floor).
    @return Context manager.
    """
    old = dict(CFG)
    CFG.update(kw)
    net0, b0 = fvm.Network, laminate.build
    fvm.Network = VariantNetwork
    laminate.build = _VARIANT_BUILD
    try:
        yield
    finally:
        fvm.Network, laminate.build = net0, b0
        CFG.clear()
        CFG.update(old)
