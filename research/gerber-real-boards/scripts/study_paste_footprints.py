#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_paste_footprints.py
@brief Can a solder-paste layer give the program its parts: component footprints and heat sources picked by a click, with reference designators from the Gerber X2 attributes or from a placement file?
@details Four questions on the downloaded boards that have a paste layer and a placement file (registry.py):
         A. Groups: how many pad groups does each paste file give by proximity (link distance 0.3, 0.6, 1.0, 1.5 mm), how many reference designators does the file itself write (X2 attribute TO.C), and how do the
            two agree (a group holding several references = parts merged by a too large link distance; a reference in several groups = a part split by a too small one)?
         B. Placement files: after `pnp.register` (translation and sign of Y found from the data, not assumed), how many parts of the file fall within 0.5, 1 and 2 mm of a paste group, and do the references of the file and of
            TO.C agree for the groups they both name? (The origin of a placement file is the part origin, not the paste centroid: a 2 mm tolerance is the fair one for large parts.)
         C. Click to footprint: for every group the click at the centre of its largest opening and at five random points of its bounding box must pick that group (`paste.pick`); the number of boxes that overlap is reported.
         E. X3 component layer (the Ucamco sample "stickhub", KiCad 8): the parts with reference, footprint, value, rotation, origin, courtyard and pins against the references written in the paste file.
         D. Heat source: for the three groups with the largest paste area, 1 W is put on the top layer as the bounding box, the convex hull and the largest opening, on a 30 mm window imported at 0.5 mm cells with the flow-based
            faces (program network of 2.4.5): the hottest cell and the mean rise over the bounding box are compared. This shows what the choice of footprint does to the answer; it is not a validation of a part's temperature.
         Output: out/paste_footprints.json and a printed table per board. Success criterion (before the run): with the best link distance at least 95 % of the references of TO.C land in exactly one group, at least 90 % of the
         placement parts are within 2 mm of a group of their own side after registration, the click picks the right group in 100 % of the trials, and the footprint choice moves the hottest cell by a figure that the README can state.
         NOT verified: parts with no paste opening (through-hole, bottom-side parts of a board with a top-only paste file), rotated large parts with a bounding box much larger than the hull, the junction temperature.
         Run (from the repository root): .venv-research/bin/python research/gerber-real-boards/scripts/study_paste_footprints.py [board ...]   (about 15 minutes)
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import json
import sys
import time

import numpy as np

import boardrun
import native_gerber as ng
import paste
import pnp
import rb_paths
import x3
import registry
import faces as im

LINKS = (0.3, 0.6, 1.0, 1.5)


def contains(bbox, x, y, tol=0.0):
    """!
    @brief Whether a point is inside a bounding box.
    @param bbox (xmin, ymin, xmax, ymax).
    @param x X.
    @param y Y.
    @param tol Margin (mm).
    @return bool.
    """
    return bbox[0] - tol <= x <= bbox[2] + tol and bbox[1] - tol <= y <= bbox[3] + tol


def groups_and_references(key, roles, box, side="top"):
    """!
    @brief Part A for one board and side: groups by proximity at every link distance and the references of the file.
    @param key Board key (for the report).
    @param roles registry.roles dict.
    @param box Board box.
    @param side "top" or "bottom".
    @return tuple (report dict, groups by proximity at link 1.0, references dict from TO.C).
    """
    path = roles["paste_top"] if side == "top" else roles["paste_bottom"]
    if path is None or path.stat().st_size < 400:
        return {"side": side, "empty": True}, [], {}
    refs = paste.by_reference(path)
    rep = {"side": side, "empty": False, "references_in_file": len(refs), "links": {}}
    keep = []
    for link in LINKS:
        g = paste.by_proximity(path, box, pix=0.05, link_mm=link)
        merged = split = 0
        if refs:
            per_group = [[r for r, v in refs.items() if contains(gr["bbox"], v["x"], v["y"], 0.05)] for gr in g]
            merged = sum(1 for lst in per_group if len(lst) > 1)
            hits = {r: sum(1 for lst in per_group if r in lst) for r in refs}
            split = sum(1 for n in hits.values() if n > 1)
            exactly_one = sum(1 for n in hits.values() if n == 1)
            # A part is intact when one group holds all of its pads (its box is covered to 95 %) and no other part's centre: the metric that says the group IS the part
            intact = 0
            for r, v in refs.items():
                bb = v["bbox"]
                area_r = max((bb[2] - bb[0]) * (bb[3] - bb[1]), 1e-9)
                for gr, lst in zip(g, per_group):
                    gb = gr["bbox"]
                    inter = max(0.0, min(bb[2], gb[2]) - max(bb[0], gb[0])) * max(0.0, min(bb[3], gb[3]) - max(bb[1], gb[1]))
                    if inter >= 0.95 * area_r and lst == [r]:
                        intact += 1
                        break
            rep["links"][str(link)] = {"groups": len(g), "groups_with_several_references": merged, "references_in_several_groups": split, "references_in_exactly_one_group": exactly_one, "parts_intact": intact}
        else:
            rep["links"][str(link)] = {"groups": len(g)}
        if link == 1.0:
            keep = g
    return rep, keep, refs


