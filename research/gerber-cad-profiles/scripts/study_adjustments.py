#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_adjustments.py
@brief Measure the per-tool adjustments that make the refused or failed files of `study_reader.py` readable.
@details Question answered (README 5): for each refusal or failure of the program's reader on a real tool output, does a small,
         tool-specific adjustment fix it, and does the result agree with an independent check?
         A. Outline: the files taken as outline that the program refuses ("not a closed contour"): the effect of the join
            tolerance and of removing duplicate and dangling segments (`lib/outline_prune.py`); the result is judged by the
            bounding box of the loop against the bounding box of the copper of the same set.
         B. Xpedition / Mentor NC drill: `G93X0Y0` (a zero origin shift) in every .ncd file; with that line removed, the holes
            read must lie inside the board outline of the same set and their count must equal the number of drill hits of the tool lists.
         C. Upverter: `M71,TZ` in the drill header and the macro names with a hyphen in the Gerber files; with both rewritten in memory,
            the copper area against gerbonara + shapely.
         Run: .venv-research/bin/python research/gerber-cad-profiles/scripts/study_adjustments.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research", "gerber-import", "lib"))
import numpy as np  # noqa: E402
import outline_prune as op  # noqa: E402
import study_markers as sm  # noqa: E402
from pcbthermal import gerber as G  # noqa: E402

DATA = sm.DATA


def bbox_of_set(folder, exclude=()):
    """!
    @brief Union bounding box of the copper-like Gerber files of a folder (every file that parses and is not excluded).
    @param folder   Folder.
    @param exclude  File names to skip.
    @return tuple (x0, y0, x1, y1) or None.
    """
    best = None
    for f in os.listdir(folder):
        if f in exclude or not re.search(r"(?i)(gtl|gbl|top|bottom|etchlayer|cu\.gbr|_cu\.gbr|layer1)", f):
            continue
        try:
            b = G.read_layer(os.path.join(folder, f)).bbox()
        except Exception:
            continue
        if b is None:
            continue
        best = b if best is None else (min(best[0], b[0]), min(best[1], b[1]), max(best[2], b[2]), max(best[3], b[3]))
    return best


def study_outline():
    """!
    @brief Part A: outlines refused by the program, with tolerance and pruning.
    @return None
    """
    print("### A. outline files the program refuses\n")
    print("| file | program at 0.01 mm | at 0.1 mm | after pruning (0.01 mm): loops, duplicates, dangling | largest loop / copper box |")
    print("| :-- | :-- | :-- | :-- | :-- |")
    cand = []
    for dp, _, fs in os.walk(DATA):
        for f in fs:
            if re.search(r"(?i)(\.gko$|\.gm1$|outline|edge.?cuts|boardoutline|profile)", f) and not f.endswith((".svg", ".png", ".json", ".txt", ".zip", ".pdf")):
                cand.append(os.path.join(dp, f))
    shown = 0
    for p in sorted(cand):
        try:
            lay = G.read_layer(p)
        except Exception:
            continue
        try:
            G.outline_from_layer(lay, 0.01)
            continue                                            # accepted: not part of this table
        except Exception as e0:
            r0 = "fail"
        try:
            G.outline_from_layer(lay, 0.1)
            r1 = "closes"
        except Exception:
            r1 = "fail"
        rel = os.path.relpath(p, DATA)
        try:
            loops, dup, dang = op.outline_pruned(lay, 0.01)
            areas = [abs(G.outline.signed_area(l)) for l in loops]
            big = loops[int(np.argmax(areas))]
            lb = (big[:, 0].min(), big[:, 1].min(), big[:, 0].max(), big[:, 1].max())
            cb = bbox_of_set(os.path.dirname(p), exclude=(os.path.basename(p),))
            ratio = ""
            if cb:
                ratio = "%.2f x %.2f" % ((lb[2] - lb[0]) / max(cb[2] - cb[0], 1e-9), (lb[3] - lb[1]) / max(cb[3] - cb[1], 1e-9))
            res = "%d, %d, %d" % (len(loops), dup, dang)
        except Exception as e2:
            res, ratio = "fails: %s" % str(e2)[:50], ""
        print("| %s | %s | %s | %s | %s |" % (rel, r0, r1, res, ratio))
        shown += 1
    print("\nfiles listed: %d (the other outline files are accepted at 0.01 mm)\n" % shown)


