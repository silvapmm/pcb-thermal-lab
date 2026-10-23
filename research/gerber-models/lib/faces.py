"""!
@file faces.py
@brief The import path of the research from the masks to the program: a `pcbthermal.Problem` for the imported board, the face conductances of every copper layer (every mapping of `METHODS`), and the program's own finite-volume network solved with them.
@details Phase 2 of the Gerber research (reading is phase 1, `research/gerber-import/lib/importer.py`). Stage 0 of `INTEGRATION.md` as research code (nothing in `pcbthermal/` is changed, the program is only imported):
         1. `to_problem` makes the program's `Problem` (size, number of layers, one `Via` per plated hole, the heater given by the caller); the copper is not given as zones.
         2. `layer_sheets` and `layer_faces` turn the masks into the sheet conductance of every pixel (the program's own two-phase formula) and into the face conductances of the cells (any mapping of `METHODS`).
         3. `solve_faces` runs the program's `fvm.Network` with those faces (a subclass that only replaces the lateral couplings of every layer, the vertical couplings, vias and losses are the program's);
            `solve_today` runs the program as it is, with one zone per cell whose fill is the copper fraction (what an import as a fill gives); `solve_fine` runs the program on the pixel grid, the reference.
         Limits: a rectangular board, plated holes become open barrels of the hole's diameter (a component lead is not modelled), one heater, steady state, no blocks.
         The names of the reading step are re-exported so that a study needs one import.
"""

import numpy as np
import scipy.sparse as sp

from pcbthermal import fvm
from pcbthermal.model import Problem

import conduction as cd
from importer import ImportedBoard, import_board, roles_of_downloaded      # noqa: F401  (re-exported)


def to_problem(ib, heater, thickness_mm=1.6, copper_um=35.0, h_face=10.0):
    """!
    @brief The program's Problem for the imported board: size, layers, one via per plated hole, one heater; no zones (the copper enters through the face conductances).
    @param ib Imported board.
    @param heater Dict with layer (1 = top), x, y (centre, board coordinates, mm), size (mm, square) and power (W).
    @param thickness_mm Board thickness (mm).
    @param copper_um Copper thickness of every layer (micrometres).
    @param h_face Heat transfer coefficient of the top and bottom faces (W/m2K).
    @return pcbthermal.Problem.
    """
    p = Problem.new(width_mm=ib.width, height_mm=ib.height, layers=max(len(ib.layers), 1), thickness_mm=thickness_mm, copper_um=copper_um, h_top=h_face, h_bottom=h_face, h_side=None)
    for r in ib.holes:
        p.add_via(r["bx"], r["by"], diameter=max(r["d"], 0.1))
    s = heater["size"] / 2.0
    p.add_heater(heater["layer"], heater["power"], rect=(heater["x"] - s, heater["y"] - s, heater["x"] + s, heater["y"] + s))
    return p


def phases(problem, layer=0):
    """!
    @brief The two phase conductances of the program's formula S = f k_cu t_cu + k_lam (slab - f t_cu) for one layer.
    @param problem Problem.
    @param layer Layer index (0 = top).
    @return Tuple (copper phase, laminate phase) in W/K.
    """
    b = problem.board
    k_lam, slab, tc = b.layer_laminate()[0][layer], b.slab_thicknesses()[layer], b.copper_thickness[layer]
    return b.materials.k_copper * tc + k_lam * (slab - tc), k_lam * slab


def layer_sheets(ib, problem, kind="coverage"):
    """!
    @brief The sheet conductance of every pixel of every layer, rows from the bottom (y up), as the program's grid.
    @param ib Imported board.
    @param problem Problem (for the phases).
    @param kind "coverage" (grey-level mask) or "binary".
    @return List of arrays (rows, cols), one per layer, top first.
    """
    out = []
    for l, ly in enumerate(ib.layers):
        a, b = phases(problem, l)
        m = ly[kind].astype(float)
        out.append((b + m * (a - b))[::-1])
    return out


METHODS = ("fill", "geometric", "bruggeman", "hs_lower", "hs_upper", "wiener_low", "wiener_up", "lambda", "cell_problem", "flow")


def layer_faces(sheets, ib, problem, method="flow"):
    """!
    @brief The face conductances of the cells of every layer.
    @param sheets List of pixel sheet conductance arrays.
    @param ib Imported board.
    @param problem Problem (for the phases).
    @param method One of METHODS: "fill" (the program's own formula, arithmetic fraction), "geometric", "bruggeman", "hs_lower", "hs_upper" (from the fraction alone); "wiener_low", "wiener_up", "lambda" (lambda 0.5), "cell_problem" (from the pixels, directional cell values); "flow" (flow-based faces, Sampson's method).
    @return List of (gx, gy) per layer.
    @throws ValueError If the method is not known.
    """
    if method not in METHODS:
        raise ValueError(f"unknown mapping {method!r}; known: {', '.join(METHODS)}")
    n = int(round(ib.cell / ib.pix))
    out = []
    for l, S in enumerate(sheets):
        a, b = phases(problem, l)
        if method == "flow":
            out.append(cd.dual_faces(S, n, 0))
            continue
        blk = cd.cell_blocks(S, n)
        if method == "lambda":
            sx, sy = cd.map_lambda(blk, 0.5)
        elif method in ("wiener_low", "wiener_up"):
            lx, ly, ux, uy = cd.map_bounds(blk)
            sx, sy = (lx, ly) if method == "wiener_low" else (ux, uy)
        elif method == "cell_problem":
            sx, sy = cd.map_cell_problem(blk)
        else:
            f = ((blk - b) / (a - b)).mean(axis=(2, 3))
            if method == "fill":
                sx = sy = cd.map_power(f, 1.0, a, b)
            elif method == "geometric":
                sx = sy = cd.map_power(f, 0.0, a, b)
            elif method == "bruggeman":
                sx = sy = cd.map_bruggeman(f, a, b)
            else:
                sx = sy = cd.map_hashin_shtrikman(f, "lower" if method == "hs_lower" else "upper", a, b)
        out.append(cd.faces_from_cells(sx, sy))
    return out


