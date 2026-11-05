#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_heater_margin.py
@brief Does a user margin around the heat-source polygon (grow the shape by 0.2, 0.3, 0.5 or 1.0 mm) cover the shapes the maintainer liked (the envelope from the package name, the exposed pad
       from the name), and how much does it move the part temperature of the SOT-223 and QFN parts?
@details Same parts, boards, windows, cell, coefficients and read-out as `study_heater_shape.py` (FVM at 0.5 mm, 1 W on the top layer, h = 10 W/m2K on both faces and the edge, the hottest
         face point under the heater as the program reports it). Five exposed-pad or tab parts: RP2040 U1 (SOT-223) and U3 (QFN-56), ISASTM U5 (SOT-223) and U15 (QFN-24), CMM2 U4 (QFN-28).
         For each: the hull of all the openings and the exposed pad (hull of the dominant group, `parts.dominant_group`, the program's default) each grown by a margin m (the Minkowski sum
         of the convex polygon with a disc of radius m, 48 points on the circle), and, as references, the envelope from the package name (`parts.part_envelope_polygon`, margin 0) and,
         for the QFN, the exposed pad as the square of the size in the footprint name.
         Run (from the repository root): .venv/bin/python research/gerber-real-boards/scripts/study_heater_margin.py   (about 1 minute, peak below 1 GB); writes out/heater_margin.json;
         `--table` prints the Markdown table of the last run.
"""

import json
import sys
import time

import _bootstrap  # noqa: F401  (paths of this investigation and the repository root)
import numpy as np

import study_heater_shape as base
from pcbthermal import fvm
from pcbthermal.gerber import parts as parts_mod

MARGINS = (0.0, 0.2, 0.3, 0.5, 1.0)
## The exposed-pad or tab parts of the shape study
PARTS = tuple(p for p in base.PARTS if p[1] in ("U1", "U3", "U5", "U15", "U4"))


def grow(poly, m, n=48):
    """!
    @brief Grow a convex polygon by a distance (Minkowski sum with a disc; the corners become arcs).
    @param poly List of (x, y) in mm, convex.
    @param m Margin in mm (0 returns the polygon).
    @param n Points on the circle.
    @return list of (x, y) in mm (counter-clockwise).
    """
    if m <= 0:
        return [tuple(map(float, v)) for v in poly]
    a = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    ring = np.stack([m * np.cos(a), m * np.sin(a)], axis=1)
    pts = (np.asarray(poly, float)[:, None, :] + ring[None, :, :]).reshape(-1, 2)
    return parts_mod._hull([tuple(p) for p in pts])


def main():
    """!
    @brief Run every part, shape and margin; print the rows and write out/heater_margin.json.
    @return None
    """
    base.OUT.mkdir(exist_ok=True)
    res = {"cell_mm": base.CELL_MM, "h": base.H, "margins": MARGINS, "parts": []}
    cache = {}
    for board, ref, cls in PARTS:
        if board not in cache:
            s = base.session(board)
            place = {p["ref"]: p for p in parts_mod.read_placement(base.DATA / board / "pos.csv")}
            whole = base.problem_of(s) if board == "rp2040" else None
            cache[board] = (s, place, whole)
        s, place, whole = cache[board]
        part = s.part(ref)
        ops = s._openings_of(part)
        shp = base.shapes_of(part, ops, place.get(ref))
        hull = shp["hull"][0][0]
        exposed = parts_mod.shape_polygon(ops, "exposed")
        if whole is not None:
            prob, box = whole
        else:
            cx, cy = np.mean(np.asarray(hull), axis=0)
            bb = s.board().box
            x0 = min(max(cx - base.WINDOW_MM / 2, bb[0]), bb[2] - base.WINDOW_MM)
            y0 = min(max(cy - base.WINDOW_MM / 2, bb[1]), bb[3] - base.WINDOW_MM)
            prob, box = base.problem_of(s, (x0, y0, x0 + base.WINDOW_MM, y0 + base.WINDOW_MM))
        cases = [(f"hull+{m:.1f}", grow(hull, m)) for m in MARGINS] + [(f"exposed+{m:.1f}", grow(exposed, m)) for m in MARGINS]
        cases.append(("envelope", shp["envelope"][0][0]))
        if "ep_pad" in shp:
            cases.append(("ep_pad", shp["ep_pad"][0][0]))
        row = {"board": board, "ref": ref, "class": cls, "package": part.footprint, "runs": {}, "polygons": {},
               "openings_xy": [[list(map(float, v)) for v in o.hull] for o in ops]}
        t0 = time.time()
        with fvm.factor_reuse():
            for name, poly in cases:
                rr = base.run_shape(prob, box, [(poly, 1.0)], hull)
                row["runs"][name] = {"area": base.area(poly), "t_max": rr["t_max"], "t_node": rr["t_node"], "t_mean": rr["t_mean"]}
                row["polygons"][name] = [list(map(float, v)) for v in poly]
        h0 = row["runs"]["hull+0.0"]["t_max"]
        print(f"{board} {ref} ({cls}), {time.time() - t0:.1f} s", flush=True)
        for name, rr in row["runs"].items():
            print(f"   {name:13s} area {rr['area']:7.2f} mm2  t_max {rr['t_max']:7.2f} K ({100 * (rr['t_max'] / h0 - 1):+6.1f} % vs hull)  node {rr['t_node']:7.2f}", flush=True)
        res["parts"].append(row)
    (base.OUT / "heater_margin.json").write_text(json.dumps(res, indent=1))


def table():
    """!
    @brief Print the Markdown table of out/heater_margin.json: per part the hottest rise for each shape and margin, and the change against the hull and against the exposed pad.
    @return None
    """
    res = json.loads((base.OUT / "heater_margin.json").read_text())
    print("| Part | Shape | Area (mm2) | T_max rise (K/W) | vs hull (%) | vs exposed pad (%) |")
    print("| :-- | :-- | --: | --: | --: | --: |")
    for row in res["parts"]:
        h0, e0 = row["runs"]["hull+0.0"]["t_max"], row["runs"]["exposed+0.0"]["t_max"]
        first = True
        for name, rr in row["runs"].items():
            part = f"{row['board']} {row['ref']} ({row['class']})" if first else ""
            first = False
            print(f"| {part} | {name} | {rr['area']:.1f} | {rr['t_max']:.1f} | {100 * (rr['t_max'] / h0 - 1):+.1f} | {100 * (rr['t_max'] / e0 - 1):+.1f} |")


if __name__ == "__main__":
    if "--table" in sys.argv:
        table()
    else:
        main()
