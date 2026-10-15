"""!
@file cli.py
@brief Command line interface: `python -m pcbthermal <command> ...`.

Commands
- run         solve one or all models and write a summary, plots and a CSV
- transient   power-step response with the FVM model
- convergence FVM grid refinement study
- convert     legacy editor JSON -> native JSON
- example     write the reference board as a native JSON file
"""

import argparse
import csv
import json
import os
import sys
import time

import numpy as np

from . import analytic, fvm, lumped
from .model import load_problem, problem_to_dict, reference_problem

MODELS = ("fvm", "lumped", "analytic")


def _solve(problem, model, args):
    """!
    @brief Run one model.
    @param problem The Problem.
    @param model "fvm", "lumped" or "analytic".
    @param args Parsed command line arguments (cell size, solver).
    @return SteadyResult.
    """
    if model == "fvm":
        return fvm.solve_steady(problem, cell_mm=args.cell_mm, method=args.solver)
    if model == "lumped":
        return lumped.solve_steady(problem)
    return analytic.solve_steady(problem, cell_mm=min(args.cell_mm, 1.0))


def _print_table(results):
    """!
    @brief Print a comparison table of the results.
    @param results Dict {model: SteadyResult}.
    """
    print(f"{'model':9s} {'Tmax':>8s} {'Tmean':>8s} {'dT':>8s} {'Rth K/W':>8s} {'P_in W':>8s} {'balance':>10s} {'time s':>7s}")
    for name, (r, dt) in results.items():
        print(f"{name:9s} {r.t_max:8.2f} {r.t_mean:8.2f} {r.delta_t:8.2f} {r.r_theta:8.3f} "
              f"{r.power_in:8.3f} {r.balance_error:+10.1e} {dt:7.2f}")


def cmd_run(args):
    """!
    @brief Handler of the `run` command.
    @param args Parsed arguments.
    @return Process exit code.
    """
    problem = load_problem(args.config)
    models = MODELS if args.model == "all" else (args.model,)
    timed = {}
    for mname in models:
        t0 = time.time()
        timed[mname] = (_solve(problem, mname, args), time.time() - t0)
    print(f"Board '{problem.name}': {problem.board.width * 1000:.0f} x {problem.board.height * 1000:.0f} mm, "
          f"{problem.board.layers} layers, {problem.total_power():.3f} W")
    _print_table(timed)
    results = {k: v[0] for k, v in timed.items()}

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump({k: r.summary() for k, r in results.items()}, fh, indent=2)
    for name, r in results.items():
        if r.T is not None:
            # CSV of the top layer, one row per cell (x and y are cell centres in mm)
            with open(os.path.join(args.out, f"field_{name}_layer1.csv"), "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["x_mm", "y_mm", "T_c"])
                for i in range(r.T.shape[1]):
                    for j in range(r.T.shape[2]):
                        w.writerow([(j + 0.5) * r.dx * 1000, (i + 0.5) * r.dy * 1000, r.T[0, i, j]])
    if not args.no_plots:
        from . import plots
        for name, r in results.items():
            if r.T is not None:
                plots.plot_fields(r, problem, os.path.join(args.out, f"fields_{name}.png"))
        if len(results) > 1:
            plots.plot_comparison(results, os.path.join(args.out, "comparison.png"))
        plots.plot_profiles(results, problem, os.path.join(args.out, "profiles.png"))
    print(f"Outputs written to {args.out}/")
    return 0


def cmd_transient(args):
    """!
    @brief Handler of the `transient` command.
    @param args Parsed arguments.
    @return Process exit code.
    """
    problem = load_problem(args.config)
    t0 = time.time()
    tr = fvm.solve_transient(problem, t_end=args.t_end, n_out=args.steps, cell_mm=args.cell_mm,
                             theta_scheme=args.theta)
    print(f"Transient done in {time.time() - t0:.2f} s: steady Tmax {tr.steady_t_max:.2f} degC, "
          f"time constant (63 %) {tr.time_constant():.1f} s, Tmax at t_end {tr.t_max[-1]:.2f} degC")
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "transient.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t_s", "Tmax_c", "Tmean_c"])
        for t, a, b in zip(tr.times, tr.t_max, tr.t_mean):
            w.writerow([t, a, b])
    if not args.no_plots:
        from . import plots
        plots.plot_transient(tr, os.path.join(args.out, "transient.png"))
    print(f"Outputs written to {args.out}/")
    return 0


