#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file x3_components.py
@brief Prototype of `pcbthermal/gerber/components.py`: the Gerber X3 component layer (`%TF.FileFunction,Component,L<p>,Top|Bot*%`) read into `Component` objects, and the heat-source shape taken from them.
@details Written from the Ucamco Gerber Layer Format Specification, revision 2026.05 (pages 157 and 158 for the aperture functions `ComponentMain`, `ComponentOutline,<type>`
         and `ComponentPin`, pages 165 to 167 for the object attributes `.C`, `.P`, `.CRot`, `.CVal`, `.CMnt`, `.CFtp`, `.CHgt`, ..., pages 179 to 181 for the data set and the annotated
         example), and independent of `lib/x3.py` (the regex reader of the earlier study) and of the program's reader `pcbthermal.gerber` (which keeps `.C`, `.N`, `.P` only and ignores `.Cxxx`).
         One small tokeniser: extended commands between `%`, function blocks ending in `*`; it follows the aperture function, the current aperture, the object attributes, the interpolation
         mode and the coordinate format. Lengths in mm (the file unit is converted, `.CHgt` too); angles in degrees, positive counter-clockwise seen from the top (page 166).
         Not read: step and repeat (`SR`), aperture macros (not used by the component layer), the block aperture `AB`; they are counted in `Component.notes` when met.
