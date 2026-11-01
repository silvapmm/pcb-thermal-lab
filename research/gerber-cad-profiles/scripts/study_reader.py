#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_reader.py
@brief What does the program's Gerber reader do with the files of each tool: layer function, parse, drills, outline, copper area?
@details Question answered (README 4): for every Gerber or drill file of every sample set, (1) the layer function found by
         `pcbthermal.gerber.detect_function` from the name alone and from the name plus the head, against the truth (the X2
         `TF.FileFunction` the tool wrote, else the hand label of `lib/labels.py`); (2) whether `read_layer` / `read_drill_file`
         accept the file or refuse it (and the message); (3) for the files taken as outline, whether `read_outline` finds a closed
         contour; (4) for copper files up to 600 kB, the copper area of the program (`rasterize` at a pixel of max(0.05, side/1500) mm)
         against the independent reader gerbonara + shapely (`research/gerber-import/lib/gerber_geometry.py`).
         Needs the research environment: .venv-research/bin/python research/gerber-cad-profiles/scripts/study_reader.py [--no-area] [--out FILE]
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research", "gerber-import", "lib"))
import cadprofiles as cp  # noqa: E402
import labels  # noqa: E402
import study_markers as sm  # noqa: E402
from pcbthermal import gerber as G  # noqa: E402

AREA_MAX_BYTES = 600_000


def sets():
    """!
    @brief All (set key, truth tool, folder) of the study: the marker-study roots and the held-out sets.
    @return list Tuples.
    """
    out = [(rel, truth, os.path.join(sm.DATA, rel)) for rel, truth, _ in sm.ROOTS]
    hb = os.path.join(sm.DATA, "heldout")
    for d in sorted(os.listdir(hb)):
        out.append(("heldout/" + d, d.split("__")[0], os.path.join(hb, d)))
    return [s for s in out if os.path.isdir(s[2])]


def program_area(layer, w):
    """!
    @brief Copper area of a parsed layer from the program's rasteriser.
    @param layer  Parsed Layer.
    @param w      Window (x0, y0, x1, y1) in mm.
    @return float Area in mm2.
    """
    side = max(w[2] - w[0], w[3] - w[1])
    pix = max(0.05, side / 1500.0)
    win = G.window_of(w, 0.0)
    cov = G.rasterize(layer, win, pix)
    return float(G.coverage_area_mm2(cov, pix))


def main(argv):
    """!
    @brief Run the reader on every sample file and print the per-tool tables.
    @param argv  Command line.
    @return int Exit code.
    """
    do_area = "--no-area" not in argv
    outfile = argv[argv.index("--out") + 1] if "--out" in argv else None
    if do_area:
        import gerber_geometry as gg  # noqa: E402
    rows = []
    t0 = time.time()
    for key, truth, folder in sets():
        for dp, _, fs in os.walk(folder):
            for f in sorted(fs):
                p = os.path.join(dp, f)
                if os.path.splitext(f)[1].lower() in sm.SKIP_EXT or f in ("LICENSE", "README", "SOURCE", "_SOURCE.txt", "listing.json"):
                    continue
                if os.path.getsize(p) == 0:
                    continue
                raw = open(p, "rb").read(cp.HEAD_BYTES)
                head = cp.normalise(raw)
                scope = cp.file_scope(f, head)
                if scope not in ("gerber", "drill"):
                    continue
                rel = os.path.relpath(p, folder)
                tr = labels.x2_truth(head)
                tsrc = "x2"
                if tr is None:
                    tr, tsrc = labels.rule_truth(truth, f), "hand"
                by_name = G.detect_function(f, "")
                by_head = G.detect_function(f, head)
                row = {"set": key, "tool": truth, "file": rel, "scope": scope, "truth": tr, "truth_src": tsrc if tr else None,
                       "name_kind": by_name.kind, "name_side": by_name.side, "head_kind": by_head.kind, "head_side": by_head.side,
                       "head_source": by_head.source}
                # reading
                row["read"], row["msg"] = "ok", ""
                layer = None
                try:
                    if scope == "drill" and not head.lstrip().startswith("%") and "%FS" not in head:
                        d = G.read_drill_file(p)
                        row["holes"] = len(d.holes)
                    else:
                        layer = G.read_layer(p)
                        if by_head.kind == "drill":
                            row["holes"] = len(G.drill_from_gerber(layer).holes) if hasattr(G, "drill_from_gerber") else None
                except Exception as exc:  # the reader refuses with its own message; anything else is a defect to report
                    row["read"] = "refused" if exc.__class__.__name__ in ("UnsupportedFeatureError", "GerberError", "OutlineError") else "ERROR"
                    row["msg"] = ("%s: %s" % (exc.__class__.__name__, exc))[:140]
                # outline
                want_outline = (tr and tr[0] == "outline") or by_head.kind == "outline"
                if want_outline and layer is not None:
                    try:
                        o = G.outline_from_layer(layer)
                        row["outline"] = "ok %.1fx%.1f mm" % (o.bbox[2] - o.bbox[0], o.bbox[3] - o.bbox[1])
                    except Exception as exc:
                        row["outline"] = "fail: %s" % str(exc)[:100]
                # copper area against the independent reader
                if do_area and layer is not None and tr and tr[0] == "copper" and os.path.getsize(p) <= AREA_MAX_BYTES:
                    try:
                        bb = layer.bbox()
                        w = (bb[0], bb[1], bb[2], bb[3])
                        a_prog = program_area(layer, w)
                        geom, _ = gg.load_copper(p)
                        row["area_prog"], row["area_ref"] = a_prog, float(geom.area)
                    except Exception as exc:
                        row["area_err"] = str(exc)[:100]
                rows.append(row)
    print("files examined: %d in %.0f s" % (len(rows), time.time() - t0))
    if outfile:
        os.makedirs(os.path.dirname(outfile), exist_ok=True)
        with open(outfile, "w") as fh:
            json.dump(rows, fh, indent=0)
    report(rows)
    return 0


