#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fvm.py
@brief Cell-centred finite-volume thermal solver for a multi-layer PCB (steady and transient).

@details Every copper layer is a 2D sheet of cells. A cell is a control volume of size
dx x dy and thickness t_pcb / layers. Heat flows

- sideways between neighbouring cells through the layer sheet conductance
  S = f * k_cu * t_cu + k_fr4_inplane * (slab - f * t_cu), where f is the copper fill,
- vertically between layers through the FR-4 dielectric (and the via barrels),
- to ambient through the top and bottom surfaces, the heatsinks and, optionally, the edges.

The steady problem is the sparse symmetric positive definite system K*theta = Q with
theta = T - T_ambient, solved directly (sparse LU) or with Conjugate Gradients. The transient
problem adds the heat capacity C and is advanced with the theta-method (implicit Euler or
Crank-Nicolson). Because the scheme is a finite-volume balance, the heat leaving the board
equals the injected power to solver precision, which the results report.
"""

import contextlib
import hashlib
import logging
import threading

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.sparse import csgraph

from . import copper, memory, blocks, laminate, viawell
from .geometry import (part_weights, edge_length_on_board, nearest_active_cell, coverage_fraction, cell_index_of_point, polygon_centroid, zone_fill,
                       face_apertures, signed_distance_to_outline)
from .results import SteadyResult, TransientResult
from .numfmt import num

# Column ordering of the sparse LU: the thermal matrices are symmetric, and the symmetric minimum-degree ordering gives about half
# the fill and 40 % less time than the default COLAMD (measured on the example board at 1 and 0.5 mm)
ORDERING = "MMD_AT_PLUS_A"

# Relative residual of the probe solve that a symmetric-mode factorisation must meet; above it the default (non-symmetric) factorisation is used
SYMMETRIC_LU_TOLERANCE = 1e-8
# Set to False (tests, studies) to force SuperLU's default non-symmetric mode everywhere
SYMMETRIC_LU = True

log = logging.getLogger(__name__)

# Blocks of the block SOR (unknowns of the merged footprints of vias that touch): the build of the dense inverse of a block of n unknowns takes about 75 n^2 bytes
# (measured 66 to 75 n^2; 5 000 unknowns are about 1.9 GB, not the 200 MB an earlier comment said) and every inverse is kept, so the sum over the blocks is allowed
# up to a quarter of the memory limit (memory.sor_block_fits). Above it the SOR solves the board with the direct solver instead and says so.

# Smallest value of the film denominator 1 + H d / S of the edge of a cut cell (see Network._cut_edge_film): the film in series with the conduction from the node to the
# outline can be made at most 1 / EDGE_FILM_FLOOR = 4 times stiffer than the film alone (a safety net for a node outside the board and a very stiff edge)
EDGE_FILM_FLOOR = 0.25

# Reuse of the last LU factorisation for a repeated matrix, only inside a factor_reuse() block (the top-path split solves the same board
# several times with other powers). One entry per thread, released before a new factorisation, so the peak memory is that of one LU, as with spsolve.
_REUSE = threading.local()


def lu_factor(A):
    """!
    @brief Sparse LU factorisation of a thermal matrix, in SuperLU's symmetric mode when the matrix allows it.
    @details The conductance matrices of the FVM, FDM and transient steps are symmetric and positive definite, so the diagonal is a good pivot:
             `diag_pivot_thresh=0` with `SymmetricMode` keeps the symmetric ordering (no row exchanges), which gives the same fill with far less work and
             workspace. The mode is used only after a cheap check (positive diagonal, symmetric values) and is kept only if a probe solve has a relative
             residual below SYMMETRIC_LU_TOLERANCE; if the check fails, the factorisation raises, or the residual is worse, the default mode is used
             instead (never a silent wrong answer). The probe measures the backward error of the factor (a pivot that breaks down, as on an indefinite
             matrix with a tiny diagonal, is caught: [[1e-14, 1], [1, 1e-14]] gives 7e-3); it does not measure the conditioning, so a nearly singular matrix
             (a board almost without a path to ambient) is solved as badly as by the default mode, which has no such check either. The default mode
             exchanged no row either on the boards measured (perm_r equal to perm_c): its extra time and memory are SuperLU's pivot search and workspace.
    @param A Square sparse matrix in W/K, any format.
    @return scipy.sparse.linalg.SuperLU object with a solve(b) method.
    """
    A = A.tocsc()
    if SYMMETRIC_LU and A.shape[0] > 0:
        lu = None
        try:
            scale = float(abs(A).max())
            # Symmetry to rounding (the assembly builds both triangles from the same couplings) and a positive diagonal
            if A.diagonal().min() > 0.0 and abs(A - A.T).max() <= 1e-12 * scale:
                lu = spla.splu(A, permc_spec=ORDERING, diag_pivot_thresh=0.0, options={"SymmetricMode": True})
                # The probe is a ramp, so that the residual tests the whole factor and not one eigenvector
                x0 = 1.0 + np.arange(A.shape[0], dtype=float) / A.shape[0]
                b0 = A @ x0
                rel = float(np.linalg.norm(A @ lu.solve(b0) - b0)) / max(float(np.linalg.norm(b0)), 1e-300)
                if np.isfinite(rel) and rel <= SYMMETRIC_LU_TOLERANCE:
                    return lu
                log.warning("Symmetric LU residual %.2e too large; using the default factorisation", rel)
        except (RuntimeError, ValueError, MemoryError) as exc:
            log.warning("Symmetric LU failed (%s); using the default factorisation", exc)
        lu = None                                  # Release a rejected factor before the default one is built (peak memory of one factorisation)
    return spla.splu(A, permc_spec=ORDERING)


@contextlib.contextmanager
def factor_reuse():
    """!
    @brief Within this block, a direct solve of a matrix identical to the previous one reuses its LU factorisation instead of factorising again.
    @details Used by api._solve_with_tc around the top-path split and the power-coefficient loop, and by inverse.power_from_temperature around its runs at
             other powers, which solve the same board with other part powers: with fixed face coefficients every board solve has the same matrix (6 factorisations
             become 1 for one part with a top path, 4 become 1 for the Power Calculator; with computed coefficients the matrix changes at every Picard step and
             nothing is reused). One factorisation is kept at a time (the old one is released before a new one is made), and it is
             released when the outermost block ends, so the peak memory is that of a plain solve. SuperLU's splu + solve gives the same numbers as spsolve
             with the same column ordering (tests/test_top_path.py checks it to 1e-9 K). Nested blocks share the outer one.
    @return Context manager (yields nothing).
    """
    outer = getattr(_REUSE, "slot", None)
    if outer is None:
        _REUSE.slot = {}
    try:
        yield
    finally:
        if outer is None:
            _REUSE.slot = None                     # Release the kept factorisation


def direct_solve(A, b):
    """!
    @brief Sparse direct solve A x = b with the column ordering ORDERING; reuses the previous factorisation of an identical matrix inside factor_reuse().
    @param A Sparse matrix (any format; converted to CSC).
    @param b Right-hand side, 1D array.
    @return numpy.ndarray Solution x.
    """
    slot = getattr(_REUSE, "slot", None)
    if slot is None:
        return lu_factor(A).solve(np.asarray(b, dtype=float))
    A = A.tocsc()
    A.sum_duplicates()                             # Canonical form, so that equal matrices give equal bytes
    # The key is the exact content (structure and values), hashed: two matrices differ by a face coefficient in the computed-h loop
    digest = hashlib.blake2b(digest_size=20)
    # (the dtypes go in too, so that the byte stream parses one way only; a 160-bit digest makes an accidental collision of two consecutive matrices
    # about 2^-160, and a different key only costs a new factorisation, never a wrong reuse)
    digest.update(f"{A.indptr.dtype.str}{A.indices.dtype.str}{A.data.dtype.str}".encode())
    for arr in (np.asarray(A.shape), A.indptr, A.indices, A.data):
        digest.update(np.ascontiguousarray(arr).tobytes())
    key = digest.hexdigest()
    if slot.get("key") != key:
        slot.clear()                               # Release the old LU before the new one is made (peak memory of one factorisation)
        slot["lu"] = lu_factor(A)
        slot["key"] = key
        _REUSE.count = getattr(_REUSE, "count", 0) + 1
    return slot["lu"].solve(np.asarray(b, dtype=float))


def factorisation_count():
    """!
    @brief Number of LU factorisations made inside factor_reuse() blocks by this thread since the start (for the tests).
    @return int.
    """
    return int(getattr(_REUSE, "count", 0))


class Network:
    """!
    @brief Assembled thermal network: conductances, capacities, sources and the sparse matrix.
    """

    def __init__(self, problem, nx, ny, assemble=True, with_blocks=True, ladder=True, faces=None, cut_cells=True):
        """!
        @brief Build the network of a problem on an nx x ny grid.
        @param problem A validated Problem.
        @param nx Number of cells along x.
        @param ny Number of cells along y.
        @param assemble If False, skip building the sparse matrix (the lumped model only needs the per-cell arrays).
        @param with_blocks If False the metal blocks (heatsinks with a thickness) are left out: the heatsinks only add their coefficient on the
               board face (the lumped and analytic models see them that way).
        @param ladder True: the laminate nodes of the rule (laminate.py) in the cells with absent copper, and the bottom node of a one-layer board; False: the network of the earlier
               versions (one node per copper layer, the two laminate nodes of a one-layer board), which the Lumped model reads ring by ring. A problem with a metal block always
               gets the earlier treatment.
        @param faces Imported copper (copper.py): None takes `problem.imported` when it has masks (and nothing changes for a problem without), False ignores it, or a
               copper.CopperSource. The cell fill of the imported layers comes from the masks; with the "faces" or "lambda" mapping the in-plane couplings of those layers are
               the face conductances of the reduced sheet (built when the matrix is assembled), with "fill" the program's harmonic mean of the cell values.
        @param cut_cells True (default): the cut-cell treatment of the board edge: the links of a board with an outline carry the open fraction of the shared face (the aperture,
               `geometry.face_apertures`) on the physical sheet, and the edge film h_side is in series with the conduction from the node to the closest outline point (on a rectangle:
               to the edge, half a cell away). False: the earlier treatment (links of the cover-scaled sheets, the film on the node); the Lumped model, which reads the per-cell
               arrays ring by ring and never sees the links, asks for it so that its numbers do not move. A problem with an outline and imported copper always keeps the earlier
               treatment (`cut_cells_note` says so).
        """
        problem.validate()
        self.problem = problem
        b = problem.board
        m = b.materials
        self.nx, self.ny, self.nl = nx, ny, b.layers
        self.n_board = b.layers                        # Board layers; the metal blocks, if any, add layers after them
        self.extra_links = []                          # (layer a, layer b, conductance array) between non-adjacent layers
        self.block_info = []
        self.laminate_layers = []                      # Indices of the laminate node layers of a one-layer board (laminate.py)
        use_rule = bool(ladder) and laminate.uses_rule(problem)
        self.ladder = None                             # laminate.Ladder when the rule was applied
        self.drop = None                               # Boolean (nl, ny, nx) of the nodes that no cell uses (left out of the direct solve)
        self.dx, self.dy = b.width / nx, b.height / ny
        L, dx, dy = b.layers, self.dx, self.dy
        # Fraction of every cell that is board (all ones for a rectangle); cells off the board carry nothing
        self.cover = b.cover(nx, ny, dx, dy)
        self.active = self.cover > 0
        cell = dx * dy * self.cover          # Board area of every cell (m2), (ny, nx)
        slab = b.slab_thicknesses()          # Thickness represented by each layer node (m)
        k_lam, rho_cp_lam = b.layer_laminate()   # In-plane conductivity and volumetric heat capacity of the dielectric part of each node
        t_cu = np.asarray(b.copper_thickness)
        # A one-layer board gets laminate nodes under its copper (laminate.py): the copper node keeps the copper and half a gap
        self.laminate = None if use_rule else laminate.nodes(b)        # (the rule gives a one-layer board its bottom node in _add_ladder instead)
        if self.laminate is not None:
            slab = np.array([self.laminate.copper_slab])
        if np.any(t_cu >= slab):
            raise ValueError("copper thickness must be smaller than thickness / layers")

        # --- Copper fill fraction of every layer (union of its zones, hatching via 'fill')
        self.copper = copper.resolve(faces, problem)                     # The imported copper (masks), or None for a drawn board
        f = zone_fill(problem.zones, L, nx, ny, dx, dy, samples=4)      # Union per sample point, not per cell (geometry.zone_fill)
        copper.override_fill(f, self.copper, ny, nx, b.width, b.height)  # The imported layers come from their masks
        self.fill = f
        # The cut-cell treatment is not applied where the imported faces would mix with it: the faces of an imported layer are built from pixel sheets times the cell cover
        # (copper.lateral), so the aperture would have to enter there as a pixel-level mask of the board; until then a board with an outline and imported copper keeps the
        # cover-weighted links and the film on the node in all its layers (one consistent treatment), and the run says so
        self.cut_cells_note = None
        self.cut_edge = bool(cut_cells)
        self.cut_links = bool(cut_cells) and b.has_outline()
        if cut_cells and b.has_outline() and self.copper is not None:
            # (no note when the outline is the whole box: no cell is cut, only the half-cell series term of the border film is left out)
            self.cut_cells_note = copper.CUT_CELLS_IMPORTED_NOTE if copper.outline_cuts_cells(b) else None
            self.cut_edge = self.cut_links = False

        # --- Sheet conductance (W/K) and heat capacity (J/K) of every cell
        tc = t_cu[:, None, None]
        diel_t = slab[:, None, None] - f * tc          # Dielectric thickness left in the slab (m)
        self.S = (f * m.k_copper * tc + k_lam[:, None, None] * diel_t) * self.cover
        self.C = (f * m.rho_copper * m.cp_copper * tc + diel_t * rho_cp_lam[:, None, None]) * cell

        # --- Vertical conductance between layer l and l+1 (W/K)
        self.gz = np.zeros((max(L - 1, 0), ny, nx))
        self.via_blocks, self.gz_via = [], np.zeros_like(self.gz)
        if L > 1:
            d = b.gap_thicknesses()                    # One value per gap (equal in the simple stack-up)
            k_gap = b.gap_properties()[0]
            self.gz[:] = k_gap[:, None, None] * cell[None] / d[:, None, None]    # Dielectric alone
            # The barrel is not added to gz: every via is a mean-potential coupling of a footprint of cells (viawell.py), appended to the matrix in
            # _assemble. gz_via keeps the point conductance in the cell of the via centre, which the Lumped model reads ring by ring (gz + gz_via)
            self.via_blocks, self.gz_via = viawell.build(problem, d, self.S, self.cover, dx, dy, nx, ny, 0.0, self.active)

        # --- Conductance to ambient (W/K): top, bottom, heatsinks and edges are kept separate
        self.g_top = np.zeros((L, ny, nx))
        self.g_bottom = np.zeros((L, ny, nx))
        self.g_heatsink = np.zeros((L, ny, nx))
        self.g_side = np.zeros((L, ny, nx))
        self.g_top[0] = b.h_top * cell
        if self.laminate is None:
            self.g_bottom[L - 1] = b.h_bottom * cell   # (With laminate nodes the bottom film acts on the last of them, below)
        for s in problem.heatsinks:
            if s.is_block() and with_blocks:
                continue                               # A metal block is a layer of its own (below)
            cov = coverage_fraction(s.polygon, nx, ny, dx, dy, samples=4)
            self.g_heatsink[s.layer] += s.h_extra * cell * cov
        self.g_block = np.zeros((L, ny, nx))
        if self.laminate is not None:
            self._add_laminate(b, cell)
        if with_blocks:
            area = cell.copy()
            # The block is cut at the board outline: a cell off the board carries no block (it would be pinned to the ambient and drain the block)
            layers = blocks.extra_layers(problem, lambda poly, n: coverage_fraction(poly, nx, ny, dx, dy, samples=n) * self.cover, area, f, dx, dy)
            self._add_blocks(layers)
        if b.h_side and b.has_outline():
            # Edge of a non-rectangular board: the length of the outline inside every cell times the slab thickness
            edge = edge_length_on_board(b.outline, nx, ny, dx, dy, self.active)
            self.g_side[:L] += b.h_side * slab[:, None, None] * edge[None]
        elif b.h_side:
            # Each edge cell exposes a face of (cell edge length) x (slab thickness)
            sl = slab[:, None]
            self.g_side[:L, :, 0] += b.h_side * dy * sl
            self.g_side[:L, :, -1] += b.h_side * dy * sl
            self.g_side[:L, 0, :] += b.h_side * dx * sl
            self.g_side[:L, -1, :] += b.h_side * dx * sl
        # The faces of the imported layers are built on the sheet the copper node keeps after the rule: keep the sheet before it and the two-phase values of a pixel
        self._lateral = None
        self._face_context = None
        if self.copper is not None and self.copper.mapping != "fill" and assemble:
            # (sheet of the copper nodes before the rule, sheet of a pixel with copper, sheet of a bare pixel), the last two per layer in W/K
            self._face_context = (self.S[:L].copy(), m.k_copper * t_cu + k_lam * (slab - t_cu), k_lam * slab)
        pin_extra = self._add_ladder(b, cell) if use_rule else None      # After the edge conductance: the new nodes take their share of it from the copper nodes
        self.aperture = None
        if self.cut_links:
            # Open fraction of every interior face (only the board edge cuts a face); a face between two whole cells is exactly 1
            self.aperture = face_apertures(b.outline, nx, ny, dx, dy, cover=self.cover)
        if self.cut_edge and b.h_side:
            self.g_side = self._cut_edge_film(self.g_side)
        self.g_amb = self.g_top + self.g_bottom + self.g_heatsink + self.g_side + self.g_block
        # Cells off the board are isolated: pin them to ambient so the matrix stays regular (they carry no heat: theta = 0).
        # The pin is kept apart (g_pin) because it is not a path to the air: the time constant must leave it out
        self.g_pin = np.zeros_like(self.g_amb)
        self.g_pin[:, ~self.active] = 1.0
        if pin_extra is not None:
            self.g_pin[L:] = np.maximum(self.g_pin[L:], pin_extra)             # Laminate nodes of the cells that do not use them are pinned too (and dropped from the direct solve)
        self.g_amb = self.g_amb + self.g_pin

        # --- Heat sources (W): the requested power is spread exactly over the covered cells.
        # The unit-power distribution of every heater (weights that sum to 1) is kept, so that the source of a
        # power profile can be rebuilt at every time step as a matrix-vector product.
        self.Qw = []
        L = self.nl                                    # Board layers plus the block layers
        self.Q = np.zeros((L, ny, nx))
        for h in problem.heaters:
            # Heated only where it is both on the part and on the board (intersection per sample), scaled to the board cover of the cell
            cov = part_weights(h.polygon, b.outline, nx, ny, dx, dy, cover=self.cover) * self.active
            if cov.sum() <= 0:
                # Footprint smaller than the sampling: put all the power in the centroid cell
                cx, cy = polygon_centroid(h.polygon)
                i, j = cell_index_of_point(cx, cy, nx, ny, dx, dy)
                if not self.active[i, j]:                      # A part off the board: its power goes to the nearest board cell
                    i, j = nearest_active_cell(self.active, cx, cy, dx, dy)
                cov[i, j] = 1.0
            w = np.zeros((L, ny, nx))
            w[h.layer] = cov / cov.sum()
            self.Qw.append(w)
            self.Q += h.power * w
        n_cells = L * ny * nx
        # Sparse (cells x heaters) matrix of the weights, and the flat indices of every footprint
        self.Qw_matrix = sp.csc_matrix(np.stack([w.ravel() for w in self.Qw], axis=1)) if self.Qw \
            else sp.csc_matrix((n_cells, 0))
        self.footprints = [np.flatnonzero(w.ravel() > 0) for w in self.Qw]

        self.K = self._assemble() if assemble else None

    def _edge_lengths(self):
        """!
        @brief Length of the board edge exposed in every cell (m): the outline inside the cell, or the cell sides on the border of a rectangle.
        @return Array (ny, nx).
        """
        b = self.problem.board
        if b.has_outline():
            return edge_length_on_board(b.outline, self.nx, self.ny, self.dx, self.dy, self.active)
        e = np.zeros((self.ny, self.nx))
        e[:, 0] += self.dy
        e[:, -1] += self.dy
        e[0, :] += self.dx
        e[-1, :] += self.dx
        return e

    def _add_laminate(self, b, cell):
        """!
        @brief Append the laminate nodes of a one-layer board (laminate.py) as node layers under the copper, joined by vertical conductances.
        @param b The Board.
        @param cell Board area of every cell (m2), shape (ny, nx).
        """
        layers = laminate.extra_layers(b, self.laminate, cell, self.cover, self._edge_lengths(), b.h_side)
        zeros = np.zeros((len(layers), self.ny, self.nx))
        base = self.nl
        self.S = np.concatenate([self.S, np.stack([ly["S"] for ly in layers])])
        self.C = np.concatenate([self.C, np.stack([ly["C"] for ly in layers])])
        self.g_top = np.concatenate([self.g_top, zeros])
        self.g_bottom = np.concatenate([self.g_bottom, np.stack([ly["g_bottom"] for ly in layers])])
        self.g_heatsink = np.concatenate([self.g_heatsink, zeros])
        self.g_side = np.concatenate([self.g_side, np.stack([ly["g_side"] for ly in layers])])
        self.g_block = np.concatenate([self.g_block, zeros])
        for k, ly in enumerate(layers):
            self.extra_links.append((base + k - 1 if k else 0, base + k, ly["g_link"]))
        self.laminate_layers = list(range(base, base + len(layers)))
        self.nl = base + len(layers)

    def _add_ladder(self, b, cell):
        """!
        @brief Apply the rule of laminate.py: interior laminate nodes in the cells with absent copper (plus a margin), the bottom node of a one-layer board, the vertical correction.
        @details Changes the arrays of the copper nodes (S, C, gz, g_bottom, g_side), appends the new node layers after them and registers their links; boards with copper in every cell
                 get no new node and keep the arrays of the earlier versions bit for bit (a one-layer board gets its bottom node).
        @param b The Board.
        @param cell Board area of every cell (m2), shape (ny, nx).
        @return Boolean array (new layers, ny, nx) of the new nodes that are pinned (unused or off the board), or None when no layer was added.
        """
        edge = self._edge_lengths() if b.h_side else np.zeros((self.ny, self.nx))
        plans = laminate.plan_gaps(b, self.fill, self.dx, self.active, edge=edge)
        res = laminate.build(b, self.fill, cell, self.cover, self.active, edge, self.S, self.C, self.gz, self.g_bottom, self.g_side, plans)
        self.S, self.C, self.gz, self.g_bottom, self.g_side = res.S, res.C, res.gz, res.g_bottom, res.g_side
        self.ladder, self.drop = res.ladder, res.ladder.drop
        k = len(res.layers)
        if not k:
            return None
        zeros = np.zeros((k, self.ny, self.nx))
        self.S = np.concatenate([self.S, np.stack([ly["S"] for ly in res.layers])])
        self.C = np.concatenate([self.C, np.stack([ly["C"] for ly in res.layers])])
        self.g_top = np.concatenate([self.g_top, zeros])
        self.g_heatsink = np.concatenate([self.g_heatsink, zeros])
        self.g_block = np.concatenate([self.g_block, zeros])
        self.g_bottom = np.concatenate([self.g_bottom, np.stack([ly["g_bottom"] for ly in res.layers])])
        self.g_side = np.concatenate([self.g_side, np.stack([ly["g_side"] for ly in res.layers])])
        self.extra_links = list(res.links)
        if res.ladder.bottom_layer >= 0:
            self.laminate_layers = [res.ladder.bottom_layer]          # The bottom face of a one-layer board (the computed coefficients read it)
        self.nl = b.layers + k
        return np.stack([ly["pin"] | ~self.active for ly in res.layers])

    def _add_blocks(self, layers):
        """!
        @brief Append the layers of the metal blocks to the arrays of the network (see blocks.py).
        @param layers List from blocks.extra_layers.
        """
        if not layers:
            return
        base, ny, nx = self.nl, self.ny, self.nx            # The block layers come after the board and the laminate nodes
        E = len(layers)
        zeros = np.zeros((E, ny, nx))
        self.S = np.concatenate([self.S, np.stack([ly["S"] for ly in layers])])
        self.C = np.concatenate([self.C, np.stack([ly["C"] for ly in layers])])
        for name in ("g_top", "g_bottom", "g_heatsink", "g_side"):
            setattr(self, name, np.concatenate([getattr(self, name), zeros]))
        self.g_block = np.concatenate([self.g_block, np.stack([ly["g_amb"] for ly in layers])])
        # (g_pin is built after the blocks, so it already has their layers)
        for k, ly in enumerate(layers):
            idx = base + k
            self.extra_links.append((ly["board_layer"], idx, ly["g_link"]))
            # The face covered by the block no longer exchanges heat with the air
            (self.g_top if ly["face"] == 0 else self.g_bottom)[ly["board_layer"]] *= ly["face_scale"]
            self.block_info.append({"layer": idx, "face": ly["face"], "cov": ly["cov"], "names": ly["names"],
                                    "g_link": ly["g_link"], "board_layer": ly["board_layer"]})
        self.nl = base + E

    def _physical_sheet(self):
        """!
        @brief Sheet conductance of every node layer without the cover factor: the sheet of the board material itself (W/K), zero off the board.
        @return Array (nl, ny, nx).
        """
        out = np.zeros_like(self.S)
        np.divide(self.S, self.cover[None], out=out, where=self.cover[None] > 0)
        return out

    def _cut_edge_film(self, g0):
        """!
        @brief Put the conduction from the node to the closest edge point in series with the edge film h_side (Robin condition of a cut cell: Papac, Gibou and Ratsch 2010; Bochkov and Gibou 2019 eqs. 1.7, 1.13, 1.14; Barrett, Fogelson and Griffith 2022 eqs. 12 to 14).
        @details The film of a cell is H L with H = h_side times the slab (W/m K) and L the edge length in the cell. The node is the cell centre, a distance d from the edge,
                 so the heat passes the sheet from the node to the edge, d / (S L), and then the film: g = g0 / (1 + g0 d / (S L)) = H L / (1 + H d / S) (L cancels), with S the
                 physical sheet of the node. For an outline d is the signed distance from the cell centre to the closest outline point (negative for a centre outside the board,
                 which stiffens the film); for the border of a rectangle d is half a cell normal to the edge (a corner cell has two edges, each with its own d). The denominator is
                 floored at EDGE_FILM_FLOOR so that it cannot vanish or turn negative; it is reached only where a node lies outside the board by more than S / H (bare-laminate
                 nodes of a cut cell at about 1000 W/m2K and above, or an edge coefficient beyond any physical film). Nodes with no sheet keep their film unchanged.
                 The ambient term is scaled with the same factor as the conductance (the change goes into g_amb), so a constant field is reproduced to round-off; the unfloored
                 form fails for a node outside the board with a large cell Biot number, which is why the floor is kept (condition 1.21 of Bochkov and Gibou: mu - alpha d > 0).
        @param g0 Edge conductance of every node layer before the series term, W/K, shape (nl, ny, nx).
        @return The conductance after it, same shape; the heat balance of `power_out` follows because the diagonal is built from it.
        """
        L = self._edge_lengths()
        sp_ = self._physical_sheet()
        H = np.zeros_like(g0)
        np.divide(g0, L[None], out=H, where=L[None] > 0)
        b = self.problem.board
        if b.has_outline():
            d = np.zeros((self.ny, self.nx))
            cells = np.argwhere(L > 0)
            if len(cells):
                x = (cells[:, 1] + 0.5) * self.dx
                y = (cells[:, 0] + 0.5) * self.dy
                d[cells[:, 0], cells[:, 1]] = signed_distance_to_outline(b.outline, x, y)
            pieces = [(L, d)]
        else:
            cols = np.zeros((self.ny, self.nx))
            rows = np.zeros((self.ny, self.nx))
            cols[:, 0] += 1.0
            cols[:, -1] += 1.0
            rows[0, :] += 1.0
            rows[-1, :] += 1.0
            pieces = [(cols * self.dy, 0.5 * self.dx), (rows * self.dx, 0.5 * self.dy)]
        new = np.zeros_like(g0)
        for length, dist in pieces:
            with np.errstate(divide="ignore", invalid="ignore"):
                fac = np.where(sp_ > 0, 1.0 + H * dist / sp_, 1.0)
            fac = np.where(H > 0, np.maximum(fac, EDGE_FILM_FLOOR), 1.0)
            new += H * length[None] / fac
        return np.where((g0 > 0) & (L[None] > 0), new, g0)

    def _lateral_links(self):
        """!
        @brief Conductances (W/K) of the lateral links of every node layer: the x links (ny, nx - 1) and the y links (ny - 1, nx) of the assembled matrix and of the SOR.
        @details The program's link between two cells is the harmonic mean of the two sheets over one cell width. The sheets of a cut cell are scaled by its cover, so that link
                 is a factor c too weak into a cut cell (the whole cell side is open to the heat, not c of it). With the aperture the link is a S dy / dx with S the PHYSICAL sheet
                 (the cover-scaled one over the cover) and a the open fraction of the shared face, which is the program's link bit for bit where both cells are whole (a = 1, cover 1).
                 Block layers keep the cover-scaled links. The faces of the imported layers replace these (`_imported_faces`).
        @return Tuple (gx, gy) of arrays (nl, ny, nx - 1) and (nl, ny - 1, nx).
        """
        S = self.S
        gx = self._harmonic(S[:, :, :-1], S[:, :, 1:]) * self.dy / self.dx
        gy = self._harmonic(S[:, :-1, :], S[:, 1:, :]) * self.dx / self.dy
        if self.aperture is not None:
            ax, ay = self.aperture
            sp_ = self._physical_sheet()
            cx = ax[None] * self._harmonic(sp_[:, :, :-1], sp_[:, :, 1:]) * self.dy / self.dx
            cy = ay[None] * self._harmonic(sp_[:, :-1, :], sp_[:, 1:, :]) * self.dx / self.dy
            use = np.ones(self.nl, bool)
            for info in self.block_info:
                use[info["layer"]] = False
            gx[use] = cx[use]
            gy[use] = cy[use]
        for layer, (fx, fy) in self._imported_faces().items():          # Imported copper: the face conductances of the reduced sheet
            on = self.active
            gx[layer] = fx * (on[:, :-1] & on[:, 1:])
            gy[layer] = fy * (on[:-1, :] & on[1:, :])
        return gx, gy

    def _imported_faces(self):
        """!
        @brief The face conductances of the imported layers, built once on the sheet the copper node keeps after the laminate rule.
        @details dS = (sheet before the rule - sheet after it) / cover is what the rule moved into the interior laminate nodes of the cell; it is taken off every pixel of the
                 cell before the faces are computed (copper.py), so the laminate is not counted twice. Without the rule dS is zero.
        @return dict layer index -> (gx (ny, nx - 1), gy (ny - 1, nx)) in W/K; empty for a drawn board or the "fill" mapping.
        """
        if self._lateral is None:
            self._lateral = {}
            if self._face_context is not None:
                s_pre, a_full, b_bare = self._face_context
                b = self.problem.board
                with np.errstate(divide="ignore", invalid="ignore"):
                    for layer in self.copper.layers:
                        red = np.where(self.cover > 0, np.maximum(s_pre[layer] - self.S[layer], 0.0) / self.cover, 0.0)
                        self._lateral[layer] = self.copper.lateral(layer, a_full[layer], b_bare[layer], red, self.cover, self.ny, self.nx, b.width, b.height)
                self._face_context = None                       # The copy of the sheet is not needed again
        return self._lateral

    # ------------------------------------------------------------------ assembly
    @staticmethod
    def _harmonic(a, b):
        """!
        @brief Harmonic mean of two conductances (series combination of the half cells).
        @param a First array.
        @param b Second array.
        @return Array with 2ab/(a+b), zero where both are zero.
        """
        s = a + b
        out = np.zeros_like(s)
        np.divide(2.0 * a * b, s, out=out, where=s > 0)
        return out

    def _assemble(self):
        """!
        @brief Assemble the sparse conductance matrix K (W/K).
        @return scipy.sparse.csr_matrix of shape (N, N), N = layers * ny * nx.
        """
        L, ny, nx = self.nl, self.ny, self.nx
        nb = self.n_board
        idx = np.arange(L * ny * nx).reshape(L, ny, nx)
        rows, cols, vals = [], [], []

        def couple(a_idx, b_idx, g):
            # A symmetric coupling g between nodes a and b adds +g to both diagonals and -g off diagonal
            a, bb, gg = a_idx.ravel(), b_idx.ravel(), g.ravel()
            keep = gg > 0
            a, bb, gg = a[keep], bb[keep], gg[keep]
            rows.extend([a, bb, a, bb])
            cols.extend([a, bb, bb, a])
            vals.extend([gg, gg, -gg, -gg])

        # Lateral couplings: face width / distance gives dy/dx (x) and dx/dy (y), times the open fraction of the face on a board with an outline
        gx, gy = self._lateral_links()
        couple(idx[:, :, :-1], idx[:, :, 1:], gx)
        couple(idx[:, :-1, :], idx[:, 1:, :], gy)
        if nb > 1:
            couple(idx[:nb - 1], idx[1:nb], self.gz)
        for a_layer, b_layer, g in self.extra_links:           # Contact of a metal block with its board face
            couple(idx[a_layer], idx[b_layer], g)
        # The mean-potential couplings of the vias (they add to the diagonal and couple the footprint cells of the layers they join)
        vr, vc, vv = viawell.matrix_entries(self.via_blocks, idx)
        rows.extend(vr)
        cols.extend(vc)
        vals.extend(vv)
        # Conductance to ambient only adds to the diagonal
        n = L * ny * nx
        diag = self.g_amb.ravel()
        rows.append(np.arange(n))
        cols.append(np.arange(n))
        vals.append(diag)
        K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                          shape=(n, n)).tocsr()
        return K

    # ------------------------------------------------------------------ solving
    def solve_steady(self, method="direct", rtol=1e-12):
        """!
        @brief Solve K*theta = Q for the steady temperature rise.
        @param method "direct" (sparse LU) or "cg" (Conjugate Gradients, Jacobi preconditioned).
        @param rtol Relative tolerance for "cg".
        @return Tuple (theta, residual): rise array of shape (layers, ny, nx) and relative residual.
        @throws RuntimeError If the iterative solver does not converge.
        """
        q = self.Q.ravel()
        if method == "direct":
            if self.drop is not None and self.drop.any():
                # Ragged solve: the laminate nodes that no cell uses (outside the flagged cells) are pinned rows of the matrix; leave them out of the factorisation
                keep = np.flatnonzero(~self.drop.ravel())
                theta = np.zeros(self.K.shape[0])
                theta[keep] = direct_solve(self.K.tocsr()[keep][:, keep], q[keep])
            else:
                theta = direct_solve(self.K, q)
        elif method == "cg":
            # Jacobi (diagonal) preconditioner keeps CG cheap and robust for SPD thermal matrices
            dinv = 1.0 / self.K.diagonal()
            M = spla.LinearOperator(self.K.shape, matvec=lambda x: dinv * x)
            theta, info = spla.cg(self.K, q, rtol=rtol, atol=0.0, maxiter=20000, M=M)
            if info != 0:
                raise RuntimeError(f"CG did not converge (info={info})")
        else:
            raise ValueError("method must be 'direct' or 'cg'")
        res = np.linalg.norm(self.K @ theta - q) / max(np.linalg.norm(q), 1e-300)
        return theta.reshape(self.nl, self.ny, self.nx), float(res)

    def sor_omega(self):
        """!
        @brief Estimate of Young's optimum relaxation factor of the red-black SOR from the Rayleigh quotient of the Jacobi matrix.
        @details For the symmetric positive definite K = D - N with a two-colourable graph (the parity of l + i + j) the optimum is 2 / (1 + sqrt(1 - rho^2)), rho the
                 spectral radius of D^-1 N (Young; Saad 2003, section 4.2.5, Theorem 4.16 and eq. 4.47, pp 126-127; the theorem holds for consistently ordered matrices). rho is bounded from below by the Rayleigh quotient 1 - (m^T K m) / (m^T D m) of the trial
                 vector m = D^1/2 1 restricted to the nodes that have a link: one product with K, always a LOWER bound, so the omega that follows is below the optimum (safe side).
                 K is the full matrix that the SOR solves, with the via couplings and the footprints. Nodes without any link (the cells off a board with an outline, pinned to the ambient)
                 are left out of both sums: they are eigenvectors with mu = 0 and would dilute the quotient (omega near 1 on a round board). The result is capped at 1.999 as a guard.
                 The old formula 2 / (1 + sin(pi / n)) is the optimum of a plate with fixed edges, and was 2.8 to 19 times slower on boards with insulated edges (research/young-omega-tiles).
        @return float Relaxation factor in [1, 1.999].
        """
        K = self.K.tocsr()
        d = np.asarray(K.diagonal(), float)
        # Nodes with at least one off-diagonal entry: the row has more stored entries than the diagonal, or a stored off-diagonal that is not zero
        off = np.asarray(abs(K).sum(axis=1)).ravel() - np.abs(d)
        m = (off > 0).astype(float)
        den = float(m @ d)
        if den <= 0.0:
            return 1.0
        rho = 1.0 - float(m @ (K @ m)) / den
        rho = min(max(rho, 0.0), 1.0)
        return float(min(2.0 / (1.0 + np.sqrt(1.0 - rho * rho)), 1.999))

    def solve_sor(self, omega=None, tol=1e-9, max_iter=200000, criterion="residual", memory_limit=None):
        """!
        @brief Solve K*theta = Q with red-black Successive Over-Relaxation (vectorised with NumPy).
        @details Every sweep updates the "red" nodes (l+i+j even) and then the "black" ones, each colour in one
                 array operation, so the iteration is the classical SOR of the original program but fast.
                 theta_new = (sum_m G_m theta_m + Q) / diag, theta += omega * (theta_new - theta).
                 The cells of the vias are updated as dense blocks after the colours (block SOR).
        @param omega Relaxation factor; None picks the estimate of Young's optimum of `sor_omega` (below 2, on the safe side).
        @param tol Stopping tolerance.
        @param max_iter Sweep limit.
        @param criterion "residual" stops when |K theta - Q| / |Q| < tol (reliable);
                         "step" stops when the largest change of one sweep is below tol in kelvin
                         (the rule of the original program, which can stop far from the solution).
        @param memory_limit Memory limit in bytes of the guard (None: memory.limit_bytes()); the dense inverses of the via blocks may take a quarter of it.
        @return Tuple (theta, residual, info) with info = dict(iterations, converged, omega, last_step); a board with vias whose footprint blocks would need more than a
                 quarter of the memory limit (75 n^2 bytes for a block of n unknowns, summed over the blocks, since every inverse is kept) is solved directly
                 (info["fallback"] = "direct", info["block"] = the largest n, info["block_bytes"] = the sum).
        """
        if self.block_info:
            raise ValueError("SOR does not support metal blocks: use the direct solver or the conjugate gradients")
        L, ny, nx = self.nl, self.ny, self.nx
        K, Q = self.K, self.Q
        if omega is None:
            omega = self.sor_omega()
        if self.ladder is not None and self.nl > self.n_board:
            # Laminate nodes of the rule: the vertical neighbour is no longer layer +- 1 and no point colouring exists, so the plan columns are relaxed as blocks
            return self._sor_columns(omega, tol, max_iter, criterion, memory_limit)
        diag = K.diagonal().reshape(L, ny, nx)
        # Conductances towards the six neighbours (zero where the neighbour does not exist)
        gl = np.zeros((L, ny, nx)); gr = np.zeros((L, ny, nx))     # x-1, x+1
        gd = np.zeros((L, ny, nx)); gu = np.zeros((L, ny, nx))     # y-1, y+1
        ga = np.zeros((L, ny, nx)); gb = np.zeros((L, ny, nx))     # layer-1, layer+1
        gx, gy = self._lateral_links()                                  # (the same links as the matrix: aperture and imported faces included)
        gr[:, :, :-1], gl[:, :, 1:] = gx, gx
        gu[:, :-1, :], gd[:, 1:, :] = gy, gy
        if L > 1:
            # Vertical conductances between consecutive node layers: the dielectric gaps of the board and the links of the laminate nodes
            gzz = np.zeros((L - 1, ny, nx))
            gzz[:self.n_board - 1] = self.gz
            for a, b_layer, g in self.extra_links:
                gzz[a] += g                            # The laminate links join consecutive layers (a, a + 1)
            gb[:-1], ga[1:] = gzz, gzz
        l_i, i_i, j_i = np.indices((L, ny, nx))
        colour = (l_i + i_i + j_i) % 2 == 0
        masks = (colour, ~colour)
        # The vias couple all the cells of a footprint (a dense block of K that the six-neighbour update does not see), so the cells of every via are
        # solved together: a block SOR. The two colours skip them and, after the colours, each group of blocks that K does not couple takes the exact
        # solution of its block, relaxed by the same omega (research/sor-with-via-couplings, variant c'; convergence for 0 < omega < 2)
        groups = []
        if self.via_blocks:
            idx3 = np.arange(L * ny * nx).reshape(L, ny, nx)
            vblocks = viawell.unknown_blocks(self.via_blocks, idx3, self.n_board)
            biggest = max(len(bk) for bk in vblocks)
            sizes = [len(bk) for bk in vblocks]
            if not memory.sor_block_fits(sizes, memory.limit_bytes() if memory_limit is None else memory_limit):
                # The dense inverses of the blocks (all kept for the iterations) take too much of the memory limit: use the direct solver and say so
                need = sum(memory.sor_block_bytes(k) for k in sizes)
                log.warning("SOR: the via blocks (%d, the largest of %d unknowns; about %.1f GB for their dense inverses) are too large for the block SOR; "
                            "the direct solver is used instead", len(sizes), biggest, need / memory.GB)
                theta, res = self.solve_steady("direct")
                return theta, res, {"iterations": 0, "converged": True, "omega": float(omega), "last_step": 0.0, "fallback": "direct", "block": float(biggest),
                                    "block_bytes": float(need)}
            groups = self._sor_block_groups(vblocks)
            skip = np.zeros(L * ny * nx, bool)
            for bk in vblocks:
                skip[bk] = True
            skip = skip.reshape(L, ny, nx)
            masks = (colour & ~skip, ~colour & ~skip)
        qn = np.linalg.norm(Q)
        theta = np.zeros((L, ny, nx))
        pad = np.zeros((L + 2, ny + 2, nx + 2))
        converged, last_step, it = False, np.inf, 0

        def neighbours(t):
            # Weighted sum of the neighbour temperatures using a zero-padded copy
            pad[1:-1, 1:-1, 1:-1] = t
            return (gl * pad[1:-1, 1:-1, :-2] + gr * pad[1:-1, 1:-1, 2:] + gd * pad[1:-1, :-2, 1:-1] +
                    gu * pad[1:-1, 2:, 1:-1] + ga * pad[:-2, 1:-1, 1:-1] + gb * pad[2:, 1:-1, 1:-1])

        for it in range(1, max_iter + 1):
            step = 0.0
            for m in masks:
                new = (neighbours(theta) + Q) / diag
                delta = np.where(m, new - theta, 0.0)
                theta = theta + omega * delta
                step = max(step, float(np.abs(delta).max()))
            if groups:
                tf = theta.ravel().copy()
                qf = Q.ravel()
                for rows_g, K_g, Binv in groups:
                    dtheta = omega * (Binv @ (qf[rows_g] - K_g @ tf))
                    tf[rows_g] += dtheta
                    step = max(step, float(np.abs(dtheta).max()) / omega)
                theta = tf.reshape(L, ny, nx)
            last_step = step
            if criterion == "step":
                if step < tol:
                    converged = True
                    break
            elif it % 10 == 0 or step < tol:
                if np.linalg.norm(K @ theta.ravel() - Q.ravel()) / max(qn, 1e-300) < tol:
                    converged = True
                    break
        res = float(np.linalg.norm(K @ theta.ravel() - Q.ravel()) / max(qn, 1e-300))
        return theta, res, {"iterations": it, "converged": converged, "omega": float(omega), "last_step": last_step}

    def _sor_columns(self, omega, tol, max_iter, criterion, memory_limit=None):
        """!
        @brief Block SOR for a network with laminate nodes: every plan cell is a block of all its nodes (copper, interior, bottom), the blocks are coloured and each colour is solved exactly.
        @details Why not the point red-black sweep: in a refined cell the two copper nodes are joined by n links and in a single-link cell by one, so the cycle
                 a(i) - b(i) - b(j) - [n links] - a(j) - a(i) has length n + 3, odd for every even n, and no two-colouring of the nodes exists (the default rule gives n = 2 or 4).
                 Every coupling of the network joins two nodes of one plan cell, the same node of two neighbouring cells, or the cells of a via footprint, so the blocks of the plan
                 cells (merged where a via footprint joins them) can be coloured; the blocks of one colour are not coupled to each other and take the exact solution of their
                 block-diagonal part, relaxed by omega (convergence for 0 < omega < 2, as for the via blocks). Nodes no cell uses are left out. A merged block whose dense
                 bound (75 n^2 bytes) is above a quarter of the memory limit is not factored: the board is solved directly (info["fallback"] = "direct"). The
                 bound is conservative here: the blocks of one colour are factored by a sparse LU, which takes far less than a dense inverse.
                 Measured on 30 mm boards at 1 mm: 730 / 5200 / 730 sweeps against 719 / 5221 / 775 for the point SOR of the earlier network (research/laminate-nodes, 3.11).
        @param omega Relaxation factor.
        @param tol Stopping tolerance.
        @param max_iter Sweep limit.
        @param criterion "residual" or "step" (see solve_sor).
        @param memory_limit Memory limit in bytes (None: memory.limit_bytes()).
        @return Tuple (theta, residual, info) as solve_sor.
        """
        L, ny, nx = self.nl, self.ny, self.nx
        cells = ny * nx
        K = self.K.tocsr()
        q = self.Q.ravel()
        # Blocks: the plan cells, merged where a via footprint joins them (the via couples all the cells of its footprint)
        links = []
        for ci, cj, _w, _G in self.via_blocks:
            c = (ci * nx + cj).astype(int)
            links.append(np.stack([c[:-1], c[1:]], axis=1))
        pairs = np.concatenate(links) if links else np.zeros((0, 2), dtype=int)
        graph = sp.coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(cells, cells))
        _, comp = csgraph.connected_components(graph, directed=False)
        used = ~self.drop.ravel() if self.drop is not None else np.ones(L * cells, bool)
        node_cell = np.tile(np.arange(cells), L)
        node_block = comp[node_cell]
        sizes = np.bincount(node_block[used], minlength=comp.max() + 1)
        if not memory.sor_block_fits(int(sizes.max()), memory.limit_bytes() if memory_limit is None else memory_limit):
            log.warning("SOR: a block of %d unknowns (a via footprint with its laminate nodes; about %.1f GB) is too large for the block SOR; the direct solver is used instead",
                        int(sizes.max()), memory.sor_block_bytes(int(sizes.max())) / memory.GB)
            theta, res = self.solve_steady("direct")
            return theta, res, {"iterations": 0, "converged": True, "omega": float(omega), "last_step": 0.0, "fallback": "direct", "block": float(sizes.max())}
        # Colour the blocks greedily so that coupled blocks differ (blocks in raster order on a grid give the usual two colours)
        coo = K.tocoo()
        br, bc = node_block[coo.row], node_block[coo.col]
        off = (br != bc) & used[coo.row] & used[coo.col]
        nb_blocks = comp.max() + 1
        neigh = [set() for _ in range(nb_blocks)]
        for a, c in zip(br[off].tolist(), bc[off].tolist()):
            neigh[a].add(c)
        colour = np.zeros(nb_blocks, dtype=int)
        for k in range(nb_blocks):
            taken = {int(colour[o]) for o in neigh[k] if o < k}
            colour[k] = min(c for c in range(len(taken) + 1) if c not in taken)
        node_colour = colour[node_block]
        groups = []
        for c in range(int(colour.max()) + 1):
            idx = np.flatnonzero(used & (node_colour == c))
            if idx.size:
                groups.append((idx, K[idx], spla.splu(K[idx][:, idx].tocsc())))
        qn = np.linalg.norm(q)
        x = np.zeros(L * cells)
        converged, last_step, it = False, np.inf, 0
        for it in range(1, max_iter + 1):
            step = 0.0
            for idx, rows, lu in groups:
                d = omega * lu.solve(q[idx] - rows @ x)
                x[idx] += d
                step = max(step, float(np.abs(d).max()) / omega)
            last_step = step
            if criterion == "step":
                if step < tol:
                    converged = True
                    break
            elif it % 10 == 0 or step < tol:
                if np.linalg.norm(K @ x - q) / max(qn, 1e-300) < tol:
                    converged = True
                    break
        res = float(np.linalg.norm(K @ x - q) / max(qn, 1e-300))
        return x.reshape(L, ny, nx), res, {"iterations": it, "converged": converged, "omega": float(omega), "last_step": last_step}

    def _sor_block_groups(self, vblocks):
        """!
        @brief Colour the via blocks and invert them, for the block step of the SOR.
        @details Two blocks are neighbours when K couples a cell of one to a cell of the other (touching footprints); the blocks are coloured greedily so
                 that the blocks of one colour are mutually uncoupled and can be updated at once (moving neighbours at once with over-relaxation diverges).
        @param vblocks List of integer arrays of flat unknowns (disjoint).
        @return List of (rows, K[rows, :], block-diagonal inverse of K[rows, rows]) per colour.
        """
        K = self.K.tocsr()
        owner = np.full(K.shape[0], -1)
        for k, bk in enumerate(vblocks):
            owner[bk] = k
        colour = [0] * len(vblocks)
        for k, bk in enumerate(vblocks):
            near = {int(o) for o in owner[K[bk].indices] if 0 <= o < k}
            used = {colour[o] for o in near}
            colour[k] = min(c for c in range(len(vblocks) + 1) if c not in used)
        groups = []
        for c in sorted(set(colour)):
            members = [bk for bk, ck in zip(vblocks, colour) if ck == c]
            rows = np.concatenate(members)
            inv = [np.linalg.inv(K[bk][:, bk].toarray()) for bk in members]
            groups.append((rows, K[rows, :], sp.block_diag([sp.csr_matrix(m) for m in inv], format="csr")))
        return groups

    def power_out(self, theta):
        """!
        @brief Heat leaving the board through every path for a given temperature rise.
        @param theta Rise array of shape (layers, ny, nx).
        @return Dict with keys top, bottom, heatsinks, sides in watts.
        """
        out = {
            "top": float((self.g_top * theta).sum()),
            "bottom": float((self.g_bottom * theta).sum()),
            "heatsinks": float((self.g_heatsink * theta).sum()),
            "sides": float((self.g_side * theta).sum()),
        }
        if self.extra_links:
            out["blocks"] = float((self.g_block * theta).sum())           # Heat leaving through the exposed surface of the blocks
        return out


def _result_from_theta(net, theta, residual, model="fvm"):
    """!
    @brief Package a temperature-rise field as a SteadyResult.
    @param net The Network that produced it.
    @param theta Rise array (layers, ny, nx) in kelvin.
    @param residual Relative residual of the linear solve.
    @param model Model name to store.
    @return SteadyResult with absolute temperatures.
    """
    amb = net.problem.board.ambient
    nb = net.n_board
    T_all = theta + amb
    T = T_all[:nb]                                     # The board; the block layers are kept apart
    inside = net.active                                # Cells that are board (all of them for a rectangle)
    cover = net.cover
    k = int(np.argmax(np.where(inside[None], T, -np.inf)))
    l, i, j = np.unravel_index(k, T.shape)
    res = SteadyResult(
        model=model, ambient=amb, power_in=float(net.Q.sum()),
        t_max=float(T[:, inside].max()), t_min=float(T[:, inside].min()),
        t_mean=float((T * cover[None]).sum() / (nb * cover.sum())),
        layer_mean=[float((T[n] * cover).sum() / cover.sum()) for n in range(nb)],
        t_max_location=(int(l), (j + 0.5) * net.dx, (i + 0.5) * net.dy),
        T=T, dx=net.dx, dy=net.dy, power_out=net.power_out(theta), residual=residual,
        extras={"cells": float(inside.sum() * nb)},
    )
    if not inside.all():
        res.arrays["board_mask"] = inside              # The plots leave the cells off the board blank
    attach_laminate_results(res, net, T_all, cover)
    attach_block_results(res, net, T_all, theta)
    attach_face_terms(res, net, net.dx * net.dy * net.cover, net.dx)
    return res


def attach_face_terms(res, net, cell, dx):
    """!
    @brief Put the rise between the node and the face of a part over absent copper in a result (laminate.face_terms), for the peak and mean read under the part.
    @param res SteadyResult of the board.
    @param net Network built with the laminate rule (nothing is done otherwise).
    @param cell Board area of every cell or control volume in m2, shape (ny, nx).
    @param dx Cell size or node spacing in m.
    """
    if getattr(net, "ladder", None) is None:
        return
    terms = laminate.face_terms(net.problem.board, net.fill, net.Q, cell, dx)
    if terms is not None:
        res.arrays["face_peak"], res.arrays["face_mean"] = terms


def attach_laminate_results(res, net, T_all, weights):
    """!
    @brief Put the mean temperature of the bottom face of a one-layer board (its last laminate node) in a result, for the computed heat transfer coefficients.
    @param res SteadyResult of the board.
    @param net Network with laminate nodes (nothing is done without them).
    @param T_all Temperatures of all node layers in degC.
    @param weights Board area or cover of every cell or node, shape (ny, nx).
    """
    layers = getattr(net, "laminate_layers", None)
    if not layers:
        return
    res.extras["bottom_face_mean"] = float((T_all[layers[-1]] * weights).sum() / weights.sum())


def attach_block_results(res, net, T_all, theta):
    """!
    @brief Put the temperature of the metal blocks, the heat they take and the heat flux entering them in a result.
    @details arrays["block_flux"] is the heat flux through the interface into every block cell or node, in W/m2 of block area (zero off the blocks),
             and arrays["block_face"] the face (0 top, 1 bottom) of every block layer; checks.check_thick_plates reads them.
    @param res SteadyResult of the board.
    @param net Network with block layers (nothing is done without them).
    @param T_all Temperatures of all layers, board first, in degC.
    @param theta Rise of all layers in kelvin.
    """
    if not net.block_info:
        return
    # Only the block layers: on a one-layer board the laminate nodes sit between the board layer and the blocks
    ids = [bi["layer"] for bi in net.block_info]
    res.arrays["block_T"] = T_all[ids]                 # (blocks layers, ny, nx), ambient where there is no block
    res.arrays["block_cov"] = np.stack([bi["cov"] for bi in net.block_info])
    res.arrays["block_face"] = np.array([bi["face"] for bi in net.block_info])
    # Plan area of every cell (FVM) or node (FDM) on the board, in m2: the flux is the heat into the block over the block's share of it
    area = net.area if hasattr(net, "area") else net.dx * net.dy * net.cover
    flux = []
    for bi in net.block_info:
        heat = bi["g_link"] * (theta[bi["board_layer"]] - theta[bi["layer"]])
        share = bi["cov"] * area
        flux.append(np.where(share > 0, heat / np.where(share > 0, share, 1.0), 0.0))
    res.arrays["block_flux"] = np.stack(flux)
    for k, bi in enumerate(net.block_info):
        sel = bi["cov"] > 0
        tag = "top" if bi["face"] == 0 else "bottom"
        layer_theta = theta[bi["layer"]]
        res.extras[f"block_{tag}_max"] = float(T_all[bi["layer"]][sel].max())
        res.extras[f"block_{tag}_mean"] = float((T_all[bi["layer"]][sel] * bi["cov"][sel]).sum() / bi["cov"][sel].sum())
        res.extras[f"block_{tag}_w_to_block"] = float((bi["g_link"] * (theta[bi["board_layer"]] - layer_theta)).sum())
        res.extras[f"block_{tag}_w_to_air"] = float((net.g_block[bi["layer"]] * layer_theta).sum())


def unknowns(problem, cell_mm=2.0):
    """!
    @brief Number of unknowns of the layered finite-volume model of a problem, counted without building it (the same nodes as Network, ragged).
    @details The model has one node per copper layer of nx x ny cells, the bottom node of a one-layer board, the laminate nodes of the rule (laminate.py) **only in the cells that
             carry them** (the cells with absent copper next to a gap plus a margin: up to 2.5 times the unknowns of a thick two-layer board with a bare bottom, 1.0 times on boards
             with copper everywhere), and, for a board with a metal block (blocks.py, which keeps the earlier treatment), one layer per face of blocks and the two laminate nodes
             of a one-layer board. The application shows this number next to the cell size.
    @param problem A Problem.
    @param cell_mm Target size of the cells in millimetres (the grid is round(width / cell) by round(height / cell), at least 2 each).
    @return Tuple (unknowns, layers, nx, ny) with layers the number of node layers of the arrays (dense) and unknowns the nodes that are solved (ragged).
    """
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    if laminate.uses_rule(problem):
        # The laminate nodes of the rule exist only in the flagged cells: count them as the network will (the same fill, cover and plan)
        dx, dy = b.width / nx, b.height / ny
        active = b.cover(nx, ny, dx, dy) > 0
        fill = zone_fill(problem.zones, b.layers, nx, ny, dx, dy, samples=4)
        copper.override_fill(fill, copper.resolve(None, problem), ny, nx, b.width, b.height)
        # The band along the edge is counted too (it exists only with an edge coefficient)
        edge = laminate.edge_lengths(b, nx, ny, dx, dy, active) if b.h_side else None
        return (*laminate.count_unknowns(b, laminate.plan_gaps(b, fill, dx, active, edge=edge), nx * ny), nx, ny)
    lam = laminate.nodes(b)
    layers = b.layers + (lam.count if lam is not None else 0) + len(blocks.block_faces(problem))
    return layers * nx * ny, layers, nx, ny


def solve_steady(problem, cell_mm=2.0, method="direct", sor_omega=None, sor_tol=1e-9, sor_criterion="residual", memory_limit=None):
    """!
    @brief Steady-state FVM solution of a problem.
    @param problem A Problem.
    @param cell_mm Target cell size in millimetres (the grid is nx = round(width / cell)).
    @param method "direct" (sparse LU), "cg" (conjugate gradients) or "sor" (red-black SOR, for comparison).
    @param sor_omega Relaxation factor for "sor" (None = automatic).
    @param sor_tol Tolerance for "sor".
    @param sor_criterion "residual" or "step" (see Network.solve_sor).
    @param memory_limit Memory limit in bytes for the SOR block guard (None: memory.limit_bytes()).
    @return SteadyResult (for "sor" the extras hold iterations, omega and converged).
    """
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    net = Network(problem, nx, ny)
    if method == "sor":
        theta, res, info = net.solve_sor(omega=sor_omega, tol=sor_tol, criterion=sor_criterion, memory_limit=memory_limit)
        r = _result_from_theta(net, theta, res)
        r.extras.update({"iterations": float(info["iterations"]), "omega": info["omega"],
                         "converged": float(info["converged"])})
        if not info["converged"]:
            r.warnings.append(f"SOR did not converge in {info['iterations']} sweeps (residual {num(res)})")
        if info.get("fallback") == "direct":
            # The user chose SOR: say in the result (not only in the log) that another solver produced it
            r.extras["fallback_direct"] = 1.0
            n_blk = int(info.get("block", 0))
            need = info.get("block_bytes", memory.sor_block_bytes(n_blk))
            r.warnings.append(f"SOR not used: the cells of the vias form blocks (the largest of {n_blk} unknowns) whose dense inverses need about {need / memory.GB:.1f} GB, "
                              "too much for the block SOR within the memory limit; the board was solved with the direct solver instead")
        return r
    theta, res = net.solve_steady(method=method)
    return _result_from_theta(net, theta, res)


def solve_transient(problem, t_end, n_out=40, cell_mm=2.0, substeps=4, theta_scheme=1.0,
                    log_times=True):
    """!
    @brief Transient response to a power step starting from a board at ambient temperature.
    @details Uses the theta-method: (C/dt + theta*K) x1 = (C/dt - (1-theta)*K) x0 + Q.
             theta = 1 is implicit Euler (robust), theta = 0.5 is Crank-Nicolson (more accurate).
             Both are unconditionally stable for the diffusion equation.
    @param problem A Problem.
    @param t_end Final time in seconds.
    @param n_out Number of output frames (excluding t = 0); in logarithmic mode it is rounded up to a multiple of 10.
    @param cell_mm Target cell size in millimetres.
    @param substeps Implicit steps between two output frames (linear mode only; logarithmic mode uses one step per frame).
    @param theta_scheme 1.0 for implicit Euler, 0.5 for Crank-Nicolson.
    @param log_times If True the time step doubles in ten stages (resolves fast and slow parts with few factorisations).
    @return TransientResult.
    """
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    return transient_from_network(Network(problem, nx, ny), b.ambient, t_end, n_out, substeps, theta_scheme, log_times)


def transient_from_network(net, ambient, t_end, n_out=40, substeps=4, theta_scheme=1.0, log_times=True, grid="cells"):
    """!
    @brief Power-step transient of any thermal network with the attributes of Network (also the finite-difference one).
    @details The network provides K (sparse conductances), C (heat capacity per unknown), Q (source), nl, ny, nx and solve_steady().
    @param net The network.
    @param ambient Ambient temperature in degC.
    @param t_end Final time in seconds.
    @param n_out Number of output frames (excluding t = 0).
    @param substeps Implicit steps between two frames (linear mode only).
    @param theta_scheme 1.0 for implicit Euler, 0.5 for Crank-Nicolson.
    @param log_times True for the doubling time step.
    @param grid "cells" or "nodes": what the frames hold.
    @return TransientResult.
    """
    ny, nx = net.ny, net.nx
    nb = getattr(net, "n_board", net.nl)
    steady_theta, _ = net.solve_steady()
    weights = mean_weights(net)                             # Board area of every cell or node: the mean leaves out what is off the board

    # --- Time grid: every frame is one time step, and the steps are built so that few distinct dt occur
    # (one LU factorisation per distinct dt). Linear: one dt. Logarithmic: dt doubles stage after stage.
    if log_times:
        stages = 10
        per_stage = max(int(np.ceil(n_out / stages)), 1)
        dt0 = t_end / (per_stage * (2 ** stages - 1))
        dts = np.concatenate([np.full(per_stage, dt0 * 2.0 ** j) for j in range(stages)])
    else:
        dts = np.full(max(n_out, 1) * max(substeps, 1), t_end / (max(n_out, 1) * max(substeps, 1)))
    step_times = np.concatenate([[0.0], np.cumsum(dts)])
    step_times[-1] = t_end                                  # Remove round-off at the end
    keep = np.arange(len(step_times)) if log_times else np.arange(0, len(step_times), max(substeps, 1))
    times = step_times[keep]

    N = net.nl * ny * nx
    Cd = net.C.ravel()
    q = net.Q.ravel()
    x = np.zeros(N)                                         # Rise above ambient, starts at zero
    frames = {0: x.reshape(net.nl, ny, nx)[:nb] + ambient}
    # Only the factor of the current step size is kept: the steps of a stage are equal and a stage never comes back, so an old factor is dead
    # weight (ten factors were held before; the peak memory of an animation fell from about 3.5 to 1.9 times a steady solve).
    current_key, lu, B = None, None, None
    kept = set(keep.tolist())
    for k, dt in enumerate(dts, start=1):
        key = round(float(dt), 12)
        if key != current_key:
            lu = B = None                                   # Free the old factor before the new one is built
            A = (sp.diags(Cd / dt) + theta_scheme * net.K).tocsc()
            B = (sp.diags(Cd / dt) - (1.0 - theta_scheme) * net.K).tocsr()
            lu, current_key = lu_factor(A), key
        x = lu.solve(B @ x + q)
        if k in kept:
            frames[k] = x.reshape(net.nl, ny, nx)[:nb] + ambient
    frames = np.asarray([frames[k] for k in keep])
    inside = weights > 0
    return TransientResult(
        times=times, t_max=frames[:, :, inside].reshape(len(times), -1).max(axis=1),
        t_mean=(frames * weights).sum(axis=(1, 2, 3)) / (nb * weights.sum()), frames=frames,
        steady_t_max=float(steady_theta[:nb].max() + ambient), ambient=ambient, grid=grid,
    )


def step_responses(problem, cell_mm=2.0, t_end=None, ratio=3.0, per_stage=4, stages=18, theta_scheme=0.5):
    """!
    @brief Response of every heater's hottest point to a unit power step of that heater, all heaters at once.
    @details The heaters are solved as several right-hand sides of the same matrices. The time step grows by
             the factor `ratio` after every `per_stage` steps (one matrix factorisation per stage), which covers
             about nine decades of time with a few dozen steps. The result Z_i(t) is in degC per W and is what the
             power-profile analysis uses to estimate oscillations and periodic peaks.
    @param problem A Problem with at least one heater.
    @param cell_mm Target cell size in millimetres.
    @param t_end Last time in seconds (default: ten board time constants).
    @param ratio Growth factor of the time step between stages.
    @param per_stage Steps per stage.
    @param stages Number of stages.
    @param theta_scheme 0.5 (Crank-Nicolson) or 1.0 (implicit Euler).
    @return Tuple (times, z, rth): times (nt,) in s without t = 0, z (n_heaters, nt) in degC/W and rth (n_heaters,)
            in degC/W (steady state).
    @throws ValueError If the problem has no heater.
    """
    if not problem.heaters:
        raise ValueError("the problem has no heater")
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    return step_responses_from_network(Network(problem, nx, ny), t_end, ratio, per_stage, stages, theta_scheme)


def step_responses_from_network(net, t_end=None, ratio=3.0, per_stage=4, stages=18, theta_scheme=0.5):
    """!
    @brief Step responses of the heaters of any network with the attributes of Network (see step_responses).
    @param net The network (K, C, g_amb, Qw_matrix).
    @param t_end Last time in seconds (default: ten board time constants).
    @param ratio Growth factor of the time step between stages.
    @param per_stage Steps per stage.
    @param stages Number of stages.
    @param theta_scheme 0.5 (Crank-Nicolson) or 1.0 (implicit Euler).
    @return Tuple (times, z, rth).
    """
    if t_end is None:
        t_end = 10.0 * board_time_constant(net)
    Q = net.Qw_matrix.toarray()                                   # (cells, heaters), unit power each
    rth = (lu_factor(net.K).solve(Q)).max(axis=0)
    # Step sizes: per_stage steps of dt0 * ratio^j for j = 0..stages-1, scaled so that they sum to t_end
    geometric = per_stage * (ratio ** stages - 1.0) / (ratio - 1.0)
    dt0 = t_end / geometric
    Cd = net.C.ravel()
    x = np.zeros_like(Q)
    times, z, t = [], [], 0.0
    for j in range(stages):
        dt = dt0 * ratio ** j
        A = (sp.diags(Cd / dt) + theta_scheme * net.K).tocsc()
        B = (sp.diags(Cd / dt) - (1.0 - theta_scheme) * net.K).tocsr()
        lu = lu_factor(A)
        for _ in range(per_stage):
            x = lu.solve((B @ x) + Q)
            t += dt
            times.append(t)
            z.append(x.max(axis=0))
    return np.asarray(times), np.asarray(z).T, rth


def estimate_time_constant(problem, cell_mm=5.0):
    """!
    @brief Slowest-scale thermal time constant of the whole board, C_total / G_total.
    @details Uniform-board estimate: the total heat capacity divided by the total conductance to ambient.
             The hottest point reaches 63 % much sooner; the board mean needs a few of these constants.
    @param problem A Problem.
    @param cell_mm Cell size used to aggregate the properties (the result hardly depends on it).
    @return Time constant in seconds.
    """
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    net = Network(problem, nx, ny, assemble=False, with_blocks=False, ladder=False)       # (the laminate nodes change neither the total capacity nor the total conductance)
    return board_time_constant(net)


def board_time_constant(net):
    """!
    @brief Total heat capacity over the total conductance to the ambient of a network, C_total / G_total.
    @details The conductance that pins the cells or nodes off a board with an outline (g_pin, 1 W/K each) keeps the matrix regular but is not a
             path to the air; it is left out (counting it gave 0.2 s instead of about 100 s on a round board of 100 mm).
    @param net A network with C, g_amb and optionally g_pin (fvm.Network, fdm.Network).
    @return Time constant in seconds.
    """
    g = net.g_amb.sum() - (net.g_pin.sum() if getattr(net, "g_pin", None) is not None else 0.0)
    return float(net.C.sum() / g)


def mean_weights(net):
    """!
    @brief Weights of the board mean over the grid of a network: the board area of every cell (FVM) or node (FDM).
    @param net A network (fvm.Network has cover and dx, dy; fdm.Network has area).
    @return Array (ny, nx) in m2, zero off the board.
    """
    if getattr(net, "area", None) is not None:
        return np.asarray(net.area, dtype=float)
    return np.asarray(net.cover, dtype=float) * net.dx * net.dy
