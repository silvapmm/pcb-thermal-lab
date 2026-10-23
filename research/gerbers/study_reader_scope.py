"""!
@file study_reader_scope.py
@brief Can the independent reader read any copper layer and any drill file? Only copper and drills matter here (silkscreen, mask, paste and assembly layers are not needed).
@details Uses the test resources of gerbonara downloaded by study_reader_conformance.py (data/conformance/, git-ignored) and the downloaded boards.
         Copper: every file that `classify` calls copper (X2 file function or name) is read and drawn; reported: files read, files refused (and why), agreement of the copper area with
         gerbonara + shapely, and how many carry net names (X2 attribute TO.N).
         Drills: every Excellon-like file (extensions .drl .xln .cnc .drill .txt, or a name containing drill) is read with the independent reader and with gerbonara; reported: files read by
         each, the hole counts, the difference of the positions and diameters where both read.
         Run: python study_reader_scope.py (needs study_reader_conformance.py to have run once; about 3 minutes).
"""

import collections
import json
import re
import urllib.parse
import urllib.request
import warnings
from pathlib import Path

import numpy as np

warnings.simplefilter("ignore")

import gerber_geometry as gg
import native_gerber as ng
import study_reader_conformance as sc

DRILL_EXT = {".drl", ".xln", ".cnc", ".drill", ".txt", ".exc", ".ncd", ".tap", ".nc", ""}


def download_drills():
    """!
    @brief Download the Excellon-like files of the gerbonara test resources (once).
    @return List of local paths.
    """
    listing = json.loads((sc.DEST / "listing.json").read_text())
    out = []
    for p in listing:
        low = p.lower()
        name = Path(p).name.lower()
        if "drill" not in low and Path(p).suffix.lower() not in (".drl", ".xln", ".cnc", ".exc", ".ncd"):
            continue
        if Path(p).suffix.lower() in (".log", ".rou", ".pdf", ".png", ".svg", ".zip", ".py", ".md", ".json", ".ini") or "param" in name or "license" in name or "readme" in name:
            continue
        local = sc.DEST / ("drill__" + p.replace("tests/resources/", "").replace("/", "__"))
        if not local.exists():
            try:
                with urllib.request.urlopen(sc.RAW + urllib.parse.quote(p), timeout=60) as r:
                    data = r.read(sc.MAX_BYTES + 1)
            except Exception:
                continue
            if len(data) > sc.MAX_BYTES:
                continue
            local.write_bytes(data)
        out.append(local)
    return out


def is_excellon(text):
    """!
    @brief Does the text look like an Excellon drill file (tool table or M48 header and tool coordinates)?
    @param text File content.
    @return True or False.
    """
    return bool(re.search(r"^M48", text, re.M) or (re.search(r"^T\d+C[\d.]+", text, re.M) and re.search(r"^X-?[\d.]+Y-?[\d.]+", text, re.M)))


def copper_scope():
    """!
    @brief Read every copper layer of the test resources and the downloaded boards.
    @return None (prints).
    """
    files = [f for f in sorted(sc.DEST.glob("*")) if f.name != "listing.json" and not f.name.startswith("drill__")]
    files += [f for d in sorted(sc.DEST.parent.iterdir()) if d.is_dir() and d.name != "conformance" for f in d.glob("*.gbr")]
    nread, refused, reasons, withnets, agree, diffs = 0, [], collections.Counter(), 0, 0, []
    ncopper = 0
    for f in files:
        try:
            role = ng.classify(f)[0]
        except Exception:
            continue
        if role != "copper":
            continue
        text = f.read_text(errors="replace")
        if "%FS" not in text:
            continue
        ncopper += 1
        try:
            layer = ng.Layer(text)
            bb = layer.bbox()
            if bb is None:
                continue
            w, h = bb[2] - bb[0] + 0.4, bb[3] - bb[1] + 0.4
            thin = [min(v for v in ap.p[:2] if v > 0) for ap in layer.apertures.values() if ap.kind in "CRO" and any(v > 0 for v in ap.p[:2])]
            pix = max(max(w, h) / 2000, min(0.2, max(0.02, min(thin) / 2)) if thin else 0.2)
            cv = ng.Canvas(bb[0] - 0.2, bb[3] + 0.2, w, h, pix)
            layer.draw(cv)
        except NotImplementedError as e:
            refused.append(f.name)
            reasons[str(e).split(" (")[0][:50]] += 1
            continue
        except Exception as e:
            refused.append(f.name)
            reasons["error: " + type(e).__name__] += 1
            continue
        nread += 1
        withnets += bool(layer.net_names())
        try:
            geom, _ = gg.load_copper(f)
            ref = gg.sample_mask(geom, bb[0] - 0.2, bb[3] + 0.2, cv.mask.shape[1] * pix, cv.mask.shape[0] * pix, pix) > 0.5
        except Exception:
            continue
        a, b = cv.mask.sum(), ref.sum()
        if b:
            diffs.append(100 * (a / b - 1))
    d = np.abs(np.array(diffs))
    print(f"COPPER layers found by the classifier: {ncopper}; drawn by the independent reader: {nread}; refused: {len(refused)} {dict(reasons)}")
    print(f"  with net names (TO.N): {withnets}; compared with gerbonara: {len(diffs)}, within 3 % of the area: {(d < 3).sum()}, median |difference| {np.median(d):.2f} %, worst {d.max():.1f} %")
    if refused:
        print("  refused:", ", ".join(refused[:15]))


def drill_scope():
    """!
    @brief Read every Excellon-like file with both readers and compare the holes.
    @return None (prints).
    """
    files = download_drills()
    rows, nat_fail, gb_fail, n = [], [], [], 0
    for f in files:
        text = f.read_text(errors="replace")
        if not is_excellon(text):
            continue
        n += 1
        try:
            mine = ng.read_drill(f)
        except Exception as e:
            nat_fail.append((f.name, type(e).__name__))
            mine = None
        try:
            ref = gg.drill_holes(f)
        except Exception as e:
            gb_fail.append(f.name)
            ref = None
        if mine is None or ref is None:
            continue
        key = lambda h: (round(h[0], 2), round(h[1], 2), round(h[2], 3))
        a, b = sorted(key(h) for h in mine), sorted(key(h) for h in ref)
        rows.append((f.name, len(mine), len(ref), a == b))
    print(f"\nDRILL files that look like Excellon: {n}")
    print(f"  read by the independent reader: {n - len(nat_fail)}; failed: {len(nat_fail)} {nat_fail[:6]}")
    print(f"  read by gerbonara: {n - len(gb_fail)}; failed: {len(gb_fail)} {gb_fail[:8]}")
    same = [r for r in rows if r[3]]
    print(f"  read by both: {len(rows)}; identical holes (positions to 0.01 mm, diameters to 1 um): {len(same)}; same count but different list: {len([r for r in rows if not r[3] and r[1] == r[2]])}; different count: {len([r for r in rows if r[1] != r[2]])}")
    for r in rows:
        if not r[3]:
            print(f"    differs: {r[0][:70]:70s} mine {r[1]:5d}  gerbonara {r[2]:5d}")


def main():
    """!
    @brief Run the copper and the drill scope studies.
    @return None.
    """
    copper_scope()
    drill_scope()


if __name__ == "__main__":
    main()