def placement_check(roles, groups, side="top"):
    """!
    @brief Part B: register the placement file on the groups and count the parts near a group.
    @param roles registry.roles dict.
    @param groups Groups by proximity (one side).
    @param side "top" or "bottom" (the parts of that side are used).
    @return dict with the transform and the counts within 0.5, 1 and 2 mm; empty when there is no placement file.
    """
    if roles["placement"] is None or not groups:
        return {}
    parts = [p for p in pnp.read_placement(roles["placement"]) if p["side"] == side]
    if not parts:
        return {"parts": 0}
    gc = np.array([[g["x"], g["y"]] for g in groups])
    pc = np.array([[p["x"], p["y"]] for p in parts])
    tr = pnp.register(gc, pc, tol_mm=2.0)
    q = pc * np.array([tr["sx"], tr["sy"]]) + np.array([tr["dx"], tr["dy"]])
    d = np.linalg.norm(q[:, None, :] - gc[None, :, :], axis=2).min(axis=1)
    return {"parts": len(parts), "transform": {k: tr[k] for k in ("sx", "sy", "dx", "dy")},
            "within_0.5mm": int((d <= 0.5).sum()), "within_1mm": int((d <= 1.0).sum()), "within_2mm": int((d <= 2.0).sum()), "median_mm": float(np.median(d))}


def reference_agreement(roles, groups, refs, tr, side="top"):
    """!
    @brief Whether the reference designator of the placement file and the one of TO.C agree for the groups both name.
    @param roles registry.roles dict.
    @param groups Groups by proximity.
    @param refs References of TO.C (paste.by_reference).
    @param tr Transform of placement_check.
    @param side "top" or "bottom".
    @return dict with compared, agree, and the first ten disagreements.
    """
    if not refs or not groups or "sx" not in tr:
        return {}
    parts = [p for p in pnp.read_placement(roles["placement"]) if p["side"] == side]
    out = {"compared": 0, "agree": 0, "disagreements": []}
    for g in groups:
        in_g = [r for r, v in refs.items() if contains(g["bbox"], v["x"], v["y"], 0.05)]
        near = [(np.hypot(*(np.array(pnp.apply(tr, p["x"], p["y"])) - [g["x"], g["y"]])), p["ref"]) for p in parts]
        if not in_g or not near:
            continue
        nearest = min(near)[1]
        out["compared"] += 1
        if nearest in in_g:
            out["agree"] += 1
        elif len(out["disagreements"]) < 10:
            out["disagreements"].append({"group_at": [round(g["x"], 2), round(g["y"], 2)], "gerber": in_g, "placement_nearest": nearest})
    return out


def click_test(groups, rng):
    """!
    @brief Part C: the click at the centre of the largest opening and at five random points of the bounding box picks the right group.
    @param groups Groups by proximity (with pads).
    @param rng numpy random generator.
    @return dict with trials, right (the centre clicks, which must always be right), random_trials, random_right (clicks at random points of the box: wrong ones are boxes inside other boxes), overlapping_boxes.
    """
    trials = right = rtrials = rright = 0
    for i, g in enumerate(groups):
        big = max(g["pads"], key=lambda p: p["area"])
        trials += 1
        right += int(paste.pick(groups, big["x"], big["y"]) == i)    # the centre of the largest opening must always pick its own group
        for _ in range(5):
            x, y = rng.uniform(g["bbox"][0], g["bbox"][2]), rng.uniform(g["bbox"][1], g["bbox"][3])
            rtrials += 1
            rright += int(paste.pick(groups, x, y) == i)
    overlap = sum(1 for i, a in enumerate(groups) for b in groups[i + 1:] if a["bbox"][0] < b["bbox"][2] and b["bbox"][0] < a["bbox"][2] and a["bbox"][1] < b["bbox"][3] and b["bbox"][1] < a["bbox"][3])
    return {"trials": trials, "right": right, "random_trials": rtrials, "random_right": rright, "overlapping_boxes": overlap}