def cmd_convergence(args):
    """!
    @brief Handler of the `convergence` command (FVM grid refinement).
    @param args Parsed arguments.
    @return Process exit code.
    """
    problem = load_problem(args.config)
    rows = []
    print(f"{'cell mm':>8s} {'cells':>8s} {'Tmax':>9s} {'time s':>7s}")
    for c in (10, 5, 2.5, 2, 1, 0.5):
        t0 = time.time()
        r = fvm.solve_steady(problem, cell_mm=c)
        dt = time.time() - t0
        rows.append((c, r.t_max, dt))
        print(f"{c:8.2f} {int(r.extras['cells']):8d} {r.t_max:9.3f} {dt:7.2f}")
    os.makedirs(args.out, exist_ok=True)
    if not args.no_plots:
        from . import plots
        plots.plot_convergence(rows, os.path.join(args.out, "convergence.png"))
    return 0


def cmd_convert(args):
    """!
    @brief Handler of the `convert` command.
    @param args Parsed arguments.
    @return Process exit code.
    """
    problem = load_problem(args.legacy)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(problem_to_dict(problem), fh, indent=2)
    print(f"Wrote {args.output}")
    return 0


def cmd_example(args):
    """!
    @brief Handler of the `example` command.
    @param args Parsed arguments.
    @return Process exit code.
    """
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(problem_to_dict(reference_problem()), fh, indent=2)
    print(f"Wrote {args.output}")
    return 0


def build_parser():
    """!
    @brief Build the argument parser.
    @return argparse.ArgumentParser.
    """
    p = argparse.ArgumentParser(prog="pcbthermal", description="PCB thermal simulator (command line).")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp, config=True):
        if config:
            sp.add_argument("config", help="board JSON file (native or legacy editor format)")
        sp.add_argument("--out", default="output", help="output directory (default: output)")
        sp.add_argument("--cell-mm", type=float, default=2.0, help="FVM cell size in mm (default 2)")
        sp.add_argument("--no-plots", action="store_true", help="skip figure generation")

    r = sub.add_parser("run", help="solve steady state")
    common(r)
    r.add_argument("--model", choices=MODELS + ("all",), default="all")
    r.add_argument("--solver", choices=("direct", "cg"), default="direct", help="FVM linear solver")
    r.set_defaults(func=cmd_run)

    t = sub.add_parser("transient", help="power-step response (FVM)")
    common(t)
    t.add_argument("--t-end", type=float, default=600.0, help="final time in seconds")
    t.add_argument("--steps", type=int, default=40, help="number of output times")
    t.add_argument("--theta", type=float, default=1.0, help="1 = implicit Euler, 0.5 = Crank-Nicolson")
    t.set_defaults(func=cmd_transient)

    c = sub.add_parser("convergence", help="FVM grid refinement study")
    common(c)
    c.set_defaults(func=cmd_convergence)

    v = sub.add_parser("convert", help="legacy editor JSON -> native JSON")
    v.add_argument("legacy")
    v.add_argument("output")
    v.set_defaults(func=cmd_convert)

    e = sub.add_parser("example", help="write the reference board JSON")
    e.add_argument("output", nargs="?", default="examples/reference_board.json")
    e.set_defaults(func=cmd_example)
    return p


def main(argv=None):
    """!
    @brief Entry point.
    @param argv Optional argument list (defaults to sys.argv[1:]).
    @return Process exit code.
    """
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
