#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cases.py
@brief The boards of the comparison, built for the finite-element solver: the published spreading cases (Seri Lee's plate, the Culham-Yovanovich
       coupon), the strong-edge plate with and without a via, the 20 mm square (copper inset or to the wall), the disc, and the T outline.
@details Every builder returns a `board.Board` (and, where the read-out differs, a callable that reads the published quantity). Lengths in the
         arguments are mm, inside the models m. Physics as the finite-volume references of the repository (see `board.py`). Symmetry halves and
         quarters are used where the references use them; the power given to the model is the power inside the modelled domain.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import board                                                           # noqa: E402
import mesh2d                                                          # noqa: E402

MM = 1e-3


def rect(x0, y0, x1, y1):
    """!
    @brief Rectangle polygon in m from mm corners.
    @param x0 Left, mm.
    @param y0 Bottom, mm.
    @param x1 Right, mm.
    @param y1 Top, mm.
    @return numpy.ndarray (4, 2) in m.
    """
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], float) * MM


def axis(length, breaks, zones, hf, growth=1.3, hmax=0.5, start=0.0):
    """!
    @brief Graded plan axis in m from mm data.
    @param length End, mm.
    @param breaks Required nodes, mm.
    @param zones Fine zones (a, b), mm.
    @param hf Fine size, mm.
    @param growth Growth with the distance from a zone.
    @param hmax Largest size, mm.
    @param start Start, mm.
    @return numpy.ndarray in m.
    """
    return mesh2d.grid1d(length * MM, [b * MM for b in breaks], [(a * MM, b * MM) for a, b in zones], hf * MM, growth, hmax * MM, start * MM)


# ----------------------------------------------------------------------------------------------------------------------------------- published cases

def lee_plate(position, hf=1.0, n_z=3, hmax=4.0, growth=1.5):
    """!
    @brief Seri Lee's plate (Electronics Cooling, 1998): aluminium 100 x 100 x 1.3 mm, k 200 W/mK, a 25 x 25 mm source of 1 W as a flux on the top face,
           the fin side as a film h = 1 / (R0 A) = 100 W/m2K on the bottom face, the top face insulated outside the source, the sides insulated.
    @details Symmetry: the centre source uses a quarter (x, y >= 50 mm), the edge-midpoint source a half (x >= 50 mm), the corner the whole plate. The
             published quantity is the maximum constriction resistance Rc = (max source temperature - mean bottom-face temperature) / Q.
    @param position 'centre', 'edge midpoint' or 'corner'.
    @param hf Fine plan size near the source edges, mm.
    @param n_z Elements through the thickness.
    @param hmax Largest plan size, mm.
    @param growth Growth with the distance from the fine zones.
    @return Tuple (Board, read_out callable(result) -> Rc in K/W).
    """
    S, src = 100.0, 25.0
    c = (S - src) / 2
    if position == "centre":
        x0, x1 = 50.0, 100.0
        y0, y1 = 50.0, 100.0
        r = (50.0, 50.0, c + src, c + src)
        sym, power = [("x", 50 * MM), ("y", 50 * MM)], 0.25
    elif position == "edge midpoint":
        x0, x1 = 50.0, 100.0
        y0, y1 = 0.0, 100.0
        r = (50.0, 0.0, c + src, src)
        sym, power = [("x", 50 * MM)], 0.5
    else:
        x0, x1 = 0.0, 100.0
        y0, y1 = 0.0, 100.0
        r = (0.0, 0.0, src, src)
        sym, power = [], 1.0
    pad = 2.0
    zx = [(max(r[0] - pad, x0), r[0] + pad), (r[2] - pad, min(r[2] + pad, x1))]
    zy = [(max(r[1] - pad, y0), r[1] + pad), (r[3] - pad, min(r[3] + pad, y1))]
    xn = axis(x1, [r[0], r[2]], zx, hf, growth, hmax, x0)
    yn = axis(y1, [r[1], r[3]], zy, hf, growth, hmax, y0)
    plan = mesh2d.tensor(xn, yn)
    b = board.Board(plan, 1, board_t=1.3 * MM, t_cu=1.3 * MM, k_cu=200.0, n_cu=n_z, h_top=0.0, h_bottom=100.0, h_side=0.0, symmetry=sym,
                    heaters=[(rect(*r), power)], source_mode="surface", copper=None)

    def read(res):
        """!
        @brief Maximum constriction resistance from a solve (whole-plate power 1 W).
        @param res Result of Board.solve.
        @return float K/W.
        """
        m, T = res["model"], res["T"]
        tot, area = m.face_integral(T, res["info"]["bottom_faces"])
        return (res["heater_max"] - tot / area) / 1.0
    return b, read


