"""!
@file api.py
@brief Public entry point: SolverOptions in, Simulation out.

@details One call runs any combination of the three models on a Problem and returns a
Simulation object that holds the results, the timings and helpers to compare, export and
plot them:

    from pcbthermal import Problem, simulate, SolverOptions

    p = Problem.new(width_mm=100, height_mm=80, layers=4)
    p.add_full_copper().add_heater(1, 4.0, rect=(30, 35, 40, 45), name="U1", theta=8.0)
    sim = simulate(p, SolverOptions(models=("fvm", "lumped"), cell_mm=1.0))
    print(sim.to_markdown())
    sim.save("results")
"""

import csv
import json

import numpy as np
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, Optional, Tuple

import copy
import math

from . import __version__, analytic, blocks, convection, fdm, fvm, lumped, profiles, solid3d
from .analysis import block_stats, part_split, heater_stats, hotspots, zone_stats
from . import defaults
from .checks import check_problem, check_thick_plates
from .model import Problem
from .results import SteadyResult

MODEL_NAMES = ("fvm", "lumped", "analytic")
COMPARISON_MODELS = ("fdm", "solid3d")          # Comparison models: never the reference of the decisions
RECTANGLE_ONLY = ("lumped", "analytic")           # Models that need a rectangular board: for an outline they run on the rectangle of the same area
TIME_MODELS = MODEL_NAMES + ("fdm",)             # Models that also do the time simulation (the 3D solid is steady state only)


@dataclass
class SolverOptions:
    """!
    @brief Every solver setting in one validated, JSON-serialisable object.
    """
    models: Tuple[str, ...] = MODEL_NAMES        # Models to run, any subset of MODEL_NAMES
    cell_mm: float = 1.0                         # FVM cell size and sampling grid of the others (mm)
    linear_solver: str = "direct"                # FVM solver: "direct" (sparse LU), "cg" or "sor" (comparison)
    lumped_rings: int = 10                       # Rings per heater network in the lumped model
    analytic_modes: int = 300                    # Cosine modes per direction in the analytic model
    analytic_local_corrections: bool = True      # Treat vias and heatsinks locally (Green's function update)
    hotspot_c: float = 100.0                     # Temperature limit used for hotspot detection (degC)
    steady_power: str = "average"                # Power of heaters with a profile in the steady models: "average" or "peak"
    profile: profiles.ProfileOptions = field(default_factory=profiles.ProfileOptions)   # Time-simulation settings

    def validate(self):
        """!
        @brief Check the values.
        @throws ValueError If a value is out of range or a model name is unknown.
        """
        bad = [m for m in self.models if m not in MODEL_NAMES + COMPARISON_MODELS]
        if bad or not self.models:
            raise ValueError(f"models must be a non-empty subset of {MODEL_NAMES + COMPARISON_MODELS}, got {self.models}")
        if not 0.05 <= self.cell_mm <= 50:
            raise ValueError("cell_mm must be between 0.05 and 50")
        if self.linear_solver not in ("direct", "cg", "sor"):
            raise ValueError("linear_solver must be 'direct', 'cg' or 'sor'")
        if self.lumped_rings < 3 or self.analytic_modes < 20:
            raise ValueError("lumped_rings must be >= 3 and analytic_modes >= 20")
        if self.steady_power not in ("average", "peak"):
            raise ValueError("steady_power must be 'average' or 'peak'")
        self.profile.validate()

    def to_dict(self):
        """!
        @brief JSON-ready dictionary.
        @return Dict of the options.
        """
        d = asdict(self)
        d["models"] = list(self.models)
        d["profile"] = self.profile.to_dict()
        return d

    @classmethod
    def from_dict(cls, data):
        """!
        @brief Build options from a dictionary, ignoring unknown keys.
        @param data Dict as produced by to_dict.
        @return Validated SolverOptions.
        """
        known = {k: v for k, v in (data or {}).items() if k in cls.__dataclass_fields__}
        if "models" in known:
            known["models"] = tuple(known["models"])
        known["profile"] = profiles.ProfileOptions.from_dict(known.get("profile"))
        o = cls(**known)
        o.validate()
        return o


