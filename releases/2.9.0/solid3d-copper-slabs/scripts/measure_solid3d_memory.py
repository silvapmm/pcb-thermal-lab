#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file measure_solid3d_memory.py
@brief Peak memory of the 3D solid with thick copper (several slabs per copper layer) against the law of `pcbthermal/memory.py` (`CONTINUOUS["solid3d"]`), one case per fresh process.
@details Question: does the law of the 3D solid, fitted on boards whose slabs were the gaps and one slab per copper layer, still bound the peak of a board with 2 to 8 slabs in each copper layer
         (the unknown count that the law reads is exact, `solid3d.unknowns`, so only the bytes per unknown and the dependence on the slabs can change)? The peak is `ru_maxrss` of the child
         minus the resident size after the imports (bytes on macOS), the same measure as `releases/2.8.0/fem-model/scripts/measure_fem_law.py`; the estimate is `memory.estimate_bytes("solid3d", n, cells,
         base=0)`, which carries the safety factor, so `measured / estimate` must stay below 1.
         Usage, from the repository root, ONE heavy job at a time (`--heavy` cases peak at 2 to 6 GB and take minutes: the maintainer schedules them):

             .venv/bin/python releases/2.9.0/solid3d-copper-slabs/scripts/measure_solid3d_memory.py --dry-run          # list the cases and their unknowns, run nothing
             .venv/bin/python releases/2.9.0/solid3d-copper-slabs/scripts/measure_solid3d_memory.py                    # the light cases
             .venv/bin/python releases/2.9.0/solid3d-copper-slabs/scripts/measure_solid3d_memory.py --heavy            # the heavy cases too
             .venv/bin/python releases/2.9.0/solid3d-copper-slabs/scripts/measure_solid3d_memory.py --one 4 210 2.0    # one case, one JSON line (layers, copper um, cell mm)
"""

import argparse
import json
import os
import resource
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

# (copper layers, copper um of every layer, cell mm, side mm); light: up to about 250 000 unknowns, heavy: above
LIGHT = [(2, 35.0, 2.0, 100.0), (2, 210.0, 2.0, 100.0), (2, 420.0, 2.0, 100.0), (4, 140.0, 2.0, 100.0), (4, 420.0, 2.0, 100.0), (6, 210.0, 3.0, 100.0), (2, 420.0, 1.5, 100.0)]
HEAVY = [(2, 420.0, 1.0, 100.0), (4, 140.0, 1.0, 100.0), (4, 420.0, 1.0, 100.0), (6, 420.0, 1.5, 100.0), (2, 560.0, 0.75, 100.0)]


def build(layers, um, side):
    """!
    @brief A board with `layers` copper layers of `um` um, full copper, one part on the top layer (the gaps are those of a 1.6 mm board).
    @param layers Copper layers, count.
    @param um Copper thickness of every layer, um.
    @param side Side of the square board, mm.
    @return Problem.
    """
    sys.path.insert(0, ROOT)
    from pcbthermal import Problem
    p = Problem.new(side, side, layers=layers, thickness_mm=1.6 + layers * (um - 35.0) * 1e-3, copper_um=um)
    p.board.h_top = p.board.h_bottom = 500.0
    p.board.h_side = None
    c = side / 2.0
    p.add_full_copper(layers=None)
    p.add_heater(1, 5.0, rect=(c - 5, c - 5, c + 5, c + 5), name="U")
    return p


def one(layers, um, cell, side=100.0):
    """!
    @brief Build and solve one case in this process.
    @param layers Copper layers, count.
    @param um Copper thickness, um.
    @param cell Cell, mm.
    @param side Side of the board, mm.
    @return dict with the unknowns, slabs, seconds, growth and peak in bytes and the estimate of the law without the base.
    """
    p = build(layers, um, side)
    from pcbthermal import memory, solid3d
    n, ns, nx, ny = solid3d.unknowns(p, cell)
    start = memory.resident_bytes()
    t0 = time.time()
    with solid3d.size_limit(10_000_000):
        net = solid3d.Solid(p, cell)
        net.solve()
    sec = time.time() - t0
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)
    est = memory.estimate_bytes("solid3d", n, nx * ny, base=0.0)
    return {"layers": layers, "um": um, "cell": cell, "n": n, "slabs": ns, "seconds": sec, "growth": peak - start, "estimate": est, "ratio": (peak - start) / est}


def main(argv=None):
    """!
    @brief List or run the cases, each in a fresh process, and print the table.
    @param argv Arguments (default sys.argv[1:]).
    @return int exit code.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--dry-run", action="store_true", help="list the cases and their unknowns; run nothing")
    ap.add_argument("--heavy", action="store_true", help="include the heavy cases")
    ap.add_argument("--one", nargs=3, metavar=("LAYERS", "UM", "CELL"), help="run one case and print one JSON line")
    a = ap.parse_args(argv)
    if a.one:
        print(json.dumps(one(int(a.one[0]), float(a.one[1]), float(a.one[2]))))
        return 0
    cases = LIGHT + (HEAVY if a.heavy else [])
    sys.path.insert(0, ROOT)
    from pcbthermal import solid3d
    for layers, um, cell, side in cases:
        n, ns, _, _ = solid3d.unknowns(build(layers, um, side), cell)
        if a.dry_run:
            print(f"would run {layers} layers, {um:g} um, cell {cell} mm: {n} unknowns, {ns} slabs{'  (heavy)' if (layers, um, cell, side) in HEAVY else ''}")
            continue
        out = subprocess.run([sys.executable, os.path.abspath(__file__), "--one", str(layers), str(um), str(cell)], capture_output=True, text=True)
        if out.returncode != 0:
            print(f"{layers} layers {um:g} um {cell} mm: FAILED {out.stderr.strip().splitlines()[-1:]}")
            continue
        r = json.loads(out.stdout.strip().splitlines()[-1])
        print(f"{r['layers']} layers {r['um']:5g} um cell {r['cell']:4.2f} mm n={r['n']:8d} slabs {r['slabs']:3d} solve {r['seconds']:6.1f} s growth {r['growth'] / 1e9:5.2f} GB "
              f"= {r['growth'] / r['n']:6.0f} B/unknown, estimate {r['estimate'] / 1e9:5.2f} GB, measured/estimate {r['ratio']:.2f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
