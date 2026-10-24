"""!
@file study_time_and_coefficients.py
@brief Which numbers do the time-dependent models and the computed heat transfer coefficients give now? Prints the tables of README sections 4.6 and 4.7.

@details Before this script the numbers of those sections were copied from docs/validation.md and from the tests, and no script of the folder printed
         them. It runs, on the current program:
         1. the exact check of the time integrator (a uniform one-layer slab, C dtheta/dt = P - G theta, laminate nodes off as in tests/test_fvm.py);
         2. the power-step animation of the example board, FVM against FDM (2 mm) and FVM against Analytic (1 mm);
         3. the power-profile example (example_profile_board) in the FVM, Lumped and Analytic models, and the CSV example of examples/csv_profiles;
         4. the computed heat transfer coefficients on the example board against the power, the orientation, the air speed and the convection multiplier.
Usage: .venv/bin/python research/models-comparison/scripts/study_time_and_coefficients.py   (from the repository root; about 2 minutes)
"""

import copy
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)

from pcbthermal import SolverOptions, analytic, convection, fdm, fvm, laminate, load_project, read_profile_csv, simulate   # noqa: E402
from pcbthermal.examples import example_board, example_profile_board                                                     # noqa: E402
from pcbthermal.model import reference_problem                                                                           # noqa: E402

TIMES_FDM = (0.0, 0.12, 0.82, 3.6, 15.0, 60.0, 120.0)                       # Output times quoted for FVM against FDM (s)
TIMES_ANALYTIC = (0.0, 0.12, 0.35, 0.82, 1.8, 3.6, 7.4, 15.0, 30.0, 60.0, 120.0)   # Output times quoted for FVM against Analytic (s)


def exact_step():
    """!
    @brief Maximum error of implicit Euler and Crank-Nicolson against the exact exponential of a uniform slab, for four time steps.
    @return str Text lines.
    """
    old = laminate.LAMINATE_NODES
    laminate.LAMINATE_NODES = 0              # The closed form is that of one node: the integrator is what is tested (as in tests/test_fvm.py)
    try:
        p = reference_problem(layers=1, heater_mm=100.0, power=10.0)
        p.board.h_side = None                # Insulated edges: the field stays uniform
        net = fvm.Network(p, 8, 8, assemble=False)
        C, G, P = net.C.sum(), net.g_amb.sum(), net.Q.sum()
        tau = C / G
        exact = lambda t: p.board.ambient + P / G * (1.0 - np.exp(-t / tau))
        out = [f"uniform slab: tau = {tau:.1f} s, steady rise {P / G:.2f} K; max error in K over 3 tau (dt, dt/2, dt/4, dt/8, dt = tau/2)"]
        for scheme, name in ((1.0, "implicit Euler"), (0.5, "Crank-Nicolson")):
            errs = []
            for sub in (1, 2, 4, 8):
                tr = fvm.solve_transient(p, t_end=3 * tau, n_out=6, cell_mm=12.5, substeps=sub, theta_scheme=scheme, log_times=False)
                errs.append(float(np.abs(tr.t_max - exact(tr.times)).max()))
            out.append(f"  {name}: " + " / ".join(f"{e:.3g}" for e in errs))
        tr = fvm.solve_transient(p, t_end=3 * tau, n_out=40, cell_mm=12.5, substeps=4, theta_scheme=0.5, log_times=False)
        stored = C * (tr.t_mean[-1] - p.board.ambient)
        # Lost heat: trapezoidal integral of G (T_mean - T_amb) over time
        lost = G * float(np.trapezoid(tr.t_mean - p.board.ambient, tr.times))
        injected = P * float(tr.times[-1])
        out.append(f"  energy (CN): stored + lost = {stored + lost:.2f} J against injected {injected:.2f} J ({100 * ((stored + lost) / injected - 1):+.2f} %)")
        return "\n".join(out)
    finally:
        laminate.LAMINATE_NODES = old


