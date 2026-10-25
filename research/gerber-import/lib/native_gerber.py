"""!
@file native_gerber.py
@brief An independent Gerber (RS-274X) and Excellon reader and rasteriser that needs only NumPy: no gerbonara, no shapely, no GEOS.
@details Written from the public Gerber layer format specification (Ucamco) and the common Excellon conventions, so that the Gerber import can be built
         without third-party geometry libraries. It draws straight into a boolean mask of a window of the board, sampling the centre of every pixel.
         Supported: units (MM, IN, G70/G71), coordinate formats (leading or trailing zero omission), standard apertures C, R, O, P with holes, aperture macros
         (primitives 0, 1, 4, 5, 7, 20, 21, 22 with variables and arithmetic), draws (D01) with circular apertures and with rectangular ones (convex hull of the two
         flashes), flashes (D03), arcs (G02/G03 in single and multi quadrant mode, G74/G75), regions (G36/G37), dark and clear polarity (LPD/LPC), step and repeat (SR)
         and the image polarity IPNEG. Not supported (the reader raises NotImplementedError and says what): aperture blocks (AB), mirrored, rotated or scaled
         apertures (LM, LR, LS), the moire macro primitive 6, a non-zero image offset, mirror, scale or rotation (OF, MI, SF, IR), an axis select that swaps the axes (AS)
         and incremental coordinates (FS with I, G91). Deviation kept on purpose: G37 resets the interpolation mode to G01 (the specification keeps it modal; gerbonara's
         test file example_level_holes.gbr needs the reset, README section 5). Silently ignored: everything else that does not draw (G54, IN, LN, the object attributes other than TO.N, ...).
"""

import math
import re
from pathlib import Path

import numpy as np

ARC_TOLERANCE = 0.005          # mm, maximum chord error when an arc is cut into straight pieces


class GerberError(ValueError):
    """!@brief A file that cannot be read."""


# --------------------------------------------------------------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------------------------------------------------------------

def _attributes_as_commands(text):
    """!
    @brief Turn attributes written as comments into extended commands.
    @details The Gerber specification allows (and the gerber-writer library writes) the attributes in the compatibility form `G04 #@! TF.FileFunction,Copper,L1,Top*`, which an older reader
             ignores as a comment; they carry the file function, the aperture functions and the net names, so they are rewritten as `%TF.FileFunction,Copper,L1,Top*%`.
    @param text File content.
    @return Text with the attribute comments as extended commands.
    """
    return re.sub(r"G04\s+#@!\s+(T[FAOD][^*]*)\*", r"%\1*%", text)


def _blocks(text):
    """!
    @brief Split a Gerber file into its blocks: extended commands (between % signs) and ordinary data blocks (ended by *).
    @param text File content.
    @return List of tuples (kind, text) with kind "ext" or "data".
    """
    out = []
    text = _attributes_as_commands(text)
    # Some writers (gerbonara) leave the star off a lone G code line ("G75"); without it the block would swallow the next command
    text = re.sub(r"(?m)^(G\d{1,2})[ \t]*$", r"\1*", text)
    pos, n = 0, len(text)
    while pos < n:
        c = text[pos]
        if c in " \r\n\t":
            pos += 1
        elif c == "%":                                   # An extended command may hold several blocks, ending at the next %
            end = text.find("%", pos + 1)
            if end < 0:
                break
            out.append(("ext", text[pos + 1:end]))
            pos = end + 1
        else:
            end = text.find("*", pos)
            if end < 0:
                break
            out.append(("data", text[pos:end].strip()))
            pos = end + 1
    return out


def _number(s, nint, ndec, zeros):
    """!
    @brief Convert a coordinate string of a Gerber file to a float in file units.
    @param s String with an optional sign and digits (or a decimal point, as some generators write).
    @param nint Integer digits of the format.
    @param ndec Decimal digits of the format.
    @param zeros "L" (leading zeros omitted) or "T" (trailing zeros omitted).
    @return Value as a float.
    """
    if "." in s:
        return float(s)
    sign = -1.0 if s.startswith("-") else 1.0
    digits = s.lstrip("+-")
    if zeros == "T":                                    # Trailing zeros omitted: pad on the right to the full width
        digits = digits.ljust(nint + ndec, "0")
    return sign * int(digits or "0") / (10 ** ndec)


def _eval(expr, variables):
    """!
    @brief Evaluate an aperture-macro arithmetic expression ($n variables, + - x / and parentheses).
    @param expr Expression text.
    @param variables Dict number -> value.
    @return Float.
    @throws GerberError If the expression contains anything else.
    """
    e = expr.strip().replace("X", "x").replace("x", "*")
    e = re.sub(r"\$(\d+)", lambda m: repr(float(variables.get(int(m.group(1)), 0.0))), e)
    if not re.fullmatch(r"[0-9eE.+\-*/() ]*", e):
        raise GerberError(f"unsupported macro expression {expr!r}")
    return float(eval(e, {"__builtins__": {}}, {}))      # The character set above leaves only numbers and arithmetic


class Aperture:
    """!@brief One aperture: a standard shape or an aperture macro instance, with the test "is this local point inside"."""

    def __init__(self, kind, params, macro=None):
        """!
        @brief Store the definition.
        @param kind "C", "R", "O", "P" or "M" (macro).
        @param params List of floats (mm).
        @param macro List of macro primitives (already evaluated) for kind "M".
        """
        self.kind, self.p, self.macro = kind, params, macro or []
        self.func = ""                 # X2 aperture function (TA.AperFunction): "ViaPad", "ComponentPad", "SMDPad,CuDef", "Conductor", ... ; empty when the file has none
        # Radius that contains the whole aperture around its origin (for the bounding box of a flash)
        if kind == "C":
            self.radius = params[0] / 2
        elif kind in ("R", "O"):
            self.radius = math.hypot(params[0], params[1]) / 2
        elif kind == "P":
            self.radius = params[0] / 2
        else:
            self.radius = max([q["radius"] for q in self.macro] + [0.0])

    def inside(self, u, v):
        """!
        @brief Which of the points (u, v), in the aperture's own coordinates (mm), are inside it.
        @param u Array of x coordinates.
        @param v Array of y coordinates.
        @return Boolean array.
        """
        k, p = self.kind, self.p
        if k == "C":
            m = u * u + v * v <= (p[0] / 2) ** 2
            hole = p[1] if len(p) > 1 else 0.0
            return m & ~(u * u + v * v < (hole / 2) ** 2) if hole > 0 else m
        if k == "R":
            m = (np.abs(u) <= p[0] / 2) & (np.abs(v) <= p[1] / 2)
            hole = p[2] if len(p) > 2 else 0.0
            return m & ~(u * u + v * v < (hole / 2) ** 2) if hole > 0 else m
        if k == "O":
            w, h = p[0], p[1]
            if w >= h:                                       # horizontal stadium: a segment of length w - h with radius h / 2
                d = np.maximum(np.abs(u) - (w - h) / 2, 0.0)
                m = d * d + v * v <= (h / 2) ** 2
            else:
                d = np.maximum(np.abs(v) - (h - w) / 2, 0.0)
                m = u * u + d * d <= (w / 2) ** 2
            hole = p[2] if len(p) > 2 else 0.0
            return m & ~(u * u + v * v < (hole / 2) ** 2) if hole > 0 else m
        if k == "P":
            m = _regular_polygon(u, v, p[0] / 2, int(p[1]), p[2] if len(p) > 2 else 0.0)
            hole = p[3] if len(p) > 3 else 0.0
            return m & ~(u * u + v * v < (hole / 2) ** 2) if hole > 0 else m
        # Macro: the primitives are applied in order, exposure 1 adds, exposure 0 removes (inside this aperture only)
        m = np.zeros(u.shape, bool)
        for q in self.macro:
            r = q["inside"](u, v)
            m = (m | r) if q["exposure"] else (m & ~r)
        return m


