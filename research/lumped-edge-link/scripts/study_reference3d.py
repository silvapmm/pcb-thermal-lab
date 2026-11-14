#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_reference3d.py
@brief The converged independent 3D reference for the near-edge deficit: FVM, Lumped (program and variants) against `tests/helpers/layered3d.py` on a 40 x 40 mm board.
@details Two layers of full copper, a 6 mm part, insulated sides (h_side 0, the 3D solver has no edge film), FR-4 isotropic 0.3 W/mK in the program too. Edge cases use the symmetry plane
         (half board), corner cases the whole board, both at 0.5 and 0.25 mm. The converged value is the Richardson extrapolation of the two cells (first order: the part's surface node
         sits half a cell below the film). A run at 0.125 mm of the edge cases (307 200 unknowns) peaked at 4.9 GB resident, above the 3 GB kept here: it was done for gap 0, 1, 2 and
         5 mm and moved the peak by at most 0.003 K (README 4.1), so 0.25 mm is converged to 0.01 % on the peak. Heavy (hundreds of thousands of unknowns): run one at a time, under 3 GB resident.
         Writes out/reference3d.json. Run from the repository root: QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-edge-link/scripts/study_reference3d.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import boards as B  # noqa: E402
import ref3d  # noqa: E402
import variants as V  # noqa: E402

VARIANTS = ("program", "expo_peak", "img", "pot", "first")
SIDE = 6.0


def board(gap, place):
    """!
    @brief The 40 x 40 mm board with isotropic FR-4 and insulated sides.
    @param gap Gap from the part to the side (mm).
    @param place "edge" or "corner".
    @return (Problem, centre).
    """
    pos = (gap + SIDE / 2, 20.0 if place == "edge" else gap + SIDE / 2)
    p = B.board(40.0, 40.0, SIDE, pos, h_side=0.0)
    p.board.materials.k_fr4_inplane = p.board.materials.k_fr4_through
    return p, pos


def main():
    """!
    @brief Run the reference cases.
    @return None.
    """
    rows = []
    done = {(r["place"], r["gap"]): r for r in (json.loads((B.OUT / "reference3d.json").read_text()) if (B.OUT / "reference3d.json").exists() else [])}   # the 3D solves are kept
    cases = [("edge", g) for g in (0.0, 1.0, 2.0, 5.0, 10.0)] + [("corner", g) for g in (0.0, 2.0, 5.0)] + [("centre", 0.0)]
    for place, gap in cases:
        p, pos = board(gap, place)
        if place == "centre":
            pos = (20.0, 20.0)
            p = B.board(40.0, 40.0, SIDE, pos, h_side=0.0)
            p.board.materials.k_fr4_inplane = p.board.materials.k_fr4_through
        cells = (0.5, 0.25)
        t3 = {}
        for dx in (cells if (place, gap) not in done else ()):
            r = ref3d.solve(p, pos, SIDE, "edge" if place == "edge" else "corner", dx)   # a centred part uses the whole board as a corner would
            t3[dx] = r
            print(place, gap, dx, r, flush=True)
        if (place, gap) in done:
            t3 = done[(place, gap)]["3d"]
            conv = done[(place, gap)]["3d_converged"]
        else:
            fine, coarse = cells[-1], cells[-2]
            conv = {k: 2 * t3[fine][k] - t3[coarse][k] for k in ("peak", "mean")}
        f_mean, f_peak, _ = B.part_read(p, "fvm", 0.5)
        f25 = B.part_read(p, "fvm", 0.25)
        row = {"place": place, "gap": gap, "3d": {str(k): v for k, v in t3.items()}, "3d_converged": conv, "fvm_0.5": [f_mean, f_peak], "fvm_0.25": list(f25[:2])}
        for v in VARIANTS:
            V.install(v)
            m, x, _ = B.part_read(p, "lumped", 0.5)
            row[v] = [m, x]
        rows.append(row)
        print(place, gap, "conv", conv, "fvm", f_mean, f_peak, flush=True)
        B.OUT.mkdir(exist_ok=True)
        (B.OUT / "reference3d.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
