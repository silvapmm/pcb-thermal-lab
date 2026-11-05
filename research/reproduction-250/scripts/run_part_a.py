#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file run_part_a.py
@brief Runner of Part A of the reproduction pass of 2.5.0: runs the studies of eleven research folders one at a time, with a time limit and a pause when the machine is loaded.
@details Usage: .venv/bin/python research/reproduction-250/scripts/run_part_a.py [--timeout S] [--only folder] [--late] [--force] (from the repository root). Outputs go to
         `research/reproduction-250/out/<folder>/<script>.txt` (git-ignored) and the summary to `out/part_a.json`. A job that reaches the limit is killed and recorded as timeout.
         The child process group is stopped (SIGSTOP) while the load average stays above 7 or swap used is above 3 GB and resumed below 5 and 3 GB.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(FOLDER))
OUT = os.path.join(FOLDER, "out")
SUMMARY = os.path.join(OUT, "part_a.json")

# (folder, script, args), cheap folders first.
JOBS = [
    ("analytic-partial-copper", "study_baseline.py", []),
    ("analytic-partial-copper", "study_causes.py", []),
    ("analytic-partial-copper", "study_candidate.py", []),
    ("analytic-partial-copper", "study_rows.py", []),
    ("analytic-partial-copper", "study_review.py", []),
    ("analytic-2-6", "study_frozen_impact.py", []),
    ("analytic-2-6", "study_frozen_transient.py", []),
    ("analytic-2-6", "study_transient_both.py", []),
    ("analytic-2-6", "study_transient_edge_block.py", []),
    ("analytic-2-6", "study_perlayer_edge.py", []),
    ("analytic-2-6", "study_4l_convergence.py", []),
    ("analytic-2-6", "study_review.py", []),
    ("analytic-edge-spatial", "study_edge_variants.py", []),
    ("analytic-edge-spatial", "study_edge_complications.py", []),
    ("analytic-edge-spatial", "study_frozen_impact.py", []),
    ("analytic-edge-spatial", "study_muzychka_eq21.py", []),
    ("analytic-edge-spatial", "study_strip_sensitivity.py", []),
    ("analytic-edge-spatial", "study_review_checks.py", []),
    ("fin-channel", "study_channel_correlations.py", []),
    ("fin-channel", "study_optimum_spacing.py", []),
    ("fin-channel", "study_program_finned_block.py", []),
    ("fin-channel", "study_warning_rule.py", []),
    ("fin-channel-sources", "study_source_checks.py", []),
    ("fin-channel-sources", "study_review_checks.py", []),
    ("block-and-fins", "study_finned_block_all_models.py", []),
    ("block-and-fins", "study_thick_plate_criterion.py", []),
    ("block-and-fins", "fin_validation.py", []),
    ("block-and-fins", "study_why_coefficients_fail.py", []),
    ("block-and-fins", "block_equivalent_study.py", []),
    ("convection-laws", "study_laws_table.py", []),
    ("convection-laws", "print_tables.py", []),
    ("convection-laws", "study_board_effect.py", []),
    ("convection-laws", "study_measurement_prediction.py", []),
    ("convection-laws", "study_cavity.py", []),
    ("component-heatsink", "component_study.py", []),
    ("component-heatsink", "top_path_study.py", []),
    ("component-heatsink", "chain_study.py", []),
    ("component-heatsink", "heatsink_study.py", []),
    ("component-heatsink", "heatsink_convection_study.py", []),
    ("component-heatsink", "base_spreading_study.py", []),
    ("component-heatsink", "block_contact_study.py", []),
    ("component-heatsink", "study_notes_r2.py", []),
    ("component-heatsink", "study_top_path_convergence.py", []),
    ("component-heatsink", "package_prototype.py", []),
    ("effective-conductivity", "study_corrections_impact.py", []),
    ("effective-conductivity", "study_program_vs_coupon.py", []),
    ("effective-conductivity", "study_one_layer_independent.py", []),
    ("effective-conductivity", "study_natural_convection.py", []),
    ("effective-conductivity", "study_channel_correlations.py", []),
    ("effective-conductivity", "study_lee_spreading.py", []),
    ("effective-conductivity", "study_biot_definitions.py", []),
    ("effective-conductivity", "study_muzychka_2003.py", []),
    ("effective-conductivity", "study_culham_1998.py", []),
    ("bare-spot-under-source", "study_validation_rows.py", []),
    ("bare-spot-under-source", "study_margin.py", []),
    ("bare-spot-under-source", "study_skin.py", []),
    ("bare-spot-under-source", "study_reference.py", []),
    ("bare-spot-under-source", "study_real_stormduino.py", []),
    ("bare-spot-under-source", "study_review.py", []),
    ("gap-subdivision", "rerun_baseline.py", []),
    ("gap-subdivision", "study_validation_impact.py", []),
    ("gap-subdivision", "study_baseline_uniform.py", []),
    ("gap-subdivision", "study_real_boards.py", []),
    ("gap-subdivision", "study_references.py", []),
]

