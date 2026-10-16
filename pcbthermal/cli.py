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

from . import fvm
from .api import simulate
from .examples import example_board
from .model import load_problem, problem_to_dict, reference_problem
from .project import Project, load_project, save_project

MODELS = ("fvm", "lumped", "analytic")


def cmd_run(args):
    """!
    @brief Handler of the `run` command: simulate with the public API and save the outputs.
    @param args Parsed arguments.
    @return Process exit code.
    """
    project = load_project(args.config)
    options = project.options
    options.models = MODELS if args.model == "all" else (args.model,)
    if args.cell_mm is not None:
        options.cell_mm = args.cell_mm
    options.linear_solver = args.solver
    sim = simulate(project.problem, options)
    print(f"Board '{project.problem.name}': {project.problem.board.width * 1000:.0f} x "
          f"{project.problem.board.height * 1000:.0f} mm, {project.problem.board.layers} layers, "
          f"{project.problem.total_power():.3f} W")
    print(sim.to_markdown())
    files = sim.save(args.out, plots=not args.no_plots)
    print(f"{len(files)} files written to {args.out}/")
    return 0


def cmd_transient(args):
    """!
    @brief Handler of the `transient` command.
    @param args Parsed arguments.
    @return Process exit code.
    """
    problem = load_problem(args.config)
    t0 = time.time()
    tr = fvm.solve_transient(problem, t_end=args.t_end, n_out=args.steps, cell_mm=args.cell_mm or 2.0,
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
    board = example_board() if args.which == "example" else reference_problem()
    save_project(args.output, Project(problem=board))
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
        sp.add_argument("--cell-mm", type=float, default=None, help="cell size in mm (default: from the project, 1)")
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
    e.add_argument("output", nargs="?", default="examples/reference_board.pcbt.json")
    e.add_argument("--which", choices=("reference", "example"), default="reference",
                   help="reference: 100x100 mm 2-layer board; example: 4-layer board with vias and a sink")
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
