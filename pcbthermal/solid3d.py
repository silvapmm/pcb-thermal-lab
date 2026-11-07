#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file solid3d.py
@brief Three-dimensional finite-volume model of the board as a solid: the comparison that does not use the "one node per copper layer" idea.

@details The board is cut into the cells of the plan grid (same nx by ny as the FVM) and, across its thickness, into **real slabs**: every copper
         layer is a slab of its own thickness, every dielectric gap is cut into `n_diel` slabs, and a metal block is a pad slab (the interface, of
         thickness R'' times 1 W/mK) plus `n` slabs of metal. The unknown is the temperature of every cell of every slab, so the heat spreads in
         the gaps and inside the blocks and a heater feels the real vertical path.

         Material of a cell (volume-averaged on the structured grid, as in the tiled conductivity maps used for PCB models [Electronics Cooling 2010]):
         * copper slab with copper fill f: in-plane k = f k_Cu + (1 - f) k_FR4,ip (arithmetic, copper and laminate side by side), through k = the same
           parallel mix with k_FR4,th (they are side by side in plan, so the vertical heat takes both in parallel);
         * a via is copper: in every slab of its cell the through conductivity gets the copper area of the plated barrel (so the cell holds the real
           barrel area, not a square rod) in parallel with the rest;
         * the faces between two cells use the harmonic mean of the half-cell resistances (exact for a conservative scheme with a jump in k).
         Boundary: convection on the outer faces and edges as in the other models (series with the half cell), the extra coefficient of a heatsink
         inside its polygon, a block hiding the board face under it and losing heat on its exposed face and its sides, the heater power distributed
         exactly over its footprint on the copper slab of its layer.

         The result has the same layout as the FVM (one temperature per copper layer: the temperature of its slab), so the plots and tables work.
         Only the steady state is implemented. The model needs no other package than SciPy; the offline FEM script (research/solid3d-verification/scripts/fem3d_validation.py,
         scikit-fem) checks this model in turn.
