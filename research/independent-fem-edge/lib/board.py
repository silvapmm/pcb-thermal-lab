#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file board.py
@brief The layered PCB as a finite-element model: a plan quad mesh extruded through the stack (copper layers, graded laminate gaps), copper per layer
       from polygons, vias as conforming copper cylinders (barrel and fill), heaters on the top copper, films on the faces and the walls.
@details Physics as the finite-volume references of the repository: copper of thickness `t_cu` and conductivity `k_cu`, laminate orthotropic
         (`k_xy` in the plane, `k_z` through the thickness), the gaps between copper layers equal (board thickness minus the copper, over the gaps)
         or given one by one; the side film `h_side` acts on every wall slab, copper and laminate; `h_top` and `h_bottom` on the faces, also under
         the heater unless `source_mode` is 'surface' (then the heater area is a prescribed flux with no film, the convention of the published
         spreading cases). A heater is a polygon on the top copper layer: its power is a uniform volumetric source in the copper elements whose
         centroid lies in the polygon (exact area when the polygon edges are mesh lines). A via is a cylinder: the elements whose plan centroid lies
         within `r_drill` of its centre are copper through every slab (the barrel), those within `r_in` take the fill conductivity; with an O-grid
         patch (`mesh2d.embed_ogrid`) those circles are mesh levels, so the barrel is a conforming cylinder. SI units; the plan mesh is in m.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import fem                                                             # noqa: E402
import mesh2d                                                          # noqa: E402


def graded_gap(thickness, n, ratio=1.4):
    """!
    @brief Element thicknesses of a gap cut in n elements, finest next to both faces (the copper), growing towards the middle.
    @param thickness Gap thickness (m).
    @param n Number of elements.
    @param ratio Size ratio between neighbouring elements (1: uniform).
    @return numpy.ndarray of n thicknesses summing to `thickness`.
    """
    if n == 1:
        return np.array([float(thickness)])
    i = np.arange(n)
    w = ratio ** np.minimum(i, n - 1 - i)
    return thickness * w / w.sum()


def stack(layers, board_t, t_cu=35e-6, n_gap=6, ratio=1.4, gaps=None, n_cu=1):
    """!
    @brief Slabs of the stack from the top face down.
    @param layers Copper layers (1 or more).
    @param board_t Board thickness in m, copper included (ignored when `gaps` is given).
    @param t_cu Copper thickness in m (a number, or one per layer).
    @param n_gap Elements per gap.
    @param ratio Grading ratio of the gap elements.
    @param gaps Gap thicknesses in m, one per gap (default: equal gaps that make up `board_t`).
    @param n_cu Elements through every copper layer.
    @return Tuple (dz (nz,), kind list of ('cu', layer) or ('gap', gap)).
    """
    tcu = np.broadcast_to(np.asarray(t_cu, float), (layers,))
    if gaps is None:
        gaps = [(board_t - tcu.sum()) / max(layers - 1, 1)] * max(layers - 1, 0)
    dz, kind = [], []
    for l in range(layers):
        for _ in range(n_cu):
            dz.append(tcu[l] / n_cu)
            kind.append(("cu", l))
        if l < layers - 1:
            for t in graded_gap(gaps[l], n_gap, ratio):
                dz.append(t)
                kind.append(("gap", l))
    return np.asarray(dz), kind


def extrude(plan, dz):
    """!
    @brief Extrude a plan mesh through the slabs (z = 0 the top face, z growing downwards).
    @param plan Quad2D plan mesh.
    @param dz Slab thicknesses (nz,).
    @return dict with nodes (N, 3), elems (E, 8), slab (E,), quad (E,), zn (nz + 1,), n_plan (plan nodes).
    """
    zn = np.concatenate([[0.0], np.cumsum(dz)])
    Np, Q, nz = plan.xy.shape[0], plan.quads.shape[0], dz.size
    nodes = np.column_stack([np.tile(plan.xy, (nz + 1, 1)), np.repeat(zn, Np)])
    q = plan.quads
    elems = np.concatenate([np.tile(q, (nz, 1)) + np.repeat(np.arange(nz) * Np, Q)[:, None],
                            np.tile(q, (nz, 1)) + np.repeat((np.arange(nz) + 1) * Np, Q)[:, None]], axis=1)
    return {"nodes": nodes, "elems": elems, "slab": np.repeat(np.arange(nz), Q), "quad": np.tile(np.arange(Q), nz), "zn": zn, "n_plan": Np}


def in_polygons(pts, polys):
    """!
    @brief Points inside the union of polygons (each in m).
    @param pts Points (P, 2).
    @param polys A polygon (V, 2) or a list of polygons; None means everywhere.
    @return bool (P,).
    """
    if polys is None:
        return np.ones(pts.shape[0], bool)
    if np.ndim(polys[0][0]) == 0:
        polys = [polys]
    m = np.zeros(pts.shape[0], bool)
    for p in polys:
        m |= mesh2d.point_in_polygon(pts, p)
    return m


