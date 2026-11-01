#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file components.py
@brief The Gerber X3 component layer (`%TF.FileFunction,Component,L<p>,Top|Bot*%`) read into `Component` objects, the link of the components to the paste and copper layers by `TO.C` and `TO.P`, and the heat-source shape.
@details Written from the Ucamco Gerber Layer Format Specification (aperture functions `ComponentMain`, `ComponentOutline,<type>` and `ComponentPin`; object attributes `.C`, `.P`, `.CRot`, `.CVal`,
         `.CMnt`, `.CFtp`, `.CHgt`, ...); port of the research prototype `research/gerber-real-boards/lib/x3_components.py`, independent of the raster reader (`parser.Layer` keeps `.C`, `.N`, `.P` only and
         ignores the `.Cxxx`). No GUI; the coordinate numbers are read by `parser.parse_number` (leading or trailing zeros omitted, as the main reader); any malformed input ends in a `GerberError`.
         One small tokeniser: extended commands between `%`, function blocks ending in `*`; it follows the aperture function, the current aperture, the object attributes (a dictionary that `TO` adds to and
         `TD` removes from, read when each object is created, so the order in the file does not matter), the interpolation mode and the coordinate format. Lengths in mm (the file unit is converted,
         `.CHgt` too); angles in degrees, positive counter-clockwise seen from the top. Not read: aperture blocks and macros (not used by a component layer); step and repeat is counted in `Component.notes`.
         Mount types: `SMD` parts are heat-source candidates; `TH`, `Pressfit`, `Other` (and `Fiducial`, the value of files older than revision 2024.05, or any unknown value) are listed without a source.
         Heat-source shape, in order: Body, Lead2Lead, the hull of the paste openings linked by `TO.C`, Footprint, Courtyard, hull of the pins (`heat_polygon`).
         Rotation: zero as in IPC-7351B; a bottom part is the top footprint turned over, so the local x changes sign before the rotation (`to_board`).
