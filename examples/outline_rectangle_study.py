"""!
@file outline_rectangle_study.py
@brief How good is the rectangle of the same area that the lumped and analytic models use on a board with an outline?

@details For five outlines and several part positions the FVM solves the real shape (the reference) and the lumped and analytic models solve (a) the bounding
         box, which ignores the outline, (b) the rectangle of the same area (`Problem.equivalent_rectangle`, what the program does), (c) a box 10 % larger than
         the bounding box. The error is the difference of the maximum temperature divided by the FVM rise above ambient, in percent (negative = too cool).

Usage: python examples/outline_rectangle_study.py
"""

import copy
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from pcbthermal import SolverOptions, simulate                        # noqa: E402
from pcbthermal.examples import example_board                         # noqa: E402
from pcbthermal.geometry import points_in_polygon, polygon_area, rounded_rectangle   # noqa: E402

LAYOUTS = {                                   # Centres of the two parts in metres
    "example": [(0.035, 0.040), (0.068, 0.041)],
    "centre": [(0.050, 0.040), (0.056, 0.040)],
    "off-centre": [(0.030, 0.025), (0.070, 0.055)],
    "near the edge": [(0.025, 0.020), (0.030, 0.060)],
}


def outlines(w, h):
    """!
    @brief The five outlines of the Board panel presets.
    @param w Box width in mm.
    @param h Box height in mm.
    @return Dict name -> list of [x, y] in mm.
    """
    c = 0.15 * min(w, h)
    return {
        "ellipse": [[w / 2 * (1 + math.cos(2 * math.pi * k / 48)), h / 2 * (1 + math.sin(2 * math.pi * k / 48))] for k in range(48)],
        "L": [[0, 0], [w, 0], [w, h / 2], [w / 2, h / 2], [w / 2, h], [0, h]],
        "T": [[0, h / 2], [w / 3, h / 2], [w / 3, 0], [2 * w / 3, 0], [2 * w / 3, h / 2], [w, h / 2], [w, h], [0, h]],
        "chamfer": [[c, 0], [w - c, 0], [w, c], [w, h - c], [w - c, h], [c, h], [0, h - c], [0, c]],
        "rounded": rounded_rectangle(w, h, c),
    }


def with_parts(centres):
    """!
    @brief The example board with its two parts moved to the given centres.
    @param centres Two (x, y) centres in metres.
    @return Problem.
    """
    p = example_board()
    for h, c in zip(p.heaters, centres):
        h.polygon = h.polygon - h.polygon.mean(axis=0) + np.array(c)
    return p


def scaled_box(p, s):
    """!
    @brief Rectangular copy of the problem whose box and positions are scaled by s (parts keep their size).
    @param p Problem without outline.
    @param s Scale factor.
    @return Problem.
    """
    q = copy.deepcopy(p)
    q.board.width, q.board.height = p.board.width * s, p.board.height * s
    for z in q.zones:
        z.polygon = z.polygon * s
    for v in q.vias:
        v.x, v.y = v.x * s, v.y * s
    for h in q.heaters:
        c = h.polygon.mean(axis=0)
        h.polygon = h.polygon - c + c * s
    return q


def main():
    """!
    @brief Print the error table of the three rectangles for every outline and layout.
    """
    opt = lambda m: SolverOptions(models=(m,), cell_mm=1.0)                # noqa: E731
    print("| Outline | Parts | Area ratio | FVM Tmax | bbox L / A | same area L / A | 1.1 x bbox L / A |")
    print("| :-- | :-- | --: | --: | --: | --: | --: |")
    for name, poly in outlines(100.0, 80.0).items():
        pa = np.array(poly) / 1000.0
        for lay, centres in LAYOUTS.items():
            if not all(points_in_polygon(np.array([c[0]]), np.array([c[1]]), pa)[0] for c in centres):
                continue                                                  # A part would be off the board
            real = with_parts(centres)
            real.board.outline = pa
            ref = simulate(real, opt("fvm")).results["fvm"]
            rise = ref.delta_t
            ratio = polygon_area(pa) / (real.board.width * real.board.height)
            plain = with_parts(centres)
            cols = []
            for prob in (plain, real, scaled_box(plain, 1.1)):
                row = []
                for m in ("lumped", "analytic"):
                    row.append((simulate(prob, opt(m)).results[m].t_max - ref.t_max) / rise * 100.0)
                cols.append(f"{row[0]:+.1f} / {row[1]:+.1f}")
            print(f"| {name} | {lay} | {ratio:.3f} | {ref.t_max:.1f} | " + " | ".join(cols) + " |", flush=True)


if __name__ == "__main__":
    main()