CULHAM_FR4 = (0.5263 * MM, 0.4)
CULHAM_CU = (0.0356 * MM, 400.0)
CULHAM_LAYERS = {1: [CULHAM_CU, CULHAM_CU, CULHAM_FR4, CULHAM_FR4, CULHAM_FR4], 2: [CULHAM_CU, CULHAM_FR4, CULHAM_FR4, CULHAM_FR4, CULHAM_CU],
                 3: [CULHAM_FR4, CULHAM_CU, CULHAM_FR4, CULHAM_CU, CULHAM_FR4], 4: [(0.7895 * MM, 0.4), CULHAM_CU, CULHAM_CU, (0.7895 * MM, 0.4)],
                 5: [CULHAM_FR4, CULHAM_FR4, CULHAM_FR4, CULHAM_CU, CULHAM_CU]}


def culham_block(layers, hf=1.0, n_fr4=3, n_cu=1, hmax=2.0):
    """!
    @brief The coupon of Culham and Yovanovich (1998) as a general stack: 50 x 50 mm, layers (thickness, k) from the top, a concentric 25 x 25 mm source of
           2.5 W as a flux on the top face, a film of 5 W/m2K on the free top face and on the bottom, insulated sides; quarter domain (x, y >= 25 mm).
    @param layers List of (thickness m, conductivity W/mK) from the top down.
    @param hf Fine plan size near the source edge, mm.
    @param n_fr4 Elements through a layer thicker than 0.1 mm.
    @param n_cu Elements through a thin layer.
    @param hmax Largest plan size, mm.
    @return Tuple (Board, read_out callable(result) -> R_solid in K/W: (mean source temperature - mean wall temperature) / Q).
    """
    xn = axis(50.0, [37.5], [(35.5, 39.5)], hf, 1.4, hmax, 25.0)
    plan = mesh2d.tensor(xn, xn)
    dz, kind = [], []
    for i, (t, k) in enumerate(layers):
        n = n_fr4 if t > 0.1 * MM else n_cu
        for _ in range(n):
            dz.append(t / n)
            kind.append(k)
    b = board.Board(plan, 1, board_t=sum(dz), t_cu=sum(dz), k_cu=1.0, h_top=5.0, h_bottom=5.0, h_side=0.0, symmetry=[("x", 25 * MM), ("y", 25 * MM)],
                    heaters=[(rect(25.0, 25.0, 37.5, 37.5), 2.5 / 4)], source_mode="surface", copper=None)
    # override the stack: the Board made one slab; replace by the layer list (isotropic every slab)
    b.dz = np.asarray(dz)
    b.kind = [("cu", 0)] * len(dz)
    b._k_slab = np.asarray(kind)

    def build_patched():
        """!
        @brief Build with the per-slab conductivities.
        @return Tuple (model, info).
        """
        m, info = board.Board.build(b)
        ks = b._k_slab[info["ex"]["slab"]]
        m.k[:, 0] = ks
        m.k[:, 1] = ks
        m.k[:, 2] = ks
        return m, info
    b.build = build_patched

    def read(res):
        """!
        @brief Solid-body resistance of the coupon (power 2.5 W on the whole coupon).
        @param res Result of Board.solve.
        @return float K/W.
        """
        m, T, info = res["model"], res["T"], res["info"]
        hsel = np.zeros(b.plan.quads.shape[0], bool)
        c = b.plan.centroids()
        for poly, _ in b.heaters:
            hsel |= board.in_polygons(c, poly)
        walls = np.vstack([info["top_faces"][~hsel], info["bottom_faces"]])
        tot, area = m.face_integral(T, walls)
        return (res["heater_mean"] - tot / area) / 2.5
    return b, read


def culham_effective(target, hf=1.0, total=None, n_sub=8, lo=0.3, hi=60.0, iters=30):
    """!
    @brief Effective conductivity of the paper: the single isotropic layer of the same thickness and boundary conditions with the same solid-body resistance.
    @param target R_solid of the laminate, K/W.
    @param hf Fine plan size, mm.
    @param total Total thickness in m.
    @param n_sub Elements through the single layer.
    @param lo Lower bracket W/mK.
    @param hi Upper bracket W/mK.
    @param iters Bisection steps on the logarithm.
    @return float W/mK.
    """
    a, bb = np.log(lo), np.log(hi)
    for _ in range(iters):
        mid = 0.5 * (a + bb)
        k = float(np.exp(mid))
        b, read = culham_block([(total, k)], hf, n_fr4=n_sub)
        r = read(b.solve())
        if r > target:
            a = mid
        else:
            bb = mid
    return float(np.exp(0.5 * (a + bb)))


