#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_discretisation.py
@brief Causes d, e and f: the ring and tile structure, the series truncation and the peak term, on boards where the constriction is already treated.
@details Part 1 (e, Lumped): number of rings (4, 6, 10, 20) and raster cell (0.5, 1 mm) for the program and the patched model (cluster), on the 3 x 3 array at 3.5 and 1 mm and a lone via.
         Part 2 (e, Analytic): tile size (1.5, 2.5, 4 mm) and number of cosine modes (100, 300) for the program and the patched model, same boards and a unit cell.
         Part 3 (d, position in the tile): a via placed at several positions of the tiles of an 8 mm cell (reference: fine-grid solver with the via at that position), Analytic
         without correction, with the self-term and with the self-term plus the bilinear spread; interior positions only (a via on the symmetry line of the reference is a half via).
         Part 4 (f, the peak term of the Lumped): error of the footprint mean rise and of the peak for the array boards with the cluster treatment (macro factor 0, 0.5, 1).
Usage: python research/lumped-analytic-vias/scripts/study_discretisation.py   (from the repository root; about 5 minutes)
"""

import contextlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import analytic_patch as ap                                                  # noqa: E402
import cases                                                                 # noqa: E402
import harness as hz                                                         # noqa: E402
import lumped_patch as lp                                                    # noqa: E402
import program_cases as pc                                                   # noqa: E402
from pcbthermal import SolverOptions, analytic, simulate                    # noqa: E402


def run(prob, model, cell, rings=10, modes=300):
    """!
    @brief Maximum rise of one model with explicit rings and modes.
    @param prob Problem.
    @param model "lumped" or "analytic".
    @param cell Cell in mm.
    @param rings Rings of the Lumped model.
    @param modes Cosine modes of the Analytic model.
    @return float Rise in K.
    """
    r = simulate(prob, SolverOptions(models=(model,), cell_mm=cell, lumped_rings=rings, analytic_modes=modes)).results[model]
    return float(r.t_max - prob.board.ambient)


@contextlib.contextmanager
def tiles(target_mm):
    """!
    @brief Replace the tile grid of the Analytic model by tiles of about target_mm.
    @param target_mm Tile size in mm (None keeps the program's rule).
    @return Context manager.
    """
    old = analytic._tile_grid
    if target_mm is not None:
        def tg(W, H, lam):
            t = target_mm * 1e-3
            ntx, nty = max(int(np.ceil(W / t - 1e-9)), 1), max(int(np.ceil(H / t - 1e-9)), 1)
            return ntx, nty, W / ntx, H / nty
        analytic._tile_grid = tg
    try:
        yield
    finally:
        analytic._tile_grid = old


def boards():
    """!
    @brief The boards of parts 1 and 2 with their reference via effect.
    @return list of (label, Problem, E_ref).
    """
    out = []
    for label, prob in (("array 3.5 mm Cu", cases.array(4, 3, 3.5, 0.3, 385.0)), ("array 1.0 mm Cu", cases.array(4, 3, 1.0, 0.3, 385.0)),
                        ("lone via 4 mm Cu", cases.lone_via(30.0, 0.3, 385.0, 2, 3.0, 4.0)), ("unit cell 8 mm Cu", cases.unit_cell(8, 0.3, 385.0, layers=2))):
        e_ref, _, _ = hz.reference_uniform(prob, 1.0 / 16)
        out.append((label, prob, e_ref))
    return out


def part1(bs):
    """!
    @brief Rings and raster cell of the Lumped model.
    @param bs Boards.
    @return None.
    """
    print("## 1. Lumped: rings and raster cell (error of the via effect, percent)\n")
    print("| board | E_ref K | model | " + " | ".join(f"{r} rings, {c} mm" for r in (4, 6, 10, 20) for c in (0.5, 1.0)) + " |")
    print("| :-- | --: | :-- |" + " --: |" * 8)
    for label, prob, e_ref in bs:
        q0 = hz.no_vias(prob)
        for name, ctx in (("program", lambda: contextlib.nullcontext()), ("cluster", lambda: lp.patched("krogh", cell="nn", cluster=True, macro_cap=0.75))):
            cells = []
            for r in (4, 6, 10, 20):
                for c in (0.5, 1.0):
                    with ctx():
                        e = run(q0, "lumped", c, r) - run(prob, "lumped", c, r)
                    cells.append(f"{100 * (e / e_ref - 1):+.1f}")
            print(f"| {label} | {e_ref:.2f} | {name} | " + " | ".join(cells) + " |")


def part2(bs):
    """!
    @brief Tiles and modes of the Analytic model.
    @param bs Boards.
    @return None.
    """
    print("\n## 2. Analytic: tile size and cosine modes (error of the via effect, percent)\n")
    cols = [(t, m) for t in (1.5, 2.5, 4.0) for m in (100, 300)]
    print("| board | E_ref K | model | " + " | ".join(f"tile {t} mm, {m} modes" for t, m in cols) + " |")
    print("| :-- | --: | :-- |" + " --: |" * len(cols))
    for label, prob, e_ref in bs:
        q0 = hz.no_vias(prob)
        for name, ctx in (("program", lambda: ap.patched("off")), ("patched", lambda: ap.patched("on", spread="bilinear"))):
            cells = []
            for t, m in cols:
                with tiles(t), ctx():
                    e = run(q0, "analytic", 0.5, modes=m) - run(prob, "analytic", 0.5, modes=m)
                cells.append(f"{100 * (e / e_ref - 1):+.1f}")
            print(f"| {label} | {e_ref:.2f} | {name} | " + " | ".join(cells) + " |")


def part3():
    """!
    @brief Position of the via in the tile.
    @return None.
    """
    print("\n## 3. Position of a lone via in the tiles (8 mm cell, tiles of 2.67 mm, 2 layers, copper fill; error of the via effect, percent)\n")
    print("| via at (x, y) mm | position in the tile | E_ref K | program | self-term | self-term + spread |")
    print("| :-- | :-- | --: | --: | --: | --: |")
    for dx, dy in ((0, 0), (-1, 0), (-1, -1), (-2, -2), (-3, -3), (-3, -1), (1, -3), (-0.667, -0.667)):
        x, y = 4 + dx, 4 + dy
        prob = cases.unit_cell(8.0, 0.3, 385.0, offset=(dx, dy))
        par = pc.layer_parameters(prob)
        import resolved_boards as rb
        e_ref = rb.full_board_2d(par, 1e-3 / 16, [], 1.0) - rb.full_board_2d(par, 1e-3 / 16, [(x * 1e-3, y * 1e-3, 0)], 1.0)
        q0 = hz.no_vias(prob)
        out = []
        for ctx in (lambda: ap.patched("off"), lambda: ap.patched("on"), lambda: ap.patched("on", spread="bilinear")):
            with ctx():
                out.append(100 * ((pc.max_rise(q0, "analytic", 0.5) - pc.max_rise(prob, "analytic", 0.5)) / e_ref - 1))
        fx, fy = (x / (8 / 3)) % 1, (y / (8 / 3)) % 1
        print(f"| ({x:.2f}, {y:.2f}) | ({fx:.2f}, {fy:.2f}) of a tile | {e_ref:.2f} | " + " | ".join(f"{v:+.1f}" for v in out) + " |")


def part4():
    """!
    @brief Mean and peak of the footprint in the Lumped model.
    @return None.
    """
    print("\n## 4. The peak term of the Lumped model: error of the drop of the footprint MEAN and of the PEAK (percent), array boards, copper fill\n")
    print("| pitch mm | dMean ref K | dMax ref K | macro factor | error mean | error peak | error peak with the inward-flow term |")
    print("| --: | --: | --: | --: | --: | --: | --: |")
    for pitch in (3.5, 2.0, 1.0):
        prob = cases.array(4, 3, pitch, 0.3, 385.0)
        t_v, dx = hz.reference_field(prob, 1.0 / 16)
        t_n, _ = hz.reference_field(prob, 1.0 / 16, with_vias=False)
        c = 10.5e-3
        sl = slice(int(round((c - 5e-3) / dx)), int(round((c + 5e-3) / dx)))
        d_mean = t_n[0][sl, sl].mean() - t_v[0][sl, sl].mean()
        d_max = t_n[0].max() - t_v[0].max()
        q0 = hz.no_vias(prob)

        def mean_max(p):
            r = simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5)).results["lumped"]
            a, b = int(round((c - 5e-3) / r.dx)), int(round((c + 5e-3) / r.dx))
            return float(r.T[0][a:b, a:b].mean()), float(r.t_max)
        m0, x0 = mean_max(q0)
        for ms in (0.0, 0.5, 1.0):
            with lp.patched("krogh", cell="nn", cluster=True, macro_scale=ms):
                m, x = mean_max(prob)
            with lp.patched("krogh", cell="nn", cluster=True, macro_scale=ms, peak=True):
                _, xp = mean_max(prob)
            print(f"| {pitch} | {d_mean:.2f} | {d_max:.2f} | {ms} | {100 * ((m0 - m) / d_mean - 1):+.1f} | {100 * ((x0 - x) / d_max - 1):+.1f} | {100 * ((x0 - xp) / d_max - 1):+.1f} |")


def main():
    """!
    @brief Run the four parts.
    @return None.
    """
    pc.load_libraries()
    bs = boards()
    part1(bs)
    part2(bs)
    part3()
    part4()


if __name__ == "__main__":
    main()
