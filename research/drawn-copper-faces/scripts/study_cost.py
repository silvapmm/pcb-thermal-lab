#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cost.py
@brief The cost (seconds and peak resident memory) of reading the zones of a drawn board as an import, on a board the size of a real one.
@details A 100 x 75 mm board, 4 layers, copper planes inside a 1.5 mm inset on the inner layers, stripes (1.2 mm every 2.4 mm) with a 20 mm pad on the top layer, bottom plane, six 6 mm
         heaters (1 W each). Each run is a fresh process (peak memory is `ru_maxrss`): `study_cost.py one <fvm|fdm> <program|patched> <cell mm>` prints one line; `study_cost.py all` runs the
         grid in subprocesses (one at a time). Memory in MB (macOS reports bytes).
"""
import os
import resource
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))


def big():
    """!
    @brief The big board.
    @return Problem.
    """
    from pcbthermal import Problem
    p = Problem.new(100.0, 75.0, 4, h_side=10.0)
    p.board.h_top = p.board.h_bottom = 10.0
    for l in (2, 3, 4):
        p.add_zone(l, polygon=[[1.5, 1.5], [98.5, 1.5], [98.5, 73.5], [1.5, 73.5]])
    y = 1.5
    while y < 73.5 - 1e-9:
        p.add_zone(1, polygon=[[1.5, y], [98.5, y], [98.5, min(y + 1.2, 73.5)], [1.5, min(y + 1.2, 73.5)]])
        y += 2.4
    p.add_zone(1, polygon=[[40, 27.5], [60, 27.5], [60, 47.5], [40, 47.5]])
    for i, (cx, cy) in enumerate([(20, 20), (50, 20), (80, 20), (20, 55), (50, 37.5), (80, 55)]):
        p.add_heater(1, 1.0, polygon=[[cx - 3, cy - 3], [cx + 3, cy - 3], [cx + 3, cy + 3], [cx - 3, cy + 3]], name=f"U{i}")
    return p


def one(model, mode, cell):
    """!
    @brief Run one steady solve in this process and print the time and the peak memory.
    @param model 'fvm' or 'fdm'.
    @param mode 'program' or 'patched'.
    @param cell Cell in mm.
    @return None.
    """
    import patched as P
    from pcbthermal import fvm, fdm
    p = big()
    t0 = time.time()
    if mode == "patched":
        with P.use("faces"):
            r = (fvm if model == "fvm" else fdm).solve_steady(p, cell_mm=cell)
    else:
        r = (fvm if model == "fvm" else fdm).solve_steady(p, cell_mm=cell)
    dt = time.time() - t0
    mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
    print(f"{model} {mode} {cell:g} mm: {dt:.1f} s, peak {mb:.0f} MB, hottest rise {r.t_max - r.ambient:.3f} K, balance {r.balance_error:.1e}")


def main():
    """!
    @brief Dispatch.
    @return None.
    """
    if sys.argv[1] == "one":
        one(sys.argv[2], sys.argv[3], float(sys.argv[4]))
        return
    for model in ("fvm", "fdm"):
        for cell in (2.0, 1.0, 0.5):
            for mode in ("program", "patched"):
                subprocess.run([sys.executable, __file__, "one", model, mode, str(cell)], check=False)


if __name__ == "__main__":
    main()