"""

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from .errors import GerberError, UnsupportedFeatureError
from .parser import parse_number

## The outline types of the specification, the ones that come before the paste hull in the heat-source order, and the ones that come after it.
OUTLINE_BEFORE_PASTE = ("Body", "Lead2Lead")
OUTLINE_AFTER_PASTE = ("Footprint", "Courtyard")
## Mount types that make a part a heat-source candidate.
SMD_MOUNTS = ("SMD",)


@dataclass
class Pin:
    """!@brief A pin of a component: number, optional pin function (third field of `.P`), position in mm (board frame) and whether it is the key pin (the diamond aperture of the specification)."""
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

    @property
    def is_smd(self):
        """!
        @brief Whether the part is a heat-source candidate (mount type SMD).
        @return bool.
        """
        return self.mount in SMD_MOUNTS


def _arc_points(p0, p1, ij, clockwise, step_deg=5.0):
    """!
    @brief Points of a multi-quadrant circular arc (G75) from p0 to p1 with the centre at p0 + (I, J).
    @param p0 Start (x, y) in mm.
    @param p1 End (x, y) in mm.
    @param ij Offsets (I, J) of the centre from the start in mm.
    @param clockwise True for G02.
    @param step_deg Largest angle of a chord in degrees.
    @return list of (x, y) after the start point up to and including p1.
    """
    cx, cy = p0[0] + ij[0], p0[1] + ij[1]
    a0 = math.atan2(p0[1] - cy, p0[0] - cx)
    a1 = math.atan2(p1[1] - cy, p1[0] - cx)
    # A full circle (start equal to end) is a sweep of 2 pi, not 0
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


def _num(token, fmt, scale):
    """!
    @brief A coordinate of the file to mm (the format statement says the digits and which zeros are omitted).
    @param token Text of the number (sign allowed).
    @param fmt Tuple (integer digits, decimal digits, "L" or "T") of the format statement.
    @param scale mm per file unit.
    @return float in mm.
    @throws GerberError If the value is not finite.
    """
    v = parse_number(token, fmt[0], fmt[1], fmt[2]) * scale
    if not math.isfinite(v):
        raise GerberError(f"coordinate {token[:20]!r} is not finite")
    return v


def parse_components(text, name=""):
    """!
    @brief Read the components of an X3 component layer.
    @details The object attributes are kept as the specification defines them (a dictionary that `TO` adds to and `TD` removes from): they are read when an object is created, so their order in the
             file does not matter. The characteristics (`.Cxxx`) are taken from the `ComponentMain` flash, an outline draw belongs to the part named by its `.C`, and a pin flash to the part named by
             the first field of its `.P` (`.C` is not required on a pin). A second `ComponentMain` flash with a reference that already has an origin is a duplicate and becomes a second entry;
             outlines and pins of a reference that has no `ComponentMain` (yet) create the entry, so a writer that groups the objects by kind is read the same.
    @param text Content of the file.
    @param name File name for the messages.
    @return list of Component in file order (a reference flashed twice as ComponentMain is two entries: the check is `duplicate_references`).
    @throws GerberError If the file has no coordinate format statement, uses incremental coordinates (`UnsupportedFeatureError`) or is malformed (a number that is not finite or has
            thousands of digits); never another exception.
    """
    try:
        return _parse_components(text, name)
    except GerberError:
        raise
    except (ValueError, IndexError, KeyError, TypeError, ZeroDivisionError, OverflowError, RecursionError, MemoryError) as exc:
        # A number of thousands of digits, a malformed field: always the reader's own error, naming the file (as parser.Layer does)
        raise GerberError(f"{name or 'file'}: malformed component layer ({type(exc).__name__}: {exc})") from exc


def _parse_components(text, name):
    """!
    @brief The body of `parse_components` (any Python error it raises is turned into a GerberError by the caller).
    @param text Content of the file.
    @param name File name for the messages.
    @return list of Component in file order.
    @throws GerberError If the file has no coordinate format statement or uses incremental coordinates.
    """
    text = text.lstrip("\ufeff")                           # a byte order mark would hide the first extended command
    fm = re.search(r"%FS([LTD]?)([AI])X(\d)(\d)Y(\d)(\d)\*%", text)
    if not fm:
        raise GerberError(f"{name or 'file'}: no format statement (FS)")
    if fm.group(2) == "I":
        raise UnsupportedFeatureError(name, "incremental coordinates (FS with I)")
    zeros = "T" if fm.group(1) == "T" else "L"               # trailing-zero omission (deprecated) is read as the main reader does
    fmt_x = (int(fm.group(3)), int(fm.group(4)), zeros)
    fmt_y = (int(fm.group(5)), int(fm.group(6)), zeros)
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
    attr = {}                                               # the object attribute dictionary: name without the dot -> value text
    out = []
    latest = {}                                             # reference -> its latest Component (the one outlines and pins are added to)
    mode = "G01"
    pos = (0.0, 0.0)
    path = None                                             # the polyline being drawn: (reference, list of points)
    sr_seen = False
    single_quadrant = False                                 # G74 (deprecated): an arc is then replaced by its chord and noted

    def record(ref):
        """!
        @brief The entry of a reference, created when it does not exist yet.
        @param ref Reference text.
        @return Component.
        """
        if ref not in latest:
            latest[ref] = Component(ref=ref, side=side, layer=layer_no)
            out.append(latest[ref])
            if sr_seen:
                latest[ref].notes.append("step and repeat not read")
        return latest[ref]

    for ext, blk in toks:
        if ext:
            for cmd in [c.strip() for c in ext.split("*") if c.strip()]:
                if cmd.startswith("TA.AperFunction,"):
                    cur_func = cmd[len("TA.AperFunction,"):]
                elif cmd.startswith("TD"):
                    key = cmd[2:].lstrip(".")
                    if key == "":
                        cur_func = ""
                        attr = {}
                    elif key == "AperFunction":
                        cur_func = ""
                    else:
                        attr.pop(key, None)
                elif cmd.startswith("ADD"):
                    m = re.match(r"ADD(\d+)(.*)", cmd)
                    if m:
                        ap_func[int(m.group(1))] = cur_func
                        ap_shape[int(m.group(1))] = m.group(2)
                elif cmd.startswith("TO."):
                    key, _, val = cmd[3:].partition(",")
                    attr[key] = val.strip()
                elif cmd.startswith("SR") and cmd != "SR":
                    sr_seen = True
                    for r in out:
                        r.notes.append("step and repeat not read")
            continue
        blk = blk.strip()
        if not blk or blk.startswith("G04"):
            continue
        if re.fullmatch(r"G0?([123])", blk):
            mode = "G0" + blk[-1]
            continue
        if blk in ("G74", "G75"):
            single_quadrant = blk == "G74"
            continue
        if blk.startswith("M0") or blk in ("G36", "G37"):
            continue
        md = re.fullmatch(r"D(\d+)", blk)
        if md and int(md.group(1)) >= 10:
            cur_ap = int(md.group(1))
            path = None                                     # draws with another aperture are another outline (consecutive draws only)
            continue
        mc = re.fullmatch(r"(?:G0?([123]))?(?:X([-+]?[\d.]+))?(?:Y([-+]?[\d.]+))?(?:I([-+]?[\d.]+))?(?:J([-+]?[\d.]+))?(?:D0?([123]))?", blk)
        if not mc or not any(mc.groups()):
            continue
        g, xs, ys, i_, j_, d = mc.groups()
        if g:
            mode = "G0" + g
        newpos = (_num(xs, fmt_x, scale) if xs is not None else pos[0], _num(ys, fmt_y, scale) if ys is not None else pos[1])
        func = ap_func.get(cur_ap, "")
        if d == "3":
            pos = newpos
            path = None
            if func.startswith("ComponentMain") and "C" in attr:
                rec = record(attr["C"])
                if rec.origin is not None:
                    # A second ComponentMain with the same reference: a duplicate, kept as its own entry (the reference should be unique)
                    rec = Component(ref=attr["C"], side=side, layer=layer_no)
                    out.append(rec)
                    latest[attr["C"]] = rec
                rec.origin = pos
                for k, v in attr.items():
                    if k.startswith("C") and k != "C":
                        _set_char(rec, k, v, scale)
            elif func.startswith("ComponentPin") and "P" in attr:
                # .P,<refdes>,<number>[,<function>]: the part is named by the first field
                f = [v.strip() for v in attr["P"].split(",")]
                rec = record(f[0])
                shape = ap_shape.get(cur_ap, "")
                rec.pins.append(Pin(f[1] if len(f) > 1 else "", f[2] if len(f) > 2 else "", pos[0], pos[1], key=shape.startswith("P,")))
            continue
        if d == "2":
            pos = newpos
            path = None
            continue
        # D01 (or a repeated D01 with only coordinates): a segment of the outline of the part named by .C
        if func.startswith("ComponentOutline,") and "C" in attr:
            kind = func.split(",", 1)[1].strip()
            if path is None or path[0] != attr["C"]:
                pts = [pos]
                path = (attr["C"], pts)
                record(attr["C"]).outlines.setdefault(kind, []).append(pts)
            if mode == "G01":
                path[1].append(newpos)
            elif single_quadrant:
                # The sign of I and J is not in the file in G74 mode: the chord is kept and the part says so (no silent wrong arc)
                path[1].append(newpos)
                rec = record(attr["C"])
                if "single-quadrant arc (G74) read as its chord" not in rec.notes:
                    rec.notes.append("single-quadrant arc (G74) read as its chord")
            else:
                path[1].extend(_arc_points(pos, newpos, (_num(i_ or "0", fmt_x, scale), _num(j_ or "0", fmt_y, scale)), mode == "G02"))
        pos = newpos
    return out


def read_components(path):
    """!
    @brief Read an X3 component layer from disk.
    @param path File path.
    @return list of Component.
    @throws GerberError If the file has no coordinate format statement.
    """
    p = Path(path)
    return parse_components(p.read_text(encoding="utf-8", errors="replace"), p.name)


def is_component_layer(text):
    """!
    @brief Whether a file is an X3 component layer: by the file function first, else by the content (an aperture with the function `ComponentMain`), never by the name.
    @param text Content of the file (the head is enough for the file function; the content for the fallback).
    @return bool.
    """
    if re.search(r"%TF\.FileFunction,Component\b", text):
        return True
    return "TA.AperFunction,ComponentMain" in text


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
            r = float(v)
        except ValueError:
            r = math.nan
        if math.isfinite(r):
            rec.rotation = r
        else:                                               # nan or inf would turn every point of the part into nan
            rec.notes.append("bad .CRot " + v[:40])
    elif key == "CHgt":
        try:
            h = float(v) * scale
        except ValueError:
            h = math.nan
        if math.isfinite(h) and h >= 0:
            rec.height_mm = h
        else:
            rec.notes.append("bad .CHgt " + v[:40])
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
    # .CPgD, .CLbD and .CSup are read but not kept (no use in the thermal model)


def duplicate_references(parts):
    """!
    @brief The references used by more than one component (the specification says a reference must be unique).
    @param parts List of Component.
    @return sorted list of str.
    """
    seen, dup = set(), set()
    for p in parts:
        (dup if p.ref in seen else seen).add(p.ref)
    return sorted(dup)


def to_board(part, local):
    """!
    @brief Local footprint coordinates to board coordinates: rotation zero as in IPC-7351B, positive rotation counter-clockwise seen from the top; a bottom part is the top footprint turned over, so the local x changes sign before the rotation.
    @param part Component (origin, rotation, side).
    @param local List of (x, y) in mm of the footprint at rotation zero as drawn for a top part.
    @return list of (x, y) in mm.
    """
    a = math.radians(part.rotation)
    c, s = math.cos(a), math.sin(a)
    ox, oy = part.origin
    out = []
    for x, y in local:
        if part.side == "bottom":
            x = -x                                          # the board is turned over: the local x changes sign (7 of 7 top/bottom footprint pairs of three boards)
        out.append((ox + c * x - s * y, oy + s * x + c * y))
    return out


def to_local(part, pts):
    """!
    @brief Board coordinates to the local footprint frame at rotation zero (inverse of `to_board`).
    @param part Component (origin, rotation, side).
    @param pts List of (x, y) in mm.
    @return list of (x, y) in mm.
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
    @param points Iterable of (x, y) in mm.
    @return list of (x, y) counter-clockwise, without repeating the first point; fewer than 3 distinct points are returned as they are.
    """
    pts = sorted(set((round(x, 9), round(y, 9)) for x, y in points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        """!@brief Z of the cross product (a - o) x (b - o). @param o Origin. @param a First point. @param b Second point. @return float."""
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
    @param poly List of (x, y) in mm; the closing point may be repeated.
    @return float in mm2.
    """
    if len(poly) < 3:
        return 0.0
    s = 0.0
    for (x0, y0), (x1, y1) in zip(poly, list(poly[1:]) + [poly[0]]):
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def bbox(points):
    """!
    @brief Bounding box of points.
    @param points List of (x, y) in mm.
    @return (xmin, ymin, xmax, ymax) or None for no points.
    """
    if not len(points):
        return None
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _best_loop(loops):
    """!
    @brief The largest closed polyline of a list, as a polygon without the repeated closing point.
    @param loops List of polylines.
    @return list of (x, y), or None when no loop has an area.
    """
    if not loops:
        return None
    loop = max(loops, key=polygon_area)
    if polygon_area(loop) <= 1e-9:
        return None
    return list(loop[:-1] if loop[0] == loop[-1] else loop)