def _regular_polygon(u, v, r, n, rot_deg):
    """!
    @brief Points inside a regular polygon with n vertices on a circle of radius r (first vertex at the rotation angle).
    @param u X coordinates.
    @param v Y coordinates.
    @param r Circumscribed radius.
    @param n Number of vertices.
    @param rot_deg Rotation in degrees.
    @return Boolean array.
    """
    a = math.radians(rot_deg)
    uu, vv = u * math.cos(a) + v * math.sin(a), -u * math.sin(a) + v * math.cos(a)
    sector = 2 * math.pi / n
    theta = np.mod(np.arctan2(vv, uu), sector)                       # angle measured from the previous vertex direction
    return np.hypot(uu, vv) * np.cos(theta - sector / 2) <= r * math.cos(math.pi / n)        # distance along the edge normal against the apothem


def _rot(u, v, deg):
    """!
    @brief Express points in a frame rotated by deg degrees (counter-clockwise rotation of the shape = clockwise rotation of the points).
    @param u X coordinates.
    @param v Y coordinates.
    @param deg Rotation of the shape in degrees.
    @return Tuple (u', v').
    """
    a = math.radians(deg)
    return u * math.cos(a) + v * math.sin(a), -u * math.sin(a) + v * math.cos(a)


def _macro_primitive(code, args):
    """!
    @brief Turn one evaluated aperture-macro primitive into a dict with its exposure, a bounding radius and an inside test.
    @param code Primitive code (0, 1, 4, 5, 7, 20, 21, 22).
    @param args List of evaluated numbers.
    @return Dict or None (a comment).
    @throws NotImplementedError For the moire primitive (6) and unknown codes.
    """
    if code == 0:
        return None
    args = list(args) + [0.0] * 8                                    # a missing optional parameter (centre, rotation) is zero
    exp = bool(int(args[0])) if code != 7 else True
    if code == 1:                                                    # circle: exposure, diameter, cx, cy, [rotation]
        d, cx, cy = args[1], args[2], args[3]
        rot = args[4] if len(args) > 4 else 0.0
        a = math.radians(rot)
        cx, cy = cx * math.cos(a) - cy * math.sin(a), cx * math.sin(a) + cy * math.cos(a)
        return {"exposure": exp, "radius": math.hypot(cx, cy) + d / 2, "inside": lambda u, v: (u - cx) ** 2 + (v - cy) ** 2 <= (d / 2) ** 2}
    if code in (20, 21, 22):
        if code == 20:                                               # vector line: exposure, width, x1, y1, x2, y2, rotation
            w, x1, y1, x2, y2, rot = args[1], args[2], args[3], args[4], args[5], args[6] if len(args) > 6 else 0.0
            cx, cy, ln, ang = (x1 + x2) / 2, (y1 + y2) / 2, math.hypot(x2 - x1, y2 - y1), math.atan2(y2 - y1, x2 - x1)
            half_w, half_h, tilt = ln / 2, w / 2, ang
        elif code == 21:                                             # centre line: exposure, width, height, cx, cy, rotation
            w, h, cx, cy, rot = args[1], args[2], args[3], args[4], args[5] if len(args) > 5 else 0.0
            half_w, half_h, tilt = w / 2, h / 2, 0.0
        else:                                                        # lower-left line: exposure, width, height, x, y, rotation
            w, h, x, y, rot = args[1], args[2], args[3], args[4], args[5] if len(args) > 5 else 0.0
            cx, cy, half_w, half_h, tilt = x + w / 2, y + h / 2, w / 2, h / 2, 0.0
        a = math.radians(rot)
        gx, gy = cx * math.cos(a) - cy * math.sin(a), cx * math.sin(a) + cy * math.cos(a)

        def inside(u, v):
            """!@brief Oriented rectangle test. @param u X. @param v Y. @return Boolean array."""
            p, q = _rot(u - gx, v - gy, math.degrees(tilt) + rot)
            return (np.abs(p) <= half_w) & (np.abs(q) <= half_h)
        return {"exposure": exp, "radius": math.hypot(gx, gy) + math.hypot(half_w, half_h), "inside": inside}
    if code == 4:                                                    # outline: exposure, n, x0, y0, x1, y1, ..., xn, yn, rotation
        n = int(args[1])
        pts = [(args[2 + 2 * i], args[3 + 2 * i]) for i in range(n + 1)]
        rot = args[2 + 2 * (n + 1)]
        return {"exposure": exp, "radius": max(math.hypot(x, y) for x, y in pts), "inside": lambda u, v: _in_polygon(*_rot(u, v, rot), pts)}
    if code == 5:                                                    # polygon: exposure, vertices, cx, cy, diameter, rotation
        n, cx, cy, d = int(args[1]), args[2], args[3], args[4]
        rot = args[5] if len(args) > 5 else 0.0
        a = math.radians(rot)                                        # the rotation is about the macro origin, so the centre turns too (it turned about its own centre before)
        cx, cy = cx * math.cos(a) - cy * math.sin(a), cx * math.sin(a) + cy * math.cos(a)
        return {"exposure": exp, "radius": math.hypot(cx, cy) + d / 2, "inside": lambda u, v: _regular_polygon(u - cx, v - cy, d / 2, n, rot)}
    if code == 7:                                                    # thermal: cx, cy, outer diameter, inner diameter, gap, rotation
        cx, cy, od, idia, gap = args[0], args[1], args[2], args[3], args[4]
        rot = args[5] if len(args) > 5 else 0.0
        a = math.radians(rot)                                        # rotation about the macro origin: the centre turns with it
        cx, cy = cx * math.cos(a) - cy * math.sin(a), cx * math.sin(a) + cy * math.cos(a)

        def inside(u, v):
            """!@brief Ring with two crossing gaps. @param u X. @param v Y. @return Boolean array."""
            p, q = _rot(u - cx, v - cy, rot)
            rho2 = p * p + q * q
            return (rho2 <= (od / 2) ** 2) & (rho2 >= (idia / 2) ** 2) & (np.abs(p) >= gap / 2) & (np.abs(q) >= gap / 2)
        return {"exposure": True, "radius": math.hypot(cx, cy) + od / 2, "inside": inside}
    raise NotImplementedError(f"aperture macro primitive {code} is not supported")


