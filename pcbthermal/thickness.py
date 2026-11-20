#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file thickness.py
@brief The surface read-out of the outer copper faces: the temperature of a face from the node (the column mean) and the heat fluxes that enter through the faces. Always computed, for every steady FVM/FDM result.
@details The layered models keep ONE temperature per copper layer, the mean through the thickness (the COLUMN read-out, docs/theory.md 1.2). Where a flux crosses a layer of
         thickness t and conductivity k the face is hotter or cooler than that mean. A layer whose temperature varies slowly in the plane satisfies k t laplace(T_m) = -(q_top + q_bot)
         (q_top and q_bot the heat flux ENTERING through the two faces, z downwards), so the profile through the thickness is a parabola with T_z(0) = -q_top / k and T_z(t) = q_bot / k:
             T_top - T_m = t (2 q_top - q_bot) / (6 k),    T_bottom - T_m = t (2 q_bot - q_top) / (6 k).
         A column fed at the top and cooled at the bottom (q_bot = -q_top) gives the familiar q t / (2 k); heat that spreads sideways (q_bot = 0) gives q t / (3 k). The parabola is
         within 7 % of an independent 3D solution up to t/a = 0.5 (a the side of the source) and an UPPER estimate beyond (research/through-thickness-readout 4.2, validation 55.6).
         For a rectangular source b x c the overshoot depends on the NARROW side b only (releases/2.9.0/surface-flag: 2 x 10, 2 x 20 and 2 x 40 mm on 2 mm copper all read 1.15 times
         the true term, 10 x 10 and 10 x 20 mm both 0.99), so `source_width` takes the smallest of the minimum width of the hull, the narrowest local width of the polygon (an L, a U) and the equivalent side sqrt(A), never the area alone.
         The surface is ALWAYS a second number beside the column, never a mode: no option, no project key (decision of the maintainer, releases/2.8.0/fem-model/SURFACE_DECISIONS.md).
         `attach` is called by the FVM and the FDM for EVERY steady result, with NO thickness or size threshold (the former 105 um limit and the 'worth showing' test are gone:
         the cost is 0 to 3 ms and no number of any model sees the arrays); the result holds (absolute temperatures in degC, NaN off the board and on a face that is not computed)
             arrays["T_surface"] (2, ny, nx)       top face of layer 1 and bottom face of the last layer, the HOTTEST value in the cell;
             arrays["T_surface_mean"] (2, ny, nx)  the same with the area mean of a partly filled cell;
             arrays["T_surface_flag"] (2, ny, nx)  bool, true under a part with t/a above UPPER_RATIO, a = source_width (the value is an upper estimate);
             extras["t_max_surface_top"], ["t_max_surface_bottom"], ["surface_excess_k"].
         The face fluxes: the heat of a part and the films on the outer face, the sum of the conductances to the other layers (laminate, inner copper, via couplings) on the inner face,
         the heat into a block on its face; the sideways flow is not a face flux. Partly filled cells: the copper term c uses the fluxes of the cell; the mean is f c plus the
         laminate face term of laminate.face_terms (already weighted by the bare share), the PEAK the larger of c and the laminate peak, never their sum (research README 7.1).
         Nothing here is read by the part rows' t_max, Tj, the margin, the power limit, the top-path split, the power coefficient, the Power Calculator or the calibration: they stay on the
         column (tests/test_thickness.py holds them bit-identical with and without the arrays).
         VALIDITY PER LAYER TYPE. Outer copper (top of layer 1, bottom of the last layer; both faces of a one-layer board): the formula applies at every thickness; on 35 um copper it is
         correct and tiny (0.4 to 5.6 mK on the harness boards). Inner copper: no outer face and no flux to define one (its faces are interfaces with the laminate, where the temperature is
         continuous), so the surface IS the column ('equal'); no array is made for it. Laminate: resolved through its thickness by the sub-gap nodes, so its face is a node (nothing to
         estimate). Metal blocks: ONE node through the block's thickness (blocks.py), so the block face is NOT resolved and has no surface read-out (the thick-plate warning
         gives its bound); the heat into a block is a face flux of the copper layer it sits on.
         CONTRACT FOR ANOTHER MODEL (the FEM of feature/fem-model will fill these): a SteadyResult with T (layers, ny, nx) in degC may carry arrays["T_surface"],
         ["T_surface_mean"] (float, shape (2, ny, nx), degC, face 0 the top of layer 1 and face 1 the bottom of the last layer, NaN off the board and on a face not computed),
         ["T_surface_flag"] (bool, (2, ny, nx), True where the value is an upper estimate; a computed face has none) and extras["t_max_surface_top"], ["t_max_surface_bottom"]
         (float degC, the nanmax of each finite face, absent for a face not computed) and ["surface_excess_k"] (float K). Every reader (analysis.surface_stats, api.surface_report_lines,
         plots.draw_surface, the Layer box, the part table, Simulation.save) needs only these names and shapes, so a model that fills them gets the whole display.
         THE THIN-COPPER TRAP: on a patterned board the surface under a source over ABSENT copper includes the rise across the bare laminate (the face term of laminate.face_terms):
         the surface can be 1 to 4 K above the node maximum on 35 um copper although the copper term is milli-kelvin. The part rows already include that term in their 'column' maximum,
         so there surface minus column is the copper term only. Never gate anything on the board-level difference (surface_excess_k).
         OTHER MODELS (feature/surface-readout-models; the same arrays, every reader shows them): `attach_field` gives the ANALYTIC an estimate (rule F: the parabola fed with the fluxes of its own field and the
         uniform conductances of its sheet; vias, blocks and heatsinks are not in them and a part over absent copper has no bare-laminate term), `attach_solid` gives the 3D SOLID a value computed from its copper
         slabs above 105 um (outer slab plus the half slab above it) and an estimate from its own links on one slab; `surface_kind` and `surface_how` word which one a result holds, `lumped_surface_note` is the
         text of the LUMPED, which has no face flux and so no surface: only the through-thickness term as a measured upper value, not a guarantee.
         NOT modelled: the Lumped (a text only), the face of a metal block, the transient and the profiles (steady state only).