def heat_polygon(part, paste_hull=None):
    """!
    @brief The heat-source shape of a part with the name of its source, in the order Body, Lead2Lead, hull of the paste openings linked by `TO.C`, Footprint, Courtyard, hull of the pins.
    @details A body outline is what dissipates; the Footprint outline is the contour of the land pattern (about the paste hull); a courtyard is a clearance (1.57 times the paste box in area, median of
             360 parts) and is offered after them; the pin hull has no area for a two-pin part along one axis, so a hull of less than 1e-6 mm2 is returned as the bounding box of the pins grown by 0.1 mm.
    @param part Component.
    @param paste_hull Hull of the paste openings of the part as a list of (x, y) in mm, or None when the part has none (through-hole).
    @return tuple (polygon as list of (x, y) without the repeated closing point, source name "Body", "Lead2Lead", "paste", "Footprint", "Courtyard" or "pins") or (None, "none").
    """
    for kind in OUTLINE_BEFORE_PASTE:
        loop = _best_loop(part.outlines.get(kind))
        if loop:
            return loop, kind
    if paste_hull is not None and len(paste_hull) >= 3 and polygon_area(paste_hull) > 1e-9:
        return [tuple(map(float, p)) for p in paste_hull], "paste"
    for kind in OUTLINE_AFTER_PASTE:
        loop = _best_loop(part.outlines.get(kind))
        if loop:
            return loop, kind
    pts = part.pin_points()
    if pts:
        h = hull(pts)
        if polygon_area(h) > 1e-6:
            return h, "pins"
        x0, y0, x1, y1 = bbox(pts)
        g = 0.1
        return [(x0 - g, y0 - g), (x1 + g, y0 - g), (x1 + g, y1 + g), (x0 - g, y1 + g)], "pins"
    return None, "none"