def _at(tr, times):
    """!
    @brief Hottest temperature of a transient at the output times closest to the given times.
    @param tr TransientResult.
    @param times Times in seconds.
    @return list of (time actually used in s, temperature in degC).
    """
    return [(float(tr.times[k]), float(tr.t_max[k])) for k in (int(np.argmin(np.abs(tr.times - t))) for t in times)]


def step_animation():
    """!
    @brief The power-step animation of the example board: FVM against FDM at 2 mm and FVM against Analytic at 1 mm.
    @return str Text lines.
    """
    p = example_board()
    out = []
    a = fvm.solve_transient(p, t_end=120.0, cell_mm=2.0)
    b = fdm.solve_transient(p, t_end=120.0, cell_mm=2.0)
    ta, tb = _at(a, TIMES_FDM), _at(b, TIMES_FDM)
    out.append("FVM against FDM, example board, 2 mm (time used: FVM / FDM)")
    out.append("  t [s]: " + ", ".join(f"{x[0]:.3g}/{y[0]:.3g}" for x, y in zip(ta, tb)))
    out.append("  FVM:   " + ", ".join(f"{x[1]:.1f}" for x in ta))
    out.append("  FDM:   " + ", ".join(f"{y[1]:.1f}" for y in tb))
    # The largest difference over every common output time, not only the quoted ones
    common = min(len(a.times), len(b.times))
    out.append(f"  largest |FVM - FDM| over the frames: {float(np.abs(a.t_max[:common] - b.t_max[:common]).max()):.2f} K; steady maxima {a.steady_t_max:.2f} / {b.steady_t_max:.2f} degC")
    c = fvm.solve_transient(p, t_end=120.0, cell_mm=1.0)
    d = analytic.solve_transient(p, t_end=120.0, cell_mm=1.0)
    tc, td = _at(c, TIMES_ANALYTIC), _at(d, TIMES_ANALYTIC)
    out.append("FVM against Analytic, example board, 1 mm")
    out.append("  t [s]:    " + ", ".join(f"{x[0]:.3g}/{y[0]:.3g}" for x, y in zip(tc, td)))
    out.append("  FVM:      " + ", ".join(f"{x[1]:.1f}" for x in tc))
    out.append("  Analytic: " + ", ".join(f"{y[1]:.1f}" for y in td))
    out.append(f"  largest |FVM - Analytic| at the quoted times: {max(abs(x[1] - y[1]) for x, y in zip(tc, td)):.2f} K; FVM 63 % time {c.time_constant():.1f} s")
    return "\n".join(out)


def profiles_text():
    """!
    @brief Peaks of the power-profile example (2 mm and 1 mm) and of the CSV example in every model that has a time simulation.
    @return str Text lines.
    """
    out = []
    for cell in (2.0, 1.0):
        sim = simulate(example_profile_board(), SolverOptions(cell_mm=cell))
        dec = ", ".join(f"{d.name} {d.regime} ({d.oscillation:.1f} degC)" for d in sim.decisions)
        out.append(f"example_profile_board, {cell:g} mm: decisions {dec}")
        out.append("  peak: " + ", ".join(f"{k} {r.peak:.1f}" for k, r in sim.profile_results.items())
                   + "; steady at the average: " + ", ".join(f"{k} {r.steady_average_max:.1f}" for k, r in sim.profile_results.items())
                   + f"; bound (on-state, FVM) {sim.profile_results['fvm'].steady_peak_max:.1f} degC")
    sim = simulate(example_profile_board(), SolverOptions(models=("fvm", "fdm"), cell_mm=2.0))
    out.append("  FVM against FDM, 2 mm: peak " + ", ".join(f"{k} {r.peak:.1f}" for k, r in sim.profile_results.items()))
    folder = os.path.join(ROOT, "examples", "csv_profiles")
    problem = load_project(os.path.join(folder, "board.pcbt.json")).problem
    by_name = {h.name: h for h in problem.heaters}
    by_name["U1"].set_profile(read_profile_csv(os.path.join(folder, "profiles", "u1_motor_driver_cycle.csv")))
    by_name["U2"].set_profile(read_profile_csv(os.path.join(folder, "profiles", "u2_regulator_startup.csv")))
    sim = simulate(problem, SolverOptions(cell_mm=1.0))
    out.append("CSV example (examples/csv_profiles, start-up), 1 mm: peak " + ", ".join(f"{k} {r.peak:.1f}" for k, r in sim.profile_results.items())
               + f"; steady at the average (FVM) {sim.profile_results['fvm'].steady_average_max:.1f}; bound (FVM) {sim.profile_results['fvm'].steady_peak_max:.1f} degC")
    return "\n".join(out)


