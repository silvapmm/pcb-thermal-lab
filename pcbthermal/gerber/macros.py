#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file macros.py
@brief Apertures (standard shapes and aperture macros) as point-inclusion tests, and the arithmetic of aperture macros.
@details Written from the public Gerber layer format specification (Ucamco). An aperture answers "which of these points are inside" in its own
         coordinates (mm), which is all the rasteriser needs. Macro primitives supported: comment (0), circle (1), vector line (20), centre line (21),
         lower-left line (22), outline (4), polygon (5) and thermal (7), with variables ($n) and arithmetic (+ - x / and parentheses). The moire (6) and any
         unknown primitive are refused. Macro expressions are parsed by a small recursive-descent parser, never by eval.
"""

import math
import re

import numpy as np

from .errors import GerberError, UnsupportedFeatureError

_TOKEN = re.compile(r"\s*(?:(\d+\.?\d*|\.\d+)|\$(\d+)|([-+*/()xX]))")


def evaluate(expr, variables):
    """!
    @brief Evaluate an aperture-macro arithmetic expression.
    @param expr      Expression text ($n variables, numbers, + - x X * /, parentheses, unary signs).
    @param variables Dict variable number -> value (an undefined variable is zero).
    @return float Value of the expression.
    @throws GerberError If the expression contains anything else.
    """
    tokens, pos, text = [], 0, expr.strip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            raise GerberError(f"unsupported macro expression {expr!r}")
        if m.group(1) is not None:
            tokens.append(float(m.group(1)))
        elif m.group(2) is not None:
            tokens.append(float(variables.get(int(m.group(2)), 0.0)))
        else:
            tokens.append(m.group(3).lower().replace("x", "*"))
        pos = m.end()
        while pos < len(text) and text[pos] in " \t":
            pos += 1
    state = {"i": 0}

    def peek():
        """!@brief Next token without consuming it. @return Token or None."""
        return tokens[state["i"]] if state["i"] < len(tokens) else None

    def take():
        """!@brief Consume the next token. @return Token."""
        state["i"] += 1
        return tokens[state["i"] - 1]

    def factor():
        """!@brief Number, variable, parenthesis or a signed factor. @return float."""
        t = peek()
        if t is None:
            raise GerberError(f"unsupported macro expression {expr!r}")
        if t == "-":
            take()
            return -factor()
        if t == "+":
            take()
            return factor()
        if t == "(":
            take()
            v = add()
            if peek() != ")":
                raise GerberError(f"unbalanced parentheses in macro expression {expr!r}")
            take()
            return v
        if isinstance(t, float):
            return take()
        raise GerberError(f"unsupported macro expression {expr!r}")

    def mul():
        """!@brief Product and quotient level. @return float."""
        v = factor()
        while peek() in ("*", "/"):
            op = take()
            w = factor()
            v = v * w if op == "*" else (v / w if w != 0 else 0.0)        # a zero divisor gives 0 (the specification leaves it undefined)
        return v

    def add():
        """!@brief Sum and difference level. @return float."""
        v = mul()
        while peek() in ("+", "-"):
            op = take()
            w = mul()
            v = v + w if op == "+" else v - w
        return v

    value = add()
    if peek() is not None:
        raise GerberError(f"unsupported macro expression {expr!r}")
    return value


class Aperture:
    """!@brief One aperture: a standard shape or an aperture-macro instance, with the test "is this local point inside"."""

    def __init__(self, kind, params, macro=None):
        """!
        @brief Store the definition.
        @param kind   "C", "R", "O", "P" or "M" (macro).
        @param params List of floats (mm; the vertex count of a polygon and angles stay as written).
        @param macro  List of evaluated macro primitives (dicts) for kind "M".
        """
        self.kind, self.p, self.macro = kind, params, macro or []
        self.func = ""                 # X2 aperture function (TA.AperFunction), empty when the file has none
        # Radius of the circle around the origin that contains the aperture (bounding box of a flash)
        if kind == "C":
            self.radius = params[0] / 2
        elif kind in ("R", "O"):
            self.radius = math.hypot(params[0], params[1]) / 2
        elif kind == "P":
            self.radius = params[0] / 2
        else:
            self.radius = max([q["radius"] for q in self.macro] + [0.0])

    def min_dimension(self):
        """!
        @brief The smallest width of the aperture (the thinnest line it draws), used to choose the pixel.
        @return float Millimetres, or 0.0 when the aperture draws nothing or the width is not defined (macro).
        """
        if self.kind == "C":
            return self.p[0]
        if self.kind in ("R", "O"):
            return min(self.p[0], self.p[1])
        if self.kind == "P":
            return self.p[0] * math.cos(math.pi / max(int(self.p[1]), 3))
        return 0.0

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
            if w >= h:                                       # horizontal stadium: a segment of length w - h swept by a disc of diameter h
                d = np.maximum(np.abs(u) - (w - h) / 2, 0.0)
                m = d * d + v * v <= (h / 2) ** 2
            else:
                d = np.maximum(np.abs(v) - (h - w) / 2, 0.0)
                m = u * u + d * d <= (w / 2) ** 2
            hole = p[2] if len(p) > 2 else 0.0
            return m & ~(u * u + v * v < (hole / 2) ** 2) if hole > 0 else m
        if k == "P":
            m = regular_polygon(u, v, p[0] / 2, int(p[1]), p[2] if len(p) > 2 else 0.0)
            hole = p[3] if len(p) > 3 else 0.0
            return m & ~(u * u + v * v < (hole / 2) ** 2) if hole > 0 else m
        # Macro: the primitives apply in order; exposure on adds, exposure off removes (inside this aperture only)
        m = np.zeros(u.shape, bool)
        for q in self.macro:
            r = q["inside"](u, v)
            m = (m | r) if q["exposure"] else (m & ~r)
        return m


def regular_polygon(u, v, r, n, rot_deg):
    """!
    @brief Points inside a regular polygon with n vertices on a circle of radius r (first vertex at the rotation angle).
    @param u       X coordinates.
    @param v       Y coordinates.
    @param r       Circumscribed radius.
    @param n       Number of vertices.
    @param rot_deg Rotation in degrees.
    @return Boolean array.
    """
    a = math.radians(rot_deg)
    uu, vv = u * math.cos(a) + v * math.sin(a), -u * math.sin(a) + v * math.cos(a)
    sector = 2 * math.pi / n
    theta = np.mod(np.arctan2(vv, uu), sector)                       # angle measured from the previous vertex direction
    return np.hypot(uu, vv) * np.cos(theta - sector / 2) <= r * math.cos(math.pi / n)        # distance along the edge normal against the apothem


def rotate_points(u, v, deg):
    """!
    @brief Express points in a frame rotated by deg degrees (a counter-clockwise rotation of the shape is a clockwise rotation of the points).
    @param u   X coordinates.
    @param v   Y coordinates.
    @param deg Rotation of the shape in degrees.
    @return Tuple (u', v').
    """
    a = math.radians(deg)
    return u * math.cos(a) + v * math.sin(a), -u * math.sin(a) + v * math.cos(a)


def in_polygon(u, v, pts):
    """!
    @brief Points inside a polygon (even-odd rule), for macro outlines.
    @param u   X coordinates (any shape).
    @param v   Y coordinates.
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
        inside ^= ((y0 <= v) != (y1 <= v)) & (u < x0 + (v - y0) * (x1 - x0) / (y1 - y0))
    return inside


