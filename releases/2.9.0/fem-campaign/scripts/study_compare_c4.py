#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_compare_c4.py
@brief Rows C4 and C8 of the FEM campaign (validation 56.4 and 56.8): the published plate cases of `tests/test_published_cases.py` (cases 1a, 1b, 2 and 3 of Muzychka, Culham and
       Yovanovich 2003) in every model that can hold them, against the printed centroids, and the strong-edge plate against the stored finite-element limits.
@details Mode `published`: the plates are built exactly as in `tests/test_published_cases.py` (one copper layer of the plate thickness and conductivity, the film on the bottom face,
         top and edges insulated; case 1b a 2 mm spreader over a 10 mm substrate), each source's centroid is read in the column of the model and, where the model has a surface map
         (the FEM, the 3D solid, the estimate of the FVM and FDM), on the surface, and compared with the paper's printed centroid (the paper prints the SURFACE). Shortfall = paper
         minus model, as a share of the paper's rise above the 25 degC ambient; positive = the model is below the paper.
         Mode `edge`: the 10 x 10 mm four-layer 1.6 mm plate with a cooled edge (`tests/test_published_cases.py::_strong_edge_plate`, section 46 of docs/validation.md) at 200 and 1000
         W/m2K against the finite-element limits 36.981 and 24.332 K of `research/independent-fem-edge` README 3(a) (quoted, not re-run here: the independent tool lives in its own
         environment), plus 500 and 2000 W/m2K against the FEM alone; hottest column rise, cells 0.5 and 0.25 mm.
         Run from the repository root: `.venv/bin/python -u releases/2.9.0/fem-campaign/scripts/study_compare_c4.py published|edge` (a few minutes, under 3 GB).
