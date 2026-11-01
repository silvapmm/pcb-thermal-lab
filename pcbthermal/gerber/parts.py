#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file parts.py
@brief Parts (heat sources) from the solder-paste layers of an import: the paste openings, the placement file, the `TO.C` references, the envelope matching rule, the X3 component layer, the click and the re-import merge.
@details Port of the research prototypes `research/gerber-real-boards/lib/component_match.py` and `prototypes/import_window/backend.py` (design in `research/gerber-real-boards/INTEGRATION.md` 9 to 12). No GUI.
         Lengths in mm, angles in degrees (counter-clockwise, Y up, as in the Gerber frame and in a KiCad position file).

         The matching rule, in this order of trust (the `source` of `ImportPart.from_file`):
         1. "x3": a component layer (`components.py`) names every part with reference, mount type, rotation and outlines; the paste openings are linked by `TO.C`.
         2. "to.c+placement": the paste file carries `TO.C`; the designator of each opening is the answer, the placement file adds value, package and rotation.
         3. "placement by position": no `TO.C`; per opening (no grouping first), the part of the placement file whose pad envelope, rotated by the part angle and grown by 0.3 mm, contains the opening
            centre; the smallest envelope wins; one part takes many openings. The envelope comes from the footprint NAME (0402 to 1206, SOIC pins and pitch, SOT-223, pin headers, QFN from the size in the
            name), no footprint library is read. Before it, the frame of the placement file is checked: the bottom-side X convention (as written or negated, a KiCad option) is detected from the openings,
            and a frame check proposes an offset when the share of parts with an opening falls clearly below the share the offset gives.
         4. "paste only": an opening no file names; the user clicks it (the largest opening under the point) and the heat-source shape is suggested as the convex hull (the box is available); grouping
            openings by proximity is a marked fallback only.
         Limits (carried from the research): the envelope table is small (TSOP, USB-C, batteries are guessed); an opening of a part that the placement file does not list, inside the envelope of a listed
         neighbour, is taken by it (cmm2: 9 of 494 openings); a placement file whose origin is off by more than about 0.5 mm assigns wrong designators silently unless the frame check proposes the offset.