def _in_polygon(u, v, pts):
    """!
    @brief Points inside a polygon (even-odd rule), for macro outlines.
    @param u X coordinates (any shape).
    @param v Y coordinates.
    @param pts List of vertices (x, y).
    @return Boolean array.
    """
    inside = np.zeros(u.shape, bool)
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        if y0 == y1:
            continue
        cross = ((y0 <= v) != (y1 <= v)) & (u < x0 + (v - y0) * (x1 - x0) / (y1 - y0))
        inside ^= cross
    return inside


# --------------------------------------------------------------------------------------------------------------------------------
# Rasteriser
# --------------------------------------------------------------------------------------------------------------------------------

class Canvas:
    """!@brief A boolean mask of a window of the board that objects are drawn onto (dark adds, clear removes)."""

    def __init__(self, x_left, y_top, width_mm, height_mm, pix_mm):
        """!
        @brief Create an empty canvas.
        @param x_left X of the left edge of the window (mm).
        @param y_top Y of the top edge of the window (mm).
        @param width_mm Window width (mm).
        @param height_mm Window height (mm).
        @param pix_mm Pixel size (mm).
        """
        self.x0, self.y0, self.pix = x_left, y_top, pix_mm
        self.nx, self.ny = int(round(width_mm / pix_mm)), int(round(height_mm / pix_mm))
        self.mask = np.zeros((self.ny, self.nx), bool)

    def _window(self, xmin, xmax, ymin, ymax):
        """!
        @brief Pixel index ranges and centre coordinates of a bounding box clipped to the canvas.
        @param xmin Left of the box (mm).
        @param xmax Right of the box.
        @param ymin Bottom of the box.
        @param ymax Top of the box.
        @return None when the box is outside, else (row slice, column slice, X centres, Y centres) with X, Y as 2D arrays.
        """
        j0 = max(int(math.floor((xmin - self.x0) / self.pix - 0.5)), 0)
        j1 = min(int(math.ceil((xmax - self.x0) / self.pix - 0.5)) + 1, self.nx)
        i0 = max(int(math.floor((self.y0 - ymax) / self.pix - 0.5)), 0)
        i1 = min(int(math.ceil((self.y0 - ymin) / self.pix - 0.5)) + 1, self.ny)
        if j0 >= j1 or i0 >= i1:
            return None
        xs = self.x0 + (np.arange(j0, j1) + 0.5) * self.pix
        ys = self.y0 - (np.arange(i0, i1) + 0.5) * self.pix
        X, Y = np.meshgrid(xs, ys)
        return slice(i0, i1), slice(j0, j1), X, Y

    def _apply(self, sl, inside, dark):
        """!
        @brief Add or remove the pixels of a shape.
        @param sl Tuple (row slice, column slice).
        @param inside Boolean array of the shape on that window.
        @param dark True to add copper, False to clear.
        @return None.
        """
        view = self.mask[sl[0], sl[1]]
        if dark:
            view |= inside
        else:
            view &= ~inside

    def flash(self, ap, x, y, dark):
        """!
        @brief Draw an aperture at a point.
        @param ap Aperture.
        @param x X (mm).
        @param y Y (mm).
        @param dark Polarity.
        @return None.
        """
        r = ap.radius
        w = self._window(x - r, x + r, y - r, y + r)
        if w:
            self._apply(w[:2], ap.inside(w[2] - x, w[3] - y), dark)

    def stroke(self, ap, x0, y0, x1, y1, dark):
        """!
        @brief Draw a straight line with an aperture (round aperture: a capsule; rectangular aperture: the convex hull of its two positions).
        @param ap Aperture.
        @param x0 Start X (mm).
        @param y0 Start Y (mm).
        @param x1 End X (mm).
        @param y1 End Y (mm).
        @param dark Polarity.
        @return None.
        """
        r = ap.radius
        w = self._window(min(x0, x1) - r, max(x0, x1) + r, min(y0, y1) - r, max(y0, y1) + r)
        if not w:
            return
        X, Y = w[2], w[3]
        if ap.kind == "C":
            dx, dy = x1 - x0, y1 - y0
            L2 = dx * dx + dy * dy
            t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L2, 0.0, 1.0) if L2 > 0 else np.zeros_like(X)
            inside = (X - (x0 + t * dx)) ** 2 + (Y - (y0 + t * dy)) ** 2 <= r * r
        else:
            # Convex hull of the aperture at both ends: a point is inside if some point of the segment's aperture covers it; sample the segment densely
            n = max(int(math.hypot(x1 - x0, y1 - y0) / (self.pix * 0.5)) + 1, 2)
            inside = np.zeros(X.shape, bool)
            for s in np.linspace(0.0, 1.0, n):
                inside |= ap.inside(X - (x0 + s * (x1 - x0)), Y - (y0 + s * (y1 - y0)))
        self._apply(w[:2], inside, dark)

    def polygon(self, pts, dark):
        """!
        @brief Fill a closed polygon (even-odd rule, which equals the non-zero rule for the simple contours of a Gerber region).
        @param pts Array (n, 2) of vertices (mm).
        @param dark Polarity.
        @return None.
        """
        pts = np.asarray(pts, float)
        if len(pts) < 3:
            return
        w = self._window(pts[:, 0].min(), pts[:, 0].max(), pts[:, 1].min(), pts[:, 1].max())
        if not w:
            return
        rows, cols = w[0], w[1]
        nrow, ncol = rows.stop - rows.start, cols.stop - cols.start
        x_a, y_a = pts[:, 0], pts[:, 1]
        x_b, y_b = np.roll(x_a, -1), np.roll(y_a, -1)
        keep = y_a != y_b
        x_a, y_a, x_b, y_b = x_a[keep], y_a[keep], x_b[keep], y_b[keep]
        lo, hi = np.minimum(y_a, y_b), np.maximum(y_a, y_b)
        inside = np.zeros((nrow, ncol), bool)
        yc = self.y0 - (np.arange(rows.start, rows.stop) + 0.5) * self.pix
        for k in range(nrow):                                  # Scanline: crossings of the row centre with the edges, then fill between pairs
            sel = (lo <= yc[k]) & (yc[k] < hi)
            if not sel.any():
                continue
            xs = np.sort(x_a[sel] + (yc[k] - y_a[sel]) * (x_b[sel] - x_a[sel]) / (y_b[sel] - y_a[sel]))
            if len(xs) % 2:
                xs = xs[:-1]
            j = np.ceil((xs - self.x0) / self.pix - 0.5).astype(int) - cols.start        # first pixel centre at or right of every crossing
            j = np.clip(j, 0, ncol)
            diff = np.zeros(ncol + 1, int)
            np.add.at(diff, j[0::2], 1)
            np.add.at(diff, j[1::2], -1)
            inside[k] = np.cumsum(diff[:ncol]) > 0
        self._apply((rows, cols), inside, dark)


