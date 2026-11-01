#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file parser.py
@brief Gerber RS-274X (and X2 attributes) parser: a text file becomes a list of drawing operations in millimetres.
@details Written from the public Gerber layer format specification (Ucamco), with the research reader `research/gerber-import/lib/native_gerber.py` as the prototype.
         Supported: units (MO, G70/G71), coordinate formats (leading or trailing zero omission, X and Y formats apart), the standard apertures C, R, O and P with a hole,
         aperture macros (see macros.py), draws (D01) with circular apertures and with rectangular ones (the convex hull of the two flashes), flashes (D03), arcs
         (G02/G03 in single- and multi-quadrant mode, G74/G75), regions (G36/G37), dark and clear polarity (LPD/LPC), step and repeat (SR), image polarity (IPNEG) and
         the X2 attributes: the file attributes (TF) are kept in `Layer.attributes`, the aperture function (TA.AperFunction) in each aperture, and the object attributes are
         kept apart: net (TO.N), component reference (TO.C) and pin (TO.P) are three separate fields of every operation (the research rewrote TO.C into the net, which is
         safe only for a paste file; a copper file carries both).
         Refused with an `UnsupportedFeatureError` that names the file and the feature (the geometry would change if they were ignored): aperture blocks (AB), mirrored, rotated
         or scaled apertures (LM, LR, LS), the macro moire (6) and unknown primitives, non-standard aperture shapes, an image offset, mirror, scale or rotation (OF, MI, SF, IR),
         an axis select that swaps the axes (AS), and incremental coordinates (FS with I, G91). Deviation kept on purpose: G37 resets the interpolation mode to G01
         (the specification keeps it modal; the Ucamco test file example_level_holes needs the reset). Silently ignored: what does not draw (G54, IN, LN, M01, other attributes).
