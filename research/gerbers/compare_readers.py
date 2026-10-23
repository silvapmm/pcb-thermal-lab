"""!
@file compare_readers.py
@brief The independent reader against the other Python Gerber tools, on files with a known copper area (made with gerbonara, see make_synthetic.py) and on the real boards.
@details Tools: the independent reader (`native_gerber`, centre sampling), gerbonara (vector geometry through shapely: exact area, and centre sampling), pygerber 2.4.3 (MIT, raster
         render with anti-aliasing) and pcb-tools 0.1.6 (cairo render with anti-aliasing). For the renderers two areas are given: the sum of the grey level (coverage) and the pixels above 50 %.
         A tool that cannot parse a file is reported; pygerber is also given a cleaned copy of the file (gerbonara writes `G75` without its `*` and an obsolete `%IPPOS*%`).
         Run with the comparison environment (numpy, shapely, gerbonara, pygerber, pcb-tools, pillow): python compare_readers.py [synthetic|boards]
"""

import sys
import time
import warnings
from pathlib import Path

import numpy as np
from PIL import Image

warnings.simplefilter("ignore")

import gerber_geometry as gg
import native_gerber as ng
import make_synthetic as ms

HERE = Path(__file__).resolve().parent
SCRATCH = HERE / "out" / "compare_tmp"
PIXELS = (0.1, 0.05, 0.025)                    # mm; 0.0125 is added for the files with the thinnest tracks


def clean(path):
    """!
    @brief Copy of a gerbonara-written file with the two syntax oddities removed (obsolete %IPPOS*%, G75 without its star, double star after G01).
    @param path Gerber file.
    @return Path of the cleaned copy.
    """
    SCRATCH.mkdir(parents=True, exist_ok=True)
    text = Path(path).read_text().replace("%IPPOS*%\n", "").replace("\nG75\n", "\nG75*\n").replace("G01**", "G01*")
    out = SCRATCH / (Path(path).stem + "_clean.gbr")
    out.write_text(text)
    return out


def native_area(path, pix):
    """!
    @brief Copper area by the independent reader (centre sampling).
    @param path Gerber file.
    @param pix Pixel size (mm).
    @return Tuple (area mm2, seconds).
    """
    t = time.time()
    layer = ng.Layer(Path(path).read_text())
    bb = layer.bbox()
    cv = ng.Canvas(bb[0] - 0.5, bb[3] + 0.5, bb[2] - bb[0] + 1.0, bb[3] - bb[1] + 1.0, pix)
    layer.draw(cv)
    return float(cv.mask.sum() * pix * pix), time.time() - t


def gerbonara_area(path, pix):
    """!
    @brief Copper area by gerbonara: exact (vector, shapely) and by centre sampling.
    @param path Gerber file.
    @param pix Pixel size (mm).
    @return Tuple (exact area, sampled area, seconds).
    """
    t = time.time()
    geom, _ = gg.load_copper(path)
    x0, y0, x1, y1 = geom.bounds
    m = gg.sample_mask(geom, x0 - 0.5, y1 + 0.5, x1 - x0 + 1.0, y1 - y0 + 1.0, pix) > 0.5
    return float(geom.area), float(m.sum() * pix * pix), time.time() - t


def pygerber_area(path, pix):
    """!
    @brief Copper area by pygerber's raster renderer (white copper on black).
    @param path Gerber file (cleaned copy).
    @param pix Pixel size (mm).
    @return Tuple (coverage area, threshold area, seconds).
    @throws Exception If pygerber cannot parse or render the file.
    """
    from pygerber.common.rgba import RGBA
    from pygerber.gerberx3.api.v2 import ColorScheme, GerberFile
    white, black = RGBA.from_hex("#FFFFFFFF"), RGBA.from_hex("#000000FF")
    cs = ColorScheme(background_color=black, solid_color=white, clear_color=black, solid_region_color=white, clear_region_color=black)
    t = time.time()
    png = SCRATCH / "py.png"
    GerberFile.from_file(path).parse().render_raster(png, color_scheme=cs, dpmm=int(round(1 / pix)))
    a = np.asarray(Image.open(png).convert("L"), float) / 255.0
    return float(a.sum() * pix * pix), float((a > 0.5).sum() * pix * pix), time.time() - t


def pcbtools_area(path, pix, bounds):
    """!
    @brief Copper area by pcb-tools (cairo render, white on black) over explicit bounds (its automatic bounds were wrong for round flashes).
    @param path Gerber file.
    @param pix Pixel size (mm).
    @param bounds ((xmin, xmax), (ymin, ymax)) in mm.
    @return Tuple (coverage area, threshold area, seconds).
    @throws Exception If pcb-tools cannot parse or render the file.
    """
    import gerber
    from gerber.render import RenderSettings, theme
    from gerber.render.cairo_backend import GerberCairoContext
    t = time.time()
    layer = gerber.loads(Path(path).read_text())
    ctx = GerberCairoContext(scale=1.0 / pix)
    ctx.render_layer(layer, settings=RenderSettings(color=theme.COLORS["white"], alpha=1.0), bgsettings=RenderSettings(color=theme.COLORS["black"], alpha=1.0), bounds=bounds)
    png = SCRATCH / "pt.png"
    ctx.dump(str(png))
    a = np.asarray(Image.open(png).convert("L"), float) / 255.0
    return float(a.sum() * pix * pix), float((a > 0.5).sum() * pix * pix), time.time() - t