def _arc_points(x0, y0, x1, y1, cx, cy, clockwise, multi_quadrant=True):
    """!
    @brief Points along an arc from (x0, y0) to (x1, y1) around (cx, cy), cut so that the chord error stays below ARC_TOLERANCE.
    @param x0 Start X.
    @param y0 Start Y.
    @param x1 End X.
    @param y1 End Y.
    @param cx Centre X.
    @param cy Centre Y.
    @param clockwise Direction.
    @param multi_quadrant True in G75 mode (start equal to end is a full circle), False in G74 mode (start equal to end is an arc of zero length).
    @return List of (x, y) from the start (excluded) to the end (included).
    """
    r = 0.5 * (math.hypot(x0 - cx, y0 - cy) + math.hypot(x1 - cx, y1 - cy))
    a0, a1 = math.atan2(y0 - cy, x0 - cx), math.atan2(y1 - cy, x1 - cx)
    sweep = (a1 - a0) % (2 * math.pi)
    if clockwise:
        sweep = sweep - 2 * math.pi if sweep > 0 else sweep
    if math.hypot(x1 - x0, y1 - y0) < 1e-9:                              # Start equals end: a full circle in G75 mode, nothing to sweep in G74 mode
        if not multi_quadrant:
            return [(x1, y1)]
        sweep = -2 * math.pi if clockwise else 2 * math.pi
    step = 2 * math.acos(max(1 - ARC_TOLERANCE / max(r, 1e-9), 0.0)) if r > ARC_TOLERANCE else math.pi / 4
    n = max(int(math.ceil(abs(sweep) / max(step, 1e-3))), 1)
    pts = [(cx + r * math.cos(a0 + sweep * k / n), cy + r * math.sin(a0 + sweep * k / n)) for k in range(1, n)]
    return pts + [(x1, y1)]


def _single_quadrant_centre(x0, y0, x1, y1, i, j, clockwise):
    """!
    @brief Centre of an arc in the obsolete single-quadrant mode (G74), where the offsets I and J are unsigned: the sign pair that gives equal radii and a sweep of at most 90 degrees.
    @param x0 Start X.
    @param y0 Start Y.
    @param x1 End X.
    @param y1 End Y.
    @param i Unsigned offset along x.
    @param j Unsigned offset along y.
    @param clockwise Direction.
    @return Tuple (cx, cy).
    """
    best = None
    for si in (1, -1):
        for sj in (1, -1):
            cx, cy = x0 + si * abs(i), y0 + sj * abs(j)
            err = abs(math.hypot(x0 - cx, y0 - cy) - math.hypot(x1 - cx, y1 - cy))
            a0, a1 = math.atan2(y0 - cy, x0 - cx), math.atan2(y1 - cy, x1 - cx)
            sweep = (a1 - a0) % (2 * math.pi)
            if clockwise:
                sweep = 2 * math.pi - sweep if sweep > 0 else 0.0
            score = err + (1.0 if sweep > math.pi / 2 + 1e-6 else 0.0)
            if best is None or score < best[0]:
                best = (score, cx, cy)
    return best[1], best[2]


