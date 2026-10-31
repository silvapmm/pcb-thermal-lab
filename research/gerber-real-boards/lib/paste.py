#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file paste.py
@brief Solder-paste layers as component footprints: the pad groups of a paste file, with their reference designators when the file carries them, and the heat-source shapes a click can pick.
@details The paste layer holds one opening per pad that is soldered, so a part appears as a group of openings (an exposed pad of a QFN as one large opening, often split into windows by the CAD tool).
         Two ways to get the groups, both NumPy and SciPy only, on top of the independent reader of research/gerber-import:
         1. By reference: KiCad (and other tools that write Gerber X2 component attributes) put `%TO.C,R49*%` before the objects of a part. The reader keeps the net attribute `TO.N` per object, so the text is
            rewritten (`TO.C,` -> `TO.N,`) and the objects of a part are drawn on their own: reference designator, area, bounding box and centre come straight from the file, no placement file needed.
         2. By proximity: with no attribute, the paste mask is drawn at a fine pixel, dilated by `link_mm` and labelled; each connected piece is a group (a part, or a neighbour pair closer than `link_mm`).
         `shapes` gives the candidate heat-source footprints of a group (bounding box, convex hull, largest opening) and `pick` the group under a click. Doxygen headers follow the project rules.
"""

import re
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull

import native_gerber as ng

CLEAR_RE = re.compile(r"%TO\.C,")


def reference_text(text):
    """!
    @brief Rewrite the component attribute of a Gerber text as the net attribute the reader keeps per object.
    @param text Content of a Gerber file.
    @return str with every `%TO.C,` replaced by `%TO.N,` (the reader then stores the reference designator as the "net" of the objects that follow).
    """
    return CLEAR_RE.sub("%TO.N,", text)


def _op_bbox(op):
    """!
    @brief Bounding box of one drawing operation of the reader.
    @param op Tuple (kind, dark, args) of native_gerber.Layer.ops.
    @return tuple (xmin, ymin, xmax, ymax) in mm, or None for an operation without extent.
    """
    kind, _, a = op
    if kind == "flash":
        r = getattr(a[0], "radius", 0.0)
        return a[1] - r, a[2] - r, a[1] + r, a[2] + r
    if kind == "stroke":
        r = getattr(a[0], "radius", 0.0)
        return min(a[1], a[3]) - r, min(a[2], a[4]) - r, max(a[1], a[3]) + r, max(a[2], a[4]) + r
    if kind == "region":
        pts = np.asarray(a, float).reshape(-1, 2)
        return pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max()
    return None


def _group_from_mask(mask, x_left, y_top, pix):
    """!
    @brief Centre, area and bounding box of a boolean mask drawn on a window.
    @param mask Boolean array (rows from the top, cols).
    @param x_left X of the left edge of the window (mm).
    @param y_top Y of the top edge of the window (mm).
    @param pix Pixel (mm).
    @return dict with x, y (centroid, mm), area (mm2), bbox (xmin, ymin, xmax, ymax in mm), n_px; None when the mask is empty.
    """
    rows, cols = np.nonzero(mask)
    if len(rows) == 0:
        return None
    xs = x_left + (cols + 0.5) * pix
    ys = y_top - (rows + 0.5) * pix
    return {"x": float(xs.mean()), "y": float(ys.mean()), "area": float(len(rows) * pix * pix),
            "bbox": (float(xs.min() - pix / 2), float(ys.min() - pix / 2), float(xs.max() + pix / 2), float(ys.max() + pix / 2)), "n_px": int(len(rows))}


def by_reference(path, pix=0.02):
    """!
    @brief The pad groups of a paste file by the reference designator written in it (Gerber X2 attribute TO.C).
    @param path Paste Gerber file.
    @param pix Pixel of the small canvas each part is drawn on (mm); the opening of a 0201 pad is 0.25 mm, so 0.02 mm resolves it.
    @return dict reference -> group (x, y, area, bbox, n_px, mask, x_left, y_top, pix); empty when the file has no TO.C attribute.
    """
    layer = ng.Layer(reference_text(Path(path).read_text(errors="replace")))
    out = {}
    for ref in layer.net_names():
        boxes = [b for op, net in zip(layer.ops, layer.nets) if net == ref and op[1] for b in [_op_bbox(op)] if b]
        if not boxes:
            continue
        x0, y0 = min(b[0] for b in boxes) - 2 * pix, min(b[1] for b in boxes) - 2 * pix
        x1, y1 = max(b[2] for b in boxes) + 2 * pix, max(b[3] for b in boxes) + 2 * pix
        cv = ng.Canvas(x0, y1, x1 - x0, y1 - y0, pix)
        layer.draw(cv, nets=[ref])
        g = _group_from_mask(cv.mask, x0, y1, pix)
        if g is not None:
            g.update(mask=cv.mask.copy(), x_left=x0, y_top=y1, pix=pix)
            out[ref] = g
    return out


def by_proximity(path, box, pix=0.05, link_mm=1.0):
    """!
    @brief The pad groups of a paste file with no attributes: connected pieces of the paste mask after dilating it by `link_mm`.
    @param path Paste Gerber file.
    @param box Board box (x0, y0, x1, y1) in mm (the importer's box).
    @param pix Pixel (mm).
    @param link_mm Openings whose edges are closer than this belong to the same group (mm); the study sweeps it.
    @return list of groups (x, y, area, bbox, n_px, pads) where pads is the list of the individual openings (each a dict x, y, area, bbox) inside the group.
    """
    layer = ng.Layer(Path(path).read_text(errors="replace"))
    x0, y0, x1, y1 = box
    cv = ng.Canvas(x0, y1, x1 - x0, y1 - y0, pix)
    layer.draw(cv)
    mask = cv.mask
    if not mask.any():
        return []
    pad_lab, n_pad = ndimage.label(mask)                                # the individual openings
    # Each opening is grown by half the link distance, so two openings closer than link_mm touch and fall into one group
    near = ndimage.distance_transform_edt(~mask) <= link_mm / 2.0 / pix
    grp_lab, n_grp = ndimage.label(near)
    out = []
    # Work on the slice of each group, not on the whole board: a board has hundreds of groups and millions of pixels
    for gi, (rs, cs) in enumerate(ndimage.find_objects(grp_lab), start=1):
        xl, yt = x0 + cs.start * pix, y1 - rs.start * pix
        sub_lab, sub_pad, sub_mask = grp_lab[rs, cs], pad_lab[rs, cs], mask[rs, cs]
        sel = (sub_lab == gi) & sub_mask
        g = _group_from_mask(sel, xl, yt, pix)
        if g is None:
            continue
        ids = np.unique(sub_pad[sel])
        g["pads"] = [_group_from_mask(sub_pad == i, xl, yt, pix) for i in ids]
        out.append(g)
    return out


def shapes(group):
    """!
    @brief The candidate heat-source footprints of a group of openings.
    @details "bbox": the rectangle around all openings (what a click on the part would draw; worst case for the density: the power spreads over the gaps too);
             "hull": the convex hull of the openings (a polygon, the program's heater accepts polygons);
             "largest": the rectangle around the largest opening (the exposed pad of a QFN or the tab of a power package, where most of the heat enters the board).
    @param group A group of `by_proximity` (needs "pads") or of `by_reference` (needs "mask", "x_left", "y_top", "pix").
    @return dict name -> dict(kind="rect"/"polygon", rect=(x0, y0, x1, y1) or polygon=array (k, 2), area=float mm2 of the shape).
    """
    bb = group["bbox"]
    out = {"bbox": {"kind": "rect", "rect": bb, "area": (bb[2] - bb[0]) * (bb[3] - bb[1])}}
    if "pads" in group:
        pads = group["pads"]
        corners = np.array([c for p in pads for c in ((p["bbox"][0], p["bbox"][1]), (p["bbox"][2], p["bbox"][1]), (p["bbox"][2], p["bbox"][3]), (p["bbox"][0], p["bbox"][3]))])
        big = max(pads, key=lambda p: p["area"])
    else:
        m, pix = group["mask"], group["pix"]
        lab, n = ndimage.label(m)
        areas = ndimage.sum(m, lab, range(1, n + 1))
        k = int(np.argmax(areas)) + 1
        big = _group_from_mask(lab == k, group["x_left"], group["y_top"], pix)
        rows, cols = np.nonzero(m)
        xs, ys = group["x_left"] + (cols + 0.5) * pix, group["y_top"] - (rows + 0.5) * pix
        corners = np.column_stack([np.concatenate([xs - pix / 2, xs + pix / 2]), np.concatenate([ys - pix / 2, ys + pix / 2])])
    out["largest"] = {"kind": "rect", "rect": big["bbox"], "area": (big["bbox"][2] - big["bbox"][0]) * (big["bbox"][3] - big["bbox"][1])}
    if len(corners) >= 3 and np.ptp(corners[:, 0]) > 0 and np.ptp(corners[:, 1]) > 0:
        hull = ConvexHull(corners)
        out["hull"] = {"kind": "polygon", "polygon": corners[hull.vertices], "area": float(hull.volume)}   # in 2D, ConvexHull.volume is the area
    return out


def pick(groups, x, y, max_mm=1.5):
    """!
    @brief The group a click selects: the one whose bounding box contains the point, else the nearest centre within max_mm.
    @param groups List of groups (dicts with x, y, bbox).
    @param x Click X (mm, Gerber coordinates).
    @param y Click Y (mm).
    @param max_mm Largest distance from a group's bounding box accepted when the click is outside every box (mm).
    @return the index of the group in the list, or None when nothing is near; a click inside several boxes (a small part over a large one) gives the one with the smallest box.
    """
    inside = [i for i, g in enumerate(groups) if g["bbox"][0] <= x <= g["bbox"][2] and g["bbox"][1] <= y <= g["bbox"][3]]
    if inside:
        return min(inside, key=lambda i: (groups[i]["bbox"][2] - groups[i]["bbox"][0]) * (groups[i]["bbox"][3] - groups[i]["bbox"][1]))
    best, d_best = None, max_mm
    for i, g in enumerate(groups):
        b = g["bbox"]
        d = float(np.hypot(max(b[0] - x, 0, x - b[2]), max(b[1] - y, 0, y - b[3])))
        if d <= d_best:
            best, d_best = i, d
    return best
