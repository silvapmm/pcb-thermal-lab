"""!
@file study_render_compare.py
@brief Does the independent reader draw the same copper as the other tools? The same layer rendered by four methods and compared pixel by pixel: the independent reader, gerbonara + shapely (the vector truth, sampled at the pixel centres), pygerber and pcb-tools (rasters with anti-aliasing).
@details Four parts. (1) The top copper of the Stormduino (KiCad, MIT) rendered by the four tools on the whole board at 0.025 mm; pygerber and pcb-tools draw their own raster, which is aligned to the common grid by the bounding box of the copper and a search of at most 6 pixels, and thresholded at 50 %; the difference with the vector truth is counted pixel by pixel. (2) Every copper layer of the eight boards (12 layers) at 0.1 mm, the independent reader against the vector truth: the pixels that differ, and how far each of them lies from the exact edge of the copper (a pixel centre that falls within a fraction of a pixel of an edge can go either way, so a real error would show up as a pixel far from any edge). (4) How much of the difference is the truth's own approximation of circles (16 segments per quarter turn in gerber_geometry; this study raises it to 64 and shows the sweep). (3) The pixels that differ against the pixel size (0.2 to 0.025 mm) on the Stormduino, on a grid shifted by an odd amount so that no pixel centre falls exactly on an edge (the coordinates of the files are multiples of 0.01 or 0.05 mm, so on the aligned grid many centres sit on an edge and go either way).
         Writes out/render_compare.npz (masks) and out/render_compare.json (numbers) read by make_figures.py. Needs gerbonara, shapely, pygerber 2.4.3, pcb-tools 0.1.6 and pillow.
         Run: .venv/bin/python research/gerber-import/scripts/study_render_compare.py (from the repository root; about 5 minutes).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-import in order)

import inspect
import json
import warnings
from pathlib import Path

import numpy as np
import shapely
from PIL import Image

import compare_readers as cr
import gerber_geometry as gg
import native_gerber as ng
from paths import OUT
from readers import board_files

warnings.simplefilter("ignore")
TRUTH_SEGMENTS = 64                           # segments per quarter circle of the vector truth (gerbonara_geometry uses 16: see part 4 for why it is raised here)
_ORIGINAL_PRIMITIVE = gg.primitive_polygon
OFFSET = (0.0137, 0.0091)                    # mm; a grid shifted by an odd amount so that no pixel centre falls exactly on an edge (coordinates in the files are multiples of 0.01 or 0.05 mm)
BOARDS = ("storm", "chibi", "easyeda", "pcbrnd", "pcad", "dip", "fritz", "alleg")
LAYERS = ("F", "L2", "L3", "L4", "L5", "B")


def set_segments(n):
    """!
    @brief Make the vector truth draw round ends, pads and arcs with n segments per quarter circle (gerber_geometry draws them with 16, an inscribed polygon that is a little smaller than the true circle).
    @param n Segments per quarter circle.
    @return None.
    """
    source = inspect.getsource(_ORIGINAL_PRIMITIVE).replace("quad_segs=16", f"quad_segs={n}")
    namespace = dict(gg.__dict__)
    exec(source, namespace)                         # the same function with a finer circle
    gg.primitive_polygon = namespace["primitive_polygon"]


def ours(path, window, pix):
    """!
    @brief Copper mask of the independent reader on a window.
    @param path Gerber file.
    @param window (x_left, y_top, width, height) in mm.
    @param pix Pixel size (mm).
    @return Boolean array (rows, cols).
    """
    cv = ng.Canvas(window[0], window[1], window[2], window[3], pix)
    ng.Layer(Path(path).read_text()).draw(cv)
    return cv.mask


def truth(geom, window, pix):
    """!
    @brief Copper mask of the exact vector geometry (gerbonara + shapely) sampled at the pixel centres.
    @param geom shapely geometry in mm.
    @param window (x_left, y_top, width, height) in mm.
    @param pix Pixel size (mm).
    @return Boolean array (rows, cols).
    """
    return gg.sample_mask(geom, window[0], window[1], window[2], window[3], pix) > 0.5


def align(img, ref):
    """!
    @brief Put a raster drawn by another tool on the grid of the reference: padded or cropped to its shape, placed by the bounding box of the copper, then the best shift of at most 6 pixels around it.
    @param img Boolean array of the other tool (its own extent).
    @param ref Boolean array of the reference grid.
    @return Tuple (aligned boolean array, (dy, dx) shift relative to the bounding-box estimate).
    """
    def bbox(m):
        r, c = np.where(m)
        return r.min(), c.min()
    (r0, c0), (r1, c1) = bbox(ref), bbox(img)
    out = np.zeros_like(ref)
    base = (r0 - r1, c0 - c1)
    best = None
    for dy in range(base[0] - 6, base[0] + 7):
        for dx in range(base[1] - 6, base[1] + 7):
            o = np.zeros_like(ref)
            ys, xs = slice(max(dy, 0), min(dy + img.shape[0], ref.shape[0])), slice(max(dx, 0), min(dx + img.shape[1], ref.shape[1]))
            iy, ix = slice(ys.start - dy, ys.stop - dy), slice(xs.start - dx, xs.stop - dx)
            o[ys, xs] = img[iy, ix]
            score = int((o ^ ref).sum())
            if best is None or score < best[0]:
                best, out = (score, (int(dy - base[0]), int(dx - base[1]))), o
    return out, best[1]


def pygerber_mask(path, pix):
    """!
    @brief Raster of pygerber (anti-aliased) thresholded at 50 %.
    @param path Gerber file (a cleaned copy is made).
    @param pix Pixel size (mm).
    @return Boolean array on pygerber's own extent.
    """
    from pygerber.common.rgba import RGBA
    from pygerber.gerberx3.api.v2 import ColorScheme, GerberFile
    white, black = RGBA.from_hex("#FFFFFFFF"), RGBA.from_hex("#000000FF")
    scheme = ColorScheme(background_color=black, solid_color=white, clear_color=black, solid_region_color=white, clear_region_color=black)
    cr.SCRATCH.mkdir(parents=True, exist_ok=True)
    png = cr.SCRATCH / "rc_py.png"
    GerberFile.from_file(cr.clean(path)).parse().render_raster(png, color_scheme=scheme, dpmm=int(round(1 / pix)))
    return np.asarray(Image.open(png).convert("L"), float) / 255.0 > 0.5


def pcbtools_mask(path, pix, bounds):
    """!
    @brief Raster of pcb-tools (cairo, anti-aliased) thresholded at 50 % over explicit bounds.
    @param path Gerber file.
    @param pix Pixel size (mm).
    @param bounds ((xmin, xmax), (ymin, ymax)) in mm.
    @return Boolean array.
    """
    import gerber
    from gerber.render import RenderSettings, theme
    from gerber.render.cairo_backend import GerberCairoContext
    layer = gerber.loads(Path(path).read_text())
    ctx = GerberCairoContext(scale=1.0 / pix)
    ctx.render_layer(layer, settings=RenderSettings(color=theme.COLORS["white"], alpha=1.0), bgsettings=RenderSettings(color=theme.COLORS["black"], alpha=1.0), bounds=bounds)
    png = cr.SCRATCH / "rc_pt.png"
    ctx.dump(str(png))
    return np.asarray(Image.open(png).convert("L"), float) / 255.0 > 0.5


def edge_distance(geom, mask_a, mask_b, window, pix):
    """!
    @brief Distance from the centre of every pixel that differs between two masks to the exact edge of the copper.
    @param geom shapely geometry in mm.
    @param mask_a First mask.
    @param mask_b Second mask.
    @param window (x_left, y_top, width, height) in mm.
    @param pix Pixel size (mm).
    @return numpy.ndarray Distances in pixels (empty when the masks are equal).
    """
    rows, cols = np.where(mask_a ^ mask_b)
    if rows.size == 0:
        return np.zeros(0)
    xs = window[0] + (cols + 0.5) * pix
    ys = window[1] - (rows + 0.5) * pix
    return shapely.distance(shapely.points(xs, ys), geom.boundary) / pix


def part1(results, store):
    """!
    @brief The four tools on the whole top copper of the Stormduino at 0.025 mm.
    @param results Dict that receives the numbers.
    @param store Dict that receives the masks.
    @return None.
    """
    path = board_files("storm")["F"]
    geom, _ = gg.load_copper(path)
    x0, y0, x1, y1 = geom.bounds
    pix = 0.025
    window = (x0 - 0.5, y1 + 0.5, x1 - x0 + 1.0, y1 - y0 + 1.0)
    tr = truth(geom, window, pix)
    masks = {"independent reader": ours(path, window, pix), "gerbonara + shapely (truth)": tr}
    shifts = {}
    masks["pygerber"], shifts["pygerber"] = align(pygerber_mask(path, pix), tr)
    masks["pcb-tools"], shifts["pcb-tools"] = align(pcbtools_mask(path, pix, ((window[0], window[0] + window[2]), (y0 - 0.5, y1 + 0.5))), tr)
    rows = {}
    for name, m in masks.items():
        diff = int((m ^ tr).sum())
        rows[name] = {"copper_pixels": int(m.sum()), "differing_pixels": diff, "differing_fraction_percent": 100.0 * diff / int(tr.sum()), "only_in_tool": int((m & ~tr).sum()), "only_in_truth": int((~m & tr).sum()), "shift": shifts.get(name)}
    results["storm_top"] = {"pixel_mm": pix, "shape": list(tr.shape), "window_mm": list(window), "tools": rows}
    for name, m in masks.items():
        store["storm_" + name.split(" ")[0]] = np.packbits(m)
    store["storm_shape"] = np.array(tr.shape)
    store["storm_window"] = np.array(window)
    # distance of the pixels where our reader differs to the exact edge, at this resolution
    d = edge_distance(geom, masks["independent reader"], tr, window, pix)
    results["storm_top"]["independent_reader_edge_distance_px"] = {"max": float(d.max()) if d.size else 0.0, "count": int(d.size)}


def part2(results):
    """!
    @brief Every copper layer of the eight boards at 0.1 mm: the independent reader against the vector truth, on the pixel grid that lines up with the coordinates of the file (where a pixel centre can sit exactly on an edge) and on a grid shifted by an odd amount.
    @param results Dict that receives the numbers.
    @return None.
    """
    rows = []
    for name in BOARDS:
        files = board_files(name)
        for role in LAYERS:
            if role not in files:
                continue
            geom, _ = gg.load_copper(files[role])
            x0, y0, x1, y1 = geom.bounds
            pix = 0.1
            row = {"board": name, "layer": role}
            for tag, off in (("aligned", (0.0, 0.0)), ("shifted", OFFSET)):
                window = (x0 - 0.5 + off[0], y1 + 0.5 - off[1], x1 - x0 + 1.0, y1 - y0 + 1.0)
                tr, mine = truth(geom, window, pix), ours(files[role], window, pix)
                d = edge_distance(geom, mine, tr, window, pix)
                row[tag] = {"copper_pixels": int(tr.sum()), "differing_pixels": int((mine ^ tr).sum()), "differing_fraction_percent": 100.0 * float((mine ^ tr).sum()) / float(tr.sum()), "area_difference_percent": 100.0 * (float(mine.sum()) - float(tr.sum())) / float(tr.sum()), "edge_distance_px": [round(float(v), 4) for v in d]}
            rows.append(row)
            print(f"{name:8s} {role:3s} copper {row['aligned']['copper_pixels']:8d}  differ aligned {row['aligned']['differing_pixels']:6d}  shifted {row['shifted']['differing_pixels']:5d} ({row['shifted']['differing_fraction_percent']:.4f} %)  area {row['shifted']['area_difference_percent']:+.4f} %", flush=True)
    results["layers"] = rows


def part3(results):
    """!
    @brief The pixels that differ against the pixel size, on the top copper of the Stormduino, on the shifted grid.
    @param results Dict that receives the numbers.
    @return None.
    """
    path = board_files("storm")["F"]
    geom, _ = gg.load_copper(path)
    x0, y0, x1, y1 = geom.bounds
    rows = []
    for pix in (0.2, 0.1, 0.05, 0.025):
        window = (x0 - 0.5 + OFFSET[0], y1 + 0.5 - OFFSET[1], x1 - x0 + 1.0, y1 - y0 + 1.0)
        tr, mine = truth(geom, window, pix), ours(path, window, pix)
        d = edge_distance(geom, mine, tr, window, pix)
        rows.append({"pixel_mm": pix, "differing_pixels": int((tr ^ mine).sum()), "differing_area_mm2": float((tr ^ mine).sum() * pix * pix), "area_truth_mm2": float(tr.sum() * pix * pix), "area_ours_mm2": float(mine.sum() * pix * pix), "perimeter_mm": float(geom.length), "max_edge_distance_px": float(d.max()) if d.size else 0.0})
        print(f"pixel {pix}: {rows[-1]['differing_pixels']} pixels differ ({rows[-1]['differing_area_mm2']:.3f} mm2), farthest {rows[-1]['max_edge_distance_px']:.3f} px from an edge", flush=True)
    results["pixel_sweep"] = rows


def part4(results):
    """!
    @brief How much of the difference is the truth's own polygon approximation of the circle: the same layer against a vector truth with 16, 32, 64 and 128 segments per quarter circle.
    @param results Dict that receives the numbers.
    @return None.
    """
    path = board_files("storm")["F"]
    rows = []
    for n in (16, 32, 64, 128):
        set_segments(n)
        geom, _ = gg.load_copper(path)
        x0, y0, x1, y1 = geom.bounds
        pix = 0.025
        window = (x0 - 0.5 + OFFSET[0], y1 + 0.5 - OFFSET[1], x1 - x0 + 1.0, y1 - y0 + 1.0)
        tr, mine = truth(geom, window, pix), ours(path, window, pix)
        rows.append({"segments_per_quarter": n, "vector_area_mm2": float(geom.area), "truth_sampled_mm2": float(tr.sum() * pix * pix), "ours_mm2": float(mine.sum() * pix * pix), "differing_pixels": int((tr ^ mine).sum()), "area_difference_percent": 100.0 * float(mine.sum() - tr.sum()) / float(tr.sum())})
        print(f"truth with {n:3d} segments per quarter: {rows[-1]['differing_pixels']:5d} pixels differ, ours - truth {rows[-1]['area_difference_percent']:+.4f} %", flush=True)
    results["truth_segments"] = rows
    set_segments(TRUTH_SEGMENTS)


def main():
    """!
    @brief Run the four parts and write the results.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    results, store = {}, {}
    set_segments(TRUTH_SEGMENTS)
    part4(results)
    part1(results, store)
    for name, row in results["storm_top"]["tools"].items():
        print(f"{name:30s} differ {row['differing_pixels']:7d} px = {row['differing_fraction_percent']:.3f} % of the copper (shift {row['shift']})")
    part3(results)
    part2(results)
    np.savez_compressed(OUT / "render_compare.npz", **store)
    (OUT / "render_compare.json").write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
