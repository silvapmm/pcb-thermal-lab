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
            name), no footprint library is read. Before it, the frame of the placement file is checked: the bottom-side X convention (as written or negated, a KiCad option) is detected from the openings
            (with the offset, when one is given), the mirror of an off-centre bottom footprint too (the specification's local-x flip, or the same turned by 180 degrees), and a frame check proposes an
            offset when it aligns clearly more parts (thresholds `FRAME_*`, measured on four real boards) or says that the files do not fit at all.
         4. "paste only": an opening no file names; the user clicks it (the largest opening under the point) and the heat-source shape is suggested as the convex hull (the box is available); grouping
            openings by proximity is a marked fallback only. Such parts have a name the files do not give (H<n>, P<n>): a re-import matches them by position (`merge_parts`).
         The openings are drawn cluster by cluster at 0.05 mm, so the pixel does not grow with the size of the board; a paste layer with a negative image is refused.
         Limits (carried from the research): the envelope table is small (TSOP, USB-C, batteries are guessed); an opening of a part that the placement file does not list, inside the envelope of a listed
         neighbour, is taken by it (cmm2: 9 of 494 openings); an origin offset beyond 10 mm, a rotated or mirrored placement file are not corrected (the import says the files do not fit); the
         rotation of an off-centre bottom footprint in a KiCad placement file was not checked on a real board (none has one).
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
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from ..model import ImportPart
from .errors import UnsupportedFeatureError
from .components import duplicate_references, heat_polygon, hull as _hull, link_copper, polygon_area
from .raster import Window, rasterize

## The sources of a match, in order of trust (ImportPart.from_file["source"]).
SOURCES = ("x3", "to.c+placement", "placement by position", "paste only")
## Source of a part that the placement file lists but no paste opening belongs to (through-hole parts, connectors): listed, no heat source.
SOURCE_NO_OPENING = "placement only"
## Tolerance (mm) added to the pad envelope of a part.
ENVELOPE_TOLERANCE_MM = 0.3
## Raster pixel (mm) of the paste layers (the research used 0.05 mm: the opening of a 0201 pad is 0.25 mm).
PASTE_PIXEL_MM = 0.05
## Largest number of pixels of a side of the raster of one cluster of paste objects; a single cluster larger than this (150 mm at 0.05 mm) gets a coarser pixel.
MAX_PASTE_SIDE_PIXELS = 3000
## Side (mm) up to which a box is paired with its neighbours through a k-d tree when the objects are clustered; larger boxes are tested against all.
_SMALL_BOX_MM = 2.0


# ------------------------------------------------------------------------------------------------------------------------------ placement files
## Largest placement file read (bytes): a real one of 60 000 rows is about 4 MB; a larger file is not read into memory.
MAX_PLACEMENT_BYTES = 64 * 1024 * 1024
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
    @throws ValueError If the text holds no number or the number is not finite.
    """
    m = re.fullmatch(r"\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(mm|mils?|in|inch|inches)?\s*", text, re.I)
    if not m:
        raise ValueError(f"not a length: {text[:40]!r}")
    v = float(m.group(1)) * _UNIT_MM[(m.group(2) or default_unit).lower()]
    if not math.isfinite(v):
        raise ValueError(f"not a finite length: {text[:40]!r}")
    return v


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
    @return list of dicts with ref, value, package, x, y (mm), rot (degrees), side ("top"/"bottom"); value, package, rot and side a file lacks are "", 0.0 and "top". Rows are kept as
            written: a designator repeated is returned twice (`build_parts` keeps the first and warns).
    @throws ValueError If no header with a reference column and X and Y columns is found, or a row (named by its line number) has a value that is not a finite number or no X or Y.
    """
    header, rows, delim, unit = None, [], None, "mm"
    label = name or "file"
    text = text.lstrip("\ufeff")                                       # a byte order mark (Excel, some exporters) would hide the first `#` or header cell
    for lineno, ln in enumerate(text.splitlines(), start=1):
        if not ln.strip():
            continue
        if ln.startswith("##"):                                       # KiCad text report: comment lines (the unit is one of them)
            m = re.search(r"unit\s*=\s*([a-z]+)", ln, re.I)
            if m and m.group(1).lower() in _UNIT_MM:
                unit = {"mils": "mil", "inch": "in", "inches": "in"}.get(m.group(1).lower(), m.group(1).lower())
            continue
        if header is None:
            body = ln[1:].lstrip() if ln.startswith("#") else ln
            # The separator: of the comma, semicolon and tab present, the one that splits the line into the most cells and gives a header (a semicolon header may hold a comma in
            # "Pos X (mm, abs)"); blanks only when none does (the KiCad text report "Ref Val Package PosX ...")
            tries = sorted(((len(next(csv.reader([body], delimiter=d))), d) for d in (",", ";", "\t") if d in body), reverse=True)
            for _, d in tries + [(0, None)]:
                cells = next(csv.reader([body], delimiter=d)) if d else body.split()
                keys = [_field_of(c) for c in cells]
                if "ref" in keys and "x" in keys and "y" in keys:
                    header, delim = cells, d
                    break
            if header is not None:
                continue
            if ln.startswith("#"):                                    # another comment line of the report
                continue
            raise ValueError(f"{label}: no placement header found (first line {ln[:60]!r})")
        if ln.startswith("#"):
            continue
        if delim:
            cells = next(csv.reader([ln], delimiter=delim))
        else:
            try:
                cells = shlex.split(ln)                              # quoted values with blanks ("10 k")
            except ValueError:
                cells = ln.split()
        rows.append((lineno, cells))
    if header is None:
        raise ValueError(f"{label}: empty placement file")
    keys = [_field_of(c) for c in header]
    units = [_header_unit(c) or unit for c in header]
    out = []
    for lineno, r in rows:
        d = {"ref": "", "value": "", "package": "", "x": None, "y": None, "rot": 0.0, "side": "top"}
        for k, u, v in zip(keys, units, r):
            if delim in (";", "\t"):
                v = v.replace(",", ".") if k in ("x", "y", "rot") else v
            try:
                if k in ("x", "y"):
                    d[k] = _length_mm(v, u) if v.strip() else None
                elif k == "rot":
                    rv = float(re.sub(r"[^0-9eE.+-]", "", v) or 0.0)
                    if not math.isfinite(rv):
                        raise ValueError(f"not a finite rotation: {v[:40]!r}")
                    d[k] = rv
                elif k == "side":
                    d[k] = _side(v)
                elif k in ("ref", "value", "package"):
                    d[k] = v.strip().strip('"')
            except ValueError as exc:
                raise ValueError(f"{label}, line {lineno}: {exc}") from None
        if not d["ref"]:
            continue
        if d["x"] is None or d["y"] is None:
            # A short row would otherwise put the part at the origin without a word
            raise ValueError(f"{label}, line {lineno}: {d['ref']} has no X or Y value")
        out.append(d)
    return out


def read_placement(path):
    """!
    @brief Read a placement file from disk.
    @param path File path.
    @return list of dicts as `parse_placement`.
    @throws ValueError If the file is not a placement file or is larger than `MAX_PLACEMENT_BYTES`.
    """
    p = Path(path)
    if p.stat().st_size > MAX_PLACEMENT_BYTES:
        raise ValueError(f"{p.name}: {p.stat().st_size} bytes is more than a placement file holds (limit {MAX_PLACEMENT_BYTES} bytes)")
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
    sub._boxes = layer.op_boxes()[np.asarray(indices, int)] if len(indices) else None
    sub.negative = False
    return sub


def _clusters(boxes, margin):
    """!
    @brief Groups of operations whose boxes (grown by `margin`) touch, directly or through others: a connected piece of the paste can only lie inside one group, so each group is drawn on
           its own small raster and the pixel does not depend on the size of the board.
    @details Boxes up to `_SMALL_BOX_MM` a side are paired through a k-d tree of their centres; the few larger ones (exposed pads, connectors, a large region) are tested against all boxes.
    @param boxes Array (n, 4) of (xmin, ymin, xmax, ymax) in mm.
    @param margin Growth of every box in mm.
    @return list of index arrays (into `boxes`), each sorted (file order).
    """
    n = len(boxes)
    if n == 0:
        return []
    b = np.asarray(boxes, float)
    side = np.maximum(b[:, 2] - b[:, 0], b[:, 3] - b[:, 1])
    small = np.nonzero(side <= _SMALL_BOX_MM)[0]
    large = np.nonzero(side > _SMALL_BOX_MM)[0]
    rows, cols = [], []
    if len(small) > 1:
        cen = np.column_stack(((b[small, 0] + b[small, 2]) / 2, (b[small, 1] + b[small, 3]) / 2))
        # Two boxes of at most S a side that touch after growing by margin have centres closer than sqrt(2) (S + 2 margin)
        pairs = cKDTree(cen).query_pairs(math.sqrt(2.0) * (_SMALL_BOX_MM + 2 * margin) + 1e-9, output_type="ndarray")
        if len(pairs):
            i, j = small[pairs[:, 0]], small[pairs[:, 1]]
            ok = (b[i, 0] <= b[j, 2] + 2 * margin) & (b[j, 0] <= b[i, 2] + 2 * margin) & (b[i, 1] <= b[j, 3] + 2 * margin) & (b[j, 1] <= b[i, 3] + 2 * margin)
            rows.append(i[ok])
            cols.append(j[ok])
    for k in large:
        ok = (b[:, 0] <= b[k, 2] + 2 * margin) & (b[k, 0] <= b[:, 2] + 2 * margin) & (b[:, 1] <= b[k, 3] + 2 * margin) & (b[k, 1] <= b[:, 3] + 2 * margin)
        j = np.nonzero(ok)[0]
        rows.append(np.full(len(j), k))
        cols.append(j)
    r = np.concatenate(rows) if rows else np.zeros(0, int)
    c = np.concatenate(cols) if cols else np.zeros(0, int)
    graph = coo_matrix((np.ones(len(r), bool), (r, c)), shape=(n, n))
    _, label = connected_components(graph, directed=False)
    order = np.argsort(label, kind="stable")
    cuts = np.nonzero(np.diff(label[order]))[0] + 1
    return [np.sort(g) for g in np.split(order, cuts)]


def _raster_openings(layer, indices, side, ref, pix, margin):
    """!
    @brief Rasterise some operations of a paste layer, cluster by cluster, and return the connected pieces as openings.
    @param layer Parsed `parser.Layer`.
    @param indices Operation indices to draw (dark and the clear ones that may cut them).
    @param side "top" or "bottom".
    @param ref Designator of the objects, or None.
    @param pix Raster pixel (mm); a cluster wider than `MAX_PASTE_SIDE_PIXELS` pixels gets a coarser one.
    @param margin Margin around the box of a cluster (mm).
    @return list of Opening.
    """
    idx = np.asarray(sorted(indices), int)
    if len(idx) == 0:
        return []
    boxes = layer.op_boxes()[idx]
    out = []
    for g in _clusters(boxes, margin):
        if not any(layer.ops[i][1] for i in idx[g]):
            continue                                                   # clear objects alone draw nothing
        sub = _sub_layer(layer, idx[g])
        bb = sub.bbox()
        p = max(pix, max(bb[2] - bb[0], bb[3] - bb[1]) / MAX_PASTE_SIDE_PIXELS)
        win = Window(bb[0] - margin, bb[3] + margin, bb[2] - bb[0] + 2 * margin, bb[3] - bb[1] + 2 * margin)
        cov = rasterize(sub, win, p, supersample=1)
        out += _openings_of_mask(cov >= 128, win.x_left, win.y_top, p, side, ref)
    return out


## Aperture functions of objects that a paste layer may carry but that are not stencil openings (Gerber specification, "All data layers", p. 158).
NOT_STENCIL_FUNCTIONS = ("Profile", "NonMaterial")


def _not_stencil(op):
    """!
    @brief Whether an operation of a paste layer is a drawing element, not an opening: a stroke or flash whose aperture function is `Profile` or `NonMaterial`.
    @param op Operation (kind, dark, args) of `parser.Layer.ops`.
    @return bool.
    """
    if op[0] == "region":
        return False
    func = getattr(op[2][0], "func", "") or ""
    return func.split(",")[0].strip() in NOT_STENCIL_FUNCTIONS


def check_paste_polarity(layer):
    """!
    @brief Refuse a paste layer whose image is negative (`%IPNEG*%`, or the X2 attribute `%TF.FilePolarity,Negative*%`): the dark objects would then be the stencil, not the openings,
           and reading them as openings would invent parts. Clear objects (`%LPC*%`) inside a positive layer are handled (they cut the openings in file order).
    @param layer Parsed paste `parser.Layer`.
    @return None
    @throws UnsupportedFeatureError For a negative paste layer (the file and the feature are named).
    """
    if layer.negative:
        raise UnsupportedFeatureError(layer.name, "a paste layer with negative image polarity (IPNEG)")
    if [v.lower() for v in layer.attributes.get("FilePolarity", [])][:1] == ["negative"]:
        raise UnsupportedFeatureError(layer.name, "a paste layer with negative file polarity (TF.FilePolarity,Negative)")


def read_openings(layer, side="top", pix=PASTE_PIXEL_MM, by_ref=True):
    """!
    @brief The individual openings of a paste layer (a connected piece of the dark objects is one opening; no grouping).
    @details With `by_ref` and a layer that carries `TO.C`, every designator is drawn apart, so that openings of two parts that touch stay two and each opening knows its part; the objects
             without `TO.C` are drawn together. Without `TO.C` (or with `by_ref` False) the whole layer is one group. Clear objects that meet the box of a group are drawn with it, in file order.
             A group is drawn cluster by cluster (operations whose boxes touch), each on its own small raster at `pix`, so the pixel does not grow with the board or with a stray object
             far away (review: one raster of the whole layer coarsened the pixel to 0.1 mm on a 300 mm board, up to 42 % off in the area of a 0201 opening); only a single cluster wider than
             `MAX_PASTE_SIDE_PIXELS` pixels gets a coarser pixel. Objects with the aperture function `Profile` (the board outline plotted on every layer) or `NonMaterial` are not openings
             and are left out.
    @param layer Parsed paste `parser.Layer`.
    @param side "top" or "bottom".
    @param pix Raster pixel in mm.
    @param by_ref True: use `TO.C` when the layer has it.
    @return list of Opening in the order of the references (file order) then the rest.
    @throws UnsupportedFeatureError For a paste layer with a negative image (`check_paste_polarity`).
    """
    check_paste_polarity(layer)
    if layer.bbox() is None:
        return []
    margin = 2 * pix
    # Objects that are not stencil: the board profile that a CAD tool plots on every layer (aperture function `Profile`, StickHub and Coldfire) and drawing elements
    # (`NonMaterial`); review: the profile of Coldfire became an "opening" of 183 mm2 whose hull is the board, so every click selected it
    drawn = [i for i, op in enumerate(layer.ops) if not _not_stencil(op)]
    dark = [i for i in drawn if layer.ops[i][1]]
    clear = [i for i in drawn if not layer.ops[i][1]]
    if not (by_ref and layer.references()):
        return _raster_openings(layer, dark + clear, side, None, pix, margin)
    groups = {}
    for i in dark:
        groups.setdefault(layer.attrs(i).ref, []).append(i)
    boxes = layer.op_boxes()
    clear_arr = np.asarray(clear, int)
    out = []
    for ref, idx in groups.items():
        near = list(idx)
        if clear:
            x0, y0 = boxes[idx, 0].min() - margin, boxes[idx, 1].min() - margin
            x1, y1 = boxes[idx, 2].max() + margin, boxes[idx, 3].max() + margin
            cb = boxes[clear_arr]
            near += clear_arr[(cb[:, 0] <= x1) & (cb[:, 2] >= x0) & (cb[:, 1] <= y1) & (cb[:, 3] >= y0)].tolist()
        out += _raster_openings(layer, near, side, ref, pix, margin)
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


## The mirror of a bottom-side footprint: "x" (the local x changes sign before the rotation; Gerber X3 specification p. 166 and its drawing, `components.to_board`), "y" (the local y changes
## sign: the same as "x" turned by 180 degrees, as a footprint flipped top to bottom in a CAD tool may be stored), or "none" (no mirror).
BOTTOM_MIRRORS = ("x", "y", "none")


def _mirror_kind(mirror_bottom):
    """!
    @brief Normalise the mirror argument of the envelope functions.
    @param mirror_bottom "x", "y", "none", True (= "x") or False/None (= "none").
    @return "x", "y" or "none".
    @throws ValueError For another value.
    """
    if mirror_bottom is True:
        return "x"
    if mirror_bottom is False or mirror_bottom is None:
        return "none"
    if mirror_bottom not in BOTTOM_MIRRORS:
        raise ValueError(f"unknown bottom mirror {mirror_bottom!r}")
    return mirror_bottom


def _rotation(rot_deg, side="top", mirror_bottom="x"):
    """!
    @brief Matrix that takes the local footprint frame of a part to the board frame: the mirror of a bottom-side footprint, then the rotation (counter-clockwise seen from the top).
    @param rot_deg Rotation of the part in degrees (counter-clockwise).
    @param side "top" or "bottom".
    @param mirror_bottom Mirror of a bottom-side footprint, see `BOTTOM_MIRRORS` (True means "x").
    @return numpy.ndarray 2 x 2 (orthogonal).
    """
    a = math.radians(rot_deg)
    c, s = math.cos(a), math.sin(a)
    r = np.array([[c, -s], [s, c]])
    kind = _mirror_kind(mirror_bottom)
    if side == "bottom" and kind != "none":
        r = r @ (np.diag([-1.0, 1.0]) if kind == "x" else np.diag([1.0, -1.0]))
    return r


def part_envelope_polygon(part, margin=0.0, mirror_bottom="x"):
    """!
    @brief Board-frame corners of the pad envelope of a part.
    @param part Dict with package, x, y (mm), rot (degrees), side.
    @param margin Growth of the envelope on every side (mm).
    @param mirror_bottom Mirror of a bottom-side footprint, see `BOTTOM_MIRRORS` (the specification's "x" by default).
    @return numpy.ndarray 4 x 2 corners in mm.
    """
    lx, ly, ox, oy = envelope(part["package"])[:4]
    hx, hy = lx / 2 + margin, ly / 2 + margin
    loc = np.array([[ox - hx, oy - hy], [ox + hx, oy - hy], [ox + hx, oy + hy], [ox - hx, oy + hy]])
    return loc @ _rotation(part["rot"], part["side"], mirror_bottom).T + np.array([part["x"], part["y"]])


def _inside_envelope(part, xs, ys, margin, mirror_bottom="x"):
    """!
    @brief Which points lie inside the pad envelope of a part (grown by a margin).
    @param part Dict with package, x, y, rot, side.
    @param xs X of the points (mm).
    @param ys Y of the points (mm).
    @param margin Growth of the envelope on every side (mm).
    @param mirror_bottom Mirror of a bottom-side footprint, see `BOTTOM_MIRRORS` (the specification's "x" by default).
    @return tuple (boolean array, envelope area in mm2).
    """
    lx, ly, ox, oy = envelope(part["package"])[:4]
    r = _rotation(part["rot"], part["side"], mirror_bottom)
    d = np.stack([np.asarray(xs) - part["x"], np.asarray(ys) - part["y"]])
    loc = r.T @ d                                                      # world = R local + position, R orthogonal
    ok = (np.abs(loc[0] - ox) <= lx / 2 + margin + 1e-9) & (np.abs(loc[1] - oy) <= ly / 2 + margin + 1e-9)
    return ok, (lx + 2 * margin) * (ly + 2 * margin)


def match_envelope(parts, openings, tol=ENVELOPE_TOLERANCE_MM, mirror_bottom="x"):
    """!
    @brief The envelope rule: every opening goes to the part (same side) whose rotated pad envelope, grown by `tol`, contains its centre; the smallest envelope wins; one part may take many openings.
    @param parts List of dicts (ref, package, x, y, rot, side) in the frame of the Gerber files.
    @param openings List of Opening.
    @param tol Tolerance added to the envelope in mm.
    @param mirror_bottom Mirror of a bottom-side footprint, see `BOTTOM_MIRRORS` (the specification's "x" by default; it matters only for an envelope off the part origin).
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


CONVENTION_NOT_CHECKED = "not checked"      # info["convention"] when the files hold nothing to check it with (no placement file, or no bottom parts or openings)


def bottom_convention(parts, openings, tol=ENVELOPE_TOLERANCE_MM, offset=(0.0, 0.0), mirror_bottom="x"):
    """!
    @brief Detect whether the placement file writes the X of bottom-side parts negated (a KiCad export option), by trying both and keeping the one that puts more bottom openings inside an envelope.
    @details The local mirror of the footprint does not decide it: every SMD envelope of the name table is centred, so a mirror (and the sign of a rotation by a multiple of 90 degrees) leaves it unchanged.
             A tie keeps the file as it is. The offset of the frame check is applied after the negation (KiCad writes `-(x - origin)`), so a file that is both negated and offset is
             detected once the offset is known (review: the detection ran before the offset and fell back to "as is").
    @param parts List of dicts (ref, package, x, y, rot, side), positions in mm as the file writes them.
    @param openings List of Opening.
    @param tol Tolerance added to the envelope in mm.
    @param offset Offset (dx, dy) in mm added after the convention.
    @param mirror_bottom Mirror of a bottom-side footprint, see `BOTTOM_MIRRORS`.
    @return tuple (convention "as is" or "negated X", openings assigned as is, openings assigned negated).
    """
    bp = [p for p in parts if p["side"] == "bottom"]
    bo = [o for o in openings if o.side == "bottom"]
    if not bp or not bo:
        return "as is", 0, 0
    n_as = len(match_envelope(apply_offset(bp, *offset), bo, tol, mirror_bottom)[1])
    n_neg = len(match_envelope(apply_offset([dict(p, x=-p["x"]) for p in bp], *offset), bo, tol, mirror_bottom)[1])
    return ("negated X" if n_neg > n_as else "as is"), n_as, n_neg


def bottom_mirror(parts, openings, tol=ENVELOPE_TOLERANCE_MM):
    """!
    @brief Which mirror of a bottom-side footprint puts more bottom openings inside an envelope: the specification's "x" or "y" (the same turned by 180 degrees).
    @details Only an envelope off the part origin (a pin header, a micro USB socket) can tell them apart; with none, or a tie, the specification's "x" is kept. The rotation of a bottom part in
             the placement file of a CAD tool may follow either (the KiCad placement file was not checked on a bottom part with an off-centre footprint: no such board).
    @param parts List of part dicts in the frame of the Gerber files (bottom convention and offset applied).
    @param openings List of Opening.
    @param tol Tolerance added to the envelope in mm.
    @return tuple (mirror "x" or "y", openings assigned with "x", openings assigned with "y").
    """
    bp = [p for p in parts if p["side"] == "bottom" and envelope(p["package"])[2:4] != (0, 0)]
    bo = [o for o in openings if o.side == "bottom"]
    if not bp or not bo:
        return "x", 0, 0
    n_x = len(match_envelope(bp, bo, tol, "x")[1])
    n_y = len(match_envelope(bp, bo, tol, "y")[1])
    return ("y" if n_y > n_x else "x"), n_x, n_y


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


def _known_smd(parts):
    """!
    @brief The parts whose envelope is an SMD pattern of the name table (the ones the frame check counts).
    @param parts List of part dicts.
    @return list of part dicts.
    """
    return [p for p in parts if envelope(p["package"])[4] == "smd" and envelope(p["package"])[5]]


## Frame check: an offset is proposed only when it raises the share of SMD parts with their openings by at least FRAME_MIN_GAIN (and by FRAME_MIN_PARTS parts), when the share it reaches is at
## least FRAME_MIN_BEST, and when it is at least FRAME_MIN_SHIFT_MM long. Measured by the review on the four real boards (rp2040, cmm2, isastm, oswlight; the placement file moved by 0.2 to
## 9.7 mm along X and diagonally, half of its parts removed, rotated by 90 degrees about the origin, mirrored in Y, inches read as mm): files that agree or are off by up to 0.5 mm give a
## gain of 0; every offset of 1 to 9.7 mm is found within 0.05 mm, reaches 1.000 and gains at least 0.60; a shift beyond the search (20 mm) reaches at most 0.535 by coincidence and is not
## proposed; a rotated, mirrored or inch file scores 0. Below a share FRAME_MISFIT with no proposal, the files are said not to fit.
FRAME_MIN_GAIN = 0.1
FRAME_MIN_PARTS = 2
FRAME_MIN_BEST = 0.8
FRAME_MIN_SHIFT_MM = 0.5
FRAME_MISFIT = 0.5


def frame_check(parts, openings, tol=ENVELOPE_TOLERANCE_MM, search_mm=10.0, min_gain=FRAME_MIN_GAIN, min_best=FRAME_MIN_BEST, mirror_bottom="x"):
    """!
    @brief Check that the placement file and the Gerber files share one origin, and propose the offset that aligns them when they do not.
    @details The score of an offset is the number of SMD parts (known envelope) that have their openings in their envelope (both pads for a two-pad passive, one for the others). The search is a grid of 0.5 mm over +-search_mm; many offsets reach
             the top score (the envelope with its tolerance is wider than a pad), so the answer is the centre of that plateau, refined on a 0.1 mm grid over +-1 mm around it (when the
             centre of an irregular plateau scores less, the plateau point nearest to it is taken). The offset is proposed only when it raises the share by `min_gain` and by
             `FRAME_MIN_PARTS` parts, reaches `min_best`, and is at least `FRAME_MIN_SHIFT_MM` long, so a board whose files agree is never moved and an offset beyond the search (which can
             only align a few parts by chance) is not proposed (`FRAME_*` constants, measured on four real boards). `misfit` is True when the share of the file as given is below
             `FRAME_MISFIT` and no offset is proposed: the files do not fit (a rotation, a mirror, a unit or an offset larger than the search). The rule of the envelopes tolerates
             0.5 mm, loses a quarter of the openings at 1 mm and assigns wrong designators silently at 5 mm (research README 11.4).
    @param parts List of part dicts, bottom-side X convention already applied.
    @param openings List of Opening.
    @param tol Tolerance of the envelope in mm.
    @param search_mm Largest offset looked for (mm, each axis).
    @param min_gain Smallest rise of the share that makes the offset a proposal.
    @param min_best Smallest share the offset must reach to be proposed.
    @param mirror_bottom Mirror of a bottom-side footprint, see `BOTTOM_MIRRORS`.
    @return dict: given (share of the parts with their openings as the file is), best (share with the offset), dx, dy (mm to add to the part positions), propose (bool), misfit (bool), n_parts (SMD parts counted).
    """
    smd = _known_smd(parts)
    out = {"given": 0.0, "best": 0.0, "dx": 0.0, "dy": 0.0, "propose": False, "misfit": False, "n_parts": len(smd)}
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
    n = len(smd)
    if len(pair_part) == 0:
        out["misfit"] = True
        return out
    # Per part: rotation transposed (with the bottom mirror, as in _inside_envelope), envelope half-sizes and centre offset
    rt = np.array([_rotation(p["rot"], p["side"], mirror_bottom).T for p in smd])
    half = np.array([[envelope(p["package"])[0] / 2 + tol, envelope(p["package"])[1] / 2 + tol] for p in smd])
    cen = np.array([[envelope(p["package"])[2], envelope(p["package"])[3]] for p in smd])
    rp = rt[pair_part]

    # A two-pad passive of the name table counts only with both pads inside its envelope: with one pad it could be catching a pad of a neighbour, which widens the plateau of the
    # score towards a wrong offset (review: a periodic board with half of its parts missing from the file gave an offset 1.5 mm off)
    need = np.array([2 if re.match(r"^(?:R|C|L|D|LED|F|FB)_(\d{4})_", p["package"]) else 1 for p in smd])

    def score(t):
        """!
        @brief The score of an offset: the parts with their openings inside their envelope (two for a passive, one otherwise) after moving the parts by t.
        @param t Offset (dx, dy) in mm.
        @return int.
        """
        vx, vy = pair_dx - t[0], pair_dy - t[1]
        lx = rp[:, 0, 0] * vx + rp[:, 0, 1] * vy
        ly = rp[:, 1, 0] * vx + rp[:, 1, 1] * vy
        ok = (np.abs(lx - cen[pair_part, 0]) <= half[pair_part, 0] + 1e-9) & (np.abs(ly - cen[pair_part, 1]) <= half[pair_part, 1] + 1e-9)
        return int(np.count_nonzero(np.bincount(pair_part[ok], minlength=n) >= need))

    def centre(cands):
        """!
        @brief The centre of the plateau of a list of scored offsets: the mean of the offsets of the top score, or the plateau point nearest to the mean when the plateau has islands and
               the mean falls outside.
        @param cands List of (score, dx, dy).
        @return tuple (top score, numpy.ndarray (dx, dy)).
        """
        best = max(c[0] for c in cands)
        pts = np.array([(c[1], c[2]) for c in cands if c[0] == best])
        m = pts.mean(axis=0)
        if score(m) < best:
            m = pts[np.argmin(np.hypot(pts[:, 0] - m[0], pts[:, 1] - m[1]))]
        return best, m

    given = score((0.0, 0.0))
    steps = np.arange(-search_mm, search_mm + 1e-9, 0.5)
    # Many offsets reach the top score (the envelope and its tolerance are wider than a pad), so the answer is the CENTRE of the plateau, not its edge nearest to zero
    ctop, c0 = centre([(score((dx, dy)), float(dx), float(dy)) for dx in steps for dy in steps])
    fine = [(score((dx, dy)), float(dx), float(dy)) for dx in np.arange(c0[0] - 1.0, c0[0] + 1.0 + 1e-9, 0.1) for dy in np.arange(c0[1] - 1.0, c0[1] + 1.0 + 1e-9, 0.1)]
    ftop, best_xy = centre(fine)
    if ftop < ctop:
        ftop, best_xy = ctop, c0
    top = ftop
    if top <= given:                                             # the files agree as they are
        top, best_xy = given, np.zeros(2)
    out.update(given=given / n, best=top / n, dx=round(float(best_xy[0]), 3), dy=round(float(best_xy[1]), 3))
    out["propose"] = bool((top - given) / n >= min_gain and top - given >= FRAME_MIN_PARTS and top / n >= min_best and math.hypot(*best_xy) >= FRAME_MIN_SHIFT_MM)
    out["misfit"] = bool(not out["propose"] and given / n < FRAME_MISFIT)
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
# The rule of the exposed pad (research/gerber-real-boards/docs/heater-shape-opinion.md, section 6). First set on ELEVEN PARTS of three open KiCad boards (RP2040 minimal design,
# ISASTM, CMM2), then checked by the review on every part of eight open boards (RP2040, ISASTM, CMM2, oswlight, co60, StickHub X3, Ucamco X3 coldfire and li-ion; 875 parts):
# the first rule (hull ratio at most 0.5, no compactness test) missed the four DPAK (TO-252, group hull 0.60 of the part) and the D2PAK (TO-263, 0.62) of the li-ion charger
# and the coldfire kit, and took eleven parts with two side mounting pads for an exposed pad (seven JST SH connectors, four tactile switches: group fill 0.34 / 0.39, gap 1.9
# to 3.0). With the fill and the gap tests every exposed pad and tab of the eight boards is found (QFN, SOT-223, DPAK, D2PAK, exposed-pad SSOP: fill 0.70 to 1.00, gap at most
# 0.25, hull ratio at most 0.62) and no connector or switch is; the nearest connector is a micro-USB with three mounting pads (fill 0.59, gap 0.66). Not on a physical board,
# and no SOT-89, power SO-8 or LGA with a thermal pad was among the parts. Thin margin: the paste share of the RP2040-QFN-56 (U3) is 0.32 against EXPOSED_MIN_PASTE = 0.25.
# The tables are in tests/test_exposed_pad.py; change a constant only with a new table.
EXPOSED_MIN_AREA = 0.5      # an opening joins the dominant group when its area is at least this share of the largest opening's area
EXPOSED_MIN_PASTE = 0.25    # the group must hold at least this share of the paste area of the part
EXPOSED_MAX_HULL = 0.75     # its hull must be at most this share of the hull of the whole part (USB micro-B J3: 1.0; DPAK 0.60, D2PAK 0.62, QFN 0.08 to 0.36)
EXPOSED_MIN_FILL = 0.5      # the group must fill at least this share of its own hull: one pad or a pad cut in windows (0.70 to 1.00), not pads at two ends (0.34, 0.39)
EXPOSED_MAX_GAP = 0.5       # and be one cluster: no gap between its openings wider than this times the side sqrt(area) of the largest (windows 0.06 to 0.25; mounting pads 0.66 to 3.0)
# The version of the rule written in `from_file["shape_rule"]`: a part from an older project has none, and a re-import then keeps its polygon instead of re-deriving the new default
SHAPE_RULE = "exposed-v1"


def dominant_group(openings):
    """!
    @brief The openings of an exposed pad or a tab, or [] when the part has none.
    @details The openings with at least `EXPOSED_MIN_AREA` of the area of the largest are the candidate group. It is an exposed pad when it is not all the openings (a SOIC, a
             crystal, a 0402 pair have equal pads), holds at least `EXPOSED_MIN_PASTE` of the paste, its hull is at most `EXPOSED_MAX_HULL` of the hull of the part (the six mounting
             pads of a connector hold most of the paste but span the part), its openings fill at least `EXPOSED_MIN_FILL` of its own hull and no gap between them (the longest link
             of the minimum spanning tree of their boxes) is wider than `EXPOSED_MAX_GAP` times the side of the largest opening: one pad or one pad cut in windows, not two mounting
             pads at the ends of a connector or the four legs of a switch. Thresholds: see the comment above them.
    @param openings List of Opening (one part).
    @return list of Opening (the dominant group), empty when the part has no exposed pad or tab.
    """
    if len(openings) < 2:
        return []
    amax = max(o.area for o in openings)
    grp = [o for o in openings if o.area >= EXPOSED_MIN_AREA * amax]
    if len(grp) == len(openings):
        return []
    a_grp = sum(o.area for o in grp)
    if a_grp < EXPOSED_MIN_PASTE * sum(o.area for o in openings):
        return []
    whole = polygon_area(_hull([p for o in openings for p in o.hull]))
    h_grp = polygon_area(_hull([p for o in grp for p in o.hull]))
    if whole <= 0 or h_grp <= 0 or h_grp > EXPOSED_MAX_HULL * whole or a_grp < EXPOSED_MIN_FILL * h_grp:
        return []
    if _largest_gap(grp) > EXPOSED_MAX_GAP * math.sqrt(amax):
        return []
    return grp


def _largest_gap(ops):
    """!
    @brief The widest gap that joins a set of openings into one cluster: the longest edge of the minimum spanning tree of the gaps between their boxes (Prim, O(n^2)).
    @param ops List of Opening.
    @return float in mm (0 for one opening or for boxes that touch).
    """
    def gap(a, b):
        """!@brief Distance between the boxes of two openings. @param a Opening. @param b Opening. @return float in mm (0 when they overlap)."""
        dx = max(a.bbox[0] - b.bbox[2], b.bbox[0] - a.bbox[2], 0.0)
        dy = max(a.bbox[1] - b.bbox[3], b.bbox[1] - a.bbox[3], 0.0)
        return math.hypot(dx, dy)
    if len(ops) < 2:
        return 0.0
    best = {j: gap(ops[0], ops[j]) for j in range(1, len(ops))}
    widest = 0.0
    while best:
        # Join the nearest opening to the tree; the longest join is the gap the cluster needs
        j = min(best, key=best.get)
        widest = max(widest, best.pop(j))
        for k in best:
            best[k] = min(best[k], gap(ops[j], ops[k]))
    return widest


def default_shape_kind(openings):
    """!
    @brief The shape the program proposes for a part: "exposed" when it has an exposed pad or a tab (`dominant_group`), else "hull".
    @param openings List of Opening (one part).
    @return str "exposed" or "hull".
    """
    return "exposed" if dominant_group(openings) else "hull"


def shape_polygon(openings, kind="hull"):
    """!
    @brief The candidate heat-source shape of a set of openings.
    @param openings List of Opening (one part).
    @param kind "hull" (convex hull of all the openings), "box" (the rectangle around them), "exposed" (the hull of the dominant group, the exposed pad or tab; the hull when the part
           has none), "auto" (exposed when the part has an exposed pad, else the hull: the default of the import) or "largest" (the hull of the largest opening: right only for a single tab).
    @return list of (x, y) in mm (counter-clockwise), empty for no openings.
    @throws ValueError For an unknown kind.
    """
    if not openings:
        return []
    if kind == "auto":
        kind = default_shape_kind(openings)
    if kind == "exposed":
        grp = dominant_group(openings) or openings
        return _hull([p for o in grp for p in o.hull])
    if kind == "hull":
        return _hull([p for o in openings for p in o.hull])
    if kind == "box":
        x0, y0 = min(o.bbox[0] for o in openings), min(o.bbox[1] for o in openings)
        x1, y1 = max(o.bbox[2] for o in openings), max(o.bbox[3] for o in openings)
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if kind == "largest":
        return list(max(openings, key=lambda o: o.area).hull)
    raise ValueError(f"unknown shape {kind!r}")


def _set_outer(ff, ops):
    """!
    @brief Write or drop `from_file["outer_mm"]`: the hull of all the openings of a part that has an exposed pad (where the part is; the heat-source polygon is only the pad).
    @param ff Dict of file data (changed in place).
    @param ops List of Opening of the part.
    @return None
    """
    if ops and dominant_group(ops):
        ff["outer_mm"] = [[float(x), float(y)] for x, y in shape_polygon(ops, "hull")]
    else:
        ff.pop("outer_mm", None)


def shape_set(ops):
    """!
    @brief The shapes of a part kept for the re-import: the box and the hull, and the exposed pad when the part has one.
    @param ops List of Opening of the part.
    @return dict kind -> polygon.
    """
    out = {"box": shape_polygon(ops, "box"), "hull": shape_polygon(ops, "hull")}
    if dominant_group(ops):
        out["exposed"] = shape_polygon(ops, "exposed")
    return out


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


def part_from_openings(designator, openings, shape="auto", source="paste only", from_file=None, footprint="", side=None, grouping=None):
    """!
    @brief Make an `ImportPart` from the openings of one part (the click, the proximity fallback, `TO.C`).
    @param designator Designator (the key of the part in a re-import; "H<n>" for a part picked by hand).
    @param openings List of Opening of the part.
    @param shape "auto" (the exposed pad when the part has one, else the hull; the resolved name is stored), "hull", "box", "exposed" or "largest": the heat-source polygon taken.
    @param source Source of the match, one of `SOURCES`.
    @param from_file Dict of file data to start from (copied).
    @param footprint Footprint name when known.
    @param side "top" or "bottom"; the side of the first opening when None.
    @param grouping None for a part named by the files, "hand" for a part picked by a click, "proximity" for the fallback groups: a part with a grouping has a name the files do not
           give, so a re-import matches it by position, not by name (`merge_parts`).
    @return ImportPart (power 0, no edits).
    """
    ff = dict(from_file or {})
    ff["source"] = source
    ff["n_openings"] = len(openings)
    if shape == "auto":
        shape = default_shape_kind(openings)
    # The version of the shape rule: a part without it comes from an older project (the hull was the default) and keeps its polygon in a re-import
    ff["shape_rule"] = SHAPE_RULE
    # With an exposed pad the polygon is only the pad, so the part's region (which openings are its own) is kept apart: the hull of all its openings
    _set_outer(ff, openings)
    if grouping:
        ff["grouping"] = grouping
    return ImportPart(designator, shape, [list(map(float, p)) for p in shape_polygon(openings, shape)], 0.0, {}, footprint,
                      side or (openings[0].side if openings else ""), ff)


# ------------------------------------------------------------------------------------------------------------------------------ build
@dataclass
class PartsResult:
    """!
    @brief The parts of an import: the heat-source candidates, the parts that are only listed, the openings no file names, and what was found on the way.
    """
    parts: list = field(default_factory=list)        # ImportPart with a heat-source polygon (the candidates)
    listed: list = field(default_factory=list)       # ImportPart that is not a heat-source candidate: no opening (placement only, polygon empty) or an X3 part that is not SMD (the offered outline kept, from_file["heat_source"] False); listed, not an error
    unmatched: list = field(default_factory=list)    # Opening no file names (the user clicks them)
    openings: list = field(default_factory=list)     # Every Opening read
    shapes: dict = field(default_factory=dict)       # designator -> {"box", "hull" and, for an exposed pad, "exposed": polygon} for the re-import
    info: dict = field(default_factory=dict)         # convention, frame check, counts by source, warnings


def _x3_note(components, placement):
    """!
    @brief Compare an X3 component layer with a placement file (parts in one and not in the other; positions farther than 0.5 mm).
    @details The bottom-side X of the placement file is taken as written or negated, whichever puts more bottom parts within 0.5 mm of their X3 origin (a KiCad export option negates
             it; the X3 layer is in the frame of the other layers), so a negated file does not read as every bottom part moved.
    @param components List of Component.
    @param placement List of placement dicts.
    @return dict only_x3, only_placement, moved (list of (ref, distance in mm)), bottom_convention ("as is" or "negated X").
    """
    cx = {c.ref: c for c in components}
    px = {p["ref"]: p for p in placement}
    common = [r for r in cx.keys() & px.keys() if cx[r].origin is not None]

    def dist(r, negate):
        """!@brief Distance of the placement position from the X3 origin. @param r Designator. @param negate True: negate the X of a bottom part. @return float mm."""
        c, p = cx[r], px[r]
        x = -p["x"] if negate and p["side"] == "bottom" else p["x"]
        return math.hypot(c.origin[0] - x, c.origin[1] - p["y"])

    bottom = [r for r in common if px[r]["side"] == "bottom"]
    negate = sum(dist(r, True) <= 0.5 for r in bottom) > sum(dist(r, False) <= 0.5 for r in bottom)
    moved = [(r, round(dist(r, negate), 3)) for r in common if dist(r, negate) > 0.5]
    return {"only_x3": sorted(cx.keys() - px.keys()), "only_placement": sorted(px.keys() - cx.keys()), "moved": sorted(moved),
            "bottom_convention": "negated X" if negate else "as is"}


def _x3_part(comp, ops, shape):
    """!
    @brief The ImportPart of an X3 component.
    @param comp Component.
    @param ops Openings of the part (paste linked by `TO.C`).
    @param shape "auto", "hull", "box" or "exposed": the polygon taken from the openings when the paste is the source. With "auto" an exposed pad or tab of the paste goes before the
           Body outline (the mould does not carry the heat); an explicit "hull" or "box" keeps the order of the specification.
    @return tuple (ImportPart, dict of the shapes of the openings).
    """
    paste_hull = shape_polygon(ops, "hull") if ops else None
    exposed = shape_polygon(ops, "exposed") if ops and shape in ("auto", "exposed") and dominant_group(ops) else None
    poly, src = heat_polygon(comp, paste_hull, exposed)
    if src == "paste" and shape == "box":
        poly = shape_polygon(ops, "box")
    ff = {"value": comp.value, "mount": comp.mount, "rotation_deg": comp.rotation, "package": comp.package, "source": "x3", "shape_source": src, "shape_rule": SHAPE_RULE,
          "position_mm": [comp.origin[0], comp.origin[1]] if comp.origin else None, "n_openings": len(ops)}
    if comp.height_mm is not None:
        ff["height_mm"] = comp.height_mm
    if comp.mpn:
        ff["mpn"] = comp.mpn
    if comp.manufacturer:
        ff["manufacturer"] = comp.manufacturer
    if comp.library:
        ff["library"] = comp.library
    # The shape name: "hull" or "box" for the paste openings (as asked), "hull" for the pins, "outline" for an outline of the layer (Body, Lead2Lead, Footprint, Courtyard)
    kind = ("box" if shape == "box" else "hull") if src == "paste" else "exposed" if src == "exposed" else "hull" if src == "pins" else "outline"
    _set_outer(ff, ops)
    if not comp.is_smd:
        # TH, Pressfit, Other, Fiducial or an unknown mount type: listed with the offered shape, not a heat-source candidate (INTEGRATION 12 item 4)
        ff["heat_source"] = False
    part = ImportPart(comp.ref, kind, [list(map(float, p)) for p in (poly or [])], 0.0, {}, comp.footprint, comp.side, ff)
    shapes = shape_set(ops) if ops else {}
    return part, shapes


def _first_of_each(placement, info):
    """!
    @brief Keep the first row of every designator of a placement file and warn about the repeated ones (a designator is the key of a part; two rows of one name would make two parts that share openings).
    @param placement List of placement dicts.
    @param info Dict of `PartsResult.info` (a warning is appended).
    @return list of placement dicts.
    """
    seen, out, dup = set(), [], []
    for p in placement:
        if p["ref"] in seen:
            dup.append(p["ref"])
            continue
        seen.add(p["ref"])
        out.append(p)
    if dup:
        info["warnings"].append("duplicate designators in the placement file (first row kept): " + ", ".join(sorted(set(dup))))
    return out


def build_parts(paste=None, placement=None, components=None, copper=None, pix=PASTE_PIXEL_MM, tol=ENVELOPE_TOLERANCE_MM, shape="auto", bottom="auto",
                offset=(0.0, 0.0), proximity_fallback=False, use_refs=True):
    """!
    @brief The parts of an import from the paste layers, the placement file and the X3 component layers.
    @details Order of trust: X3 (every component, exact), then `TO.C` of the paste file with the placement file for value and package, then the envelope rule by position, then "paste only". A board with
             both an X3 layer and a placement file uses the X3 layer; `info["x3_vs_placement"]` says where the two differ. The bottom-side X convention of the placement file is detected from the
             openings (`bottom` = "auto"; or "as is" / "negated X" to force it) and `info["frame"]` holds the frame check with the offset it proposes; the offset is applied only when given in `offset`
             (mm, added to the part positions of the placement file); the convention is detected with that offset, and the mirror of an off-centre bottom footprint (`bottom_mirror`)
             is detected from the openings as well (`info["bottom_mirror"]`). A placement file that does not fit at all (`info["frame"]["misfit"]`) and repeated designators (first row kept)
             are warned in `info["warnings"]`. Parts with no opening (through-hole headers, connectors) are returned in `listed`, with no polygon; X3 parts whose mount type is not
             SMD are returned in `listed` with their offered outline and `from_file["heat_source"]` False (the user may switch one on).
    @param paste Dict {"top": Layer, "bottom": Layer} of the paste layers (either may be missing).
    @param placement List of placement dicts (`read_placement`), or None.
    @param components List of Component (the X3 layers, top and bottom together), or None.
    @param copper List of copper `parser.Layer` (to report how the X3 pins sit on the copper pads), or None.
    @param pix Raster pixel of the paste in mm.
    @param tol Tolerance of the pad envelope in mm.
    @param shape "auto" (default: the exposed pad of a part that has one, else the hull), "hull", "box" or "exposed": the heat-source polygon of a part from its openings.
    @param bottom "auto", "as is" or "negated X": the X convention of bottom-side parts in the placement file.
    @param offset Offset (dx, dy) in mm added to the part positions of the placement file.
    @param proximity_fallback True: openings nobody names are grouped by proximity into parts P1, P2, ... (marked, "paste only"); False: they are returned in `unmatched`.
    @param use_refs True: read the `TO.C` designators of the paste files.
    @return PartsResult.
    """
    paste = paste or {}
    res = PartsResult()
    info = res.info
    info.update(convention=CONVENTION_NOT_CHECKED, bottom_mirror="x", frame=None, counts={s: 0 for s in SOURCES}, warnings=[], x3_vs_placement=None, unknown_refs=[], copper=None)
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
            add(part, shapes, listed_only=not part.polygon_mm or not c.is_smd)
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
    placement = _first_of_each(placement or [], info)
    plc = {p["ref"]: p for p in placement}
    by_ref = {}
    for i, o in enumerate(openings):
        if o.ref:
            by_ref.setdefault(o.ref, []).append(i)
    # --- 3. The placement file by position, for the openings that carry no TO.C
    plain = [i for i, o in enumerate(openings) if not o.ref]
    parts_pl = [p for p in placement if p["ref"] not in by_ref]
    if parts_pl and plain:
        open_plain = [openings[i] for i in plain]
        conv = bottom
        if bottom == "auto":
            conv = bottom_convention(parts_pl, open_plain, tol, offset)[0]
        info["convention"] = conv
        parts_pl = apply_offset(apply_bottom_convention(parts_pl, conv), *offset)
        mirror = bottom_mirror(parts_pl, open_plain, tol)[0]
        info["bottom_mirror"] = mirror
        info["frame"] = frame_check(parts_pl, open_plain, tol, mirror_bottom=mirror)
        fr = info["frame"]
        if fr["propose"]:
            info["warnings"].append(f"the placement file may use another origin: an offset of ({fr['dx']:+.2f}, {fr['dy']:+.2f}) mm raises the parts with an opening from "
                                    f"{fr['given']:.0%} to {fr['best']:.0%}")
        elif fr["misfit"]:
            info["warnings"].append(f"the placement file does not fit the paste: only {fr['given']:.0%} of its SMD parts have an opening in their pad envelope and no offset up to 10 mm "
                                    "aligns them (another rotation, a mirror, a unit or a larger offset); the parts matched by position are unreliable")
        byref_pl, _ = match_envelope(parts_pl, open_plain, tol, mirror)
    else:
        byref_pl = {}
        # Parts matched by TO.C take their position from the openings, so the convention does not move them; it is still CHECKED from the openings here (or reported as not
        # checked), because "as is" by default would state something nobody looked at
        if placement and bottom == "auto":
            if any(p["side"] == "bottom" for p in placement) and any(o.side == "bottom" for o in openings):
                conv, n_as, n_neg = bottom_convention(placement, openings, tol, offset)
                # No bottom opening inside an envelope either way (another frame, unknown packages) or a tie: bottom_convention keeps "as is", but nothing was checked
                info["convention"] = conv if n_as != n_neg else CONVENTION_NOT_CHECKED
        elif placement and bottom != "auto":
            info["convention"] = bottom
    for ref, idx in by_ref.items():
        ops = [openings[i] for i in idx]
        claimed.update(idx)
        p = plc.get(ref)
        src = "to.c+placement" if p else "paste only"
        ff = {}
        if p:
            ff.update(value=p["value"], package=p["package"], rotation_deg=p["rot"], position_mm=[p["x"], p["y"]])
        part = part_from_openings(ref, ops, shape, src, ff, p["package"] if p else "", ops[0].side)
        add(part, shape_set(ops))
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
        add(part, shape_set(ops))
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
        part = part_from_openings(f"P{k}", ops, "auto", "paste only", grouping="proximity")
        res.parts.append(part)
        res.shapes[part.designator] = shape_set(ops)
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


# A part whose centre moved by more than this between two imports is reported as moved, by the table of the re-import dialog (`diff_parts`) and by the status line (`merge_parts`,
# `reimport_summary`) alike (review: the table used 0.3 mm and the status 0.05 mm, so a 0.1 mm shift was "kept" in one and "moved" in the other). 0.3 mm is the tolerance the
# review of the update table chose (a centre within a third of a millimetre is the same place for a heat source) and the radius of the match by position.
MOVED_MM = 0.3


def _moved_mm(old_poly, new_poly):
    """!
    @brief Distance between the centres of the boxes of two polygons.
    @param old_poly Stored polygon (mm) or empty.
    @param new_poly New polygon (mm) or empty.
    @return float Distance in mm (0 when either polygon is empty).
    """
    a, b = _centre_size(old_poly), _centre_size(new_poly)
    return math.hypot(a[0][0] - b[0][0], a[0][1] - b[0][1]) if a and b else 0.0


def _sides(poly):
    """!
    @brief Width and height of the box of a polygon (not sorted).
    @param poly List of (x, y).
    @return tuple (width, height) in mm.
    """
    x0, y0, x1, y1 = _bbox_of(poly)
    return x1 - x0, y1 - y0


def diff_parts(old, new, move_mm=MOVED_MM, resize_mm=0.2):
    """!
    @brief The table a user reads before confirming an update: new, removed, moved (centre shifted by more than `move_mm`), resized (a sorted side changed by more than `resize_mm`), rotated
           (the rotation of the files changed by more than 1 degree, or, without a rotation in the files, the box swapped its sides), kept. The same files twice give only "kept".
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
        # Rotated: the rotation written by the files changed, or (no rotation in the files) the box of the shape swapped its sides; the sorted sides of `resized` do not see a quarter turn
        ra, rb = a.from_file.get("rotation_deg"), b.from_file.get("rotation_deg")
        turn = None
        if ra is not None and rb is not None:
            t = (float(rb) - float(ra)) % 360.0
            turn = min(t, 360.0 - t) if min(t, 360.0 - t) > 1.0 else None
        elif ca and cb:
            wa, ha = _sides(a.polygon_mm)
            wb, hb = _sides(b.polygon_mm)
            if abs(wa - ha) > resize_mm and abs(wa - hb) <= resize_mm and abs(ha - wb) <= resize_mm:
                turn = 90.0
        if turn is not None:
            changes.append("rotated")
            detail.append(f"{turn:.0f} degrees")
        rows.append({"ref": ref, "change": " and ".join(changes) or "kept", "detail": ", ".join(detail)})
    return rows


@dataclass
class MergeResult:
    """!@brief The outcome of a re-import merge: the parts, the changes as text lines and the designators kept as orphans."""
    parts: list
    changes: list
    orphans: list


def _positional(part):
    """!
    @brief Whether a part has a name the files do not give (picked by hand, or a proximity group), so that a re-import matches it by position.
    @param part ImportPart.
    @return bool.
    """
    return part.from_file.get("grouping") in ("hand", "proximity")


def merge_parts(old, new, shapes=None, remove=(), openings=None, move_mm=MOVED_MM):
    """!
    @brief Merge the parts of a new import into the stored ones: copper, drills and outline come from the new files elsewhere; here, a part with the same designator keeps its power and its `edits` and takes the
           `from_file` and the polygon of the new files; the user's shape choice (`edits["shape_user"]`) is applied to the NEW openings; a part that is not in the new files is an orphan.
    @details A part whose name the files do not give (`from_file["grouping"]` "hand" or "proximity": H<n>, P<n>) is matched by POSITION, never by name (review: the proximity groups are
             numbered again at every import, so P3 took the power of another group): the new positional part whose centre is within `move_mm` of it, else the new openings whose centres lie
             in its polygon (given `openings`), else it is an orphan. New positional parts left over are renamed when their name is taken.
             An orphan is kept (power and edits intact) with `from_file["orphan"] = True` and is not a heat source (consumers check the flag); it is removed only when listed in `remove`.
             `new` should hold the listed parts too (`PartsResult.parts + listed`), or a part that lost its openings reads as an orphan.
    @param old List of ImportPart stored in the project.
    @param new List of ImportPart of the new files.
    @param shapes Dict designator -> {"box": polygon, "hull": polygon} of the new import (`PartsResult.shapes`), or None.
    @param remove Designators the user confirmed to remove.
    @param openings List of Opening of the new import (`PartsResult.openings`), to re-pick a part chosen by hand; None to skip.
    @param move_mm Distance (mm) within which a positional part is the same part.
    @return MergeResult.
    """
    shapes = shapes or {}
    o = {p.designator: p for p in old if not _positional(p)}
    merged, changes, orphans = [], [], []
    taken = set()
    for p in new:
        if _positional(p):
            continue
        q = copy.deepcopy(p)
        a = o.get(p.designator)
        if a is not None:
            q.power = a.power
            q.edits = copy.deepcopy(a.edits)
            q.extra = copy.deepcopy(a.extra)
            if a.shape == "largest":
                # The 'largest opening' radio was removed from the import window (it put all the heat on one pad of a part with several equal pads); a choice stored with it
                # becomes the proposed shape of the new import, and the line says so (the user's other choices, power, tick, role, are kept)
                q.edits["shape_user"] = False
                changes.append(f"{p.designator}: the shape 'largest opening' is no longer offered; the part has the proposed shape '{q.shape}'")
            elif a.edits.get("shape_user") and a.shape in shapes.get(p.designator, {}):
                q.shape = a.shape
                q.polygon_mm = [list(map(float, pt)) for pt in shapes[p.designator][a.shape]]
            elif "shape_rule" not in a.from_file and a.polygon_mm and a.shape in ("hull", "box", "outline") and q.shape == "exposed":
                # A part of a project written before the exposed-pad rule: its shape was the default of that time and a re-import keeps that KIND, drawn from the NEW openings when
                # the new import has it (review: the first version kept the old coordinates, so a part moved by a layout revision kept its heater at the old place); an outline,
                # which the new import does not offer, keeps its stored polygon (a retired 'largest' is taken by the first branch). The new file data loses `shape_rule`, so the next re-import keeps it too
                # (review: it flipped to the pad at the second re-import); the user turns it to the pad in the import window.
                q.shape = a.shape
                src = shapes.get(p.designator, {}).get(a.shape) or a.polygon_mm
                q.polygon_mm = [list(map(float, pt)) for pt in src]
                q.from_file.pop("shape_rule", None)
                changes.append(f"{p.designator}: kept the shape '{a.shape}' of a project written before the exposed-pad rule (the pad is now proposed and reads hotter: choose it in step 2)")
            moved = _moved_mm(a.polygon_mm, q.polygon_mm)
            how = f"moved by {moved:.2f} mm" if moved > MOVED_MM else "matched"
            changes.append(f"{p.designator}: {how}" + (f", kept power {a.power:g} W" if a.power else ""))
        merged.append(q)
        taken.add(q.designator)
    # Parts with a name the files do not give: by position
    pos_new = [p for p in new if _positional(p)]
    used_new, used_open = set(), set()
    pending = []
    for a in old:
        if not _positional(a):
            continue
        ca = _centre_size(a.polygon_mm)
        hit = None
        if ca:
            for k, p in enumerate(pos_new):
                cb = _centre_size(p.polygon_mm)
                if k not in used_new and cb and p.side == a.side and math.hypot(ca[0][0] - cb[0][0], ca[0][1] - cb[0][1]) <= move_mm:
                    hit = k
                    break
        if hit is not None:
            used_new.add(hit)
            q = copy.deepcopy(pos_new[hit])
            q.designator, q.power, q.edits, q.extra = a.designator, a.power, copy.deepcopy(a.edits), copy.deepcopy(a.extra)
            q.from_file["grouping"] = a.from_file.get("grouping")
        elif openings is not None and len(a.polygon_mm) >= 3:
            region = _hull(a.from_file.get("outer_mm") or a.polygon_mm)         # the hull of all the openings, not only the exposed pad
            inside = [i for i, op in enumerate(openings) if i not in used_open and op.side == a.side and _point_to_hull(region, op.x, op.y) <= 1e-9]
            if not inside:
                pending.append(a)
                continue
            used_open.update(inside)
            q = part_from_openings(a.designator, [openings[i] for i in inside], a.shape if a.shape in ("hull", "box", "exposed") else "auto" if a.shape == "largest" else "hull", "paste only",
                                   footprint=a.footprint, side=a.side, grouping=a.from_file.get("grouping"))
            q.power, q.edits, q.extra = a.power, copy.deepcopy(a.edits), copy.deepcopy(a.extra)
        else:
            pending.append(a)
            continue
        if a.shape == "largest":
            # Review: the positional paths also take a retired 'largest' to the proposed shape, clear the user's mark and say so. The stored polygon was ONE opening, so the region
            # above finds only that opening: the line says how many of the stored openings were found, and the user adds the others with Ctrl+click in step 2
            q.edits["shape_user"] = False
            found, stored = q.from_file.get("n_openings"), a.from_file.get("n_openings")
            short = f" ({found} of its {stored} openings found: add the others with Ctrl+click in step 2)" if found and stored and found < stored else ""
            changes.append(f"{a.designator}: the shape 'largest opening' is no longer offered; the part has the proposed shape '{q.shape}'{short}")
        merged.append(q)
        taken.add(q.designator)
        moved = _moved_mm(a.polygon_mm, q.polygon_mm)
        changes.append(f"{a.designator}: matched by position" + (f", moved by {moved:.2f} mm" if moved > MOVED_MM else "") + (f", kept power {a.power:g} W" if a.power else ""))
    # New positional parts that no stored part took: added, renamed when the name is taken
    for k, p in enumerate(pos_new):
        if k in used_new:
            continue
        q = copy.deepcopy(p)
        if q.designator in taken or q.designator in o:
            stem = re.sub(r"\d+$", "", q.designator) or "P"
            n = 1
            while f"{stem}{n}" in taken or f"{stem}{n}" in o or any(f"{stem}{n}" == x.designator for x in old):
                n += 1
            q.designator = f"{stem}{n}"
        merged.append(q)
        taken.add(q.designator)
    new_refs = {p.designator for p in new if not _positional(p)}
    for a in [x for x in old if not _positional(x) and x.designator not in new_refs] + pending:
        ref = a.designator
        if ref in remove:
            changes.append(f"{ref}: removed (confirmed)")
            continue
        q = copy.deepcopy(a)
        q.from_file = dict(q.from_file, orphan=True)
        merged.append(q)
        orphans.append(ref)
        changes.append(f"{ref}: not in the new files, kept as an orphan until confirmed")
    return MergeResult(merged, changes, orphans)