"""

import contextlib
import logging
import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from . import copper, laminate, memory, viawell
from .fvm import ORDERING
from .geometry import (part_weights, coverage_fraction, edge_length_on_board, face_apertures, nearest_active_cell, polygon_centroid,
                       signed_distance_to_outline)
from .results import SteadyResult

log = logging.getLogger(__name__)

ISOLATED = 1.0e-9            # W/K to the ambient of a cell with no block: keeps the matrix regular, changes nothing
EDGE_FILM_FLOOR = 0.25       # Smallest value of 1 + h d / k of the edge film on a cut cell: the film is at most four times stiffer than the plain film
K_FLOOR = 1.0e-9             # W/mK of a cell that holds no material (outside a block)
# The size of a 3D model is no longer a fixed number: pcbthermal/memory.py estimates the peak memory from the unknowns and refuses a run above a share of the
# installed memory (api.simulate, jobs.py and the constructor of Solid call it before anything is built). Measured on a quiet 16 GB machine (research/memory-guard): the example board
# (16 slabs) takes 3.5 GB at 247 000 unknowns and 9.9 GB at 512 000; a plain two-layer board (6 slabs) 3.3 GB at 500 000.
K_PAD = 1.0                  # W/mK of the interface pad slab (its thickness is R'' times this)
# Slabs across a dielectric gap (research/laminate-2-6 5): a slab of at most 0.2 mm, at least 4 and at most 16 per gap. A fixed 4 slabs left the heat of a small part
# (2 mm) too concentrated over a thick laminate (+23 % bare, +27 % pad at 3.2 mm); 8 slabs of the 1.53 mm core of a two-layer board and 6 of the 1.065 mm core of a four-layer one
SLAB_MM = 0.2
SLABS_MIN = 4
SLABS_MAX = 16


@contextlib.contextmanager
def size_limit(max_cells):
    """!
    @brief Accept 3D models up to a number of unknowns inside a with block whatever the memory estimate, and refuse them above it (the offline studies).
    @details The memory guard (`memory.check`) would refuse such a model on a small machine; inside the block it does not, up to `max_cells`, and the ceiling of the 3D
             solid is lifted to it. A study that needs a finer 3D grid (the 0.5 mm columns of validation_study.py, the 6-layer board of study_complex_boards.py) runs inside
             `with solid3d.size_limit(2_000_000):`; a study that must stay small (`size_limit(250_000)`) gets a refusal above the number, as before the guard.
             The guard acts in `api.simulate`, `jobs.py` and the constructor of `Solid`, so a study that builds the 3D solid directly is checked too.
    @param max_cells Largest number of unknowns accepted inside the block (and refused above it), count.
    @return Context manager (yields nothing).
    """
    with memory.accept_unknowns("solid3d", int(max_cells)):
        yield


def slab_rule(d):
    """!
    @brief Number of slabs of one dielectric gap by its thickness: ceil(d / 0.2 mm), at least 4 and at most 16.
    @param d Gap thickness in m.
    @return int.
    """
    return int(min(SLABS_MAX, max(SLABS_MIN, math.ceil(d * 1e3 / SLAB_MM - 1e-9))))


def slabs_per_gap(problem, n_diel=None):
    """!
    @brief Slabs across every dielectric gap of a board (the laminate under the copper for a one-layer board, which has no gap).
    @details None gives the rule of `slab_rule` per gap (the 1.53 mm gap of a two-layer board: 8 slabs; the 1.065 mm core of a four-layer template: 6; the thin prepreg: 4);
             an int gives the same count to every gap (the studies that ask for the old fixed 4, or a convergence sweep); a sequence gives one count per gap.
    @param problem A Problem.
    @param n_diel None for the rule, an int for every gap, or a sequence with one count per gap (one element for a one-layer board), count.
    @return List of int with L - 1 elements (one element, or none when the laminate has no thickness, for a one-layer board).
    @throws ValueError If a sequence has the wrong length or a count below 1.
    """
    b = problem.board
    if b.layers == 1:
        t_lam = float(b.slab_thicknesses()[0] - np.asarray(b.copper_thickness)[0])
        ds = [t_lam] if t_lam > 0 else []
    else:
        ds = [float(d) for d in b.gap_thicknesses()]
    if n_diel is None:
        return [slab_rule(d) for d in ds]
    if np.ndim(n_diel) == 0:
        out = [int(n_diel)] * len(ds)
    else:
        out = [int(n) for n in n_diel]
        if len(out) != len(ds):
            raise ValueError(f"n_diel has {len(out)} counts for {len(ds)} dielectric gaps")
    if any(n < 1 for n in out):
        raise ValueError("every dielectric gap needs at least one slab")
    return out


def unknowns(problem, cell_mm=2.0, n_diel=None):
    """!
    @brief Number of unknowns of the 3D model of a problem, counted without building it (same slabs as Solid).
    @details Used by the memory guard to refuse a model that is too large before anything is assembled, and by the application to show the size next to the cell.
    @param problem A Problem.
    @param cell_mm Target size of the cells in the plan in millimetres.
    @param n_diel Slabs across the dielectric gaps: None for the rule by thickness (slabs_per_gap), an int for every gap or a sequence per gap, count.
    @return Tuple (unknowns, slabs, nx, ny).
    """
    b = problem.board
    L = b.layers
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    ns = L + sum(slabs_per_gap(problem, n_diel))                 # A copper slab per layer and the slabs of every gap (the laminate under a one-layer board's copper)
    thick = {}
    for s in problem.heatsinks:
        if s.is_block():
            face = 0 if (s.layer == 0 or L == 1) else 1
            thick[face] = max(thick.get(face, 0.0), s.thickness)
    # Every face with a block gets a pad slab and 1 to 6 metal slabs (one per millimetre of the thickest block), as in Solid
    ns += sum(1 + int(np.clip(round(t * 1000.0), 1, 6)) for t in thick.values())
    return ns * nx * ny, ns, nx, ny


def _edge_length(cov, dx, dy):
    """!
    @brief Length of the outline of a covered region inside every cell.
    @param cov Covered fraction of every cell, shape (ny, nx).
    @param dx Cell size along x in m.
    @param dy Cell size along y in m.
    @return Array (ny, nx) of lengths in metres (a rectangular block on the grid gets the full length of its outline).
    """
    pad = np.pad(cov, 1)
    out = np.zeros_like(cov)
    for axis, length in ((1, dy), (0, dx)):
        for sgn in (-1, 1):
            out += length * np.maximum(cov - np.roll(pad, sgn, axis=axis)[1:-1, 1:-1], 0.0)
    return out


class Solid:
    """!
    @brief The slabs, conductances and sources of the 3D model.
    """

    def __init__(self, problem, cell_mm=2.0, n_diel=None, memory_fraction=None):
        """!
        @param problem A Problem.
        @param cell_mm Target size of the cells in the plan in millimetres (same rule as the FVM).
        @param n_diel Slabs across the dielectric gaps: None for the rule by thickness (slabs_per_gap), an int for every gap or a sequence per gap, count.
        @param memory_fraction Share of the physical memory the solve may use (None: memory.default_fraction()); api.simulate passes the option of the run.
        @throws memory.MemoryGuardError (a ValueError) If the estimated memory is above the limit, the model is above the 3D ceiling, or it is outside the
                window of a size_limit block; checked before any array of the size of the model is made.
        """
        problem.validate()
        # The memory guard here too, not only in api.simulate: the studies and the tests build the 3D solid directly, and before the guard this constructor
        # refused a model above MAX_CELLS; a study that catches ValueError to print "-" for a model too large keeps working
        memory.check(problem, ("solid3d",), cell_mm, fraction=memory_fraction, n_diel=n_diel)
        self.problem = problem
        self.n_gap = slabs_per_gap(problem, n_diel)                  # Slabs of every gap (the laminate of a one-layer board is one element)
        b, m = problem.board, problem.board.materials
        L, W, H = b.layers, b.width, b.height
        nx = max(int(round(W * 1000.0 / cell_mm)), 2)
        ny = max(int(round(H * 1000.0 / cell_mm)), 2)
        dx, dy = W / nx, H / ny
        A = dx * dy
        self.nx, self.ny, self.dx, self.dy, self.area = nx, ny, dx, dy, A
        Ab = A                                                       # Board area of every cell (set below once the cover is known)
        ones = np.ones((ny, nx))

        def cover(poly, samples):
            return coverage_fraction(poly, nx, ny, dx, dy, samples)

        # Share of every plan cell that is board (ones for a rectangle); cells off the board carry nothing
        bcov = b.cover(nx, ny, dx, dy)
        self.cover, self.active = bcov, bcov > 0
        Ab = A * bcov
        self.area_b = Ab

        # --- Copper fill of every layer and the plated area of the vias in every cell
        fill = copper.problem_fill(problem, nx, ny, dx, dy, 4)           # Union per sample point, not per cell
        via_frac = np.zeros((ny, nx))
        for v, share in zip(problem.vias, problem.via_board_shares()):
            if share > 0.0:                    # The geometric test of the warning and of every model: a via with no board under its drill adds nothing
                a_via = v.thermal_area(b.via_plating, b.materials.k_copper)
                # One footprint rule for every via (an open and a filled via are the same model): the weights whose lattice effective radius is 0.78 r_via,
                # the radius of the uniform sink density of the layered models, centred on the via and on the cells of the board; the cell of the centre
                # alone when that radius is below the one of a point sink on this grid (a cell coarser than the via). See viawell.tuned_footprint
                w = viawell.tuned_footprint(v.x, v.y, 0.5 * v.diameter, dx, 0.0, bcov, dy)
                for (i, j), wk in w.items():
                    via_frac[i, j] += a_via * wk / A             # The copper area of the barrel is conserved
        if float(via_frac.max(initial=0.0)) > 1.0:
            log.warning("the copper of the vias in one cell is larger than the cell: the excess is clipped; use a finer cell for this model")
        via_frac = np.minimum(via_frac, 1.0)
        self.via_frac = via_frac                                   # Copper area of the vias as a fraction of every cell (the area of the barrels is conserved)

        tc = np.asarray(b.copper_thickness)
        gaps = b.gap_thicknesses()                                  # (L-1,) thickness of every gap
        g_kz, g_kip, _ = b.gap_properties()
        k_lam = b.layer_laminate()[0]                               # In-plane conductivity of the dielectric around each copper layer
        kz_lam = np.array([float(np.dot([gaps[g] for g in a], [g_kz[g] for g in a]) / sum(gaps[g] for g in a))
                           if (a := [g for g in (l - 1, l) if 0 <= g < L - 1]) else m.k_fr4_through for l in range(L)])

        # --- Slabs from the top face down: each is (kind, layer, dz, kx, kz); dz, kx, kz are arrays (ny, nx)
        slabs = []

        def add(kind, layer, dz, kx, kz):
            slabs.append({"kind": kind, "layer": layer, "dz": np.broadcast_to(dz, (ny, nx)).astype(float),
                          "kx": np.maximum(np.broadcast_to(kx, (ny, nx)).astype(float), K_FLOOR),
                          "kz": np.maximum(np.broadcast_to(kz, (ny, nx)).astype(float), K_FLOOR)})
            if kind in ("cu", "fr4"):                    # Board slabs: the conducting cross-section is the share of the cell on the board
                slabs[-1]["kphys"] = slabs[-1]["kx"].copy()          # The conductivity of the material itself (no cover factor), for the cut-cell links and film
                slabs[-1]["kx"] = np.maximum(slabs[-1]["kx"] * bcov, K_FLOOR * 1e-3)
                slabs[-1]["bcov"] = bcov

        # Metal blocks: one stack per face, parameters per cell (a later block wins where blocks overlap)
        faces = {}
        for s in problem.heatsinks:
            if not s.is_block():
                continue
            face = 0 if (s.layer == 0 or L == 1) else 1
            c = cover(s.polygon, 4) * bcov                     # The block is cut at the board outline (cells off the board are pinned to the ambient)
            f = faces.setdefault(face, {"cov": np.zeros((ny, nx)), "t": np.zeros((ny, nx)), "k": np.ones((ny, nx)),
                                        "r": np.zeros((ny, nx)), "he": np.zeros((ny, nx)), "names": [], "fins": {}})
            take = c > 0
            f["cov"] = np.where(take, c, f["cov"])
            f["t"] = np.where(take, s.thickness, f["t"])
            f["k"] = np.where(take, s.k, f["k"])
            f["r"] = np.where(take, max(s.interface_resistance(), 1e-7), f["r"])
            f["he"] = np.where(take, s.h_extra, f["he"])
            f["fins"] = {k: np.where(take, v, f["fins"].get(k, 0.0)) for k, v in
                         (("h", s.fin_height if s.has_fins() else 0.0), ("t", s.fin_thickness if s.has_fins() else 0.0),
                          ("p", s.fin_pitch if s.has_fins() else 0.0), ("k", s.k))}
            f["names"].append(s.name or "block")
        self.faces = faces
        n_blk = {face: int(np.clip(round(float(f["t"].max()) * 1000.0), 1, 6)) for face, f in faces.items()}
        self.n_blk = n_blk

        def block_slabs(face):
            f = faces[face]
            cov = f["cov"]
            out = [("pad", f["r"] * K_PAD, np.maximum(cov, 0.0) * K_PAD, np.maximum(cov, 0.0) * K_PAD)]
            out += [("blk", f["t"] / n_blk[face], cov * f["k"], cov * f["k"])] * n_blk[face]
            return out                                          # Ordered from the board outwards

        if 0 in faces:
            for kind, dz, kx, kz in reversed(block_slabs(0)):
                add(kind, 0, np.maximum(dz, 1e-9), kx, kz)
        first_board = len(slabs)
        self.board_slab = []                                    # Index of the copper slab of every layer
        for l in range(L):
            f_eff = np.minimum(fill[l] + via_frac, 1.0)
            kx = fill[l] * m.k_copper + (1.0 - fill[l]) * k_lam[l]
            kz = f_eff * m.k_copper + (1.0 - f_eff) * kz_lam[l]
            self.board_slab.append(len(slabs))
            add("cu", l, tc[l], kx, kz)
            if l < L - 1:
                kz = via_frac * m.k_copper + (1.0 - via_frac) * g_kz[l]
                for _ in range(self.n_gap[l]):
                    add("fr4", l, gaps[l] / self.n_gap[l], g_kip[l], kz)
        if L == 1:
            # A one-layer board has no gap, but its laminate is still there under the copper: the slab of the layered models (thickness minus
            # copper, FR-4 of `materials`) as dielectric slabs, so it spreads heat sideways and the bottom face loses heat through it.
            # Without it the board was only its copper (a 20 mm pad on a 60 mm board read 120 degC against about 74 in the other models)
            t_lam = float(b.slab_thicknesses()[0] - tc[0])
            if t_lam > 0:
                kz = via_frac * m.k_copper + (1.0 - via_frac) * m.k_fr4_through
                for _ in range(self.n_gap[0]):
                    add("fr4", 0, t_lam / self.n_gap[0], m.k_fr4_inplane, kz)
        last_board = len(slabs) - 1
        if 1 in faces:
            for kind, dz, kx, kz in block_slabs(1):
                add(kind, L - 1, np.maximum(dz, 1e-9), kx, kz)
        ns = len(slabs)
        n = ns * ny * nx                                         # Equal to unknowns() (checked by the tests), the size the memory guard saw
        self.ns, self.n = ns, n

        # --- Conductances inside the solid (W/K): x and y neighbours in a slab, z neighbours between slabs
        stride = ny * nx
        idx = np.arange(n).reshape(ns, ny, nx)
        rows, cols, vals = [], [], []

        def link(a, b_, g):
            rows.append(a.ravel())
            cols.append(b_.ravel())
            vals.append(g.ravel())

        # A board with an outline joins its cut cells through the open part of the shared face (the aperture, Johansen and Colella 1998), with the physical
        # conductivity: the cover-scaled conductivity made the link into a thin sliver of a cell proportional to the sliver (2c / (1 + c) of a full link), so the heat of
        # the edge column could not reach the sliver and the sliver cell read far too hot (13 % of the rise at 1 mm and a coefficient of 200 W/m2K). Rectangles keep their links
        cut = b.has_outline()
        if cut:
            ap_x, ap_y = face_apertures(b.outline, nx, ny, dx, dy)
            ap_x = ap_x * (self.active[:, :-1] & self.active[:, 1:])      # A cell off the board is joined to nothing
            ap_y = ap_y * (self.active[:-1] & self.active[1:])
        for s, sl in enumerate(slabs):
            dz = sl["dz"]
            if cut and "kphys" in sl:
                k = sl["kphys"]
                g = ap_x * np.minimum(dz[:, :-1], dz[:, 1:]) * dy * 2.0 * k[:, :-1] * k[:, 1:] / ((k[:, :-1] + k[:, 1:]) * dx)
                link(idx[s][:, :-1], idx[s][:, 1:], g)
                g = ap_y * np.minimum(dz[:-1], dz[1:]) * dx * 2.0 * k[:-1] * k[1:] / ((k[:-1] + k[1:]) * dy)
                link(idx[s][:-1], idx[s][1:], g)
                continue
            k = sl["kx"]
            g = np.minimum(dz[:, :-1], dz[:, 1:]) * dy * 2.0 * k[:, :-1] * k[:, 1:] / ((k[:, :-1] + k[:, 1:]) * dx)
            link(idx[s][:, :-1], idx[s][:, 1:], g)
            g = np.minimum(dz[:-1], dz[1:]) * dx * 2.0 * k[:-1] * k[1:] / ((k[:-1] + k[1:]) * dy)
            link(idx[s][:-1], idx[s][1:], g)
        gz_pad_board = None
        for s in range(ns - 1):
            a, c = slabs[s], slabs[s + 1]
            g = Ab / (a["dz"] / (2.0 * a["kz"]) + c["dz"] / (2.0 * c["kz"]))
            link(idx[s], idx[s + 1], g)
            if (a["kind"], c["kind"]) in (("pad", "cu"), ("cu", "pad")):
                gz_pad_board = (s, g)

        # --- Conductances to the ambient, by path
        g_top, g_bottom, g_hs = np.zeros(n), np.zeros(n), np.zeros(n)
        g_side, g_blk, g_leak = np.zeros(n), np.zeros(n), np.zeros(n)
        view = lambda a: a.reshape(ns, ny, nx)                  # noqa: E731
        vt, vb, vs, vk, vl, vh = view(g_top), view(g_bottom), view(g_side), view(g_blk), view(g_leak), view(g_hs)

        def face_g(h, s):
            """Series of the film (h) and half a slab for a face of area A."""
            sl = slabs[s]
            return Ab / (1.0 / np.maximum(h, 1e-12) + sl["dz"] / (2.0 * sl["kz"]))

        # Plain heatsinks add their coefficient on the board face inside their polygon
        he_top, he_bot = np.zeros((ny, nx)), np.zeros((ny, nx))
        for s in problem.heatsinks:
            if not s.is_block():
                (he_top if (s.layer == 0 or L == 1) else he_bot)[:] += s.h_extra * cover(s.polygon, 4)
        top_s, bot_s = self.board_slab[0], last_board
        cov_t = faces[0]["cov"] if 0 in faces else np.zeros((ny, nx))
        cov_b = faces[1]["cov"] if 1 in faces else np.zeros((ny, nx))
        free_t, free_b = 1.0 - cov_t, 1.0 - cov_b                # The board face is covered where a block sits
        h_t, h_b = b.h_top * ones, b.h_bottom * ones
        tot = face_g(h_t + he_top, top_s) * free_t
        share = np.where(h_t + he_top > 0, h_t / np.maximum(h_t + he_top, 1e-12), 1.0)
        vt[top_s] += tot * share
        vh[top_s] += tot * (1.0 - share)
        tot = face_g(h_b + he_bot, bot_s) * free_b
        share = np.where(h_b + he_bot > 0, h_b / np.maximum(h_b + he_bot, 1e-12), 1.0)
        vb[bot_s] += tot * share
        vh[bot_s] += tot * (1.0 - share)
        # Edges of the board
        if b.h_side and b.has_outline():
            # Non-rectangular board: the outline length inside every cell, the film in series with the conduction from the cell centre to the closest outline point
            # (Robin condition at that point, Barrett and others 2022 eq. 12 to 14): g = g0 / (1 + h d / k) with d the signed distance, negative when the centre lies off the
            # board (a sliver cell), floored at 0.25. The distance replaces the fixed half cell of the cover-scaled conductivity, which cut the film off the sliver
            edge = edge_length_on_board(b.outline, nx, ny, dx, dy, self.active)
            on = edge > 0
            ii, jj = np.nonzero(on)
            d_edge = signed_distance_to_outline(b.outline, (jj + 0.5) * dx, (ii + 0.5) * dy)
            for s in range(first_board, last_board + 1):
                sl = slabs[s]
                length, dz, kx = edge[on], sl["dz"][on], sl["kphys"][on]
                g0 = b.h_side * length * dz
                vs[s][on] += g0 / np.maximum(1.0 + b.h_side * d_edge / kx, EDGE_FILM_FLOOR)
        elif b.h_side:
            for s in range(first_board, last_board + 1):
                sl = slabs[s]
                for mask, length, half in ((np.s_[:, 0], dy, dx), (np.s_[:, -1], dy, dx), (np.s_[0, :], dx, dy), (np.s_[-1, :], dx, dy)):
                    dz, kx = sl["dz"][mask], sl["kx"][mask]
                    vs[s][mask] += 1.0 / (1.0 / (b.h_side * length * dz) + (half / 2.0) / (kx * length * dz))
        # Exposed face and sides of the blocks
        for face, f in faces.items():
            h_face = b.h_top if face == 0 else b.h_bottom
            fi = f["fins"]
            hc = fi["h"] + 0.5 * fi["t"]
            with np.errstate(divide="ignore", invalid="ignore"):
                m = np.sqrt(2.0 * max(h_face, 1e-12) / (fi["k"] * np.where(fi["t"] > 0, fi["t"], 1.0)))
                eta = np.where(hc > 0, np.tanh(m * hc) / np.where(m * hc > 0, m * hc, 1.0), 1.0)
                ratio = np.where(fi["p"] > 0, (1.0 - fi["t"] / np.where(fi["p"] > 0, fi["p"], 1.0)) + 2.0 * hc * eta / np.where(fi["p"] > 0, fi["p"], 1.0), 1.0)
            h_tot = h_face * ratio + f["he"]
            h_sd = h_face + f["he"]                                  # The fins stand on the exposed face: the side walls see no fin ratio
            edge = _edge_length(f["cov"], dx, dy)
            blk_ids = [s for s, sl in enumerate(slabs) if sl["kind"] == "blk" and ((s < first_board) == (face == 0))]
            outer = blk_ids[0] if face == 0 else blk_ids[-1]
            vk[outer] += Ab / (1.0 / np.maximum(h_tot, 1e-12) + slabs[outer]["dz"] / (2.0 * slabs[outer]["kz"])) * f["cov"]
            for s in blk_ids:
                vk[s] += h_sd * slabs[s]["dz"] * edge
            for s in range(ns):
                if slabs[s]["kind"] in ("pad", "blk") and ((s < first_board) == (face == 0)):
                    vl[s] += ISOLATED
        g_amb = g_top + g_bottom + g_hs + g_side + g_blk + g_leak
        pin = np.zeros((ns, ny, nx))
        pin[:, ~self.active] = 1.0                              # Cells off the board are pinned to ambient (they carry no heat)
        g_amb = g_amb + pin.ravel()

        # --- Matrix
        offd = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))
        offd = offd + offd.T
        diag = np.asarray(offd.sum(axis=1)).ravel() + g_amb
        self.K = (sp.diags(diag) - offd).tocsc()
        self.g = {"top": g_top, "bottom": g_bottom, "heatsinks": g_hs, "sides": g_side, "blocks": g_blk}
        self.g_leak = g_leak                                    # Counted with the blocks in the energy balance (about 1e-4 of a watt)
        self.slabs, self.fill, self.first_board, self.last_board = slabs, fill, first_board, last_board
        self.gz_pad_board = gz_pad_board

        # --- Heaters on the copper slab of their layer, power exact over the footprint
        Q = np.zeros(n)
        for h in problem.heaters:
            # Exact area of the part on the board in every cell (equal to its share of the exact board cover times that cover)
            w = part_weights(h.polygon, b.outline, nx, ny, dx, dy, cover=bcov) * self.active
            if w.sum() <= 0:                                     # A part off the board: its power goes to the nearest board cell
                cx, cy = polygon_centroid(h.polygon)
                w = np.zeros((ny, nx))
                w[nearest_active_cell(self.active, cx, cy, dx, dy)] = 1.0
            tot_w = w.sum()
            if tot_w > 0:
                Q.reshape(ns, ny, nx)[self.board_slab[h.layer]] += h.power * w / tot_w
        self.Q = Q

    def solve(self):
        """!
        @brief Solve K theta = Q.
        @return Tuple (theta of shape (slabs, ny, nx) in kelvin above ambient, relative residual).
        """
        theta = spla.spsolve(self.K, self.Q, permc_spec=ORDERING)
        res = float(np.linalg.norm(self.K @ theta - self.Q) / max(np.linalg.norm(self.Q), 1e-300))
        return theta.reshape(self.ns, self.ny, self.nx), res


def solve_steady(problem, cell_mm=2.0, n_diel=None, memory_fraction=None):
    """!
    @brief Steady-state solution of the 3D model.
    @param problem A Problem.
    @param cell_mm Target size of the cells in the plan in millimetres.
    @param n_diel Slabs across the dielectric gaps: None (default) is the rule by thickness, ceil(d / 0.2 mm) between 4 and 16 per gap (slabs_per_gap); an int gives every gap the same count (the studies; 4 was the
                  fixed count before the rule and is too few under a part whose side is under about 6.7 times the slab); a sequence gives one count per gap.
    @param memory_fraction Share of the physical memory the solve may use (None: memory.default_fraction()).
    @return SteadyResult with the temperature of the copper slab of every layer (layout of the FVM), the heat by path and, with metal
            blocks, their temperature and heat as the FVM does. A part over absent copper on an outer layer also gets the face terms (arrays "face_peak" and "face_mean", the
            half layer of laminate between the node and the face, laminate.face_terms) as the FVM and FDM, so the temperature read under it is that of its face.
    @throws memory.MemoryGuardError (a ValueError) If the model is too large for the memory guard.
    """
    net = Solid(problem, cell_mm, n_diel, memory_fraction)
    b = problem.board
    theta_all, res = net.solve()
    L = b.layers
    theta = theta_all[net.board_slab]                           # The copper slabs, one per layer
    T = theta + b.ambient
    A = net.area_b
    cells = net.nx * net.ny
    inside = net.active
    l, j, i = np.unravel_index(int(np.argmax(np.where(inside[None], T, -np.inf))), T.shape)
    power_out = {k: float((g * theta_all.ravel()).sum()) for k, g in net.g.items() if k != "blocks"}
    out = SteadyResult(
        model="solid3d", ambient=b.ambient, power_in=float(net.Q.sum()), t_max=float(T[:, inside].max()), t_min=float(T[:, inside].min()),
        t_mean=float((T * net.cover[None]).sum() / (L * net.cover.sum())), layer_mean=[float((T[q] * net.cover).sum() / net.cover.sum()) for q in range(L)],
        t_max_location=(int(l), (i + 0.5) * net.dx, (j + 0.5) * net.dy), T=T, dx=net.dx, dy=net.dy,
        power_out=power_out, residual=res,
        extras={"cells": float(net.n), "slabs": float(net.ns)}, warnings=[])
    if not inside.all():
        out.arrays["board_mask"] = inside
    if laminate.uses_rule(problem):
        # The heat of a part enters the copper slab at mid-thickness: over absent copper the half layer of laminate between that node and the face of the part is not in the
        # slabs (the same term as the layered models, applied to the peak and mean read under the part; a board with a metal block keeps the earlier reading, as they do).
        # It is right only together with the slab rule (research/laminate-2-6 5.1): with 4 slabs per gap alone it makes the solid hotter than the reference
        q_layers = net.Q.reshape(net.ns, net.ny, net.nx)[net.board_slab]
        terms = laminate.face_terms(b, net.fill, q_layers, net.area_b, net.dx)
        if terms is not None:
            out.arrays["face_peak"], out.arrays["face_mean"] = terms
    if net.faces:
        out.power_out["blocks"] = float(((net.g["blocks"] + net.g_leak) * theta_all.ravel()).sum())
        covs, temps = [], []
        for face in sorted(net.faces):
            f = net.faces[face]
            tag = "top" if face == 0 else "bottom"
            ids = [s for s, sl in enumerate(net.slabs) if sl["kind"] == "blk" and ((s < net.first_board) == (face == 0))]
            field = theta_all[ids].mean(axis=0) + b.ambient     # Mean over the thickness of the block
            sel = f["cov"] > 0
            covs.append(f["cov"])
            temps.append(np.where(sel, field, b.ambient))
            if not sel.any():
                # A block wholly off the board (outside the outline, inside its box) has no cell: nothing to report
                continue
            out.extras[f"block_{tag}_max"] = float(theta_all[ids][:, sel].max() + b.ambient)
            out.extras[f"block_{tag}_mean"] = float((field[sel] * f["cov"][sel]).sum() / f["cov"][sel].sum())
            g_air = net.g["blocks"].reshape(net.ns, net.ny, net.nx)
            out.extras[f"block_{tag}_w_to_air"] = float((g_air[ids] * theta_all[ids]).sum())
            pad = next(s for s, sl in enumerate(net.slabs) if sl["kind"] == "pad" and ((s < net.first_board) == (face == 0)))
            nb = pad + 1 if face == 0 else pad - 1
            gz = A / (net.slabs[pad]["dz"] / (2.0 * net.slabs[pad]["kz"]) + net.slabs[nb]["dz"] / (2.0 * net.slabs[nb]["kz"]))
            out.extras[f"block_{tag}_w_to_block"] = float((gz * (theta_all[nb] - theta_all[pad])).sum())
        out.arrays["block_T"] = np.stack(temps)
        out.arrays["block_cov"] = np.stack(covs)
    return out
