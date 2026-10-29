"""!
@file study_cost.py
@brief Q5: time and memory of the zone fill under the old rule, the per-point union (prototype) and the exact polygon union (shapely), on boards of 1, 4 and 25 million sample points.
@details Question answered: what does the per-point union cost against the loop of `develop`, and what would the polygon union cost? A board of N cells has 16 N sample points (4 x 4 per cell): 1 M points = 250 x 250 cells,
         4 M = 500 x 500, 25 M = 1250 x 1250. Three drawings: one zone over the whole board, 100 rectangles of a tenth of the side, 2000 small rectangles (tracks). Time is the best of 3 (1 for the largest),
         memory the peak of numpy allocations (tracemalloc) above the start; the largest board runs only when the memory projected from the two smaller ones is below 2 GB (the projection is printed).
         The accuracy of the 4 x 4 lattice against the exact union is measured on the 250 x 250 board with the 100 rectangles (random fills).
         Run from the repository root: .venv/bin/python research/zone-union/scripts/study_cost.py ; out/study_cost.json, out/study_cost.txt (about 2 minutes).
"""

import _bootstrap  # noqa: F401  (import paths)

import json
import time
import tracemalloc
from types import SimpleNamespace

import numpy as np

import variant
from paths import OUT

SIZES = {"1 M": 250, "4 M": 500, "25 M": 1250}
BOARD = 0.1                                           # side of the board (m); the cell size follows from the number of cells


def drawing(kind, rng):
    """!
    @brief Zones of a drawing, in metres, on a 0.1 m board.
    @param kind "one", "100" or "2000".
    @param rng numpy random Generator.
    @return list of zone-like objects.
    """
    zs = []
    if kind == "one":
        zs.append((0, 0, BOARD, BOARD, 1.0))
    else:
        n = int(kind)
        side = BOARD / 10 if n == 100 else BOARD / 100
        for _ in range(n):
            x, y = rng.uniform(0, BOARD - side, 2)
            w, h = (side * rng.uniform(0.5, 1.0, 2)) if n == 100 else (side * rng.uniform(0.3, 1.0), side * rng.uniform(0.05, 0.2))
            zs.append((x, y, x + w, y + h, float(rng.choice([1.0, 1.0, 0.5, 0.8]))))
    return [SimpleNamespace(polygon=np.array([[a, b], [c, b], [c, d], [a, d]]), fill=f, layer=0) for a, b, c, d, f in zs]


def measure(fn, repeat):
    """!
    @brief Best time and peak memory of a call.
    @param fn Function without arguments.
    @param repeat Number of repetitions for the time.
    @return tuple (seconds, peak memory in MB).
    """
    best = 1e9
    for _ in range(repeat):
        t = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t)
    tracemalloc.start()
    fn()
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return best, peak / 1e6


def main():
    """!
    @brief Run the measurements and print the tables.
    @return None.
    """
    variant.use()
    import zone_rules as zr
    import zone_shapely as zs
    from pcbthermal.geometry import coverage_fraction
    rng = np.random.default_rng(7)
    lines, result = [], {}

    def out(s=""):
        """!
        @brief Print and keep a line.
        @param s Text.
        @return None.
        """
        print(s, flush=True)
        lines.append(s)

    def old_rule(zones, n, dx):
        """!
        @brief The loop of `develop`: the larger share of every cell.
        @param zones Zones.
        @param n Cells per side.
        @param dx Cell size (m).
        @return array (n, n).
        """
        f = np.zeros((n, n))
        for z in zones:
            f = np.maximum(f, coverage_fraction(z.polygon, n, n, dx, dx, 4) * z.fill)
        return f

    out(f"{'board':>6s}{'cells':>10s}{'drawing':>9s}{'old s':>9s}{'old MB':>9s}{'point s':>9s}{'point MB':>10s}{'exact s':>9s}{'exact MB':>10s}")
    mem_proj = {}
    for label, n in SIZES.items():
        dx = BOARD / n
        for kind in ("one", "100", "2000"):
            zones = drawing(kind, rng)
            rep = 3 if n <= 500 else 1
            # The largest board with one zone over everything needs the most memory: run it only if the projection from the smaller boards is safe
            if n == 1250 and kind == "one":
                proj = mem_proj.get("500/one", (0, 0))[1] * (1250 / 500) ** 2
                out(f"  (25 M, one zone: projected peak {proj:.0f} MB for the point rule)")
                if proj > 2000:
                    out("  skipped: projection above 2 GB")
                    continue
            ts_o, m_o = measure(lambda: old_rule(zones, n, dx), rep)
            ts_p, m_p = measure(lambda: zr.combine(zones, 1, n, n, dx, dx, 4, "max_point"), rep)
            if kind == "2000" and n > 500:
                ts_e, m_e = float("nan"), float("nan")           # the exact union of 2000 rectangles on 1.5 M cells: not run, the scaling is measured on the smaller boards
            else:
                ts_e, m_e = measure(lambda: zs.exact_fill(zones, 1, n, n, dx, dx), 1)
            mem_proj[f"{n}/{kind}"] = (ts_p, m_p)
            result[f"{label}/{kind}"] = {"cells": n * n, "old": [ts_o, m_o], "point": [ts_p, m_p], "exact": [ts_e, m_e]}
            out(f"{label:>6s}{n * n:10d}{kind:>9s}{ts_o:9.3f}{m_o:9.0f}{ts_p:9.3f}{m_p:10.0f}{ts_e:9.3f}{m_e:10.0f}")
    # Accuracy of the lattice against the exact union
    n = 250
    dx = BOARD / n
    zones = drawing("100", np.random.default_rng(11))
    ex = zs.exact_fill(zones, 1, n, n, dx, dx)[0]
    out("\nAccuracy of the sub-sample lattice against the exact union (250 x 250 cells, 100 rectangles of fills 1, 0.8, 0.5)")
    out(f"{'s':>4s}{'max |dfill|':>14s}{'mean |dfill|':>14s}{'copper area error %':>22s}")
    acc = {}
    for s in (2, 3, 4, 8, 16):
        f = zr.combine(zones, 1, n, n, dx, dx, s, "max_point")[0]
        acc[s] = (float(np.abs(f - ex).max()), float(np.abs(f - ex).mean()), float(100 * (f.sum() / ex.sum() - 1)))
        out(f"{s:4d}{acc[s][0]:14.4f}{acc[s][1]:14.5f}{acc[s][2]:22.4f}")
    old = old_rule(zones, n, dx)
    out(f"old rule (4 x 4): max |dfill| {np.abs(old - ex).max():.4f}, mean {np.abs(old - ex).mean():.5f}, copper area error {100 * (old.sum() / ex.sum() - 1):.3f} %")
    result["accuracy"] = acc
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "study_cost.json").write_text(json.dumps(result, indent=1))
    (OUT / "study_cost.txt").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
