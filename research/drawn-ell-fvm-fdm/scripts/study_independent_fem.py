#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_independent_fem.py
@brief Question: does the hottest point of the `drawn_ell` board converge with the mesh, and to what, in the independent finite-element tool of the research (not the program's FEM)?
@details Uses `research/drawn-copper-faces/lib/dc_fem.py` (the hand-written hexahedral FEM of `research/independent-fem-edge/lib`, copper resolved, edge film 200 W/m2K, the same
         board as the harness board `drawn_ell`: 20 mm square, 2 layers, top copper an L, bottom copper 1.2 mm inside the wall, 4 mm part with 1 W, h = 10 W/m2K). Prints, per plan
         element size, the heater mean and the hottest node. One solve at a time, each guarded under 2 GB by dc_fem.
         Run from the repository root: `nice -n 10 .venv/bin/python research/drawn-ell-fvm-fdm/scripts/study_independent_fem.py [hf1,hf2,...]` (default 1,0.5,0.25,0.125).
"""
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "drawn-copper-faces" / "lib"))
import dc_cases as D      # noqa: E402
import dc_fem             # noqa: E402


def main():
    """!
    @brief Solve the L board at the plan sizes given.
    @return None.
    """
    hfs = [float(x) for x in (sys.argv[1] if len(sys.argv) > 1 else "1,0.5,0.25,0.125").split(",")]
    for hf in hfs:
        t0 = time.time()
        r = dc_fem.solve(D.case("ell", 200.0, 2), hf)
        if r is None:
            print(f"hf {hf} mm refused (above 2 GB)", flush=True)
            continue
        print(f"hf {hf:6.3f} mm  nodes {r['n']:7d}  heater mean {r['heater_mean']:8.3f} K  hottest node {r['tmax']:8.3f} K  balance {r['balance']:.2e}  "
              f"{r['solver']} peak {r['peak_gb']:.2f} GB  {time.time() - t0:.1f} s", flush=True)


if __name__ == "__main__":
    main()
