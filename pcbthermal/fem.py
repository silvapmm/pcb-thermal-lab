#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fem.py
@brief Finite-element comparison model of the board (steady state): the Problem as a 3D mesh of hexahedra (femmesh), solved by the Q1 Galerkin solver (femcore), read out
       in the layout of the other models. Comparison model, key `fem`; never the reference of a decision.
@details **What it is.** The board is a continuous trilinear temperature field on hexahedra that conform to the copper slabs, the graded laminate gaps, the blocks with their
         interface pads and the hollow via barrels (femmesh.build). The film on a face is the natural boundary integral `h N_i N_j` on the real face, so there is NO half-cell
         film in series (contrast docs/theory.md 1.2a): the plain `h` of the problem (`board.h_top`, `board.h_bottom`, `board.h_side`, the heatsink `h_extra`, the block
         `exposed_h` and `wall_h`) is the boundary coefficient, and a 1D column with a source over the whole face reads `T_face = T_amb + q / h` exactly (tests/test_fem_model.py).
         The computed-h loop (api._solve_computed_h), the top-path split and the power coefficient (api._solve_with_tc) wrap this model as they wrap the others: they read
         `layer_mean[0]`, `layer_mean[-1]` (and `bottom_face_mean` for a one-layer board) and the part rows of `analysis.heater_stats` on the column read-out.
         **Three read-outs** (docs/theory.md 4a, named the same everywhere):
         * **column** (the headline: `T`, `t_max`, `t_mean`, `layer_mean`, the part rows): for a cell of the run grid and a copper layer, the volume mean of the trilinear field
           over that cell and the copper slabs of that layer (the elements are shared between cells in proportion to the overlap of their plan rectangle); like for like with the
           node value of the FVM, FDM and 3D solid;
         * **surface**: the area mean of the field over the cell on the outer face of the outer copper layers (top of layer 1, bottom of the last layer; for a one-layer board the
           bottom face of its laminate), resolved, not the parabola of thickness.py: `arrays["T_surface"]` and `arrays["T_surface_mean"]` (2, ny, nx; both are that area mean, so
           that their difference from the column is the through-thickness term only), `arrays["T_surface_flag"]` (all False: nothing is estimated), `extras["t_max_surface_top"]`,
           `["t_max_surface_bottom"]`, `["surface_excess_k"]`; the names and the meaning of thickness.py, so the Layer entries and the part rows read them unchanged;
         * **point**: the hottest node of the whole mesh, `extras["t_max_point"]`, and `arrays["T_point"]` (2, ny, nx), the hottest node of each face in each cell.
         Cells off the outline carry the ambient and `arrays["board_mask"]` is False there. The heat leaves by the paths `top`, `bottom`, `edge` and `blocks` (the face integral of
         `h theta`), so `balance_error` is the balance of the assembly itself (an identity of a consistent mesh, printed for every solve).
         **Refusals** (ValueError with the reason): a slanted or curved outline, too many break lines, a cell that is too fine, a mesh above the memory guard. Without pyamg a mesh
         above `femcore.FEM_DIRECT_MAX` unknowns raises femcore.FemUnavailable (a RuntimeError the API turns into a skipped model).
         Steady state only; the time simulation is a later stage. SI units inside; temperatures in degC at the interface.