def footprint_effect(key, roles, groups, n_groups=3, window=30.0, cell=0.5):
    """!
    @brief Part D: the same 1 W on the three biggest groups as bounding box, hull and largest opening.
    @param key Board key.
    @param roles registry.roles dict.
    @param groups Groups by proximity (top side).
    @param n_groups Number of groups.
    @param window Window side (mm).
    @param cell Cell (mm).
    @return list of dicts with the group position, its paste area and, per shape, the hottest cell and the mean over the bounding box (K).
    """
    out = []
    big = sorted(groups, key=lambda g: -g["area"])[:n_groups]
    for g in big:
        shp = paste.shapes(g)
        box = (g["x"] - window / 2, g["y"] - window / 2, g["x"] + window / 2, g["y"] + window / 2)
        ib = boardrun.import_window(key, box, cell / 10.0, cell)
        sheets = im.layer_sheets(ib, boardrun.make_problem(ib, (window / 2, window / 2)), "coverage")
        rec = {"x": g["x"], "y": g["y"], "paste_area_mm2": g["area"], "shapes": {}}
        for name, s in shp.items():
            off = np.array([ib.box[0], ib.box[1]])
            p = boardrun.make_problem(ib, (window / 2, window / 2), rect=None if s["kind"] != "rect" else (s["rect"][0] - off[0], s["rect"][1] - off[1], s["rect"][2] - off[0], s["rect"][3] - off[1]),
                                      polygon=None if s["kind"] != "polygon" else s["polygon"] - off)
            f = im.solve_faces(ib, p, im.layer_faces(sheets, ib, p, "flow"))
            bb = g["bbox"]
            i0, i1 = int((bb[1] - ib.box[1]) / cell), int(np.ceil((bb[3] - ib.box[1]) / cell))
            j0, j1 = int((bb[0] - ib.box[0]) / cell), int(np.ceil((bb[2] - ib.box[0]) / cell))
            rec["shapes"][name] = {"area_mm2": s["area"], "hottest_K": float(f[0].max()), "bbox_mean_K": float(f[0][i0:i1, j0:j1].mean())}
        out.append(rec)
    return out


def x3_check(roles, refs):
    """!
    @brief Part E: the Gerber X3 component layer (when the set has one) against the references written in the paste file.
    @param roles registry.roles dict.
    @param refs References of the paste file (paste.by_reference), top side.
    @return dict with the number of parts, how many have an origin, a courtyard and pins, how many references are in the paste file too, and the ratio of the courtyard area to the paste bounding box (median).
    """
    if roles.get("component_top") is None:
        return {}
    parts = x3.components(roles["component_top"])
    ratios = []
    for p in parts:
        cb = x3.courtyard_box(p)
        v = refs.get(p["ref"])
        if cb and v:
            bb = v["bbox"]
            ratios.append(((cb[2] - cb[0]) * (cb[3] - cb[1])) / max((bb[2] - bb[0]) * (bb[3] - bb[1]), 1e-9))
    return {"parts": len(parts), "with_origin": sum(p["origin"] is not None for p in parts), "with_courtyard": sum(bool(p["courtyard"]) for p in parts), "with_pins": sum(bool(p["pins"]) for p in parts),
            "in_paste_file": sum(p["ref"] in refs for p in parts), "paste_refs_not_in_component_layer": len([r for r in refs if r not in {p["ref"] for p in parts}]),
            "courtyard_to_paste_box_area_median": float(np.median(ratios)) if ratios else None, "first": [{k: p[k] for k in ("ref", "footprint", "value", "rotation", "origin")} for p in parts[:3]]}


