"""!
@file study_offgrid_heater.py
@brief Heater whose edges fall between cell edges: FVM and FDM against a fine grid.

Question: what happens to the peak temperature when the heater polygon does not follow the cell
edges? The polygon is defined explicitly here (it replaces the earlier "10.4 x 10.7 mm heater at
30.3 mm", whose board could not be rebuilt): the reference board (100 x 100 mm, 2 layers, full
copper), 4 W, a heater with corners (30.3, 30.3) and (40.7, 41.0) mm, area 10.4 x 10.7 = 111.28 mm2.
The corner x = 30.3 mm lies between cell edges at 2, 1, 0.5 and 0.2 mm; at 0.1 mm every edge is on the grid.

Usage: python research/models-comparison/scripts/study_offgrid_heater.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pcbthermal import fdm, fvm                                                 # noqa: E402
from pcbthermal.model import problem_from_dict, problem_to_dict, reference_problem   # noqa: E402

# Explicit heater polygon in millimetres (counter-clockwise), and the area it must have
POLYGON_MM = [[30.3, 30.3], [40.7, 30.3], [40.7, 41.0], [30.3, 41.0]]
AREA_MM2 = 10.4 * 10.7


def build():
    """!
    @brief The reference board with the off-grid heater.
    @return Problem (4 W, 2 layers, full copper, heater polygon POLYGON_MM).
    """
    d = problem_to_dict(reference_problem(power=4.0, layers=2))
    d["heaters"][0]["polygon_mm"] = POLYGON_MM
    return problem_from_dict(d)


def main():
    """!
    @brief Print the peak temperature of FVM and FDM (area and point sampling) at several cell sizes.
    @return None
    """
    p = build()
    print(f"heater polygon {POLYGON_MM}, area {AREA_MM2:.2f} mm2, power {p.heaters[0].power} W")
    ref = fvm.solve_steady(p, 0.1).t_max
    print(f"reference: FVM at 0.1 mm (edges on the grid) = {ref:.2f} C")
    print("| Cell [mm] | FVM | FDM area | FDM point |")
    print("| --: | --: | --: | --: |")
    for c in (2.0, 1.0, 0.5, 0.2):
        f = fvm.solve_steady(p, c).t_max
        a = fdm.solve_steady(p, c).t_max
        q = fdm.solve_steady(p, c, sampling="point").t_max
        print(f"| {c:g} | {f:.2f} ({f - ref:+.2f}) | {a:.2f} ({a - ref:+.2f}) | {q:.2f} ({q - ref:+.2f}) |")


if __name__ == "__main__":
    main()
