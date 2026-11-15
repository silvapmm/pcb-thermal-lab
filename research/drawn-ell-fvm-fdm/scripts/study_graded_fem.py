#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_graded_fem.py
@brief Question: what does the hottest point of the `drawn_ell` board converge to when the mesh is refined only around the bare-laminate corner of the part?
@details Same board and tool as `study_independent_fem.py` (hand-written hexahedral FEM of `research/independent-fem-edge/lib`, copper resolved), but the plan mesh is graded:
         fine size `hf` in the window 9 to 13 mm (the part is 8 to 12 mm, the inner corner of the L is at 10.8 mm), growing by 1.3 per element to 1 mm elsewhere. This is the
         refinement that the uniform meshes of the program cannot afford. One solve at a time, each guarded under 2 GB.
         Run from the repository root: `nice -n 10 .venv/bin/python research/drawn-ell-fvm-fdm/scripts/study_graded_fem.py [hf1,hf2,...]` (default 0.25,0.125,0.0625,0.03125).
"""
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
for sub in ("research/drawn-copper-faces/lib", "research/independent-fem-edge/lib"):
    sys.path.insert(0, str(REPO / sub))
import board              # noqa: E402
import cases              # noqa: E402
import mesh2d             # noqa: E402
import dc_cases as D      # noqa: E402


def graded_board(hf, window=(9.0, 13.0), hmax=1.0):
    """!
    @brief The finite-element board of the L case with a fine plan mesh in a window.
    @param hf Fine plan size in mm.
    @param window Fine window (a, b) in mm, in both directions.
    @param hmax Largest plan size in mm.
    @return board.Board.
    """
    c = D.case("ell", 200.0, 2)
    brk = {0.0, D.A, 8.0, 12.0}
    for rs in c["copper"]:
        for (x0, y0, x1, y1) in rs:
            brk.update((x0, x1, y0, y1))
    xn = cases.axis(D.A, sorted(brk), [window], hf, 1.3, hmax)
    plan = mesh2d.tensor(xn, xn)
    cu = [None if (len(rs) == 1 and rs[0] == (0.0, 0.0, D.A, D.A)) else [cases.rect(*r) for r in rs] for rs in c["copper"]]
    return board.Board(plan, c["layers"], board_t=1.6e-3, k_xy=0.9, k_z=0.3, n_gap=12, h_top=10.0, h_bottom=10.0, h_side=200.0, copper=cu,
                       heaters=[(cases.rect(8, 8, 12, 12), 1.0)])


def main():
    """!
    @brief Solve the sizes given.
    @return None.
    """
    hfs = [float(x) for x in (sys.argv[1] if len(sys.argv) > 1 else "0.25,0.125,0.0625,0.03125").split(",")]
    for hf in hfs:
        t0 = time.time()
        b = graded_board(hf)
        m, _ = b.build()
        n = m.nodes.shape[0]
        if n * (46000.0 if n <= 30000 else 8500.0) / 1e9 > 2.0:
            print(f"hf {hf} mm: {n} nodes, refused (estimated above 2 GB)", flush=True)
            continue
        r = b.solve(direct_max=30000)
        print(f"hf {hf:7.4f} mm  nodes {r['n']:7d}  heater mean {r['heater_mean']:8.3f} K  hottest node {r['tmax']:8.3f} K  balance {r['balance']:.3e}  "
              f"{r['solver']} peak {r['peak_gb']:.2f} GB  {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main()
