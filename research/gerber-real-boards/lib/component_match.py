#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file component_match.py
@brief Matching of solder-paste openings to the parts of a placement file by the pad envelope of each part (the rule proposed for the import window), and the table of the 30 parts of the RP2040 board.
@details Question answered: which part does each paste opening belong to when the paste file names no part (no X2 `TO.C`), and why does the prototype's group rule miss parts?
         Rule B: every individual opening (link 0.05 mm) goes to the part whose rotated pad envelope, grown by a tolerance of 0.3 mm, contains the opening centre; the smallest envelope wins; one part may take many openings.
         The envelope comes from the footprint NAME only (0402 .. 1206 pad extents, SOIC pitch and pins, SOT-223, pin headers, QFN from the paste); no footprint library is read.
         Truth for the boards that carry `TO.C` is that attribute (the rule never uses it). Lengths in mm, angles in degrees, positions in the board frame of the placement file.
         The prototype backend (`prototypes/import_window/backend.py`) is imported for reading the board.
"""
import math, re, sys
import numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "prototypes" / "import_window"))
import backend as b  # noqa: E402  (the prototype's data side)

paste = b.paste; ng = b.ng; pnp = b.pnp

## Folder of the git-ignored downloaded boards.
DATA = HERE / "data"

IMP = {"0201": (1.0, 0.5), "0402": (1.5, 0.6), "0603": (2.45, 0.95), "0805": (2.9, 1.45), "1206": (4.1, 1.8)}
TH_WORDS = ("PinHeader", "USB_Micro", "USB_C", "Battery", "TS-1187", "Molex", "MountingHole", "Conn", "TerminalBlock", "Jack")


def envelope(pkg, value=""):
    """!
    @brief Local pad envelope of a part from its footprint NAME only.
    @param pkg footprint name
    @param value part value (unused, kept for future rules)
    @return tuple (lx, ly, ox, oy, kind, known): size and centre offset in mm along the part axes, kind smd or th, known False when it is a guess
    """
    m = re.match(r"^(?:R|C|L|D|LED|F|FB)_(\d{4})_", pkg)
    if m and m.group(1) in IMP:
        lx, ly = IMP[m.group(1)]; return lx, ly, 0, 0, "smd", True
    m = re.match(r"PinHeader_(\d)x(\d+)_P([\d.]+)mm", pkg)
    if m:
        c, r, p = int(m.group(1)), int(m.group(2)), float(m.group(3))
        # pins at local x 0..(c-1)p and local y' = 0..-(r-1)p (pos file Y up), pad ring 1.7 mm
        lx, ly = (c - 1) * p + 1.7, (r - 1) * p + 1.7
        return lx, ly, (c - 1) * p / 2, -(r - 1) * p / 2, "th", True
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
    m = re.search(r"(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)mm", pkg)
    if m:   # crystals / oscillators with body size
        a, c = float(m.group(1)), float(m.group(2))
        return a + 0.8, c, 0, 0, "smd", True
    if pkg.startswith("RP2040-QFN"):
        return 7.8, 7.8, 0, 0, "smd", True
    if any(w in pkg for w in TH_WORDS):
        return 5.0, 5.0, 0, 0, "th", False
    return 3.0, 3.0, 0, 0, "smd", False


def rot_matrix(rot_deg, side="top", mirror_bottom=False):
    """!
    @brief Rotation matrix of a part, optionally with the mirrored X of the bottom side.
    @param rot_deg rotation of the part in degrees
    @param side top or bottom
    @param mirror_bottom True: mirror X on the bottom side
    @return numpy.ndarray 2 x 2
    """
    a = math.radians(rot_deg); c, s = math.cos(a), math.sin(a)
    R = np.array([[c, -s], [s, c]])
    if side == "bottom" and mirror_bottom:
        R = R @ np.diag([-1.0, 1.0])
    return R


def part_polygon(p, mirror_bottom=False, margin=0.0):
    """!
    @brief Board-frame corners of the envelope of a part.
    @param p part dict (ref, package, x, y, rot, side) with x, y in mm and rot in degrees
    @param mirror_bottom True: mirror X on the bottom side
    @param margin growth of the envelope on every side in mm
    @return numpy.ndarray 4 x 2 corners in mm
    """
    lx, ly, ox, oy, kind, known = envelope(p["package"], p.get("value", ""))
    hx, hy = lx / 2 + margin, ly / 2 + margin
    loc = np.array([[ox - hx, oy - hy], [ox + hx, oy - hy], [ox + hx, oy + hy], [ox - hx, oy + hy]])
    R = rot_matrix(p["rot"], p["side"], mirror_bottom)
    return (loc @ R.T) + np.array([p["x"], p["y"]])


def inside(poly, pt):
    """!
    @brief Point in a convex quadrilateral of any orientation.
    @param poly 4 x 2 corners in mm
    @param pt point (x, y) in mm
    @return bool
    """
    s = []
    for i in range(4):
        a, bb = poly[i], poly[(i + 1) % 4]
        s.append((bb[0] - a[0]) * (pt[1] - a[1]) - (bb[1] - a[1]) * (pt[0] - a[0]))
    return all(v >= 0 for v in s) or all(v <= 0 for v in s)


def dist_to_poly(poly, pt):
    """!
    @brief Distance from a point to a convex quadrilateral.
    @param poly 4 x 2 corners in mm
    @param pt point (x, y) in mm
    @return float distance in mm, 0 inside
    """
    if inside(poly, pt): return 0.0
    best = 1e9
    for i in range(4):
        a, bb = poly[i], poly[(i + 1) % 4]
        ab = bb - a; t = np.clip(np.dot(pt - a, ab) / np.dot(ab, ab), 0, 1)
        best = min(best, float(np.hypot(*(a + t * ab - pt))))
    return best


def read_pads(folder, side, box, pix=0.05, link=0.05):
    """!
    @brief Individual openings (no grouping beyond a 0.05 mm link) of a paste file.
    @param folder board folder
    @param side top or bottom
    @param box board box (xmin, ymin, xmax, ymax) in mm
    @param pix raster pixel in mm
    @param link link distance in mm
    @return list of pad dicts with x, y, bbox, side
    """
    fn = Path(folder) / ("pasteF.gbr" if side == "top" else "pasteB.gbr")
    if not fn.exists(): return []
    gs = paste.by_proximity(fn, box, pix=pix, link_mm=link)
    return [dict(p, side=side) for g in gs for p in g["pads"]]


def truth_pads(folder, side, pads):
    """!
    @brief Reference of each pad from the X2 `TO.C` boxes: the smallest box that contains the pad centre.
    @param folder board folder
    @param side top or bottom
    @param pads list from read_pads
    @return list of designators (None where unknown), or None when the file has no TO.C
    """
    fn = Path(folder) / ("pasteF.gbr" if side == "top" else "pasteB.gbr")
    text = fn.read_text(errors="replace")
    if "%TO.C," not in text: return None
    layer = ng.Layer(paste.reference_text(text))
    boxes = []
    for op, net in zip(layer.ops, layer.nets):
        if net and op[1]:
            bx = paste._op_bbox(op)
            if bx: boxes.append((net, bx))
    out = []
    for p in pads:
        cand = [(n, bx) for n, bx in boxes if bx[0] - 0.03 <= p["x"] <= bx[2] + 0.03 and bx[1] - 0.03 <= p["y"] <= bx[3] + 0.03]
        out.append(min(cand, key=lambda c: (c[1][2] - c[1][0]) * (c[1][3] - c[1][1]))[0] if cand else None)
    return out


def improved_match(parts, pads, mirror_bottom=False, tol=0.3):
    """!
    @brief Rule B: every opening goes to the part whose rotated pad envelope (tolerance tol) contains its centre; the smallest envelope wins.
    @param parts list of part dicts
    @param pads list from read_pads
    @param mirror_bottom True: mirror X on the bottom side
    @param tol tolerance in mm added to the envelope
    @return tuple (dict ref -> pad indices, dict pad index -> ref)
    """
    polys = {p["ref"]: part_polygon(p, mirror_bottom, tol) for p in parts}
    areas = {r: float(abs((q[1][0]-q[0][0])*(q[3][1]-q[0][1])-(q[1][1]-q[0][1])*(q[3][0]-q[0][0]))) for r, q in polys.items()}
    byref, bypad = {}, {}
    for i, pd in enumerate(pads):
        cands = [p["ref"] for p in parts if p["side"] == pd["side"] and inside(polys[p["ref"]], (pd["x"], pd["y"]))]
        if cands:
            r = min(cands, key=lambda r: areas[r])
            byref.setdefault(r, []).append(i); bypad[i] = r
    return byref, bypad


def part_rows(name="rp2040"):
    """!
    @brief The table of the parts of a board: prototype status (group rule, 0.6 mm link, 0.8 mm pick), improved status (envelope rule), the openings in each part and the reason of each miss.
    @param name board folder name under data/.
    @return tuple (rows, unclaimed, ctx): rows (list of dicts), prototype groups no part claimed (list of dicts), and the context (board, parts, pads, matches).
    """
    folder = DATA / name
    files = b.scan(folder)
    bd = b.load_board(files)
    parts = bd["placement"]
    box = bd["box"]
    pads = read_pads(folder, "top", box)
    groups = list(bd["groups"]["top"])
    bd2 = dict(bd)
    bd2["groups"] = {"top": [dict(g, ref=None) for g in groups], "bottom": []}
    pa, _unm = b.match_parts(bd2)
    proto = {p["ref"]: p for p in pa}
    byref, bypad = improved_match(parts, pads)
    holes = list(bd["holes"])

    def group_of_pad(pd):
        # the smallest prototype group whose box holds the opening centre
        c = [g for g in groups if g["bbox"][0] - 1e-3 <= pd["x"] <= g["bbox"][2] + 1e-3 and g["bbox"][1] - 1e-3 <= pd["y"] <= g["bbox"][3] + 1e-3]
        return min(c, key=lambda g: (g["bbox"][2] - g["bbox"][0]) * (g["bbox"][3] - g["bbox"][1]))["id"] if c else None

    gid_pads = {}
    for i, pd in enumerate(pads):
        gid_pads.setdefault(group_of_pad(pd), []).append(i)
    claimed_by = {g: p["ref"] for p in pa for g in p["groups"]}
    rows = []
    for p in parts:
        r = p["ref"]
        lx, ly, _ox, _oy, kind, known = envelope(p["package"])
        poly = part_polygon(p)
        mine = byref.get(r, [])
        gids = sorted({group_of_pad(pads[i]) for i in mine})
        nh = sum(1 for h in holes if h[3] and inside(part_polygon(p, margin=0.6), (h[0], h[1])))
        pr = proto[r]
        status = "matched" if pr["groups"] else "no_match"
        reason = ""
        if status == "matched":
            reason = "matched by position (nearest group within 0.8 mm)"
            extra = [g for g in gids if g not in pr["groups"]]
            if extra:
                reason += f"; but {len(extra)} more group(s) of the same part ({', '.join(extra)}) are not attached"
        elif not mine:
            reason = f"through-hole part: no paste layer for it ({nh} drilled holes in its footprint)" if (kind == "th" or nh > 0) else "no paste opening inside its footprint"
        else:
            why = []
            if len(gids) > 1:
                why.append(f"its {len(mine)} openings are split into {len(gids)} groups by the 0.6 mm link ({', '.join(gids)}); none holds the part origin")
            for gd in gids:
                owner = claimed_by.get(gd)
                others = {bypad[i] for i in gid_pads.get(gd, []) if i in bypad and bypad[i] != r}
                if others:
                    why.append(f"group {gd} also holds openings of {', '.join(sorted(others))}")
                if owner and owner != r:
                    why.append(f"group {gd} was claimed first by {owner}")
            dmin = min(float(np.hypot(max(g["bbox"][0] - p["x"], 0, p["x"] - g["bbox"][2]), max(g["bbox"][1] - p["y"], 0, p["y"] - g["bbox"][3]))) for g in groups if g["id"] in gids)
            if dmin > 0.8:
                why.append(f"origin is {dmin:.1f} mm from the nearest of its groups (limit 0.8)")
            reason = "; ".join(why) if why else "unknown"
        rows.append(dict(ref=r, package=p["package"], value=p["value"], x=p["x"], y=p["y"], rot=p["rot"], side=p["side"], env=[lx, ly], kind=kind, known=known,
                         proto=status, improved=bool(mine), n_open=len(mine), groups=gids, holes=nh, reason=reason,
                         n_near=sum(1 for q in pads if dist_to_poly(poly, (q["x"], q["y"])) <= 1.0)))
    unclaimed = [dict(id=g["id"], bbox=g["bbox"], n=len(g["pads"]), owner_improved=sorted({bypad.get(i) for i in gid_pads.get(g["id"], [])} - {None}))
                 for g in groups if g["id"] not in claimed_by]
    return rows, unclaimed, dict(bd=bd, parts=parts, pads=pads, byref=byref, bypad=bypad)


def board_counts(name):
    """!
    @brief The counts of one board for the comparison table: parts, the prototype rule (group rule, no TO.C used), the envelope rule, and the openings against the TO.C truth when the paste file has it.
    @param name board folder name under data/.
    @return dict parts, proto, improved, openings, and ok, wrong, missed (None without TO.C).
    """
    folder = DATA / name
    bd = b.load_board(b.scan(folder))
    box, parts = bd["box"], bd["placement"]
    pads = {s: read_pads(folder, s, box) for s in ("top", "bottom")}
    allpads = pads["top"] + pads["bottom"]
    bd2 = dict(bd)
    bd2["groups"] = {}
    for side, fn in (("top", "pasteF.gbr"), ("bottom", "pasteB.gbr")):
        gs = []
        if (folder / fn).exists():
            gs = [dict(g, ref=None) for g in paste.by_proximity(folder / fn, box, pix=max(0.05, max(bd["w"], bd["h"]) / 2000.0), link_mm=0.6)]
            for i, g in enumerate(gs):
                g["side"], g["id"] = side, f"{side[0]}{i}"
        bd2["groups"][side] = gs
    pa, _ = b.match_parts(bd2)
    byref, bypad = improved_match(parts, allpads)
    out = dict(parts=len(parts), proto=sum(1 for p in pa if p["groups"]), improved=len(byref), openings=len(allpads), ok=None, wrong=None, missed=None)
    tr = {s: truth_pads(folder, s, pads[s]) for s in ("top", "bottom")}
    if any(t is not None for t in tr.values()):
        truth = (tr["top"] or [None] * len(pads["top"])) + (tr["bottom"] or [None] * len(pads["bottom"]))
        ok = sum(1 for i, r in bypad.items() if truth[i] == r)
        wrong = sum(1 for i, r in bypad.items() if truth[i] not in (None, r))
        out.update(ok=ok, wrong=wrong, missed=sum(1 for t in truth if t) - ok - wrong)
    return out