"""

import numpy as np

from . import copper
from .geometry import coverage_fraction, points_in_polygon, polygon_area

UPPER_RATIO = 0.5                          # t / a above this: the parabola overshoots, the surface is an upper estimate (research README 4.2)


def offsets(t, k, q_top, q_bot):
    """!
    @brief Surface-minus-column-mean temperature of the two faces of a layer (parabolic profile through the thickness).
    @param t Layer thickness in m.
    @param k Through-thickness conductivity of the layer in W/mK.
    @param q_top Net heat flux entering through the top face in W/m2 (positive in; scalar or array).
    @param q_bot Net heat flux entering through the bottom face in W/m2 (a face that loses heat has a negative value).
    @return Tuple (d_top, d_bottom) in K, shaped like the fluxes.
    """
    q_top, q_bot = np.asarray(q_top, dtype=float), np.asarray(q_bot, dtype=float)
    return t * (2.0 * q_top - q_bot) / (6.0 * k), t * (2.0 * q_bot - q_top) / (6.0 * k)


def column_bound(t, k, q):
    """!
    @brief The bound q t / (2 k) of the thick-plate warning (a column fed at the top and cooled at the bottom).
    @param t Layer thickness in m.
    @param k Conductivity in W/mK.
    @param q Flux through the layer in W/m2.
    @return Temperature difference in K.
    """
    return np.abs(q) * t / (2.0 * k)


def surface_kind(res, face=0):
    """!
    @brief How the surface of a result was obtained: "resolved" (the finite elements), "computed" (the 3D solid with its copper cut into slabs) or "estimate" (a parabola, rules F and S, the FVM and FDM).
    @param res SteadyResult that holds arrays["T_surface"].
    @param face 0 for the top face of layer 1, 1 for the bottom face of the last layer.
    @return str, one of "resolved", "computed", "estimate".
    """
    if res.model == "fem":
        return "resolved"
    if res.model == "solid3d" and res.extras.get("surface_copper_slabs_top" if face == 0 else "surface_copper_slabs_bottom", 1.0) >= 2.0:
        return "computed"
    return "estimate"


def surface_how(res, flagged=False, face=0):
    """!
    @brief The words that say how a surface number was made, for the report, the Layer box and the tables (every number names its read-out).
    @param res SteadyResult that holds arrays["T_surface"].
    @param flagged True when the face is flagged as an upper estimate (t/a above UPPER_RATIO under a part).
    @param face 0 for the top face of layer 1, 1 for the bottom face of the last layer.
    @return str, without brackets: "resolved by the finite elements", "computed from the copper slabs of the 3D solid ...", "estimate from the Analytic model's own field ...", or "estimate"
            with ", upper side: a source is narrow against the plate (t/a above 0.5, a the narrow side)" when flagged.
    """
    kind = surface_kind(res, face)
    if kind == "resolved":
        return "resolved by the finite elements"
    if kind == "computed":
        return "computed from the copper slabs of the 3D solid (the half slab above the outer one), not a parabola"
    upper = ", upper side: a source is narrow against the plate (t/a above 0.5, a the narrow side)" if flagged else ""
    if res.model == "analytic":
        bare = "; a part over absent copper has no bare-laminate term" if res.extras.get("surface_part_over_bare_laminate") else ""
        return ("estimate from this model's own field and its uniform conductances (vias, blocks and heatsinks are not in the heat fluxes" + bare + ")" + upper)
    if res.model == "solid3d":
        return "estimate from the links of the 3D solid (one copper slab)" + upper
    return "estimate" + upper


def lumped_surface_note(bound_k, layer):
    """!
    @brief The text of the Lumped model for a part on an outer face of a copper layer: no surface temperature, only the through-thickness term as a measured upper value.
    @details The Lumped has no heat flux through the face of the copper and no per-cell field of its own, so it gives NO surface temperature (an absolute upper bound measured 8 of 22 parts
             too low against the FEM, up to 50 K, because of its column: outlines and copper windows; research/surface-readout-models 4.3 and its review). The term it can quote is the
             through-thickness term q t / (2 k) of the part's footprint flux: above the true term on 8 of 8 plates and case 2, above the FVM term on 23 of 23 harness parts and the FEM
             term on 21 of 22 (not over absent copper). It was MEASURED, not proved, and it is a bound on the term (surface minus column), never on the temperature.
    @param bound_k The term q'' t / (2 k) in K (`column_bound`).
    @param layer 1-based layer of the part.
    @return str.
    """
    return (f"The Lumped model has no heat flux through the face of the copper, so it gives no surface temperature. The surface of this part (layer {layer}) is above the column value by at most "
            f"about {bound_k:.3g} K (q'' t / 2k, the through-thickness term of the copper only: a measured upper value on plates and boards, not a guarantee). It can fail for heat that "
            "arrives from a hotter neighbouring part, for a part over absent copper (the bare laminate adds its own term) and for thick plates, and it does not contain this model's own error. "
            "Use the FVM, the FDM, the FEM or the 3D solid for the surface.")


def _couplings_out(net, theta, layer):
    """!
    @brief Heat leaving the nodes of one layer through its couplings to nodes of OTHER layers, split into the blocks (by face) and everything else.
    @details Reads the off-diagonal entries of the conductance matrix K of the network, so that the laminate sub-nodes, the inner copper, the contact of a block and the
             couplings of the vias are all counted, whatever their arrangement. The couplings to nodes of the same layer are the sideways flow and are left out.
    @param net A fvm.Network or fdm.Network with the matrix K built.
    @param theta Rise of all node layers, shape (layers, ny, nx), in kelvin.
    @param layer Index of the node layer.
    @return Tuple (inner, block_top, block_bottom) of arrays (ny, nx) in W (positive: heat leaves the node).
    """
    ny, nx = theta.shape[1:]
    n = ny * nx
    sub = net.K.tocsr()[layer * n:(layer + 1) * n].tocoo()
    th = theta.ravel()
    col_layer = sub.col // n
    off = col_layer != layer
    r, c, g = sub.row[off], sub.col[off], -sub.data[off]
    heat = g * (th[layer * n + r] - th[c])
    block_face = {bi["layer"]: bi["face"] for bi in net.block_info}
    is_block = np.isin(col_layer[off], list(block_face)) if block_face else np.zeros(len(r), dtype=bool)
    inner = np.bincount(r[~is_block], weights=heat[~is_block], minlength=n).reshape(ny, nx)
    out_block = [np.zeros(n), np.zeros(n)]
    for lay, face in block_face.items():
        sel = is_block & (col_layer[off] == lay)
        out_block[face] += np.bincount(r[sel], weights=heat[sel], minlength=n)
    return inner, out_block[0].reshape(ny, nx), out_block[1].reshape(ny, nx)


def source_width(polygon):
    """!
    @brief The length a of the thin-sheet limit t / a of a source: its narrowest width, never more than the equivalent side sqrt(A).
    @details For a rectangle b x c the parabola of `offsets` overshoots the true surface term by an amount that is set by b once c is about 3 b or longer (measured against the
             independent 3D solver and an exact cosine series, releases/2.9.0/surface-flag: the ratio is 1.15 for 2 x 10, 2 x 20 and 2 x 40 mm on a 2 mm plate, 1.28 for the
             2 x 2 square), so sqrt(A) misses the elongated ones. Three lengths, the smallest wins: the minimum width of the convex hull (the smallest distance between two
             parallel lines that enclose the part; b for a rectangle of any orientation), the narrowest local width of a concave polygon (`_local_width`: the arm of an L or a U,
             which the hull bridges: an L of 2 mm arms on 2 mm copper overshoots 1.19 times with a hull 8.7 mm wide), and sqrt(A), so that a shape whose width is larger than its
             equivalent side (a disc: d against 0.886 d) is flagged exactly as before; a square gives its own side either way. Every choice errs small, so the flag comes early.
    @param polygon Vertices (n, 2) in m.
    @return Length in m (0 for a degenerate polygon).
    """
    pts = np.unique(np.round(np.asarray(polygon, dtype=float), 12), axis=0)
    root_a = float(np.sqrt(max(polygon_area(polygon), 0.0)))
    if len(pts) < 3 or root_a <= 0.0:
        return root_a
    # Convex hull by the monotone chain: the minimum width of a set is reached perpendicular to an edge of its hull
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]
    def half(seq):
        out = []
        for q in seq:
            while len(out) >= 2 and (out[-1][0] - out[-2][0]) * (q[1] - out[-2][1]) - (out[-1][1] - out[-2][1]) * (q[0] - out[-2][0]) <= 0.0:
                out.pop()
            out.append(q)
        return out[:-1]
    hull = np.array(half(pts) + half(pts[::-1]))
    best = np.inf
    for i in range(len(hull)):
        e = hull[(i + 1) % len(hull)] - hull[i]
        n = np.hypot(*e)
        if n == 0.0:
            continue
        normal = np.array([-e[1], e[0]]) / n
        proj = hull @ normal
        best = min(best, float(proj.max() - proj.min()))
    hull_width = best if np.isfinite(best) else root_a
    # The hull bridges the notch of a concave part (an L or a U of 2 mm arms has a hull 9 to 11 mm wide), so the narrowest arm is found on the polygon itself;
    # a convex part is its own hull, whose minimum width is the right length (the chords of a triangle can be shorter), so it keeps the hull width
    if len(hull) == len(pts) or _is_convex(np.asarray(polygon, dtype=float)):
        return min(root_a, hull_width)
    return min(root_a, hull_width, _local_width(np.asarray(polygon, dtype=float)))


def _is_convex(polygon):
    """!
    @brief True when a simple polygon is convex (every turn has the same sense; collinear vertices allowed).
    @param polygon Vertices (n, 2) in m.
    @return bool.
    """
    e = np.roll(polygon, -1, axis=0) - polygon
    cross = e[:, 0] * np.roll(e[:, 1], -1) - e[:, 1] * np.roll(e[:, 0], -1)
    scale = float(np.max(np.abs(cross))) if len(cross) else 0.0
    cross = cross[np.abs(cross) > 1e-9 * scale]
    return bool(np.all(cross > 0.0) or np.all(cross < 0.0))


def _local_width(polygon):
    """!
    @brief The narrowest local width of a simple polygon: the shortest chord cast inwards, normal to an edge, from points of its edges.
    @details From three points of every edge (a quarter, a half and three quarters of its length) a ray is cast along the inward normal to the first edge it meets; the
             shortest such chord is the width of the narrowest arm (2 mm for an L or a U of 2 mm arms, b for a rectangle b x c, at most the minimum width for a convex
             polygon). A chord whose middle point lies outside the polygon (a ray that leaves through a zero-width slit of a keyhole outline) and hits closer than a
             millionth of the size are ignored, so a degenerate outline never gives a width of zero. Erring small is the safe side: a thinner arm flags the part earlier.
    @param polygon Vertices (n, 2) in m (either orientation, closing vertex optional).
    @return Length in m (inf when no chord was found).
    """
    p = polygon
    if len(p) > 1 and np.allclose(p[0], p[-1]):
        p = p[:-1]
    if len(p) < 3:
        return np.inf
    a_start, a_end = p, np.roll(p, -1, axis=0)
    edge = a_end - a_start
    length = np.hypot(edge[:, 0], edge[:, 1])
    keep = length > 0.0
    a_start, edge, length = a_start[keep], edge[keep], length[keep]
    # The inward normal: to the left of the edge for a counter-clockwise outline, to the right for a clockwise one
    signed = 0.5 * float(np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]))
    sense = 1.0 if signed > 0.0 else -1.0
    normal = sense * np.stack([-edge[:, 1], edge[:, 0]], axis=1) / length[:, None]
    tol = 1e-6 * float(np.max(np.ptp(p, axis=0)))
    best = np.inf
    chunk = 256                                                          # rays per block: a Gerber outline of thousands of vertices stays at a few MB
    # Three points per edge on a drawn outline; the middle one only on a long (imported) outline, whose edges are short anyway
    for frac in ((0.25, 0.5, 0.75) if len(edge) <= 256 else (0.5,)):
        for lo in range(0, len(edge), chunk):
            sl = slice(lo, lo + chunk)
            origin, nrm = a_start[sl] + frac * edge[sl], normal[sl]           # (r, 2) ray origins and directions
            # Ray origin + s n against every edge start + u e (0 <= u <= 1): solve the 2 x 2 system for all pairs at once
            d = origin[:, None, :] - a_start[None, :, :]                     # (r, m, 2)
            den = nrm[:, None, 0] * edge[None, :, 1] - nrm[:, None, 1] * edge[None, :, 0]
            with np.errstate(divide="ignore", invalid="ignore"):
                s = (edge[None, :, 0] * d[..., 1] - edge[None, :, 1] * d[..., 0]) / den
                u = (nrm[:, None, 0] * d[..., 1] - nrm[:, None, 1] * d[..., 0]) / den
            # A ray parallel to an edge has den 0 and never hits it; its own edge gives s = 0 and is cut by the tolerance
            hit = (np.abs(den) > 0.0) & (s > tol) & (u >= 0.0) & (u <= 1.0)
            s = np.where(hit, s, np.inf).min(axis=1)                          # the first edge each ray meets
            ok = np.isfinite(s)
            if not ok.any():
                continue
            mid = origin[ok] + 0.5 * s[ok, None] * nrm[ok]
            inside = points_in_polygon(mid[:, 0], mid[:, 1], p)               # the chord must run through the part, not across a gap
            if inside.any():
                best = min(best, float(s[ok][inside].min()))
    return best


def _upper_flags(problem, res, faces):
    """!
    @brief Cells under a part whose narrow side is wide against the plate it sits on the wrong way round: t / a above UPPER_RATIO, a = source_width, where the parabola is an upper estimate.
    @param problem The Problem.
    @param res SteadyResult (gives the sample positions).
    @param faces List [(face index 0 or 1, layer index)] of the outer faces that were computed.
    @return Boolean array (2, ny, nx).
    """
    ny, nx = res.T.shape[1:]
    flag = np.zeros((2, ny, nx), dtype=bool)
    xs, ys = res.coords()
    X, Y = np.meshgrid(xs, ys)
    b = problem.board
    for face, layer in faces:
        t = float(b.copper_thickness[layer])
        for h in problem.heaters:
            on_face = (h.layer == layer) if b.layers > 1 else True
            a = source_width(h.polygon)   # the narrow side, not sqrt(A): an elongated part overshoots through its narrow side
            if on_face and a > 0 and t / a > UPPER_RATIO:
                flag[face] |= points_in_polygon(X.ravel(), Y.ravel(), h.polygon).reshape(X.shape)
    return flag


def _finish(res, problem, d, fill, faces, area):
    """!
    @brief Turn the copper terms of the outer faces into the arrays of the result (the FVM and the FDM; written so that a model without partial cells can pass fill None).
    @param res SteadyResult.
    @param problem The Problem.
    @param d Dict {face: copper term in K per cell}, faces 0 (top of layer 1) and 1 (bottom of the last layer).
    @param fill Copper fill of the layers (layers, ny, nx), or None for a uniform sheet (no partial cells).
    @param faces List of (face, layer) to fill.
    @param area Board area of every cell (ny, nx) in m2; cells with no board get no offset.
    """
    ny, nx = res.T.shape[1:]
    surf, surf_mean = np.zeros((2, ny, nx)), np.zeros((2, ny, nx))
    on = area > 0
    for face, layer in faces:
        c = np.where(on, d[face], 0.0)
        T = res.T[layer]
        if fill is None:
            peak, mean = c, c
        else:
            f = fill[layer]
            fp = res.arrays["face_peak"][layer] if "face_peak" in res.arrays else np.zeros_like(c)
            fm = res.arrays["face_mean"][layer] if "face_mean" in res.arrays else np.zeros_like(c)
            c_cu = np.where(f > 0, c, 0.0)
            # The hottest point of a partly filled cell is over the bare laminate: the larger of the two terms; where the laminate term is absent the copper term is the peak
            # (and a cell without copper and without a laminate term has no offset: the copper term of an empty cell has no meaning, as in the mean f c)
            peak = np.where(fp > 0, np.maximum(c_cu, fp), c_cu)
            mean = f * c + fm
        surf[face], surf_mean[face] = T + peak, T + mean
    for face in (0, 1):                                                       # A face that is not computed, or off the board, has no surface value
        if face not in {f for f, _ in faces}:
            surf[face], surf_mean[face] = np.nan, np.nan
        surf[face][~on], surf_mean[face][~on] = np.nan, np.nan
    res.arrays["T_surface"] = surf
    res.arrays["T_surface_mean"] = surf_mean
    res.arrays["T_surface_flag"] = _upper_flags(problem, res, faces)
    exc = [float(np.nanmax(np.abs(surf[f] - res.T[ly]))) for f, ly in faces]
    res.extras["surface_excess_k"] = max(exc)
    # Extras are plain numbers that go to JSON: a face that was not computed has no entry
    for face, key in ((0, "t_max_surface_top"), (1, "t_max_surface_bottom")):
        if np.isfinite(surf[face]).any():
            res.extras[key] = float(np.nanmax(surf[face]))


def source_flux(problem, ny, nx, dx, dy):
    """!
    @brief Power density of the parts on every layer, spread over the cells of their footprint (a model without a face flux of its own: the Analytic).
    @param problem The Problem.
    @param ny Cells along y.
    @param nx Cells along x.
    @param dx Cell width in m.
    @param dy Cell height in m.
    @return Array (layers, ny, nx) in W/m2: the power of each part over its footprint area, on every cell the footprint touches (partly covered cells too: the same cells as the part rows).
    """
    q = np.zeros((problem.board.layers, ny, nx))
    for h in problem.heaters:
        area = polygon_area(h.polygon)
        if area > 0 and h.power > 0:
            q[h.layer] += h.power / area * (coverage_fraction(h.polygon, nx, ny, dx, dy, 4) > 0)
    return q


def attach_field(res, problem, sheet):
    """!
    @brief Add the surface arrays of the outer copper faces to the result of the ANALYTIC model (rule F, "field": an estimate from the model's own field and its uniform conductances).
    @details The Analytic has a temperature per layer and per cell (the column) but no per-cell face flux, so the fluxes of the parabola are read from that field and from the UNIFORM
             conductances of its sheet (`analytic._effective_sheet`: the film of each outer face in series with the half copper, `h_top_eff` and `h_bottom_eff`, and the laminate conductance per
             gap `g_diel`):
                 top face of layer 1:      q_top = q_src - h_top_eff theta_1,       q_bot = -g_diel[0] (theta_1 - theta_2)     (a one-layer board: q_bot = -h_bottom_eff theta_1)
                 bottom face of layer L:   q_top = g_diel[L-2] (theta_{L-1} - theta_L),   q_bot = q_src - h_bottom_eff theta_L
             then `offsets` and the arrays of `_finish`, with no partial cells (fill None: the sheet is uniform). Vias, blocks and heatsinks are NOT in these fluxes (a via carries heat the
             uniform gap conductance does not see) and a part over a copper window has no bare-laminate face term (the column of the Analytic does not hold one either): the surface is
             column + copper term, never better than the column, and it is always an ESTIMATE (the flag is the same t/a test as the FVM's). Measured against the FVM parabola:
             within 0.02 K on the six one-layer plates and case 2, 0.056 K on the via plate; 0.4 to 2.6 mK on the harness boards (research/surface-readout-models 4.1 to 4.4).
             Nothing that exists is changed: only arrays["T_surface"], ["T_surface_mean"], ["T_surface_flag"] and the extras are added, and no reader of a decided number looks at them.
    @param res SteadyResult of the Analytic (T in degC, layers x ny x nx).
    @param problem The Problem that was solved (after the one-layer series laminate).
    @param sheet The dict returned by analytic._effective_sheet for it.
    """
    b = problem.board
    L = b.layers
    ny, nx = res.T.shape[1:]
    th = np.asarray(res.T, dtype=float) - b.ambient
    q = source_flux(problem, ny, nx, res.dx, res.dy)
    t_cu = np.asarray(b.copper_thickness, dtype=float)
    k = b.materials.k_copper
    g = np.asarray(sheet["g_diel"], dtype=float)
    ht, hb = sheet["h_top_eff"], sheet["h_bottom_eff"]
    if L == 1:
        q_top, q_bot = q[0] - ht * th[0], -hb * th[0]
        d_top, d_bot = offsets(t_cu[0], k, q_top, q_bot)
        faces = [(0, 0), (1, 0)]
    else:
        d_top, _ = offsets(t_cu[0], k, q[0] - ht * th[0], -g[0] * (th[0] - th[1]))
        _, d_bot = offsets(t_cu[L - 1], k, g[L - 2] * (th[L - 2] - th[L - 1]), q[L - 1] - hb * th[L - 1])
        faces = [(0, 0), (1, L - 1)]
    _finish(res, problem, {0: d_top, 1: d_bot}, None, faces, np.ones((ny, nx)))
    res.extras["surface_rule_field"] = 1.0                                       # Marks the estimate of rule F for the readers that word it
    # A part over absent copper (a window, a pad edge): the face term of the bare laminate (laminate.face_terms, which the FVM, the FDM and the 3D solid add) is not in this model's
    # column and so not in this surface; the sheet smears the copper of the layer into one uniform fill. Measured: a 6 x 6 mm, 2 W part over a 10 x 10 mm window of the top copper of
    # a 60 x 40 mm board reads 109.6 degC in the Analytic against 287.3 in the FVM, the surface 1.8 mK above the column in both senses of the word (checked on the feature branch)
    fill = copper.problem_fill(problem, nx, ny, res.dx, res.dy, 4)
    for h in problem.heaters:
        if h.power > 0 and (h.layer == 0 or h.layer == L - 1):
            cov = coverage_fraction(h.polygon, nx, ny, res.dx, res.dy, 4) > 0
            if cov.any() and float(fill[h.layer][cov].min()) < 1.0 - 1e-6:
                res.extras["surface_part_over_bare_laminate"] = 1.0
                break


def attach_solid(res, net, theta_all):
    """!
    @brief Add the surface arrays of the outer copper faces to the result of the 3D SOLID (rule S, "solid links", and the half slab of a copper layer cut into several slabs).
    @details The solid has every conductance of the board in its matrix, so the heat that crosses each face of the outer copper slab is read from its own links: for the slab s of the face,
                 entering through the face   q_face = Q_s - (g_film + g_heatsink) theta_s + sum over the neighbour slabs on the face side of g (theta_c - theta_s)   (a block above or below)
                 entering through the other  q_in   = sum over the neighbour slabs on the other side of g (theta_c - theta_s)
             (the sideways links of the slab and the heat lost at its edge are not face fluxes). The face is then read in one of two ways, by the number n of slabs through the copper of the layer
             (solid3d.copper_slab_count: one up to 105 um, ceil(t / 70 um) above, at most 8):
             * n = 1 (every board of 35 to 105 um of copper): the slab IS the node of the layer, so the face is the parabola of `offsets` fed with q_face and q_in, the same rule as the FVM
               and the FDM (one-layer plates: the FVM parabola to 1 mK; research/surface-readout-models 4.5); an ESTIMATE, flagged like theirs by t/a;
             * n >= 2: the outer slab is a resolved node a half slab below the face, the heat of a part enters it as a source and flows down, so the face is that node plus the half slab
               above it, q_face dz / (2 k) with dz = t / n: face minus column mean = theta_s + q_face dz / (2 k) - mean of the slabs. Computed from the slabs (8 slabs: -0.00 to +0.13 K of the
               independent 3D solver on the eight plates, 4 slabs +0.01 to +0.73 K), not a parabola; no estimate flag. A thick OUTER layer is the only one cut (an inner layer has no face).
             Over absent copper the laminate face term and the partly filled cells are those of `_finish` (the arrays face_peak and face_mean that the solid already holds), k is the copper's
             as in the FVM. Nothing that exists is changed: the arrays and extras are added and the column read-outs (mean of the slabs) stay the headline.
    @param res SteadyResult of the solid (T = column mean of every layer, in degC).
    @param net The solved solid3d.Solid (K, Q, g, slabs, copper_slabs, fill, area_b, nx, ny).
    @param theta_all Rise of every slab above the ambient, shape (slabs, ny, nx), in K.
    """
    problem = net.problem
    b = problem.board
    L = b.layers
    ny, nx, ns = net.ny, net.nx, net.ns
    n = ny * nx
    k = b.materials.k_copper
    area = np.where(net.area_b > 0, net.area_b, 1.0)
    theta = theta_all.reshape(ns, n)
    K = net.K.tocsr()
    Q = net.Q.reshape(ns, n)
    g_top = (net.g["top"] + net.g["heatsinks"]).reshape(ns, n)
    g_bottom = (net.g["bottom"] + net.g["heatsinks"]).reshape(ns, n)

    def links(s):
        """!
        @brief Heat entering slab s through its links to the slabs above and to the slabs below (W per cell).
        @param s Index of the slab.
        @return Tuple (from_above, from_below), arrays (n,).
        """
        sub = K[s * n:(s + 1) * n].tocoo()
        cl = sub.col // n
        out = []
        for sel in (cl < s, cl > s):
            g = -sub.data[sel]
            heat = g * (theta[cl[sel], sub.col[sel] - cl[sel] * n] - theta[s][sub.row[sel]])
            out.append(np.bincount(sub.row[sel], weights=heat, minlength=n))
        return out[0], out[1]

    d, faces = {}, []
    for face in (0, 1):
        layer = 0 if face == 0 else L - 1
        cs = net.copper_slabs[layer]
        s = cs[0] if face == 0 else cs[-1]
        up, down = links(s)
        film = (g_top[s] if (face == 0 and s == net.board_slab[0]) else 0.0) + (g_bottom[s] if (face == 1 and s == net.last_board) else 0.0)
        # The heat of the parts enters the slab of the face they sit on (layer 1: top; the last layer: bottom); a one-layer board feeds its top face only
        src = net.Q.reshape(ns, n)[s] if (face == 0 or L > 1) else 0.0
        if face == 0:
            q_face, q_in = src - film * theta[s] + up, down
        else:
            q_face, q_in = src - film * theta[s] + down, up
        mean = theta_all[cs].mean(axis=0)
        if len(cs) > 1:
            dz = float(b.copper_thickness[layer]) / len(cs)
            top = theta_all[s] + (q_face.reshape(ny, nx) / area) * dz / (2.0 * k)
            d[face] = top - mean
        else:
            q_t, q_b = (q_face, q_in) if face == 0 else (q_in, q_face)
            d_top, d_bot = offsets(float(b.copper_thickness[layer]), k, q_t.reshape(ny, nx) / area, q_b.reshape(ny, nx) / area)
            d[face] = d_top if face == 0 else d_bot
        res.extras["surface_copper_slabs_top" if face == 0 else "surface_copper_slabs_bottom"] = float(len(cs))
        faces.append((face, layer))
    _finish(res, problem, d, net.fill, faces, net.area_b)
    # A face read from several slabs is computed, not a parabola: the t/a overshoot of the estimate does not apply, so it carries no upper flag (research 4.5)
    for face, layer in faces:
        if len(net.copper_slabs[layer]) > 1:
            res.arrays["T_surface_flag"][face] = False


def attach(res, net, theta, cell, problem):
    """!
    @brief Add the surface arrays of the outer copper faces to the result of the FVM or the FDM (every board, every thickness).
    @details Called with the solved rise of ALL node layers; nothing that exists is changed. The face fluxes are those of the module docstring; the heat of a part enters the
             face it sits on (layer 1: top, the last layer: bottom, a one-layer board: top).
    @param res SteadyResult of the board (T on the board layers, arrays face_peak and face_mean when the laminate rule made them).
    @param net The Network (fvm or fdm) with K, Q, g_top, g_bottom, g_heatsink, fill and block_info.
    @param theta Rise of all node layers (board first, then laminate and block nodes) in kelvin.
    @param cell Board area of every cell or node (ny, nx) in m2.
    @param problem The Problem that was solved.
    """
    b = problem.board
    L = b.layers
    t_cu = np.asarray(b.copper_thickness, dtype=float)
    k_cu = b.materials.k_copper
    area = np.where(cell > 0, cell, 1.0)
    d, faces = {}, []
    # (layer, face of its heat source and of its outer film); a one-layer board has both faces on layer 0
    plan = [(0, 0)] if L == 1 else [(0, 0), (L - 1, 1)]
    for layer, face in plan:
        inner, blk_top, blk_bot = _couplings_out(net, theta, layer)
        th = theta[layer]
        q = net.Q[layer]
        film_top = (net.g_top[layer] + (net.g_heatsink[layer] if face == 0 else 0.0)) * th
        film_bot = (net.g_bottom[layer] + (net.g_heatsink[layer] if face == 1 else 0.0)) * th
        src_top, src_bot = (q, 0.0) if face == 0 else (0.0, q)
        # Heat entering through the faces, W per cell: the part and the films on the outer face, the other layers on the inner face, the block on its face
        if face == 0:
            q_top = src_top - film_top - blk_top
            q_bot = -inner - film_bot - blk_bot
        else:
            q_top = -inner - film_top - blk_top
            q_bot = src_bot - film_bot - blk_bot
        if L == 1:
            q_top = src_top - film_top - blk_top
            q_bot = -inner - film_bot - blk_bot
        d_top, d_bot = offsets(t_cu[layer], k_cu, q_top / area, q_bot / area)
        d[face] = d_top if face == 0 else d_bot
        faces.append((face, layer))
        if L == 1:
            d[1] = d_bot
            faces.append((1, 0))
    _finish(res, problem, d, net.fill, faces, cell)
