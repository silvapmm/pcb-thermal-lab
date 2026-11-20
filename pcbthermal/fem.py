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
           bottom face of its copper, as in thickness.py; the bottom of its laminate is `extras["bottom_face_mean"]`), resolved, not the parabola of thickness.py: `arrays["T_surface"]` and `arrays["T_surface_mean"]` (2, ny, nx; both are that area mean, so
           that their difference from the column is the through-thickness term only), `arrays["T_surface_flag"]` (all False: nothing is estimated), `extras["t_max_surface_top"]`,
           `["t_max_surface_bottom"]`, `["surface_excess_k"]`; the names and the meaning of thickness.py, so the Layer entries and the part rows read them unchanged;
         * **point**: the hottest node of the whole mesh, `extras["t_max_point"]`, and `arrays["T_point"]` (2, ny, nx), the hottest node of each face in each cell.
         Cells off the outline carry the ambient and `arrays["board_mask"]` is False there. The heat leaves by the paths `top`, `bottom`, `edge` and `blocks` (the face integral of
         `h theta`), so `balance_error` is the balance of the assembly itself (an identity of a consistent mesh, printed for every solve).
         **Refusals** (ValueError with the reason): a slanted or curved outline, too many break lines, a cell that is too fine, a mesh above the memory guard. Without pyamg a mesh
         above `femcore.FEM_DIRECT_MAX` unknowns raises femcore.FemUnavailable (a RuntimeError the API turns into a skipped model).
         **Time** (since 2.9.0, `solve_transient`, `step_responses`; docs/theory.md 4b): the semi-discrete system `M dT/dt + A T = p(t) F` with the consistent mass `M` (the heat
         capacity `rho c` per element of femmesh: the copper of the fill and the laminate of the rest of every slab, the dielectric gaps, the metal blocks; NOT the copper of a via
         barrel, the interface pad or a part, as the FVM and FDM do not count them) and the theta step of `femcore.Stepper`, one factor alive. The column read-out of every output
         frame is a sparse linear operator made once; the surface read-out of the transient is not delivered yet (`TransientResult.arrays["T_surface"]` is reserved for it).
         SI units inside; temperatures in degC at the interface.
