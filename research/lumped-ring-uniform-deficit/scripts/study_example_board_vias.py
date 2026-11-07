#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_example_board_vias.py
@brief The example board (100 x 80 mm class, several parts, vias) with the original 9 vias and with 5 x 5, 7 x 7 and 20 x 20 arrays: via effect and hottest temperature, program against the proposed first ring, FVM at 0.25 mm as the reference.
@details The boards are those of research/lumped-analytic-vias (`study_real_boards.example`, open and copper-filled vias). The via effect is E = T_max(no vias) - T_max(vias). This is the one place
         where the proposal changes a board of the via studies (a large board), so the two are compared on E and on T_max. Run from the repository root:
         QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-ring-uniform-deficit/scripts/study_example_board_vias.py (about 3 minutes, peak under 1.5 GB).
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "lib"))
for sub in ("lumped-via-groups/lib", "lumped-analytic-vias/lib", "lumped-analytic-vias/scripts", "point-via-convergence/lib"):
    sys.path.insert(0, str(RESEARCH / sub))

import runner as R  # noqa: E402
import harness as hz  # noqa: E402
import program_cases as pc  # noqa: E402
import study_real_boards as srb  # noqa: E402
from pcbthermal import SolverOptions, simulate  # noqa: E402

BOARDS = [("9 vias at 3.5 mm", 0, 3.5), ("5 x 5 at 1.2 mm", 5, 1.2), ("7 x 7 at 1.0 mm", 7, 1.0), ("20 x 20 at 1.0 mm", 20, 1.0)]


def tmax(p, model, cell, cand=None):
    """!
    @brief Maximum temperature of a model.
    @param p Problem.
    @param model Model key.
    @param cell Cell in mm.
    @param cand Key of runner.CANDIDATES for the Lumped.
    @return float degC.
    """
    if cand:
        R.LL.configure(*R.CANDIDATES[cand])
    return simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max


def main():
    """!
    @brief Print the table and write out/example_board_vias.json.
    @return None.
    """
    pc.load_libraries()
    rows = []
    cache_path = R.OUT / "example_vias_fvm.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    print("| board | fill | FVM 0.25: E (K) / T_max | program: E error / T_max error | proposal: E error / T_max error |")
    print("| :-- | :-- | :-- | :-- | :-- |")
    for label, n, pitch in BOARDS:
        for fill in (0.0, 385.0):
            p = srb.example(fill, n, pitch)
            q0 = hz.no_vias(p)
            key = f"{n}|{pitch}|{fill}"
            if key not in cache:
                cache[key] = [tmax(q0, "fvm", 0.25), tmax(p, "fvm", 0.25)]
                R.OUT.mkdir(exist_ok=True)
                cache_path.write_text(json.dumps(cache))
            f0, f1 = cache[key]
            e_ref = f0 - f1
            out = {}
            for c in ("program", R.PROPOSAL):
                l0, l1 = tmax(q0, "lumped", 0.5, c), tmax(p, "lumped", 0.5, c)
                out[c] = (100 * ((l0 - l1) / e_ref - 1), 100 * ((l1 - 25) / (f1 - 25) - 1))
            rows.append({"board": label, "fill": fill, "E_ref": e_ref, "T_ref": f1, **{c: out[c] for c in out}})
            print(f"| {label} | {'Cu' if fill else 'open'} | {e_ref:.2f} / {f1:.2f} | {out['program'][0]:+.1f} % / {out['program'][1]:+.1f} % | {out[R.PROPOSAL][0]:+.1f} % / {out[R.PROPOSAL][1]:+.1f} % |", flush=True)
    (R.OUT / "example_board_vias.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
