#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_heater_shape.py
@brief Which heat-source polygon should an imported part get: does the shape (hull, box, envelope, exposed pad, the openings themselves) move the part temperature by more than the rest of the model error?
@details The program's import path (`ImportSession`: the paste openings, the placement file, `TO.C`, `parts.shape_polygon`) gives the openings of eleven parts of three open boards
         (RP2040 minimal design, ISASTM, CMM2; data/ is git-ignored, `fetch_boards.py`). For each part six shapes carry 1 W on the top layer of the imported copper (faces mapping,
         FVM at 0.5 mm, fixed h = 10 W/m2K on both faces and the edge, so the rise is linear in the power):
           hull     convex hull of the paste openings (the program's default, `shape_polygon(.., "hull")`)
           box      bounding box of the openings (`"box"`)
           envelope pad envelope from the footprint name (`parts.part_envelope_polygon`, the matching rule's rectangle; never a heat source in the program)
           largest  the largest opening alone (`"largest"`)
           ep       hull of the openings whose area is at least half of the largest: the exposed pad when it is split into windows (a candidate rule, not in the program)
           ep_pad   the exposed pad as a square of the size in the footprint name (`EP2.6x2.6mm`), centred on those windows (the paste windows are inset in the copper pad); EP parts only
           openings every opening is its own heater, power in proportion to its area (the pads as the entry of the heat)
         Read-outs, as the program reports them: `t_max` the hottest face temperature under the heater(s) (the board point of Tj = t_max + theta P), `t_node` the same without the face term of bare laminate, `t_mean` the power-weighted mean under the
         heater(s), `t_hull` the hottest face temperature under the hull (one common area for every shape), and the board mean. The RP2040 board is run whole (52 x 51 mm, two layers); ISASTM
         and CMM2 (four layers, 102 x 102 and 130 x 102 mm) as 40 mm windows around the part (the cut edges carry the edge coefficient; the same window for every shape of a part).
         Second part: the JEDEC 2s2p exposed-pad QFN of the power-calculator validation (TPS7A47, RthJA 32.5 K/W, theta_JC(bot) 1.7 K/W, read) with the heater on the exposed pad (3.15 mm, the
         validated row), on the body (5 mm) and on the body with the leads (5.8 mm), cell 1 mm (the memory rule of this study; 0.5 mm in the calculator README).
         Run (from the repository root): .venv/bin/python research/gerber-real-boards/scripts/study_heater_shape.py   (about 1 to 2 minutes, peak below 1 GB); writes out/heater_shape.json; `--table` prints the Markdown table of the last run.
"""

import json
import re
import sys
import time
from pathlib import Path

import _bootstrap  # noqa: F401  (paths of this investigation and the repository root)
import numpy as np

from pcbthermal import analysis, api, fvm
from pcbthermal import copper as copper_mod
from pcbthermal.gerber import parts as parts_mod
from pcbthermal.gerber.outline import Outline, OutlinePolygon
from pcbthermal.gui.import_session import ImportSession

ROOT = Path(__file__).resolve().parents[1]
DATA, OUT = ROOT / "data", ROOT / "out"
CELL_MM = 0.5
H = 10.0
WINDOW_MM = 40.0
SHAPES = ("hull", "box", "envelope", "largest", "ep", "ep_pad", "openings")
## Side of the exposed pad (mm) of a footprint name without the `EP<a>x<b>mm` field: the RP2040 QFN-56 (3.2 mm, from memory of the RP2040 datasheet, not opened in this study)
EP_SIDE_FALLBACK = {"RP2040-QFN-56": 3.2}

## (board, designator, class) of the parts compared
PARTS = (("rp2040", "U3", "QFN-56, exposed pad in 4 windows (RP2040)"),
         ("rp2040", "U1", "SOT-223 LDO, tab (NCP1117)"),
         ("rp2040", "U2", "SOIC-8 (flash)"),
         ("rp2040", "Y1", "HC49 crystal, two pads"),
         ("rp2040", "R2", "0402 resistor"),
         ("rp2040", "C1", "0805 capacitor"),
         ("rp2040", "J3", "USB micro-B connector"),
         ("isastm", "U5", "SOT-223 LDO, tab (AMS1117)"),
         ("isastm", "U15", "QFN-24, exposed pad 2.6 mm in 4 windows"),
         ("isastm", "U14", "SOT-23-6"),
         ("cmm2", "U4", "QFN-28, exposed pad 3.35 mm in 9 windows"))


def session(board):
    """!
    @brief The import session of a downloaded board (the JLC placement file is switched off where two exist).
    @param board Board key (folder of data/).
    @return ImportSession with the board loaded and the parts built.
    """
    s = ImportSession()
    s.set_files(str(DATA / board))
    for i, f in enumerate(s.files):
        if f.name == "cpl_jlc.csv":
            s.set_use(i, False)
    s.cell_mm = CELL_MM
    s.load()
    return s


def problem_of(s, box=None):
    """!
    @brief The Problem of the imported copper of a board or of a window of it, with the typical stack-up and fixed coefficients, no heater.
    @param s ImportSession.
    @param box None for the whole board, or (x0, y0, x1, y1) in the Gerber frame (mm) of a rectangular window.
    @return tuple (Problem, box of the problem in the Gerber frame).
    """
    cl = s._copper_layers()
    outline = s._outline
    if box is not None:
        rect = np.array([[box[0], box[1]], [box[2], box[1]], [box[2], box[3]], [box[0], box[3]]], float)
        outline = Outline([OutlinePolygon(rect, [])], tuple(box), (box[2] - box[0]) * (box[3] - box[1]))
    ib = copper_mod.import_copper([lay for _, lay in cl], outline, s._drills(), pixel_mm=s.effective_pixel(), cell_mm=CELL_MM, mapping="faces",
                                  names=[f.name for f, _ in cl])
    p = ib.to_problem(thickness_mm=1.6, name=s.name)
    p.board.apply_template()
    b = p.board
    b.h_mode, b.h_top, b.h_bottom, b.h_side = "manual", H, H, H
    return p, ib.box_mm


def ep_group(ops):
    """!
    @brief The candidate exposed-pad group: the openings whose area is at least half of the largest one.
    @param ops Openings of one part.
    @return list of Opening (all of them when the part has no dominant opening).
    """
    amax = max(o.area for o in ops)
    return [o for o in ops if o.area >= 0.5 * amax]


def shapes_of(part, ops, place):
    """!
    @brief The six heat-source shapes of a part in the Gerber frame.
    @param part ImportPart.
    @param ops Openings of the part.
    @param place Placement dict of the part (package, x, y, rot, side), or None.
    @return dict name -> list of (polygon, share of the power).
    """
    out = {"hull": [(parts_mod.shape_polygon(ops, "hull"), 1.0)], "box": [(parts_mod.shape_polygon(ops, "box"), 1.0)],
           "largest": [(parts_mod.shape_polygon(ops, "largest"), 1.0)], "ep": [(parts_mod.shape_polygon(ep_group(ops), "hull"), 1.0)]}
    if place is not None:
        out["envelope"] = [([tuple(v) for v in parts_mod.part_envelope_polygon(place)], 1.0)]
    # The exposed pad as the copper pad of the footprint name (the paste windows are inset in it), centred on the windows; only for a part with a dominant group
    m = re.search(r"EP(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)mm", part.footprint)
    side = (float(m.group(1)), float(m.group(2))) if m else (EP_SIDE_FALLBACK[part.footprint],) * 2 if part.footprint in EP_SIDE_FALLBACK else None
    grp = ep_group(ops)
    if side is not None and len(grp) < len(ops):
        cx, cy = np.mean([[o.x, o.y] for o in grp], axis=0)
        out["ep_pad"] = [([(cx - side[0] / 2, cy - side[1] / 2), (cx + side[0] / 2, cy - side[1] / 2), (cx + side[0] / 2, cy + side[1] / 2), (cx - side[0] / 2, cy + side[1] / 2)], 1.0)]
    tot = sum(o.area for o in ops)
    out["openings"] = [(list(o.hull), o.area / tot) for o in ops]
    return out


def area(poly):
    """!
    @brief Area of a polygon.
    @param poly List of (x, y) in mm.
    @return float mm2.
    """
    a = np.asarray(poly, float)
    return 0.5 * abs(float(np.dot(a[:, 0], np.roll(a[:, 1], -1)) - np.dot(a[:, 1], np.roll(a[:, 0], -1))))


def run_shape(prob, box, pieces, hull):
    """!
    @brief Run the FVM with one shape of a part carrying 1 W and read the part as the program does.
    @param prob Problem without heaters (copied heaters are cleared).
    @param box Box of the problem in the Gerber frame (mm).
    @param pieces List of (polygon in the Gerber frame, share of the power).
    @param hull Hull of the openings in the Gerber frame (the common read-out area).
    @return dict t_max, t_mean, t_hull (K above ambient), board_mean (K), seconds.
    """
    prob.heaters.clear()
    for k, (poly, share) in enumerate(pieces):
        prob.add_heater(1, share, polygon=[[x - box[0], y - box[1]] for x, y in poly], name=f"h{k}")
    t0 = time.time()
    sim = api.simulate(prob, api.SolverOptions(models=("fvm",), cell_mm=CELL_MM))
    r = sim.results["fvm"]
    amb = r.ambient
    rows = analysis.heater_stats(r, prob)
    t_max = max(row["t_max"] for row in rows) - amb
    t_mean = sum(row["t_mean"] * row["power_w"] for row in rows) / sum(row["power_w"] for row in rows) - amb
    hpoly = np.array([[x - box[0], y - box[1]] for x, y in hull]) * 1e-3
    _, t_hull, _ = analysis._footprint_stats(r, hpoly, 0, prob.board.outline, face=True)
    # The same hottest point without the face term (the node value): the face term is the drop of the half layer of laminate where a heater covers bare laminate
    t_node = max(analysis._footprint_stats(r, np.asarray(h.polygon), h.layer, prob.board.outline, face=False)[1] for h in prob.heaters) - amb
    return {"t_max": t_max, "t_node": t_node, "t_mean": t_mean, "t_hull": t_hull - amb, "board_mean": r.t_mean - amb, "seconds": time.time() - t0}


def jedec_rows():
    """!
    @brief The JEDEC 2s2p exposed-pad QFN of the power-calculator validation with the heater on the exposed pad, the body and the body with leads (cell 1 mm, computed h at 1 W).
    @return list of dicts shape, side_mm, rth_ja (K/W: junction = hottest board point under the heater + 1.7 K/W x 1 W), against the datasheet's 32.5 K/W.
    """
    sys.path.insert(0, str(ROOT.parent / "power-calculator" / "scripts"))
    import calculator_validation as cv
    out = []
    for name, side in (("exposed pad", 3.15), ("body", 5.0), ("body with leads", 5.8)):
        p = cv.jedec_2s2p_board()
        h = p.heaters[0]
        cx, cy = 57.15, 38.1
        p.heaters.clear()
        p.add_heater(1, 1.0, rect=(cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2), name="U1", theta=h.theta)
        sim = api.simulate(p, api.SolverOptions(models=("fvm",), cell_mm=1.0))
        r = sim.results["fvm"]
        row = analysis.heater_stats(r, p)[0]
        node = analysis._footprint_stats(r, np.asarray(p.heaters[0].polygon), 0, None, face=False)[1]
        out.append({"shape": name, "side_mm": side, "rth_ja": row["t_junction"] - r.ambient, "rth_ja_node": node + 1.7 - r.ambient, "datasheet": 32.5})
        print(f"JEDEC 2s2p, heater on the {name} ({side} mm): RthJA {out[-1]['rth_ja']:.1f} K/W (node value without the face term {out[-1]['rth_ja_node']:.1f}; datasheet 32.5)", flush=True)
    return out


LABELS = {"hull": "(a) hull", "box": "(b) box", "envelope": "(c) envelope", "largest": "(d) largest opening", "ep": "(d') exposed-pad windows", "ep_pad": "(d'') exposed pad from the name", "openings": "(e) openings by area"}


def table():
    """!
    @brief Print the Markdown table of out/heater_shape.json (the table of the opinion document): per part and shape the area, the power density at 1 W, the hottest and the mean rise
           under the heater, the part-to-board resistance and the difference to the hull.
    @return None
    """
    res = json.loads((OUT / "heater_shape.json").read_text())
    print("| Part | Shape | Area (mm2) | Power density at 1 W (W/cm2) | T_max rise (K) | Mean rise under the heater (K) | R part-to-board (K/W) | vs hull (K) | vs hull (%) |")
    print("| :-- | :-- | --: | --: | --: | --: | --: | --: | --: |")
    for row in res["parts"]:
        h0 = row["runs"]["hull"]["t_max"]
        for name in SHAPES:
            if name not in row["runs"]:
                continue
            rr, a = row["runs"][name], row["areas"][name]
            part = f"{row['board']} {row['ref']} ({row['class']})" if name == "hull" else ""
            print(f"| {part} | {LABELS[name]} | {a:.2f} | {100.0 / a:.1f} | {rr['t_max']:.1f} | {rr['t_mean']:.1f} | {rr['t_max']:.1f} | {rr['t_max'] - h0:+.1f} | {100 * (rr['t_max'] / h0 - 1):+.1f} |")


def main():
    """!
    @brief Run every part and shape, print the table and write out/heater_shape.json.
    @return None
    """
    OUT.mkdir(exist_ok=True)
    res = {"cell_mm": CELL_MM, "h": H, "window_mm": WINDOW_MM, "parts": [], "jedec": None}
    cache = {}
    for board, ref, cls in PARTS:
        if board not in cache:
            s = session(board)
            place = {p["ref"]: p for p in parts_mod.read_placement(DATA / board / "pos.csv")}
            whole = problem_of(s) if board == "rp2040" else None
            cache[board] = (s, place, whole)
        s, place, whole = cache[board]
        part = s.part(ref)
        ops = s._openings_of(part)
        shp = shapes_of(part, ops, place.get(ref))
        hull = shp["hull"][0][0]
        if whole is not None:
            prob, box = whole
        else:
            cx, cy = np.mean(np.asarray(hull), axis=0)
            bb = s.board().box
            x0 = min(max(cx - WINDOW_MM / 2, bb[0]), bb[2] - WINDOW_MM)
            y0 = min(max(cy - WINDOW_MM / 2, bb[1]), bb[3] - WINDOW_MM)
            prob, box = problem_of(s, (x0, y0, x0 + WINDOW_MM, y0 + WINDOW_MM))
        row = {"board": board, "ref": ref, "class": cls, "package": part.footprint, "n_openings": len(ops), "paste_mm2": sum(o.area for o in ops),
               "n_ep": len(ep_group(ops)), "ep_paste_mm2": sum(o.area for o in ep_group(ops)), "areas": {}, "runs": {}, "polygons": {},
               "box_mm": list(map(float, box)), "licence_note": "BSD-3-Clause, may be drawn" if board == "rp2040" else "GPL-3.0 board: out/ only, not drawn in committed figures"}
        with fvm.factor_reuse():
            for name in SHAPES:
                if name not in shp:
                    continue
                row["areas"][name] = sum(area(pg) for pg, _ in shp[name])
                row["runs"][name] = run_shape(prob, box, shp[name], hull)
                row["polygons"][name] = [[list(map(float, v)) for v in pg] for pg, _ in shp[name]]
        row["openings_xy"] = [[list(map(float, v)) for v in o.hull] for o in ops]
        h0 = row["runs"]["hull"]["t_max"]
        print(f"{board} {ref} ({cls}): {len(ops)} openings, paste {row['paste_mm2']:.1f} mm2, ep group {row['n_ep']} ({row['ep_paste_mm2']:.1f} mm2 of paste); board mean {row['runs']['hull']['board_mean']:.1f} K", flush=True)
        for name, rr in row["runs"].items():
            print(f"   {name:9s} area {row['areas'][name]:7.2f} mm2  t_max {rr['t_max']:7.2f} K ({100 * (rr['t_max'] / h0 - 1):+6.1f} %)  node {rr['t_node']:7.2f}  t_mean {rr['t_mean']:7.2f}  t_hull {rr['t_hull']:7.2f}"
                  f"  local {rr['t_max'] - rr['board_mean']:6.2f} K  ({rr['seconds']:.1f} s)", flush=True)
        res["parts"].append(row)
    res["jedec"] = jedec_rows()
    (OUT / "heater_shape.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    if "--table" in sys.argv:
        table()                                        # only print the table of the last run
    else:
        main()