def study_xpedition_drill():
    """!
    @brief Part B: Xpedition NC drill files with the G93X0Y0 line removed.
    @return None
    """
    print("### B. Xpedition / Mentor NC drill, `G93X0Y0` removed in memory\n")
    print("| file | tools | holes read | holes outside the board box |")
    print("| :-- | --: | --: | --: |")
    folders = [("siemens", "80101_0125_F200_ContourPlated.ncd"), ("siemens-2/NCDrill", None), ("xpedition/bouled/NCDrill", None),
               ("xpedition/spirose/NCDrill", None), ("xpedition/hw0004", None), ("heldout/xpedition__swarm/NCDrill", None),
               ("heldout/xpedition__banshee", None)]
    for fol, _ in folders:
        d = os.path.join(DATA, fol)
        sibling = os.path.join(DATA, fol.split("/NCDrill")[0])
        outline_box = None
        for dp, _, fs in os.walk(sibling):
            for f in fs:
                if re.search(r"(?i)boardoutl+ine|outline\.gdo", f):
                    try:
                        outline_box = G.outline_from_layer(G.read_layer(os.path.join(dp, f)), 0.01).bbox
                    except Exception:
                        pass
        if outline_box is None:
            outline_box = bbox_of_set(sibling)
        for f in sorted(os.listdir(d)):
            if not f.endswith(".ncd"):
                continue
            text = open(os.path.join(d, f), encoding="latin-1").read()
            fixed = re.sub(r"(?m)^G93X0Y0\s*$", "", text)
            try:
                dr = G.read_drill(fixed, f)
            except Exception as e:
                print("| %s/%s | | still refused: %s | |" % (fol, f, str(e)[:60]))
                continue
            out = "n/a"
            if outline_box is not None and dr.holes:
                m = 0.5
                out = str(sum(1 for h in dr.holes if not (outline_box[0] - m <= h.x <= outline_box[2] + m and outline_box[1] - m <= h.y <= outline_box[3] + m)))
            print("| %s/%s | %d | %d | %s |" % (fol, f, len(dr.tools) if hasattr(dr, "tools") else -1, len(dr.holes), out))
    print()


def study_upverter():
    """!
    @brief Part C: Upverter files with the drill header and the macro names rewritten in memory.
    @return None
    """
    print("### C. Upverter, header and macro names rewritten in memory\n")
    import gerber_geometry as gg
    folder = os.path.join(DATA, "upverter")
    text = open(os.path.join(folder, "design_export.drl"), encoding="latin-1").read().replace("M71,TZ", "METRIC,TZ")
    dr = G.read_drill(text, "design_export.drl")
    print("drill: %d holes read after `M71,TZ` -> `METRIC,TZ`\n" % len(dr.holes))
    print("| file | program after renaming the macros | gerbonara + shapely | difference |")
    print("| :-- | --: | --: | --: |")
    for f in sorted(os.listdir(folder)):
        if not re.search(r"\.(gtl|gbl|gts|gbs|gto|gbo|gtp|gbp)$", f):
            continue
        raw = open(os.path.join(folder, f), encoding="latin-1").read()
        names = set(re.findall(r"%AM([^*]+)\*", raw))
        fixed = raw
        for n in sorted(names, key=len, reverse=True):
            fixed = fixed.replace(n, re.sub(r"[^A-Za-z0-9_.$]", "_", n))
        try:
            lay = G.parse_layer(fixed, f)
            bb = lay.bbox()
            if bb is None:
                # review: the paste file holds no object at all (`M02` only); the earlier run printed a TypeError of this script here
                print("| %s | empty layer (no object): read | | |" % f)
                continue
            side = max(bb[2] - bb[0], bb[3] - bb[1])
            pix = max(0.05, side / 1500.0)
            cov = G.rasterize(lay, G.window_of(bb, 0.0), pix)
            a = float(G.coverage_area_mm2(cov, pix))
            ref = float(gg.load_copper(os.path.join(folder, f))[0].area)
            print("| %s | %.2f | %.2f | %.2f %% |" % (f, a, ref, 100 * abs(a - ref) / max(ref, 1e-9)))
        except Exception as e:
            print("| %s | fails: %s | | |" % (f, str(e)[:70]))
    print()


def main():
    """!
    @brief Run the three parts.
    @return int Exit code.
    """
    study_outline()
    study_xpedition_drill()
    study_upverter()
    return 0


if __name__ == "__main__":
    sys.exit(main())