class FaceNetwork(fvm.Network):
    """!@brief The program's network with the lateral face conductances of every layer given from outside; vertical couplings, vias, losses and sources are the program's."""

    def set_faces(self, faces):
        """!
        @brief Replace the lateral couplings of the board layers and assemble.
        @param faces List of (gx, gy) per board layer, shapes (ny, nx - 1) and (ny - 1, nx), W/K.
        @return None.
        """
        self._faces = faces
        self.K = self._assemble()

    def _assemble(self):
        """!
        @brief The program's assembly with the lateral couplings replaced.
        @return Sparse matrix.
        """
        L, ny, nx = self.nl, self.ny, self.nx
        nb = self.n_board
        idx = np.arange(L * ny * nx).reshape(L, ny, nx)
        rows, cols, vals = [], [], []

        def couple(a_idx, b_idx, g):
            a, bb, gg = a_idx.ravel(), b_idx.ravel(), g.ravel()
            keep = gg > 0
            a, bb, gg = a[keep], bb[keep], gg[keep]
            rows.extend([a, bb, a, bb])
            cols.extend([a, bb, bb, a])
            vals.extend([gg, gg, -gg, -gg])

        for l, (gx, gy) in enumerate(self._faces):
            couple(idx[l, :, :-1], idx[l, :, 1:], gx)
            couple(idx[l, :-1, :], idx[l, 1:, :], gy)
        if nb > 1:
            couple(idx[:nb - 1], idx[1:nb], self.gz)
        n = L * ny * nx
        rows.append(np.arange(n))
        cols.append(np.arange(n))
        vals.append(self.g_amb.ravel())
        return sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()


def solve_faces(ib, problem, faces):
    """!
    @brief Solve the program's network on the cells of the board with the given faces.
    @param ib Imported board.
    @param problem Problem.
    @param faces List of (gx, gy) per layer.
    @return Temperature rise (layers, ny, nx) in K, rows from the bottom.
    """
    ny, nx = int(round(ib.height / ib.cell)), int(round(ib.width / ib.cell))
    net = FaceNetwork(problem, nx, ny, assemble=False)
    net.set_faces(faces)
    return net.solve_steady()[0]


def solve_today(ib, problem, kind="binary"):
    """!
    @brief The program as it is: one zone per cell whose fill is the copper fraction of the cell (the fill-fraction path), solved by the program's own network.
    @param ib Imported board.
    @param problem Problem (it is copied: zones are added to a copy).
    @param kind "binary" or "coverage" mask to take the fractions from.
    @return Temperature rise (layers, ny, nx) in K, rows from the bottom.
    """
    import copy
    p = copy.deepcopy(problem)
    n = int(round(ib.cell / ib.pix))
    for l, ly in enumerate(ib.layers):
        f = cd.cell_blocks(ly[kind].astype(float)[::-1], n).mean(axis=(2, 3))
        for i in range(f.shape[0]):
            for j in range(f.shape[1]):
                if f[i, j] > 1e-6:
                    p.add_zone(l + 1, rect=(j * ib.cell, i * ib.cell, (j + 1) * ib.cell, (i + 1) * ib.cell), fill=float(f[i, j]))
    ny, nx = int(round(ib.height / ib.cell)), int(round(ib.width / ib.cell))
    return fvm.Network(p, nx, ny).solve_steady()[0]


def solve_fine(ib, problem, kind="binary"):
    """!
    @brief The reference: the program's network on the pixel grid with the sheet conductance of every pixel.
    @param ib Imported board.
    @param problem Problem.
    @param kind "binary" or "coverage" mask.
    @return Temperature rise (layers, rows, cols) in K at the pixel grid, rows from the bottom.
    """
    ny, nx = int(round(ib.height / ib.pix)), int(round(ib.width / ib.pix))
    net = fvm.Network(problem, nx, ny, assemble=False)
    for l, S in enumerate(layer_sheets(ib, problem, kind)):
        net.S[l] = S * net.cover
    net.K = net._assemble()
    return net.solve_steady()[0]


def block_mean(field_px, ib):
    """!
    @brief Average a pixel-grid field over the cells.
    @param field_px Array (layers, rows, cols) on the pixel grid.
    @param ib Imported board.
    @return Array (layers, cell rows, cell cols).
    """
    n = int(round(ib.cell / ib.pix))
    L, ny, nx = field_px.shape
    return field_px.reshape(L, ny // n, n, nx // n, n).mean(axis=(2, 4))
