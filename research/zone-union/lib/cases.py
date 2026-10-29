"""!
@file cases.py
@brief The test boards of the zone-union investigation: each case gives the zones for the models (polygon and fill) and the resolved copper for the reference (solid polygons).
@details Question answered: on which drawings do the rules that combine zones differ, and which one agrees with the resolved copper? All boards are 20 x 20 mm, 1.6 mm, 35 um copper,
         h = 10 W/m2K on both faces, one rectangular 4 x 4 mm heater of 1 W at the centre (the board of gerber-models 4.39), one copper layer unless the case has `layers`.
         A case is a dict: `zones` (list of dicts layer, poly in mm, fill), `resolved` (dict layer -> list of polygons in mm, the copper that exists; None when the case has no resolved copper
         because a fill below 1 is a density, not a geometry), `equals` (name of the case that must give the same result), `layers`.
         Polygons are given in mm; `build` converts. Needs pcbthermal importable (variant.use first) only in new_problem and build.
"""

import numpy as np

SIZE = 20.0                                          # Board side (mm)


def rect(x0, y0, x1, y1):
    """!
    @brief Rectangle as a polygon.
    @param x0 Left (mm).
    @param y0 Bottom (mm).
    @param x1 Right (mm).
    @param y1 Top (mm).
    @return numpy.ndarray (4, 2).
    """
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=float)


def clip_halfplane(poly, p0, n):
    """!
    @brief Part of a convex polygon on the side of a line (Sutherland-Hodgman against one half-plane).
    @param poly Convex polygon (m, 2).
    @param p0 A point of the line.
    @param n Normal pointing to the side that is kept.
    @return numpy.ndarray Clipped polygon (empty if nothing is kept).
    """
    out = []
    pts = [np.asarray(q, dtype=float) for q in poly]
    for i, a in enumerate(pts):
        b = pts[(i + 1) % len(pts)]
        da, db = float(np.dot(a - p0, n)), float(np.dot(b - p0, n))
        if da >= 0:
            out.append(a)
        if (da >= 0) != (db >= 0):
            out.append(a + (b - a) * da / (da - db))
    return np.array(out)


def split_board(angle_deg, offset_mm):
    """!
    @brief The board cut in two zones by a line through the centre of the board shifted along its normal.
    @param angle_deg Direction of the line (0 = along x).
    @param offset_mm Shift of the line along its normal (mm).
    @return tuple of two polygons whose union is the whole board and that share the cut line.
    """
    a = np.radians(angle_deg)
    t, n = np.array([np.cos(a), np.sin(a)]), np.array([-np.sin(a), np.cos(a)])
    p0 = np.array([SIZE / 2, SIZE / 2]) + n * offset_mm
    board = rect(0, 0, SIZE, SIZE)
    return clip_halfplane(board, p0, n), clip_halfplane(board, p0, -n)


def stripes(vertical, width, pitch, shift=0.0):
    """!
    @brief Solid stripes (separate rectangles) that make a hatched pattern over the whole board.
    @param vertical True for stripes along y, False along x.
    @param width Stripe width (mm).
    @param pitch Stripe pitch (mm).
    @param shift Offset of the first stripe (mm).
    @return list of polygons.
    """
    out = []
    x = shift
    while x < SIZE - 1e-9:
        lo, hi = x, min(x + width, SIZE)
        out.append(rect(lo, 0, hi, SIZE) if vertical else rect(0, lo, SIZE, hi))
        x += pitch
    return out


def zone(poly, fill=1.0, layer=0):
    """!
    @brief A zone dict.
    @param poly Polygon (mm).
    @param fill Fill (0 to 1).
    @param layer 0-based layer.
    @return dict.
    """
    return {"layer": layer, "poly": np.asarray(poly, dtype=float), "fill": fill}


def solid_of(zones):
    """!
    @brief Resolved copper of zones that are all solid: the same polygons.
    @param zones List of zone dicts.
    @return dict layer -> list of polygons (mm).
    """
    out = {}
    for z in zones:
        out.setdefault(z["layer"], []).append(z["poly"])
    return out


def new_problem(layers=1, isotropic=True):
    """!
    @brief The 20 x 20 mm board with its heater.
    @param layers Copper layers.
    @param isotropic True: laminate 0.3 W/mK in every direction (as the reference); False: the program's default 0.3 through / 0.9 in plane.
    @return Problem.
    """
    from pcbthermal import Problem
    from pcbthermal.model import Materials
    mat = Materials(k_fr4_through=0.3, k_fr4_inplane=0.3) if isotropic else Materials()
    p = Problem.new(width_mm=SIZE, height_mm=SIZE, layers=layers, thickness_mm=1.6, copper_um=35.0, h_top=10.0, h_bottom=10.0, h_side=None, materials=mat)
    p.add_heater(1, 1.0, rect=(8, 8, 12, 12))
    return p


def build(case, isotropic=True):
    """!
    @brief The Problem of a case (zones with their fill) and the resolved copper in metres for the reference.
    @param case Case dict.
    @param isotropic Laminate isotropic or the program's default.
    @return tuple (Problem, resolved dict layer -> list of polygons in metres or None).
    """
    p = new_problem(case.get("layers", 1), isotropic)
    for z in case["zones"]:
        p.add_zone(z["layer"] + 1, polygon=z["poly"].tolist(), fill=z["fill"])
    res = case["resolved"]
    return p, (None if res is None else {k: [np.asarray(q) * 1e-3 for q in v] for k, v in res.items()})