def run_file(name, path, exact, pixels):
    """!
    @brief Run every tool on one file at every pixel size and print the error of the area against the exact value.
    @param name Label.
    @param path Gerber file.
    @param exact Exact copper area (mm2) or None to use gerbonara's vector area as the reference.
    @param pixels Pixel sizes (mm).
    @return List of rows (label, pixel, tool, error %, seconds) for the summary.
    """
    rows = []
    cleaned = clean(path)
    layer = ng.Layer(Path(path).read_text())
    bb = layer.bbox()
    bounds = ((bb[0] - 0.5, bb[2] + 0.5), (bb[1] - 0.5, bb[3] + 0.5))
    ref = exact
    for pix in pixels:
        res = {}
        try:
            a, t = native_area(path, pix)
            res["native"] = (a, t)
        except Exception as e:
            res["native"] = (None, type(e).__name__)
        try:
            ex, a, t = gerbonara_area(path, pix)
            res["gerbonara vector"] = (ex, t)
            res["gerbonara sampled"] = (a, t)
            ref = ref if ref is not None else ex
        except Exception as e:
            res["gerbonara vector"] = (None, type(e).__name__)
        for label, fn in (("pygerber raw", lambda: pygerber_area(path, pix)), ("pygerber cleaned", lambda: pygerber_area(cleaned, pix)), ("pcb-tools", lambda: pcbtools_area(path, pix, bounds))):
            try:
                cov, thr, t = fn()
                res[label + " coverage"] = (cov, t)
                res[label + " >50%"] = (thr, t)
            except Exception as e:
                res[label] = (None, type(e).__name__)
        for tool, (a, t) in res.items():
            rows.append((name, pix, tool, None if a is None else 100 * (a / ref - 1), t))
    return rows, ref


def summarize(allrows):
    """!
    @brief Print a table: one line per tool, one column per pixel size, the mean absolute area error over the files and the number of failures.
    @param allrows Rows from `run_file`.
    @return None.
    """
    tools = list(dict.fromkeys(r[2] for r in allrows))
    pixels = sorted({r[1] for r in allrows}, reverse=True)
    print(f"\n{'tool':26s}" + "".join(f"{'pix ' + str(p) + ' mm':>20s}" for p in pixels) + f"{'failures':>10s}{'mean s':>9s}")
    for tool in tools:
        line = f"{tool:26s}"
        for p in pixels:
            e = [r[3] for r in allrows if r[2] == tool and r[1] == p and r[3] is not None]
            line += f"{(f'{np.mean(np.abs(e)):.2f} % ({np.mean(e):+.2f})' if e else '-'):>20s}"
        fails = sum(1 for r in allrows if r[2] == tool and r[3] is None)
        ts = [r[4] for r in allrows if r[2] == tool and isinstance(r[4], float)]
        print(line + f"{fails:>10d}{(np.mean(ts) if ts else 0):9.2f}")


def synthetic():
    """!
    @brief The synthetic files: per file and per pixel size, then the summary.
    @return None.
    """
    ms.main()
    allrows = []
    cases = ms.cases()
    for name, (_, geom, text) in cases.items():
        pixels = PIXELS + ((0.0125,) if name.startswith("track_0.0") or name.startswith("thin") else ())
        rows, ref = run_file(name, ms.OUT / f"{name}.gbr", geom.area, pixels)
        allrows += rows
        print(f"\n{name}: exact {geom.area:.4f} mm2 ({text})")
        for pix in pixels:
            print(f"  pix {pix}: " + ", ".join(f"{r[2]} {r[3]:+.1f}%" for r in rows if r[1] == pix and r[3] is not None and "pygerber raw" not in r[2] and "coverage" not in r[2] or (r[1] == pix and r[2] == "native")))
    summarize(allrows)


def boards():
    """!
    @brief The real boards: every tool against gerbonara's vector area of the top copper layer.
    @return None.
    """
    allrows = []
    for d in sorted((HERE / "data").iterdir()):
        f = d / "F.gbr"
        if d.name in ("conformance", "synthetic") or not f.exists():
            continue
        rows, ref = run_file(d.name, f, None, (0.1, 0.05))
        allrows += rows
        print(f"{d.name}: vector area {ref:.1f} mm2")
    summarize(allrows)


if __name__ == "__main__":
    {"synthetic": synthetic, "boards": boards}[sys.argv[1] if len(sys.argv) > 1 else "synthetic"]()