class Board:
    """!
    @brief A layered board on a plan mesh, built into a finite-element model and solved.
    """

    def __init__(self, plan, layers, board_t=1.6e-3, t_cu=35e-6, k_cu=385.0, k_xy=0.9, k_z=0.3, gaps=None, n_gap=6, gap_ratio=1.4, n_cu=1,
                 h_top=10.0, h_bottom=10.0, h_side=0.0, symmetry=(), copper=None, vias=(), heaters=(), source_mode="volume", outline_wall=None):
        """!
        @brief Describe the board.
        @param plan Quad2D plan mesh (m); its boundary edges are the walls.
        @param layers Copper layers.
        @param board_t Board thickness in m, copper included.
        @param t_cu Copper thickness in m (number or one per layer).
        @param k_cu Copper conductivity W/mK.
        @param k_xy Laminate in-plane conductivity W/mK.
        @param k_z Laminate through-thickness conductivity W/mK.
        @param gaps Gap thicknesses in m (default equal gaps from `board_t`).
        @param n_gap Elements per gap.
        @param gap_ratio Grading ratio of the gap elements.
        @param n_cu Elements through a copper layer.
        @param h_top Top face film W/m2K.
        @param h_bottom Bottom face film W/m2K.
        @param h_side Wall film W/m2K (every wall slab).
        @param symmetry Lines where the wall is a symmetry plane (no film): list of ('x', value) or ('y', value) in m.
        @param copper Copper of every layer: a list (one entry per layer) of a polygon (V, 2) in m, a list of polygons, None for full copper, or a
                      callable(centroids (Q, 2)) -> bool array; a single entry is used for every layer.
        @param vias List of dicts: cx, cy, r_drill (m), optional r_in (m, inner radius of the barrel; 0 = solid), k_fill (W/mK, default k_cu).
        @param heaters List of (polygon (V, 2) in m, power W) on the top copper layer.
        @param source_mode 'volume': uniform source in the top copper elements under the heater, films on the whole faces; 'surface': prescribed flux
                           on the top face over the heater, no film there (the convention of the spreading papers).
        @param outline_wall Optional callable(edge midpoints (B, 2)) -> bool: which boundary edges carry the film (default all but the symmetry lines).
        @return None.
        """
        self.plan, self.layers, self.k_cu, self.k_xy, self.k_z = plan, layers, k_cu, k_xy, k_z
        self.dz, self.kind = stack(layers, board_t, t_cu, n_gap, gap_ratio, gaps, n_cu)
        self.h_top, self.h_bottom, self.h_side, self.symmetry = h_top, h_bottom, h_side, list(symmetry)
        # a Python list is one entry per layer; anything else (None, a callable, a polygon as an array or a tuple of points) is used for every layer
        if isinstance(copper, list):
            if len(copper) != layers:
                raise ValueError("copper: one entry per layer (give a single polygon as an array or a tuple, not a list)")
            self.copper = copper
        else:
            self.copper = [copper] * layers
        self.vias, self.heaters, self.source_mode, self.outline_wall = list(vias), list(heaters), source_mode, outline_wall

    def copper_mask(self, layer, c):
        """!
        @brief Copper of a layer at the quad centroids.
        @param layer Layer index (0 = top).
        @param c Centroids (Q, 2).
        @return bool (Q,).
        """
        cu = self.copper[layer]
        if cu is None:
            return np.ones(c.shape[0], bool)
        if callable(cu):
            return np.asarray(cu(c), bool)
        return in_polygons(c, cu)

    def build(self):
        """!
        @brief Build the finite-element model.
        @return Tuple (fem.Model, info dict: top_faces, bottom_faces, heater_faces (lists of (F, 4) node arrays), heater_elems (E ids), heater_area m2,
                ex (the extrusion dict), top_cu (bool per plan quad)).
        """
        plan = self.plan
        ex = extrude(plan, self.dz)
        m = fem.Model(ex["nodes"], ex["elems"])
        c = plan.centroids()
        Q = c.shape[0]
        slab, quad = ex["slab"], ex["quad"]
        kx = np.empty(m.elems.shape[0])
        kz = np.empty(m.elems.shape[0])
        cu_masks = [self.copper_mask(l, c) for l in range(self.layers)]
        for s, kd in enumerate(self.kind):
            sel = slab == s
            if kd[0] == "cu":
                cu = cu_masks[kd[1]][quad[sel]]
                kx[sel] = np.where(cu, self.k_cu, self.k_xy)
                kz[sel] = np.where(cu, self.k_cu, self.k_z)
            else:
                kx[sel] = self.k_xy
                kz[sel] = self.k_z
        for v in self.vias:
            r = np.hypot(c[:, 0] - v["cx"], c[:, 1] - v["cy"])
            barrel = (r < v["r_drill"]) & (r >= v.get("r_in", 0.0))
            fill = r < v.get("r_in", 0.0)
            kf = v.get("k_fill", self.k_cu)
            kx[barrel[quad]] = self.k_cu
            kz[barrel[quad]] = self.k_cu
            kx[fill[quad]] = kf
            kz[fill[quad]] = kf
        m.k[:, 0] = kx
        m.k[:, 1] = kx
        m.k[:, 2] = kz
        Np = ex["n_plan"]
        nz = self.dz.size
        top = plan.quads.copy()
        bottom = plan.quads + nz * Np
        heater_faces, heater_elems, heater_area = [], [], 0.0
        top_cu = cu_masks[0]
        areas = plan.areas()
        for poly, power in self.heaters:
            sel = in_polygons(c, poly)
            area = float(areas[sel].sum())
            heater_area += area
            heater_faces.append(top[sel])
            if self.source_mode == "volume":
                top_slabs = [s for s, kd in enumerate(self.kind) if kd == ("cu", 0)]
                els = np.nonzero(np.isin(slab, top_slabs) & sel[quad])[0]
                t_top = float(self.dz[top_slabs].sum())
                m.q[els] += power / (area * t_top)
                heater_elems.append(els)
            else:
                m.add_faces(top[sel], h=0.0, flux=power / area)
        hsel = np.zeros(Q, bool)
        for poly, _ in self.heaters:
            hsel |= in_polygons(c, poly)
        if self.source_mode == "volume":
            m.add_faces(top, h=self.h_top)
        else:
            m.add_faces(top[~hsel], h=self.h_top)
        m.add_faces(bottom, h=self.h_bottom)
        edges, owner = plan.boundary_edges()
        mid = plan.xy[edges].mean(axis=1)
        film = np.ones(edges.shape[0], bool)
        for axis, value in self.symmetry:
            film &= np.abs(mid[:, 0 if axis == "x" else 1] - value) > 1e-9
        if self.outline_wall is not None:
            film &= np.asarray(self.outline_wall(mid), bool)
        if self.h_side > 0 and film.any():
            e = edges[film]
            for s in range(nz):
                f = np.column_stack([e[:, 0] + s * Np, e[:, 1] + s * Np, e[:, 1] + (s + 1) * Np, e[:, 0] + (s + 1) * Np])
                m.add_faces(f, h=self.h_side)
        info = {"top_faces": top, "bottom_faces": bottom, "heater_faces": heater_faces, "heater_elems": heater_elems, "heater_area": heater_area,
                "ex": ex, "top_cu": top_cu, "wall_edges": edges[film]}
        return m, info

    def solve(self, **kw):
        """!
        @brief Build and solve; read out the hottest top-face node, the heater mean and the balance.
        @param kw Passed to `fem.Model.solve`.
        @return dict: tmax (hottest top-face node, K), heater_mean (surface mean of the heater area, K), heater_max (hottest heater node), balance,
                n, E, peak_gb, solver, T (node field), model, info.
        """
        m, info = self.build()
        r = m.solve(**kw)
        T = r["T"]
        Np = info["ex"]["n_plan"]
        out = {"tmax": float(np.nanmax(T[:Np])), "balance": r["balance"], "n": r["n"], "E": r["E"], "peak_gb": r["peak_gb"], "solver": r["solver"],
               "T": T, "model": m, "info": info, "q_in": r["q_in"]}
        if info["heater_faces"]:
            hf = np.vstack(info["heater_faces"])
            tot, area = m.face_integral(T, hf)
            out["heater_mean"] = tot / area
            out["heater_max"] = float(np.nanmax(T[hf]))
            out["heater_area"] = area
        return out


