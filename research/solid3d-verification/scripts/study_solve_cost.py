"""!
@file study_solve_cost.py
@brief How long does a steady solve take and how much memory does it need, against the number of unknowns, for the 3D solid and for the layered finite-volume model (the numbers behind the 250 000 unknowns limit of `solid3d.MAX_CELLS`)?

@details A 100 x 80 mm two-layer board with full copper on both layers and one 2 W part, and the program's example board, are solved at several cell sizes. Every size runs in its own child process, so that the peak
         resident memory (`resource.getrusage`, kilobytes on Linux and bytes on macOS) belongs to that run alone. Time includes the assembly of the model and the direct sparse solve
         (the SuperLU solve that the application uses). The 3D solid runs inside `solid3d.size_limit` so that sizes above the 250 000 unknowns of the application can be timed. The result is written to
         `out/solve_cost.json` (git-ignored) with the machine and the library versions, and read by `make_figures.py` for figure 9. The last four cases reproduce the larger sizes quoted by the program documents (3D solid 400 000 and 512 000 unknowns, layered FVM 1 and 2 million).
         Usage: .venv/bin/python research/solid3d-verification/scripts/study_solve_cost.py (from the repository root; about 25 minutes and up to 9 GB; run nothing else heavy at the same time).
"""

import json
import os
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

# "solid3d" and "fvm": the plain board of board(); "example": the program's example board (4 layers, partial top copper, nine vias, a heatsink), 3D solid
CASES = [("solid3d", 1.10), ("solid3d", 0.70), ("solid3d", 0.55), ("solid3d", 0.44), ("fvm", 0.64), ("fvm", 0.40), ("fvm", 0.25),
         ("example", 1.4), ("example", 0.9), ("example", 0.72),
         # the sizes that the program documents quote: 3D solid about 400 000 and 512 000 unknowns, layered FVM about 1 and 2 million
         ("solid3d", 0.35), ("solid3d", 0.31), ("fvm", 0.127), ("fvm", 0.09)]


def board():
    """!
    @brief The board of the study: 100 x 80 mm, two layers, full copper, one 2 W part of 10 x 10 mm.
    @return Problem.
    """
    from pcbthermal import Problem
    p = Problem.new(100.0, 80.0, 2).add_full_copper()
    p.add_heater(1, 2.0, rect=(45, 35, 55, 45), name="U")
    return p


def child(kind, cell):
    """!
    @brief Run one solve in this process and print its unknowns, time and peak memory as one JSON line.
    @param kind "solid3d" or "fvm" (the plain board) or "example" (the example board in the 3D solid).
    @param cell Cell size in mm.
    @return None.
    """
    from pcbthermal import examples, fvm, solid3d
    p = examples.example_board() if kind == "example" else board()
    if kind in ("solid3d", "example"):
        n = solid3d.unknowns(p, cell)[0]
        t0 = time.perf_counter()
        with solid3d.size_limit(10_000_000):
            solid3d.solve_steady(p, cell)
    else:
        nx, ny = int(round(100.0 / cell)), int(round(80.0 / cell))
        n = 2 * nx * ny
        t0 = time.perf_counter()
        fvm.solve_steady(p, cell, method="direct")
    dt = time.perf_counter() - t0
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_gb = peak / 1e9 if sys.platform == "darwin" else peak * 1024 / 1e9      # bytes on macOS, kilobytes on Linux
    print(json.dumps({"model": kind, "cell_mm": cell, "unknowns": int(n), "seconds": dt, "peak_gb": peak_gb}))


def main():
    """!
    @brief Run every case in a child process and write out/solve_cost.json.
    @return None.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        child(sys.argv[2], float(sys.argv[3]))
        return
    rows = []
    for kind, cell in CASES:
        out = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--child", kind, str(cell)], capture_output=True, text=True, check=True)
        row = json.loads(out.stdout.strip().splitlines()[-1])
        rows.append(row)
        print(f"{row['model']:8s} cell {row['cell_mm']:.2f} mm: {row['unknowns']:>8,} unknowns, {row['seconds']:7.1f} s, peak {row['peak_gb']:.2f} GB", flush=True)
    import numpy, scipy
    info = {"machine": platform.platform(), "processor": platform.processor(), "python": platform.python_version(), "numpy": numpy.__version__, "scipy": scipy.__version__}
    (HERE.parent / "out").mkdir(exist_ok=True)
    (HERE.parent / "out" / "solve_cost.json").write_text(json.dumps({"info": info, "rows": rows}, indent=1))


if __name__ == "__main__":
    main()
