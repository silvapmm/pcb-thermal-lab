#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_run_suite.py
@brief Question: what are the numbers of one revision of the program on the regression boards? Runs the five models at 2, 1 and 0.5 mm (steady state, a short transient, the SOR) and writes a result set.
@details Usage, from the repository root:

         .venv/bin/python releases/regression-harness/scripts/study_run_suite.py --label rc                    # the tree you are in -> out/rc.json
         .venv/bin/python releases/regression-harness/scripts/study_run_suite.py --program-root /path/to/tree --label v2.4.4

         `--program-root` is a folder that contains the `pcbthermal` package (the repository, or an extracted `git archive`; see `study_baseline_release.py`). The program under test is
         the only `pcbthermal` that is imported (the script refuses otherwise). `--quick` runs the 2 mm cell only. The output is `out/<label>.json` (git-ignored). Solve times are
         stored for information and never compared. A run can be resumed with `--resume` (finished boards are kept).
"""

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "lib"))

import regress_boards as B                                                  # noqa: E402
import regress_harness as H                                                 # noqa: E402


def main(argv=None):
    """!
    @brief Parse the command line and run the suite.
    @param argv List of arguments (default: sys.argv[1:]).
    @return int exit code (0).
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--program-root", default=str(B.REPO), help="folder that contains the pcbthermal package to test (default: this repository)")
    ap.add_argument("--label", default="rc", help="name of the result set and of the output file (default rc)")
    ap.add_argument("--out", default=None, help="output JSON (default out/<label>.json in this folder)")
    ap.add_argument("--cells", nargs="+", type=float, default=list(H.CELLS), help="cell sizes in mm (default 2 1 0.5)")
    ap.add_argument("--models", nargs="+", default=list(H.MODELS), choices=list(H.MODELS))
    ap.add_argument("--boards", nargs="+", default=None, help="board names (default all): " + ", ".join(B.board_names()))
    ap.add_argument("--examples-dir", default=None, help="folder of the example files (default examples/ of this repository, the same for every revision)")
    ap.add_argument("--max-unknowns", type=int, default=H.MAX_UNKNOWNS, help="FVM and FDM above this many unknowns are skipped")
    ap.add_argument("--solid-cap", type=int, default=H.SOLID_CAP, help="the 3D solid above this many unknowns is skipped")
    ap.add_argument("--quick", action="store_true", help="2 mm cell only")
    ap.add_argument("--no-transients", action="store_true")
    ap.add_argument("--no-sor", action="store_true")
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out) if a.out else ROOT / "out" / f"{a.label}.json"
    data = H.run_suite(a.program_root, out, a.label, boards=a.boards, models=tuple(a.models), cells=(2.0,) if a.quick else tuple(a.cells), examples_dir=a.examples_dir,
                       max_unknowns=a.max_unknowns, solid_cap=a.solid_cap, transients=not a.no_transients, sor=not a.no_sor, resume=a.resume, log=print)
    n_ok = sum(1 for r in data["records"] if r["status"] == "ok")
    print(f"\n{a.label}: program {data['program']['version']} from {data['program']['root']}")
    print(f"{len(data['records'])} runs: {n_ok} ok, {sum(1 for r in data['records'] if r['status'] == 'skipped')} skipped, "
          f"{sum(1 for r in data['records'] if r['status'] == 'error')} failed; written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