class Layer:
    """!@brief A parsed Gerber layer: the list of drawing operations in file order, in mm, ready to be drawn on any canvas."""

    def __init__(self, text):
        """!
        @brief Parse the content of a Gerber file.
        @param text File content.
        @throws NotImplementedError For features this reader does not support.
        @throws GerberError For a file that cannot be understood.
        """
        self.ops = []                  # (kind, dark, args): kind "flash", "stroke", "region"
        self.nets = []                 # net name (or None) of every operation, from the X2 object attribute TO.N (KiCad, Altium, ... write it); same length as ops
        self._net = None
        self._aper_func = ""
        self._last_d = 1               # a coordinate block without a D code repeats the previous one
        self.negative = False
        self.attributes = {}           # X2 file attributes, for example {"FileFunction": ["Copper", "L1", "Top"]}
        self.apertures = {}
        self._parse(text)

    def _parse(self, text):
        """!
        @brief Run through the blocks and build the operation list.
        @param text File content.
        @return None.
        """
        unit = 1.0
        fmt = (2, 4, "L")
        macros = {}
        blocks = _blocks(text)
        dark = True
        ap = None
        x = y = 0.0
        mode, quad_multi = "G01", True
        in_region, contour = False, []
        sr = None                                                         # (nx, ny, dx, dy, start index in ops) while a step and repeat is open
        for kind, body in blocks:
            if kind == "ext":
                for cmd in [c.strip() for c in body.split("*") if c.strip()]:
                    if cmd.startswith("FS"):
                        m = re.match(r"FS([LTD]?)([AI])X(\d)(\d)Y(\d)(\d)", cmd)
                        if not m:
                            raise GerberError(f"bad format statement {cmd}")
                        fmt = (int(m.group(3)), int(m.group(4)), "T" if m.group(1) == "T" else "L")
                        if m.group(2) == "I":
                            raise NotImplementedError("incremental coordinates")
                    elif cmd.startswith("MO"):
                        unit = 25.4 if cmd[2:4] == "IN" else 1.0
                    elif cmd.startswith("ADD"):
                        m = re.match(r"ADD(\d+)([A-Za-z_][\w.$]*)(?:,(.*))?", cmd)
                        num, name, par = int(m.group(1)), m.group(2), m.group(3) or ""
                        vals = [float(v) for v in re.split(r"[xX]", par)] if par and name in "CROP" and len(name) == 1 else []
                        if name in ("C", "R", "O", "P"):
                            if name == "P" and len(vals) < 2:
                                raise GerberError("polygon aperture needs a diameter and a number of vertices")
                            self.apertures[num] = Aperture(name, [v * unit if (name != "P" or k in (0, 3)) else v for k, v in enumerate(vals)])
                            self.apertures[num].func = self._aper_func
                        elif name in macros:
                            args = [float(v) for v in re.split(r"[xX]", par)] if par else []
                            self.apertures[num] = Aperture("M", [], [q for q in (_macro_primitive(*pr) for pr in macros[name](args, unit)) if q])
                            self.apertures[num].func = self._aper_func
                        else:
                            # Some CAD tools (Upverter) write their own shapes such as "Rect-W..-H..": reported as unsupported, not as a broken file
                            raise NotImplementedError(f"aperture shape {name} (non-standard) is not supported")
                    elif cmd.startswith("AM"):
                        # The macro body follows in the same extended command: statements separated by *
                        parts = [c.strip() for c in body.split("*") if c.strip()]
                        name = parts[0][2:]
                        macros[name] = self._macro(parts[1:])
                        break
                    elif cmd.startswith("LP"):
                        dark = cmd[2] == "D"
                    elif cmd.startswith("IPNEG"):
                        self.negative = True
                    elif cmd.startswith("TO.N"):                                      # object attribute: the net of the objects that follow
                        names = [v.strip() for v in cmd[5:].split(",") if v.strip()]
                        self._net = names[0] if names else None
                    elif cmd.startswith("TA.AperFunction"):                          # aperture attribute: applies to the apertures defined after it
                        self._aper_func = cmd[len("TA.AperFunction,"):].strip()
                    elif cmd == "TD" or cmd.startswith("TD.N") or cmd.startswith("TD.AperFunction"):   # delete attributes (all, the net, or the aperture function)
                        if cmd == "TD" or cmd.startswith("TD.N"):
                            self._net = None
                        if cmd == "TD" or cmd.startswith("TD.AperFunction"):
                            self._aper_func = ""
                    elif cmd.startswith("TF."):                                      # X2 file attributes: FileFunction, FilePolarity, ...
                        key, _, val = cmd[3:].partition(",")
                        self.attributes[key] = [v.strip() for v in val.split(",")]
                    elif cmd.startswith("SR"):
                        if sr:                                              # close the previous step and repeat
                            self._close_sr(sr)
                            sr = None
                        m = re.match(r"SR(?:X(\d+))?(?:Y(\d+))?(?:I([-\d.]+))?(?:J([-\d.]+))?", cmd)
                        if m and m.group(1) and (int(m.group(1)) > 1 or int(m.group(2) or 1) > 1):
                            sr = (int(m.group(1)), int(m.group(2) or 1), float(m.group(3) or 0) * unit, float(m.group(4) or 0) * unit, len(self.ops))
                    elif cmd.startswith("AS") and cmd[2:6] != "AXBY":
                        raise NotImplementedError(f"{cmd} (axis select that swaps the axes, deprecated) is not supported")
                    elif cmd.startswith(("AB", "LM", "LR", "LS")):
                        raise NotImplementedError(f"{cmd[:2]} (aperture blocks and transformed apertures) is not supported")
                    elif cmd.startswith("OF") and any(abs(float(v)) > 0 for v in re.findall(r"[-\d.]+", cmd[2:])):
                        raise NotImplementedError(f"{cmd} (image offset) is not supported")
                    elif cmd.startswith("MI") and "1" in cmd[2:]:
                        raise NotImplementedError(f"{cmd} (image mirror) is not supported")
                    elif cmd.startswith("SF") and any(abs(float(v) - 1.0) > 1e-9 for v in re.findall(r"[-\d.]+", cmd[2:])):
                        raise NotImplementedError(f"{cmd} (image scale) is not supported")
                    elif cmd.startswith("IR") and any(abs(float(v)) > 0 for v in re.findall(r"[-\d.]+", cmd[2:])):
                        raise NotImplementedError(f"{cmd} (image rotation) is not supported")
                continue
            if body.startswith("G04"):
                continue
            words = re.findall(r"([GDMXYIJ])\s*([-+]?[\d.]+)", body)
            nx_, ny_ = None, None
            ii = jj = 0.0
            op = None
            for letter, val in words:
                if letter == "G":
                    g = int(float(val))
                    if g in (1, 2, 3):
                        mode = f"G0{g}"
                    elif g == 70:
                        unit = 25.4
                    elif g == 71:
                        unit = 1.0
                    elif g == 91:                                          # incremental coordinates (deprecated): refused, as the FS statement with I is
                        raise NotImplementedError("incremental coordinates (G91)")
                    elif g == 74:
                        quad_multi = False
                    elif g == 75:
                        quad_multi = True
                    elif g == 36:
                        in_region, contour = True, []
                        region_start = (x, y)
                    elif g == 37:
                        if contour:
                            self._add(("region", dark, np.array(contour)))
                        in_region, contour = False, []
                        mode = "G01"                                       # a region may end in a G03 arc; the next one starts straight (as other readers do)
                elif letter == "X":
                    nx_ = _number(val, *fmt) * unit
                elif letter == "Y":
                    ny_ = _number(val, *fmt) * unit
                elif letter == "I":
                    ii = _number(val, *fmt) * unit
                elif letter == "J":
                    jj = _number(val, *fmt) * unit
                elif letter == "D":
                    d = int(float(val))
                    if d >= 10:
                        ap = self.apertures.get(d)
                        if ap is None and not in_region:
                            raise GerberError(f"aperture D{d} is used before it is defined")
                    else:
                        op = d
                elif letter == "M" and int(float(val)) == 2:
                    op = "end"
            if op == "end":
                break
            nx2 = x if nx_ is None else nx_
            ny2 = y if ny_ is None else ny_
            if op is None and (nx_ is not None or ny_ is not None):
                op = self._last_d                                              # a coordinate without a D code repeats the previous one (modal)
            if op in (1, 2, 3):
                self._last_d = op
            if op == 2:                                                       # move
                if in_region and contour:
                    self._add(("region", dark, np.array(contour)))
                    contour = []
                x, y = nx2, ny2
                if in_region:
                    contour = [(x, y)]
            elif op == 1:                                                     # draw
                if mode == "G01":
                    pts = [(nx2, ny2)]
                else:
                    cw = mode == "G02"
                    if quad_multi:
                        cx, cy = x + ii, y + jj
                    else:
                        cx, cy = _single_quadrant_centre(x, y, nx2, ny2, ii, jj, cw)
                    pts = _arc_points(x, y, nx2, ny2, cx, cy, cw, quad_multi)
                if in_region:
                    if not contour:
                        contour = [(x, y)]
                    contour.extend(pts)
                else:
                    px, py = x, y
                    for qx, qy in pts:
                        self._add(("stroke", dark, (ap, px, py, qx, qy)))
                        px, py = qx, qy
                x, y = nx2, ny2
            elif op == 3:                                                     # flash
                x, y = nx2, ny2
                if ap is not None:
                    self._add(("flash", dark, (ap, x, y)))
            else:
                x, y = nx2, ny2
        if in_region and contour:
            self._add(("region", dark, np.array(contour)))
        if sr:
            self._close_sr(sr)

    @staticmethod
    def _macro(statements):
        """!
        @brief Compile the statements of an aperture macro into a function of the aperture parameters.
        @param statements List of statement strings (without the *).
        @return Function (args, unit) -> list of (code, evaluated numbers) with lengths in mm.
        """
        def build(args, unit):
            """!@brief Evaluate the macro for given parameters. @param args Parameters $1..$n. @param unit mm per file unit. @return List of (code, args)."""
            var = {i + 1: a for i, a in enumerate(args)}
            out = []
            for st in statements:
                if st.startswith("$"):                                       # variable definition $n=expression
                    n, ex = st.split("=", 1)
                    var[int(n[1:])] = _eval(ex, var)
                    continue
                if re.match(r"\s*0(\s|$)", st):                              # comment primitive "0 text" (no comma)
                    continue
                parts = st.split(",")
                code = int(parts[0])
                nums = [_eval(p, var) for p in parts[1:]] if code != 0 else []
                if code in (1, 20, 21, 22, 4, 5, 7, 6):
                    nums = _scale_macro(code, nums, unit)
                out.append((code, nums))
            return out
        return build

    def _close_sr(self, sr):
        """!
        @brief Replicate the operations drawn since an SR command over its grid of copies.
        @param sr Tuple (nx, ny, dx, dy, index of the first operation of the block).
        @return None.
        """
        nx, ny, dx, dy, start = sr
        block = self.ops[start:]
        block_nets = self.nets[start:]
        for i in range(nx):
            for j in range(ny):
                if i == 0 and j == 0:
                    continue
                for (kind, dark, a), net in zip(block, block_nets):
                    ox, oy = i * dx, j * dy
                    self._net = net
                    if kind == "flash":
                        self._add((kind, dark, (a[0], a[1] + ox, a[2] + oy)))
                    elif kind == "stroke":
                        self._add((kind, dark, (a[0], a[1] + ox, a[2] + oy, a[3] + ox, a[4] + oy)))
                    else:
                        self._add((kind, dark, a + np.array([ox, oy])))

    def _add(self, op):
        """!
        @brief Append an operation together with the net attribute that is active now.
        @param op Tuple (kind, dark, args).
        @return None.
        """
        self.ops.append(op)
        self.nets.append(self._net)

    def flashes(self):
        """!
        @brief The dark flashes (pads) of the layer with their position, size, aperture function and net.
        @return List of tuples (x mm, y mm, diameter mm (the circle that contains the pad), function string, net name or None).
        """
        out = []
        for (kind, dark, a), net in zip(self.ops, self.nets):
            if kind == "flash" and dark:
                out.append((a[1], a[2], 2.0 * a[0].radius, a[0].func, net))
        return out

    def net_names(self):
        """!
        @brief The nets named in the file (X2 object attribute TO.N), in order of appearance.
        @return List of names; empty when the file carries no net information.
        """
        return list(dict.fromkeys(n for n in self.nets if n))

    def draw(self, canvas, nets=None):
        """!
        @brief Draw every operation on a canvas, in file order.
        @details With `nets` only the dark operations of those nets are drawn; clear operations are always drawn (an approximation: a clear object removes copper of any net).
        @param canvas Canvas.
        @param nets Optional collection of net names to draw (None draws everything).
        @return None.
        """
        wanted = None if nets is None else set(nets)
        for (kind, dark, a), net in zip(self.ops, self.nets):
            if wanted is not None and dark and net not in wanted:
                continue
            if kind == "flash":
                canvas.flash(a[0], a[1], a[2], dark)
            elif kind == "stroke":
                canvas.stroke(a[0], a[1], a[2], a[3], a[4], dark)
            else:
                canvas.polygon(a, dark)
        if self.negative:                                                      # image polarity: negative
            canvas.mask = ~canvas.mask

    def bbox(self):
        """!
        @brief Bounding box of everything drawn (mm), including the half width of strokes.
        @return Tuple (x0, y0, x1, y1), or None for an empty layer.
        """
        xs, ys = [], []
        for kind, dark, a in self.ops:
            if kind == "flash":
                r = a[0].radius
                xs += [a[1] - r, a[1] + r]
                ys += [a[2] - r, a[2] + r]
            elif kind == "stroke":
                r = a[0].radius
                xs += [a[1] - r, a[3] + r, a[1] + r, a[3] - r]
                ys += [a[2] - r, a[4] + r, a[2] + r, a[4] - r]
            else:
                xs += list(a[:, 0])
                ys += list(a[:, 1])
        return (min(xs), min(ys), max(xs), max(ys)) if xs else None


