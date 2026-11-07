#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_error_vs_reference.py
@brief Question: how far is each model from the independent layered 3D solver on the four reference boards, before (v2.4.4) and after (the release candidate)?
@details Usage, from the repository root (after `study_references.py`, `study_baseline_release.py` and `study_run_suite.py`):

         .venv/bin/python research/release-regression-245/scripts/study_error_vs_reference.py out/v2.4.4.json out/rc.json

         Prints and writes `out/error_vs_reference.md`: one row per board, cell and model with the reference rise, the relative error of the rise in both sets and the change in
         percentage points. The reference is solved on the same cell size as the model. The boards are the ones with a square source, one conductivity of laminate and insulated
         sides (`regress_boards.REFERENCE_SPECS`); the other boards have no independent reference here. Skipped runs show n/a.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "lib"))

import regress_classify as C                                                # noqa: E402
import regress_refsolve as R                                                # noqa: E402


def main(argv=None):
    """!
    @brief Build the before/after error table.
    @param argv List of arguments (default: sys.argv[1:]).
    @return int exit code (0; 2 when the reference file is missing).
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("base")
    ap.add_argument("new")
    ap.add_argument("--references", default=str(ROOT / "out" / "references.json"))
    a = ap.parse_args(argv)
    if not Path(a.references).exists():
        print(f"{a.references} does not exist: run study_references.py first")
        return 2
    refs = json.loads(Path(a.references).read_text(encoding="utf-8"))
    base, new = C.load_set(a.base), C.load_set(a.new)
    text = "# Error of the rise against the independent layered solver\n\n" + R.before_after_table(base, new, refs)
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out" / "error_vs_reference.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
