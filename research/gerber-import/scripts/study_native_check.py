"""!
@file study_native_check.py
@brief Cross-check of the independent reader (native_gerber.py, NumPy only) against gerbonara + shapely on the same windows.
@details For every window of windows.py the copper mask is drawn twice (centre-sampled at 0.1 mm): by native_gerber.render and by gerber_geometry.sample_mask on the shapely
         union. Reported per board: copper-area difference, share of pixels that differ (XOR over union), the boundary pixels excluded as well (a disagreement of one
         pixel on an edge is noise: a pixel is "edge" when a neighbour differs in the shapely mask), and the time of each route. Also the board box and the drills.
         Run: .venv/bin/python research/gerber-import/scripts/study_native_check.py (from the repository root) (about 1 minute).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-import in order)

import time

import numpy as np
from scipy import ndimage

import gerber_geometry as gg
import native_gerber as ng
import windows


def main():
    """!
    @brief Compare the two readers on every window and print a table per board.
    @return None.
    """
    masks, meta = windows.load()
    by = {}
    geoms = {}
    t_native = t_shape = 0.0
    for i, m in enumerate(meta):
        b, ox, oy = m[0], m[1], m[2]
        files = gg.board_files(b)
        if b not in geoms:
            t = time.time()
            geoms[b] = gg.load_copper(files["F"])[0]
            t_shape += time.time() - t
        t = time.time()
        native = ng.render(files["F"], ox, oy + windows.WIN, windows.WIN, windows.WIN, windows.PIX)
        t_native += time.time() - t
        ref = masks[i]
        diff = native != ref
        near_edge = ndimage.binary_dilation(ref, iterations=1) != ndimage.binary_erosion(ref, iterations=1)         # pixels touching a boundary of the shapely mask
        by.setdefault(b, []).append((100 * (native.sum() / ref.sum() - 1), 100 * diff.sum() / (native | ref).sum(), 100 * (diff & ~near_edge).sum() / ref.size))
    print("board    | copper area difference | pixels that differ (XOR/union) | differing pixels away from any edge (of the window)")
    for b, rows in by.items():
        a = np.array(rows)
        print(f"{b:8s} | {a[:, 0].mean():+6.3f} % (max {np.abs(a[:, 0]).max():.3f})   | {a[:, 1].mean():5.2f} % (max {a[:, 1].max():.2f})        | {a[:, 2].mean():.4f} % (max {a[:, 2].max():.4f})")
    print(f"\ntime for {len(meta)} windows: native {t_native:.1f} s; shapely route (one union per board) {t_shape:.1f} s plus the sampling")
    print("\nboard boxes (native outline layer vs gerbonara), mm:")
    for b in by:
        files = gg.board_files(b)
        if "edge" in files:
            nb = ng.layer_bbox(files["edge"])
            gb = gg.board_bbox(files["edge"], None)
            print(f"  {b:8s} native ({nb[0]:.2f}, {nb[1]:.2f}, {nb[2]:.2f}, {nb[3]:.2f})  gerbonara ({gb[0]:.2f}, {gb[1]:.2f}, {gb[2]:.2f}, {gb[3]:.2f})")
    files = gg.board_files("storm")
    h1 = sorted((round(x, 2), round(y, 2), round(d, 2)) for x, y, d in gg.drill_holes(files["drill"]))
    h2 = sorted((round(x, 2), round(y, 2), round(d, 2)) for x, y, d, _ in ng.read_drill(files["drill"]))
    print(f"\nstorm drill: gerbonara {len(h1)} holes, native {len(h2)} holes, identical: {h1 == h2}")


if __name__ == "__main__":
    main()
