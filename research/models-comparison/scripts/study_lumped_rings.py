"""!
@file study_lumped_rings.py
@brief Does the Lumped model converge with the number of rings, and does it jump with the source size? Before and after the minimum ring width.

@details The Lumped model (pcbthermal/lumped.py) builds rings around every footprint at distances of a geometric series. With many rings the inner ones get
         thinner than a cell; their cell count then does not match their width, their contour length (area / width) is underestimated and their resistance
         overestimated, so the result grew with the ring count and moved by 1 % from one millimetre of source size to the next. The program now merges ring
         edges closer than one cell (lumped.RING_MIN_WIDTH = 1); the old behaviour is RING_MIN_WIDTH = 0. Boards: the Cu / FR4 / Cu coupon of Culham and
         Yovanovich (50 mm, 2.5 W, h = 5 W/m2K on both faces, sources of 26 to 44 mm) and the example board, against the FVM; 10, 20 and 40 rings.
         With --json FILE it writes the numbers for the figures.

Usage: .venv/bin/python research/models-comparison/scripts/study_lumped_rings.py [--json FILE] (from the repository root; about 1 minute)
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from pcbthermal import Problem, SolverOptions, lumped, simulate        # noqa: E402
from pcbthermal.examples import example_board                         # noqa: E402
from pcbthermal.model import Materials                                # noqa: E402

CU, GAP = 35.6e-6, 1.5789e-3
SIDES = tuple(float(s) for s in range(26, 45, 1))
RINGS = (10, 20, 40)


def coupon(side):
    """!
    @brief The Cu / FR4 / Cu coupon with a centred square source.
    @param side Side of the source in mm.
    @return Problem.
    """
    mat = Materials(k_copper=400, k_fr4_through=0.4, k_fr4_inplane=0.4)
    p = Problem.new(50.0, 50.0, layers=2, thickness_mm=(2 * CU + GAP) * 1e3, copper_um=CU * 1e6, ambient=0.0, h_top=5, h_bottom=5, h_side=None, materials=mat)
    p.add_full_copper()
    p.add_heater(1, 2.5, rect=(25 - side / 2, 25 - side / 2, 25 + side / 2, 25 + side / 2), name="U")
    return p


def lumped_max(p, rings, width, cell_mm):
    """!
    @brief Maximum temperature of the Lumped model with a given ring count and minimum ring width.
    @param p Problem.
    @param rings Number of rings.
    @param width Minimum ring width in cells (0: the old behaviour).
    @param cell_mm Cell size in mm.
    @return float Temperature in degC.
    """
    saved = lumped.RING_MIN_WIDTH
    try:
        lumped.RING_MIN_WIDTH = width
        return simulate(p, SolverOptions(models=("lumped",), cell_mm=cell_mm, lumped_rings=rings)).results["lumped"].t_max
    finally:
        lumped.RING_MIN_WIDTH = saved


def main():
    """!
    @brief Print the errors against the FVM before and after, and write the JSON for the figures.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write the numbers to this file")
    args = ap.parse_args()
    out = {"sides": list(SIDES), "rings": list(RINGS), "coupon": {}, "example": {}}
    fvm_c = {s: simulate(coupon(s), SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"].t_max for s in SIDES}
    print("Coupon (50 mm, sources of 26 to 44 mm): error of the Lumped maximum against the FVM")
    print("| rings | before: range over the sources | largest step between 1 mm sizes | now: range | largest step |")
    print("| --: | --: | --: | --: | --: |")
    for r in RINGS:
        row = {}
        for tag, w in (("before", 0.0), ("after", 1.0)):
            row[tag] = [100.0 * (lumped_max(coupon(s), r, w, 0.5) / fvm_c[s] - 1.0) for s in SIDES]
        out["coupon"][str(r)] = row
        steps = {t: max(abs(a - b) for a, b in zip(v[1:], v[:-1])) for t, v in row.items()}
        print(f"| {r} | {min(row['before']):+.1f} to {max(row['before']):+.1f} % | {steps['before']:.1f} % | {min(row['after']):+.1f} to {max(row['after']):+.1f} % | {steps['after']:.1f} % |", flush=True)
    p = example_board()
    f = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"].t_max
    print("\nExample board: error of the Lumped maximum rise against the FVM")
    print("| rings | before | now |")
    print("| --: | --: | --: |")
    for r in RINGS:
        e = {tag: 100.0 * ((lumped_max(example_board(), r, w, 1.0) - 25.0) / (f - 25.0) - 1.0) for tag, w in (("before", 0.0), ("after", 1.0))}
        out["example"][str(r)] = e
        print(f"| {r} | {e['before']:+.1f} % | {e['after']:+.1f} % |", flush=True)
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