def coefficients_table():
    """!
    @brief Example board, FVM at 1 mm: typed h against computed h over the power, with the vertical board, 2 m/s air and a convection multiplier of 0.8.
    @return str Markdown table and the radiation share.
    """
    def run(scale, **board):
        """!
        @brief Solve the example board with every heater power scaled.
        @param scale Power factor.
        @param board Board fields to set (h_mode and the computed settings).
        @return tuple (Tmax in degC, (h_top, h_bottom) or None, Simulation).
        """
        p = example_board()
        for h in p.heaters:
            h.power *= scale
        for k, v in board.items():
            setattr(p.board, k, v)
        sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0))
        return sim.results["fvm"].t_max, sim.h_used.get("fvm"), sim

    lines = ["| Power [W] | Typed | Computed | Difference | Computed h top / bottom [W/m²K] | Vertical | 2 m/s air | Convection ×0.8 |",
             "| --: | --: | --: | --: | :-: | --: | --: | --: |"]
    share = ""
    for scale in (0.1, 0.25, 1.0, 2.0, 4.0):
        typed, _, _ = run(scale)
        comp, hh, sim = run(scale, h_mode="computed")
        vert, _, _ = run(scale, h_mode="computed", orientation="vertical")
        fan, _, _ = run(scale, h_mode="computed", air_speed=2.0)
        cal, _, _ = run(scale, h_mode="computed", h_calibration=0.8)
        lines.append(f"| {5.5 * scale:.3g} | {typed:.1f} | {comp:.1f} | {comp - typed:+.1f} | {hh[0]:.1f} / {hh[1]:.1f} | {vert:.1f} | {fan:.1f} | {cal:.1f} |")
        if scale == 1.0:
            r = sim.results["fvm"]
            _, _, info = convection.board_h(sim.problem.board, r.layer_mean[0], r.layer_mean[-1])
            share = (f"radiation share of the computed coefficient at 5.5 W: top {100 * info['top']['radiation'] / (info['top']['radiation'] + info['top']['convection']):.0f} %, "
                     f"bottom {100 * info['bottom']['radiation'] / (info['bottom']['radiation'] + info['bottom']['convection']):.0f} %")
    # Do the three main models land on the same coefficients? (largest difference to the FVM over three powers)
    spread = 0.0
    for scale in (0.1, 1.0, 4.0):
        p = example_board()
        for h in p.heaters:
            h.power *= scale
        p.board.h_mode = "computed"
        used = simulate(p, SolverOptions(cell_mm=1.0)).h_used
        spread = max(spread, max(abs(used[m][k] - used["fvm"][k]) for m in used for k in (0, 1)))
    return "\n".join(lines) + "\n\n" + share + f"\nlargest difference of the Lumped and Analytic coefficients to the FVM ones (0.55, 5.5, 22 W): {spread:.2f} W/m2K"


def main():
    """!
    @brief Print every section.
    @return None.
    """
    print("## Exact check of the time integrator\n")
    print(exact_step())
    print("\n## Power-step animation\n")
    print(step_animation())
    print("\n## Power profiles\n")
    print(profiles_text())
    print("\n## Computed heat transfer coefficients (example board, FVM, 1 mm)\n")
    print(coefficients_table())


if __name__ == "__main__":
    main()