# ------------------------------------------------------------------------------------------------------------------------------- strong-edge plate

def strong_edge(h_side, hf=0.1, n_gap=6, via_dist=None, inset=0.0, growth=1.3, hmax=0.5, via_r=0.15, power=0.5, n_side_via=8, gap_ratio=1.4):
    """!
    @brief The strong-edge board of `research/strong-edge-laminate`: 10 x 10 mm, four copper layers 35 um, equal gaps (0.487 mm), FR-4 0.3 W/mK in the plane and
           through, h_top 10, h_bottom 200, a 3 x 2 mm source of 0.5 W at (1..4, 4..6) mm, the film `h_side` on every wall slab; half domain y <= 5 mm.
    @details The via, when given, is a solid copper cylinder of radius `via_r` mm centred on the symmetry line y = 5 mm at `via_dist` mm from the wall x = 10 mm,
             meshed as a conforming O-grid patch (its window reaches the wall when the via is within one window of it) cut by the symmetry line.
    @param h_side Wall film, W/m2K.
    @param hf Fine plan size near the walls, the source edges and the via, mm.
    @param n_gap Elements per gap (graded towards the copper).
    @param via_dist Distance of the via centre from the wall x = 10 mm, in mm; None for no via.
    @param inset Copper inset from the walls, mm.
    @param growth Size growth with the distance from a fine zone.
    @param hmax Largest plan size, mm.
    @param via_r Drill radius, mm.
    @param power Source power of the whole board, W.
    @param n_side_via Intervals per side of the via window.
    @param gap_ratio Grading ratio of the gap elements.
    @return Board.
    """
    W = 10.0
    bx = [0, 1, 4, W] + ([inset, W - inset] if inset > 0 else [])
    by = [0, 4, 5] + ([inset] if inset > 0 else [])
    zx = [(0, 0.6), (W - 0.6, W), (0.4, 1.6), (3.4, 4.6)]
    zy = [(0, 0.6), (3.4, 5)]
    vias = []
    if via_dist is not None:
        cx = W - via_dist
        half = min(via_dist, 0.5)                                       # the window reaches the wall when the via is near it
        radii = [via_r] + ([0.3] if half > 0.4 else [])
        n_blend = 2 if half > 0.4 else 0
        zx.append((cx - half - 0.3, min(cx + half + 0.3, W)))
        # the plan axes carry the window: uniform intervals across it, symmetric about the via centre in y
        xn = axis(W, bx, zx, hf, growth, hmax)
        yn = axis(5.0 + half, by + [5.0], zy + [(5.0 - half - 0.3, 5.0 + half)], hf, growth, hmax)
        xn = mesh2d.uniform_window(xn, (cx - half) * MM, (cx + half) * MM, n_side_via)
        yn = mesh2d.uniform_window(yn, (5.0 - half) * MM, (5.0 + half) * MM, n_side_via)
        plan = mesh2d.tensor(xn, yn)
        plan = mesh2d.embed_ogrid(plan, cx * MM, 5.0 * MM, half * MM, n_side_via, [r * MM for r in radii], n_blend=n_blend, n_inner=1 if half > 0.4 else 0)
        plan = plan.remove(plan.centroids()[:, 1] > 5.0 * MM)           # keep the half domain: the O-grid is symmetric about the line through its centre
        vias = [dict(cx=cx * MM, cy=5.0 * MM, r_drill=via_r * MM)]
    else:
        xn = axis(W, bx, zx, hf, growth, hmax)
        yn = axis(5.0, by, zy, hf, growth, hmax)
        plan = mesh2d.tensor(xn, yn)
    copper = None if inset <= 0 else rect(inset, inset, W - inset, W - inset)
    return board.Board(plan, 4, board_t=1.6 * MM, k_xy=0.3, k_z=0.3, n_gap=n_gap, gap_ratio=gap_ratio, h_top=10.0, h_bottom=200.0, h_side=h_side,
                       symmetry=[("y", 5.0 * MM)], copper=copper, vias=vias, heaters=[(rect(1, 4, 4, 5), 0.5 * power)])