def by_reference_check(roles, refs, side, rng):
    """!
    @brief Part B2: the groups the file itself names (TO.C) against the placement file, by reference designator, and the click on those groups.
    @param roles registry.roles dict.
    @param refs References of the paste file (paste.by_reference) of the side.
    @param side "top" or "bottom".
    @param rng numpy random generator.
    @return dict with the names in both files, the offset found from the names (median dx, dy over the common parts; no sign is assumed: the four sign pairs of X and Y are tried), the distance from the placement origin to the centre and to the bounding box of the group, and the click trials (a random opening pixel of the group must give its own reference when the smallest box containing the click is taken).
    """
    if not refs or roles["placement"] is None:
        return {}
    parts = {p["ref"]: p for p in pnp.read_placement(roles["placement"]) if p["side"] == side}
    common = [r for r in refs if r in parts]
    out = {"references_in_paste": len(refs), "parts_in_placement": len(parts), "in_both": len(common)}
    if not common:
        return out
    gc = np.array([[refs[r]["x"], refs[r]["y"]] for r in common])
    pc = np.array([[parts[r]["x"], parts[r]["y"]] for r in common])
    best = None
    for sx in (1, -1):                                                  # KiCad's position file mirrors X for the parts of the bottom side
        for sy in (1, -1):
            sg = np.array([sx, sy])
            off = np.median(gc - pc * sg, axis=0)
            d = np.linalg.norm(pc * sg + off - gc, axis=1)
            if best is None or np.median(d) < best[1]:
                best = ((sx, sy), float(np.median(d)), off, d)
    (sx, sy), med, off, d = best
    inside = sum(1 for r, q in zip(common, pc * np.array([sx, sy]) + off) if contains(refs[r]["bbox"], q[0], q[1], 0.0))
    out.update(sx=sx, sy=sy, offset_mm=[float(off[0]), float(off[1])], origin_to_group_centre_median_mm=med, origin_to_group_centre_p90_mm=float(np.percentile(d, 90)),
               origin_to_group_centre_max_mm=float(d.max()), origin_inside_group_box=inside, within_0_5mm=int((d <= 0.5).sum()), within_2mm=int((d <= 2.0).sum()),
               names_only_in_paste=sorted(set(refs) - set(parts))[:10], names_only_in_placement=len(set(parts) - set(refs)))
    # Click: a random lit pixel of each group; the answer is the reference whose box contains the click and is the smallest
    trials = right = 0
    for r, g in refs.items():
        ii, jj = np.nonzero(g["mask"])
        for k in rng.integers(0, len(ii), size=min(5, len(ii))):
            x, y = g["x_left"] + (jj[k] + 0.5) * g["pix"], g["y_top"] - (ii[k] + 0.5) * g["pix"]
            cand = [(((v["bbox"][2] - v["bbox"][0]) * (v["bbox"][3] - v["bbox"][1])), q) for q, v in refs.items() if contains(v["bbox"], x, y)]
            trials += 1
            right += int(bool(cand) and min(cand)[1] == r)
    out["click_trials"], out["click_right"] = trials, right
    return out


def main(argv):
    """!
    @brief Run the parts on every board that has a paste file and print the tables.
    @param argv Optional board keys.
    @return None.
    """
    keys = argv or registry.available()
    rng = np.random.default_rng(3)
    report = {}
    for key in keys:
        roles = registry.roles(key)
        if roles["paste_top"] is None and roles["paste_bottom"] is None:
            continue
        t = time.time()
        box = ng.layer_bbox(roles["outline"]) if roles["outline"] else ng.layer_bbox(roles["copper"][0])
        rec = {}
        for side in ("top", "bottom"):
            rep, groups, refs = groups_and_references(key, roles, box, side)
            rec[side] = {"groups": rep}
            if rep.get("empty"):
                continue
            rec[side]["placement"] = placement_check(roles, groups, side)
            rec[side]["reference_agreement"] = reference_agreement(roles, groups, refs, rec[side]["placement"].get("transform", {}), side)
            rec[side]["click"] = click_test(groups, rng)
            rec[side]["by_reference"] = by_reference_check(roles, paste.by_reference(roles["paste_top"] if side == "top" else roles["paste_bottom"]), side, rng)
            if side == "top":
                rec[side]["x3"] = x3_check(roles, refs)
                rec[side]["footprint_effect"] = footprint_effect(key, roles, groups)
        report[key] = rec
        print(f"\n{key} ({time.time() - t:.0f} s)")
        print(json.dumps(rec, indent=1)[:4000])
    rb_paths.OUT.mkdir(parents=True, exist_ok=True)
    with open(rb_paths.OUT / "paste_footprints.json", "w") as fh:
        json.dump(report, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