class PasteLink(NamedTuple):
    """!
    @brief The link of components to a paste layer: for every component the indices of its dark operations, the components without paste and the references of the layer that no component has.
    """
    by_ref: dict
    without_paste: list
    unknown_refs: list


class CopperLink(NamedTuple):
    """!
    @brief The link of components to copper layers by `TO.P`: for every component the flashes of its pins, the references that no component has, and the pins found (matched by number) with the largest offset.
    """
    by_ref: dict
    unknown_refs: list
    pins_matched: int
    pins_total: int
    max_offset_mm: float


def link_paste(components, layer):
    """!
    @brief Link the components to the openings of a paste layer by the component reference `TO.C`.
    @param components List of Component.
    @param layer Paste `parser.Layer` (its objects carry `TO.C` in `attrs(i).ref`).
    @return PasteLink: by_ref {reference: [operation indices of the dark objects]}, without_paste (Components with no object in the layer, in order), unknown_refs (references of the layer no component has).
    """
    by_ref = {}
    for i, (kind, dark, _a) in enumerate(layer.ops):
        ref = layer.attrs(i).ref
        if ref and dark:
            by_ref.setdefault(ref, []).append(i)
    known = {c.ref for c in components}
    without = [c for c in components if c.ref not in by_ref]
    unknown = sorted(r for r in by_ref if r not in known)
    return PasteLink({c.ref: by_ref[c.ref] for c in components if c.ref in by_ref}, without, unknown)


def link_copper(components, layers):
    """!
    @brief Link the components to the pads of copper layers by the pin attribute `TO.P,<ref>,<number>`.
    @param components List of Component (their pins give the expected positions).
    @param layers List of copper `parser.Layer`.
    @return CopperLink: by_ref {reference: [Flash of its pins]}, the references of the layers no component has, and how many component pins sit on a flash of the same reference and number (largest centre offset in mm).
    """
    by_ref, unknown = {}, set()
    flashes = {}
    known = {c.ref for c in components}
    for lay in layers:
        for f in lay.flashes():
            if not f.pin:
                continue
            ref, number = f.pin[0], f.pin[1]
            if ref not in known:
                unknown.add(ref)
                continue
            by_ref.setdefault(ref, []).append(f)
            flashes.setdefault((ref, number), []).append(f)
    matched, total, worst = 0, 0, 0.0
    for c in components:
        for p in c.pins:
            total += 1
            cands = flashes.get((c.ref, p.number))
            if cands:
                matched += 1
                worst = max(worst, min(math.hypot(f.x - p.x, f.y - p.y) for f in cands))
    return CopperLink(by_ref, sorted(unknown), matched, total, worst)