# --------------------------------------------------------------------------------------------------------------------- square, disc and T outline

def square(h_side, inset=0.0, hf=0.2, n_gap=6, growth=1.3, hmax=0.8, layers=2, side=20.0, heater=4.0):
    """!
    @brief The 20 mm square of the edge-film study: two copper layers (35 um, 1.6 mm board), FR-4 0.9 / 0.3 W/mK, h_top = h_bottom = 10, 1 W in a 4 mm square at the
           centre of the top layer, the copper to the wall or held `inset` inside it; quarter domain (x, y >= 0 are the symmetry planes).
    @param h_side Wall film W/m2K.
    @param inset Copper inset from the wall, mm (0: to the wall).
    @param hf Fine plan size, mm.
    @param n_gap Elements per gap.
    @param growth Growth with the distance from a fine zone.
    @param hmax Largest plan size, mm.
    @param layers Copper layers.
    @param side Board side, mm.
    @param heater Heater side, mm.
    @return Board.
    """
    h = side / 2
    lim = h - inset
    bx = [heater / 2, lim, h]
    zx = [(heater / 2 - 0.4, heater / 2 + 0.4), (lim - 0.5, h)]
    xn = axis(h, bx, zx, hf, growth, hmax)
    plan = mesh2d.tensor(xn, xn)
    copper = None if inset <= 0 else rect(-1, -1, lim, lim)
    return board.Board(plan, layers, board_t=1.6 * MM, k_xy=0.9, k_z=0.3, n_gap=n_gap, h_top=10.0, h_bottom=10.0, h_side=h_side,
                       symmetry=[("x", 0.0), ("y", 0.0)], copper=copper, heaters=[(rect(-1, -1, heater / 2, heater / 2), 0.25)])


def disc_board(h_side, inset=0.0, n_side=10, n_gap=6, layers=2, radius=10.0, heater=4.0, growth=1.3):
    """!
    @brief A disc of radius 10 mm (same stack, films and 4 mm heater as the square), meshed as a conforming O-grid whose inner square is the heater itself; copper to
           the rim or held `inset` inside it (a circle level of the mesh). Whole disc (no symmetry).
    @param h_side Wall film W/m2K.
    @param inset Copper inset from the rim, mm.
    @param n_side Intervals per side of the heater square (the mesh scale).
    @param n_gap Elements per gap.
    @param layers Copper layers.
    @param radius Disc radius, mm.
    @param heater Heater side, mm.
    @param growth Unused (kept for the signature of the other builders).
    @return Board.
    """
    R, s0 = radius * MM, heater / 2 * MM
    r_cu = (radius - inset) * MM
    # rings: radial size about the angular size of the heater grid (2 s0 / n_side), finer towards the rim
    hc = 2 * s0 / n_side
    r0 = s0 * np.sqrt(2.0) * 1.1
    n_inner = max(int(round((r0 - s0) / hc)) - 1, 0)
    radii = [r0]
    r = r0
    while r < R - 1e-12:
        step = min(hc * 1.6, (R - r))
        r = min(r + step, R)
        radii.append(r)
    radii[-1] = R
    if inset > 0:
        radii = sorted(set(radii + [r_cu]))
        # drop a level too close to the copper edge
        radii = [x for x in radii if abs(x - r_cu) < 1e-12 or abs(x - r_cu) > 0.3 * hc]
    plan = mesh2d.ogrid(0.0, 0.0, s0, radii, n_side, ("circle", R), n_inner=n_inner)
    copper = None if inset <= 0 else (lambda c: np.hypot(c[:, 0], c[:, 1]) < r_cu)
    heater_poly = np.array([[-s0, -s0], [s0, -s0], [s0, s0], [-s0, s0]])
    return board.Board(plan, layers, board_t=1.6 * MM, k_xy=0.9, k_z=0.3, n_gap=n_gap, h_top=10.0, h_bottom=10.0, h_side=h_side, copper=copper,
                       heaters=[(heater_poly, 1.0)])


T_OUT = [[0, 20], [20, 20], [20, 14], [13.2, 14], [13.2, 0], [6.8, 0], [6.8, 14], [0, 14]]


