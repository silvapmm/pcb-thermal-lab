#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file run_all.py
@brief Runs the tests of the folder and the six studies in order, one command, writing the printed tables to out/*.txt.
@details Order: the tests of the folder (`tests/test_zoned_lumped.py`), study 6 (invariants, cheap, to fail early), study 5 (footprint potentials), study 1 (zones on the 2.4.5 well, the long one when the
         references are not cached), study 3 (raster), study 4 (edge and off-centre), study 2 (transient), then the figures. Each study is run as its own process from the repository root; the output of
         each goes to `out/<name>.txt`. Nothing here edits the program. The machine must be quiet: the fine-grid references and the 3D-free layered solves take hours on a busy one.
Usage: python research/lumped-zones-adoption/scripts/run_all.py [--quick] [--procs N] [--old-cache] [--skip-tests]   (from the repository root; use .venv/bin/python)
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(FOLDER))
OUT = os.path.join(FOLDER, "out")

STUDIES = [("study_invariants", []), ("study_footprint_potential", []), ("study_zones_on_245", ["--procs"]), ("study_raster", ["--procs"]),
           ("study_edge_and_offcentre", ["--procs"]), ("study_transient", []), ("make_diagrams", []), ("make_figures", [])]


def run(cmd, log):
    """!
    @brief Run one command from the repository root and tee its output to a file.
    @param cmd Argument list.
    @param log Path of the log file.
    @return int Return code.
    """
    print("running:", " ".join(cmd), flush=True)
    with open(log, "w") as fh:
        proc = subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    print("  ->", log, "return code", proc.returncode, flush=True)
    return proc.returncode


def main():
    """!
    @brief Run everything.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--old-cache", action="store_true")
    ap.add_argument("--skip-tests", action="store_true")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    py = sys.executable
    if not args.skip_tests:
        run([py, "-m", "pytest", "-q", "research/lumped-zones-adoption/tests", "--timeout=1800"], os.path.join(OUT, "tests.txt"))
    for name, flags in STUDIES:
        cmd = [py, os.path.join("research", "lumped-zones-adoption", "scripts", name + ".py")]
        if "--procs" in flags:
            cmd += ["--procs", str(args.procs)]
        if args.quick and name.startswith("study_") and name not in ("study_invariants", "study_transient"):
            cmd += ["--quick"]
        if args.old_cache and name == "study_zones_on_245":
            cmd += ["--old-cache"]
        run(cmd, os.path.join(OUT, name + ".txt"))


if __name__ == "__main__":
    main()