@dataclass
class Simulation:
    """!
    @brief Outcome of simulate(): the problem, the options, one result per model and the timings.
    """
    problem: Problem
    options: SolverOptions
    results: Dict[str, SteadyResult] = field(default_factory=dict)
    seconds: Dict[str, float] = field(default_factory=dict)
    problem_warnings: list = field(default_factory=list)       # Validity checks of the input (see checks.py)
    decisions: list = field(default_factory=list)              # profiles.HeaterDecision per heater (power profiles)
    profile_results: Dict[str, profiles.ProfileResult] = field(default_factory=dict)   # Time simulation per model
    profile_reference: str = ""                                # Model whose step response made the decisions
    profile_error: str = ""                                    # Why the time simulation was not run, if it was not
    step_response: Optional[profiles.StepResponse] = None      # Step responses behind the decisions
    h_used: Dict[str, tuple] = field(default_factory=dict)     # (h_top, h_bottom) per model when h is computed
    effective_problem: Optional[Problem] = None                # Problem with the computed h as typed values (computed mode)
    power_used: Dict[str, list] = field(default_factory=dict)  # Powers dissipated per heater and model when a power temperature coefficient is set
    part_warnings: list = field(default_factory=list)          # Junction limits, implausible theta, thermal runaway (after the solves)

    @property
    def warnings(self):
        """!
        @brief Every warning: input checks first, then those of each model.
        @return List of strings.
        """
        out = list(self.problem_warnings) + list(self.part_warnings)
        for name, r in self.results.items():
            out += [f"{name}: {w}" for w in r.warnings]
        for name, r in self.profile_results.items():
            out += [f"{name} (time simulation): {w}" for w in r.warnings]
        if self.profile_error:
            out.append(f"time simulation not run: {self.profile_error}")
        return out

    @property
    def reference(self):
        """!
        @brief The most trustworthy result available (FVM if it was run).
        @return SteadyResult.
        """
        return self.results.get("fvm") or next(iter(self.results.values()))

    def heater_rows(self):
        """!
        @brief Heater and junction statistics of the reference model, with the powers actually dissipated.
        @return List of dicts of analysis.heater_stats (empty without a field).
        """
        ref = self.reference
        if ref.T is None:
            return []
        return heater_stats(ref, self.problem, self.power_used.get(ref.model))

    def table(self):
        """!
        @brief One row per model, with the error against the reference model.
        @return List of dicts.
        """
        ref = self.reference
        rows = []
        for name, r in self.results.items():
            err = (r.delta_t / ref.delta_t - 1.0) if ref.delta_t > 0 else 0.0
            rows.append({"model": name, "t_max_c": r.t_max, "t_mean_c": r.t_mean, "delta_t_k": r.delta_t,
                         "r_theta_k_per_w": r.r_theta, "power_in_w": r.power_in,
                         "energy_balance": r.balance_error, "error_vs_reference": err,
                         "seconds": self.seconds.get(name, 0.0), "warnings": len(r.warnings)})
        return rows

    def to_markdown(self):
        """!
        @brief The comparison table as Markdown, followed by the warnings.
        @return String.
        """
        lines = ["| Model | Tmax [°C] | Tmean [°C] | ΔT [°C] | Rθ [K/W] | Power [W] | Balance | Error vs " +
                 self.reference.model + " | Time [s] |",
                 "| :-- | --: | --: | --: | --: | --: | --: | --: | --: |"]
        for r in self.table():
            lines.append(f"| {r['model']} | {r['t_max_c']:.2f} | {r['t_mean_c']:.2f} | {r['delta_t_k']:.2f} | "
                         f"{r['r_theta_k_per_w']:.3f} | {r['power_in_w']:.3f} | {r['energy_balance']:+.0e} | "
                         f"{r['error_vs_reference'] * 100:+.1f} % | {r['seconds']:.2f} |")
        lines += self._profile_markdown()
        for w in self.warnings:
            lines.append(f"\n> **Warning**: {w}")
        return "\n".join(lines) + "\n"

    def _profile_markdown(self):
        """!
        @brief Markdown tables of the power-profile decisions and of the time simulation.
        @return List of lines (empty without profiles).
        """
        if not self.decisions:
            return []
        lines = ["", f"Power profiles (decision from the {self.profile_reference} step response, "
                     f"threshold {self.options.profile.threshold_c:g} °C):", "",
                 "| Heater | Period [s] | Duty | Average [W] | Peak [W] | Oscillation [°C] | % of rise | Decision |",
                 "| :-- | --: | --: | --: | --: | --: | --: | :-- |"]
        for d in self.decisions:
            if d.kind != "constant":
                lines.append(f"| {d.name} | {d.period:g}{'' if d.repeat else ' (once)'} | {_duty_text(d)} | {d.average_power:.3f} | {d.peak_power:.3f} | "
                             f"{d.oscillation:.2f} | {d.oscillation_percent:.1f} % | {d.regime} |")
            else:
                lines.append(f"| {d.name} | - | - | {d.average_power:.3f} | {d.peak_power:.3f} | - | - | constant |")
        if self.profile_results:
            lines += ["", "| Model | Peak [°C] | Minimum [°C] | Oscillation [°C] | Steady, average power [°C] | "
                          "Steady, peak power (bound) [°C] | Windows | Steps | Time [s] |",
                      "| :-- | --: | --: | --: | --: | --: | --: | --: | --: |"]
            for name, r in self.profile_results.items():
                if r.resolved:
                    lines.append(f"| {name} | {r.peak:.2f} | {r.minimum:.2f} | {r.oscillation:.2f} | "
                                 f"{r.steady_average_max:.2f} | {r.steady_peak_max:.2f} | {r.windows} | {r.steps} | "
                                 f"{r.seconds:.2f} |")
                else:
                    lines.append(f"| {name} | {r.steady_average_max:.2f} (all heaters averaged) | - | - | "
                                 f"{r.steady_average_max:.2f} | {r.steady_peak_max:.2f} | - | - | {r.seconds:.2f} |")
        return lines

    def to_text(self):
        """!
        @brief The comparison table as aligned plain text, followed by the warnings.
        @return String.
        """
        head = f"{'model':9s} {'Tmax C':>8s} {'Tmean C':>8s} {'dT C':>8s} {'Rth K/W':>8s} {'P W':>7s} {'balance':>9s} " \
               f"{'vs ' + self.reference.model:>9s} {'time s':>7s}"
        lines = [head, "-" * len(head)]
        for r in self.table():
            lines.append(f"{r['model']:9s} {r['t_max_c']:8.2f} {r['t_mean_c']:8.2f} {r['delta_t_k']:8.2f} "
                         f"{r['r_theta_k_per_w']:8.3f} {r['power_in_w']:7.3f} {r['energy_balance']:+9.0e} "
                         f"{r['error_vs_reference'] * 100:+8.1f}% {r['seconds']:7.2f}")
        for w in self.warnings:
            lines.append(f"WARNING: {w}")
        return "\n".join(lines) + "\n"

    def report(self):
        """!
        @brief Plain-text report with the table, hotspots, zones and heaters (reference model).
        @return String.
        """
        ref = self.reference
        lines = [f"PCB Thermal Lab {__version__} - report: {self.problem.name}",
                 f"Board {self.problem.board.width * 1000:.1f} x {self.problem.board.height * 1000:.1f} mm, "
                 f"{self.problem.board.layers} layers, ambient {self.problem.board.ambient:g} degC, "
                 f"total power {self.problem.total_power():.3f} W", "", self.to_text()]
        if self.h_used:
            b = self.problem.board
            lines.append("")
            lines.append(f"Heat transfer coefficients computed from correlations (emissivity {b.emissivity_top:g} top, "
                         f"{b.emissivity_bottom:g} bottom, {b.orientation} board{' (' + b.natural_form + ' form)' if b.orientation == 'vertical' else ''}, air speed {b.air_speed:g} m/s, "
                         f"convection multiplier {b.h_calibration:g}):")
            for name, (ht, hb) in self.h_used.items():
                e = self.results[name].extras
                lines.append(f"  {name}: top {ht:.2f} W/m2K (convection {e['h_top_convection']:.2f} + radiation "
                             f"{e['h_top_radiation']:.2f}), bottom {hb:.2f} W/m2K (convection {e['h_bottom_convection']:.2f} + "
                             f"radiation {e['h_bottom_radiation']:.2f}), {int(e['h_iterations'])} iterations")
        if self.decisions:
            lines.append("")
            lines.append(f"Power profiles (steady models use the {self.options.steady_power} power; decision from the "
                         f"{self.profile_reference} step response, threshold {self.options.profile.threshold_c:g} C):")
            for d in self.decisions:
                if d.kind != "constant":
                    lines.append(f"  {d.name}: {'period' if d.repeat else 'one-shot, length'} {d.period:g} s, duty {_duty_text(d)}, "
                                 f"average {d.average_power:.3f} W, "
                                 f"on {d.peak_power:.3f} W, oscillation {d.oscillation:.2f} C "
                                 f"({d.oscillation_percent:.1f} % of the rise) -> {d.regime}")
                else:
                    lines.append(f"  {d.name}: constant {d.average_power:.3f} W")
            for name, r in self.profile_results.items():
                if r.resolved:
                    lines.append(f"  {name}: peak {r.peak:.2f} C, minimum {r.minimum:.2f} C, oscillation {r.oscillation:.2f} C "
                                 f"(steady with the average power {r.steady_average_max:.2f} C, with the peak power "
                                 f"{r.steady_peak_max:.2f} C); {r.windows} windows, {r.steps} steps, "
                                 f"{'stable' if r.converged else 'not stable'}")
                else:
                    lines.append(f"  {name}: every heater averaged; steady {r.steady_average_max:.2f} C")
        if ref.T is not None:
            lines.append(f"Reference model: {ref.model}")
            hs = hotspots(ref, self.options.hotspot_c)
            lines.append(f"Hotspots above {self.options.hotspot_c:g} degC: {len(hs)}")
            for h in hs[:10]:
                lines.append(f"  layer {h['layer']}: {h['t_max']:.1f} degC at ({h['x_mm']:.1f}, {h['y_mm']:.1f}) mm, "
                             f"{h['area_mm2']:.1f} mm2")
            for h in self.heater_rows():
                extra = f", junction {h['t_junction']:.1f} degC" if h["t_junction"] is not None else ""
                if h["t_ring"] is not None and h["theta"] > 0:
                    extra += f", board ring {h['t_ring']:.1f} degC"
                if h["t_junction_psi"] is not None:
                    extra += f", junction by psi_JB {h['t_junction_psi']:.1f} degC"
                if h["power_top_w"] > 0:
                    extra += f", top path {h['power_top_w']:.2f} W ({100.0 * h['power_top_w'] / h['power_w']:.0f} % of the power, {h['r_top']:.1f} K/W)"
                if h["margin_k"] is not None:
                    extra += f", limit {h['tj_max']:g} degC (margin {h['margin_k']:.1f} K, power limit {h['p_limit_w']:.2f} W)"
                nominal = f", {h['power_nominal_w']:.2f} W nominal" if abs(h["power_w"] - h["power_nominal_w"]) > 1e-9 else ""
                lines.append(f"Heater {h['name']} (layer {h['layer']}, {h['power_w']:.2f} W{nominal}): "
                             f"mean {h['t_mean']:.1f}, max {h['t_max']:.1f} degC{extra}")
            for z in zone_stats(ref, self.problem):
                lines.append(f"Zone {z['name']} (layer {z['layer']}): mean {z['t_mean']:.1f}, "
                             f"max {z['t_max']:.1f}, min {z['t_min']:.1f} degC")
            for k in block_stats(ref, self.problem):
                lines.append(f"Metal block {k['name']} ({k['face']} face): mean {k['t_mean']:.1f}, max {k['t_max']:.1f} degC; "
                             f"{k['w_to_block']:.2f} W enter it through the interface, {k['w_to_air']:.2f} W leave by its surface")
        return "\n".join(lines) + "\n"

    def to_dict(self):
        """!
        @brief JSON-ready summary of the whole simulation.
        @return Dict with options, table and per-model summaries.
        """
        d = {"version": __version__, "problem": self.problem.name, "options": self.options.to_dict(), "table": self.table(),
             "models": {k: r.summary() for k, r in self.results.items()}}
        if self.decisions:
            d["profile"] = {"reference": self.profile_reference, "error": self.profile_error,
                            "models": {k: r.summary() for k, r in self.profile_results.items()}}
        return d

    def save(self, directory, plots=True):
        """!
        @brief Write summary.json, report.txt, one CSV per field and, optionally, the figures.
        @param directory Output directory (created if needed).
        @param plots If True, also write PNG figures (needs matplotlib).
        @return List of written file paths.
        """
        os.makedirs(directory, exist_ok=True)
        written = []

        def path(name):
            p = os.path.join(directory, name)
            written.append(p)
            return p

        with open(path("summary.json"), "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)
        with open(path("report.txt"), "w", encoding="utf-8") as fh:
            fh.write(self.report())
        for name, r in self.results.items():
            if r.T is None:
                continue
            with open(path(f"field_{name}.csv"), "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["layer", "x_mm", "y_mm", "T_c"])
                for l in range(r.T.shape[0]):
                    for i in range(r.T.shape[1]):
                        for j in range(r.T.shape[2]):
                            w.writerow([l + 1, round((j + 0.5) * r.dx * 1000, 4),
                                        round((i + 0.5) * r.dy * 1000, 4), round(float(r.T[l, i, j]), 4)])
        for name, r in self.profile_results.items():
            if not r.resolved:
                continue
            with open(path(f"profile_{name}.csv"), "w", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(["t_s", "Tmax_c"] + [f"T_{d.name}_c" for d in self.decisions])
                for k in range(len(r.times)):
                    w.writerow([round(float(r.times[k]), 6), round(float(r.t_max[k]), 4)] +
                               [round(float(r.t_heaters[j, k]), 4) for j in range(len(self.decisions))])
        if plots:
            from . import plots
            for name, r in self.profile_results.items():
                if r.resolved:
                    plots.plot_profile_series(r, self.problem, path(f"profile_{name}.png"))
                    plots.plot_peak_map(r, self.problem, path(f"peak_map_{name}.png"))
            for name, r in self.results.items():
                if r.T is not None:
                    plots.plot_fields(r, self.problem, path(f"fields_{name}.png"))
            if len(self.results) > 1:
                plots.plot_comparison(self.results, path("comparison.png"))
            plots.plot_profiles(self.results, self.problem, path("profiles.png"))
        return written


def suggest_cell_mm(problem, lo=0.25, hi=2.0):
    """!
    @brief Cell size that resolves the smallest heater with about four cells across its narrow side.
    @param problem A Problem.
    @param lo Smallest cell size returned (mm).
    @param hi Largest cell size returned (mm).
    @return Cell size in millimetres, clipped to [lo, hi]; hi when there is no heater.
    """
    sizes = [min(np.ptp(h.polygon[:, 0]), np.ptp(h.polygon[:, 1])) * 1000.0 for h in problem.heaters if h.power > 0]
    if not sizes:
        return hi
    return float(min(max(min(sizes) / 4.0, lo), hi))


def _solve_with_tc(problem, name, options, computed):
    """!
    @brief Solve one model, iterating on the powers when a heater has a power temperature coefficient or a top path.
    @details P = P0 (1 + tc (Tj - 25 degC)) with Tj the junction (or the hottest board point under a part without theta); with a top path (theta_sa) the part sends
             part of P to the ambient through the top and only the rest enters the board (analysis.part_split). Both are a fixed-point loop around the solve,
             like the computed heat transfer coefficients; the board receives the power that is not taken by the top. Without either it is a plain solve.
             The loop stops when the board powers change by less than 1e-5 (relative), or reports a thermal runaway when the device passes 1500 degC or the
             power grows 50 times (no stable operating point); after 80 iterations without either it warns that the powers did not settle.
    @param problem A Problem (steady powers; it is not modified).
    @param name Model name.
    @param options SolverOptions.
    @param computed True when the board uses computed heat transfer coefficients.
    @return Tuple (SteadyResult, (h_top, h_bottom) or None, list of total powers dissipated by the parts or None).
    """
    def once(pr):
        if computed:
            res, ht, hb, _ = _solve_computed_h(pr, name, options)
            return res, (ht, hb)
        return _run_model(pr, name, options), None

    tcs = [h.power_tc for h in problem.heaters]
    tops = [h.top_resistance() > 0 for h in problem.heaters]
    if not any(tcs) and not any(tops):
        res, hh = once(problem)
        return res, hh, None
    base = [h.power for h in problem.heaters]
    pr = copy.deepcopy(problem)
    totals = list(base)                      # Power dissipated by every part
    board = list(base)                       # Power that enters the board (the total minus the top path)
    runaway, settled = False, False
    for it in range(1, 81):
        for h, pw in zip(pr.heaters, board):
            h.power = pw
        res, hh = once(pr)
        amb = res.ambient
        new_total, new_board = [], []
        for h, row, b, tc in zip(problem.heaters, heater_stats(res, problem, totals), base, tcs):
            mx = row["t_max"]
            device = row["t_junction"] if row["t_junction"] is not None else mx
            total = max(b * (1.0 + tc * (device - 25.0)), 0.0) if tc else b
            _, p_top = part_split(h, mx, total, amb)
            new_total.append(total)
            new_board.append(total - p_top)
            runaway = runaway or device > 1500.0 or (b > 0 and total > 50.0 * b)
        change = max((abs(a - c) / max(c, 1e-9) for a, c in zip(new_board, board)), default=0.0)
        if runaway or change < 1e-5:
            settled = not runaway
            break                                                   # `totals` still pairs with the board power of the last solve
        totals, board = new_total, new_board
    res.extras["power_tc_iterations"] = float(it)
    res.extras["thermal_runaway"] = float(runaway)
    if runaway:
        res.warnings.append("no stable operating point: the power grows faster with temperature than the board removes heat (thermal runaway)")
    elif not settled:
        # Close to runaway the fixed point converges slowly; the result is the last iterate, not the operating point
        res.warnings.append(f"the powers of the parts did not settle in {it} iterations (last relative change {change:.1e}): "
                            "the board is close to thermal runaway and the temperatures are underestimated")
    return res, hh, totals


def _block_flux_result(sim):
    """!
    @brief The result that carries the heat flux into the metal blocks, for the thick-plate warning.
    @details The reference result of the FVM or FDM has it. For the other models (Lumped, Analytic, 3D solid) a quiet auxiliary FVM run of the same
             problem (steady power, cell of at least 2 mm, no other model, its own warnings dropped) gives it, so the warning rests on a simulation and
             not on the flux of the footprint, which overstates a block under the board 5 to 70 times. Nothing is run without a metal block.
    @param sim Simulation with its results.
    @return SteadyResult with arrays["block_flux"], or the reference result when no such run is possible (the check then falls back to the footprint flux).
    """
    ref = sim.reference
    if "block_flux" in ref.arrays or not blocks.has_blocks(sim.problem):
        return ref
    try:
        steady = sim.problem.steady_copy(sim.options.steady_power) if sim.problem.has_profiles() else sim.problem
        aux = simulate(steady, SolverOptions(models=("fvm",), cell_mm=max(sim.options.cell_mm, 2.0)))
    except ValueError:
        return ref
    return aux.reference


def _part_warnings(sim):
    """!
    @brief Warnings about the parts after the solves: junction above its limit, a theta that is probably not a junction-to-pad value, unused coefficients.
    @param sim Simulation with its results.
    @return List of strings.
    """
    out = []
    runaway = any(r.extras.get("thermal_runaway") for r in sim.results.values())
    for row, h in zip(sim.heater_rows(), sim.problem.heaters):
        if row["margin_k"] is not None and row["margin_k"] < 0 and not runaway:
            out.append(f"{row['name']}: the junction reaches {row['t_junction'] if row['t_junction'] is not None else row['t_max']:.1f} degC, "
                       f"{-row['margin_k']:.1f} K above its limit of {row['tj_max']:g} degC (power limit {row['p_limit_w']:.2f} W with this board)")
        if h.is_component() and h.theta > 0 and row["power_board_w"] * h.theta > max(row["t_max"] - sim.reference.ambient, 0.0) > 0:
            out.append(f"{row['name']}: theta x P = {row['power_board_w'] * h.theta:.1f} K is larger than the board's own rise under the part "
                       f"({row['t_max'] - sim.reference.ambient:.1f} K): check that theta is a junction-to-pad number (theta_JC(bot), theta_J-L) and not theta_JA")
    out += check_thick_plates(sim.problem, sim.heater_rows(), _block_flux_result(sim))
    if sim.problem.has_profiles() and any(h.power_tc for h in sim.problem.heaters):
        out.append("the power temperature coefficient is applied to the steady-state models only, not to the time simulation")
    if sim.problem.has_profiles() and any(h.top_resistance() > 0 for h in sim.problem.heaters):
        out.append("the top path (heatsink on the package) is applied to the steady-state models only: the time simulation sends all the power into the board")
    return out


def _run_model(problem, name, o):
    """!
    @brief Run one model with the matching options.
    @param problem The Problem.
    @param name Model name.
    @param o SolverOptions.
    @return SteadyResult.
    """
    if name in RECTANGLE_ONLY and problem.board.has_outline():
        # Solve the rectangle of the same area, then stretch the field back over the real box (the cells outside the outline are blanked by the plots)
        eq, s = problem.equivalent_rectangle()
        res = _run_model(eq, name, o)
        res.dx, res.dy = res.dx / s, res.dy / s
        if res.t_max_location is not None:
            layer, x, y = res.t_max_location
            res.t_max_location = (layer, x / s, y / s)
        res.warnings.append(f"the board has an outline: computed on a rectangle of the same area (box and positions scaled by {s:.3f}); expect a few percent of "
                            "difference, more for parts near the edge or in a narrow arm; the FVM, FDM and 3D solid use the real shape")
        return res
    if name == "fvm":
        return fvm.solve_steady(problem, cell_mm=o.cell_mm, method=o.linear_solver)
    if name == "fdm":
        return fdm.solve_steady(problem, cell_mm=o.cell_mm)
    if name == "solid3d":
        return solid3d.solve_steady(problem, cell_mm=o.cell_mm)
    if name == "lumped":
        return lumped.solve_steady(problem, rings=o.lumped_rings, cell_mm=min(max(o.cell_mm, 0.5), 1.0))
    return analytic.solve_steady(problem, cell_mm=min(max(o.cell_mm, 0.5), 1.0), n_terms=o.analytic_modes,
                                 local_corrections=o.analytic_local_corrections)


def _duty_text(d):
    """!
    @brief Duty of a decision as text: a percentage for a square wave, a dash for a table.
    @param d HeaterDecision.
    @return String.
    """
    return "-" if d.duty != d.duty else f"{d.duty:.0%}"       # NaN is the only value that differs from itself


def _solve_computed_h(problem, name, o):
    """!
    @brief Steady solution with the face coefficients computed from the correlations (Picard iteration).
    @details h_top and h_bottom depend on the mean face temperature, which depends on h: the model is solved, the
             coefficients are recomputed from the mean temperature of the top and bottom layers, and the loop repeats until
             they change by less than 0.01 W/m2K (typically 3 to 6 solves). The edge coefficient stays as typed.
    @param problem A Problem whose board has h_mode "computed".
    @param name Model name.
    @param o SolverOptions.
    @return Tuple (SteadyResult, h_top, h_bottom, iterations).
    """
    p = copy.deepcopy(problem)
    b = p.board
    ht, hb = b.h_top, b.h_bottom                    # The typed values are the starting guess
    res, it = None, 0
    for it in range(1, 31):
        b.h_top, b.h_bottom = ht, hb
        res = _run_model(p, name, o)
        # The bottom face of a one-layer board is its last laminate node (laminate.py), not the copper node
        nt, nb, info = convection.board_h(problem.board, res.layer_mean[0], res.extras.get("bottom_face_mean", res.layer_mean[-1]))
        done = abs(nt - ht) < 0.01 and abs(nb - hb) < 0.01
        ht, hb = nt, nb
        if done:
            break
    # Report the coefficients that produced the result (the last solve used the previous pair, within 0.01)
    res.extras.update({"h_top": ht, "h_bottom": hb, "h_iterations": float(it),
                       "h_top_convection": info["top"]["convection"], "h_top_radiation": info["top"]["radiation"],
                       "h_bottom_convection": info["bottom"]["convection"], "h_bottom_radiation": info["bottom"]["radiation"]})
    if problem.board.orientation == "horizontal" and not 1e4 <= info["top"]["rayleigh"] <= 1e11:
        res.warnings.append(f"the top-face Rayleigh number {info['top']['rayleigh']:.2g} is outside 1e4 to 1e11, "
                            "where the natural-convection correlation was fitted; the coefficient is an extrapolation")
    if problem.board.orientation == "vertical" and problem.board.natural_form == "laminar" and info["top"]["rayleigh"] > 1e9:
        # The laminar form of Churchill and Chu is meant for Ra below 1e9 (a board of about 0.5 m or more); the general form covers the whole range
        res.warnings.append(f"the Rayleigh number {info['top']['rayleigh']:.2g} is above 1e9, outside the laminar form of the vertical-plate correlation: "
                            "choose the general form")
    if it == 30 and not done:
        res.warnings.append("the computed heat transfer coefficients did not settle in 30 iterations")
    return res, ht, hb, it


def calibrate_convection(problem, measured_c, options=None, model="fvm", heater=None):
    """!
    @brief Fit the convection multiplier (Board.h_calibration) so that the model reproduces a measured temperature.
    @details The board is put in computed mode and the multiplier is found by bisection on its logarithm (the temperature falls
             as the multiplier grows). The measured quantity is the hottest point of the board, or the hottest point under a
             named heater. The correlations are for isothermal plates and uncertain by 20 to 30 % on a board with hot spots;
             this turns one measurement into the correction. Use a measurement taken in steady state, with the same power,
             and note that the multiplier absorbs every other model error (copper, vias, enclosure) at that operating point.
    @param problem A Problem (it is not modified).
    @param measured_c Measured steady temperature in degC.
    @param options SolverOptions (default: 1 mm cell); only the chosen model is run.
    @param model "fvm" (default), "lumped" or "analytic".
    @param heater Name of the heater whose footprint maximum was measured; None for the board maximum.
    @return Tuple (multiplier, model temperature with it in degC).
    @throws ValueError If the measured value is not between the temperatures with multipliers 0.1 and 10.
    """
    from .analysis import heater_stats
    options = copy.deepcopy(options) if options else SolverOptions()
    options.models = (model,)
    p = copy.deepcopy(problem)
    p.board.h_mode = "computed"
    steady = p.steady_copy(options.steady_power) if p.has_profiles() else p

    def predicted(multiplier):
        steady.board.h_calibration = multiplier
        res = _solve_computed_h(steady, model, options)[0]
        if heater is None:
            return res.t_max
        rows = [r for r in heater_stats(res, steady) if r["name"] == heater]
        if not rows:
            raise ValueError(f"no heater named '{heater}'")
        return rows[0]["t_max"]

    lo, hi = math.log(0.1), math.log(10.0)
    if not predicted(math.exp(hi)) <= measured_c <= predicted(math.exp(lo)):
        raise ValueError(f"the measured {measured_c:g} degC is outside what a multiplier between 0.1 and 10 can give "
                         f"({predicted(math.exp(hi)):.1f} to {predicted(math.exp(lo)):.1f} degC): check the powers, the ambient "
                         "temperature and where the measurement was taken")
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if predicted(math.exp(mid)) > measured_c:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-3:
            break
    m = math.exp(0.5 * (lo + hi))
    return m, predicted(m)


def step_response(problem, model, options):
    """!
    @brief Unit-step responses of the heaters with one model (the input of the average-or-resolve decision).
    @param problem A Problem with at least one heater.
    @param model "fvm", "lumped" or "analytic".
    @param options SolverOptions.
    @return profiles.StepResponse.
    """
    if model == "fvm":
        return profiles.step_response_fvm(problem, cell_mm=max(options.cell_mm, 2.0))
    if model == "fdm":
        return profiles.step_response_fdm(problem, cell_mm=max(options.cell_mm, 2.0))
    if model == "lumped":
        t, z, r = lumped.step_responses(problem, rings=options.lumped_rings, cell_mm=min(max(options.cell_mm, 0.5), 1.0))
    else:
        t, z, r = analytic.step_responses(problem, cell_mm=min(max(options.cell_mm, 0.5), 1.0), n_terms=options.analytic_modes)
    return profiles.StepResponse(model, t, z, r)


def _run_profiles(sim, progress, start):
    """!
    @brief Decide average-or-resolve for every heater and simulate the profiles with every selected model.
    @details The decision is made once, with the most reliable selected model (FVM, then lumped, then analytic), and
             applied to all models. A run that is too expensive is reported in sim.profile_error, never raised.
    @param sim Simulation with the steady results already filled in.
    @param progress Optional callback progress(message, fraction).
    @param start Progress fraction at which this stage starts.
    """
    o = sim.options
    p = sim.effective_problem or sim.problem
    # The lumped and analytic models have no time simulation on a board with an outline (the rectangle of the same area is a steady-state device)
    # Lumped and Analytic have no time simulation with a metal block either (the block layer is a steady-state aggregation)
    usable = tuple(m for m in o.models if not (m in RECTANGLE_ONLY and (p.board.has_outline() or blocks.has_blocks(p))))
    left_out = [m for m in o.models if m in RECTANGLE_ONLY and m not in usable]
    if left_out:
        sim.problem_warnings.append("time simulation not run for " + ", ".join(left_out) + " (no time simulation with a metal block or an outline)")
    ref = next((m for m in TIME_MODELS if m in usable), None)     # The FDM only if nothing else is selected; the 3D solid has no time simulation
    if ref is None:
        sim.profile_error = "select the FVM or the FDM (or Lumped/Analytic on a rectangular board) for the time simulation (the 3D solid is steady state only)"
        return
    sim.profile_reference = ref
    if progress:
        progress("Thermal response of the heaters", start)
    t0 = time.time()
    try:
        resp = step_response(p, ref, o)
        sim.decisions = profiles.decide(p, resp, o.profile.threshold_c)
        sim.step_response = resp
        for name in usable:
            if name == "solid3d":
                continue
            if progress:
                progress(f"Time simulation: {name}", start + 0.1)
            if name == "fvm":
                sim.profile_results[name] = profiles.run_fvm(p, sim.decisions, o.profile, o.cell_mm)
            elif name == "fdm":
                sim.profile_results[name] = profiles.run_fdm(p, sim.decisions, o.profile, o.cell_mm)
            elif name == "lumped":
                sim.profile_results[name] = lumped.run_profile(p, sim.decisions, o.profile, o.lumped_rings,
                                                               min(max(o.cell_mm, 0.5), 1.0))
            else:
                sim.profile_results[name] = analytic.run_profile(p, sim.decisions, o.profile,
                                                                 min(max(o.cell_mm, 0.5), 1.0), o.analytic_modes)
    except profiles.ProfileError as exc:
        sim.profile_error = str(exc)
    sim.seconds["profile"] = time.time() - t0


def default_options():
    """!
    @brief The solver settings a new project starts with: the defaults of the program (defaults.json plus the user's file).
    @return SolverOptions (the models of the defaults that exist; at least the FVM).
    """
    d = defaults.load()["solver"]
    o = SolverOptions()
    models = tuple(m for m in d.get("models", ()) if m in MODEL_NAMES + COMPARISON_MODELS) or ("fvm",)
    for key, val in (("models", models), ("cell_mm", d.get("cell_mm")), ("linear_solver", d.get("linear_solver")), ("lumped_rings", d.get("lumped_rings")),
                     ("analytic_modes", d.get("analytic_modes")), ("hotspot_c", d.get("hotspot_c"))):
        if val is not None:
            setattr(o, key, val)
    try:
        o.validate()
    except ValueError:                                   # A bad user value: fall back to the built-in settings
        o = SolverOptions()
    return o


def simulate(problem, options=None, progress: Optional[Callable[[str, float], None]] = None):
    """!
    @brief Run the selected models on a problem.
    @param problem A Problem (it is validated first).
    @param options SolverOptions; defaults run all three models with a 1 mm cell.
    @param progress Optional callback progress(message, fraction) called before every model.
    @return Simulation.
    @throws ValueError If the problem or the options are invalid.
    """
    options = options or SolverOptions()
    options.validate()
    problem.validate()
    sim = Simulation(problem=problem, options=options, problem_warnings=check_problem(problem, options.cell_mm))
    steady_problem = problem.steady_copy(options.steady_power) if problem.has_profiles() else problem
    computed = problem.board.h_mode == "computed"
    n = len(options.models) + (1 if problem.has_profiles() else 0)
    for k, name in enumerate(options.models):
        if progress:
            progress(f"Solving {name}", k / n)
        t0 = time.time()
        try:
            sim.results[name], hh, powers = _solve_with_tc(steady_problem, name, options, computed)
            if hh is not None:
                sim.h_used[name] = hh
            if powers is not None:
                sim.power_used[name] = powers
        except ValueError as exc:
            if name != "solid3d" or len(options.models) == 1:
                raise
            sim.problem_warnings.append(f"the 3D solid was not run: {exc}")        # Too large: the other models still answer
            continue
        sim.seconds[name] = time.time() - t0
    if blocks.has_blocks(problem):
        for name, how in (("lumped", "one more layer of the ring network"), ("analytic", "a graph of tiles in the Green-function correction")):
            if name in sim.results:
                sim.results[name].warnings.append(f"the metal block is represented as {how}: within about 5 % of the FVM in the tests (docs/validation.md section 17); "
                                                  "steady state only")
    sim.part_warnings = _part_warnings(sim) if sim.results else []
    if computed:
        ref = next((m for m in MODEL_NAMES + COMPARISON_MODELS if m in options.models))
        # Later stages (time simulation, animation) use the coefficients of the reference model, fixed during the cycle
        sim.effective_problem = copy.deepcopy(problem)
        sim.effective_problem.board.h_mode = "manual"
        sim.effective_problem.board.h_top, sim.effective_problem.board.h_bottom = sim.h_used[ref]
    if problem.has_profiles():
        _run_profiles(sim, progress, len(options.models) / n)
    if progress:
        progress("Done", 1.0)
    return sim