def _scale_macro(code, nums, unit):
    """!
    @brief Convert the lengths of an evaluated macro primitive from file units to mm (angles, exposure and vertex counts stay).
    @param code Primitive code.
    @param nums Evaluated numbers.
    @param unit mm per file unit.
    @return New list.
    """
    n = list(nums)
    length_idx = {1: (1, 2, 3), 20: (1, 2, 3, 4, 5), 21: (1, 2, 3, 4), 22: (1, 2, 3, 4), 5: (2, 3, 4), 7: (0, 1, 2, 3, 4)}.get(code, ())
    if code == 4:
        length_idx = tuple(range(2, 2 + 2 * (int(n[1]) + 1)))
    for k in length_idx:
        if k < len(n):
            n[k] *= unit
    return n


def render(path, x_left, y_top, width_mm, height_mm, pix_mm):
    """!
    @brief Read a Gerber copper layer and draw it on a window of the board.
    @param path Gerber file path.
    @param x_left X of the left edge of the window (mm).
    @param y_top Y of the top edge of the window (mm).
    @param width_mm Window width (mm).
    @param height_mm Window height (mm).
    @param pix_mm Pixel size (mm).
    @return Boolean array (rows, cols), True = copper at the pixel centre.
    """
    layer = Layer(Path(path).read_text(errors="replace"))
    cv = Canvas(x_left, y_top, width_mm, height_mm, pix_mm)
    layer.draw(cv)
    return cv.mask