def t_outline(h_side, hf=0.2, n_gap=6, growth=1.3, hmax=0.8, half=True):
    """!
    @brief The T outline with copper to the wall (`T_wall` of `research/imported-copper-edge-film`): bar 20 x 6 mm (y 14..20), stem 6.4 mm wide (x 6.8..13.2, y 0..14),
           2 layers, heater 2.4 x 2.4 mm at (8.8..11.2, 16..18.4), 1 W, h_top = h_bottom = 10; the film on every wall.
    @param h_side Wall film W/m2K.
    @param hf Fine plan size, mm.
    @param n_gap Elements per gap.
    @param growth Growth with the distance from a fine zone.
    @param hmax Largest plan size, mm.
    @param half Half domain x >= 10 mm (symmetry plane) when True, the whole T otherwise.
    @return Board.
    """
    bx = [6.8, 8.8, 10, 11.2, 13.2, 20]
    by = [0, 14, 16, 18.4, 20]
    zx = [(0, 0.6), (6.2, 7.4), (8.2, 11.8), (12.6, 14), (19.4, 20)]
    zy = [(0, 0.6), (13.4, 14.6), (15.6, 18.8), (19.4, 20)]
    x0 = 10.0 if half else 0.0
    xn = axis(20.0, bx, zx, hf, growth, hmax, x0)
    yn = axis(20.0, by, zy, hf, growth, hmax)
    plan = mesh2d.tensor(xn, yn)
    c = plan.centroids() / MM
    outside = ~((c[:, 1] > 14) | ((c[:, 0] > 6.8) & (c[:, 0] < 13.2)))
    plan = plan.remove(outside)
    heater = rect(10.0 if half else 8.8, 16, 11.2, 18.4)
    return board.Board(plan, 2, board_t=1.6 * MM, k_xy=0.9, k_z=0.3, n_gap=n_gap, h_top=10.0, h_bottom=10.0, h_side=h_side,
                       symmetry=[("x", 10.0 * MM)] if half else [], copper=None, heaters=[(heater, 0.5 if half else 1.0)])


# --------------------------------------------------------------------------------------------------------------------------- thin-laminate boards

PAD_MM = (0.5, 3.0, 5.5, 7.0)


def thin_board(layers, total_mm, h_side, variant="full", hf=0.1, hmax=None, n_gap=6, growth=1.3, power=0.5, gap_ratio=1.4):
    """!
    @brief The boards of `research/strong-edge-laminate/scripts/study_thin_laminate.py` (validation 44): 10 x 10 mm, `layers` copper layers of 35 um in `total_mm`,
           equal gaps (the advanced stack-up with physical slabs), FR-4 0.3 both ways, h_top 10, h_bottom 200, a 0.5 W 3 x 2 mm source at (1..4, 4..6) mm, the film
           `h_side` on the walls x = 0, x = 10 and y = 0; half domain y <= 5 mm. Variant 'pad': the outer layers carry copper only in the pad (0.5..5.5, 3..7) mm.
    @param layers Copper layers.
    @param total_mm Board thickness, mm.
    @param h_side Wall film, W/m2K.
    @param variant 'full' or 'pad'.
    @param hf Fine plan size, mm.
    @param hmax Largest plan size, mm (default 5 hf, so that the whole plan refines with hf).
    @param n_gap Elements per gap.
    @param growth Size growth with the distance from a fine zone.
    @param power Source power of the whole board, W.
    @param gap_ratio Grading ratio of the gap elements.
    @return Board.
    """
    W = 10.0
    if hmax is None:
        hmax = 5 * hf
    bx = [0, 1, 4, W] + ([PAD_MM[0], PAD_MM[2]] if variant == "pad" else [])
    by = [0, 4, 5] + ([PAD_MM[1]] if variant == "pad" else [])
    zx = [(0, 0.6), (W - 0.6, W), (0.4, 1.6), (3.4, 4.6)] + ([(0.1, 0.9), (5.1, 5.9)] if variant == "pad" else [])
    zy = [(0, 0.6), (3.4, 5)] + ([(2.6, 3.4)] if variant == "pad" else [])
    xn = axis(W, bx, zx, hf, growth, hmax)
    yn = axis(5.0, by, zy, hf, growth, hmax)
    plan = mesh2d.tensor(xn, yn)
    pad = rect(*PAD_MM)
    copper = [pad if (variant == "pad" and l in (0, layers - 1)) else None for l in range(layers)]
    return board.Board(plan, layers, board_t=total_mm * MM, k_xy=0.3, k_z=0.3, n_gap=n_gap, gap_ratio=gap_ratio, h_top=10.0, h_bottom=200.0, h_side=h_side,
                       symmetry=[("y", 5.0 * MM)], copper=copper, heaters=[(rect(1, 4, 4, 5), 0.5 * power)])
