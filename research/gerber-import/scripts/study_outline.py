"""!
@file study_outline.py
@brief Can the board outline be read from the profile layer? The independent reader's stroke mask turned into the board shape (even-odd rule on the stroke crossings) against the exact vector construction, on the profile layers of the downloaded boards and on synthetic outlines with arcs, a slot and open contours.
@details The reference is gerbonara + shapely: the strokes buffered and unioned, the board being the interiors of that union (the region enclosed by the contour), with the cut-outs excluded by the even-odd nesting of the rings. For every file the study reports the board area from the mask and from the vector construction, the pixels that differ, the polygon extracted (vertices, area) and whether the contour was found closed. Synthetic cases: a rectangle with rounded corners (arcs), the same with a slot cut-out, and the same with a gap of 0.05, 0.2 and 0.5 mm in one side (a contour that is not closed). Writes out/outline.json and out/outline.npz (read by make_figures.py).
         Run: .venv/bin/python research/gerber-import/scripts/study_outline.py (from the repository root; about 20 seconds; the boards need scripts/fetch_boards.py).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-import in order)

import json
import warnings
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.ops import unary_union

import gerber_geometry as gg
import outline
from paths import DATA, OUT
from readers import board_files

warnings.simplefilter("ignore")
PIX = 0.05


def header():
    """!
    @brief The head of a synthetic profile file.
    @return str Gerber text.
    """
    return "G04 synthetic outline*\n%TF.FileFunction,Profile,NP*%\n%FSLAX46Y46*%\n%MOMM*%\nG75*\n%ADD10C,0.1*%\nD10*\n"


def synthetic(kind):
    """!
    @brief A synthetic profile layer: a 40 x 30 mm board with rounded corners of 3 mm radius, optionally with a slot, optionally with a gap in the bottom side.
    @param kind "rounded", "slot", "gap0.05", "gap0.2" or "gap0.5".
    @return str Gerber text.
    """
    def c(v):
        """!
        @brief A coordinate in the file's 4.6 format.
        @param v Millimetres.
        @return str Integer text.
        """
        return str(int(round(v * 1e6)))

    W, H, r = 40.0, 30.0, 3.0
    gap = float(kind[3:]) if kind.startswith("gap") else 0.0
    t = header()
    t += f"X{c(r)}Y{c(0)}D02*\n"
    # bottom side, left to right (with an optional gap in the middle)
    if gap:
        t += f"G01*\nX{c(W / 2 - gap / 2)}Y{c(0)}D01*\nX{c(W / 2 + gap / 2)}Y{c(0)}D02*\n"
    t += f"G01*\nX{c(W - r)}Y{c(0)}D01*\nG03*\nX{c(W)}Y{c(r)}I{c(0)}J{c(r)}D01*\nG01*\nX{c(W)}Y{c(H - r)}D01*\n"
    t += f"G03*\nX{c(W - r)}Y{c(H)}I{c(-r)}J{c(0)}D01*\nG01*\nX{c(r)}Y{c(H)}D01*\nG03*\nX{c(0)}Y{c(H - r)}I{c(0)}J{c(-r)}D01*\nG01*\nX{c(0)}Y{c(r)}D01*\n"
    t += f"G03*\nX{c(r)}Y{c(0)}I{c(r)}J{c(0)}D01*\nG01*\n"
    if kind == "slot":
        # a rectangular cut-out of 10 x 4 mm
        t += f"X{c(15)}Y{c(13)}D02*\nX{c(25)}Y{c(13)}D01*\nX{c(25)}Y{c(17)}D01*\nX{c(15)}Y{c(17)}D01*\nX{c(15)}Y{c(13)}D01*\n"
    return t + "M02*\n"


def reference(path):
    """!
    @brief The exact board region of a profile file by the vector construction: the strokes buffered and unioned, the board the interior rings nested once (the even-odd rule of the rings).
    @param path Path of the profile file (already prepared: no zero-width apertures).
    @return tuple (shapely geometry of the board or None, bounds of the strokes).
    """
    geom, _ = gg.load_copper(path)
    parts = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    board = None
    for p in parts:
        if p is None:
            continue
        # interiors of one stroke polygon are the regions it encloses: the board when it is the outer loop, a cut-out when it is nested inside another
        for ring in p.interiors:
            poly = Polygon(ring)
            board = poly if board is None else board.symmetric_difference(poly)
    return board, geom.bounds


def run(label, path):
    """!
    @brief Run one profile file.
    @param label Name for the report.
    @param path Path of the Gerber file.
    @return tuple (record dict, (board mask, stroke mask, window) or None).
    """
    raw = Path(path).read_text()
    text = outline.prepare(raw, PIX)
    prepared = OUT / "outline_prepared.gbr"
    prepared.write_text(text)
    board, bounds = reference(prepared)
    window = (bounds[0] - 0.5, bounds[3] + 0.5, bounds[2] - bounds[0] + 1.0, bounds[3] - bounds[1] + 1.0)
    strokes = outline.stroke_mask(text, window, PIX)
    mask, closed, leaked = outline.board_mask(strokes)
    rec = {"label": label, "pixel_mm": PIX, "closed_found": bool(closed), "leaked_pixels": leaked, "aperture_widths": outline.widths(raw), "board_area_mask_mm2": float(mask.sum() * PIX * PIX)}
    if board is not None:
        ref = gg.sample_mask(board, window[0], window[1], window[2], window[3], PIX) > 0.5
        rec.update({"board_area_vector_mm2": float(board.area), "pixels_that_differ": int((mask ^ ref).sum()), "pixels_board": int(ref.sum())})
    polys = outline.polygons(mask, window, PIX)
    rec["polygons"] = [{"vertices": int(len(p) - 1), "area_mm2": outline.area(p)} for p in polys[:6]]
    return rec, (mask, strokes, window)


def main():
    """!
    @brief Run the real boards and the synthetic outlines and write the results.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    records, store = [], {}
    cases = [(name, board_files(name)["edge"]) for name in ("storm", "chibi", "easyeda", "pcbrnd", "pcad", "dip", "fritz", "alleg") if "edge" in board_files(name)]
    synth_dir = DATA / "synthetic"
    synth_dir.mkdir(parents=True, exist_ok=True)
    for kind in ("rounded", "slot", "gap0.05", "gap0.2", "gap0.5"):
        p = synth_dir / f"outline_{kind}.gbr"
        p.write_text(synthetic(kind))
        cases.append(("synthetic " + kind, p))
    for label, path in cases:
        try:
            rec, (mask, strokes, window) = run(label, path)
        except Exception as e:
            records.append({"label": label, "error": type(e).__name__ + ": " + str(e)[:80]})
            print(f"{label:22s} failed: {type(e).__name__}")
            continue
        records.append(rec)
        store[label] = np.packbits(mask)
        store[label + "|strokes"] = np.packbits(strokes)
        store[label + "|shape"] = np.array(mask.shape)
        store[label + "|window"] = np.array(window)
        ref = rec.get("board_area_vector_mm2")
        print(f"{label:22s} closed {str(rec['closed_found']):5s}  board {rec['board_area_mask_mm2']:9.1f} mm2" + (f" vector {ref:9.1f}  ({100 * (rec['board_area_mask_mm2'] / ref - 1):+.3f} %), {rec['pixels_that_differ']} px differ" if ref else "") + f"  polygons {[(q['vertices'], round(q['area_mm2'], 1)) for q in rec['polygons'][:3]]}")
    np.savez_compressed(OUT / "outline.npz", **store)
    (OUT / "outline.json").write_text(json.dumps(records, indent=1))


if __name__ == "__main__":
    main()