def render_coverage(layer, x_left, y_top, width_mm, height_mm, pix_mm, supersample=4):
    """!
    @brief Copper coverage of every pixel (0 to 1) by drawing at a finer pixel and averaging blocks of supersample x supersample sub-pixels.
    @details A binary mask loses or invents area on features thinner than about two pixels; the coverage keeps the area (a 0.05 mm track at a 0.1 mm pixel contributes half a pixel of copper).
    @param layer Parsed Layer (or the text of a Gerber file).
    @param x_left X of the left edge of the window (mm).
    @param y_top Y of the top edge of the window (mm).
    @param width_mm Window width (mm).
    @param height_mm Window height (mm).
    @param pix_mm Pixel size of the result (mm).
    @param supersample Sub-pixels per side (the drawing pixel is pix_mm / supersample).
    @return float array (rows, cols) with the copper fraction of each pixel.
    """
    if isinstance(layer, str):
        layer = Layer(layer)
    cv = Canvas(x_left, y_top, width_mm, height_mm, pix_mm / supersample)
    layer.draw(cv)
    ny, nx = cv.mask.shape[0] // supersample, cv.mask.shape[1] // supersample
    m = cv.mask[:ny * supersample, :nx * supersample].reshape(ny, supersample, nx, supersample)
    return m.mean(axis=(1, 3))


def layer_bbox(path):
    """!
    @brief Bounding box of everything drawn in a Gerber file (the board outline layer gives the board box).
    @param path Gerber file path.
    @return Tuple (x0, y0, x1, y1) in mm, or None.
    """
    return Layer(Path(path).read_text(errors="replace")).bbox()


# --------------------------------------------------------------------------------------------------------------------------------
# Which layer is this file?
# --------------------------------------------------------------------------------------------------------------------------------

_NAME_RULES = [                       # (regex on the lower-case file name, role)
    (r"(f[._]cu|\.gtl$|\.cmp$|top[_ .-]?(layer|copper)|copper[_-]top|(^|[_-])top\.(gbr|art|ger)$|l1[_.-]?(primary|top))", "top"),
    (r"(b[._]cu|\.gbl$|\.sol$|bottom[_ .-]?(layer|copper)|copper[_-]bottom|(^|[_-])bottom\.(gbr|art|ger)$|secondary)", "bottom"),
    (r"(in(\d+)[._]cu|\.g(\d+)$|inner|copper[_-]inner|gnd|vcc|pwr|power|layer[_-]?\d)", "inner"),
    (r"(edge[._]cuts|\.gko$|\.gm1$|outline|profile|boardoutline)", "outline"),
    (r"(\.drl$|\.xln$|\.exc$|drill|ncdrill)", "drill"),
]


def classify(path):
    """!
    @brief Guess what a Gerber or Excellon file is: from the X2 file function when it has one, else from the file name.
    @details Returns ("copper", position, index) for a copper layer (position "top", "bottom" or "inner"; index 1-based from the X2 attribute when known),
             ("outline", None, None), ("drill", None, None) or (None, None, None) for silk, mask, paste and anything unknown. The guess is only a default for
             the layer-assignment dialog: the user confirms it.
    @param path File path.
    @return Tuple (role, position, index).
    """
    p = Path(path)
    name = p.name.lower()
    if p.suffix.lower() in (".gbr", ".ger", ".art", ".gtl", ".gbl", ".gko", ".gm1", ".gts", ".gbs", ".gto", ".gbo", ".gtp", ".gbp", ".pho", ".gdo", ".cmp", ".sol", ""):
        try:
            head = _attributes_as_commands(p.read_text(errors="replace")[:4000])
        except OSError:
            head = ""
        m = re.search(r"%TF\.FileFunction,([^*%]*)", head)
        if m:
            f = [v.strip() for v in m.group(1).split(",")]
            if f[0] == "Copper" and len(f) >= 3:
                idx = int(re.sub(r"\D", "", f[1]) or 0)
                return "copper", f[2].lower() if f[2].lower() in ("top", "bot", "inr") else None, idx
            if f[0] == "Profile":
                return "outline", None, None
            return None, None, None                                      # soldermask, legend, paste, ...
    if re.search(r"(mask|silk|paste|legend|assy|adhes|fab|\.gts|\.gbs|\.gto|\.gbo|\.gtp|\.gbp)", name):
        return None, None, None
    for pattern, role in _NAME_RULES:
        if re.search(pattern, name):
            if role == "outline":
                return "outline", None, None
            if role == "drill":
                return "drill", None, None
            return "copper", role, None
    return None, None, None


# --------------------------------------------------------------------------------------------------------------------------------
# Excellon
# --------------------------------------------------------------------------------------------------------------------------------

def drill_function(path):
    """!
    @brief The X2 file function of an Excellon file, written by KiCad (and others) in a comment: `; #@! TF.FileFunction,Plated,1,4,PTH`.
    @param path Excellon file.
    @return Tuple (plated True/False/None when the file does not say, first copper layer or None, last copper layer or None).
    """
    for line in Path(path).read_text(errors="replace").splitlines()[:40]:
        m = re.match(r";\s*#@!\s*TF\.FileFunction,([^,*]+)(?:,(\d+),(\d+))?", line.strip())
        if m:
            kind = m.group(1)
            plated = True if kind == "Plated" else False if kind == "NonPlated" else None
            return plated, (int(m.group(2)) if m.group(2) else None), (int(m.group(3)) if m.group(3) else None)
    return None, None, None


