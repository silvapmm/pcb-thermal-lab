#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_arc_tolerance.py
@brief Is the farthest differing pixel of README 4.45 (0.045 px = 4.5 micrometres from the exact edge) the reader's own arc tolerance? The 12-layer comparison on the shifted grid re-run with a ten times finer tolerance and a finer vector truth.
@details Runs part 2 of study_render_compare.py (12 copper layers of the 8 boards at 0.1 mm, shifted grid) three times: ARC_TOLERANCE 0.005 mm with the 64-segment truth (the
         tables of 4.45), 0.0005 mm with the same truth, and 0.0005 mm with a 256-segment truth. If the explanation holds, only the board with arcs in its copper (`alleg`)
         changes and its farthest pixel falls with the tolerance. Needs gerbonara, shapely and the boards of scripts/fetch_boards.py.
         Run: .venv/bin/python research/gerber-import/scripts/study_arc_tolerance.py (from the repository root; about 1 minute).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-import in order)

import contextlib
import io

import numpy as np

import native_gerber as ng
import study_render_compare as rc


def run(tolerance, segments):
    """!
    @brief Part 2 of the render comparison with a given arc tolerance of the reader and a given circle approximation of the truth.
    @param tolerance Largest chord error of the reader's arcs (mm).
    @param segments Segments per quarter circle of the vector truth.
    @return Tuple (total differing pixels, farthest distance to an edge in pixels, dict "board layer" -> (pixels, farthest distance)).
    """
    saved = ng.ARC_TOLERANCE
    ng.ARC_TOLERANCE = tolerance
    rc.set_segments(segments)
    res = {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):          # part2 prints one line per layer; only the totals are wanted here
            rc.part2(res)
    finally:
        ng.ARC_TOLERANCE = saved
        rc.set_segments(rc.TRUTH_SEGMENTS)
    per = {f'{r["board"]} {r["layer"]}': (r["shifted"]["differing_pixels"], max(r["shifted"]["edge_distance_px"] or [0.0])) for r in res["layers"]}
    dist = np.concatenate([np.asarray(r["shifted"]["edge_distance_px"], float) for r in res["layers"]])
    return sum(v[0] for v in per.values()), float(dist.max()) if dist.size else 0.0, per


def main():
    """!
    @brief Print the three runs.
    @return None.
    """
    for tol, segs in ((0.005, 64), (0.0005, 64), (0.0005, 256)):
        total, far, per = run(tol, segs)
        print(f"reader arc tolerance {tol} mm, truth {segs} segments per quarter circle: {total} pixels differ, farthest {far:.4f} px from an edge")
        print("   " + ", ".join(f"{k} {v[0]} ({v[1]:.4f} px)" for k, v in per.items()))


if __name__ == "__main__":
    main()
