#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file run_all.py
@brief Re-run the studies of the research folders on the current tree, one at a time, and write what each printed plus a machine-readable summary.
@details The list is the studies of the folders that import the program, in the order of JOBS (a script is run as `python <script> <args>` from the repository
         root, with the threads of the numerical libraries limited so that one job does not fill the machine). Every job has a time limit; a job that reaches it
         is killed and recorded as `timeout` (the README says "not run: reason"). Jobs that the README of the folder says take more than 20 minutes or need a
         downloaded board are in SKIP with the reason. Outputs: `research/reproduction-245/out/<folder>/<script>.txt` (stdout and stderr) and
         `research/reproduction-245/out/reproduction.json` (folder, script, args, status, return code, seconds), both git-ignored. A run that is interrupted
         can be resumed: a job whose `.txt` exists and whose entry says `ok` is not run again unless `--force` is given.
Usage: .venv/bin/python research/reproduction-245/scripts/run_all.py [--folders a,b] [--timeout SECONDS] [--force] [--list]   (from the repository root)
"""

import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(FOLDER))
OUT = os.path.join(FOLDER, "out")
SUMMARY = os.path.join(OUT, "reproduction.json")

# (folder, script, extra arguments); the order is the order of the reproduction pass.
JOBS = [
    ("analytic-partial-copper", "study_baseline.py", []),
    ("analytic-partial-copper", "study_causes.py", []),
    ("analytic-partial-copper", "study_candidate.py", []),
    ("analytic-partial-copper", "study_rows.py", []),
    ("analytic-partial-copper", "study_review.py", []),
    ("bare-spot-under-source", "study_validation_rows.py", []),
    ("bare-spot-under-source", "study_review.py", []),
    ("gap-subdivision", "rerun_baseline.py", ["--update"]),
    ("gap-subdivision", "study_validation_impact.py", []),
    ("gap-subdivision", "study_gap_nodes.py", []),
    ("gap-subdivision", "study_gap_grading.py", []),
    ("gap-subdivision", "study_real_boards.py", []),
    ("gap-subdivision", "study_review.py", ["2"]),
    ("lumped-via-groups", "study_cluster_in_cell.py", []),
    ("lumped-via-groups", "study_cell_link.py", []),
    ("lumped-via-groups", "study_example_board.py", []),
    ("lumped-via-groups", "study_outside.py", []),
    ("lumped-via-groups", "study_review.py", ["--procs", "4"]),
    ("lumped-analytic-vias", "study_causes.py", []),
    ("lumped-analytic-vias", "study_via_fill_rows.py", []),
    ("lumped-analytic-vias", "study_discretisation.py", []),
    ("lumped-analytic-vias", "study_real_boards.py", []),
    ("lumped-analytic-vias", "study_unit_cell.py", ["--procs", "4"]),
    ("lumped-analytic-vias", "study_arrays.py", ["--procs", "4"]),
    ("point-via-convergence", "study_unit_cell.py", []),
    ("point-via-convergence", "study_array_board.py", ["--model", "fvm"]),
    ("point-via-convergence", "study_array_board.py", ["--model", "fdm"]),
    ("point-via-convergence", "study_row_lone.py", ["--model", "fvm"]),
    ("point-via-convergence", "study_row_lone.py", ["--model", "fdm"]),
    ("point-via-convergence", "study_example_board.py", ["--model", "fvm"]),
    ("point-via-convergence", "study_example_board.py", ["--model", "fdm"]),
    ("point-via-convergence", "study_solid3d.py", []),
    ("point-via-convergence", "study_solvers.py", []),
    ("point-via-convergence", "study_edge_via.py", []),
    ("via-fill", "study_via_fill.py", []),
    ("via-fill", "study_via_model_checks.py", []),
    ("sor-with-via-couplings", "study_variants.py", []),
    ("sor-with-via-couplings", "study_real_board.py", []),
    ("sor-with-via-couplings", "study_block_over.py", []),
    ("sor-with-via-couplings", "study_stiffness.py", []),
    ("sor-with-via-couplings", "study_failure.py", []),
    ("sor-with-via-couplings", "study_review.py", []),
    ("rotated-square-3d", "study_regression.py", []),
    ("rotated-square-3d", "study_part_across_outline.py", []),
    ("rotated-square-3d", "study_remeasure.py", []),
    ("rotated-square-3d", "study_turned_part.py", []),
    ("rotated-square-3d", "study_edge_conductance.py", []),
    ("rotated-square-3d", "study_cut_cells.py", []),
    ("rotated-square-3d", "study_disc.py", []),
    ("rotated-square-3d", "study_square_reference.py", []),
    ("models-comparison", "validation_study.py", []),
    ("models-comparison", "solver_equivalence.py", []),
    ("models-comparison", "study_lumped_rings.py", []),
    ("models-comparison", "study_time_and_coefficients.py", []),
    ("models-comparison", "study_complex_boards_independent.py", []),
    ("outline", "outline_rectangle_study.py", []),
    ("outline", "study_edge_on_grid_lines.py", []),
    ("outline", "study_outline_time_constant.py", []),
    ("outline", "study_disc_reference.py", []),
    ("stackup", "stackup_outline_study.py", []),
    ("stackup", "study_dielectric_sensitivity.py", []),
    ("stackup", "study_inner_copper_1oz.py", []),
    ("power-calculator", "calculator_validation.py", []),
    ("power-calculator", "study_independent_datasheet_board.py", []),
    ("power-calculator", "study_power_band.py", []),
    ("component-heatsink", "study_top_path_convergence.py", []),
    ("block-and-fins", "study_finned_block_all_models.py", []),
    ("block-and-fins", "study_thick_plate_criterion.py", []),
    ("block-and-fins", "fin_validation.py", []),
    ("solid3d-verification", "study_one_layer_board.py", []),
    ("effective-conductivity", None, []),
    ("zone-union", "study_cost.py", []),
    ("zone-union", "study_cases.py", []),
    ("zone-union", "study_program.py", []),
    ("plate-h-level", None, []),
    ("horizontal-plate-h", None, []),
    ("fin-channel", None, []),
    ("fin-channel-sources", "study_source_checks.py", []),
    ("theory-sources", None, []),
    ("via-real-board", "study_validation_rows.py", []),
    ("laminate-nodes", "study_validation_rows.py", []),
    ("laminate-nodes", "study_one_layer.py", []),
    ("young-omega-tiles", "study_s3_boards.py", []),
    ("young-omega-tiles", "study_s4_example.py", []),
    ("gerber-models", "study_scalar_formulas.py", []),
    ("gerber-models", "study_heater_size.py", []),
]

# Jobs that are not run on purpose, with the reason (the README says "not run: reason").
SKIP = {
    ("gap-subdivision", "study_gap_nodes.py"): "needs out/refs_pads.json (study_baseline_pads.py, 1.5 to 3 hours the first time); without it the run reached the 25 minute limit",
    ("gap-subdivision", "study_gap_grading.py"): "needs out/refs_pads.json (study_baseline_pads.py, 1.5 to 3 hours the first time)",
    ("gap-subdivision", "study_review.py"): "reads out/refs_pads.json (1.5 to 3 hours the first time)",
    ("lumped-via-groups", "study_holdout.py"): "README says about 40 minutes the first time (over the 20 minute limit)",
    ("lumped-via-groups", "study_family.py"): "README says about 15 minutes plus fine-grid references that take about an hour the first time",
    ("lumped-via-groups", "study_zone_sensitivity.py"): "fine-grid references take about 10 minutes the first time, the zone model is a prototype in lib/",
    ("gerber-models", "study_models_self.py"): "needs a patched copy of the program and about 20 minutes",
    ("gerber-models", "study_diagonal_heldout.py"): "about 30 minutes",
    ("gerber-models", "study_import_end_to_end.py"): "about 10 minutes and 8 GB of memory",
}


def load_summary():
    """!
    @brief Read the summary of an earlier (interrupted) run.
    @return dict Map "folder/script args" to its record, empty when there is none.
    """
    if os.path.exists(SUMMARY):
        with open(SUMMARY) as handle:
            return {r["key"]: r for r in json.load(handle)}
    return {}


def save_summary(records):
    """!
    @brief Write the machine-readable summary.
    @param records  dict Map key to record.
    @return None.
    """
    os.makedirs(OUT, exist_ok=True)
    with open(SUMMARY, "w") as handle:
        json.dump(list(records.values()), handle, indent=1)


def discover(folder):
    """!
    @brief The scripts of a folder that JOBS names with no script (all its runnable studies, in name order).
    @param folder  str Folder name under research/.
    @return list The script file names (make_*, fetch_* and underscore files left out).
    """
    sdir = os.path.join(ROOT, "research", folder, "scripts")
    if not os.path.isdir(sdir):
        return []
    skip_prefix = ("make_", "fetch_", "_", "run_")
    return sorted(s for s in os.listdir(sdir) if s.endswith(".py") and not s.startswith(skip_prefix))


def expand():
    """!
    @brief The job list with the folders that name no script expanded to every script they hold.
    @return list Tuples (folder, script, args).
    """
    jobs = []
    for folder, script, args in JOBS:
        if script is None:
            jobs += [(folder, s, args) for s in discover(folder)]
        else:
            jobs.append((folder, script, args))
    return jobs


def run_job(folder, script, args, limit, python):
    """!
    @brief Run one study and capture its output.
    @param folder  str Folder under research/.
    @param script  str Script file name.
    @param args    list Extra command-line arguments.
    @param limit   float Time limit in seconds.
    @param python  str Interpreter.
    @return dict Record with status ok, failed or timeout, return code and seconds.
    """
    key = f"{folder}/{script} {' '.join(args)}".strip()
    odir = os.path.join(OUT, folder)
    os.makedirs(odir, exist_ok=True)
    tag = script[:-3] + ("_" + "_".join(a.strip("-") for a in args) if args else "")
    path = os.path.join(odir, tag + ".txt")
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2", MKL_NUM_THREADS="2", PYTHONUNBUFFERED="1")
    t0 = time.time()
    with open(path, "w") as out:
        try:
            proc = subprocess.run([python, os.path.join(ROOT, "research", folder, "scripts", script)] + args, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT,
                                  env=env, timeout=limit)
            status, rc = ("ok" if proc.returncode == 0 else "failed"), proc.returncode
        except subprocess.TimeoutExpired:
            status, rc = "timeout", None
    return {"key": key, "folder": folder, "script": script, "args": args, "status": status, "rc": rc, "seconds": round(time.time() - t0, 1),
            "output": os.path.relpath(path, ROOT)}


def main():
    """!
    @brief Parse the command line and run the jobs in turn, saving the summary after each.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--folders", default="", help="comma list of folders to run (default: all)")
    ap.add_argument("--timeout", type=float, default=1500.0, help="seconds allowed per job")
    ap.add_argument("--force", action="store_true", help="run again the jobs already recorded ok")
    ap.add_argument("--list", action="store_true", help="print the jobs and stop")
    ap.add_argument("--python", default=sys.executable)
    opts = ap.parse_args()
    wanted = set(f for f in opts.folders.split(",") if f)
    records = load_summary()
    for folder, script, args in expand():
        if wanted and folder not in wanted:
            continue
        key = f"{folder}/{script} {' '.join(args)}".strip()
        if (folder, script) in SKIP:
            records[key] = {"key": key, "folder": folder, "script": script, "args": args, "status": "skipped", "reason": SKIP[(folder, script)]}
            continue
        if opts.list:
            print(key)
            continue
        if key in records and records[key]["status"] == "ok" and not opts.force:
            continue
        print("running", key, flush=True)
        records[key] = run_job(folder, script, args, opts.timeout, opts.python)
        print("  ->", records[key]["status"], records[key]["seconds"], "s", flush=True)
        save_summary(records)
    if not opts.list:
        save_summary(records)


if __name__ == "__main__":
    main()
