#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file pnp.py
@brief Placement ("pick and place", centroid) files: reading the CSV and text variants of KiCad, JLCPCB, Altium and EasyEDA into one list, and the registration of their coordinates onto the Gerber coordinates.
@details A placement file gives, per part, the reference designator, value, package, the position of the part origin, the rotation and the side. The origin and the sign of Y differ between tools and
         between export settings (KiCad: the auxiliary axis origin, Y up in the file; Altium: the board origin), so the file is not taken at its word: `register` finds the translation (and the
         flip of Y or of X, if any) that makes the parts fall on the centres of the paste pad groups of the Gerber files, and reports how many fall within a tolerance. NumPy only.
         Header names are matched without case and spaces; a value with a unit suffix ("12.5mm", "492.1mil") is converted to millimetres.
"""

import csv
import re
from pathlib import Path

import numpy as np

# header word (lower case, no spaces) -> canonical field
_FIELDS = {
    "ref": "ref", "designator": "ref", "refdes": "ref", "reference": "ref",
    "val": "value", "value": "value", "comment": "value",
    "package": "package", "footprint": "package", "pattern": "package",
    "posx": "x", "midx": "x", "centerx": "x", "x": "x", "refx": "x_ref",
    "posy": "y", "midy": "y", "centery": "y", "y": "y", "refy": "y_ref",
    "rot": "rot", "rotation": "rot",
    "side": "side", "layer": "side",
}


def _length_mm(text):
    """!
    @brief A length with an optional unit suffix to millimetres.
    @param text String such as "12.5", "12.5mm", "492.1mil", "1.2in".
    @return float millimetres.
    @throws ValueError If the text holds no number.
    """
    m = re.fullmatch(r"\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(mm|mil|in|inch)?\s*", text)
    if not m:
        raise ValueError(f"not a length: {text!r}")
    v = float(m.group(1))
    unit = (m.group(2) or "mm").lower()
    return v * {"mm": 1.0, "mil": 0.0254, "in": 25.4, "inch": 25.4}[unit]


def _side(text):
    """!
    @brief Normalise the side of a part.
    @param text "top", "bottom", "t", "b", "front", "back" in any case.
    @return "top" or "bottom".
    """
    t = text.strip().lower()
    return "bottom" if t.startswith(("b", "back")) else "top"


def read_placement(path):
    """!
    @brief Read a placement file (CSV with a header line, or the KiCad text .pos format with a '#' header).
    @param path File path.
    @return list of dicts with ref, value, package, x, y (mm), rot (degrees), side ("top"/"bottom"); fields a file lacks are "" or 0.0.
    @throws ValueError If no header with a reference column and X and Y columns is found.
    """
    text = Path(path).read_text(errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    header, rows = None, []
    for ln in lines:
        if ln.startswith("##"):                                       # KiCad text report: comment lines
            continue
        if ln.startswith("# ") and header is None and "Ref" in ln:     # KiCad text report: the column names are a comment
            header = ln[2:].split()
            continue
        if header is None:
            # CSV header: the first line whose cells map to a reference column and X, Y
            cells = next(csv.reader([ln]))
            keys = [_FIELDS.get(re.sub(r"[^a-z]", "", c.lower()), None) for c in cells]
            if "ref" in keys and "x" in keys and "y" in keys:
                header = cells
                continue
            raise ValueError(f"{path}: no placement header found (first line {ln[:60]!r})")
        rows.append(next(csv.reader([ln])) if "," in ln else ln.split())
    if header is None:
        raise ValueError(f"{path}: empty placement file")
    keys = [_FIELDS.get(re.sub(r"[^a-z]", "", c.lower()), None) for c in header]
    out = []
    for r in rows:
        d = {"ref": "", "value": "", "package": "", "x": 0.0, "y": 0.0, "rot": 0.0, "side": "top"}
        for k, v in zip(keys, r):
            if k in ("x", "y"):
                d[k] = _length_mm(v)
            elif k == "rot":
                d[k] = float(re.sub(r"[^0-9eE.+-]", "", v) or 0.0)
            elif k == "side":
                d[k] = _side(v)
            elif k in ("ref", "value", "package"):
                d[k] = v.strip().strip('"')
        out.append(d)
    return out


def register(points_gerber, points_placement, tol_mm=0.5, search_mm=60.0, cell_mm=0.25):
    """!
    @brief Find the rigid transform that puts the placement positions on the Gerber coordinates.
    @details Tries the four sign choices (X, Y as they are, Y flipped, X flipped, both flipped) and, for each, the translation that the largest number of (placement, group centre) pairs vote for
             (a histogram of the differences at `cell_mm`, refined by the median of the differences of the winning pairs). The rotation of the whole board is not searched (files from one CAD tool
             share the orientation). Returns the best choice by the number of placements that end within `tol_mm` of a group centre.
    @param points_gerber Array (n, 2) of group centres in Gerber coordinates (mm).
    @param points_placement Array (m, 2) of placement positions (mm).
    @param tol_mm A placement counts as matched when a group centre is nearer than this (mm).
    @param search_mm Largest translation looked for (mm).
    @param cell_mm Histogram cell of the vote (mm).
    @return dict with sx, sy (+1 or -1), dx, dy (translation, mm), matched (count), total (m), median_mm (median distance of the matched pairs).
    """
    g = np.asarray(points_gerber, float).reshape(-1, 2)
    p = np.asarray(points_placement, float).reshape(-1, 2)
    best = {"sx": 1, "sy": 1, "dx": 0.0, "dy": 0.0, "matched": 0, "total": len(p), "median_mm": float("nan")}
    if len(g) == 0 or len(p) == 0:
        return best
    for sx in (1, -1):
        for sy in (1, -1):
            q = p * np.array([sx, sy])
            diff = (g[None, :, :] - q[:, None, :]).reshape(-1, 2)          # every group minus every placement
            keep = (np.abs(diff) <= search_mm).all(axis=1)
            diff = diff[keep]
            if len(diff) == 0:
                continue
            h, ex, ey = np.histogram2d(diff[:, 0], diff[:, 1], bins=[np.arange(-search_mm, search_mm + cell_mm, cell_mm)] * 2)
            i, j = np.unravel_index(np.argmax(h), h.shape)
            c = np.array([(ex[i] + ex[i + 1]) / 2, (ey[j] + ey[j + 1]) / 2])
            near = diff[np.linalg.norm(diff - c, axis=1) <= 2 * cell_mm]
            t = np.median(near, axis=0)
            d = np.linalg.norm((q + t)[:, None, :] - g[None, :, :], axis=2).min(axis=1)
            n = int((d <= tol_mm).sum())
            if n > best["matched"]:
                best = {"sx": sx, "sy": sy, "dx": float(t[0]), "dy": float(t[1]), "matched": n, "total": len(p),
                        "median_mm": float(np.median(d[d <= tol_mm]))}
    return best


def apply(transform, x, y):
    """!
    @brief Apply a transform of `register` to one placement position.
    @param transform Dict returned by register.
    @param x Placement X (mm).
    @param y Placement Y (mm).
    @return tuple (x, y) in Gerber coordinates (mm).
    """
    return transform["sx"] * x + transform["dx"], transform["sy"] * y + transform["dy"]