def read_drill(path):
    """!
    @brief Read the drilled holes of an Excellon file (and the tool sizes that some CAD tools only write in comments).
    @details Handles METRIC and INCH headers (default formats 3.3 and 2.4), leading or trailing zero suppression, explicit decimal points, tool definitions
             (T01C0.8) and the comment form ";T01 Holesize 1. = 12.000000 ... PLATED MILS". A routed slot (G00 ... M15 ... G01 ... M16) becomes one hole at the middle of every segment
             (a routed arc G02/G03 at the middle of its chord), a canned slot X..Y..G85X..Y.. one hole at its middle; the repeat command R<n>X..Y.. is expanded.
             Not read: incremental mode (ICI, G91), the pattern commands (M25, M01, M02 with offsets) and the canned circles and text.
    @param path Excellon file path.
    @return List of tuples (x mm, y mm, diameter mm, plated bool or None when the file does not say).
    """
    text = Path(path).read_text(errors="replace")
    file_plated = drill_function(path)[0]                                       # from the X2 comment, used for the holes whose tool says nothing
    unit, zeros, ndec, nint = None, "L", None, None
    sizes, plated = {}, {}
    holes = []
    tool = None
    in_header = True
    slot_start = None
    cur_g = None                                                              # routing mode: "0" (move), "1" (cut) or None (drill hits)
    last = (0.0, 0.0)
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(";"):
            ff = re.match(r";\s*FILE_FORMAT\s*=\s*(\d+):(\d+)", line)
            if ff:                                                          # P-CAD, Altium: the format as a comment (integer:decimal digits)
                nint, ndec = int(ff.group(1)), int(ff.group(2))
            m = re.match(r";\s*T(\d+)\s+Holesize\s+\d+\.\s*=\s*([\d.]+)", line)
            if m:
                u = re.search(r"\b(MILS|MM|INCH)\b", line)
                t, d = int(m.group(1)), float(m.group(2))
                sizes[t] = d * (0.0254 if u and u.group(1) == "MILS" else 25.4 if u and u.group(1) == "INCH" else 1.0)
                plated[t] = None if "PLATED" not in line else ("NON_PLATED" not in line)
            continue
        if line.upper().startswith(("METRIC", "INCH")):
            unit = 25.4 if line.upper().startswith("INCH") else 1.0
            # Excellon names the zeros that are KEPT (LZ = leading zeros kept, trailing omitted; TZ = trailing zeros kept, leading omitted), the opposite of the Gerber FS wording
            zeros = "L" if "TZ" in line.upper() else "T" if "LZ" in line.upper() else zeros
            m = re.search(r"(0+)\.(0+)", line) or re.search(r"(\d)[.:](\d)", line)   # "000.000" (digits before and after the point) or "3.3"
            if m:
                nint, ndec = (len(m.group(1)), len(m.group(2))) if m.group(1).startswith("0") and len(m.group(1)) + len(m.group(2)) > 2 else (int(m.group(1)), int(m.group(2)))
            continue
        if line in ("M71", "M72"):                                          # the unit as a code: M71 metric, M72 inch
            unit = 25.4 if line == "M72" else 1.0
            continue
        if line == "%" or line.startswith("M95"):
            in_header = False
            continue
        m = re.match(r"T(\d+)(.*)$", line)
        if m and not re.match(r"T\d+[XY]", line):
            tool = int(m.group(1))
            c = re.search(r"C([\d.]+)", m.group(2))                      # other parameters (F, S, B, H, Z) may precede the diameter
            if c:
                sizes[tool] = float(c.group(1)) * (unit or 1.0)
            continue
        rep = re.match(r"R(\d+)(?:X([-+]?[\d.]+))?(?:Y([-+]?[\d.]+))?$", line)
        if rep and holes and nint is not None:                              # repeat the last hole n more times with an offset (Allegro, Excellon "R" command)
            n = int(rep.group(1))
            ddx = _number(rep.group(2), nint, ndec, zeros) * unit if rep.group(2) else 0.0
            ddy = _number(rep.group(3), nint, ndec, zeros) * unit if rep.group(3) else 0.0
            hx, hy, hd, hp = holes[-1]
            for k in range(1, n + 1):
                holes.append((hx + k * ddx, hy + k * ddy, hd, hp))
            last = (hx + n * ddx, hy + n * ddy)
            continue
        if line in ("M16", "M17", "G05"):                                    # tool up / end of the route / back to drilling
            slot_start, cur_g = None, None
            continue
        g = re.match(r"G0([0-3])", line)
        if g:
            cur_g = "1" if g.group(1) in "23" else g.group(1)                # a routed arc (G02/G03) ends a segment like G01: one hole at the middle of its chord
        if g or line.startswith(("X", "Y")):
            if g and not in_header:                                           # a routed slot: G00 (start), M15 (tool down), G01 (end), M16 (tool up)
                line = line[3:]
            if unit is None:                                                  # no METRIC or INCH line: inch when the file talks about mils or inches (Allegro)
                if re.search(r"INCH|MILS", text.upper()):
                    unit = 25.4
                elif re.search(r"\bMM\b|METRIC", text.upper()):
                    unit = 1.0
                else:                                                         # no unit anywhere (a file without header): guessing would place the holes 25 times wrong
                    raise NotImplementedError("Excellon file without unit information (no METRIC, INCH, M71 or M72): the unit must be chosen by the user")
            if nint is None:
                nint, ndec = (2, 4) if unit == 25.4 else (3, 3)
            slot = re.match(r"(X[-+]?[\d.]+)?(Y[-+]?[\d.]+)?G85(X[-+]?[\d.]+)?(Y[-+]?[\d.]+)?$", line)
            if slot:                                                          # canned slot "X..Y..G85X..Y..": one hole at its middle (it was read as a hole at the start)
                def coord(word, prev):
                    """!@brief One coordinate of a slot line. @param word "X.." / "Y.." or None. @param prev Value kept when the word is missing. @return Value (mm)."""
                    return _number(word[1:], nint, ndec, zeros) * unit if word else prev
                sx, sy = coord(slot.group(1), last[0]), coord(slot.group(2), last[1])
                ex, ey = coord(slot.group(3), sx), coord(slot.group(4), sy)
                holes.append(((sx + ex) / 2, (sy + ey) / 2, sizes.get(tool, 0.0), plated.get(tool) if plated.get(tool) is not None else file_plated))
                last = (ex, ey)
                continue
            mx = re.search(r"X([-+]?[\d.]+)", line)
            my = re.search(r"Y([-+]?[\d.]+)", line)
            if not (mx or my):
                continue
            # A coordinate that is left out keeps its previous value (modal), as many CAD tools write repeated columns
            x = _number(mx.group(1), nint, ndec, zeros) * unit if mx else last[0]
            y = _number(my.group(1), nint, ndec, zeros) * unit if my else last[1]
            last = (x, y)
            if cur_g == "0":
                slot_start = (x, y)
            elif cur_g == "1":
                if slot_start is not None:                                    # one hole at the middle of every straight segment of the route (a slot has one, a path several)
                    holes.append(((slot_start[0] + x) / 2, (slot_start[1] + y) / 2, sizes.get(tool, 0.0), plated.get(tool) if plated.get(tool) is not None else file_plated))
                slot_start = (x, y)                                           # the route continues from here (modal G01 coordinates)
            else:
                holes.append((x, y, sizes.get(tool, 0.0), plated.get(tool) if plated.get(tool) is not None else file_plated))
    return holes
