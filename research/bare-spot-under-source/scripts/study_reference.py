#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_reference.py
@brief Q0: how good is the resolved 3D reference? Closed forms, energy balance, and its convergence with the cell and the sub-slabs on the bare-window boards.
@details Question answered: can the peak printed by lib/resolved3d.py be used as the truth to about 0.5 %? Prints (1) the 1D column against the series circuit, (2) the mean source rise of a 4 x 4 mm
         source on a 10 x 10 x 1 mm isotropic plate against Eq. 27 of Muzychka, Culham and Yovanovich (2003) at 0.2, 0.1 and 0.05 mm, (3) the peak and mean of the 6 mm window board of
         two layers at 0.5, 0.25 and 0.125 mm and 8, 16 sub-slabs (and 24 at 0.125), with the energy balance of each run, (4) the same for the 4 layer typical stack-up with a 6 mm window,
         (5) the agreement of the reference with the independent solver of tests/helpers/layered3d.py (isotropic, one window) as a second opinion.
         Run from the repository root: .venv/bin/python research/bare-spot-under-source/scripts/study_reference.py; out/reference.txt.
"""

import _bootstrap  # noqa: F401  (import paths)

import sys
import time

from _bootstrap import HERE, OUT

import cases as C                                                           # noqa: E402
import closed_forms as cf                                                   # noqa: E402
import resolved3d as r3                                                     # noqa: E402

sys.path.insert(0, str(HERE.parents[1] / "tests" / "helpers"))
import layered3d as L3                                                      # noqa: E402

lines = []


def say(s):
    """!
    @brief Print and keep a line.
    @param s Text.
    @return None.
    """
    print(s, flush=True)
    lines.append(s)


def main():
    """!
    @brief Run the checks.
    @return None.
    """
    n, dx = 6, 1e-3
    r = r3.solve(dx, n, n, [(35e-6, 385.0, 385.0, 1), (0.5e-3, 0.9, 0.3, 5), (35e-6, 385.0, 385.0, 1)], (0, 0, n * dx, n * dx), 2.0, 10.0, 200.0)
    ex = cf.column_rise(2.0, (n * dx) ** 2, [(35e-6, 385.0), (0.5e-3, 0.3), (35e-6, 385.0)], 10.0, 200.0)
    say(f"(1) 1D column: solver {r['max']:.6f} K, series circuit {ex:.6f} K, balance {r['balance']:.9f}")

    ex = cf.plate_mean_rise(10e-3, 10e-3, 4e-3, 4e-3, 5e-3, 5e-3, 1e-3, 0.3, 500.0, 1.0)
    for d, ns in ((0.2, 10), (0.1, 20), (0.05, 20)):
        m = int(round(10 / d))
        t = time.time()
        r = r3.solve(d * 1e-3, m, m, [(1e-3, 0.3, 0.3, ns)], (3e-3, 3e-3, 7e-3, 7e-3), 1.0, 0.0, 500.0)
        say(f"(2) plate 10x10x1 mm, source 4x4, k 0.3, h_bottom 500: cell {d} mm, {ns} slabs: mean {r['mean']:.5f} K, Eq. 27 {ex:.5f} K, error {100 * (r['mean'] / ex - 1):+.3f} %, balance {r['balance']:.9f} ({time.time() - t:.0f} s)")

    for label, kw, w in (("2 layers 1.6 mm, window 6 mm", dict(layers=2), 6), ("4 layers typical, window 6 mm", dict(layers=4, stack="template"), 6), ("2 layers 1.6 mm, window 2 mm", dict(layers=2), 2)):
        c = C.Case("x", window=C.centred_window(w), **kw)
        for dxm, ns in ((0.5, 8), (0.5, 16), (0.25, 8), (0.25, 16), (0.125, 8), (0.125, 12)):
            if kw.get("layers") == 4 and dxm == 0.125:
                continue                                                      # 4 layers at 0.125 mm: too large for the machine; the 2 layer rows show the trend
            t = time.time()
            q = C.reference(c, dxm, ns)
            say(f"(3) {label}: cell {dxm} mm, {ns} slabs/gap: peak {q['max']:.2f} K, mean {q['mean']:.2f} K, unknowns {q['nunknowns']}, balance {q['balance']:.9f} ({time.time() - t:.0f} s)")

    # Second opinion: the independent solver of tests/helpers (isotropic slabs, no anisotropy) on a bare window, same geometry as case (3) with isotropic laminate
    c = C.Case("iso", layers=2, window=C.centred_window(6), k_inplane=0.3, k_through=0.3)
    p = C.problem(c)
    nb = C.board_numbers(p)
    nq, dxq = 60, 0.25e-3
    masks = r3.window_masks(nq, nq, dxq, 2, (0, 0, 3e-3, 3e-3))
    kc, kl = nb["k_cu"], 0.3
    slabs = [(nb["t_cu"][0], kl + masks[0] * (kc - kl), 1), (nb["gaps"][0], kl, 8), (nb["t_cu"][1], kc, 1)]
    a = L3.solve(dxq, nq, nq, slabs, (0, 0, 3e-3, 3e-3), 0.25, nb["h_top"], nb["h_bottom"], film_under_source=True)
    b = r3.solve(dxq, nq, nq, r3.build_slabs(2, masks, kc, nb["gaps"], nb["t_cu"], 8, kl, kl), (0, 0, 3e-3, 3e-3), 0.25, nb["h_top"], nb["h_bottom"])
    say(f"(5) isotropic window board: tests/helpers/layered3d.py cell-centre max {a['cell_max_source']:.4f} K, mean {a['cell_mean_source']:.4f} K; resolved3d surface max {b['max']:.4f} K, mean {b['mean']:.4f} K "
        f"(the face value is above the cell-centre value by the half-cell drop)")
    (OUT / "reference.txt").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
