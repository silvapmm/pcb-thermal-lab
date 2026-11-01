#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file backend.py
@brief Data side of the Gerber import window prototype: scan a folder or ZIP, detect the function of each file, read the board with the independent reader of the research, match paste openings to parts, diff two imports.
@details Everything here is real (the reader `research/gerber-import/lib/native_gerber.py`, `paste.py`, `pnp.py`, `project_format.py` of this investigation) except the project creation, which the prototype
         replaces by a summary record. No Qt in this module, so the tests and the window share it. Lengths are in mm, powers in W, temperatures in degC.
"""

import hashlib
import math
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parents[2]
for _p in (RESEARCH / "gerber-import" / "lib", RESEARCH / "gerber-real-boards" / "lib", RESEARCH.parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import native_gerber as ng  # noqa: E402
import paste  # noqa: E402
import pnp  # noqa: E402
import project_format as pf  # noqa: E402

FUNCTIONS = ["Top copper", "Inner copper 1", "Inner copper 2", "Inner copper 3", "Inner copper 4", "Bottom copper", "Board outline / profile", "Plated drill", "Non-plated drill",
             "Solder paste top", "Solder paste bottom", "Solder mask top", "Solder mask bottom", "Legend (silkscreen) top", "Legend (silkscreen) bottom",
             "Placement (pick and place)", "Ignore"]
COPPER = ("Top copper", "Inner copper 1", "Inner copper 2", "Inner copper 3", "Inner copper 4", "Bottom copper")
USED_BY_DEFAULT = COPPER + ("Board outline / profile", "Plated drill", "Non-plated drill", "Solder paste top", "Solder paste bottom", "Placement (pick and place)")
DEFAULT_BOARD = RESEARCH / "gerber-real-boards" / "data" / "rp2040"


# ------------------------------------------------------------------------------------------------------------------------------ sources
def open_source(path, workdir):
    """!
    @brief Give a folder of fabrication files from a folder or a ZIP archive.
    @param path A folder, or a .zip file (extracted to `workdir`; names that leave the folder are refused).
    @param workdir Empty folder where an archive is extracted.
    @return pathlib.Path of the folder that holds the files (the only sub-folder when the archive has one).
    @throws ValueError If a ZIP member would be written outside `workdir`.
    """
    p = Path(path).expanduser()
    if p.is_dir():
        return p
    root = Path(workdir).resolve()
    with zipfile.ZipFile(p) as z:
        for m in z.namelist():
            if not (root / m).resolve().is_relative_to(root):          # zip-slip guard: the archive is untrusted data
                raise ValueError(f"unsafe name in the archive: {m}")
        z.extractall(root)
    subs = [d for d in root.iterdir() if d.is_dir() and not d.name.startswith("__")]
    files = [f for f in root.iterdir() if f.is_file()]
    return subs[0] if len(subs) == 1 and not files else root


def sha256_of(path):
    """!
    @brief SHA-256 of a file (recognises the same set of files again).
    @param path File path.
    @return str hex digest.
    """
    return pf.sha256_of(path)


def detect_function(path):
    """!
    @brief Guess the function of a fabrication file from its X2 attributes (Gerber and Excellon comment), then from its name and, for a table, from its header.
    @param path File path.
    @return tuple (function from FUNCTIONS, how it was detected) or ("Ignore", "unknown").
    """
    p = Path(path)
    suffix = p.suffix.lower()
    try:
        head = p.read_text(errors="replace")[:6000]
    except OSError:
        return "Ignore", "unreadable"
    if suffix in (".drl", ".xln", ".exc", ".txt") and re.search(r"(M48|METRIC|INCH)", head) and not head.lstrip().startswith("%"):
        plated, _, _ = ng.drill_function(p)
        return ("Non-plated drill" if plated is False else "Plated drill"), ("Excellon: " + ("Plated" if plated else "NonPlated") if plated is not None else "Excellon: header")
    m = re.search(r"%TF\.FileFunction,([^*%]*)", head)
    if m:
        f = [v.strip() for v in m.group(1).split(",")]
        side = f[2].lower() if len(f) > 2 else (f[1].lower() if len(f) > 1 else "")
        if f[0] == "Copper" and len(f) >= 3:
            n = int(re.sub(r"\D", "", f[1]) or 0)
            if side.startswith("top"):
                return "Top copper", "X2: " + ",".join(f[:3])
            if side.startswith("bot"):
                return "Bottom copper", "X2: " + ",".join(f[:3])
            return f"Inner copper {max(1, min(4, n - 1))}", "X2: " + ",".join(f[:3])
        if f[0] == "Profile":
            return "Board outline / profile", "X2: Profile"
        top = side.startswith("top")
        table = {"Paste": ("Solder paste top", "Solder paste bottom"), "Soldermask": ("Solder mask top", "Solder mask bottom"), "Legend": ("Legend (silkscreen) top", "Legend (silkscreen) bottom")}
        if f[0] in table:
            return table[f[0]][0 if top else 1], "X2: " + ",".join(f[:2])
        return "Ignore", "X2: " + f[0]
    name = p.name.lower()
    stem = p.stem.lower()
    if stem in ("f", "top"):                                       # bare names of some CAD exports: F.gbr / B.gbr
        return "Top copper", "name"
    if stem in ("b", "bot", "bottom"):
        return "Bottom copper", "name"
    role, pos, _ = ng.classify(p)
    if role == "copper":
        return {"top": "Top copper", "bottom": "Bottom copper"}.get(pos, "Inner copper 1"), "name"
    if role == "outline":
        return "Board outline / profile", "name"
    if role == "drill":
        return "Plated drill", "name"
    for key, (a, b) in (("paste", ("Solder paste top", "Solder paste bottom")), ("mask", ("Solder mask top", "Solder mask bottom")), ("silk", ("Legend (silkscreen) top", "Legend (silkscreen) bottom"))):
        if key in name:
            return (b if re.search(r"(bot|\.gb|[a-z]b$)", stem) or stem.endswith(("_b", "-b", ".b")) else a), "name"
    if suffix in (".csv", ".pos", ".txt", ".xy"):
        try:
            if pnp.read_placement(p):
                return "Placement (pick and place)", "columns"
        except ValueError:
            pass
    return "Ignore", "unknown"


def scan(folder):
    """!
    @brief List the files of a folder with the function the program detects for each.
    @param folder Folder with fabrication files.
    @return list of dicts: name, path, size (bytes), func, how, use (bool), sha (hex).
    """
    out = []
    for f in sorted(Path(folder).iterdir()):
        if not f.is_file() or f.name.startswith(".") or f.suffix.lower() in (".zip", ".png", ".pdf", ".md", ".json", ".gbrjob", ".kicad_pcb"):
            continue
        func, how = detect_function(f)
        out.append({"name": f.name, "path": str(f), "size": f.stat().st_size, "func": func, "how": how, "use": func in USED_BY_DEFAULT, "sha": sha256_of(f)})
    return out


def check_files(files):
    """!
    @brief Problems of the layer assignment that stop the import (step 1 complete or not).
    @param files List of file dicts of `scan`.
    @return list of text lines; empty when the step is complete.
    """
    used = [f for f in files if f["use"] and f["func"] != "Ignore"]
    problems = []
    seen = {}
    for f in used:
        if f["func"] in COPPER or f["func"] in ("Board outline / profile", "Solder paste top", "Solder paste bottom", "Placement (pick and place)"):
            if f["func"] in seen:
                problems.append(f"Two files claim '{f['func']}': {seen[f['func']]} and {f['name']}")
            seen[f["func"]] = f["name"]
    if not any(f["func"] in COPPER for f in used):
        problems.append("No copper layer is selected")
    if not any(f["func"] == "Board outline / profile" for f in used):
        problems.append("No board outline: the box of the copper is used")
        problems = [p for p in problems if not p.startswith("No board outline")]    # a warning, not a stop; kept out of the blocking list
    return problems


# ------------------------------------------------------------------------------------------------------------------------------ board
def _pixel(w, h):
    """!
    @brief Preview pixel: 0.1 mm, coarser for a large board so that a layer stays near 900 pixels a side.
    @param w Board width (mm).
    @param h Board height (mm).
    @return float pixel (mm).
    """
    return max(0.1, max(w, h) / 900.0)


def load_board(files, cache=None):
    """!
    @brief Read the used files and build everything the three steps show: copper coverage per layer, outline, holes, paste groups and the placement.
    @param files List of file dicts of `scan` (the `use` and `func` fields decide).
    @param cache Optional dict reused between calls (a changed function does not redraw the layers that did not change).
    @return dict with box, w, h, pix, copper (list of (function, coverage)), outline mask, holes (x, y, d, plated), groups (list per paste side), placement (list of parts read), thinnest_line, n_layers.
    """
    cache = {} if cache is None else cache
    used = {f["func"]: f for f in files if f["use"] and f["func"] != "Ignore"}
    outline = used.get("Board outline / profile")
    boxes = []
    if outline:
        boxes.append(ng.layer_bbox(outline["path"]))
    cu = [(fn, used[fn]) for fn in COPPER if fn in used]
    if not boxes:
        boxes = [ng.layer_bbox(f["path"]) for _, f in cu]
    boxes = [b for b in boxes if b]
    if not boxes:
        raise ValueError("no outline and no copper to size the board")
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    w, h = box[2] - box[0], box[3] - box[1]
    pix = _pixel(w, h)
    board = {"box": box, "w": w, "h": h, "pix": pix, "copper": [], "outline": None, "holes": [], "groups": {"top": [], "bottom": []}, "placement": [], "thinnest_line": None}
    thin = []
    for fn, f in cu:
        key = (f["sha"], box, pix)
        if key not in cache:
            lay = ng.Layer(Path(f["path"]).read_text(errors="replace"))
            radii = [getattr(op[2][0], "radius", None) for op in lay.ops if op[0] == "stroke"]
            radii = [r for r in radii if r]
            cache[key] = (ng.render_coverage(lay, box[0], box[3], w, h, pix, supersample=2), 2 * min(radii) if radii else None)
        cov, t = cache[key]
        board["copper"].append((fn, cov))
        if t:
            thin.append(t)
    board["thinnest_line"] = min(thin) if thin else None
    if outline:
        board["outline"] = ng.render(outline["path"], box[0], box[3], w, h, pix)
    for fn in ("Plated drill", "Non-plated drill"):
        if fn in used:
            for (x, y, d, plated) in ng.read_drill(used[fn]["path"]):
                board["holes"].append((x, y, d, fn == "Plated drill" if plated is None else bool(plated)))
    pix_p = max(0.05, max(w, h) / 2000.0)
    for side, fn in (("top", "Solder paste top"), ("bottom", "Solder paste bottom")):
        if fn in used:
            path = used[fn]["path"]
            text = Path(path).read_text(errors="replace")
            if "%TO.C," in text:
                byref = paste.by_reference(path)
                board["groups"][side] = [dict(g, ref=r, pads=[{"bbox": g["bbox"], "area": g["area"], "x": g["x"], "y": g["y"]}]) for r, g in byref.items()]
            else:
                board["groups"][side] = [dict(g, ref=None) for g in paste.by_proximity(path, box, pix=pix_p, link_mm=0.6)]
            for i, g in enumerate(board["groups"][side]):
                g["side"], g["id"] = side, f"{side[0]}{i}"
    if "Placement (pick and place)" in used:
        board["placement"] = pnp.read_placement(used["Placement (pick and place)"]["path"])
    board["n_layers"] = len(board["copper"])
    return board


def _union_box(boxes):
    """!
    @brief Rectangle around several boxes.
    @param boxes List of (x0, y0, x1, y1).
    @return tuple or None for an empty list.
    """
    return None if not boxes else (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def part_shapes(groups):
    """!
    @brief The two heat-source shapes of a part from its paste openings, and the one the program suggests.
    @details The hull is suggested when it covers clearly less than the box (a tab and pins, a QFN pad: heat enters where the pads are); otherwise the box.
    @param groups List of paste groups of the part.
    @return dict with box (x0, y0, x1, y1), hull (array or None), box_area, hull_area (mm2), suggested ("box" or "hull").
    """
    pads = [p for g in groups for p in g["pads"]]
    bb = _union_box([g["bbox"] for g in groups])
    sh = paste.shapes({"bbox": bb, "pads": pads})
    hull = sh.get("hull")
    box_area = sh["bbox"]["area"]
    hull_area = hull["area"] if hull else box_area
    return {"box": bb, "hull": None if not hull else hull["polygon"], "box_area": box_area, "hull_area": hull_area, "suggested": "hull" if hull and hull_area <= 0.85 * box_area else "box"}


def match_parts(board, claims=None):
    """!
    @brief Turn the placement file and the paste groups into the table of parts.
    @details Rule 1: a paste group that carries a component attribute (TO.C) belongs to that designator. Rule 2: the others are matched by position to the placement file (nearest group within 0.8 mm, the group
             that contains the part centre first). A part that no group claims has no opening; a group no part claims is "unmatched" (shown in red). Without a placement file every group is a part named P<n>.
    @param board Dict of `load_board`.
    @param claims Optional dict designator -> list of group ids that the user added by hand (kept).
    @return tuple (parts, unmatched group ids): parts are dicts with ref, package, value, x, y, side, groups (ids), match (text), shape data, use, power, tj, role, shape.
    """
    claims = claims or {}
    by_id = {g["id"]: g for side in board["groups"].values() for g in side}
    claimed = {}
    parts = []
    placement = board["placement"]
    refs_in_paste = {g["ref"] for g in by_id.values() if g["ref"]}
    if not placement:
        placement = [{"ref": g["ref"] or f"P{i + 1}", "value": "", "package": "(no placement file)", "x": g["x"], "y": g["y"], "side": g["side"], "rot": 0.0} for i, g in enumerate(by_id.values())]
    for p in placement:
        side_groups = board["groups"].get(p["side"], [])
        ids, how = [], "no paste opening"
        refg = [g for g in side_groups if g["ref"] == p["ref"]]
        if refg:
            ids, how = [g["id"] for g in refg], "matched by designator (TO.C)"
        else:
            free = [g for g in side_groups if g["id"] not in claimed and not g["ref"]]
            k = paste.pick(free, p["x"], p["y"], max_mm=0.8) if free else None
            if k is not None:
                ids, how = [free[k]["id"]], "matched by position"
        for gid in claims.get(p["ref"], []):
            if gid not in ids:
                ids.append(gid)
                how = "by position + picked by hand"
        for gid in ids:
            claimed[gid] = p["ref"]
        part = {"ref": p["ref"], "value": p.get("value", ""), "package": p["package"], "x": p["x"], "y": p["y"], "side": p["side"], "groups": ids, "match": how, "use": False, "power": 0.0, "tj": 0.0,
                "role": "Component", "shape": None, "shape_user": False}
        if ids:
            sh = part_shapes([by_id[i] for i in ids])
            part.update(box=sh["box"], hull=sh["hull"], box_area=sh["box_area"], hull_area=sh["hull_area"], suggested=sh["suggested"], shape=sh["suggested"])
        else:
            part.update(box=None, hull=None, box_area=0.0, hull_area=0.0, suggested=None)
        parts.append(part)
    # Designators written in the paste but absent from the placement file become parts too, so no opening is lost
    known = {p["ref"] for p in parts}
    for g in by_id.values():
        if g["ref"] and g["ref"] not in known and g["id"] not in claimed:
            sh = part_shapes([g])
            parts.append({"ref": g["ref"], "value": "", "package": "(paste only)", "x": g["x"], "y": g["y"], "side": g["side"], "groups": [g["id"]], "match": "matched by designator (TO.C)", "use": False,
                          "power": 0.0, "tj": 0.0, "role": "Component", "shape": sh["suggested"], "shape_user": False, "box": sh["box"], "hull": sh["hull"], "box_area": sh["box_area"],
                          "hull_area": sh["hull_area"], "suggested": sh["suggested"]})
            claimed[g["id"]] = g["ref"]
    unmatched = [gid for gid in by_id if gid not in claimed and by_id[gid]["area"] > 0]
    del refs_in_paste
    return parts, unmatched


def new_part_from_group(board, parts, gid):
    """!
    @brief Create a heat source from an unmatched paste opening (a click on it in the preview).
    @param board Dict of `load_board`.
    @param parts List of part dicts (changed in place: the new part is appended).
    @param gid Id of the group.
    @return dict the new part.
    """
    g = next(g for s in board["groups"].values() for g in s if g["id"] == gid)
    n = 1 + sum(1 for p in parts if re.fullmatch(r"H\d+", p["ref"]))
    sh = part_shapes([g])
    part = {"ref": f"H{n}", "value": "", "package": "(picked by hand)", "x": g["x"], "y": g["y"], "side": g["side"], "groups": [gid], "match": "picked by hand", "use": True, "power": 0.0, "tj": 0.0,
            "role": "Source", "shape": sh["suggested"], "shape_user": False, "box": sh["box"], "hull": sh["hull"], "box_area": sh["box_area"], "hull_area": sh["hull_area"], "suggested": sh["suggested"]}
    parts.append(part)
    return part


def refresh_shape(board, part):
    """!
    @brief Recompute the shape data of a part after its openings changed (the user's shape choice is kept).
    @param board Dict of `load_board`.
    @param part Part dict, changed in place.
    @return None
    """
    by_id = {g["id"]: g for s in board["groups"].values() for g in s}
    sh = part_shapes([by_id[i] for i in part["groups"]])
    part.update(box=sh["box"], hull=sh["hull"], box_area=sh["box_area"], hull_area=sh["hull_area"], suggested=sh["suggested"])
    if not part["shape_user"]:
        part["shape"] = sh["suggested"]


def group_at(board, x, y):
    """!
    @brief The paste opening group under a point of the preview.
    @param board Dict of `load_board`.
    @param x X (mm, file coordinates).
    @param y Y (mm).
    @return dict group, or None.
    """
    for side in board["groups"].values():
        k = paste.pick(side, x, y, max_mm=0.3) if side else None
        if k is not None:
            return side[k]
    return None


def shape_polygon(part):
    """!
    @brief The chosen heat-source shape of a part as a polygon.
    @param part Part dict with a box.
    @return list of (x, y) or None when the part has no opening.
    """
    if part.get("box") is None:
        return None
    if part["shape"] == "hull" and part.get("hull") is not None:
        return [(float(x), float(y)) for x, y in part["hull"]]
    b = part["box"]
    return [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])]


# ------------------------------------------------------------------------------------------------------------------------------ record
def build_record(name, board, files, parts, mapping="faces", cell_mm=1.0):
    """!
    @brief The record the import would store in the project (format 2, `imports`), in the form of `project_format.import_record` plus the settings of the three steps.
    @param name Board name.
    @param board Dict of `load_board`.
    @param files List of file dicts.
    @param parts List of part dicts.
    @param mapping Copper mapping key: "faces", "fill" or "lambda".
    @param cell_mm Solver cell (mm).
    @return dict (no masks: embed False in the prototype).
    """
    used = [f for f in files if f["use"] and f["func"] != "Ignore"]
    rec = pf.import_record(name, board["pix"], board["box"], [(fn, fn, np.zeros((1, 1))) for fn, _ in board["copper"]], embed=False,
                           sources=[{"name": f["name"], "size": f["size"], "sha256": f["sha"], "function": f["func"]} for f in used],
                           holes=[(round(x, 4), round(y, 4), round(d, 4)) for x, y, d, p in board["holes"] if p],
                           parts=[])
    rec["parts"] = [{"ref": p["ref"], "package": p["package"], "x": round(p["x"], 4), "y": round(p["y"], 4), "side": p["side"], "use": bool(p["use"]), "power_w": p["power"], "tj_max_c": p["tj"],
                     "role": p["role"], "shape": p["shape"], "shape_user": bool(p["shape_user"]), "polygon": shape_polygon(p)} for p in parts]
    rec["settings"] = {"mapping": mapping, "cell_mm": cell_mm}
    return rec


# ------------------------------------------------------------------------------------------------------------------------------ re-import
def _centre(poly):
    """!
    @brief Centre of the bounding box of a polygon.
    @param poly List of (x, y).
    @return tuple (x, y).
    """
    a = np.asarray(poly, float)
    return (a[:, 0].min() + a[:, 0].max()) / 2, (a[:, 1].min() + a[:, 1].max()) / 2


def _size(poly):
    """!
    @brief Width and height of the bounding box of a polygon.
    @param poly List of (x, y).
    @return tuple (w, h) in mm.
    """
    a = np.asarray(poly, float)
    return float(np.ptp(a[:, 0])), float(np.ptp(a[:, 1]))


def diff_parts(old, new, move_tol=0.3, size_tol=0.2):
    """!
    @brief Compare the parts of the project's import (`old`) with the parts of the new files (`new`) by designator.
    @param old List of part records of the stored import.
    @param new List of part records of the new import.
    @param move_tol Centre shift above which a part is "moved" (mm).
    @param size_tol Change of width or height above which a part is "resized" (mm).
    @return list of dicts: ref, change ("kept", "moved", "resized", "moved and resized", "new", "removed"), detail text, old and new records.
    """
    o = {p["ref"]: p for p in old}
    n = {p["ref"]: p for p in new}
    out = []
    for ref in sorted(set(o) | set(n), key=lambda r: (re.sub(r"\d+", "", r), int(re.sub(r"\D", "", r) or 0))):
        a, b = o.get(ref), n.get(ref)
        if a is None:
            out.append({"ref": ref, "change": "new", "detail": f"at {b['x']:.2f}, {b['y']:.2f}", "old": None, "new": b})
        elif b is None:
            out.append({"ref": ref, "change": "removed", "detail": f"was at {a['x']:.2f}, {a['y']:.2f}" + (f", {a['power_w']:g} W" if a.get("power_w") else ""), "old": a, "new": None})
        else:
            parts, detail = [], []
            pa, pb = a.get("polygon"), b.get("polygon")
            ca = _centre(pa) if pa else (a["x"], a["y"])
            cb = _centre(pb) if pb else (b["x"], b["y"])
            d = math.hypot(ca[0] - cb[0], ca[1] - cb[1])
            if d > move_tol:
                parts.append("moved")
                detail.append(f"{d:.2f} mm")
            if pa and pb:
                (wa, ha), (wb, hb) = _size(pa), _size(pb)
                if abs(wa - wb) > size_tol or abs(ha - hb) > size_tol:
                    parts.append("resized")
                    detail.append(f"{wa:.1f} x {ha:.1f} -> {wb:.1f} x {hb:.1f} mm")
            out.append({"ref": ref, "change": " and ".join(parts) or "kept", "detail": ", ".join(detail), "old": a, "new": b})
    return out


def same_board(old_rec, new_rec, tol=0.05):
    """!
    @brief Decide whether a new set of files looks like the same board as a stored import (outline box within a fraction, shared sources).
    @param old_rec Stored import record.
    @param new_rec New record.
    @param tol Relative difference of width or height accepted.
    @return tuple (same bool, reasons list of str).
    """
    ow, oh = old_rec["box"][2] - old_rec["box"][0], old_rec["box"][3] - old_rec["box"][1]
    nw, nh = new_rec["box"][2] - new_rec["box"][0], new_rec["box"][3] - new_rec["box"][1]
    reasons = []
    if abs(ow - nw) > tol * ow or abs(oh - nh) > tol * oh:
        reasons.append(f"the outline is {nw:.1f} x {nh:.1f} mm, the stored one {ow:.1f} x {oh:.1f} mm")
    old_sha = {s["sha256"] for s in old_rec["sources"]}
    new_sha = {s["sha256"] for s in new_rec["sources"]}
    if not old_sha & new_sha and old_sha and new_sha:
        reasons.append("none of the files is byte-identical to a stored one")
    shared_names = {s["name"] for s in old_rec["sources"]} & {s["name"] for s in new_rec["sources"]}
    if not shared_names:
        reasons.append("no file name in common")
    return not reasons, reasons


def classify_sources(old_rec, new_rec):
    """!
    @brief Compare the file sets of the stored import and of the new files, per function.
    @param old_rec Stored import record.
    @param new_rec New record.
    @return list of dicts: function, status ("identical", "changed", "added", "only stored"), old and new source (or None).
    """
    o = {s["function"]: s for s in old_rec["sources"]}
    n = {s["function"]: s for s in new_rec["sources"]}
    out = []
    for fn in FUNCTIONS:
        a, b = o.get(fn), n.get(fn)
        if a is None and b is None:
            continue
        status = "added" if a is None else "only stored" if b is None else "identical" if a["sha256"] == b["sha256"] else "changed"
        out.append({"function": fn, "status": status, "old": a, "new": b})
    return out


def apply_reimport(mode, old_rec, new_rec, remove_refs=(), file_choice=None):
    """!
    @brief Merge a new import into the stored one by the rule of the chosen command.
    @details "replace" and "update": copper, drills and outline come from the new files; a part with the same designator keeps its power, Tj max, role, use and an edited shape; a part that disappeared is
             removed only if listed in `remove_refs` (else it stays marked as "orphan" with its data, nothing is lost silently). "update" is the same merge plus the diff table the user saw.
             "add": the stored data stay; only the functions the stored import lacks are taken from the new files, and for a function both have, `file_choice[function]` says "stored" (default) or "new".
    @param mode "replace", "update" or "add".
    @param old_rec Stored import record.
    @param new_rec New record.
    @param remove_refs Designators the user confirmed to remove.
    @param file_choice dict function -> "stored" or "new" for conflicts (mode "add").
    @return dict: the merged record, "changes" (list of text lines) and "orphans" (designators kept although absent).
    """
    file_choice = file_choice or {}
    changes, orphans = [], []
    if mode == "add":
        merged = dict(old_rec)
        sources = {s["function"]: s for s in old_rec["sources"]}
        for item in classify_sources(old_rec, new_rec):
            if item["status"] == "added":
                sources[item["function"]] = item["new"]
                changes.append(f"added {item['function']}: {item['new']['name']}")
            elif item["status"] == "changed" and file_choice.get(item["function"], "stored") == "new":
                sources[item["function"]] = item["new"]
                changes.append(f"conflict on {item['function']}: took the new file {item['new']['name']}")
            elif item["status"] == "changed":
                changes.append(f"conflict on {item['function']}: kept the stored file {item['old']['name']}")
        merged["sources"] = list(sources.values())
        if any(i["function"] in ("Placement (pick and place)", "Solder paste top", "Solder paste bottom") and i["status"] == "added" for i in classify_sources(old_rec, new_rec)):
            known = {p["ref"] for p in old_rec["parts"]}
            merged["parts"] = list(old_rec["parts"]) + [p for p in new_rec["parts"] if p["ref"] not in known]
            changes.append(f"{len(merged['parts']) - len(old_rec['parts'])} part(s) from the added files; existing parts untouched")
        return {"record": merged, "changes": changes, "orphans": orphans}
    merged = dict(new_rec)
    old = {p["ref"]: p for p in old_rec["parts"]}
    parts = []
    for p in new_rec["parts"]:
        q = dict(p)
        o = old.get(p["ref"])
        if o is not None:
            for k in ("power_w", "tj_max_c", "role", "use"):
                q[k] = o[k]
            if o.get("shape_user"):
                q["shape"], q["shape_user"], q["polygon"] = o["shape"], True, o.get("polygon") if o.get("shape") == p.get("shape") else p.get("polygon")
            changes.append(f"{p['ref']}: kept power {o['power_w']:g} W" if o["power_w"] else f"{p['ref']}: matched")
        parts.append(q)
    new_refs = {p["ref"] for p in new_rec["parts"]}
    for ref, o in old.items():
        if ref not in new_refs:
            if ref in remove_refs:
                changes.append(f"{ref}: removed (confirmed)")
            else:
                orphans.append(ref)
                parts.append(dict(o, orphan=True))
                changes.append(f"{ref}: not in the new files, kept as an orphan until confirmed")
    merged["parts"] = parts
    return {"record": merged, "changes": changes, "orphans": orphans}


def demo_previous(rec, seed_refs=None):
    """!
    @brief Make a plausible stored import from a record, for the prototype: powers on three parts, one part moved by 2 mm, one removed, one resized, one extra part, a placement file and a paste layer not yet added, a file edited.
    @param rec Record of `build_record` (not changed).
    @param seed_refs Optional list of designators to act on (default: chosen from the parts that have an opening).
    @return dict, the stored import as an earlier session would have left it.
    """
    old = {k: (list(v) if isinstance(v, list) else v) for k, v in rec.items()}
    parts = [dict(p) for p in rec["parts"]]
    refs = seed_refs or [p["ref"] for p in sorted((p for p in parts if p.get("polygon")), key=lambda p: -_area(p["polygon"]))][:6]
    for k, p in enumerate(parts):
        if p["ref"] in refs[:3]:
            p["power_w"], p["tj_max_c"], p["use"] = [1.0, 0.3, 0.05][refs.index(p["ref"])], 125.0, True
    if len(refs) >= 4:
        for p in parts:
            if p["ref"] == refs[3]:
                p["polygon"] = [(x + 2.0, y) for x, y in p["polygon"]]                      # the layout revision moved it
                p["x"] += 2.0
            if len(refs) >= 5 and p["ref"] == refs[4] and p.get("polygon"):
                cx, cy = _centre(p["polygon"])
                p["polygon"] = [(cx + (x - cx) * 0.6, cy + (y - cy) * 0.6) for x, y in p["polygon"]]   # it was smaller before
    if len(refs) >= 6:
        parts = [p for p in parts if p["ref"] != refs[5]]                                  # it is new in the new files
    parts.append({"ref": "D99", "package": "LED_0603", "x": 5.0, "y": 5.0, "side": "top", "use": True, "power_w": 0.1, "tj_max_c": 85.0, "role": "Component", "shape": "box", "shape_user": False,
                  "polygon": [(4.5, 4.5), (5.5, 4.5), (5.5, 5.5), (4.5, 5.5)]})            # it was removed from the layout
    old["parts"] = parts
    srcs = []
    for s in rec["sources"]:
        if s["function"] in ("Placement (pick and place)", "Solder paste bottom"):
            continue                                                                      # the stored import lacks them: the "add files" command offers them
        s = dict(s)
        if s["function"] == "Top copper":
            s["sha256"] = "0" * 64                                                        # an earlier revision of the copper: a conflict for "add"
        srcs.append(s)
    old["sources"] = srcs
    return old


def _area(poly):
    """!
    @brief Bounding-box area of a polygon.
    @param poly List of (x, y).
    @return float mm2.
    """
    w, h = _size(poly)
    return w * h


# ------------------------------------------------------------------------------------------------------------------------------ synthetic board
def make_synthetic(folder):
    """!
    @brief Write a small synthetic 2-layer board as Gerber, Excellon and CSV files (copper pour with tracks, three packages with TO.C paste, two vias, a placement file).
    @param folder Empty folder that receives the files.
    @return pathlib.Path of the folder.
    """
    d = Path(folder)
    d.mkdir(parents=True, exist_ok=True)
    head = "%FSLAX46Y46*%\n%MOMM*%\n%LPD*%\n"
    ap = "%ADD10C,0.250000*%\n%ADD11R,1.000000X1.000000*%\n%ADD12R,3.000000X2.500000*%\n%ADD13C,1.500000*%\n"

    def c(v):
        return int(round(v * 1e6))

    def flash(x, y, a):
        return f"D{a}*\nX{c(x)}Y{c(y)}D03*\n"

    def rect(x0, y0, x1, y1):
        return f"G36*\nX{c(x0)}Y{c(y0)}D02*\nG01*\nX{c(x1)}Y{c(y0)}D01*\nX{c(x1)}Y{c(y1)}D01*\nX{c(x0)}Y{c(y1)}D01*\nX{c(x0)}Y{c(y0)}D01*\nG37*\n"

    def line(pts, a="10"):
        s = f"D{a}*\nX{c(pts[0][0])}Y{c(pts[0][1])}D02*\n"
        return s + "".join(f"X{c(x)}Y{c(y)}D01*\n" for x, y in pts[1:])

    (d / "edge.gbr").write_text("%TF.FileFunction,Profile,NP*%\n" + head + ap + line([(0, 0), (40, 0), (40, 30), (0, 30), (0, 0)]) + "M02*\n")
    (d / "F.gbr").write_text("%TF.FileFunction,Copper,L1,Top*%\n" + head + ap + rect(1, 1, 39, 29) + "%LPC*%\n" + rect(8, 10, 10, 20) + "%LPD*%\n" + line([(5, 5), (35, 5), (35, 25)]) + flash(12, 15, 12) +
                             flash(25, 12, 11) + flash(30, 20, 13) + "M02*\n")
    (d / "B.gbr").write_text("%TF.FileFunction,Copper,L2,Bot*%\n" + head + ap + rect(1, 1, 39, 29) + "M02*\n")
    paste_txt = "%TF.FileFunction,Paste,Top*%\n" + head + ap
    for ref, x, y, a in (("U1", 12, 15, 12), ("Q1", 25, 12, 11), ("D1", 30, 20, 11)):
        paste_txt += f"%TO.C,{ref}*%\n" + flash(x, y, a) + "%TD*%\n"
    (d / "pasteF.gbr").write_text(paste_txt + "M02*\n")
    (d / "drill.drl").write_text("M48\n; #@! TF.FileFunction,Plated,1,2,PTH\nMETRIC,TZ\nT1C0.300\n%\nT1\nX20.0Y10.0\nX22.0Y10.0\nM30\n")
    (d / "pos.csv").write_text('Ref,Val,Package,PosX,PosY,Rot,Side\n"U1","reg","SOT-223",12.0,15.0,0,top\n"Q1","fet","SOT-23",25.0,12.0,0,top\n"D1","led","D_0603",30.0,20.0,0,top\n"R1","1k","R_0603",20.0,25.0,0,top\n')
    return d


def default_source(workdir):
    """!
    @brief The board the prototype opens when none is named: the RP2040 board in the git-ignored data folder, else a synthetic one.
    @param workdir Folder where the synthetic board is written when needed.
    @return tuple (path, text saying which one).
    """
    if DEFAULT_BOARD.is_dir():
        return DEFAULT_BOARD, "RP2040 minimal board (git-ignored download, licence not checked: for the maintainer's eyes)"
    return make_synthetic(Path(workdir) / "synthetic"), "synthetic board"


def temp_workdir():
    """!
    @brief A new empty working folder (archives are extracted into it).
    @return str path.
    """
    return tempfile.mkdtemp(prefix="gerber_import_proto_")


__all__ = ["os"]