"""

import logging
from typing import Callable, Optional

import numpy as np

from . import blocks, femcore, femmesh, memory
from .results import SteadyResult

log = logging.getLogger(__name__)


def available() -> bool:
    """!
    @brief Whether the optional package of the conjugate-gradient path (pyamg) can be imported.
    @return True when the FEM can solve a mesh of any size, False when only meshes within femcore.FEM_DIRECT_MAX unknowns can be solved.
    """
    return femcore.available()


def _gauss_weights(model, T, el, kind):
    """!
    @brief Integral of the nodal field over every element (kind "volume") or over the top or bottom face of every element (kind "top", "bottom"), and the matching measure.
    @param model femcore.Model.
    @param T Node field (N,) in kelvin of rise.
    @param el Element ids (n,).
    @param kind "volume", "top" (the first four local nodes: the face of the lower plane index) or "bottom" (the last four).
    @return Tuple (integral (n,), measure (n,)) in K m3 and m3 (volume) or K m2 and m2 (face).
    """
    conn = model.elems[np.asarray(el, np.int64)]
    G = femcore.G1
    tot = np.zeros(conn.shape[0])
    meas = np.zeros(conn.shape[0])
    if kind == "volume":
        X = model.nodes[conn]
        for gx in (-G, G):
            for gy in (-G, G):
                for gz in (-G, G):
                    n, dn = femcore.shape(gx, gy, gz)
                    det = np.abs(np.linalg.det(np.einsum("eai,aj->eij", X, dn)))
                    tot += (T[conn] @ n) * det
                    meas += det
        return tot, meas
    fn = conn[:, :4] if kind == "top" else conn[:, 4:]
    X = model.nodes[fn]
    for gx in (-G, G):
        for gy in (-G, G):
            n, dn = femcore.face_shape(gx, gy)
            t = np.einsum("fai,aj->fij", X, dn)
            dA = np.linalg.norm(np.cross(t[:, :, 0], t[:, :, 1]), axis=1)
            tot += (T[fn] @ n) * dA
            meas += dA
    return tot, meas


def _cell_shares(plan, quad_ids, nx, ny, width, height):
    """!
    @brief Share of every plan quad that falls in each cell of the run grid (the quads are rectangles of the tensor grid or small patch quads, taken by their box).
    @param plan femmesh.Plan.
    @param quad_ids Quad ids (n,).
    @param nx Cells along x, count.
    @param ny Cells along y, count.
    @param width Board width in m.
    @param height Board height in m.
    @return List of tuples (index into quad_ids, cell column, cell row, share in [0, 1]); the shares of one quad add up to 1.
    """
    q = np.asarray(quad_ids, np.int64)
    dx, dy = width / nx, height / ny
    x0, x1, y0, y1 = plan.x0[q], plan.x1[q], plan.y0[q], plan.y1[q]
    ix0 = np.clip(np.floor(x0 / dx + 1e-9).astype(np.int64), 0, nx - 1)
    ix1 = np.clip(np.ceil(x1 / dx - 1e-9).astype(np.int64) - 1, 0, nx - 1)
    iy0 = np.clip(np.floor(y0 / dy + 1e-9).astype(np.int64), 0, ny - 1)
    iy1 = np.clip(np.ceil(y1 / dy - 1e-9).astype(np.int64) - 1, 0, ny - 1)
    out = []
    span_x = int((ix1 - ix0).max()) + 1 if q.size else 0
    span_y = int((iy1 - iy0).max()) + 1 if q.size else 0
    wx = np.maximum(x1 - x0, 1e-30)
    wy = np.maximum(y1 - y0, 1e-30)
    for a in range(span_x):
        cx = ix0 + a
        okx = cx <= ix1
        ox = np.clip(np.minimum(x1, (cx + 1) * dx) - np.maximum(x0, cx * dx), 0.0, None) / wx
        for b in range(span_y):
            cy = iy0 + b
            ok = okx & (cy <= iy1)
            oy = np.clip(np.minimum(y1, (cy + 1) * dy) - np.maximum(y0, cy * dy), 0.0, None) / wy
            w = ox * oy
            sel = np.nonzero(ok & (w > 0))[0]
            if sel.size:
                out.append((sel, cx[sel], cy[sel], w[sel]))
    return out


def _to_cells(shares, values, weights, nx, ny):
    """!
    @brief Weighted mean of per-element values on the cells of the run grid.
    @param shares Output of _cell_shares for the elements (or faces).
    @param values Integral of the field over every element or face (n,).
    @param weights Measure (volume or area) of every element or face (n,).
    @param nx Cells along x, count.
    @param ny Cells along y, count.
    @return Tuple (mean (ny, nx), measure (ny, nx)); mean is 0 where the measure is 0.
    """
    num = np.zeros((ny, nx))
    den = np.zeros((ny, nx))
    for sel, cx, cy, w in shares:
        np.add.at(num, (cy, cx), w * values[sel])
        np.add.at(den, (cy, cx), w * weights[sel])
    return np.divide(num, den, out=np.zeros_like(num), where=den > 0), den


def _fill_empty(field, have, active):
    """!
    @brief Give the active cells with no element (inside a drill that is open) the value of the nearest cell that has one.
    @param field Values (ny, nx).
    @param have True where the field was computed.
    @param active True on the board.
    @return numpy.ndarray The field with the holes filled.
    """
    miss = active & ~have
    if not miss.any() or not have.any():
        return field
    from scipy import ndimage
    idx = ndimage.distance_transform_edt(~have, return_distances=False, return_indices=True)
    return np.where(miss, field[idx[0], idx[1]], field)


def solve_steady(problem, cell_mm: float = 2.0, memory_fraction: Optional[float] = None, gap_elements: int = 6, refine: float = 2.0,
                 cancel: Optional[Callable[[], bool]] = None, force_solver: Optional[str] = None) -> SteadyResult:
    """!
    @brief Steady-state solution of the board by finite elements, read out in the layout of the other models.
    @details Builds the mesh (femmesh.build with the plain face coefficients of the problem), asks the memory guard first (the exact unknown count), solves and reads the three
             read-outs of the module docstring. The face coefficients are the typed ones of `problem.board`: the computed-h loop of the API sets them before each call.
    @param problem A Problem.
    @param cell_mm Plan cell in mm (the coarse element and the grid of the result).
    @param memory_fraction Share of the physical memory the solve may use (None: memory.default_fraction()).
    @param gap_elements Elements across every dielectric gap, count (2 to 24).
    @param refine Ratio of the cell to the fine element near the heaters and via patches (1 to 4).
    @param cancel Optional callable checked between assembly chunks; True raises femcore.FemCancelled.
    @param force_solver None (by size), "direct" or "cg" (tests and studies).
    @return SteadyResult (model "fem"; T per layer is the column read-out, arrays T_surface and the rest as in the module docstring).
    @throws memory.MemoryGuardError (a ValueError) If the estimated memory is above the limit.
    @throws ValueError With the reason when no mesh can be built (slanted outline, too many break lines, a cell that is too fine).
    @throws femcore.FemUnavailable If the mesh needs the conjugate gradients and pyamg is not installed.
    @throws femcore.FemCancelled If `cancel` returned True.
    """
    memory.check(problem, ("fem",), cell_mm, fraction=memory_fraction, fem_params=(gap_elements, refine), quiet=True)
    unknowns = femmesh.unknowns(problem, cell_mm, gap_elements, refine)[0]
    if unknowns > femcore.FEM_DIRECT_MAX and force_solver != "direct" and not femcore.available():
        raise femcore.FemUnavailable(f"the FEM mesh has {unknowns} unknowns, above the {femcore.FEM_DIRECT_MAX} that the direct solver takes, and the package pyamg is not "
                                     "installed (pip install pyamg): use a coarser cell or install it")
    mesh = femmesh.build(problem, cell_mm, gap_elements, refine)
    model = mesh.model
    sol = model.solve(cancel=cancel, force=force_solver)
    th = sol["T"]
    b = problem.board
    L = b.layers
    W, H = b.width, b.height
    nx = max(int(round(W * 1000.0 / cell_mm)), 2)
    ny = max(int(round(H * 1000.0 / cell_mm)), 2)
    dx, dy = W / nx, H / ny
    cover = b.cover(nx, ny, dx, dy)
    active = cover > 0
    plan = mesh.plan
    amb = b.ambient

    # --- column read-out: volume mean over the copper slabs of every layer, shared between the cells by the overlap of the plan quads
    T = np.full((L, ny, nx), amb)
    for l in range(L):
        ids = np.concatenate([np.arange(*_slab_range(mesh, s)) for s in mesh.copper_slabs[l]]) if mesh.copper_slabs[l] else np.zeros(0, np.int64)
        if not ids.size:
            continue
        tot, vol = _gauss_weights(model, th, ids, "volume")
        mean, den = _to_cells(_cell_shares(plan, mesh.elem_quad[ids], nx, ny, W, H), tot, vol, nx, ny)
        have = den > 0
        T[l] = amb + _fill_empty(mean, have, active)
    T = np.where(active[None], T, amb)

    # --- surface and point read-outs on the outer faces
    surf = np.full((2, ny, nx), np.nan)
    point = np.full((2, ny, nx), np.nan)
    board_slabs = [s for s, sl in enumerate(mesh.slabs) if sl["region"] == "board"]
    for face, s_face, kind in ((0, board_slabs[0], "top"), (1, board_slabs[-1], "bottom")):
        ids = np.arange(*_slab_range(mesh, s_face))
        tot, area = _gauss_weights(model, th, ids, kind)
        mean, den = _to_cells(_cell_shares(plan, mesh.elem_quad[ids], nx, ny, W, H), tot, area, nx, ny)
        surf[face] = np.where(active, amb + _fill_empty(mean, den > 0, active), np.nan)
        conn = model.elems[ids][:, :4] if kind == "top" else model.elems[ids][:, 4:]
        pk = th[conn].max(axis=1)
        qx = np.clip((plan.cx[mesh.elem_quad[ids]] / W * nx).astype(np.int64), 0, nx - 1)
        qy = np.clip((plan.cy[mesh.elem_quad[ids]] / H * ny).astype(np.int64), 0, ny - 1)
        pm = np.full((ny, nx), -np.inf)
        np.maximum.at(pm, (qy, qx), pk)
        point[face] = np.where(np.isfinite(pm) & active, amb + pm, np.nan)
        point[face] = np.where(np.isnan(point[face]) & active, surf[face], point[face])

    inside = active
    loc = np.unravel_index(int(np.argmax(np.where(inside[None], T, -np.inf))), T.shape)
    layer_mean = [float((T[q] * cover).sum() / cover.sum()) for q in range(L)]
    # --- the heat by path: the face integral of h theta over every labelled group (an identity of the assembly: it checks it)
    paths = {}
    for f in model.faces:
        lab = f.get("label") or "other"
        lab = "blocks" if lab.startswith("block") else lab
        if lab == "source":
            continue                                               # the face flux of a part on a thick outer layer: heat in, not a path out
        paths[lab] = paths.get(lab, 0.0) + _film_heat(model, th, f)
    power_in = float(sol["q_in"])                                  # the volumetric sources plus the face fluxes of the parts on a thick outer layer
    out = SteadyResult(
        model="fem", ambient=amb, power_in=power_in, t_max=float(T[:, inside].max()), t_min=float(T[:, inside].min()),
        t_mean=float((T * cover[None]).sum() / (L * cover.sum())), layer_mean=layer_mean,
        t_max_location=(int(loc[0]), (loc[2] + 0.5) * dx, (loc[1] + 0.5) * dy), T=T, dx=dx, dy=dy,
        power_out=paths, residual=float(sol["residual"]),
        extras={"unknowns": float(sol["n"]), "elements": float(sol["E"]), "peak_gb": float(sol["peak_gb"]), "balance": float(sol["balance"]),
                "patches": float(mesh.n_patches), "rods": float(mesh.n_rods), "cg": 1.0 if sol["solver"] == "cg" else 0.0,
                "t_max_point": float(amb + np.nanmax(th)), "plan_cells_x": float(plan.xn.size - 1), "plan_cells_y": float(plan.yn.size - 1)},
        warnings=list(mesh.warnings))
    if not inside.all():
        out.arrays["board_mask"] = inside
    out.arrays["T_surface"] = surf
    out.arrays["T_surface_mean"] = surf.copy()
    out.arrays["T_surface_flag"] = np.zeros((2, ny, nx), bool)
    out.arrays["T_point"] = point
    exc = []
    for face, lay in ((0, 0), (1, L - 1)):
        d = np.abs(surf[face] - T[lay])
        if np.isfinite(d).any():
            exc.append(float(np.nanmax(d)))
        if np.isfinite(surf[face]).any():
            out.extras[f"t_max_surface_{'top' if face == 0 else 'bottom'}"] = float(np.nanmax(surf[face]))
    out.extras["surface_excess_k"] = max(exc) if exc else 0.0
    if L == 1:
        # The bottom face of a one-layer board is the last laminate node of the other models: the film temperature the computed-h loop reads
        bm = np.nanmean(np.where(active, surf[1], np.nan))
        out.extras["bottom_face_mean"] = float(bm)
    _blocks_readout(out, problem, mesh, th, nx, ny, amb)
    if abs(out.balance_error) > 1e-6:
        out.warnings.append(f"the energy balance of the finite-element solve is off by {out.balance_error:+.2e}: check the mesh and the solve")
    return out


def _slab_range(mesh, s):
    """!
    @brief First and last+1 element id of a slab.
    @param mesh femmesh.FemMesh.
    @param s Slab index.
    @return Tuple (first id, one past the last id).
    """
    ids = np.nonzero(mesh.elem_slab == s)[0]
    return (int(ids[0]), int(ids[-1]) + 1) if ids.size else (0, 0)


def _film_heat(model, th, f):
    """!
    @brief Heat leaving through one group of film faces: the integral of h theta over the faces.
    @param model femcore.Model.
    @param th Node field (N,) in kelvin of rise.
    @param f One entry of model.faces.
    @return float Heat in W.
    """
    fn = f["nodes"]
    X = model.nodes[fn]
    G = femcore.G1
    tot = 0.0
    for gx in (-G, G):
        for gy in (-G, G):
            n, dn = femcore.face_shape(gx, gy)
            t = np.einsum("fai,aj->fij", X, dn)
            dA = np.linalg.norm(np.cross(t[:, :, 0], t[:, :, 1]), axis=1)
            tot += float((f["h"] * (th[fn] @ n) * dA).sum())
    return tot


def _blocks_readout(out, problem, mesh, th, nx, ny, amb):
    """!
    @brief The metal blocks of the mesh as the other models report them (arrays block_T and block_cov, extras block_<face>_max, _mean, _w_to_air, _w_to_block).
    @details The block temperature of a cell is the volume mean over the thickness of the block slabs. A block has no source, so in steady state the heat that enters it through
             the interface equals the heat that leaves it through its exposed face and walls: both extras are the same film integral (an identity, not two measurements).
    @param out SteadyResult being filled.
    @param problem The Problem (the block polygons and their face).
    @param mesh femmesh.FemMesh.
    @param th Node field (N,) in kelvin of rise.
    @param nx Cells along x, count.
    @param ny Cells along y, count.
    @param amb Ambient in degC.
    """
    b = problem.board
    L = b.layers
    model = mesh.model
    W, H = b.width, b.height
    dx, dy = W / nx, H / ny
    bcov = b.cover(nx, ny, dx, dy)
    cov_f = {}
    for s in problem.heatsinks:
        if not s.is_block():
            continue
        face = 0 if (s.layer == 0 or L == 1) else 1
        c = blocks.block_cover(s.polygon, b.outline if b.has_outline() else None, nx, ny, dx, dy, bcov)
        cov_f[face] = np.where(c > 0, c, cov_f.get(face, np.zeros((ny, nx))))
    if not cov_f:
        return
    covs, temps = [], []
    for face in sorted(cov_f):
        tag = "top" if face == 0 else "bottom"
        sel = np.array([sl["region"] == "blk" and sl["kind"] == "blk" and sl["face"] == face for sl in mesh.slabs])
        ids = np.nonzero(sel[mesh.elem_slab])[0]
        fld = np.full((ny, nx), amb)
        if ids.size:
            tot, vol = _gauss_weights(model, th, ids, "volume")
            mean, den = _to_cells(_cell_shares(mesh.plan, mesh.elem_quad[ids], nx, ny, W, H), tot, vol, nx, ny)
            fld = np.where(den > 0, amb + mean, amb)
        cov = cov_f[face]
        covs.append(cov)
        temps.append(fld)
        on = cov > 0
        if not on.any():
            continue
        heat = sum(_film_heat(model, th, f) for f in model.faces if f.get("label") == f"block_{tag}")
        out.extras[f"block_{tag}_max"] = float(fld[on].max())
        out.extras[f"block_{tag}_mean"] = float((fld[on] * cov[on]).sum() / cov[on].sum())
        out.extras[f"block_{tag}_w_to_air"] = float(heat)
        out.extras[f"block_{tag}_w_to_block"] = float(heat)
    out.arrays["block_T"] = np.stack(temps)
    out.arrays["block_cov"] = np.stack(covs)
