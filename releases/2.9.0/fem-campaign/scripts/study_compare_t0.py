#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_compare_t0.py
@brief Row 57.0 of the FEM campaign (validation 57, first line): the published transient case NAFEMS T3 reproduced on this tree (exact series, method of lines, the program's FEM at
       several meshes and steps, the published mesh results of MOOSE and Abaqus) and the plate with held edges against the exact double series in the FVM, FDM and Analytic.
@details It re-runs, unchanged, parts A and B of `research/transient-published-case/scripts/study_t3_and_plate.py` (the exact series and the helper `lib/exact1d.py` import nothing
         from the program), so the numbers of the first line of validation 57 are printed by the tree that ships and not quoted. Sources by key of
         `research/theory/BIBLIOGRAPHY.md`: [NAFEMS-T3] (the primary publication was not obtained), [MOOSE-T3], [Abaqus-T3], [Altair-T3], [Wolfram-T3].
         Run from the repository root: `.venv/bin/python -u releases/2.9.0/fem-campaign/scripts/study_compare_t0.py` (about 3 min, light; output also in out/t0.txt).
"""

import importlib.util
import io
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
STUDY = ROOT / "research" / "transient-published-case" / "scripts" / "study_t3_and_plate.py"


def main():
    """!
    @brief Run parts A and B of the published-case study and print them with the tree.
    @return None.
    """
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("study_t3_and_plate", STUDY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tree = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    buf = io.StringIO()
    with redirect_stdout(buf):
        print(f"tree {tree}")
        print("== Part A: NAFEMS T3 (36.60 degC at x = 0.08 m, t = 32 s)")
        mod.part_a(False)
        print("== Part B: plate with held edges and a power step, centre temperature against the exact double series")
        mod.part_b(False)
    text = buf.getvalue()
    out = HERE.parent / "out"
    out.mkdir(exist_ok=True)
    (out / "t0.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
