#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_reader_conformance.py
@brief The independent reader against gerbonara on the test files that gerbonara itself is tested with (many CAD tools, and small files that each test one feature).
@details The test resources of gerbonara (https://gitlab.com/gerbolyze/gerbonara, tests/resources) are downloaded once into data/conformance/ (git-ignored; the files have their own licences).
         For every Gerber file (drill files are skipped) both readers draw the whole file at 0.2 mm pixels on its own bounding box; reported: files read by each reader, the ones the
         independent reader refuses (and why), and for the files both read the difference of the copper area and the share of pixels that differ. A file is "agreeing" when the areas differ by less than 3 %.
         Run: .venv/bin/python research/gerber-import/scripts/study_reader_conformance.py (from the repository root) (about 5 minutes; needs gerbonara and shapely and network access for the download).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-import in order)

import collections
import json
import re
import time
import urllib.parse
import urllib.request
import warnings
from pathlib import Path

import numpy as np

warnings.simplefilter("ignore")

import gerber_geometry as gg
import native_gerber as ng

API = "https://gitlab.com/api/v4/projects/gerbolyze%2Fgerbonara/repository/tree?path=tests/resources&recursive=true&per_page=100&page={}"
RAW = "https://gitlab.com/gerbolyze/gerbonara/-/raw/main/"
from paths import DATA

DEST = DATA / "conformance"
GERBER_EXT = {".gbr", ".ger", ".gtl", ".gbl", ".gto", ".gbo", ".gts", ".gbs", ".gtp", ".gbp", ".gko", ".gm1", ".art", ".pho", ".gdo", ".cmp", ".sol", ".g0", ".g1", ".g2", ".g3", ".g4", ".gml", ".ger"}
SKIP_WORDS = ("drill", "drl", "ncd", "xln", "exc", "syntax_error", "ipc", ".svg", ".png", ".zip", ".tgz", ".txt", ".cfg", ".pdf")
MAX_BYTES = 3_000_000


def download():
    """!
    @brief Download the Gerber-like test files of gerbonara (once).
    @return List of local paths.
    """
    DEST.mkdir(parents=True, exist_ok=True)
    listing = DEST / "listing.json"
    if not listing.exists():
        paths = []
        for page in range(1, 8):
            with urllib.request.urlopen(API.format(page), timeout=60) as r:
                paths += [i["path"] for i in json.load(r) if i["type"] == "blob"]
        listing.write_text(json.dumps(paths))
    out = []
    for p in json.loads(listing.read_text()):
        low = p.lower()
        if Path(p).suffix.lower() not in GERBER_EXT or any(w in low for w in SKIP_WORDS):
            continue
        local = DEST / p.replace("tests/resources/", "").replace("/", "__")
        if not local.exists():
            try:
                with urllib.request.urlopen(RAW + urllib.parse.quote(p), timeout=60) as r:
                    data = r.read(MAX_BYTES + 1)
            except Exception:
                continue
            if len(data) > MAX_BYTES:
                continue
            local.write_bytes(data)
        out.append(local)
    return out


def main():
    """!
    @brief Compare both readers on every downloaded file and print the summary.
    @return None.
    """
    files = download()
    rows, refused, reasons, gerbonara_failed, subpixel = [], [], collections.Counter(), [], []
    t_nat = t_gb = 0.0
    for f in files:
        text = f.read_text(errors="replace")
        if "%FS" not in text and "FSLA" not in text and "%MO" not in text:
            continue                                                       # not an RS-274X file (old RS-274D or something else)
        try:
            t = time.time()
            layer = ng.Layer(text)
            bb = layer.bbox()
            if bb is None or bb[2] - bb[0] < 0.1 or bb[3] - bb[1] < 0.1:
                continue
            w, h = bb[2] - bb[0] + 0.4, bb[3] - bb[1] + 0.4
            thin = [min(v for v in ap.p[:2] if v > 0) for ap in layer.apertures.values() if ap.kind in "CRO" and any(v > 0 for v in ap.p[:2])]
            # Pixel: 2 pixels across the thinnest line or pad, between 0.02 mm and 0.2 mm, at most 2000 pixels on the long side
            pix = max(max(w, h) / 2000, min(0.2, max(0.02, min(thin) / 2)) if thin else 0.2)
            cv = ng.Canvas(bb[0] - 0.2, bb[3] + 0.2, w, h, pix)
            layer.draw(cv)
            native = cv.mask
            t_nat += time.time() - t
        except NotImplementedError as e:
            refused.append(f.name)
            reasons[str(e).split(" (")[0][:50]] += 1
            continue
        except Exception as e:
            refused.append(f.name)
            reasons["error: " + type(e).__name__] += 1
            continue
        try:
            t = time.time()
            geom, _ = gg.load_copper(f)
            ref = gg.sample_mask(geom, bb[0] - 0.2, bb[3] + 0.2, native.shape[1] * pix, native.shape[0] * pix, pix) > 0.5
            t_gb += time.time() - t
        except Exception:
            gerbonara_failed.append(f.name)
            continue
        n = min(native.shape[0], ref.shape[0]), min(native.shape[1], ref.shape[1])
        a, b = native[:n[0], :n[1]], ref[:n[0], :n[1]]
        if thin and min(thin) < 1.5 * pix:                                    # features thinner than 1.5 pixels at the finest pixel allowed: both readers sample them differently
            subpixel.append(f.name)
            continue
        rows.append((f.name, 100 * (a.sum() / max(b.sum(), 1) - 1) if b.sum() else float("nan"), 100 * (a ^ b).sum() / max((a | b).sum(), 1)))
    ok = [r for r in rows if r[1] == r[1]]
    agree = [r for r in ok if abs(r[1]) < 3.0]
    print(f"{len(files)} Gerber-like files downloaded; RS-274X files drawn by the independent reader and read by gerbonara: {len(rows)}")
    print(f"  agreeing (copper area within 3 %): {len(agree)} of {len(ok)}; median |area difference| {np.median([abs(r[1]) for r in ok]):.2f} %; median pixels that differ {np.median([r[2] for r in ok]):.1f} %")
    print(f"  refused by the independent reader: {len(refused)}  {dict(reasons)}")
    print(f"  left out because a feature is thinner than 1.5 pixels of the comparison: {len(subpixel)}")
    print(f"  read by the independent reader but not by gerbonara: {len(gerbonara_failed)}")
    print(f"  time: independent {t_nat:.0f} s, gerbonara + shapely {t_gb:.0f} s")
    worst = sorted(ok, key=lambda r: -abs(r[1]))[:12]
    print("\nlargest differences (file, area difference %, pixels that differ %):")
    for r in worst:
        print(f"  {r[0][:70]:70s} {r[1]:+7.1f} {r[2]:6.1f}")
    if refused:
        print("\nrefused files:", ", ".join(sorted(refused)[:20]))


if __name__ == "__main__":
    main()