def cell_max(res, cell, x0=0.0, y0=0.0, sub=8):
    """!
    @brief The hottest CELL MEAN of the top-face field on a square grid of the given cell (the read-out of the program and of the cell-centred references), for a
           board whose plan mesh is a tensor grid.
    @details The trilinear field on the top face is bilinear on every quad; it is sampled on `sub x sub` points per cell (bilinear interpolation on the tensor
             grid) and averaged, and the largest cell mean is returned. A cell outside the mesh (symmetry half) is ignored.
    @param res Result of `Board.solve` (its model's plan must be a tensor grid).
    @param cell Cell size in m.
    @param x0 Origin of the cell grid in x (m).
    @param y0 Origin of the cell grid in y (m).
    @param sub Samples per cell side.
    @return float hottest cell mean, K.
    """
    from scipy.interpolate import RegularGridInterpolator
    m = res["model"]
    Np = res["info"]["ex"]["n_plan"]
    xy = m.nodes[:Np, :2]
    xn, yn = np.unique(xy[:, 0]), np.unique(xy[:, 1])
    if xn.size * yn.size != Np:
        raise ValueError("cell_max needs a tensor plan mesh")
    order = np.lexsort((xy[:, 0], xy[:, 1]))
    T = res["T"][:Np][order].reshape(yn.size, xn.size)
    f = RegularGridInterpolator((yn, xn), T, bounds_error=False, fill_value=np.nan)
    nx = int(np.floor((xn[-1] - x0) / cell + 1e-9))
    ny = int(np.floor((yn[-1] - y0) / cell + 1e-9))
    off = (np.arange(sub) + 0.5) / sub
    best = -np.inf
    for j in range(ny):
        for i in range(nx):
            px = x0 + (i + off) * cell
            py = y0 + (j + off) * cell
            P = np.array(np.meshgrid(py, px, indexing="ij")).reshape(2, -1).T
            v = f(P)
            if np.isnan(v).any():
                continue
            best = max(best, float(v.mean()))
    return best