# Long jobs, run last with their own limit (seconds of running time).
LATE = [
    ("bare-spot-under-source", "study_window_sweep.py", ["all"], 4200),
    ("gap-subdivision", "study_baseline_pads.py", [], 12000),
    ("gap-subdivision", "study_gap_nodes.py", [], 3600),
    ("gap-subdivision", "study_gap_grading.py", [], 3600),
    ("gap-subdivision", "study_review.py", ["2"], 3600),
    ("convection-laws", "study_plate_mac.py", ["--both"], 4200),
    # the first pass hit its 30 min limit (base_spreading, review: slow under load) or needed the reference built first (stormduino)
    ("component-heatsink", "base_spreading_study.py", [], 5400),
    ("bare-spot-under-source", "study_review.py", [], 5400),
    ("bare-spot-under-source", "study_real_stormduino.py", ["reference"], 5400),
    ("bare-spot-under-source", "study_real_stormduino.py", ["treat"], 3600),
]


def machine_state():
    """!
    @brief Read the one-minute load average and the swap used.
    @return tuple (load, swap_gb).
    """
    load = os.getloadavg()[0]
    swap = 0.0
    try:
        txt = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True).stdout
        used = txt.split("used =")[1].split()[0]
        swap = float(used[:-1]) / (1024.0 if used[-1] == "M" else 1.0)
    except Exception:
        pass
    return load, swap


def governor(proc, stop):
    """!
    @brief Pause and resume the child's process group by the load rule.
    @param proc  subprocess.Popen The job.
    @param stop  threading.Event Set when the job is over.
    @return None.
    """
    paused = False
    while not stop.wait(15):
        load, swap = machine_state()
        try:
            if not paused and (load > 7 or swap > 3):
                os.killpg(proc.pid, signal.SIGSTOP)
                paused = True
                print(f"  paused: load {load:.1f}, swap {swap:.1f} GB", flush=True)
            elif paused and load < 5 and swap < 3:
                os.killpg(proc.pid, signal.SIGCONT)
                paused = False
                print(f"  resumed: load {load:.1f}, swap {swap:.1f} GB", flush=True)
        except ProcessLookupError:
            return
    if paused:
        try:
            os.killpg(proc.pid, signal.SIGCONT)
        except ProcessLookupError:
            pass


def run_job(folder, script, args, limit, python):
    """!
    @brief Run one study with a limit on its time.
    @param folder  str Folder under research/.
    @param script  str Script file.
    @param args    list Arguments.
    @param limit   float Seconds allowed.
    @param python  str Interpreter.
    @return dict Record.
    """
    key = f"{folder}/{script} {' '.join(args)}".strip()
    odir = os.path.join(OUT, folder)
    os.makedirs(odir, exist_ok=True)
    tag = script[:-3] + ("_" + "_".join(a.strip("-") for a in args) if args else "")
    path = os.path.join(odir, tag + ".txt")
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2", MKL_NUM_THREADS="2", PYTHONUNBUFFERED="1")
    t0 = time.time()
    with open(path, "w") as out:
        proc = subprocess.Popen([python, os.path.join(ROOT, "research", folder, "scripts", script)] + args, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, env=env,
                                start_new_session=True)
        stop = threading.Event()
        th = threading.Thread(target=governor, args=(proc, stop), daemon=True)
        th.start()
        try:
            proc.wait(timeout=limit)
            status, rc = ("ok" if proc.returncode == 0 else "failed"), proc.returncode
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGCONT)
            os.killpg(proc.pid, signal.SIGKILL)
            status, rc = "timeout", None
        stop.set()
    return {"key": key, "folder": folder, "script": script, "args": args, "status": status, "rc": rc, "seconds": round(time.time() - t0, 1), "output": os.path.relpath(path, ROOT)}


def main():
    """!
    @brief Run the jobs in turn and save the summary after each.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=float, default=1800.0)
    ap.add_argument("--only", default="")
    ap.add_argument("--late", action="store_true", help="run the long jobs instead")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--python", default=sys.executable)
    opts = ap.parse_args()
    records = {}
    if os.path.exists(SUMMARY):
        records = {r["key"]: r for r in json.load(open(SUMMARY))}
    jobs = [(f, s, a, opts.timeout) for f, s, a in JOBS] if not opts.late else LATE
    for folder, script, args, limit in jobs:
        if opts.only and folder != opts.only:
            continue
        key = f"{folder}/{script} {' '.join(args)}".strip()
        if key in records and records[key]["status"] == "ok" and not opts.force:
            continue
        print("running", key, flush=True)
        records[key] = run_job(folder, script, args, limit, opts.python)
        print("  ->", records[key]["status"], records[key]["seconds"], "s", flush=True)
        os.makedirs(OUT, exist_ok=True)
        json.dump(list(records.values()), open(SUMMARY, "w"), indent=1)


if __name__ == "__main__":
    main()
