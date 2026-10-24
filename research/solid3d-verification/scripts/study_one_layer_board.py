"""!
@file study_one_layer_board.py
@brief Does the 3D solid keep the laminate of a one-layer board, and how close are the layered models to an independent 3D solver on such a board?

@details A one-layer board has no dielectric gap, and the 3D solid built its slabs from the gaps only, so the board was its copper alone: no FR-4 to spread the
         heat sideways and nothing between the copper and the bottom face. The program now adds the laminate of the layered models (the slab minus the copper)
         as four dielectric slabs under the copper. The study runs a 60 x 60 x 1.6 mm board with 35 um copper (full copper and a 20 mm pad, a 6 mm part of 1 W)
         in the five models, and the 3D solid on a board whose laminate is reduced to 1 um (what the 3D solid used to see).
         Part 2 compares every model with the independent 3D solver of lib/layered3d.py on boards that both can represent (FR-4 isotropic at 0.3 W/mK, copper of the
         program's materials, films 10 and 15 W/m2K, no edge loss, 0.5 mm cells; full copper at 0.8, 1.6 and 3.2 mm, a 20 mm pad at 0.8 and 1.6 mm), with the
         laminate nodes of the layered models (pcbthermal/laminate.py) and without them (laminate.nodes switched off and the Lumped rings unmerged, the
         behaviour before the corrections). With --json FILE it writes the numbers of part 2 for the figures.

Usage: .venv/bin/python research/solid3d-verification/scripts/study_one_layer_board.py [--json FILE] (from the repository root; about 2 minutes)
"""

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import layered3d as L                                                  # noqa: E402
from pcbthermal import Problem, SolverOptions, laminate, lumped, simulate   # noqa: E402
from pcbthermal.model import Materials                                 # noqa: E402

MODELS = ("fvm", "fdm", "solid3d", "lumped", "analytic")


def board(pad, thickness_mm=1.6):
    """!
    @brief The one-layer board of the study.
    @param pad True for a 20 mm copper pad, False for full copper.
    @param thickness_mm Board thickness in mm.
    @return Problem.
    """
    p = Problem.new(60.0, 60.0, layers=1, thickness_mm=thickness_mm, copper_um=35)
    if pad:
        p.add_zone(1, rect=(20, 20, 40, 40))
    else:
        p.add_full_copper()
    p.add_heater(1, 1.0, rect=(27, 27, 33, 33), name="U")
    return p


K_ISO, CU, H_TOP, H_BOTTOM = 0.3, 35e-6, 10.0, 15.0
CASES = ((False, 0.8), (False, 1.6), (False, 3.2), (True, 0.8), (True, 1.6))


def iso_board(pad, thickness_mm):
    """!
    @brief The one-layer board of part 2 (isotropic FR-4, no edge loss, so that the independent solver represents the same board).
    @param pad True for a 20 mm copper pad, False for full copper.
    @param thickness_mm Board thickness in mm.
    @return Problem.
    """
    p = Problem.new(60.0, 60.0, layers=1, thickness_mm=thickness_mm, copper_um=CU * 1e6, ambient=25.0, h_top=H_TOP, h_bottom=H_BOTTOM, h_side=None,
                    materials=Materials(k_fr4_through=K_ISO, k_fr4_inplane=K_ISO))
    if pad:
        p.add_zone(1, rect=(20, 20, 40, 40))
    else:
        p.add_full_copper()
    p.add_heater(1, 1.0, rect=(27, 27, 33, 33), name="U")
    return p


def independent(pad, thickness_mm):
    """!
    @brief Rise of the hottest copper cell in the independent 3D solver (the copper slab is copper in the pad and laminate elsewhere).
    @param pad True for a 20 mm copper pad, False for full copper.
    @param thickness_mm Board thickness in mm.
    @return float Rise in K.
    """
    k_cu = Materials().k_copper
    xs = (np.arange(120) + 0.5) * 0.5
    k_top = np.where((np.abs(xs[None, :] - 30.0) < 10.0) & (np.abs(xs[:, None] - 30.0) < 10.0), k_cu, K_ISO) if pad else k_cu
    res = L.solve(0.5e-3, 120, 120, [(CU, k_top, 1), (thickness_mm * 1e-3 - CU, K_ISO, 8)], (27e-3, 27e-3, 33e-3, 33e-3), 1.0, H_TOP, H_BOTTOM,
                  film_under_source=True)
    return res["cell_max_source"]


def rises(pad, thickness_mm, before=False):
    """!
    @brief Rise of the board maximum in every model, with the corrections or with the behaviour before them.
    @param pad True for a 20 mm copper pad, False for full copper.
    @param thickness_mm Board thickness in mm.
    @param before True to switch the laminate nodes and the series film off and leave the Lumped rings unmerged.
    @return Dict model -> rise in K.
    """
    saved_nodes, saved_w = laminate.nodes, lumped.RING_MIN_WIDTH
    try:
        if before:
            laminate.nodes = lambda board, count=None: None
            lumped.RING_MIN_WIDTH = 0.0
        r = simulate(iso_board(pad, thickness_mm), SolverOptions(models=MODELS, cell_mm=0.5)).results
    finally:
        laminate.nodes, lumped.RING_MIN_WIDTH = saved_nodes, saved_w
    return {m: r[m].t_max - 25.0 for m in MODELS}


def main():
    """!
    @brief Print the maximum temperature of every model and of the 3D solid without the laminate (part 1), and the comparison with the independent solver (part 2).
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write the numbers of part 2 to this file")
    args = ap.parse_args()
    print("| copper | " + " | ".join(MODELS) + " | 3D solid without the laminate (old) |")
    print("| :-- | " + " | ".join("--:" for _ in MODELS) + " | --: |")
    for label, pad in (("full copper", False), ("20 mm pad", True)):
        r = simulate(board(pad), SolverOptions(models=MODELS, cell_mm=1.0)).results
        old = simulate(board(pad, thickness_mm=0.036), SolverOptions(models=("solid3d",), cell_mm=1.0)).results["solid3d"]
        print(f"| {label} | " + " | ".join(f"{r[m].t_max:.2f}" for m in MODELS) + f" | {old.t_max:.2f} |", flush=True)
    print("\nPart 2: error of the board maximum rise against the independent 3D solver, before the corrections -> now")
    print("| copper | thickness (mm) | independent (K) | " + " | ".join(MODELS) + " |")
    print("| :-- | --: | --: | " + " | ".join("--:" for _ in MODELS) + " |")
    rows = []
    for pad, t in CASES:
        ref = independent(pad, t)
        b, a = rises(pad, t, before=True), rises(pad, t)
        rows.append({"pad": pad, "thickness_mm": t, "independent": ref, "before": b, "after": a})
        print(f"| {'20 mm pad' if pad else 'full'} | {t:g} | {ref:.2f} | " + " | ".join(f"{100 * (b[m] / ref - 1):+.1f} -> {100 * (a[m] / ref - 1):+.1f} %" for m in MODELS) + " |",
              flush=True)
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    main()