def same_kind(found, truth):
    """!
    @brief Is the kind found the kind of the truth?  A file of no electrical use (truth "other") is rightly "other" or "unknown".
    @param found  Kind returned by the detector.
    @param truth  Kind of the label.
    @return bool True when they agree.
    """
    if truth == "other":
        return found in ("other", "unknown")
    return found == truth


def report(rows):
    """!
    @brief Print the tables of the study from the collected rows.
    @param rows  List of row dicts.
    @return None
    """
    tools = sorted({r["tool"] for r in rows})
    print("\n| tool | files | judged | kind right (name only) | kind right (name+head) | side right (name+head) | read ok | refused | ERROR |")
    print("| :-- | --: | --: | --: | --: | --: | --: | --: | --: |")
    tot = [0] * 8
    for t in tools:
        rs = [r for r in rows if r["tool"] == t]
        j = [r for r in rs if r["truth"]]
        kn = sum(1 for r in j if same_kind(r["name_kind"], r["truth"][0]))
        kh = sum(1 for r in j if same_kind(r["head_kind"], r["truth"][0]))
        js = [r for r in j if r["truth"][1]]
        sh = sum(1 for r in js if r["head_side"] == r["truth"][1])
        ok = sum(1 for r in rs if r["read"] == "ok")
        rf = sum(1 for r in rs if r["read"] == "refused")
        er = sum(1 for r in rs if r["read"] == "ERROR")
        print("| %s | %d | %d | %d | %d | %d / %d | %d | %d | %d |" % (t, len(rs), len(j), kn, kh, sh, len(js), ok, rf, er))
        for i, v in enumerate((len(rs), len(j), kn, kh, sh, ok, rf, er)):
            tot[i] += v
    print("| all | %d | %d | %d | %d | %d | %d | %d | %d |" % tuple(tot))
    print("\nwrong kinds (name+head), file: truth -> found")
    for r in rows:
        if r["truth"] and not same_kind(r["head_kind"], r["truth"][0]):
            print("  %-60s %s -> %s (%s)" % (r["set"] + "/" + r["file"], r["truth"][0], r["head_kind"], r["head_source"]))
    print("\nwrong sides (name+head)")
    for r in rows:
        if r["truth"] and r["truth"][1] and same_kind(r["head_kind"], r["truth"][0]) and r["head_side"] != r["truth"][1]:
            print("  %-60s %s -> %s" % (r["set"] + "/" + r["file"], r["truth"][1], r["head_side"]))
    print("\nrefused or failed")
    for r in rows:
        if r["read"] != "ok":
            print("  %-60s %s %s" % (r["set"] + "/" + r["file"], r["read"], r["msg"]))
    print("\noutline files")
    for r in rows:
        if "outline" in r and not r["outline"].startswith("ok"):
            print("  %-60s %s" % (r["set"] + "/" + r["file"], r["outline"]))
    print("\ncopper area, program against gerbonara + shapely")
    ar = [r for r in rows if "area_ref" in r]
    if ar:
        rel = [abs(r["area_prog"] - r["area_ref"]) / max(r["area_ref"], 1e-9) for r in ar]
        print("  files compared: %d, within 3 %%: %d, worst %.1f %%, median %.2f %%" % (len(ar), sum(1 for x in rel if x < 0.03), 100 * max(rel),
                                                                                        100 * sorted(rel)[len(rel) // 2]))
        for r, x in zip(ar, rel):
            if x >= 0.03:
                print("  %-60s program %.1f, reference %.1f mm2 (%.1f %%)" % (r["set"] + "/" + r["file"], r["area_prog"], r["area_ref"], 100 * x))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