"""

import logging
from typing import Callable, Optional

import numpy as np
import scipy.sparse as sp

from . import blocks, femcore, femmesh, memory
from .results import SteadyResult, TransientResult

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
    @throws ValueError With the reason when no mesh can be built (slanted outline, too many break lines, a cell that is too fine), or when the conjugate gradients do not
                       converge (the RuntimeError of femcore turned into a refusal, so that the other models of a run still answer).
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
    try:
        sol = model.solve(cancel=cancel, force=force_solver)
    except (femcore.FemUnavailable, femcore.FemCancelled):
        raise
    except RuntimeError as exc:
        # A conjugate-gradient solve that does not reach its residual is a failure of this comparison model, not of the run: as a ValueError the API leaves the FEM
        # out with the reason when other models are ticked and says the reason when it is the only one (a raw RuntimeError would stop every model of the run)
        raise ValueError(f"the finite-element solve did not converge ({exc}); a coarser cell or a smaller refinement gives a smaller system") from exc
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
    # The faces of thickness.py: the top of layer 1 and the bottom of the last copper layer. On a one-layer board that bottom is the face of the copper on the laminate,
    # NOT the bottom of the laminate (which would put the whole laminate drop in the surface excess and in the report of an ordinary 35 um board); the bottom of the
    # laminate is read apart below as bottom_face_mean, the film temperature of the computed-h loop
    bottom_slab = mesh.copper_slabs[0][-1] if (L == 1 and mesh.copper_slabs[0]) else board_slabs[-1]
    for face, s_face, kind in ((0, board_slabs[0], "top"), (1, bottom_slab, "bottom")):
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
        # The bottom face of a one-layer board (the bottom of its laminate) is the last laminate node of the other models: the film temperature the computed-h loop reads
        ids = np.arange(*_slab_range(mesh, board_slabs[-1]))
        tot, area = _gauss_weights(model, th, ids, "bottom")
        mean, den = _to_cells(_cell_shares(plan, mesh.elem_quad[ids], nx, ny, W, H), tot, area, nx, ny)
        out.extras["bottom_face_mean"] = float(np.nanmean(np.where(active, amb + _fill_empty(mean, den > 0, active), np.nan)))
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


# ----------------------------------------------------------------------------------------------------------------------------------------
# Time: operators, time grid, marching, power step and step responses


## Implicit-Euler or Crank-Nicolson steps behind the first output frame of the logarithmic grid (the first stage is walked in steps of dt0 / FIRST_STAGE_SPLIT, DESIGN.md 14.1)
FIRST_STAGE_SPLIT = 4


def _grid_shape(problem, cell_mm):
    """!
    @brief Cells of the run grid, as the steady FEM and the FVM count them.
    @param problem A Problem.
    @param cell_mm Plan cell in mm.
    @return Tuple (nx, ny, dx in m, dy in m).
    """
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    return nx, ny, b.width / nx, b.height / ny


def column_operator(problem, mesh, nx, ny):
    """!
    @brief The column read-out as a sparse operator: `Rcol @ T_used` is the volume mean of the field over the copper slabs of every layer in every cell of the run grid.
    @details Exactly the linear map of `solve_steady` (`_gauss_weights`, `_cell_shares`, `_to_cells`, `_fill_empty`): the integral of the trilinear field over every element is a
             fixed combination of its eight nodal values, the elements are shared between cells by the overlap of their plan quads, the mean divides by the measure of the cell, and a
             board cell with no element takes the row of the nearest cell that has one. Cells off the outline and layers without copper have a zero row (the ambient, a rise of 0).
             Made once, applied once per output frame: no Python loop per frame.
    @param problem A Problem.
    @param mesh femmesh.FemMesh.
    @param nx Cells along x, count.
    @param ny Cells along y, count.
    @return Tuple (Rcol csr (L ny nx, n_used), active bool (ny, nx), cover (ny, nx) share of every cell that is board).
    """
    b = problem.board
    L = b.layers
    W, H = b.width, b.height
    dx, dy = W / nx, H / ny
    cover = b.cover(nx, ny, dx, dy)
    active = cover > 0
    model = mesh.model
    used = np.zeros(model.nodes.shape[0], bool)
    used[model.elems.ravel()] = True
    remap = np.cumsum(used) - 1
    n_used = int(used.sum())
    G = femcore.G1
    blocks_l = []
    for l in range(L):
        rows = sp.csr_matrix((ny * nx, n_used))
        ids = np.concatenate([np.arange(*_slab_range(mesh, s)) for s in mesh.copper_slabs[l]]) if mesh.copper_slabs[l] else np.zeros(0, np.int64)
        if ids.size:
            conn = model.elems[ids]
            X = model.nodes[conn]
            gint = np.zeros((ids.size, 8))                         # integral of every shape function over the element: the weights of the nodal values
            meas = np.zeros(ids.size)
            for gx in (-G, G):
                for gy in (-G, G):
                    for gz in (-G, G):
                        n, dn = femcore.shape(gx, gy, gz)
                        det = np.abs(femcore.det_inv3(femcore.jacobian(X, dn), False)[0])
                        gint += det[:, None] * n[None, :]
                        meas += det
            shares = _cell_shares(mesh.plan, mesh.elem_quad[ids], nx, ny, W, H)
            den = np.zeros((ny, nx))
            for sel, cx, cy, w in shares:
                np.add.at(den, (cy, cx), w * meas[sel])
            r_l, c_l, v_l = [], [], []
            for sel, cx, cy, w in shares:
                cell = cy * nx + cx
                r_l.append(np.repeat(cell, 8))
                c_l.append(remap[conn[sel]].ravel())
                v_l.append((w[:, None] * gint[sel] / den.ravel()[cell][:, None]).ravel())
            raw = sp.csr_matrix((np.concatenate(v_l), (np.concatenate(r_l), np.concatenate(c_l))), shape=(ny * nx, n_used))
            have = den > 0
            # a board cell with no element takes the nearest cell that has one (`_fill_empty`); a cell off the board has a zero row (the ambient)
            idx_r, idx_c = np.arange(ny)[:, None] * np.ones((1, nx), np.int64), np.ones((ny, 1), np.int64) * np.arange(nx)[None, :]
            if (active & ~have).any() and have.any():
                from scipy import ndimage
                idx = ndimage.distance_transform_edt(~have, return_distances=False, return_indices=True)
                idx_r, idx_c = idx[0], idx[1]
            src = np.where(have, np.arange(ny)[:, None] * nx + np.arange(nx)[None, :], idx_r * nx + idx_c)
            keep = np.flatnonzero(active.ravel())
            pick = sp.csr_matrix((np.ones(keep.size), (keep, src.ravel()[keep])), shape=(ny * nx, ny * nx))
            rows = (pick @ raw).tocsr()
        blocks_l.append(rows)
    return sp.vstack(blocks_l).tocsr(), active, cover


def time_grid(t_end, n_out=40, substeps=4, log_times=True, split=FIRST_STAGE_SPLIT):
    """!
    @brief The steps of a power-step run and the frames they produce: the grid of `fvm.transient_from_network` with the first stage walked in finer steps.
    @details The OUTPUT times are the program's (ten stages with the step doubling, `per_stage = ceil(n_out / 10)`, `dt0 = t_end / (per_stage (2^10 - 1))`, every step of the
             nominal grid an output, t = 0 included; or the linear grid with `substeps` steps per frame), so that the Difference view subtracts like for like. Only the first stage
             of the logarithmic grid is walked in `split` steps per frame, so that no output has fewer than `split` steps behind it (DESIGN.md 3 and 14.1: one implicit-Euler step
             of a flux switched on reads -11.4 % at the face, four steps -3.1 %, and the Crank-Nicolson start about -0.2 %).
    @param t_end Final time in s.
    @param n_out Frames excluding t = 0 (the logarithmic grid rounds it up to a multiple of 10).
    @param substeps Implicit steps between two frames (linear mode only).
    @param log_times True for the doubling step.
    @param split Steps per frame of the first stage of the logarithmic grid, count (1 to leave it as the FVM).
    @return Tuple (h steps in s (n_steps,), emit bool (n_steps,) True where the step ends at an output time, times (n_frames,) the output times in s with t = 0).
    """
    if log_times:
        stages = 10
        per_stage = max(int(np.ceil(n_out / stages)), 1)
        dt0 = t_end / (per_stage * (2 ** stages - 1))
        dts = np.concatenate([np.full(per_stage, dt0 * 2.0 ** j) for j in range(stages)])
        step_times = np.concatenate([[0.0], np.cumsum(dts)])
        step_times[-1] = t_end
        hs, emit = [], []
        for k, dt in enumerate(dts):
            m = max(int(split), 1) if k < per_stage else 1
            hs += [dt / m] * m
            emit += [False] * (m - 1) + [True]
        return np.asarray(hs), np.asarray(emit), step_times
    count = max(n_out, 1) * max(substeps, 1)
    dts = np.full(count, t_end / count)
    step_times = np.concatenate([[0.0], np.cumsum(dts)])
    step_times[-1] = t_end
    emit = np.zeros(count, bool)
    emit[max(substeps, 1) - 1::max(substeps, 1)] = True
    return dts, emit, step_times[np.concatenate([[0], np.flatnonzero(emit) + 1])]


def march(stepper, M, A, load, hs, emit, theta, on_frame, start=True, gam=None, cancel=None, progress=None, T0=None):
    """!
    @brief March a constant load from rest (or from `T0`) through the steps `hs`, calling `on_frame(k, T)` at every step that ends at an output time.
    @details With `theta < 1` and `start` the first step is replaced by two implicit-Euler steps of half its size (the Rannacher start: Crank-Nicolson is not L-stable, a stiff
             mode excited by the jump of the load would ring); the half steps are solved with the factor of the first step (`Stepper.euler_half_step`), so the start costs no
             factorisation and the output times do not move. The energy of a single load is accumulated when `gam` is given.
    @param stepper femcore.Stepper (the object that owns the factor).
    @param M Consistent mass matrix (csc), J/K.
    @param A Stiffness plus film matrix (csc), W/K.
    @param load Load vector (n,) in W, or a matrix (n, k) for several unit loads at once (no energy).
    @param hs Step sizes in s (n_steps,).
    @param emit bool (n_steps,): True where the step ends at an output time.
    @param theta 0.5 (Crank-Nicolson) or 1 (implicit Euler).
    @param on_frame Callable (frame index, T) called after every emitting step, frame index from 1 (t = 0 is the caller's).
    @param start True for the Rannacher start.
    @param gam Row sums of the film matrix on the unknowns (n,) (W/K) for the energy balance, or None.
    @param cancel Optional callable, True raises femcore.FemCancelled (the Stepper checks it before every solve too).
    @param progress Optional callback progress(message, fraction), once per output frame.
    @param T0 Start field (None: rest).
    @return Tuple (T the final field, energy dict (in, stored, lost in J) or None).
    @throws femcore.FemCancelled If cancelled.
    """
    T = np.zeros_like(load) if T0 is None else T0.copy()
    e_in = e_lost = 0.0
    frame = 0
    n_frames = int(np.count_nonzero(emit))
    loss = (lambda x: float(gam @ x)) if gam is not None and load.ndim == 1 else None
    for i, h in enumerate(hs):
        if cancel is not None and cancel():
            raise femcore.FemCancelled("the finite-element time stepping was cancelled")
        if i == 0 and start and theta < 1.0:
            stepper.prepare(h, theta)
            for _ in range(2):
                Tn = stepper.euler_half_step(T, h, load)
                if loss:
                    e_lost += 0.5 * h * loss(Tn)
                T = Tn
        else:
            Tn = stepper.step(T, h, theta, load, load)
            if loss:
                e_lost += h * (theta * loss(Tn) + (1.0 - theta) * loss(T))
            T = Tn
        if emit[i]:
            frame += 1
            on_frame(frame, T)
            if progress is not None:
                progress(f"Time step {frame} of {n_frames}", frame / max(n_frames, 1))
    energy = None
    if loss:
        energy = {"lost": e_lost}
    return T, energy


def capacity_inventory(problem, mesh, cell_mm=None):
    """!
    @brief The heat capacity of the FEM by category against the capacity computed from the description, in J/K.
    @details The description is `integral rho c dV` of the layered board (the copper of the zone fill with its laminate, the dielectric gaps, the metal blocks), evaluated on a
             fine grid of the drawn zones, independent of the mesh; the FEM entries are the sums of its elements. What the programs do not count is listed, never tuned: the copper
             of the via barrels (the barrel volume carries the laminate's capacity in the FVM, FDM and FEM), the interface pad (a resistance with no thickness) and the parts (a
             part is a source with no body). A board with imported copper is read from the mesh fill (the same mask), so its copper line is not independent.
    @param problem A Problem.
    @param mesh femmesh.FemMesh of the run.
    @param cell_mm Unused (kept so that a caller can pass its cell); the description uses its own fine grid.
    @return dict: fem (copper, laminate, blocks, pad, total), description (copper, laminate, blocks, total), via_barrel_omitted, parts ("not modelled"), difference (fem total over
            description total minus 1).
    """
    from . import copper as copper_mod
    from .geometry import zone_fill
    b = problem.board
    m = b.materials
    L = b.layers
    n = int(min(max(round(max(b.width, b.height) * 1000.0 / 0.5), 20), 400))
    nx, ny = max(int(round(n * b.width / max(b.width, b.height))), 2), max(int(round(n * b.height / max(b.width, b.height))), 2)
    dx, dy = b.width / nx, b.height / ny
    cover = b.cover(nx, ny, dx, dy)
    cell = dx * dy * cover
    tc = np.asarray(b.copper_thickness, float)
    f = zone_fill(problem.zones, L, nx, ny, dx, dy, samples=4)
    src = copper_mod.CopperSource.of(problem)
    if src is not None:
        # imported copper: the same masks as the mesh read, so this line is not independent of it
        parts = mesh.capacity_parts
        f = np.broadcast_to(np.full((L, 1, 1), parts["copper"] / max(L * m.rho_copper * m.cp_copper * float(tc.mean()) * cell.sum(), 1e-30)), (L, ny, nx))
    area = float(cell.sum())
    rc_cu = m.rho_copper * m.cp_copper
    rc_lam = b.layer_laminate()[1]
    cu_j = float(sum(rc_cu * tc[l] * float((f[l] * cell).sum()) for l in range(L)))
    if L == 1:
        gap_j = (float(b.slab_thicknesses()[0] - tc[0])) * m.rho_fr4 * m.cp_fr4 * area
    else:
        gap_j = float(np.dot(b.gap_thicknesses(), b.gap_properties()[2])) * area
    lam_j = gap_j + float(sum(rc_lam[l] * tc[l] * float(((1.0 - f[l]) * cell).sum()) for l in range(L)))
    blk_j = 0.0
    bcov = b.cover(nx, ny, dx, dy)
    for sk in problem.heatsinks:
        if sk.is_block():
            c = blocks.block_cover(sk.polygon, b.outline if b.has_outline() else None, nx, ny, dx, dy, bcov)
            blk_j += float(sk.rho_cp * sk.thickness * (c * dx * dy).sum())
    desc_total = cu_j + lam_j + blk_j
    parts = mesh.capacity_parts
    return {"fem": {k: parts[k] for k in ("copper", "laminate", "blocks", "pad", "total")},
            "description": {"copper": cu_j, "laminate": lam_j, "blocks": blk_j, "total": desc_total},
            "via_barrel_omitted": parts["via_barrel_omitted"], "parts": "not modelled",
            "difference": parts["total"] / desc_total - 1.0 if desc_total > 0 else 0.0}


def _check_transient(problem, cell_mm, gap_elements, refine, memory_fraction, force_solver, frames_bytes=0.0):
    """!
    @brief The refusals that come before any heavy work of a transient: the memory guard (exact unknown count, the time factor) and the missing pyamg above the direct limit.
    @param problem A Problem.
    @param cell_mm Plan cell in mm.
    @param gap_elements Elements across every dielectric gap, count.
    @param refine Ratio of the cell to the fine element, at least 1.
    @param memory_fraction Share of the physical memory allowed (None: default).
    @param force_solver None, "direct" or "cg".
    @param frames_bytes Bytes of the frames the run will hold, added to the estimate (not multiplied by the time factor).
    @return Unknown count of the mesh.
    @throws memory.MemoryGuardError If the estimate is above the limit.
    @throws femcore.FemUnavailable If the mesh needs the conjugate gradients and pyamg is not installed.
    """
    memory.check(problem, ("fem",), cell_mm, fraction=memory_fraction, transient=True, fem_params=(gap_elements, refine), quiet=True, frames_bytes=frames_bytes)
    unknowns = femmesh.unknowns(problem, cell_mm, gap_elements, refine)[0]
    if unknowns > femcore.FEM_TRANSIENT_DIRECT_MAX and force_solver != "direct" and not femcore.available():
        raise femcore.FemUnavailable(f"the FEM mesh has {unknowns} unknowns, above the {femcore.FEM_TRANSIENT_DIRECT_MAX} that the direct time stepping takes, and the package "
                                     "pyamg is not installed (pip install pyamg): use a coarser cell or install it")
    return unknowns


def _prepare_time(problem, cell_mm, gap_elements, refine, memory_fraction, cancel, force_solver, frames_bytes=0.0):
    """!
    @brief Mesh, matrices, stepper and read-out operator shared by the power step and the step responses.
    @param problem A Problem.
    @param cell_mm Plan cell in mm.
    @param gap_elements Elements across every dielectric gap, count.
    @param refine Ratio of the cell to the fine element, at least 1.
    @param memory_fraction Share of the physical memory allowed (None: default).
    @param cancel Optional cancel callable.
    @param force_solver None, "direct" or "cg".
    @param frames_bytes Bytes of the frames the run will hold (see `_check_transient`).
    @return dict: mesh, asm (the assembled dict), stepper, Rcol, active, cover, nx, ny, gam (on the unknowns), used.
    @throws memory.MemoryGuardError, femcore.FemUnavailable, femcore.FemCancelled, ValueError as `solve_steady`.
    """
    _check_transient(problem, cell_mm, gap_elements, refine, memory_fraction, force_solver, frames_bytes)
    mesh = femmesh.build(problem, cell_mm, gap_elements, refine)
    try:
        asm = mesh.model.assemble(cancel=cancel, capacity=True)
    except (femcore.FemUnavailable, femcore.FemCancelled):
        raise
    nx, ny, _, _ = _grid_shape(problem, cell_mm)
    Rcol, active, cover = column_operator(problem, mesh, nx, ny)
    stepper = femcore.Stepper(asm["A"], asm["M"], direct_max=femcore.FEM_TRANSIENT_DIRECT_MAX, cancel=cancel, force=force_solver)
    return {"mesh": mesh, "asm": asm, "stepper": stepper, "Rcol": Rcol, "active": active, "cover": cover, "nx": nx, "ny": ny, "gam": asm["gam"][asm["used"]]}


def _steady_field(stepper, rhs):
    """!
    @brief Steady field of one or several right-hand sides with the steady matrix of the stepper (the stepper is left prepared for the steady matrix).
    @param stepper femcore.Stepper.
    @param rhs Load (n,) or (n, k) in W.
    @return numpy.ndarray the rise in K.
    """
    stepper.prepare(0.0, 1.0)
    try:
        return stepper.solve(rhs)
    except RuntimeError as exc:
        raise ValueError(f"the finite-element solve did not converge ({exc}); a coarser cell or a smaller refinement gives a smaller system") from exc


def solve_transient(problem, t_end, n_out=40, cell_mm=2.0, substeps=4, theta_scheme=1.0, log_times=True, gap_elements: int = 6, refine: float = 2.0,
                    memory_fraction: Optional[float] = None, cancel: Optional[Callable[[], bool]] = None, progress: Optional[Callable[[str, float], None]] = None,
                    force_solver: Optional[str] = None) -> TransientResult:
    """!
    @brief Transient response of the board to a power step, by finite elements, read out like `fvm.solve_transient` (same output times, column read-out).
    @details The semi-discrete system `M dT/dt + A T = F` (consistent mass, the heaters' powers as the load), the theta step of `femcore.Stepper`, one factor alive (the steps of a
             stage are equal and a stage never comes back). The grid is that of `fvm.transient_from_network`; its first stage is walked in steps of a quarter so that no output has
             fewer than four steps behind it; with `theta_scheme < 1` the first step is opened by two implicit-Euler half steps (Rannacher). The frames are the column read-out (the
             volume mean over the copper slabs of every layer, `column_operator`); the hottest node of the mesh at every frame is `extras["t_max_point"]`.
    @param problem A Problem.
    @param t_end Final time in s.
    @param n_out Output frames excluding t = 0 (the logarithmic grid rounds it up to a multiple of 10).
    @param cell_mm Plan cell in mm (the coarse element and the grid of the frames).
    @param substeps Implicit steps between two frames (linear mode only).
    @param theta_scheme 1.0 implicit Euler (as the FVM default), 0.5 Crank-Nicolson with the Rannacher start.
    @param log_times True for the doubling step in ten stages.
    @param gap_elements Elements across every dielectric gap, count (2 to 24).
    @param refine Ratio of the cell to the fine element near the heaters and via patches (1 to 4).
    @param memory_fraction Share of the physical memory the run may use (None: default).
    @param cancel Optional callable checked at every step; True raises femcore.FemCancelled.
    @param progress Optional callback progress(message, fraction), once per output frame.
    @param force_solver None (by size), "direct" or "cg" (tests and studies).
    @return TransientResult (times, t_max, t_mean, frames in degC, steady_t_max; `extras` holds t_max_point, energy_residual, solver, steps, factorisations, iterations,
            peak_gb, capacity; `arrays` is empty: `T_surface` is reserved).
    @throws memory.MemoryGuardError If the estimated memory is above the limit (before anything is built).
    @throws femcore.FemUnavailable If the mesh needs the conjugate gradients and pyamg is not installed.
    @throws femcore.FemCancelled If `cancel` returned True.
    @throws ValueError With the reason when no mesh can be built, or the solve fails.
    """
    gx, gy, _, _ = _grid_shape(problem, cell_mm)
    frames_bytes = 8.0 * (max(n_out, 1) + 11) * problem.board.layers * gx * gy        # the frames of the run, held beside the factor (the guard adds them, no time factor)
    ctx = _prepare_time(problem, cell_mm, gap_elements, refine, memory_fraction, cancel, force_solver, frames_bytes)
    mesh, asm, stepper, Rcol = ctx["mesh"], ctx["asm"], ctx["stepper"], ctx["Rcol"]
    L, ny, nx = problem.board.layers, ctx["ny"], ctx["nx"]
    amb = problem.board.ambient
    inside, cover = ctx["active"], ctx["cover"]
    load = asm["rhs"]
    q_in = asm["q_gen"] + asm["q_flux"]
    hs, emit, times = time_grid(t_end, n_out, substeps, log_times)
    n_frames = times.size
    frames = np.zeros((n_frames, L, ny, nx))
    tmax_point = np.zeros(n_frames)
    steady = (Rcol @ _steady_field(stepper, load)).reshape(L, ny, nx)
    steady_t_max = float(steady[:, inside].max() + amb)
    frames[0] = amb
    tmax_point[0] = amb

    def on_frame(k, T):
        """!
        @brief Store the column read-out and the hottest node of one output frame.
        @param k Frame index from 1.
        @param T Field on the unknowns, K of rise.
        @return None.
        """
        frames[k] = (Rcol @ T).reshape(L, ny, nx) + amb
        tmax_point[k] = amb + float(T.max())

    try:
        T_end, energy = march(stepper, asm["M"], asm["A"], load, hs, emit, theta_scheme, on_frame, start=True, gam=ctx["gam"], cancel=cancel, progress=progress)
        e_stored = float(asm["m_lump"] @ T_end)
        e_in = q_in * float(times[-1])
        residual = (e_stored + energy["lost"] - e_in) / e_in if e_in else 0.0
    except RuntimeError as exc:
        if isinstance(exc, (femcore.FemCancelled, femcore.FemUnavailable)):
            raise
        raise ValueError(f"the finite-element time stepping failed ({exc})") from exc
    stats = {"factorisations": stepper.factorisations, "iterations": stepper.total_iterations, "solves": stepper.solves, "solver": stepper.solver}
    stepper.close()
    t_max = frames[:, :, inside].reshape(n_frames, -1).max(axis=1)
    t_mean = (frames * cover).sum(axis=(1, 2, 3)) / (L * cover.sum())
    inv = capacity_inventory(problem, mesh)
    warnings = list(mesh.warnings)
    predicted = memory.fem_transient_seconds(asm["rhs"].size, hs.size)
    if predicted > memory.SLOW_SECONDS:
        # an animation is not refused for its time (a profile run is, `profiles.run_fem`): the verdict is a note that says how long the stepping alone was expected to take
        warnings.append(f"the finite-element time simulation of this mesh ({asm['rhs'].size} unknowns, {hs.size} steps) was predicted to take about {predicted / 60.0:.0f} minutes of stepping")
    if abs(inv["difference"]) > CAPACITY_TOLERANCE:
        warnings.append(f"the heat capacity of the FEM mesh ({inv['fem']['total']:.4g} J/K) differs by {inv['difference'] * 100:+.1f} % from the capacity computed from the "
                        "description: check the stack-up and the copper")
    return TransientResult(times=times, t_max=t_max, t_mean=t_mean, frames=frames, steady_t_max=steady_t_max, ambient=amb, grid="cells", warnings=warnings,
                           extras={"t_max_point": tmax_point, "energy_residual": float(residual), "steps": int(hs.size), "unknowns": float(asm["rhs"].size),
                                   "peak_gb": femcore._peak_gb(), "capacity": inv, **stats})


## Largest difference of the heat capacity of the mesh from the capacity of the description that is not reported as a warning (maintainer, DESIGN.md 14.7)
CAPACITY_TOLERANCE = 0.01


def heater_loads(mesh):
    """!
    @brief The unit-power load vector of every heater of a mesh, on the unknowns.
    @param mesh femmesh.FemMesh.
    @return numpy.ndarray (n_used, n_heaters) in W per W; `F @ powers` equals the steady load of the model at those powers.
    """
    cols = []
    for hq, hf in zip(mesh.heater_q, mesh.heater_flux):
        if hf is not None:
            cols.append(mesh.model.load_vector(face_nodes=hf[0], flux_unit=hf[1]))
        else:
            cols.append(mesh.model.load_vector(elem_ids=hq[0], q_unit=hq[1]))
    n = int(np.unique(mesh.model.elems).size)
    return np.column_stack(cols) if cols else np.zeros((n, 0))


def step_responses(problem, cell_mm=2.0, t_end=None, ratio=3.0, per_stage=4, stages=18, theta_scheme=0.5, gap_elements: int = 6, refine: float = 2.0,
                   memory_fraction: Optional[float] = None, cancel: Optional[Callable[[], bool]] = None, force_solver: Optional[str] = None):
    """!
    @brief Response of every heater to a unit power step of that heater, by finite elements, in the form of `fvm.step_responses` (the hottest column cell for each heater).
    @details The heaters are several right-hand sides of the same matrices (one factor per stage, the stage step grows by `ratio` after `per_stage` frames). The first stage is
             walked in quarter steps and, with `theta_scheme < 1`, opened by the Rannacher half steps, so that the first frame has four steps behind it.
    @param problem A Problem with at least one heater.
    @param cell_mm Plan cell in mm.
    @param t_end Last time in s (None: ten board time constants, the capacity over the conductance to the ambient of the mesh).
    @param ratio Growth factor of the step between stages.
    @param per_stage Frames per stage, count.
    @param stages Number of stages.
    @param theta_scheme 0.5 (Crank-Nicolson with the start) or 1.0 (implicit Euler).
    @param gap_elements Elements across every dielectric gap, count.
    @param refine Ratio of the cell to the fine element, at least 1.
    @param memory_fraction Share of the physical memory the run may use (None: default).
    @param cancel Optional cancel callable.
    @param force_solver None, "direct" or "cg".
    @return Tuple (times (nt,) in s without t = 0, z (n_heaters, nt) in K/W, rth (n_heaters,) in K/W steady, both the hottest column cell for each heater).
    @throws ValueError If the problem has no heater, or as `solve_transient`.
    """
    if not problem.heaters:
        raise ValueError("the problem has no heater")
    ctx = _prepare_time(problem, cell_mm, gap_elements, refine, memory_fraction, cancel, force_solver)
    mesh, asm, stepper, Rcol = ctx["mesh"], ctx["asm"], ctx["stepper"], ctx["Rcol"]
    inside = ctx["active"].ravel()
    L = problem.board.layers
    keep_rows = np.tile(inside, L)
    F = heater_loads(mesh)
    rth = (Rcol @ _steady_field(stepper, F))[keep_rows].max(axis=0)
    if t_end is None:
        t_end = 10.0 * float(asm["capacity_total"] / ctx["gam"].sum())
    geometric = per_stage * (ratio ** stages - 1.0) / (ratio - 1.0)
    dt0 = t_end / geometric
    hs, emit, times = [], [], []
    t = 0.0
    for j in range(stages):
        dt = dt0 * ratio ** j
        for i in range(per_stage):
            m = FIRST_STAGE_SPLIT if j == 0 else 1
            hs += [dt / m] * m
            emit += [False] * (m - 1) + [True]
            t += dt
            times.append(t)
    z = []

    def on_frame(k, X):
        """!
        @brief Record the hottest column cell of every heater at one output time.
        @param k Frame index from 1 (unused).
        @param X Fields (n, n_heaters), K/W.
        @return None.
        """
        z.append((Rcol @ X)[keep_rows].max(axis=0))

    try:
        march(stepper, asm["M"], asm["A"], F, np.asarray(hs), np.asarray(emit), theta_scheme, on_frame, start=True, cancel=cancel)
    except RuntimeError as exc:
        if isinstance(exc, (femcore.FemCancelled, femcore.FemUnavailable)):
            raise
        raise ValueError(f"the finite-element time stepping failed ({exc})") from exc
    stepper.close()
    return np.asarray(times), np.asarray(z).T, rth