"""

import math
import re
from dataclasses import dataclass, field

## The outline types of the specification (page 157), in the order of preference for a heat-source shape (the body is the best, the courtyard the weakest of the four).
OUTLINE_TYPES = ("Body", "Lead2Lead", "Footprint", "Courtyard")


@dataclass
class Pin:
    """!@brief A pin of a component: number, optional net name, position in mm (board frame) and whether it is the key pin (the diamond aperture of the specification)."""
    number: str
    name: str
    x: float
    y: float
    key: bool = False


@dataclass
class Component:
    """!
    @brief One component of an X3 component layer.
    @details `outlines` maps the outline type (Body, Lead2Lead, Footprint, Courtyard) to a list of closed polylines (lists of (x, y) in mm, the last point equal to the first).
    """
    ref: str
    side: str = "top"                                       # "top" or "bottom", from the file function (Component,L<p>,Top|Bot)
    layer: int = 0                                          # p of Component,L<p>: the copper layer the part is attached to
    origin: tuple = None                                    # (x, y) mm of the ComponentMain flash (the centroid); None when missing
    rotation: float = 0.0                                   # .CRot, degrees, counter-clockwise seen from the top
    footprint: str = ""                                     # .CFtp
    value: str = ""                                         # .CVal
    mount: str = ""                                         # .CMnt: TH, SMD, Pressfit, Other
    height_mm: float = None                                 # .CHgt converted to mm; None when absent
    package: str = ""                                       # .CPgN
    manufacturer: str = ""                                  # .CMfr
    mpn: str = ""                                           # .CMPN
    library: str = ""                                       # .CLbN
    outlines: dict = field(default_factory=dict)
    pins: list = field(default_factory=list)
    notes: list = field(default_factory=list)               # things met and not handled

    def pin_points(self):
        """!
        @brief The pin positions.
        @return list of (x, y) in mm.
        """
        return [(p.x, p.y) for p in self.pins]


def _arc_points(p0, p1, ij, clockwise, step_deg=5.0):
    """!
    @brief Points of a multi-quadrant circular arc (G75) from p0 to p1 with the centre at p0 + (I, J).
    @param p0 Start (x, y).
    @param p1 End (x, y).
    @param ij Offsets (I, J) of the centre from the start.
    @param clockwise True for G02.
    @param step_deg Largest angle of a chord.
    @return list of (x, y) after the start point up to and including p1.
    """
    cx, cy = p0[0] + ij[0], p0[1] + ij[1]
    a0 = math.atan2(p0[1] - cy, p0[0] - cx)
    a1 = math.atan2(p1[1] - cy, p1[0] - cx)
    if clockwise:
        while a1 >= a0:
            a1 -= 2 * math.pi
    else:
        while a1 <= a0:
            a1 += 2 * math.pi
    r = math.hypot(p0[0] - cx, p0[1] - cy)
    n = max(1, int(math.ceil(abs(a1 - a0) / math.radians(step_deg))))
    pts = [(cx + r * math.cos(a0 + (a1 - a0) * k / n), cy + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(1, n)]
    pts.append(p1)
    return pts


def _num(token, ndec, scale):
    """!
    @brief A coordinate integer to mm (the format has no omitted zeros in the files of interest: FSLA with explicit digits, leading zeros omitted).
    @param token Text of the integer (sign allowed).
    @param ndec Digits after the decimal point of the format.
    @param scale mm per file unit.
    @return float.
    """
    return int(token) / (10 ** ndec) * scale


def parse(text, name=""):
    """!
    @brief Read the components of an X3 component layer.
    @param text Content of the file.
    @param name File name for the messages (unused otherwise).
    @return list of Component in file order (a part with the same reference twice is two entries: the check is `duplicate_references`).
    @throws ValueError If the file has no coordinate format statement.
    """
    fm = re.search(r"%FS[LT]?[AI]X(\d)(\d)Y(\d)(\d)\*%", text)
    if not fm:
        raise ValueError(f"{name}: no format statement (FS)")
    ndx, ndy = int(fm.group(2)), int(fm.group(4))
    unit = re.search(r"%MO(MM|IN)\*%", text)
    scale = 25.4 if unit and unit.group(1) == "IN" else 1.0
    ff = re.search(r"%TF\.FileFunction,Component,L(\d+),(Top|Bot)\*%", text)
    layer_no = int(ff.group(1)) if ff else 0
    side = "bottom" if ff and ff.group(2) == "Bot" else "top"
    # Tokens: extended commands (% ... %) and ordinary blocks (... *), in file order
    toks = re.findall(r"%([^%]*)%|([^%*]*)\*", text)
    ap_func = {}                                            # aperture number -> function string (TA.AperFunction active at its definition)
    ap_shape = {}                                           # aperture number -> the %ADD text
    cur_func = ""
    cur_ap = None
    attr = {}                                               # active TO attributes
    comps = {}                                              # key = id of the record, to keep file order
    out = []
    rec = None
    mode = "G01"
    pos = (0.0, 0.0)
    path = None                                             # the polyline being drawn (outline type, list of points)
    pending_pin = None
    for ext, blk in toks:
        if ext:
            for cmd in [c.strip() for c in ext.split("*") if c.strip()]:
                if cmd.startswith("TA.AperFunction,"):
                    cur_func = cmd[len("TA.AperFunction,"):]
                elif cmd.startswith("TD"):
                    key = cmd[2:].lstrip(".")
                    if cmd == "TD" or key == "":
                        cur_func = ""
                        attr = {}
                        pending_pin = None
                    elif key == "AperFunction":
                        cur_func = ""
                    else:
                        attr.pop(key, None)
                        if key == "P":
                            pending_pin = None
                elif cmd.startswith("ADD"):
                    m = re.match(r"ADD(\d+)(.*)", cmd)
                    ap_func[int(m.group(1))] = cur_func
                    ap_shape[int(m.group(1))] = m.group(2)
                elif cmd.startswith("TO."):
                    key, _, val = cmd[3:].partition(",")
                    if key == "C":
                        # A new reference starts a new part; the .Cxxx attributes that follow belong to it
                        rec = Component(ref=val.strip(), side=side, layer=layer_no)
                        out.append(rec)
                        attr = {"C": val.strip()}
                    elif key == "P":
                        f = [v.strip() for v in val.split(",")]
                        # .P,<refdes>,<pin number>[,<pin name>]: the reference is the first field (page 164)
                        pending_pin = (f[1] if len(f) > 1 else "", f[2] if len(f) > 2 else "")
                    elif key.startswith("C") and rec is not None:
                        _set_char(rec, key, val, scale)
                    elif key == "N":
                        attr["N"] = val
                elif cmd.startswith("SR") and cmd != "SR":
                    if rec is not None:
                        rec.notes.append("step and repeat not read")
            continue
        blk = blk.strip()
        if not blk or blk.startswith("G04"):
            continue
        if re.fullmatch(r"G0?([123])", blk):
            mode = "G0" + blk[-1]
            continue
        if blk == "G75" or blk == "G74" or blk.startswith("M0") or blk in ("G36", "G37"):
            if blk == "G74" and rec is not None:
                rec.notes.append("single-quadrant arcs (G74) not read")
            continue
        md = re.fullmatch(r"D(\d+)", blk)
        if md and int(md.group(1)) >= 10:
            cur_ap = int(md.group(1))
            continue
        mc = re.fullmatch(r"(?:G0?([123]))?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I(-?\d+))?(?:J(-?\d+))?(?:D0?([123]))?", blk)
        if not mc or not any(mc.groups()):
            continue
        g, xs, ys, i_, j_, d = mc.groups()
        if g:
            mode = "G0" + g
        newpos = (_num(xs, ndx, scale) if xs is not None else pos[0], _num(ys, ndy, scale) if ys is not None else pos[1])
        func = ap_func.get(cur_ap, "")
        if d == "3":
            pos = newpos
            if rec is None:
                continue
            if func.startswith("ComponentMain") and rec.origin is None:
                rec.origin = pos
            elif func.startswith("ComponentPin") and pending_pin is not None:
                shape = ap_shape.get(cur_ap, "")
                rec.pins.append(Pin(pending_pin[0], pending_pin[1], pos[0], pos[1], key=shape.startswith("P,")))
            continue
        if d == "2":
            pos = newpos
            path = None
            continue
        # D01 (or a repeated D01 with only coordinates): a segment of the current outline
        if func.startswith("ComponentOutline,") and rec is not None:
            kind = func.split(",", 1)[1].strip()
            if path is None:
                path = (kind, [pos])
                rec.outlines.setdefault(kind, []).append(path[1])
            if mode == "G01":
                path[1].append(newpos)
            else:
                path[1].extend(_arc_points(pos, newpos, (_num(i_ or "0", ndx, scale), _num(j_ or "0", ndy, scale)), mode == "G02"))
        pos = newpos
    return out


def _set_char(rec, key, val, scale):
    """!
    @brief Store one component characteristic (`.Cxxx`) on a component.
    @param rec Component.
    @param key Attribute name without the leading dot, for example `CRot`.
    @param val Attribute value text.
    @param scale mm per file unit (for the height).
    """
    v = val.strip()
    if key == "CRot":
        try:
            rec.rotation = float(v)
        except ValueError:
            rec.notes.append("bad .CRot " + v)
    elif key == "CHgt":
        try:
            rec.height_mm = float(v) * scale
        except ValueError:
            rec.notes.append("bad .CHgt " + v)
    elif key == "CFtp":
        rec.footprint = v
    elif key == "CVal":
        rec.value = v
    elif key == "CMnt":
        rec.mount = v
    elif key == "CPgN":
        rec.package = v
    elif key == "CMfr":
        rec.manufacturer = v
    elif key == "CMPN":
        rec.mpn = v
    elif key == "CLbN":
        rec.library = v


def duplicate_references(parts):
    """!
    @brief The references used by more than one component (the specification says a reference must be unique, page 167).
    @param parts List of Component.
    @return sorted list of str.
    """
    seen, dup = set(), set()
    for p in parts:
        (dup if p.ref in seen else seen).add(p.ref)
    return sorted(dup)


def to_board(part, local):
    """!
    @brief Local footprint coordinates to board coordinates: rotation zero as in IPC-7351B, positive rotation counter-clockwise seen from the top (page 166), and a bottom part is the top footprint turned over, which on the files means the local x changes sign before the rotation (the reading "flipped along the X axis" as y -> -y fails on every footprint tested, study_x3_components.py).
    @param part Component (origin, rotation, side).
    @param local List of (x, y) of the footprint at rotation zero as drawn for a top part.
    @return list of (x, y) in mm.
    """
    a = math.radians(part.rotation)
    c, s = math.cos(a), math.sin(a)
    ox, oy = part.origin
    out = []
    for x, y in local:
        if part.side == "bottom":
            x = -x                                          # the board is turned over: the local x changes sign (checked on 8 footprints of three boards, 8 of 8)
        out.append((ox + c * x - s * y, oy + s * x + c * y))
    return out


def to_local(part, pts):
    """!
    @brief Board coordinates to the local footprint frame at rotation zero (inverse of `to_board`).
    @param part Component (origin, rotation, side).
    @param pts List of (x, y) in mm.
    @return list of (x, y).
    """
    a = math.radians(part.rotation)
    c, s = math.cos(a), math.sin(a)
    ox, oy = part.origin
    out = []
    for x, y in pts:
        dx, dy = x - ox, y - oy
        lx, ly = c * dx + s * dy, -s * dx + c * dy
        out.append((-lx if part.side == "bottom" else lx, ly))
    return out


def hull(points):
    """!
    @brief Convex hull (Andrew's monotone chain).
    @param points Iterable of (x, y).
    @return list of (x, y) counter-clockwise, without repeating the first point; fewer than 3 points are returned as they are.
    """
    pts = sorted(set((round(x, 9), round(y, 9)) for x, y in points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def polygon_area(poly):
    """!
    @brief Area of a simple polygon (shoelace).
    @param poly List of (x, y); the closing point may be repeated.
    @return float, mm2.
    """
    if len(poly) < 3:
        return 0.0
    s = 0.0
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def bbox(points):
    """!
    @brief Bounding box of points.
    @param points List of (x, y).
    @return (xmin, ymin, xmax, ymax) or None.
    """
    if not points:
        return None
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def heat_shape(part):
    """!
    @brief The heat-source shape of a part from the data of its own record, with the name of the source: the best outline by the order Body, Lead2Lead, Footprint, Courtyard, else the hull of the pins (grown by nothing), else None.
    @details A body outline is what dissipates; a courtyard is a clearance (1.5 times the paste box on StickHub) and is offered last, as an upper bound; the pin hull has no area for a two-pin chip along one axis,
             so a hull with less than 1e-6 mm2 is returned as the bounding box of the pins grown by 0.1 mm each side.
    @param part Component.
    @return tuple (polygon as list of (x, y) without the repeated closing point, source name) or (None, "none").
    """
    for kind in OUTLINE_TYPES:
        loops = part.outlines.get(kind)
        if loops:
            loop = max(loops, key=polygon_area)
            if polygon_area(loop) > 1e-9:
                return (loop[:-1] if loop[0] == loop[-1] else loop), kind
    pts = part.pin_points()
    if pts:
        h = hull(pts)
        if polygon_area(h) > 1e-6:
            return h, "pins"
        x0, y0, x1, y1 = bbox(pts)
        g = 0.1
        return [(x0 - g, y0 - g), (x1 + g, y0 - g), (x1 + g, y1 + g), (x0 - g, y1 + g)], "pins"
    return None, "none"
