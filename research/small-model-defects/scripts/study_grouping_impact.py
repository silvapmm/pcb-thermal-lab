#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_grouping_impact.py
@brief Item 1, impact of the candidate grouping rule ("min_inf" of lib/grouping.py): which frozen-number boards move, and does it help or harm on random via boards.
@details Part A: the 17 boards of the regression harness at the three frozen cells (2, 1, 0.5 mm), Lumped and Analytic hottest temperature with the program's
         grouping and with the candidate; prints the boards that move. Part B: 60 random 2- and 4-layer boards with a heater and clusters, rows and scattered
         vias (seeded), Lumped error against the FVM at 0.5 mm for the via effect (T without vias minus T with vias), program against candidate.
         Usage: python research/small-model-defects/scripts/study_grouping_impact.py [--part A|B]   (from the repository root; part A about 2 minutes, part B about 6).
"""

import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(ROOT / "releases" / "regression-harness" / "lib"))

import numpy as np                                                          # noqa: E402

import grouping                                                             # noqa: E402
import regress_boards as rb                                                 # noqa: E402
from pcbthermal.api import SolverOptions, simulate                          # noqa: E402
from pcbthermal.model import Problem                                        # noqa: E402


def tm(problem, cell, models, variant):
    """!
    @brief Hottest temperatures with a grouping variant.
    @param problem Problem.
    @param cell Cell in mm.
    @param models Tuple of model keys.
    @param variant Grouping variant.
    @return dict model -> degC.
    """
    with grouping.using(variant):
        s = simulate(problem, SolverOptions(models=models, cell_mm=cell))
    return {k: float(r.t_max) for k, r in s.results.items()}


def part_a():
    """!
    @brief The harness boards.
    @return None.
    """
    print("== A. Harness boards: Lumped and Analytic hottest temperature, program vs min_inf (K); only the boards that move are listed ==")
    moved = 0
    total = 0
    for name in rb.board_names():
        for cell in (2.0, 1.0, 0.5):
            p = rb.build(name)
            if len(p.vias) < 2 and cell != 2.0:
                continue
            try:
                a = tm(rb.build(name), cell, ("lumped", "analytic"), "program")
                b = tm(rb.build(name), cell, ("lumped", "analytic"), "min_inf")
            except Exception as exc:                                         # a board the models refuse at this cell
                print(name, cell, "skipped:", str(exc)[:60])
                continue
            total += 1
            dl, da = b["lumped"] - a["lumped"], b["analytic"] - a["analytic"]
            if abs(dl) > 1e-9 or abs(da) > 1e-9:
                moved += 1
                print(f"{name} | vias {len(p.vias)} | cell {cell} | Lumped {dl:+.4f} K | Analytic {da:+.4f} K")
    print(f"{moved} of {total} (board, cell) runs move")


def random_board(rng):
    """!
    @brief A random board with a part and vias: a cluster under the part plus rows or scattered vias elsewhere.
    @param rng random.Random.
    @return (Problem without the elsewhere vias, list of elsewhere vias, list of vias under the part).
    """
    W, H = rng.choice([(60, 60), (80, 60), (100, 80)])
    layers = rng.choice([2, 4])
    p = Problem.new(W, H, layers=layers, h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_full_copper()
    s = rng.choice([6.0, 8.0, 10.0])
    cx, cy = W / 2 + rng.uniform(-5, 5), H / 2 + rng.uniform(-5, 5)
    p.add_heater(1, 4.0, rect=(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2), name="U")
    n = rng.choice([2, 3, 4])
    pitch = rng.choice([1.0, 1.5, 2.0])
    under = [(cx + (i - (n - 1) / 2) * pitch, cy + (j - (n - 1) / 2) * pitch) for i in range(n) for j in range(n)]
    kind = rng.choice(["scatter", "row", "pair"])
    other = []
    for _ in range({"scatter": rng.randint(1, 4), "row": 6, "pair": 2}[kind]):
        x, y = rng.uniform(4, W - 4), rng.uniform(4, H - 4)
        if np.hypot(x - cx, y - cy) > s + 6:
            other.append((x, y))
    if kind == "row" and other:
        x0, y0 = other[0]
        # A row of six vias at 1.5 mm, kept inside the board (no clipping: clipped vias would coincide)
        x0 = min(x0, W - 3 - 7.5)
        other = [(x0 + 1.5 * k, y0) for k in range(6) if np.hypot(x0 + 1.5 * k - cx, y0 - cy) > s + 6]
    return p, other, under


def part_b():
    """!
    @brief Random boards, via effect of the elsewhere vias against the FVM.
    @return None.
    """
    print("\n== B. Random boards: change of T_max when the elsewhere vias are added to a part with a cluster under it (cell 0.5 mm) ==")
    print("(the FVM change is the reference; the model's error is Lumped change minus FVM change, in K)")
    rows = []
    rng = random.Random(20261112)
    for i in range(40):
        p, other, under = random_board(rng)
        if not other:
            continue
        for v in under:
            p.add_via(*v, diameter=0.3)
        base = tm(p, 0.5, ("fvm", "lumped"), "program")
        for v in other:
            p.add_via(*v, diameter=0.3)
        a = tm(p, 0.5, ("fvm", "lumped"), "program")
        b = tm(p, 0.5, ("lumped",), "min_inf")
        ref = a["fvm"] - base["fvm"]
        e_prog = (a["lumped"] - base["lumped"]) - ref
        e_new = (b["lumped"] - base["lumped"]) - ref
        rows.append((e_prog, e_new, ref, len(other)))
        print(f"{i:>2} | layers {p.board.layers} | {len(other)} elsewhere | FVM change {ref:+.3f} | Lumped error program {e_prog:+.3f} | candidate {e_new:+.3f}", flush=True)
    r = np.array(rows)
    print(f"{len(r)} boards; mean |error| program {np.abs(r[:, 0]).mean():.3f} K, candidate {np.abs(r[:, 1]).mean():.3f} K; max program {np.abs(r[:, 0]).max():.3f}, "
          f"candidate {np.abs(r[:, 1]).max():.3f}; boards where the candidate is worse by more than 0.05 K: {int((np.abs(r[:, 1]) > np.abs(r[:, 0]) + 0.05).sum())}")


if __name__ == "__main__":
    part = sys.argv[sys.argv.index("--part") + 1] if "--part" in sys.argv else "AB"
    if "A" in part:
        part_a()
    if "B" in part:
        part_b()
