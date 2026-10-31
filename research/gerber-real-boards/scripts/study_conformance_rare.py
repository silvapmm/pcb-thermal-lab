#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_conformance_rare.py
@brief Does our own reader agree with the Ucamco test files and with a second reader, and do real files ever use the features it refuses (aperture blocks, LM/LR/LS transformations, the moire primitive)?
@details Files: the Gerber layer-format test files, the two PCB fabrication data examples (4 and 10 copper layers) and the X3 samples of Ucamco (scripts/fetch_boards.py --ucamco), and the layers of the open boards
         (fetch_boards.py). Three questions:
         A. Refusals: for every Gerber file, is it read by the independent reader (research/gerber-import native_gerber.Layer), and if not, with what message? The Ucamco test files are made to hit exactly the rare features.
         B. Agreement: for the files both readers read, the copper area at 0.05 mm pixels of the independent reader against gerbonara + shapely (if installed; same method as research/gerber-import
            study_reader_conformance.py, which compared 164 gerbonara test files: 161 agree within 3 %); the Ucamco test files come with a picture of the correct rendering (.png) that is NOT compared here (the area is).
         C. Frequency: how many real files (the open boards, the fabrication examples, the X3 samples) use each rare feature (lib/rare_features.py)? A feature no real file uses is not worth implementing now; a file
            that uses one is refused with a message the user can read (the program must say which file and which feature).
         Output: out/conformance_rare.json and the printed tables. Success criterion (before the run): every Ucamco test file is either read with area within 3 % of the second reader or refused with a specific message
         (never silently wrong); the real board files use none of AB/LM/LR/LS. NOT verified: the Ucamco pictures, the polarity-changing files (LPC with transformed apertures) beyond what the area shows, the Excellon files.
         Run (from the repository root): .venv-research/bin/python research/gerber-real-boards/scripts/study_conformance_rare.py   (minutes)
"""

import _bootstrap  # noqa: F401  (puts the import paths in order)

import json
import sys
import warnings
from pathlib import Path

import numpy as np

import native_gerber as ng
import rare_features as rf
import rb_paths
import registry

warnings.simplefilter("ignore")


def collect():
    """!
    @brief The Gerber files to test, with a class (ucamco test, fabrication example, x3 sample, open board).
    @return list of (class, path).
    """
    out = []
    u = rb_paths.DATA / "ucamco"
    if u.exists():
        for d in sorted(u.iterdir()):
            cls = "ucamco layer-format test" if d.name == "layer_format_tests" else ("ucamco fabrication example" if d.name.startswith("fabrication") else "ucamco X3 sample")
            for f in sorted(d.iterdir()):
                if f.suffix.lower() == ".gbr":
                    out.append((cls, f))
    for key in registry.available():
        d = registry.folder(key)
        for f in sorted(d.iterdir()):
            if f.name.endswith(".gbr") and f.name not in ("job.gbrjob",):
                out.append(("open board", f))
    return out


def area(layer, box, pix):
    """!
    @brief Copper area of a layer on a box by the independent reader.
    @param layer native_gerber.Layer.
    @param box (x0, y0, x1, y1).
    @param pix Pixel (mm).
    @return float mm2.
    """
    x0, y0, x1, y1 = box
    cov = ng.render_coverage(layer, x0, y1, x1 - x0, y1 - y0, pix, 2)
    return float(cov.sum() * pix * pix)


def second_reader_area(path, box, pix):
    """!
    @brief Copper area by gerbonara + shapely, or None when they are not installed or fail.
    @param path File path.
    @param box (x0, y0, x1, y1).
    @param pix Pixel (mm).
    @return float mm2 or None.
    """
    try:
        import gerber_geometry as gg
        geom = gg.load_copper(path)[0]
        x0, y0, x1, y1 = box
        return float(gg.sample_mask(geom, x0, y1, x1 - x0, y1 - y0, pix, aa=2).sum() * pix * pix)
    except Exception:
        return None


def main(argv):
    """!
    @brief Run A, B and C and print the tables.
    @param argv Unused.
    @return None.
    """
    files = collect()
    if not files:
        raise SystemExit("no files: run scripts/fetch_boards.py --ucamco (and the boards) first")
    rows, per_file = [], {}
    pix = 0.05
    for cls, p in files:
        text = p.read_text(errors="replace")
        per_file[f"{cls}: {p.parent.name}/{p.name}"] = rf.count(text)
        rec = {"class": cls, "file": f"{p.parent.name}/{p.name}", "size_kb": len(text) // 1024}
        try:
            layer = ng.Layer(text)
        except Exception as exc:                                       # a refusal is a result: the message is the point
            rec.update(status="refused", message=f"{type(exc).__name__}: {exc}")
            rows.append(rec)
            print(f"{rec['file']:60s} REFUSED {rec['message'][:90]}")
            continue
        box = layer.bbox()
        if not box or box[2] - box[0] <= 0 or box[3] - box[1] <= 0:
            rec.update(status="read", note="no extent (empty or only flashes of zero size)")
            rows.append(rec)
            continue
        big = max(box[2] - box[0], box[3] - box[1])
        px = max(pix, big / 4000.0)                                    # keep the raster small for large files
        a1 = area(layer, box, px)
        a2 = second_reader_area(p, box, px)
        rec.update(status="read", area_mm2=a1, second_area_mm2=a2, pix=px, difference_percent=(100.0 * (a1 / a2 - 1.0) if a2 else None))
        rows.append(rec)
        print(f"{rec['file']:60s} read, area {a1:9.2f} mm2" + (f", second reader {a2:9.2f} ({rec['difference_percent']:+.2f} %)" if a2 else ", second reader n/a"))
    summ = rf.summarise(per_file)
    print("\nrare features: files that use them / total count / examples")
    for k, (n, tot, ex) in summ.items():
        print(f"  {k:62s} {n:3d} files {tot:7d}  {', '.join(ex[:2])}")
    refused = [r for r in rows if r["status"] == "refused"]
    agree = [r for r in rows if r.get("difference_percent") is not None and abs(r["difference_percent"]) <= 3.0]
    compared = [r for r in rows if r.get("difference_percent") is not None]
    print(f"\n{len(rows)} files: {len(refused)} refused, {len(compared)} compared with the second reader, {len(agree)} within 3 %")
    rb_paths.OUT.mkdir(parents=True, exist_ok=True)
    with open(rb_paths.OUT / "conformance_rare.json", "w") as fh:
        json.dump({"rows": rows, "features": {k: list(v) for k, v in summ.items()}}, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
