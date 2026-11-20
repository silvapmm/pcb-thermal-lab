#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_compare_c7.py
@brief Row C7 of the FEM campaign (validation 56.7): the via effect of the program's FEM, FVM, FDM and 3D solid on the boards of `research/independent-fem-extensions` study 1 (a 10 x 10 mm
       four-layer plate with a cooled edge, one 0.3 mm via 0.16 and 3 mm from the wall, and a 3 x 3 array), against the independent finite-element value of that study.
@details The via effect E is the hottest rise without the via minus the hottest rise with it (K), for a hollow barrel (`fill_k` 0) and a copper core (`fill_k` 385 W/mK), at the
         edge film 200 and 1000 W/m2K and the cells 1, 0.5 and 0.25 mm. The reference values are the finest finite-element values of `research/independent-fem-extensions` README
         8.1 (conforming hexahedral elements of the independent tool; plan 0.05 mm, the array 0.1 mm), QUOTED from that table and not re-run here (the tool lives in its own
         environment and its outputs are not in the repository). The boards are built by `research/strong-edge-laminate/lib/prog.py` and the via placement of
         `study_hollow_barrel.py::prog`. The Lumped and Analytic are not run at the three cells (they have no cell), see that README for them.
         Run from the repository root: `.venv/bin/python -u releases/2.9.0/fem-campaign/scripts/study_compare_c7.py` (a few minutes, under 2 GB).
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research" / "strong-edge-laminate" / "lib"))
LABEL = {"fvm": "FVM", "fdm": "FDM", "solid3d": "3D solid", "fem": "FEM"}
# finest independent finite-element via effect E in K (research/independent-fem-extensions README 8.1): (d, h_side) -> (open, copper); d None is the 3 x 3 array
REFERENCE = {(0.16, 200.0): (0.9852, 1.5759), (3.0, 200.0): (1.4340, 2.5288), (0.16, 1000.0): (0.4309, 0.6821), (3.0, 1000.0): (0.6942, 1.2249),
             (None, 200.0): (5.0909, 6.2833), (None, 1000.0): (2.6317, 3.2928)}


def make(prog, h, d, fk):
    """!
    @brief The board of the study, with or without vias.
    @param prog The `prog` module of research/strong-edge-laminate/lib.
    @param h Edge film in W/m2K.
    @param d Distance of the via from the wall in mm (None: the 3 x 3 array).
    @param fk Fill conductivity of the barrel in W/mK, or None for no via.
    @return Problem.
    """
    p = prog.board(h, None)
    if fk is None:
        return p
    pts = [(10.0 - d, 5.0)] if d is not None else [(x, y) for x in (6.0, 7.0, 8.0) for y in (4.0, 5.0, 6.0)]
    for x, y in pts:
        p.add_via(x, y, 0.3, fill_k=fk)
    return p


def main():
    """!
    @brief Print the via effect of every model against the independent value.
    @return None.
    """
    import logging
    import prog
    from pcbthermal import SolverOptions, simulate
    logging.disable(logging.WARNING)
    import pcbthermal
    tree = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"tree {tree}, program {pcbthermal.__version__}; E = rise without the via minus rise with it (hottest column), K; % = against the independent finite-element value (quoted)")
    for core, fk, col in (("hollow barrel (fill_k 0)", 0.0, 0), ("copper core (fill_k 385)", 385.0, 1)):
        print(f"\n### {core}")
        print("| case | h_side | independent E K | cell mm | " + " | ".join(f"{LABEL[m]} E K (%)" for m in LABEL) + " |")
        print("| :-- | --: | --: | --: | " + " | ".join("--:" for _ in LABEL) + " |")
        for (d, h), ref in REFERENCE.items():
            for cell in (1.0, 0.5, 0.25):
                row = []
                for m in LABEL:
                    try:
                        o = SolverOptions(models=(m,), cell_mm=cell)
                        base = simulate(make(prog, h, d, None), o).results[m].t_max
                        with_via = simulate(make(prog, h, d, fk), o).results[m].t_max
                        e = base - with_via
                        row.append(f"{e:.4f} ({100 * (e / ref[col] - 1):+.1f})")
                    except Exception as exc:
                        row.append(f"not run: {type(exc).__name__}"[:40])
                name = "3 x 3 array" if d is None else f"via {d:g} mm from the wall"
                print(f"| {name} | {h:g} | {ref[col]:.4f} | {cell:g} | " + " | ".join(row) + " |", flush=True)


if __name__ == "__main__":
    main()