def macro_primitive(code, args, file=""):
    """!
    @brief Turn one evaluated aperture-macro primitive into a dict with its exposure, a bounding radius and an inside test.
    @param code Primitive code (0, 1, 4, 5, 7, 20, 21, 22).
    @param args List of evaluated numbers (lengths already in mm).
    @param file File name, for the refusal message.
    @return Dict {"exposure", "radius", "inside"}, or None for a comment.
    @throws UnsupportedFeatureError For the moire primitive (6) and unknown codes.
    """
    if code == 0:
        return None
    args = list(args) + [0.0] * 8                                    # a missing optional parameter (centre, rotation) is zero
    exp = bool(int(args[0])) if code != 7 else True
    if code == 1:                                                    # circle: exposure, diameter, cx, cy, [rotation]
        d, cx, cy, rot = args[1], args[2], args[3], args[4]
        a = math.radians(rot)                                        # the rotation is about the macro origin, so the centre turns too
        cx, cy = cx * math.cos(a) - cy * math.sin(a), cx * math.sin(a) + cy * math.cos(a)
        return {"exposure": exp, "radius": math.hypot(cx, cy) + d / 2, "inside": lambda u, v: (u - cx) ** 2 + (v - cy) ** 2 <= (d / 2) ** 2}
    if code in (20, 21, 22):
        if code == 20:                                               # vector line: exposure, width, x1, y1, x2, y2, rotation
            w, x1, y1, x2, y2, rot = args[1], args[2], args[3], args[4], args[5], args[6]
            cx, cy, ln, ang = (x1 + x2) / 2, (y1 + y2) / 2, math.hypot(x2 - x1, y2 - y1), math.atan2(y2 - y1, x2 - x1)
            half_w, half_h, tilt = ln / 2, w / 2, ang
        elif code == 21:                                             # centre line: exposure, width, height, cx, cy, rotation
            w, h, cx, cy, rot = args[1], args[2], args[3], args[4], args[5]
            half_w, half_h, tilt = w / 2, h / 2, 0.0
        else:                                                        # lower-left line: exposure, width, height, x, y, rotation
            w, h, x, y, rot = args[1], args[2], args[3], args[4], args[5]
            cx, cy, half_w, half_h, tilt = x + w / 2, y + h / 2, w / 2, h / 2, 0.0
        a = math.radians(rot)
        gx, gy = cx * math.cos(a) - cy * math.sin(a), cx * math.sin(a) + cy * math.cos(a)

        def inside(u, v):
            """!@brief Oriented rectangle test. @param u X. @param v Y. @return Boolean array."""
            p, q = rotate_points(u - gx, v - gy, math.degrees(tilt) + rot)
            return (np.abs(p) <= half_w) & (np.abs(q) <= half_h)
        return {"exposure": exp, "radius": math.hypot(gx, gy) + math.hypot(half_w, half_h), "inside": inside}
    if code == 4:                                                    # outline: exposure, n, x0, y0, x1, y1, ..., xn, yn, rotation
        n = int(args[1])
        pts = [(args[2 + 2 * i], args[3 + 2 * i]) for i in range(n + 1)]
        rot = args[2 + 2 * (n + 1)]
        return {"exposure": exp, "radius": max(math.hypot(x, y) for x, y in pts), "inside": lambda u, v: in_polygon(*rotate_points(u, v, rot), pts)}
    if code == 5:                                                    # polygon: exposure, vertices, cx, cy, diameter, rotation
        n, cx, cy, d, rot = int(args[1]), args[2], args[3], args[4], args[5]
        a = math.radians(rot)
        cx, cy = cx * math.cos(a) - cy * math.sin(a), cx * math.sin(a) + cy * math.cos(a)
        return {"exposure": exp, "radius": math.hypot(cx, cy) + d / 2, "inside": lambda u, v: regular_polygon(u - cx, v - cy, d / 2, n, rot)}
    if code == 7:                                                    # thermal: cx, cy, outer diameter, inner diameter, gap, rotation
        cx, cy, od, idia, gap, rot = args[0], args[1], args[2], args[3], args[4], args[5]
        a = math.radians(rot)
        cx, cy = cx * math.cos(a) - cy * math.sin(a), cx * math.sin(a) + cy * math.cos(a)

        def inside_thermal(u, v):
            """!@brief Ring with two crossing gaps. @param u X. @param v Y. @return Boolean array."""
            p, q = rotate_points(u - cx, v - cy, rot)
            rho2 = p * p + q * q
            return (rho2 <= (od / 2) ** 2) & (rho2 >= (idia / 2) ** 2) & (np.abs(p) >= gap / 2) & (np.abs(q) >= gap / 2)
        return {"exposure": True, "radius": math.hypot(cx, cy) + od / 2, "inside": inside_thermal}
    raise UnsupportedFeatureError(file, f"aperture macro primitive {code}" + (" (moire)" if code == 6 else ""))


def scale_macro(code, nums, unit):
    """!
    @brief Convert the lengths of an evaluated macro primitive from file units to mm (angles, exposure and vertex counts stay).
    @param code  Primitive code.
    @param nums  Evaluated numbers.
    @param unit  Millimetres per file unit.
    @return list The converted numbers.
    """
    n = list(nums)
    length_idx = {1: (1, 2, 3), 20: (1, 2, 3, 4, 5), 21: (1, 2, 3, 4), 22: (1, 2, 3, 4), 5: (2, 3, 4), 7: (0, 1, 2, 3, 4)}.get(code, ())
    if code == 4 and len(n) > 1:
        length_idx = tuple(range(2, 2 + 2 * (int(n[1]) + 1)))
    for k in length_idx:
        if k < len(n):
            n[k] *= unit
    return n
