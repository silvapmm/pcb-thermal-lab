#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cli.py
@brief Command line interface: `python -m pcbthermal <command> ...`.

Commands
- run         solve one or all models and write a summary, plots and a CSV
- transient   power-step response with the FVM model
- convergence FVM grid refinement study
- solvers     compare the linear solvers (direct, CG, SOR) on one board
- convert     legacy editor JSON -> native JSON; `.pcbt.json` <-> `.pcbtz` package
- gui         open the graphical application
- example     write the reference board as a native JSON file

Exit codes: 0 done, 2 usage error (argparse), 3 a run refused by the memory guard (the message names the cell that fits; `--memory-fraction` changes the limit).
"""

import argparse
import csv
import json
import os
import sys
import time

import numpy as np

from . import __version__, copper, fvm, laminate, memory
from .api import simulate, suggest_cell_mm
from .examples import example_block_board, example_board, example_profile_board
from .model import load_problem, problem_to_dict, reference_problem
from .profile_io import read_profile_csv
from . import package as pkg
from .project import Project, ProjectFormatError, save_project
from .numfmt import num

MODELS = ("fvm", "lumped", "analytic")
RUN_MODELS = MODELS + ("fdm", "solid3d")  # "fdm" is the finite-difference model, "solid3d" the 3D finite-volume solid


def _cell_arg(args, problem, default, transient=False):
    """!
    @brief Resolve the --cell-mm argument.
    @param args Parsed arguments.
    @param problem The Problem (used by "auto").
    @param default Value used when the argument is absent.
    @param transient True for a time simulation: "auto" has to fit its larger memory factor (memory.TRANSIENT_FACTOR).
    @return Cell size in millimetres.
    """
    if args.cell_mm is None:
        return default
    if args.cell_mm != "auto":
        return float(args.cell_mm)
    # The automatic cell also has to fit the memory of the models the command solves: "all" and "compare" are expanded to their model keys (the guard
    # ignores keys it does not know, so "all" passed as it is would not be checked), and the base is the resident size of this process, where the solve runs
    chosen = getattr(args, "model", "fvm")
    models = {"all": MODELS, "compare": RUN_MODELS}.get(chosen, (chosen,))
    cell = suggest_cell_mm(problem, models=models, transient=transient, base=None)
    note = copper.auto_cell_note(problem, cell)          # Imported copper wants 1 mm or less: say so when the memory forced a larger cell
    if note:
        print(note, file=sys.stderr)
    return cell


def _guard(problem, models, cells, transient=False):
    """!
    @brief Ask the memory guard about every cell a command will try, before anything is allocated.
    @param problem The Problem.
    @param models Model keys that will be solved (the guard estimates fvm, fdm and solid3d).
    @param cells Cell sizes in mm that the command will use.
    @param transient True for a time simulation (a larger factor).
    @return None.
    @throws memory.MemoryGuardError If a model is above the memory limit.
    """
    for c in cells:
        memory.check(problem, models, c, transient=transient)


def _load(path):
    """!
    @brief Load a project file of either kind (found by content) and print what the reader of a package dropped or could not check.
    @param path File path.
    @return Project.
    @throws ProjectFormatError For a file this program must not open.
    """
    project = pkg.load_any(path)
    for w in getattr(project.package, "warnings", None) or []:
        print(f"Warning: package: {w}", file=sys.stderr)   # a tampered or unlisted member is dropped or kept unverified: never silently
    return project


def cmd_run(args):
    """!
    @brief Handler of the `run` command: simulate with the public API and save the outputs.
    @param args Parsed arguments.
    @return Process exit code.
    """
    project = _load(args.config)
    options = project.options
    options.models = {"all": MODELS, "compare": RUN_MODELS}.get(args.model, (args.model,))
    options.linear_solver = args.solver
    if args.laminate_s_max_mm is not None:
        options.laminate_s_max_mm = args.laminate_s_max_mm
    if args.laminate_n_max is not None:
        options.laminate_n_max = args.laminate_n_max
    options.validate()
    with laminate.using(*options.laminate_params()):                  # "auto" counts the unknowns of the laminate rule of the run
        options.cell_mm = _cell_arg(args, project.problem, options.cell_mm)
    po = options.profile
    if args.steady_power:
        options.steady_power = args.steady_power
    if args.threshold_c is not None:
        po.threshold_c = args.threshold_c
    if args.duration:
        po.duration = args.duration
    if args.cycles:
        po.cycles = args.cycles
    if args.time_s:
        po.time_s = args.time_s
    if args.initial_c is not None:
        po.initial, po.initial_c = "temperature", args.initial_c
    for spec in args.profile or []:
        name, _, path = spec.partition("=")
        if not path:
            raise SystemExit(f"--profile expects NAME=file.csv, got '{spec}'")
        # A heater is chosen by its name or by its 1-based number (#1, #2, ...)
        heaters = project.problem.heaters
        match = [h for h in heaters if h.name == name] or ([heaters[int(name[1:]) - 1]] if name.startswith("#") and name[1:].isdigit()
                                                           and 0 < int(name[1:]) <= len(heaters) else [])
        if not match:
            raise SystemExit(f"no heater named '{name}' (names: {', '.join(h.name or '-' for h in heaters)})")
        match[0].set_profile(read_profile_csv(path))
    b = project.problem.board
    if args.computed_h:
        b.h_mode = "computed"
    if args.air_speed is not None:
        b.h_mode, b.air_speed = "computed", args.air_speed
    if args.orientation:
        b.h_mode, b.orientation = "computed", args.orientation
    if args.natural_form:
        b.h_mode, b.natural_form = "computed", args.natural_form
    if args.emissivity is not None:
        b.h_mode, b.emissivity_top, b.emissivity_bottom = "computed", args.emissivity, args.emissivity
    if args.h_multiplier is not None:
        b.h_mode, b.h_calibration = "computed", args.h_multiplier
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
    problem = _load(args.config).problem
    t0 = time.time()
    cell = _cell_arg(args, problem, 2.0, transient=True)                  # Resolved once: "auto" asks the guard, with the factor of a time simulation
    _guard(problem, (args.model,), [cell], transient=True)                # The analytic model is not estimated (the guard skips it)
    if args.model == "fdm":
        from . import fdm
        tr = fdm.solve_transient(problem, t_end=args.t_end, n_out=args.steps, cell_mm=cell, theta_scheme=args.theta)
    elif args.model == "analytic":
        from . import analytic
        tr = analytic.solve_transient(problem, t_end=args.t_end, n_out=args.steps, cell_mm=min(_cell_arg(args, problem, 1.0), 1.0))
    else:
        tr = fvm.solve_transient(problem, t_end=args.t_end, n_out=args.steps, cell_mm=cell, theta_scheme=args.theta)
    print(f"Transient done in {time.time() - t0:.2f} s: steady Tmax {tr.steady_t_max:.2f} degC, "
          f"time constant (63 %) {tr.time_constant():.1f} s, Tmax at t_end {tr.t_max[-1]:.2f} degC")
    for w in tr.warnings:
        print(f"Warning: {w}")                                            # Limits of the model met by the run (the Analytic with a heatsink), as `run` prints its warnings
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "transient.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t_s", "Tmax_c", "Tmean_c"])
        for t, a, b in zip(tr.times, tr.t_max, tr.t_mean):
            w.writerow([t, a, b])
    if not args.no_plots:
        from . import plots
        plots.plot_transient(tr, os.path.join(args.out, "transient.png"))
        if args.gif:
            plots.save_transient_gif(tr, problem, os.path.join(args.out, "transient.gif"))
    print(f"Outputs written to {args.out}/")
    return 0


def cmd_calibrate(args):
    """!
    @brief Handler of the `calibrate` command: fit the convection multiplier to a measured temperature.
    @param args Parsed arguments.
    @return Process exit code.
    """
    from .api import calibrate_convection
    project = _load(args.config)
    options = project.options
    with laminate.using(*options.laminate_params()):                    # "auto" counts the unknowns of the project's laminate rule
        options.cell_mm = _cell_arg(args, project.problem, options.cell_mm)
    multiplier, predicted = calibrate_convection(project.problem, args.measured, options, args.model, args.heater)
    what = f"heater {args.heater}" if args.heater else "the board maximum"
    print(f"Measured {num(args.measured)} degC at {what}: convection multiplier {multiplier:.3f} "
          f"(the {args.model} model then gives {predicted:.2f} degC).")
    print("Use it as Board.h_calibration (Environment panel: 'Convection x') with heat transfer set to Computed.")
    return 0


def cmd_convergence(args):
    """!
    @brief Handler of the `convergence` command (FVM grid refinement).
    @param args Parsed arguments.
    @return Process exit code.
    """
    problem = _load(args.config).problem
    rows = []
    cells = (10, 5, 2.5, 2, 1, 0.5)
    _guard(problem, ("fvm",), cells)                    # The whole study is checked first: no half-finished table when the last cell is too fine
    print(f"{'cell mm':>8s} {'cells':>8s} {'Tmax':>9s} {'time s':>7s}")
    for c in cells:
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


def cmd_solvers(args):
    """!
    @brief Handler of the `solvers` command: compare the linear solvers on one board.
    @param args Parsed arguments.
    @return Process exit code.
    """
    project = _load(args.config)
    with laminate.using(*project.options.laminate_params()):            # "auto" and the guard count the unknowns of the project's laminate rule
        cell = _cell_arg(args, project.problem, project.options.cell_mm)
        _guard(project.problem, ("fvm",), [cell])
    cases = [("direct (sparse LU)", dict(method="direct")),
             ("cg (Jacobi)", dict(method="cg")),
             ("SOR, residual 1e-9, omega auto", dict(method="sor")),
             ("SOR, residual 1e-6, omega auto", dict(method="sor", sor_tol=1e-6)),
             ("SOR, step 0.01 K, omega 1.5 (original program)", dict(method="sor", sor_omega=1.5, sor_tol=0.01,
                                                                     sor_criterion="step"))]
    ref = None
    print(f"Board '{project.problem.name}', cell {num(cell)} mm")
    print(f"{'solver':50s} {'Tmax C':>9s} {'|dT| vs direct':>15s} {'residual':>10s} {'sweeps':>8s} {'time s':>8s}")
    for name, kw in cases:
        t0 = time.time()
        with laminate.using(*project.options.laminate_params()):        # The board of the project, with its laminate rule
            r = fvm.solve_steady(project.problem, cell_mm=cell, **kw)
        dt = time.time() - t0
        ref = r if ref is None else ref
        err = float(abs(r.T - ref.T).max())
        sweeps = f"{int(r.extras['iterations'])}" if "iterations" in r.extras else "-"
        print(f"{name:50s} {r.t_max:9.4f} {num(err):>15} {num(r.residual):>10} {sweeps:>8s} {dt:8.2f}")
        for w in r.warnings:
            print(f"   warning: {w}")
    return 0


def cmd_convert(args):
    """!
    @brief Handler of the `convert` command.
    @param args Parsed arguments.
    @return Process exit code.
    """
    if pkg.is_package(args.legacy) or args.output.lower().endswith(pkg.PACKAGE_SUFFIX):
        return _convert_project(args)
    problem = load_problem(args.legacy)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(problem_to_dict(problem), fh, indent=2)
    print(f"Wrote {args.output}")
    return 0


def _convert_project(args):
    """!
    @brief `convert` between a plain project file and a package (either direction, or package to package).
    @details To a package: the project, its images and, with `--with-gerbers`, the source files the input package stores (a plain project has none). To a plain file: the
             images and stored files are dropped, and the command says what was dropped.
    @param args Parsed arguments (`legacy` is the input, `output` the output, `with_gerbers`).
    @return Process exit code.
    """
    project = _load(args.legacy)
    extras = project.package
    if args.output.lower().endswith(pkg.PACKAGE_SUFFIX):
        _, notes = pkg.save_package(args.output, project, include_sources=bool(args.with_gerbers))
        if extras is not None and extras.has_sources() and not args.with_gerbers:
            notes.append(f"{len(extras.sources)} stored source file(s) were not copied (use --with-gerbers)")
        for n in notes:
            print(f"Note: {n}")
    else:
        _, notes = pkg.save_any(args.output, project, as_package=False)
        for n in notes:
            print(f"Warning: dropped: {n}")
    print(f"Wrote {args.output}")
    return 0


def cmd_gui(args):
    """!
    @brief Handler of the `gui` command.
    @param args Parsed arguments.
    @return Process exit code.
    """
    from .gui.app import main as gui_main

    return gui_main(["pcbthermal"] + ([args.project] if args.project else []))


def cmd_example(args):
    """!
    @brief Handler of the `example` command.
    @param args Parsed arguments.
    @return Process exit code.
    """
    board = {"example": example_board, "profile": example_profile_board, "block": example_block_board}.get(args.which, reference_problem)()
    save_project(args.output, Project(problem=board))
    print(f"Wrote {args.output}")
    return 0


def build_parser():
    """!
    @brief Build the argument parser.
    @return argparse.ArgumentParser.
    """
    p = argparse.ArgumentParser(prog="pcbthermal", description="PCB Thermal Lab: PCB thermal simulator.")
    p.add_argument("--version", action="version", version=f"PCB Thermal Lab {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp, config=True):
        if config:
            sp.add_argument("config", help="board JSON file (native or legacy editor format)")
        sp.add_argument("--out", default="output", help="output directory (default: output)")
        sp.add_argument("--cell-mm", default=None, help="cell size in mm, or 'auto' (default: from the project, 1)")
        sp.add_argument("--no-plots", action="store_true", help="skip figure generation")
        sp.add_argument("--memory-fraction", type=float, default=None, metavar="F",
                        help=f"share of the physical memory a solve may use, {memory.MIN_FRACTION} to {memory.MAX_FRACTION} (default: the Preferences value, "
                             f"{memory.DEFAULT_FRACTION}); a larger model is refused with exit code {memory.EXIT_CODE}")

    r = sub.add_parser("run", help="solve steady state")
    common(r)
    r.add_argument("--model", choices=RUN_MODELS + ("all", "compare"), default="all",
                   help="all: fvm, lumped, analytic; compare: those three plus the comparison models fdm and solid3d")
    r.add_argument("--solver", choices=("direct", "cg", "sor"), default="direct", help="FVM linear solver")
    r.add_argument("--laminate-s-max-mm", type=float, default=None, metavar="S",
                   help="longest sub-gap of the laminate between two copper nodes in mm, 0.05 to 5 (FVM and FDM; default 0.4)")
    r.add_argument("--laminate-n-max", type=int, default=None, metavar="N",
                   help="most sub-gaps in one gap, 1 to 16 (1 turns the cutting off; default 4; more is slower and closer to a resolved 3D solid). A gap of "
                        "thickness d gets min(N, ceil(d / S)) sub-gaps: on a 1.6 mm board N above 4 needs a smaller --laminate-s-max-mm too")
    hg = r.add_argument_group("heat transfer coefficients computed from correlations (any of these switches to computed mode)")
    hg.add_argument("--computed-h", action="store_true", help="compute h_top and h_bottom (natural convection + radiation)")
    hg.add_argument("--air-speed", type=float, default=None, help="air speed along the board in m/s (0 = still air)")
    hg.add_argument("--orientation", choices=("horizontal", "vertical"), default=None, help="board orientation")
    hg.add_argument("--natural-form", choices=("general", "laminar"), default=None, dest="natural_form",
                    help="natural convection correlation of a vertical board: general (default) or laminar (Ra < 1.00E9)")
    hg.add_argument("--emissivity", type=float, default=None, help="emissivity of both faces (default 0.9)")
    hg.add_argument("--h-multiplier", type=float, default=None, help="calibration multiplier of the computed convection")
    pg = r.add_argument_group("power profiles (heaters with a square wave in the project file)")
    pg.add_argument("--profile", action="append", metavar="HEATER=FILE.csv",
                    help="power profile of a heater from a CSV file (heater name or #number; repeat for several heaters)")
    pg.add_argument("--steady-power", choices=("average", "peak"), default=None,
                    help="power used by the steady models for heaters with a profile (default: from the project, average)")
    pg.add_argument("--threshold-c", type=float, default=None,
                    help="oscillation in degC below which a heater is replaced by its average power (default: 1)")
    pg.add_argument("--duration", choices=("stable", "cycles", "time"), default=None,
                    help="simulate until the cycle repeats, for a number of cycles, or for a fixed time")
    pg.add_argument("--cycles", type=int, default=None, help="number of cycles of the longest resolved period")
    pg.add_argument("--time-s", type=float, default=None, help="simulated time in seconds (with --duration time)")
    pg.add_argument("--initial-c", type=float, default=None,
                    help="start from this uniform temperature in degC (default: steady state of the average power)")
    r.set_defaults(func=cmd_run)

    t = sub.add_parser("transient", help="power-step response (FVM)")
    common(t)
    t.add_argument("--t-end", type=float, default=600.0, help="final time in seconds")
    t.add_argument("--steps", type=int, default=40, help="number of output times")
    t.add_argument("--model", choices=("fvm", "fdm", "analytic"), default="fvm", help="model of the transient (default: fvm)")
    t.add_argument("--theta", type=float, default=1.0, help="1 = implicit Euler, 0.5 = Crank-Nicolson")
    t.add_argument("--gif", action="store_true", help="also write an animated GIF of the heat evolution")
    t.set_defaults(func=cmd_transient)

    k = sub.add_parser("calibrate", help="fit the convection multiplier to a measured steady temperature")
    k.add_argument("config", help="board JSON file")
    k.add_argument("--measured", type=float, required=True, help="measured steady temperature in degC")
    k.add_argument("--heater", default=None, help="heater whose footprint maximum was measured (default: board maximum)")
    k.add_argument("--model", choices=MODELS, default="fvm")
    k.add_argument("--cell-mm", default=None, help="cell size in mm, or 'auto'")
    k.add_argument("--memory-fraction", type=float, default=None, metavar="F", help="share of the physical memory a solve may use (see run)")
    k.set_defaults(func=cmd_calibrate)

    c = sub.add_parser("convergence", help="FVM grid refinement study")
    common(c)
    c.set_defaults(func=cmd_convergence)

    sv = sub.add_parser("solvers", help="compare direct, CG and SOR on one board")
    common(sv)
    sv.set_defaults(func=cmd_solvers)

    v = sub.add_parser("convert", help="legacy editor JSON -> native JSON; .pcbt.json <-> .pcbtz package")
    v.add_argument("legacy", help="input: a legacy editor file, a .pcbt.json project or a .pcbtz package")
    v.add_argument("output", help="output: a .pcbtz package, or a native JSON file")
    v.add_argument("--with-gerbers", action="store_true", help="to a package: also store the source files (Gerbers, drills, placement, BOM) that the input package holds")
    v.set_defaults(func=cmd_convert)

    g = sub.add_parser("gui", help="open the graphical application")
    g.add_argument("project", nargs="?", help="project file to open")
    g.set_defaults(func=cmd_gui)

    e = sub.add_parser("example", help="write the reference board JSON")
    e.add_argument("output", nargs="?", default="examples/reference_board.pcbt.json")
    e.add_argument("--which", choices=("reference", "example", "profile", "block"), default="reference",
                   help="reference: 100x100 mm 2-layer board; example: 4-layer board with vias and a heatsink; "
                        "profile: the example board with square-wave power on both heaters; block: the example board with a metal block on the bottom")
    e.set_defaults(func=cmd_example)
    return p


def main(argv=None):
    """!
    @brief Entry point.
    @param argv Optional argument list (defaults to sys.argv[1:]).
    @return Process exit code.
    """
    args = build_parser().parse_args(argv)
    try:
        # The fraction is a process-wide override for the command (it replaces the Preferences value); restored afterwards so that a caller (tests) is not left changed
        memory.set_default_fraction(getattr(args, "memory_fraction", None))
        return args.func(args)
    except memory.MemoryGuardError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return memory.EXIT_CODE
    except ProjectFormatError as exc:                  # A project file of a format this program does not read: a message, not a traceback
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except ValueError as exc:
        if "memory fraction" in str(exc):                # An out-of-range --memory-fraction
            print(f"error: {exc}", file=sys.stderr)
            return 2
        raise
    finally:
        memory.set_default_fraction(None)


if __name__ == "__main__":
    sys.exit(main())
