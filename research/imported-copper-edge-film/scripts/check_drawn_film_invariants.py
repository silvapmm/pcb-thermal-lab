#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_drawn_film_invariants.py
@brief Invariants of the centroid edge film on drawn layers: heat balance, symmetry of K, no positive off-diagonal entry, exact constant field for h_side 10 to 1e5, the time simulation ends at the steady value, and the time and memory on a 200 x 150 mm outline board.
@details Boards of `study_drawn_film.py` (turned 20 mm square, T, L, 4 layers, mixed) at 1 and 0.5 mm. Run: `.venv/bin/python research/imported-copper-edge-film/scripts/check_drawn_film_invariants.py`.
"""

import os
import resource
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np                                                              # noqa: E402

import study_drawn_film as sd                                                   # noqa: E402
from pcbthermal import Problem, fvm                                             # noqa: E402


def main():
    """!
    @brief Print the invariants.
    @return None.
    """
    worst = dict(bal=0.0, sym=0.0, off=0.0, const=0.0)
    for name in ("sq_in", "sq_wall", "sq_4l", "T_wall", "L_in", "sq_stripes", "mixed_4l"):
        spec = sd.CASES[name]
        for h in (10.0, 200.0, 1e3, 1e5):
            for cell in (1.0, 0.5):
                p = sd.build(spec, h, 22.5, 0.3 * cell, spec.get("imported", ()))
                n = int(round(p.board.width * 1e3 / cell))
                net = fvm.Network(p, n, n)
                K = net.K.tocsr()
                off = K.copy()
                off.setdiag(0)
                off.eliminate_zeros()
                worst["sym"] = max(worst["sym"], abs(K - K.T).max() / abs(K).max())
                worst["off"] = max(worst["off"], float(off.max()))
                # constant field: K applied to a uniform vector must equal the ambient conductance (the film change goes into g_amb)
                worst["const"] = max(worst["const"], np.abs(np.asarray(K.sum(axis=1)).ravel() - net.g_amb.ravel()).max() / net.g_amb.max())
                if h <= 1e3:
                    worst["bal"] = max(worst["bal"], abs(fvm.solve_steady(p, cell_mm=cell).balance_error))
    print("worst over the boards:", {k: "%.1e" % v for k, v in worst.items()})
    # time simulation of the turned T: step response ends at the steady value
    p = sd.build(sd.CASES["T_wall"], 200.0, 22.5, 0.0)
    ss = fvm.solve_steady(p, cell_mm=1.0)
    tr = fvm.solve_transient(p, t_end=20000.0, cell_mm=1.0)
    print("turned T, steady hottest %.4f K, end of the time simulation %.4f K" % (ss.t_max, float(tr.t_max[-1])))
    # time and memory on a big outline board
    q = Problem.new(200, 150, 2, h_side=50.0)
    q.set_outline([[5, 0], [195, 10], [200, 140], [100, 150], [0, 120]])
    q.add_zone(1, polygon=[[10, 10], [190, 15], [190, 135], [10, 115]])
    q.add_zone(2, polygon=[[10, 10], [190, 15], [190, 135], [10, 115]])
    q.add_heater(1, 5.0, rect=(90, 60, 100, 70), name="U")
    for cell in (1.0, 0.5):
        nx, ny = int(200 / cell), int(150 / cell)
        t0 = time.time()
        net = fvm.Network(q, nx, ny)
        t1 = time.time() - t0
        t0 = time.time()
        r = fvm.solve_steady(q, cell_mm=cell)
        print("200 x 150 mm outline, cell %g: network %.2f s, solve %.1f s, balance %.1e, peak RSS %.2f GB" % (cell, t1, time.time() - t0, r.balance_error, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9))


if __name__ == "__main__":
    main()