"""

import math
import re
from typing import NamedTuple, Optional

import numpy as np

from .errors import GerberError, UnsupportedFeatureError
from .macros import Aperture, evaluate, macro_primitive, scale_macro

ARC_TOLERANCE = 0.005          # mm, largest chord error when an arc is cut into straight pieces


class ObjectAttrs(NamedTuple):
    """!@brief The X2 object attributes of a drawing operation, kept apart: TO.N (net), TO.C (component reference), TO.P (reference and pin number)."""
    net: Optional[str]
    ref: Optional[str]
    pin: Optional[tuple]


class Flash(NamedTuple):
    """!@brief A dark flash (a pad): position, the diameter of the circle that contains it, aperture function and object attributes."""
    x: float
    y: float
    diameter: float
    function: str
    net: Optional[str]
    ref: Optional[str]
    pin: Optional[tuple]


def attributes_as_commands(text):
    """!
    @brief Turn attributes written as comments into extended commands.
    @details The specification allows the compatibility form `G04 #@! TF.FileFunction,Copper,L1,Top*` (an older reader ignores it as a comment); the attribute is
             rewritten as `%TF.FileFunction,Copper,L1,Top*%`.
    @param text File content.
    @return str Text with the attribute comments as extended commands.
    """
    return re.sub(r"G04\s+#@!\s+(T[FAOD][^*]*)\*", r"%\1*%", text)


def split_blocks(text):
    """!
    @brief Split a Gerber file into its blocks: extended commands (between % signs) and ordinary data blocks (ended by *).
    @param text File content.
    @return list Tuples (kind, text) with kind "ext" or "data".
    """
    out = []
    text = attributes_as_commands(text)
    # Some writers leave the star off a lone G code line ("G75"); without it the block would swallow the next command
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


def parse_number(s, nint, ndec, zeros):
    """!
    @brief Convert a coordinate string of a Gerber or Excellon file to a float in file units.
    @param s     String with an optional sign and digits (or a decimal point, as some generators write).
    @param nint  Integer digits of the format.
    @param ndec  Decimal digits of the format.
    @param zeros "L" (leading zeros omitted) or "T" (trailing zeros omitted).
    @return float Value in file units.
    """
    if "." in s:
        return float(s)
    sign = -1.0 if s.startswith("-") else 1.0
    digits = s.lstrip("+-")
    if zeros == "T":                                    # Trailing zeros omitted: pad on the right to the full width
        digits = digits.ljust(nint + ndec, "0")
    return sign * int(digits or "0") / (10 ** ndec)


def arc_points(x0, y0, x1, y1, cx, cy, clockwise, multi_quadrant=True):
    """!
    @brief Points along an arc from (x0, y0) to (x1, y1) around (cx, cy), cut so that the chord error stays below ARC_TOLERANCE.
    @param x0 Start X (mm).
    @param y0 Start Y (mm).
    @param x1 End X (mm).
    @param y1 End Y (mm).
    @param cx Centre X (mm).
    @param cy Centre Y (mm).
    @param clockwise      Direction.
    @param multi_quadrant True in G75 mode (start equal to end is a full circle), False in G74 mode (start equal to end is an arc of zero length).
    @return list (x, y) from the start (excluded) to the end (included).
    """
    r = 0.5 * (math.hypot(x0 - cx, y0 - cy) + math.hypot(x1 - cx, y1 - cy))
    a0, a1 = math.atan2(y0 - cy, x0 - cx), math.atan2(y1 - cy, x1 - cx)
    sweep = (a1 - a0) % (2 * math.pi)
    if clockwise:
        sweep = sweep - 2 * math.pi if sweep > 0 else sweep
    if math.hypot(x1 - x0, y1 - y0) < 1e-9:                              # Start equals end: a full circle in G75 mode, nothing in G74 mode
        if not multi_quadrant:
            return [(x1, y1)]
        sweep = -2 * math.pi if clockwise else 2 * math.pi
    step = 2 * math.acos(max(1 - ARC_TOLERANCE / max(r, 1e-9), 0.0)) if r > ARC_TOLERANCE else math.pi / 4
    n = max(int(math.ceil(abs(sweep) / max(step, 1e-3))), 1)
    pts = [(cx + r * math.cos(a0 + sweep * k / n), cy + r * math.sin(a0 + sweep * k / n)) for k in range(1, n)]
    return pts + [(x1, y1)]


def single_quadrant_centre(x0, y0, x1, y1, i, j, clockwise):
    """!
    @brief Centre of an arc in the obsolete single-quadrant mode (G74), where the offsets I and J are unsigned.
    @details The sign pair is chosen that gives equal radii at both ends and a sweep of at most 90 degrees.
    @param x0 Start X (mm).
    @param y0 Start Y (mm).
    @param x1 End X (mm).
    @param y1 End Y (mm).
    @param i  Unsigned offset along x (mm).
    @param j  Unsigned offset along y (mm).
    @param clockwise Direction.
    @return tuple (cx, cy) in mm.
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
    """!@brief A parsed Gerber layer: the drawing operations in file order, in mm, ready to be drawn on any window."""

    def __init__(self, text, name=""):
        """!
        @brief Parse the content of a Gerber file.
        @param text File content.
        @param name File name, used in the messages of refusals and errors.
        @throws UnsupportedFeatureError For a construct the reader refuses (file and feature named).
        @throws GerberError For a file that cannot be understood.
        """
        self.name = name
        self.ops = []                  # (kind, dark, args): kind "flash", "stroke" or "region"
        self.attr_ids = []             # index into attr_table for every operation (same length as ops)
        self.attr_table = [ObjectAttrs(None, None, None)]
        self._attr_index = {self.attr_table[0]: 0}
        self._net = self._ref = self._pin = None
        self._aper_func = ""
        self._last_d = 1               # a coordinate block without a D code repeats the previous one
        self.negative = False
        self.attributes = {}           # X2 file attributes, for example {"FileFunction": ["Copper", "L1", "Top"]}
        self.apertures = {}
        self._boxes = None
        self._parse(text)

    # ----------------------------------------------------------------------------------------------------------------------------
    # Parsing
    # ----------------------------------------------------------------------------------------------------------------------------

    def _refuse(self, feature):
        """!
        @brief Raise the refusal of a feature, naming the file.
        @param feature Description of the feature.
        @throws UnsupportedFeatureError Always.
        """
        raise UnsupportedFeatureError(self.name, feature)

    def _parse(self, text):
        """!
        @brief Run through the blocks and build the operation list.
        @param text File content.
        """
        st = {"unit": 1.0, "fmt_x": (2, 4, "L"), "fmt_y": (2, 4, "L"), "macros": {}, "dark": True, "sr": None}
        ap = None
        x = y = 0.0
        mode, quad_multi = "G01", True
        in_region, contour = False, []
        for kind, body in split_blocks(text):
            if kind == "ext":
                self._extended(body, st)
                continue
            if body.startswith("G04"):
                continue
            unit, dark = st["unit"], st["dark"]
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
                        st["unit"] = unit = 25.4
                    elif g == 71:
                        st["unit"] = unit = 1.0
                    elif g == 91:
                        self._refuse("incremental coordinates (G91)")
                    elif g == 74:
                        quad_multi = False
                    elif g == 75:
                        quad_multi = True
                    elif g == 36:
                        in_region, contour = True, []
                    elif g == 37:
                        if contour:
                            self._add(("region", dark, np.array(contour)))
                        in_region, contour = False, []
                        mode = "G01"                                       # a region may end in a G03 arc; the next one starts straight (as other readers do)
                elif letter == "X":
                    nx_ = parse_number(val, *st["fmt_x"]) * unit
                elif letter == "Y":
                    ny_ = parse_number(val, *st["fmt_y"]) * unit
                elif letter == "I":
                    ii = parse_number(val, *st["fmt_x"]) * unit
                elif letter == "J":
                    jj = parse_number(val, *st["fmt_y"]) * unit
                elif letter == "D":
                    d = int(float(val))
                    if d >= 10:
                        ap = self.apertures.get(d)
                        if ap is None and not in_region:
                            raise GerberError(f"{self.name}: aperture D{d} is used before it is defined")
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
                        cx, cy = single_quadrant_centre(x, y, nx2, ny2, ii, jj, cw)
                    pts = arc_points(x, y, nx2, ny2, cx, cy, cw, quad_multi)
                if in_region:
                    if not contour:
                        contour = [(x, y)]
                    contour.extend(pts)
                else:
                    if ap is None:
                        raise GerberError(f"{self.name}: a line is drawn before any aperture is selected")
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
            self._add(("region", st["dark"], np.array(contour)))
        if st["sr"]:
            self._close_sr(st["sr"])

    def _extended(self, body, st):
        """!
        @brief Execute one extended command (the text between two % signs, which may hold several statements).
        @param body Text of the command.
        @param st   Parser state (dict: unit, formats, macros, polarity, step and repeat).
        """
        parts = [c.strip() for c in body.split("*") if c.strip()]
        for cmd in parts:
            unit = st["unit"]
            if cmd.startswith("FS"):
                m = re.match(r"FS([LTD]?)([AI])X(\d)(\d)Y(\d)(\d)", cmd)
                if not m:
                    raise GerberError(f"{self.name}: bad format statement {cmd}")
                zeros = "T" if m.group(1) == "T" else "L"
                st["fmt_x"] = (int(m.group(3)), int(m.group(4)), zeros)
                st["fmt_y"] = (int(m.group(5)), int(m.group(6)), zeros)
                if m.group(2) == "I":
                    self._refuse("incremental coordinates (FS with I)")
            elif cmd.startswith("MO"):
                st["unit"] = 25.4 if cmd[2:4] == "IN" else 1.0
            elif cmd.startswith("ADD"):
                self._define_aperture(cmd, st)
            elif cmd.startswith("AM"):
                # The macro body follows in the same extended command: statements separated by *
                st["macros"][parts[0][2:]] = self._compile_macro(parts[1:])
                return
            elif cmd.startswith("LP"):
                st["dark"] = cmd[2] == "D"
            elif cmd.startswith("IPNEG"):
                self.negative = True
            elif cmd.startswith("TO."):
                self._object_attribute(cmd)
            elif cmd.startswith("TA.AperFunction"):                          # aperture attribute: applies to the apertures defined after it
                self._aper_func = cmd[len("TA.AperFunction,"):].strip()
            elif cmd.startswith("TD"):                                       # delete attributes: all, or one family
                what = cmd[3:] if cmd.startswith("TD.") else ""
                if what in ("", "N"):
                    self._net = None
                if what in ("", "C"):
                    self._ref = None
                if what in ("", "P"):
                    self._pin = None
                if what in ("", "AperFunction"):
                    self._aper_func = ""
            elif cmd.startswith("TF."):                                      # X2 file attributes: FileFunction, FilePolarity, ...
                key, _, val = cmd[3:].partition(",")
                self.attributes[key] = [v.strip() for v in val.split(",")]
            elif cmd.startswith("SR"):
                if st["sr"]:                                                 # close the previous step and repeat
                    self._close_sr(st["sr"])
                    st["sr"] = None
                m = re.match(r"SR(?:X(\d+))?(?:Y(\d+))?(?:I([-\d.]+))?(?:J([-\d.]+))?", cmd)
                if m and m.group(1) and (int(m.group(1)) > 1 or int(m.group(2) or 1) > 1):
                    st["sr"] = (int(m.group(1)), int(m.group(2) or 1), float(m.group(3) or 0) * unit, float(m.group(4) or 0) * unit, len(self.ops))
            elif cmd.startswith("AS") and cmd[2:6] != "AXBY":
                self._refuse(f"{cmd} (axis select that swaps the axes, deprecated)")
            elif cmd.startswith(("AB", "LM", "LR", "LS")):
                self._refuse(f"{cmd[:2]} (aperture blocks and transformed apertures)")
            elif cmd.startswith("OF") and any(abs(float(v)) > 0 for v in re.findall(r"[-\d.]+", cmd[2:])):
                self._refuse(f"{cmd} (image offset)")
            elif cmd.startswith("MI") and "1" in cmd[2:]:
                self._refuse(f"{cmd} (image mirror)")
            elif cmd.startswith("SF") and any(abs(float(v) - 1.0) > 1e-9 for v in re.findall(r"[-\d.]+", cmd[2:])):
                self._refuse(f"{cmd} (image scale)")
            elif cmd.startswith("IR") and any(abs(float(v)) > 0 for v in re.findall(r"[-\d.]+", cmd[2:])):
                self._refuse(f"{cmd} (image rotation)")

    def _define_aperture(self, cmd, st):
        """!
        @brief Execute an aperture definition (ADD).
        @param cmd Command text such as `ADD10C,0.25` or `ADD11THERM,1.5X0.8`.
        @param st  Parser state.
        """
        unit = st["unit"]
        m = re.match(r"ADD(\d+)([A-Za-z_][\w.$]*)(?:,(.*))?", cmd)
        if not m:
            raise GerberError(f"{self.name}: bad aperture definition {cmd}")
        num, name, par = int(m.group(1)), m.group(2), m.group(3) or ""
        if name in ("C", "R", "O", "P"):
            vals = [float(v) for v in re.split(r"[xX]", par)] if par else []
            if name == "P" and len(vals) < 2:
                raise GerberError(f"{self.name}: polygon aperture needs a diameter and a number of vertices")
            if (name == "C" and not vals) or (name in ("R", "O") and len(vals) < 2):
                raise GerberError(f"{self.name}: aperture {cmd} lacks its dimensions")
            aper = Aperture(name, [v * unit if (name != "P" or k in (0, 3)) else v for k, v in enumerate(vals)])
        elif name in st["macros"]:
            args = [float(v) for v in re.split(r"[xX]", par)] if par else []
            prims = [macro_primitive(code, nums, self.name) for code, nums in st["macros"][name](args, unit)]
            aper = Aperture("M", [], [q for q in prims if q])
        else:
            # Some CAD tools write their own shapes such as "Rect-W..-H..": a refusal, not a broken file
            self._refuse(f"aperture shape {name} (non-standard)")
        aper.func = self._aper_func
        self.apertures[num] = aper

    def _compile_macro(self, statements):
        """!
        @brief Compile the statements of an aperture macro into a function of the aperture parameters.
        @param statements List of statement strings (without the *).
        @return callable (args, unit) -> list of (code, evaluated numbers), lengths in mm.
        """
        def build(args, unit):
            """!@brief Evaluate the macro for given parameters. @param args Parameters $1..$n. @param unit mm per file unit. @return List of (code, args)."""
            var = {i + 1: a for i, a in enumerate(args)}
            out = []
            for stt in statements:
                if stt.startswith("$"):                                       # variable definition $n=expression
                    n, ex = stt.split("=", 1)
                    var[int(n[1:])] = evaluate(ex, var)
                    continue
                if re.match(r"\s*0(\s|$)", stt):                              # comment primitive "0 text" (no comma)
                    continue
                parts = stt.split(",")
                code = int(parts[0])
                nums = [evaluate(p, var) for p in parts[1:]]
                if code in (1, 20, 21, 22, 4, 5, 7, 6):
                    nums = scale_macro(code, nums, unit)
                out.append((code, nums))
            return out
        return build

    def _object_attribute(self, cmd):
        """!
        @brief Set an X2 object attribute: TO.N (net), TO.C (component reference) or TO.P (reference and pin). Others (TO.CRot, ...) are ignored.
        @param cmd Command text such as `TO.N,GND` or `TO.P,U1,3`.
        """
        key, _, val = cmd[3:].partition(",")
        vals = [v.strip() for v in val.split(",")]
        if key == "N":
            self._net = vals[0] if vals and vals[0] else None
        elif key == "C":
            self._ref = vals[0] if vals and vals[0] else None
        elif key == "P":
            self._pin = (vals[0], vals[1]) if len(vals) >= 2 else None

    def _close_sr(self, sr):
        """!
        @brief Replicate the operations drawn since an SR command over its grid of copies.
        @param sr Tuple (nx, ny, dx, dy, index of the first operation of the block).
        """
        nx, ny, dx, dy, start = sr
        block = self.ops[start:]
        block_attrs = self.attr_ids[start:]
        for i in range(nx):
            for j in range(ny):
                if i == 0 and j == 0:
                    continue
                for (kind, dark, a), aid in zip(block, block_attrs):
                    ox, oy = i * dx, j * dy
                    if kind == "flash":
                        op = (kind, dark, (a[0], a[1] + ox, a[2] + oy))
                    elif kind == "stroke":
                        op = (kind, dark, (a[0], a[1] + ox, a[2] + oy, a[3] + ox, a[4] + oy))
                    else:
                        op = (kind, dark, a + np.array([ox, oy]))
                    self.ops.append(op)
                    self.attr_ids.append(aid)

    def _add(self, op):
        """!
        @brief Append an operation together with the object attributes that are active now.
        @param op Tuple (kind, dark, args).
        """
        self.ops.append(op)
        key = ObjectAttrs(self._net, self._ref, self._pin)
        aid = self._attr_index.get(key)
        if aid is None:
            aid = self._attr_index[key] = len(self.attr_table)
            self.attr_table.append(key)
        self.attr_ids.append(aid)

    # ----------------------------------------------------------------------------------------------------------------------------
    # Queries
    # ----------------------------------------------------------------------------------------------------------------------------

    @property
    def file_function(self):
        """!
        @brief The X2 file function (TF.FileFunction) as a list, for example ["Copper", "L1", "Top"].
        @return list Empty when the file has none.
        """
        return list(self.attributes.get("FileFunction", []))

    def attrs(self, index):
        """!
        @brief The object attributes of one operation.
        @param index Index into `ops`.
        @return ObjectAttrs (net, ref, pin).
        """
        return self.attr_table[self.attr_ids[index]]

    def flashes(self):
        """!
        @brief The dark flashes (pads) of the layer with position, size, aperture function and the three object attributes.
        @return list of Flash.
        """
        out = []
        for (kind, dark, a), aid in zip(self.ops, self.attr_ids):
            if kind == "flash" and dark:
                t = self.attr_table[aid]
                out.append(Flash(a[1], a[2], 2.0 * a[0].radius, a[0].func, t.net, t.ref, t.pin))
        return out

    def net_names(self):
        """!
        @brief The nets named in the file (TO.N), in order of appearance.
        @return list of str; empty when the file carries none.
        """
        return list(dict.fromkeys(t.net for t in self.attr_table if t.net))

    def references(self):
        """!
        @brief The component references named in the file (TO.C), in order of appearance.
        @return list of str; empty when the file carries none.
        """
        return list(dict.fromkeys(t.ref for t in self.attr_table if t.ref))

    def op_boxes(self):
        """!
        @brief Bounding box of every operation, including the half width of strokes and the radius of flashes.
        @return numpy.ndarray Array (n, 4) of (xmin, ymin, xmax, ymax) in mm (cached).
        """
        if self._boxes is None:
            b = np.empty((len(self.ops), 4))
            for k, (kind, dark, a) in enumerate(self.ops):
                if kind == "flash":
                    r = a[0].radius
                    b[k] = (a[1] - r, a[2] - r, a[1] + r, a[2] + r)
                elif kind == "stroke":
                    r = a[0].radius
                    b[k] = (min(a[1], a[3]) - r, min(a[2], a[4]) - r, max(a[1], a[3]) + r, max(a[2], a[4]) + r)
                else:
                    b[k] = (a[:, 0].min(), a[:, 1].min(), a[:, 0].max(), a[:, 1].max())
            self._boxes = b
        return self._boxes

    def bbox(self):
        """!
        @brief Bounding box of everything drawn (mm).
        @return tuple (xmin, ymin, xmax, ymax), or None for an empty layer.
        """
        if not self.ops:
            return None
        b = self.op_boxes()
        return float(b[:, 0].min()), float(b[:, 1].min()), float(b[:, 2].max()), float(b[:, 3].max())

    def thinnest_feature_mm(self):
        """!
        @brief The smallest width among the dark lines and flashes of the layer, which sets the pixel the layer needs.
        @details Zero-size apertures (obsolete, still written for outlines) and macros (no single width) are not counted; regions have no width.
        @return float Millimetres, or None when the layer draws nothing with a width.
        """
        used = {}
        for kind, dark, a in self.ops:
            if dark and kind != "region":
                used[id(a[0])] = a[0]
        widths = [ap.min_dimension() for ap in used.values() if ap.min_dimension() > 0]
        return min(widths) if widths else None