"""

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
LABEL = {"fvm": "FVM", "fdm": "FDM", "lumped": "Lumped", "analytic": "Analytic", "solid3d": "3D solid", "fem": "FEM"}
AMB = 25.0
FE_LIMIT = {200.0: 36.981, 1000.0: 24.332}            # K, research/independent-fem-edge README 3(a), also tests/test_published_cases.py


def centroid(field, width, cx, cy):
    """!
    @brief Value of a cell field at a point: the mean of the four cells around it (the source centroids fall on cell corners).
    @param field Array (ny, nx).
    @param width Board side in mm.
    @param cx X of the point in mm.
    @param cy Y of the point in mm.
    @return float.
    """
    ny, nx = field.shape
    dx = width / nx
    i, j = int(round(cx / dx)), int(round(cy / dx))
    return float(field[j - 1:j + 1, i - 1:i + 1].mean())


def cases():
    """!
    @brief The four published plates: name, builder, width, sources, printed centroids, cell in mm.
    @return list of tuples.
    """
    import test_published_cases as TP
    from pcbthermal import Problem
    from pcbthermal.model import Materials

    def plate(width, t_mm, k, h, sources):
        """!
        @brief One plate of the papers as the tests build it.
        @param width Side in mm.
        @param t_mm Thickness in mm.
        @param k Conductivity in W/mK.
        @param h Bottom film in W/m2K.
        @param sources List of (rect, power).
        @return Problem.
        """
        p = Problem.new(width, width, layers=1, thickness_mm=1.0001 * t_mm, copper_um=t_mm * 1e3, ambient=AMB, h_top=1e-6, h_bottom=h, h_side=None, materials=Materials(k_copper=k))
        p.add_full_copper()
        for i, (r, pw) in enumerate(sources):
            p.add_heater(1, pw, rect=r, name=f"S{i}")
        return p

    def spreader():
        """!
        @brief Case 1b: a 2 mm layer of k 350 W/mK over a 10 mm substrate of k 10 W/mK.
        @return Problem.
        """
        mat = Materials(k_copper=350.0, k_fr4_through=10.0, k_fr4_inplane=10.0)
        p = Problem.new(300.0, 300.0, layers=2, thickness_mm=12.001, copper_um=2000.0, ambient=AMB, h_top=1e-6, h_bottom=10.0, h_side=None, materials=mat)
        p.board.copper_thickness = [2e-3, 1e-6]
        p.add_full_copper(layers=[1])
        p.add_full_copper(layers=[2], fill=1.0)
        for i, (r, pw) in enumerate(TP.CASE1_SOURCES):
            p.add_heater(1, pw, rect=r, name=f"S{i}")
        return p

    cross = [(TP._sq(50, 50, 20), 5.0), (TP._sq(30, 50, 20), 5.0), (TP._sq(70, 50, 20), 5.0), (TP._sq(50, 30, 20), 5.0), (TP._sq(50, 70, 20), 5.0)]
    return [("case 3, cross (100 x 100 x 10 mm, k 50, h 50)", lambda: plate(100.0, 10.0, 50.0, 50.0, cross), 100.0, [r for r, _ in cross], [80.61], 1.0),
            ("case 2, baseplate (50 x 50 x 10 mm, k 150, h 400)", lambda: plate(50.0, 10.0, 150.0, 400.0, TP.CASE2_SOURCES), 50.0, [r for r, _ in TP.CASE2_SOURCES], TP.CASE2_PAPER, 1.0),
            ("case 1a, thick plate (300 x 300 x 10 mm, k 10, h 10)", lambda: plate(300.0, 10.0, 10.0, 10.0, TP.CASE1_SOURCES), 300.0, [r for r, _ in TP.CASE1_SOURCES], [84.97, 108.43], 2.5),
            ("case 1b, spreader (2 mm, k 350, on 10 mm, k 10)", spreader, 300.0, [r for r, _ in TP.CASE1_SOURCES], [56.55, 59.94], 2.5)]


def published():
    """!
    @brief Run the four plates in every model and print the shortfall against the printed centroids.
    @return None.
    """
    from pcbthermal import SolverOptions, simulate
    for name, build, width, rects, paper, cell in cases():
        print(f"\n### {name}, cell {cell:g} mm; printed centroids {' / '.join(f'{x:.2f}' for x in paper)} degC (the paper prints the surface)")
        print("| model | read-out | centroids degC | shortfall paper - model, % of the paper rise (first source" + (" ... all)" if len(paper) > 1 else ")") + " | seconds |\n| :-- | :-- | :-- | :-- | --: |")
        for m in ("fem", "fvm", "fdm", "solid3d", "analytic", "lumped"):
            p = build()
            try:
                sim = simulate(p, SolverOptions(models=(m,), cell_mm=cell))
            except Exception as exc:
                print(f"| {LABEL[m]} | - | not run: {type(exc).__name__}: {str(exc)[:70]} | | |")
                continue
            res = sim.results.get(m)
            if res is None:
                print(f"| {LABEL[m]} | - | not run: {'; '.join(sim.warnings)[:80]} | | |")
                continue
            reads = [("column", np.asarray(res.T)[0])]
            arr = getattr(res, "arrays", None) or {}
            if "T_surface" in arr and np.isfinite(np.asarray(arr["T_surface"][0])).any():
                reads.append(("surface", np.asarray(arr["T_surface"][0], dtype=float)))
            for tag, field in reads:
                cen = [centroid(field, width, 0.5 * (r[0] + r[2]), 0.5 * (r[1] + r[3])) for r in rects][:len(paper)]
                short = [100.0 * (pp - c) / (pp - AMB) for pp, c in zip(paper, cen)]
                print(f"| {LABEL[m]} | {tag} | {' / '.join(f'{c:.2f}' for c in cen)} | {' / '.join(f'{s:+.1f}' for s in short)} | {sim.seconds.get(m, float('nan')):.1f} |")
    print("\nThe Lumped has no surface map. A shortfall of the column read-out is the through-thickness term that one node per layer cannot hold (docs/validation.md 55.1).")


def strong_edge():
    """!
    @brief The cooled-edge plate in the FVM, FDM, 3D solid and FEM against the stored finite-element limits.
    @return None.
    """
    import test_published_cases as TP
    from pcbthermal import SolverOptions, simulate
    print(f"The plate: 10 x 10 mm, four layers, 1.6 mm, 35 um copper to the wall, h_top 10, h_bottom 200 W/m2K, a 0.5 W part of 3 x 2 mm; finite-element limits (quoted): {FE_LIMIT}")
    print("| h_side W/m2K | cell mm | " + " | ".join(f"{LABEL[m]} rise K (% of the limit)" for m in ("fvm", "fdm", "solid3d", "fem")) + " |")
    print("| --: | --: | " + " | ".join("--:" for _ in range(4)) + " |")
    for h in (200.0, 500.0, 1000.0, 2000.0):
        for cell in (0.5, 0.25):
            row = []
            for m in ("fvm", "fdm", "solid3d", "fem"):
                try:
                    sim = simulate(TP._strong_edge_plate(h), SolverOptions(models=(m,), cell_mm=cell))
                    v = sim.results[m].t_max - AMB if m in sim.results else None
                except Exception as exc:
                    v = None
                    print(f"   {LABEL[m]} {h:g} {cell:g}: {type(exc).__name__}: {str(exc)[:80]}")
                row.append("-" if v is None else (f"{v:.3f} ({100 * (v / FE_LIMIT[h] - 1):+.1f})" if h in FE_LIMIT else f"{v:.3f}"))
            print(f"| {h:g} | {cell:g} | " + " | ".join(row) + " |")


def main():
    """!
    @brief Command line of the study.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("mode", choices=("published", "edge"))
    a = ap.parse_args()
    tree = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    import pcbthermal
    print(f"tree {tree}, program {pcbthermal.__version__}")
    published() if a.mode == "published" else strong_edge()


if __name__ == "__main__":
    main()