def make_cases():
    """!
    @brief All the cases of the investigation, in order.
    @return dict name -> case.
    """
    C = {}
    full = [zone(rect(0, 0, SIZE, SIZE))]
    C["one zone"] = {"zones": full, "resolved": solid_of(full)}
    st = [zone(rect(0.5 * j, 0, 0.5 * (j + 1), SIZE)) for j in range(40)]
    C["40 abutting strips of 0.5 mm"] = {"zones": st, "resolved": solid_of(st), "equals": "one zone"}
    # Densities (a fill below 1 has no geometry to resolve: the reference is not defined for these)
    C["one zone of fill 0.5"] = {"zones": [zone(rect(0, 0, SIZE, SIZE), 0.5)], "resolved": None}
    C["two overlapping zones of fill 0.5"] = {"zones": [zone(rect(0, 0, SIZE, SIZE), 0.5), zone(rect(0, 0, SIZE, SIZE), 0.5)], "resolved": None, "equals": "one zone of fill 0.5"}
    C["fills 0.8 and 0.4 overlapping partly"] = {"zones": [zone(rect(0, 0, 12, SIZE), 0.8), zone(rect(8, 0, SIZE, SIZE), 0.4)], "resolved": None}
    # Solid zones that meet
    for x in (10.0, 10.25, 10.37):
        zs = [zone(rect(0, 0, x, SIZE)), zone(rect(x, 0, SIZE, SIZE))]
        C[f"two zones meeting at x = {x} mm"] = {"zones": zs, "resolved": solid_of(full), "equals": "one zone"}
    for ang in (0, 15, 30, 45):
        a, b = split_board(ang, 0.13)
        C[f"two zones meeting along a line at {ang} degrees"] = {"zones": [zone(a), zone(b)], "resolved": solid_of(full), "equals": "one zone"}
    t3 = [zone(rect(0, 0, 10.13, SIZE)), zone(rect(10.13, 0, SIZE, 10.13)), zone(rect(10.13, 10.13, SIZE, SIZE))]
    C["three zones meeting at a T"] = {"zones": t3, "resolved": solid_of(full), "equals": "one zone"}
    c4 = [zone(rect(0, 0, 10.13, 10.13)), zone(rect(10.13, 0, SIZE, 10.13)), zone(rect(0, 10.13, 10.13, SIZE)), zone(rect(10.13, 10.13, SIZE, SIZE))]
    C["four zones meeting at a corner"] = {"zones": c4, "resolved": solid_of(full), "equals": "one zone"}
    # Zones that overlap (solid): the union is the geometric union, whatever the overlap
    ov = [zone(rect(0, 0, 12.2, SIZE)), zone(rect(7.8, 0, SIZE, SIZE))]
    C["two solid zones overlapping by 4.4 mm"] = {"zones": ov, "resolved": solid_of(full), "equals": "one zone"}
    # A frame with a hole (a cut-in joins the hole to the outside) and an island in the hole 0.3 mm from the frame: copper of two zones in the cells at the gap
    # Outer boundary, a slit of 1 um at y = 10 mm into a square hole of 5.6 .. 14.4 mm, written as one simple polygon
    ring = np.array([[0, 0], [SIZE, 0], [SIZE, SIZE], [0, SIZE], [0, 10.0], [5.6, 10.0], [5.6, 14.4], [14.4, 14.4], [14.4, 5.6], [5.6, 5.6], [5.6, 10.0 - 1e-3], [0, 10.0 - 1e-3]])
    isl = rect(5.9, 5.9, 14.1, 14.1)
    zs = [zone(ring), zone(isl)]
    C["frame with a hole and an island 0.3 mm inside it"] = {"zones": zs, "resolved": solid_of(zs)}
    # Zones on two layers: each layer is combined on its own
    st2 = [zone(rect(0.5 * j, 0, 0.5 * (j + 1), SIZE), layer=0) for j in range(40)] + [zone(rect(0, 0.5 * j, SIZE, 0.5 * (j + 1)), layer=1) for j in range(40)]
    fl2 = [zone(rect(0, 0, SIZE, SIZE), layer=0), zone(rect(0, 0, SIZE, SIZE), layer=1)]
    C["two layers, abutting strips on each (top vertical, bottom horizontal)"] = {"zones": st2, "layers": 2, "resolved": solid_of(fl2), "equals": "two layers, one zone on each"}
    C["two layers, one zone on each"] = {"zones": fl2, "layers": 2, "resolved": solid_of(fl2)}
    # Hatched zones with an explicit pattern: stripes of 0.5 mm at a pitch of 1 mm are fill 0.5; the zones are drawn with fill 0.5 over the whole board
    v0, v1 = stripes(True, 0.5, 1.0, 0.0), stripes(True, 0.5, 1.0, 0.5)
    h0 = stripes(False, 0.5, 1.0, 0.0)
    whole = rect(0, 0, SIZE, SIZE)
    C["hatch: one zone of vertical stripes (fill 0.5)"] = {"zones": [zone(whole, 0.5)], "resolved": {0: v0}}
    C["hatch: two identical hatched zones"] = {"zones": [zone(whole, 0.5), zone(whole, 0.5)], "resolved": {0: v0}}
    C["hatch: two complementary hatched zones (stripes shifted by half a pitch)"] = {"zones": [zone(whole, 0.5), zone(whole, 0.5)], "resolved": {0: v0 + v1}}
    C["hatch: crossed hatched zones (vertical and horizontal stripes)"] = {"zones": [zone(whole, 0.5), zone(whole, 0.5)], "resolved": {0: v0 + h0}}
    C["hatch: a hatched zone over a solid zone (union is solid)"] = {"zones": [zone(whole, 1.0), zone(rect(4, 4, 16, 16), 0.5)], "resolved": {0: [whole]}, "equals": "one zone"}
    return C