"""

import copy
import csv
import hashlib
import math
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

from ..model import ImportPart
from .components import duplicate_references, heat_polygon, hull as _hull, link_copper
from .raster import Window, rasterize

## The sources of a match, in order of trust (ImportPart.from_file["source"]).
SOURCES = ("x3", "to.c+placement", "placement by position", "paste only")
## Source of a part that the placement file lists but no paste opening belongs to (through-hole parts, connectors): listed, no heat source.
SOURCE_NO_OPENING = "placement only"
## Tolerance (mm) added to the pad envelope of a part.
ENVELOPE_TOLERANCE_MM = 0.3
## Raster pixel (mm) of the paste layers (the research used 0.05 mm: the opening of a 0201 pad is 0.25 mm).
PASTE_PIXEL_MM = 0.05
## Largest number of pixels of a side of a paste raster; a larger board gets a coarser pixel.
MAX_PASTE_SIDE_PIXELS = 3000


# ------------------------------------------------------------------------------------------------------------------------------ placement files
## Header word (lower case, letters only) -> canonical field.
_FIELDS = {
    "ref": "ref", "designator": "ref", "refdes": "ref", "reference": "ref",
    "val": "value", "value": "value", "comment": "value",
    "package": "package", "footprint": "package", "pattern": "package",
    "posx": "x", "midx": "x", "centerx": "x", "x": "x",
    "posy": "y", "midy": "y", "centery": "y", "y": "y",
    "rot": "rot", "rotation": "rot",
    "side": "side", "layer": "side",
}
_UNIT_MM = {"mm": 1.0, "mil": 0.0254, "mils": 0.0254, "in": 25.4, "inch": 25.4, "inches": 25.4}


def _length_mm(text, default_unit="mm"):
    """!
    @brief A length with an optional unit suffix to millimetres.
    @param text String such as "12.5", "12.5mm", "492.1mil", "1.2in".
    @param default_unit Unit of a number without a suffix: mm, mil or in.
    @return float in mm.
    @throws ValueError If the text holds no number.
    """
    m = re.fullmatch(r"\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(mm|mils?|in|inch|inches)?\s*", text)
    if not m:
        raise ValueError(f"not a length: {text!r}")
    return float(m.group(1)) * _UNIT_MM[(m.group(2) or default_unit).lower()]


def _side(text):
    """!
    @brief Normalise the side of a part.
    @param text "top", "bottom", "t", "b", "front", "back" in any case.
    @return "top" or "bottom".
    """
    t = text.strip().lower()
    return "bottom" if t.startswith("b") else "top"


def _field_of(cell):
    """!
    @brief The canonical field named by a header cell, ignoring case, spaces, punctuation and a unit in brackets.
    @param cell Header cell text.
    @return "ref", "value", "package", "x", "y", "rot", "side" or None.
    """
    return _FIELDS.get(re.sub(r"[^a-z]", "", re.sub(r"[\(\[][^\)\]]*[\)\]]", "", cell.lower())))


def _header_unit(cell):
    """!
    @brief The unit written in a column header such as "PosX (mil)" or "Mid X [in]".
    @param cell Header cell text.
    @return "mm", "mil", "in" or None when the header names none.
    """
    m = re.search(r"[\(\[]\s*(mm|mils?|in|inch|inches)\s*[\)\]]", cell.lower())
    return None if not m else {"mils": "mil", "inch": "in", "inches": "in"}.get(m.group(1), m.group(1))


def parse_placement(text, name=""):
    """!
    @brief Read a placement file: the KiCad text report (`.pos`, `#` header, `## Unit = mm` comment), or a CSV (comma, semicolon or tab; JLCPCB, Altium, EasyEDA) with a header line.
    @details Columns are found by name (reference, value, package, X, Y, rotation, side; case, spaces and punctuation ignored). Units: a `## Unit = inch` comment of a KiCad report, a unit in a
             header cell ("PosX (mil)") or a suffix on each value ("492.1mil"); no unit means millimetres. With a semicolon or a tab as separator a decimal comma is read as a point.
    @param text Content of the file.
    @param name File name for the messages.
    @return list of dicts with ref, value, package, x, y (mm), rot (degrees), side ("top"/"bottom"); fields a file lacks are "" or 0.0.
    @throws ValueError If no header with a reference column and X and Y columns is found, or a value of a row is not a number.
    """
    header, rows, delim, unit = None, [], None, "mm"
    for ln in text.splitlines():
        if not ln.strip():
            continue
        if ln.startswith("##"):                                       # KiCad text report: comment lines (the unit is one of them)
            m = re.search(r"unit\s*=\s*([a-z]+)", ln, re.I)
            if m and m.group(1).lower() in _UNIT_MM:
                unit = {"mils": "mil", "inch": "in", "inches": "in"}.get(m.group(1).lower(), m.group(1).lower())
            continue
        if header is None:
            body = ln[2:] if ln.startswith("# ") else ln
            # The separator is the one that splits the line into the most cells (a header "Ref Val Package PosX ..." splits only on blanks)
            for d in (",", ";", "\t"):
                if d in body:
                    delim = d
                    cells = next(csv.reader([body], delimiter=d))
                    break
            else:
                delim, cells = None, body.split()
            keys = [_field_of(c) for c in cells]
            if "ref" in keys and "x" in keys and "y" in keys:
                header = cells
                continue
            if ln.startswith("# "):                                   # another comment line of the report
                continue
            raise ValueError(f"{name or 'file'}: no placement header found (first line {ln[:60]!r})")
        if ln.startswith("#"):
            continue
        if delim:
            rows.append(next(csv.reader([ln], delimiter=delim)))
        else:
            try:
                rows.append(shlex.split(ln))                          # quoted values with blanks ("10 k")
            except ValueError:
                rows.append(ln.split())
    if header is None:
        raise ValueError(f"{name or 'file'}: empty placement file")
    keys = [_field_of(c) for c in header]
    units = [_header_unit(c) or unit for c in header]
    out = []
    for r in rows:
        d = {"ref": "", "value": "", "package": "", "x": 0.0, "y": 0.0, "rot": 0.0, "side": "top"}
        for k, u, v in zip(keys, units, r):
            if delim in (";", "\t"):
                v = v.replace(",", ".") if k in ("x", "y", "rot") else v
            if k in ("x", "y"):
                d[k] = _length_mm(v, u)
            elif k == "rot":
                d[k] = float(re.sub(r"[^0-9eE.+-]", "", v) or 0.0)
            elif k == "side":
                d[k] = _side(v)
            elif k in ("ref", "value", "package"):
                d[k] = v.strip().strip('"')
        if d["ref"]:
            out.append(d)
    return out


def read_placement(path):
    """!
    @brief Read a placement file from disk.
    @param path File path.
    @return list of dicts as `parse_placement`.
    @throws ValueError If the file is not a placement file.
    """
    p = Path(path)
    return parse_placement(p.read_text(encoding="utf-8", errors="replace"), p.name)


def sha256_of(path):
    """!
    @brief SHA-256 of a file (to recognise the same set of files again in a re-import).
    @param path File path.
    @return str hex digest.
    """
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------------------------------------ openings
@dataclass
class Opening:
    """!
    @brief One solder-paste opening (a connected piece of the paste layer, no grouping): centroid, area, box and convex hull in mm.
    """
    x: float                                         # Centroid X (mm)
    y: float                                         # Centroid Y (mm)
    area: float                                      # Area (mm2)
    bbox: tuple                                      # (xmin, ymin, xmax, ymax) in mm
    hull: list                                       # Convex hull of the opening as [(x, y), ...] in mm
    side: str = "top"                                # "top" or "bottom" (the paste layer)
    ref: str = None                                  # Designator from the `TO.C` attribute of the paste file, when it has one


def _hull_of_mask(mask, x_left, y_top, pix):
    """!
    @brief Convex hull of the pixels of a boolean mask (the corners of the leftmost and rightmost pixel of each row are enough).
    @param mask Boolean array (rows from the top).
    @param x_left X of the left edge of the array (mm).
    @param y_top Y of the top edge (mm).
    @param pix Pixel (mm).
    @return list of (x, y) in mm.
    """
    h = pix / 2.0
    pts = []
    for r in np.nonzero(mask.any(axis=1))[0]:
        cols = np.nonzero(mask[r])[0]
        yc = y_top - (r + 0.5) * pix
        for c, sgn in ((cols[0], -1), (cols[-1], 1)):
            xc = x_left + (c + 0.5) * pix + sgn * h
            pts += [(xc, yc - h), (xc, yc + h)]
        # The other side of each extreme pixel makes the hull cover the pixel itself
        xl, xr = x_left + cols[0] * pix, x_left + (cols[-1] + 1) * pix
        pts += [(xl, yc - h), (xl, yc + h), (xr, yc - h), (xr, yc + h)]
    return _hull(pts)


def _openings_of_mask(mask, x_left, y_top, pix, side, ref):
    """!
    @brief The connected pieces of a boolean mask as openings.
    @param mask Boolean array (rows from the top).
    @param x_left X of the left edge (mm).
    @param y_top Y of the top edge (mm).
    @param pix Pixel (mm).
    @param side "top" or "bottom".
    @param ref Designator to give them, or None.
    @return list of Opening.
    """
    lab, n = ndimage.label(mask)
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        sub = lab[sl] == i
        rows, cols = np.nonzero(sub)
        r0, c0 = sl[0].start, sl[1].start
        xs = x_left + (cols + c0 + 0.5) * pix
        ys = y_top - (rows + r0 + 0.5) * pix
        xl, yt = x_left + c0 * pix, y_top - r0 * pix
        out.append(Opening(float(xs.mean()), float(ys.mean()), float(len(rows) * pix * pix),
                           (float(xs.min() - pix / 2), float(ys.min() - pix / 2), float(xs.max() + pix / 2), float(ys.max() + pix / 2)),
                           _hull_of_mask(sub, xl, yt, pix), side, ref))
    return out


def _sub_layer(layer, indices):
    """!
    @brief A shallow copy of a layer that draws only some of its operations.
    @param layer Parsed `parser.Layer`.
    @param indices Operation indices to keep (file order).
    @return Layer (shares the apertures and the attribute table).
    """
    sub = copy.copy(layer)
    sub.ops = [layer.ops[i] for i in indices]
    sub.attr_ids = [layer.attr_ids[i] for i in indices]
    sub._boxes = None
    sub.negative = False
    return sub


def _raster_openings(layer, indices, side, ref, pix, margin):
    """!
    @brief Rasterise some operations of a paste layer to a binary mask and return its pieces as openings.
    @param layer Parsed `parser.Layer`.
    @param indices Operation indices to draw.
    @param side "top" or "bottom".
    @param ref Designator of the objects, or None.
    @param pix Pixel (mm).
    @param margin Margin around the box of the objects (mm).
    @return list of Opening.
    """
    sub = _sub_layer(layer, indices)
    bb = sub.bbox()
    if bb is None:
        return []
    win = Window(bb[0] - margin, bb[3] + margin, bb[2] - bb[0] + 2 * margin, bb[3] - bb[1] + 2 * margin)
    cov = rasterize(sub, win, pix, supersample=1)
    return _openings_of_mask(cov >= 128, win.x_left, win.y_top, pix, side, ref)


def read_openings(layer, side="top", pix=PASTE_PIXEL_MM, by_ref=True):
    """!
    @brief The individual openings of a paste layer (a connected piece of the dark objects is one opening; no grouping).
    @details With `by_ref` and a layer that carries `TO.C`, every designator is drawn on its own small raster, so that openings of two parts that touch stay two and each opening knows its part;
             the objects without `TO.C` are drawn together. Without `TO.C` (or with `by_ref` False) the whole layer is drawn once. Clear objects that meet the box of a group are drawn too.
             The pixel is coarsened for a layer whose box exceeds `MAX_PASTE_SIDE_PIXELS` pixels a side.
    @param layer Parsed paste `parser.Layer`.
    @param side "top" or "bottom".
    @param pix Raster pixel in mm.
    @param by_ref True: use `TO.C` when the layer has it.
    @return list of Opening in the order of the references (file order) then the rest.
    """
    bb = layer.bbox()
    if bb is None:
        return []
    pix = max(pix, max(bb[2] - bb[0], bb[3] - bb[1]) / MAX_PASTE_SIDE_PIXELS)
    margin = 2 * pix
    dark = [i for i, op in enumerate(layer.ops) if op[1]]
    clear = [i for i, op in enumerate(layer.ops) if not op[1]]
    if not (by_ref and layer.references()):
        return _raster_openings(layer, sorted(dark + clear), side, None, pix, margin)
    groups = {}
    for i in dark:
        groups.setdefault(layer.attrs(i).ref, []).append(i)
    boxes = layer.op_boxes()
    out = []
    for ref, idx in groups.items():
        near = list(idx)
        if clear:
            x0, y0 = boxes[idx, 0].min() - margin, boxes[idx, 1].min() - margin
            x1, y1 = boxes[idx, 2].max() + margin, boxes[idx, 3].max() + margin
            near += [i for i in clear if boxes[i, 0] <= x1 and boxes[i, 2] >= x0 and boxes[i, 1] <= y1 and boxes[i, 3] >= y0]
        out += _raster_openings(layer, sorted(near), side, ref, pix, margin)
    return out


# ------------------------------------------------------------------------------------------------------------------------------ envelope
## Pad extents (length along the part axis, width) of the passives by size code.
_PASSIVE = {"0201": (1.0, 0.5), "0402": (1.5, 0.6), "0603": (2.45, 0.95), "0805": (2.9, 1.45), "1206": (4.1, 1.8)}
_TH_WORDS = ("PinHeader", "USB_Micro", "USB_C", "Battery", "TS-1187", "Molex", "MountingHole", "Conn", "TerminalBlock", "Jack")


def envelope(pkg):
    """!
    @brief Local pad envelope of a part from its footprint NAME only (KiCad naming).
    @param pkg Footprint name.
    @return tuple (lx, ly, ox, oy, kind, known): size and centre offset in mm along the part axes, kind "smd" or "th", known False when it is a guess.
    """
    m = re.match(r"^(?:R|C|L|D|LED|F|FB)_(\d{4})_", pkg)
    if m and m.group(1) in _PASSIVE:
        lx, ly = _PASSIVE[m.group(1)]
        return lx, ly, 0, 0, "smd", True
    m = re.match(r"PinHeader_(\d)x(\d+)_P([\d.]+)mm", pkg)
    if m:
        c, r, p = int(m.group(1)), int(m.group(2)), float(m.group(3))
        # Pins at local x 0..(c-1)p and local y = 0..-(r-1)p (position file Y up), pad ring 1.7 mm
        return (c - 1) * p + 1.7, (r - 1) * p + 1.7, (c - 1) * p / 2, -(r - 1) * p / 2, "th", True
    if pkg.startswith("SOT-223"):
        return 8.3, 6.1, 0, 0, "smd", True
    if pkg.startswith("SOT-23"):
        return 3.3, 3.0, 0, 0, "smd", True
    if "HC49" in pkg:
        return 14.6, 2.1, 0, 0, "smd", True
    if "USB_Micro" in pkg:
        return 7.8, 5.3, 0, 1.125, "th", True
    m = re.match(r"(?:SOIC|SOP|TSSOP|MSOP)-(\d+)_(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)mm_P(\d+(?:\.\d+)?)mm", pkg)
    if m:   # leads left and right (KiCad default): span = body width + 3.6, rows = (N/2 - 1) pitches + a pad
        n, a, pit = int(m.group(1)), float(m.group(2)), float(m.group(4))
        return a + 3.6, (n // 2 - 1) * pit + 0.6, 0, 0, "smd", True
    m = re.search(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)mm", pkg)
    if m and not pkg.startswith(("Crystal", "Oscillator")):
        a, c = float(m.group(1)), float(m.group(2))
        mg = 0.8 if "QFN" in pkg or "LGA" in pkg or "DFN" in pkg else 1.6    # gull-wing leads reach past the body
        return a + 2 * mg, c + 2 * mg, 0, 0, "smd", True
    if m:   # crystals and oscillators with the body size
        a, c = float(m.group(1)), float(m.group(2))
        return a + 0.8, c, 0, 0, "smd", True
    if pkg.startswith("RP2040-QFN"):
        return 7.8, 7.8, 0, 0, "smd", True
    if any(w in pkg for w in _TH_WORDS):
        return 5.0, 5.0, 0, 0, "th", False
    return 3.0, 3.0, 0, 0, "smd", False


def _rotation(rot_deg, side="top", mirror_bottom=False):
    """!
    @brief Rotation matrix of a part, optionally with the mirrored X of a bottom-side footprint.
    @param rot_deg Rotation of the part in degrees (counter-clockwise).
    @param side "top" or "bottom".
    @param mirror_bottom True: mirror the local X on the bottom side.
    @return numpy.ndarray 2 x 2 (orthogonal).
    """
    a = math.radians(rot_deg)
    c, s = math.cos(a), math.sin(a)
    r = np.array([[c, -s], [s, c]])
    if side == "bottom" and mirror_bottom:
        r = r @ np.diag([-1.0, 1.0])
    return r


def part_envelope_polygon(part, margin=0.0, mirror_bottom=False):
    """!
    @brief Board-frame corners of the pad envelope of a part.
    @param part Dict with package, x, y (mm), rot (degrees), side.
    @param margin Growth of the envelope on every side (mm).
    @param mirror_bottom True: mirror the local X of bottom-side parts.
    @return numpy.ndarray 4 x 2 corners in mm.
    """
    lx, ly, ox, oy = envelope(part["package"])[:4]
    hx, hy = lx / 2 + margin, ly / 2 + margin
    loc = np.array([[ox - hx, oy - hy], [ox + hx, oy - hy], [ox + hx, oy + hy], [ox - hx, oy + hy]])
    return loc @ _rotation(part["rot"], part["side"], mirror_bottom).T + np.array([part["x"], part["y"]])


def _inside_envelope(part, xs, ys, margin, mirror_bottom=False):
    """!
    @brief Which points lie inside the pad envelope of a part (grown by a margin).
    @param part Dict with package, x, y, rot, side.
    @param xs X of the points (mm).
    @param ys Y of the points (mm).
    @param margin Growth of the envelope on every side (mm).
    @param mirror_bottom True: mirror the local X of bottom-side parts.
    @return tuple (boolean array, envelope area in mm2).
    """
    lx, ly, ox, oy = envelope(part["package"])[:4]
    r = _rotation(part["rot"], part["side"], mirror_bottom)
    d = np.stack([np.asarray(xs) - part["x"], np.asarray(ys) - part["y"]])
    loc = r.T @ d                                                      # world = R local + position, R orthogonal
    ok = (np.abs(loc[0] - ox) <= lx / 2 + margin + 1e-9) & (np.abs(loc[1] - oy) <= ly / 2 + margin + 1e-9)
    return ok, (lx + 2 * margin) * (ly + 2 * margin)


def match_envelope(parts, openings, tol=ENVELOPE_TOLERANCE_MM, mirror_bottom=False):
    """!
    @brief The envelope rule: every opening goes to the part (same side) whose rotated pad envelope, grown by `tol`, contains its centre; the smallest envelope wins; one part may take many openings.
    @param parts List of dicts (ref, package, x, y, rot, side) in the frame of the Gerber files.
    @param openings List of Opening.
    @param tol Tolerance added to the envelope in mm.
    @param mirror_bottom True: mirror the local X of bottom-side footprints.
    @return tuple (dict ref -> opening indices, dict opening index -> ref).
    """
    n = len(openings)
    xs = np.array([o.x for o in openings])
    ys = np.array([o.y for o in openings])
    sides = np.array([o.side for o in openings])
    best_area = np.full(n, np.inf)
    best_ref = [None] * n
    for p in parts:
        if n == 0:
            break
        ok, area = _inside_envelope(p, xs, ys, tol, mirror_bottom)
        ok &= sides == p["side"]
        upd = ok & (area < best_area)                                  # a strictly smaller envelope wins; a tie keeps the first part of the file
        for i in np.nonzero(upd)[0]:
            best_area[i], best_ref[i] = area, p["ref"]
    byref, bypad = {}, {}
    for i, r in enumerate(best_ref):
        if r is not None:
            byref.setdefault(r, []).append(i)
            bypad[i] = r
    return byref, bypad


def bottom_convention(parts, openings, tol=ENVELOPE_TOLERANCE_MM):
    """!
    @brief Detect whether the placement file writes the X of bottom-side parts negated (a KiCad export option), by trying both and keeping the one that puts more bottom openings inside an envelope.
    @details The local mirror of the footprint does not decide it: every SMD envelope of the name table is centred, so a mirror (and the sign of a rotation by a multiple of 90 degrees) leaves it unchanged.
             A tie keeps the file as it is.
    @param parts List of dicts (ref, package, x, y, rot, side), positions in mm.
    @param openings List of Opening.
    @param tol Tolerance added to the envelope in mm.
    @return tuple (convention "as is" or "negated X", openings assigned as is, openings assigned negated).
    """
    bp = [p for p in parts if p["side"] == "bottom"]
    bo = [o for o in openings if o.side == "bottom"]
    if not bp or not bo:
        return "as is", 0, 0
    n_as = len(match_envelope(bp, bo, tol)[1])
    n_neg = len(match_envelope([dict(p, x=-p["x"]) for p in bp], bo, tol)[1])
    return ("negated X" if n_neg > n_as else "as is"), n_as, n_neg


def apply_bottom_convention(parts, convention):
    """!
    @brief Bring the bottom-side parts to the frame of the Gerber files.
    @param parts List of part dicts.
    @param convention "as is" or "negated X" (from `bottom_convention`).
    @return list of part dicts (new dicts for the changed parts).
    """
    if convention != "negated X":
        return list(parts)
    return [dict(p, x=-p["x"]) if p["side"] == "bottom" else p for p in parts]


def _parts_share(parts, openings, tol):
    """!
    @brief Share of the SMD parts of a placement file (known envelope) that have at least one opening in their envelope.
    @param parts List of part dicts.
    @param openings List of Opening.
    @param tol Tolerance of the envelope in mm.
    @return float in 0..1 (0 for no SMD part).
    """
    smd = [p for p in parts if envelope(p["package"])[4] == "smd" and envelope(p["package"])[5]]
    if not smd or not openings:
        return 0.0
    byref, _ = match_envelope(smd, openings, tol)
    return len(byref) / len(smd)


def frame_check(parts, openings, tol=ENVELOPE_TOLERANCE_MM, search_mm=10.0, min_gain=0.15):
    """!
    @brief Check that the placement file and the Gerber files share one origin, and propose the offset that aligns them when they do not.
    @details The score of an offset is the number of SMD parts (known envelope) that have an opening in their envelope. The search is a grid of 0.5 mm over +-search_mm, refined to 0.25 and 0.05 mm
             around the best three; the offset is proposed only when it raises the share by `min_gain` (absolute) over the file as given, so a board whose files agree is never moved. The rule
             tolerates 0.5 mm, loses a quarter of the openings at 1 mm and assigns wrong designators silently at 5 mm (research README 11.4).
    @param parts List of part dicts, bottom-side X convention already applied.
    @param openings List of Opening.
    @param tol Tolerance of the envelope in mm.
    @param search_mm Largest offset looked for (mm, each axis).
    @param min_gain Smallest rise of the share that makes the offset a proposal.
    @return dict: given (share as the file is), best (share with the offset), dx, dy (mm to add to the part positions), propose (bool), n_parts (SMD parts counted).
    """
    smd = [p for p in parts if envelope(p["package"])[4] == "smd" and envelope(p["package"])[5]]
    out = {"given": 0.0, "best": 0.0, "dx": 0.0, "dy": 0.0, "propose": False, "n_parts": len(smd)}
    if not smd or not openings:
        return out
    # The pairs (part, nearby opening) are built once; an offset only shifts the part
    tree = cKDTree(np.array([[o.x, o.y] for o in openings]))
    side_of = np.array([o.side for o in openings])
    pair_part, pair_dx, pair_dy = [], [], []
    for k, p in enumerate(smd):
        lx, ly = envelope(p["package"])[:2]
        reach = search_mm + math.hypot(lx, ly) / 2 + tol + 2.0
        for j in tree.query_ball_point([p["x"], p["y"]], reach):
            if side_of[j] == p["side"]:
                pair_part.append(k)
                pair_dx.append(openings[j].x - p["x"])
                pair_dy.append(openings[j].y - p["y"])
    pair_part, pair_dx, pair_dy = np.array(pair_part, int), np.array(pair_dx), np.array(pair_dy)
    if len(pair_part) == 0:
        return out
    # Per part: rotation transposed, envelope half-sizes and centre offset (as in _inside_envelope)
    rt = np.array([_rotation(p["rot"]).T for p in smd])
    half = np.array([[envelope(p["package"])[0] / 2 + tol, envelope(p["package"])[1] / 2 + tol] for p in smd])
    cen = np.array([[envelope(p["package"])[2], envelope(p["package"])[3]] for p in smd])
    rp = rt[pair_part]

    def score(t):
        """!@brief Number of parts with an opening inside their envelope after moving the parts by t. @param t Offset (dx, dy) in mm. @return int."""
        vx, vy = pair_dx - t[0], pair_dy - t[1]
        lx = rp[:, 0, 0] * vx + rp[:, 0, 1] * vy
        ly = rp[:, 1, 0] * vx + rp[:, 1, 1] * vy
        ok = (np.abs(lx - cen[pair_part, 0]) <= half[pair_part, 0] + 1e-9) & (np.abs(ly - cen[pair_part, 1]) <= half[pair_part, 1] + 1e-9)
        return int(np.count_nonzero(np.bincount(pair_part[ok], minlength=len(smd))))

    given = score((0.0, 0.0))
    steps = np.arange(-search_mm, search_mm + 1e-9, 0.5)
    coarse = [(score((dx, dy)), float(dx), float(dy)) for dx in steps for dy in steps]
    top = max(c[0] for c in coarse)
    # Many offsets reach the top score (the envelope and its tolerance are wider than a pad), so the answer is the CENTRE of the plateau, not its edge nearest to zero
    plateau = np.array([(c[1], c[2]) for c in coarse if c[0] == top])
    c0 = plateau.mean(axis=0)
    fine = []
    for dx in np.arange(c0[0] - 1.0, c0[0] + 1.0 + 1e-9, 0.1):
        for dy in np.arange(c0[1] - 1.0, c0[1] + 1.0 + 1e-9, 0.1):
            fine.append((score((dx, dy)), float(dx), float(dy)))
    top = max(top, max(f[0] for f in fine))
    best_xy = np.array([(f[1], f[2]) for f in fine if f[0] == top]).mean(axis=0) if any(f[0] == top for f in fine) else c0
    n = len(smd)
    if top <= given:                                             # the files agree as they are
        top, best_xy = given, np.zeros(2)
    out.update(given=given / n, best=top / n, dx=round(float(best_xy[0]), 3), dy=round(float(best_xy[1]), 3))
    out["propose"] = (top - given) / n >= min_gain
    return out


def apply_offset(parts, dx, dy):
    """!
    @brief Move the parts of a placement file by an offset (the frame check's proposal).
    @param parts List of part dicts.
    @param dx Offset in X (mm).
    @param dy Offset in Y (mm).
    @return list of new part dicts.
    """
    return [dict(p, x=p["x"] + dx, y=p["y"] + dy) for p in parts]


# ------------------------------------------------------------------------------------------------------------------------------ shapes and the click
def shape_polygon(openings, kind="hull"):
    """!
    @brief The candidate heat-source shape of a set of openings.
    @param openings List of Opening (one part).
    @param kind "hull" (convex hull of all the openings, the suggested default), "box" (the rectangle around them) or "largest" (the hull of the largest opening, the exposed pad of a QFN or the tab of a power package).
    @return list of (x, y) in mm (counter-clockwise), empty for no openings.
    @throws ValueError For an unknown kind.
    """
    if not openings:
        return []
    if kind == "hull":
        return _hull([p for o in openings for p in o.hull])
    if kind == "box":
        x0, y0 = min(o.bbox[0] for o in openings), min(o.bbox[1] for o in openings)
        x1, y1 = max(o.bbox[2] for o in openings), max(o.bbox[3] for o in openings)
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if kind == "largest":
        return list(max(openings, key=lambda o: o.area).hull)
    raise ValueError(f"unknown shape {kind!r}")


def _point_to_hull(poly, px, py):
    """!
    @brief Distance from a point to a convex polygon (0 inside).
    @param poly Counter-clockwise polygon [(x, y), ...] in mm.
    @param px X of the point (mm).
    @param py Y of the point (mm).
    @return float in mm.
    """
    n = len(poly)
    if n == 0:
        return math.inf
    if n >= 3 and all((poly[(i + 1) % n][0] - poly[i][0]) * (py - poly[i][1]) - (poly[(i + 1) % n][1] - poly[i][1]) * (px - poly[i][0]) >= 0 for i in range(n)):
        return 0.0
    best = math.inf
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        dx, dy = bx - ax, by - ay
        den = dx * dx + dy * dy
        t = 0.0 if den == 0 else min(1.0, max(0.0, ((px - ax) * dx + (py - ay) * dy) / den))
        best = min(best, math.hypot(ax + t * dx - px, ay + t * dy - py))
    return best


def opening_at(openings, x, y, side=None, tol_mm=0.1):
    """!
    @brief The opening a click selects: the largest opening whose hull holds the point (or lies within `tol_mm` of it).
    @param openings List of Opening.
    @param x X of the click in mm (Gerber frame).
    @param y Y of the click in mm.
    @param side "top", "bottom" or None for both.
    @param tol_mm Distance from the opening that still counts (mm), the thickness of a finger on the preview.
    @return index of the opening in the list, or None when nothing is under the point.
    """
    best, best_area = None, -1.0
    for i, o in enumerate(openings):
        if side is not None and o.side != side:
            continue
        if not (o.bbox[0] - tol_mm <= x <= o.bbox[2] + tol_mm and o.bbox[1] - tol_mm <= y <= o.bbox[3] + tol_mm):
            continue
        if _point_to_hull(o.hull, x, y) <= tol_mm and o.area > best_area:
            best, best_area = i, o.area
    return best


def proximity_groups(openings, link_mm=0.6):
    """!
    @brief Group openings whose edges are closer than `link_mm` (the FALLBACK when nothing names the parts; a group can be a pair of neighbours, so the result is marked "proximity").
    @param openings List of Opening.
    @param link_mm Openings whose boxes are closer than this (mm) belong to one group.
    @return list of lists of indices into `openings` (same side only).
    """
    n = len(openings)
    parent = list(range(n))

    def find(a):
        """!@brief Root of a set. @param a Index. @return int."""
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    if n:
        reach = max(max(o.bbox[2] - o.bbox[0], o.bbox[3] - o.bbox[1]) for o in openings) + link_mm
        tree = cKDTree(np.array([[o.x, o.y] for o in openings]))
        for i, j in tree.query_pairs(reach * 1.0):
            a, b = openings[i], openings[j]
            if a.side != b.side:
                continue
            gap = math.hypot(max(a.bbox[0] - b.bbox[2], b.bbox[0] - a.bbox[2], 0.0), max(a.bbox[1] - b.bbox[3], b.bbox[1] - a.bbox[3], 0.0))
            if gap <= link_mm:
                parent[find(i)] = find(j)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return sorted(groups.values(), key=lambda g: g[0])


def _bbox_of(poly):
    """!
    @brief Box of a polygon.
    @param poly List of (x, y).
    @return tuple (xmin, ymin, xmax, ymax).
    """
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def part_from_openings(designator, openings, shape="hull", source="paste only", from_file=None, footprint="", side=None):
    """!
    @brief Make an `ImportPart` from the openings of one part (the click, the proximity fallback, `TO.C`).
    @param designator Designator (the key of the part in a re-import; "H<n>" for a part picked by hand).
    @param openings List of Opening of the part.
    @param shape "hull" (suggested), "box" or "largest": the heat-source polygon taken.
    @param source Source of the match, one of `SOURCES`.
    @param from_file Dict of file data to start from (copied).
    @param footprint Footprint name when known.
    @param side "top" or "bottom"; the side of the first opening when None.
    @return ImportPart (power 0, no edits).
    """
    ff = dict(from_file or {})
    ff["source"] = source
    ff["n_openings"] = len(openings)
    return ImportPart(designator, shape, [list(map(float, p)) for p in shape_polygon(openings, shape)], 0.0, {}, footprint,
                      side or (openings[0].side if openings else ""), ff)


# ------------------------------------------------------------------------------------------------------------------------------ build
@dataclass
class PartsResult:
    """!
    @brief The parts of an import: the heat-source candidates, the parts that are only listed, the openings no file names, and what was found on the way.
    """
    parts: list = field(default_factory=list)        # ImportPart with a heat-source polygon
    listed: list = field(default_factory=list)       # ImportPart without a polygon (through-hole, connectors): listed, not an error
    unmatched: list = field(default_factory=list)    # Opening no file names (the user clicks them)
    openings: list = field(default_factory=list)     # Every Opening read
    shapes: dict = field(default_factory=dict)       # designator -> {"box": polygon, "hull": polygon} for the re-import
    info: dict = field(default_factory=dict)         # convention, frame check, counts by source, warnings


def _x3_note(components, placement):
    """!
    @brief Compare an X3 component layer with a placement file (parts in one and not in the other; positions farther than 0.5 mm).
    @param components List of Component.
    @param placement List of placement dicts.
    @return dict only_x3, only_placement, moved (list of (ref, distance in mm)).
    """
    cx = {c.ref: c for c in components}
    px = {p["ref"]: p for p in placement}
    moved = []
    for r in cx.keys() & px.keys():
        c, p = cx[r], px[r]
        if c.origin is not None:
            d = math.hypot(c.origin[0] - p["x"], c.origin[1] - p["y"])
            if d > 0.5:
                moved.append((r, round(d, 3)))
    return {"only_x3": sorted(cx.keys() - px.keys()), "only_placement": sorted(px.keys() - cx.keys()), "moved": sorted(moved)}


def _x3_part(comp, ops, shape):
    """!
    @brief The ImportPart of an X3 component.
    @param comp Component.
    @param ops Openings of the part (paste linked by `TO.C`).
    @param shape "hull" or "box": the polygon taken from the openings when the paste is the source.
    @return tuple (ImportPart, {"box": polygon, "hull": polygon}).
    """
    paste_hull = shape_polygon(ops, "hull") if ops else None
    poly, src = heat_polygon(comp, paste_hull)
    if src == "paste" and shape == "box":
        poly = shape_polygon(ops, "box")
    ff = {"value": comp.value, "mount": comp.mount, "rotation_deg": comp.rotation, "package": comp.package, "source": "x3", "shape_source": src,
          "position_mm": [comp.origin[0], comp.origin[1]] if comp.origin else None, "n_openings": len(ops)}
    if comp.height_mm is not None:
        ff["height_mm"] = comp.height_mm
    if comp.mpn:
        ff["mpn"] = comp.mpn
    if comp.manufacturer:
        ff["manufacturer"] = comp.manufacturer
    if comp.library:
        ff["library"] = comp.library
    part = ImportPart(comp.ref, ("hull" if src in ("paste", "pins") and shape != "box" else "box" if src == "paste" else "outline"),
                      [list(map(float, p)) for p in (poly or [])], 0.0, {}, comp.footprint, comp.side, ff)
    shapes = {"box": shape_polygon(ops, "box"), "hull": shape_polygon(ops, "hull")} if ops else {}
    return part, shapes


def build_parts(paste=None, placement=None, components=None, copper=None, pix=PASTE_PIXEL_MM, tol=ENVELOPE_TOLERANCE_MM, shape="hull", bottom="auto",
                offset=(0.0, 0.0), proximity_fallback=False, use_refs=True):
    """!
    @brief The parts of an import from the paste layers, the placement file and the X3 component layers.
    @details Order of trust: X3 (every component, exact), then `TO.C` of the paste file with the placement file for value and package, then the envelope rule by position, then "paste only". A board with
             both an X3 layer and a placement file uses the X3 layer; `info["x3_vs_placement"]` says where the two differ. The bottom-side X convention of the placement file is detected from the
             openings (`bottom` = "auto"; or "as is" / "negated X" to force it) and `info["frame"]` holds the frame check with the offset it proposes; the offset is applied only when given in `offset`
             (mm, added to the part positions of the placement file). Parts with no opening (through-hole headers, connectors) are returned in `listed`, with no polygon.
    @param paste Dict {"top": Layer, "bottom": Layer} of the paste layers (either may be missing).
    @param placement List of placement dicts (`read_placement`), or None.
    @param components List of Component (the X3 layers, top and bottom together), or None.
    @param copper List of copper `parser.Layer` (to report how the X3 pins sit on the copper pads), or None.
    @param pix Raster pixel of the paste in mm.
    @param tol Tolerance of the pad envelope in mm.
    @param shape "hull" (default) or "box": the heat-source polygon of a part from its openings.
    @param bottom "auto", "as is" or "negated X": the X convention of bottom-side parts in the placement file.
    @param offset Offset (dx, dy) in mm added to the part positions of the placement file.
    @param proximity_fallback True: openings nobody names are grouped by proximity into parts P1, P2, ... (marked, "paste only"); False: they are returned in `unmatched`.
    @param use_refs True: read the `TO.C` designators of the paste files.
    @return PartsResult.
    """
    paste = paste or {}
    res = PartsResult()
    info = res.info
    info.update(convention="as is", frame=None, counts={s: 0 for s in SOURCES}, warnings=[], x3_vs_placement=None, unknown_refs=[], copper=None)
    openings = []
    for side in ("top", "bottom"):
        if paste.get(side) is not None:
            openings += read_openings(paste[side], side, pix, by_ref=use_refs)
    res.openings = openings
    claimed = set()

    def add(part, shapes, listed_only=False):
        """!@brief Store a part in the result. @param part ImportPart. @param shapes Dict of the two shapes. @param listed_only True: no heat source. @return None."""
        (res.listed if listed_only or not part.polygon_mm else res.parts).append(part)
        res.shapes[part.designator] = shapes
        info["counts"][part.from_file.get("source", "")] = info["counts"].get(part.from_file.get("source", ""), 0) + 1

    # --- 1. The X3 component layer: every component, linked to the paste by TO.C
    if components:
        dup = duplicate_references(components)
        if dup:
            info["warnings"].append("duplicate references in the component layer (first one kept): " + ", ".join(dup))
        seen = set()
        by_ref = {}
        for i, o in enumerate(openings):
            if o.ref:
                by_ref.setdefault(o.ref, []).append(i)
        for c in components:
            if c.ref in seen or c.origin is None:
                if c.origin is None:
                    info["warnings"].append(f"{c.ref}: component without ComponentMain flash, skipped")
                continue
            seen.add(c.ref)
            idx = [i for i in by_ref.get(c.ref, []) if openings[i].side == c.side]
            claimed.update(idx)
            part, shapes = _x3_part(c, [openings[i] for i in idx], shape)
            add(part, shapes, listed_only=not part.polygon_mm)
        known = {c.ref for c in components}
        info["unknown_refs"] = sorted({o.ref for o in openings if o.ref and o.ref not in known})
        if placement:
            info["x3_vs_placement"] = _x3_note(components, placement)
        if copper:
            cl = link_copper(components, copper)
            info["copper"] = {"pins_matched": cl.pins_matched, "pins_total": cl.pins_total, "max_offset_mm": cl.max_offset_mm, "unknown_refs": cl.unknown_refs}
        res.unmatched = [o for i, o in enumerate(openings) if i not in claimed]
        _fallback(res, proximity_fallback)
        return res

    # --- 2. TO.C of the paste file, with the placement file for value, package and rotation
    plc = {p["ref"]: p for p in (placement or [])}
    by_ref = {}
    for i, o in enumerate(openings):
        if o.ref:
            by_ref.setdefault(o.ref, []).append(i)
    # --- 3. The placement file by position, for the openings that carry no TO.C
    plain = [i for i, o in enumerate(openings) if not o.ref]
    parts_pl = [p for p in (placement or []) if p["ref"] not in by_ref]
    if parts_pl and plain:
        open_plain = [openings[i] for i in plain]
        conv = bottom
        if bottom == "auto":
            conv = bottom_convention(parts_pl, open_plain, tol)[0]
        info["convention"] = conv
        parts_pl = apply_bottom_convention(parts_pl, conv)
        if offset != (0.0, 0.0):
            parts_pl = apply_offset(parts_pl, *offset)
        info["frame"] = frame_check(parts_pl, open_plain, tol)
        if info["frame"]["propose"]:
            info["warnings"].append(f"the placement file may use another origin: an offset of ({info['frame']['dx']:+.2f}, {info['frame']['dy']:+.2f}) mm raises the parts with an opening from "
                                    f"{info['frame']['given']:.0%} to {info['frame']['best']:.0%}")
        byref_pl, _ = match_envelope(parts_pl, open_plain, tol)
    else:
        byref_pl = {}
    for ref, idx in by_ref.items():
        ops = [openings[i] for i in idx]
        claimed.update(idx)
        p = plc.get(ref)
        src = "to.c+placement" if p else "paste only"
        ff = {}
        if p:
            ff.update(value=p["value"], package=p["package"], rotation_deg=p["rot"], position_mm=[p["x"], p["y"]])
        part = part_from_openings(ref, ops, shape, src, ff, p["package"] if p else "", ops[0].side)
        add(part, {"box": shape_polygon(ops, "box"), "hull": shape_polygon(ops, "hull")})
    for p in parts_pl:
        r = p["ref"]
        idx = [plain[k] for k in byref_pl.get(r, [])]
        ff = {"value": p["value"], "package": p["package"], "rotation_deg": p["rot"], "position_mm": [p["x"], p["y"]]}
        if not idx:
            ff["source"] = SOURCE_NO_OPENING
            part = ImportPart(r, "box", [], 0.0, {}, p["package"], p["side"], ff)
            res.listed.append(part)
            info["counts"][SOURCE_NO_OPENING] = info["counts"].get(SOURCE_NO_OPENING, 0) + 1
            continue
        ops = [openings[i] for i in idx]
        claimed.update(idx)
        part = part_from_openings(r, ops, shape, "placement by position", ff, p["package"], p["side"])
        add(part, {"box": shape_polygon(ops, "box"), "hull": shape_polygon(ops, "hull")})
    res.unmatched = [o for i, o in enumerate(openings) if i not in claimed]
    _fallback(res, proximity_fallback)
    return res


def _fallback(res, enabled):
    """!
    @brief Group the unmatched openings by proximity into parts P1, P2, ... when asked (marked as the fallback: `from_file["grouping"] == "proximity"`).
    @param res PartsResult (changed in place).
    @param enabled True to group.
    @return None
    """
    if not enabled or not res.unmatched:
        return
    for k, grp in enumerate(proximity_groups(res.unmatched), start=1):
        ops = [res.unmatched[i] for i in grp]
        part = part_from_openings(f"P{k}", ops, "hull", "paste only", {"grouping": "proximity"})
        res.parts.append(part)
        res.shapes[part.designator] = {"box": shape_polygon(ops, "box"), "hull": shape_polygon(ops, "hull")}
        res.info["counts"]["paste only"] += 1
    res.unmatched = []


# ------------------------------------------------------------------------------------------------------------------------------ re-import
def _centre_size(poly):
    """!
    @brief Centre and sorted sides of the box of a polygon (a quarter turn leaves the sorted sides unchanged).
    @param poly List of (x, y) or empty.
    @return tuple ((cx, cy), (short, long)) or None for an empty polygon.
    """
    if not poly:
        return None
    x0, y0, x1, y1 = _bbox_of(poly)
    return ((x0 + x1) / 2, (y0 + y1) / 2), tuple(sorted((x1 - x0, y1 - y0)))


def diff_parts(old, new, move_mm=0.3, resize_mm=0.2):
    """!
    @brief The table a user reads before confirming an update: new, removed, moved (centre shifted by more than `move_mm`), resized (a side changed by more than `resize_mm`), rotated (the sides swapped), kept.
    @param old List of ImportPart already in the project.
    @param new List of ImportPart of the new files.
    @param move_mm Centre shift that counts as moved (mm).
    @param resize_mm Change of a side that counts as resized (mm).
    @return list of dicts: ref, change (text), detail.
    """
    o = {p.designator: p for p in old}
    n = {p.designator: p for p in new}
    rows = []
    for ref in sorted(o.keys() | n.keys()):
        a, b = o.get(ref), n.get(ref)
        if a is None:
            rows.append({"ref": ref, "change": "new", "detail": ""})
            continue
        if b is None:
            rows.append({"ref": ref, "change": "removed", "detail": "not in the new files"})
            continue
        ca, cb = _centre_size(a.polygon_mm), _centre_size(b.polygon_mm)
        changes, detail = [], []
        if ca and cb:
            d = math.hypot(ca[0][0] - cb[0][0], ca[0][1] - cb[0][1])
            if d > move_mm:
                changes.append("moved")
                detail.append(f"{d:.2f} mm")
            if max(abs(ca[1][0] - cb[1][0]), abs(ca[1][1] - cb[1][1])) > resize_mm:
                changes.append("resized")
                detail.append(f"{ca[1][0]:.2f} x {ca[1][1]:.2f} to {cb[1][0]:.2f} x {cb[1][1]:.2f} mm")
        rows.append({"ref": ref, "change": " and ".join(changes) or "kept", "detail": ", ".join(detail)})
    return rows


@dataclass
class MergeResult:
    """!@brief The outcome of a re-import merge: the parts, the changes as text lines and the designators kept as orphans."""
    parts: list
    changes: list
    orphans: list


def merge_parts(old, new, shapes=None, remove=()):
    """!
    @brief Merge the parts of a new import into the stored ones: copper, drills and outline come from the new files elsewhere; here, a part with the same designator keeps its power and its `edits` and takes the
           `from_file` and the polygon of the new files; the user's shape choice (`edits["shape_user"]`) is applied to the NEW openings; a part that is not in the new files is an orphan.
    @details An orphan is kept (power and edits intact) with `from_file["orphan"] = True` and is not a heat source (consumers check the flag); it is removed only when listed in `remove`.
    @param old List of ImportPart stored in the project.
    @param new List of ImportPart of the new files.
    @param shapes Dict designator -> {"box": polygon, "hull": polygon} of the new import (`PartsResult.shapes`), or None.
    @param remove Designators the user confirmed to remove.
    @return MergeResult.
    """
    shapes = shapes or {}
    o = {p.designator: p for p in old}
    merged, changes, orphans = [], [], []
    for p in new:
        q = copy.deepcopy(p)
        a = o.get(p.designator)
        if a is not None:
            q.power = a.power
            q.edits = copy.deepcopy(a.edits)
            q.extra = copy.deepcopy(a.extra)
            if a.edits.get("shape_user") and a.shape in shapes.get(p.designator, {}):
                q.shape = a.shape
                q.polygon_mm = [list(map(float, pt)) for pt in shapes[p.designator][a.shape]]
            changes.append(f"{p.designator}: kept power {a.power:g} W" if a.power else f"{p.designator}: matched")
        merged.append(q)
    new_refs = {p.designator for p in new}
    for ref, a in o.items():
        if ref in new_refs:
            continue
        if ref in remove:
            changes.append(f"{ref}: removed (confirmed)")
            continue
        q = copy.deepcopy(a)
        q.from_file = dict(q.from_file, orphan=True)
        merged.append(q)
        orphans.append(ref)
        changes.append(f"{ref}: not in the new files, kept as an orphan until confirmed")
    return MergeResult(merged, changes, orphans)
