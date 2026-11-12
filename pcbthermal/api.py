#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
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

from . import __version__, analytic, blocks, convection, copper, fdm, fvm, laminate, lumped, memory, profiles, solid3d
from .analysis import block_stats, part_split, heater_stats, hotspots, zone_stats
from . import defaults
from . import uicontext
from .checks import check_fin_channels, check_input, check_low_rayleigh, check_lumped_zones, check_thick_plates
from .model import Problem
from .results import SteadyResult
from .numfmt import num

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
    laminate_s_max_mm: float = 0.4               # Longest sub-gap of the laminate between two copper nodes in mm (FVM and FDM; laminate.py)
    laminate_n_max: int = 4                      # Most sub-gaps in one gap, count (1 turns the cutting off; the error against a resolved 3D solid falls as 1/n); a gap gets min(n_max, ceil(d / s_max)), so a larger n_max needs a smaller s_max
    # A machine preference (Preferences, solver.memory_fraction), not part of a project: never saved in the project file, and an old file that has the key ignores it
    memory_fraction: float = field(default_factory=memory.default_fraction)   # Share of the physical memory a solve may use; a run above it is refused (memory.py)
    profile: profiles.ProfileOptions = field(default_factory=profiles.ProfileOptions)   # Time-simulation settings
    # The front end that launched the run, which decides how the warnings name the controls ('gui' the window, 'cli' the command line and the API); never saved in a project
    ui: str = "cli"

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
        if self.ui not in uicontext.UIS:
            raise ValueError(f"ui must be one of {uicontext.UIS}")
        if self.steady_power not in ("average", "peak"):
            raise ValueError("steady_power must be 'average' or 'peak'")
        if not memory.MIN_FRACTION <= self.memory_fraction <= memory.MAX_FRACTION:
            raise ValueError(f"memory_fraction must be between {memory.MIN_FRACTION} and {memory.MAX_FRACTION}")
        if not 0.05 <= self.laminate_s_max_mm <= 5.0:
            raise ValueError("laminate_s_max_mm must be between 0.05 and 5")
        if not isinstance(self.laminate_n_max, int) or isinstance(self.laminate_n_max, bool) or not 1 <= self.laminate_n_max <= 16:
            raise ValueError("laminate_n_max must be an integer between 1 and 16")
        self.profile.validate()

    def laminate_params(self):
        """!
        @brief The two numbers of the laminate rule in SI units, for laminate.using().
        @return Tuple (s_max in m, n_max).
        """
        return self.laminate_s_max_mm * 1e-3, self.laminate_n_max

    def to_dict(self):
        """!
        @brief JSON-ready dictionary.
        @return Dict of the options.
        """
        d = asdict(self)
        d.pop("memory_fraction", None)                  # The memory limit belongs to the machine, not to the project
        d.pop("ui", None)                               # The front end belongs to the session, not to the project
        # The laminate numbers are saved only when they are not the default, so that projects of the earlier versions are written as before
        for key, default in (("laminate_s_max_mm", 0.4), ("laminate_n_max", 4)):
            if d.get(key) == default:
                d.pop(key, None)
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
        known = {k: v for k, v in (data or {}).items() if k in cls.__dataclass_fields__ and k not in ("memory_fraction", "ui")}   # Old files may hold the key: ignored
        if "models" in known:
            known["models"] = tuple(known["models"])
        known["profile"] = profiles.ProfileOptions.from_dict(known.get("profile"))
        # A JSON writer may give the count as 8.0: an integer-valued float is the integer (any other float still fails validation)
        n = known.get("laminate_n_max")
        if isinstance(n, float) and n.is_integer():
            known["laminate_n_max"] = int(n)
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
                         f"{r['r_theta_k_per_w']:.3f} | {r['power_in_w']:.3f} | {num(r['energy_balance'], sign=True)} | "
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
                     f"threshold {num(self.options.profile.threshold_c)} °C):", "",
                 "| Heater | Period [s] | Duty | Average [W] | Peak [W] | Oscillation [°C] | % of rise | Decision |",
                 "| :-- | --: | --: | --: | --: | --: | --: | :-- |"]
        for d in self.decisions:
            if d.kind != "constant":
                lines.append(f"| {d.name} | {num(d.period)}{'' if d.repeat else ' (once)'} | {_duty_text(d)} | {d.average_power:.3f} | {d.peak_power:.3f} | "
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
            for name, r in self.profile_results.items():
                for x in r.ripple:
                    lines.append(f"\n> **Ripple ({name})**: {x['name']} is held at its average power in the board run and its wave of {num(x['swing_c'], 3)} °C peak to peak "
                                 f"({num(x['minus_c'], 3)} to +{num(x['plus_c'], 3)} °C about its mean, from the closed-form impedance of the stack) is added at the heater, "
                                 "in the peak and the minimum above and not in the maps.")
        return lines

    def to_text(self, inline_warnings=True):
        """!
        @brief The comparison table as aligned plain text, followed by the warnings.
        @param inline_warnings True: every warning is a `WARNING:` paragraph (the saved report, the command line); False: one closing line says how many there are
                               and that the Warnings list of the window shows them (the on-screen report, which sits under that list).
        @return String.
        """
        head = f"{'model':9s} {'Tmax C':>8s} {'Tmean C':>8s} {'dT C':>8s} {'Rth K/W':>8s} {'P W':>7s} {'balance':>9s} " \
               f"{'vs ' + self.reference.model:>9s} {'time s':>7s}"
        lines = [head, "-" * len(head)]
        for r in self.table():
            lines.append(f"{r['model']:9s} {r['t_max_c']:8.2f} {r['t_mean_c']:8.2f} {r['delta_t_k']:8.2f} "
                         f"{r['r_theta_k_per_w']:8.3f} {r['power_in_w']:7.3f} {num(r['energy_balance'], sign=True):>9} "
                         f"{r['error_vs_reference'] * 100:+8.1f}% {r['seconds']:7.2f}")
        if inline_warnings:
            for w in self.warnings:
                lines += ["", f"WARNING: {w}"]                               # A blank line before each warning keeps the list readable (as the Summary tab and the Markdown report)
        elif self.warnings:
            n = len(self.warnings)
            lines += ["", f"({n} warning{'s' if n != 1 else ''}: see the Warnings list above; the saved report keeps {'them' if n != 1 else 'it'}.)"]
        return "\n".join(lines) + "\n"

    def report(self, inline_warnings=True):
        """!
        @brief Plain-text report with the table, hotspots, zones and heaters (reference model).
        @param inline_warnings True (default, the saved report): the warnings follow the table as `WARNING:` paragraphs; False (the on-screen report): one closing line points to the Warnings list.
        @return String.
        """
        ref = self.reference
        lines = [f"PCB Thermal Lab {__version__} - report: {self.problem.name}",
                 f"Board {self.problem.board.width * 1000:.1f} x {self.problem.board.height * 1000:.1f} mm, "
                 f"{self.problem.board.layers} layers, ambient {num(self.problem.board.ambient)} degC, "
                 f"total power {self.problem.total_power():.3f} W", "", self.to_text(inline_warnings)]
        if self.h_used:
            b = self.problem.board
            lines.append("")
            lines.append(f"Heat transfer coefficients computed from correlations (emissivity {num(b.emissivity_top)} top, "
                         f"{num(b.emissivity_bottom)} bottom, {b.orientation} board{' (' + b.natural_form + ' form)' if b.orientation == 'vertical' else ''}, air speed {num(b.air_speed)} m/s, "
                         f"convection multiplier {num(b.h_calibration)}):")
            for name, (ht, hb) in self.h_used.items():
                e = self.results[name].extras
                lines.append(f"  {name}: top {ht:.2f} W/m2K (convection {e['h_top_convection']:.2f} + radiation "
                             f"{e['h_top_radiation']:.2f}), bottom {hb:.2f} W/m2K (convection {e['h_bottom_convection']:.2f} + "
                             f"radiation {e['h_bottom_radiation']:.2f}), {int(e['h_iterations'])} iterations")
        if self.decisions:
            lines.append("")
            lines.append(f"Power profiles (steady models use the {self.options.steady_power} power; decision from the "
                         f"{self.profile_reference} step response, threshold {num(self.options.profile.threshold_c)} C):")
            for d in self.decisions:
                if d.kind != "constant":
                    lines.append(f"  {d.name}: {'period' if d.repeat else 'one-shot, length'} {num(d.period)} s, duty {_duty_text(d)}, "
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
                for x in r.ripple:
                    lines.append(f"    {x['name']}: ripple {x['swing_c']:.3f} C peak to peak at the heater ({x['minus_c']:+.3f} to {x['plus_c']:+.3f} C about its mean, closed form of the stack), "
                                 "in the peak and the minimum, not in the maps")
        if ref.T is not None:
            lines.append(f"Reference model: {ref.model}")
            hs = hotspots(ref, self.options.hotspot_c)
            lines.append(f"Hotspots above {num(self.options.hotspot_c)} degC: {len(hs)}")
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
                    extra += f", limit {num(h['tj_max'])} degC (margin {h['margin_k']:.1f} K, power limit {h['p_limit_w']:.2f} W)"
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

    def save(self, directory, plots=True, view=None, cmap="inferno"):
        """!
        @brief Write summary.json, report.txt, one CSV per field and, optionally, the figures.
        @param directory Output directory (created if needed).
        @param plots If True, also write PNG figures (needs matplotlib).
        @param view Optional plots.MapView for the temperature maps (View, underlay such as the copper or the image, opacity: what the Display panel of the window says); None draws them as always.
        @param cmap Colour map name of the temperature maps.
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
                    plots.plot_fields(r, self.problem, path(f"fields_{name}.png"), view=view, cmap=cmap)
            if len(self.results) > 1:
                plots.plot_comparison(self.results, path("comparison.png"))
            plots.plot_profiles(self.results, self.problem, path("profiles.png"))
        return written


def suggest_cell_mm(problem, lo=0.25, hi=2.0, models=None, fraction=None, transient=False, base=memory.BASE_DEFAULT, laminate_params=None):
    """!
    @brief Cell size that resolves the smallest heater with about four cells across its narrow side, and that the memory guard accepts.
    @details When models are given, a cell that the guard would refuse for one of them (fvm, fdm, solid3d) is replaced by the smallest cell that fits (memory.cell_that_fits),
             which may be above hi: the memory wins over the resolution, and the caller says so (for a board with imported copper `copper.auto_cell_note(problem, cell)` is
             the sentence). A board with imported copper (mapping other than 'fill') is capped at copper.COARSE_CELL_MM (1 mm) before the memory is considered. Only the model keys are checked ("all" or "compare" must be
             expanded by the caller).
    @param problem A Problem.
    @param lo Smallest cell size returned from the heaters (mm).
    @param hi Largest cell size returned from the heaters (mm); also the answer when there is no heater.
    @param models Model keys the cell has to fit (None: the memory is not considered).
    @param fraction Share of the physical memory allowed (None: memory.default_fraction()).
    @param transient True when the cell is for a time simulation (memory.TRANSIENT_FACTOR).
    @param base Resident bytes of the process that will solve: memory.BASE_DEFAULT for the calculation process of the window (default), None for this process
                (the command line solves in its own process).
    @param laminate_params Tuple (s_max in m, n_max) of the laminate rule that the run will use (None: the current values), because they change the unknowns the guard counts.
    @return Cell size in millimetres: the heater-based one clipped to [lo, hi], enlarged until the models fit.
    """
    sizes = [min(np.ptp(h.polygon[:, 0]), np.ptp(h.polygon[:, 1])) * 1000.0 for h in problem.heaters if h.power > 0]
    cell = float(min(max(min(sizes) / 4.0, lo), hi)) if sizes else hi
    # Imported copper wants a cell of 1 mm or less (the faces read 7 to 10 % too hot at 2 mm): Auto stays there unless the memory forces more
    cell = copper.auto_cell_cap(problem, cell)
    if models:
        for v in memory.check(problem, tuple(models), cell, fraction=fraction, transient=transient, base=base, refuse="return", quiet=True, laminate_params=laminate_params):
            if v.verdict == "refuse" and v.cell_fit:
                cell = max(cell, v.cell_fit)
    return cell


def _top_path_split(problem, pr, totals, once, active):
    """!
    @brief Find the heat that enters the board from every part with a top path, for given total powers of the parts.
    @details The unknown of part i is P_b,i, the heat into the board. The part sends p_top,i = part_split(T_max,i(P_b)) to the ambient through its top, so the
             split is the root of g_i(P_b) = P_b,i - P_i + p_top,i = 0. A plain fixed-point iteration P_b <- P - p_top(T_max(P_b)) has the slope
             -R_b/(R_top + theta) (R_b: the board's resistance under the part) and diverges when it exceeds 1, which happens on small pads, so it is not used.
             g is monotone in P_b (g' = 1 + R_b/(R_top + theta) >= 1, 1 where part_split clips the top heat at P) with g(0) <= 0 <= g(P): the root is bracketed by [0, P].
             One part: Illinois regula falsi on [0, P]; with fixed face coefficients the board is affine in P_b, so the secant between the two ends gives
             the root at once (3 board solves in all) unless the top heat is clipped at P_b = P (R_b > R_top, the small pads: g has a kink, 6 solves);
             with computed coefficients (Picard loop inside every solve) it takes 6 to 7, and up to about 20 when the root is close to the clip.
             Several parts: their splits interact through the board; a Broyden quasi-Newton iteration on the vector P_b (starting Jacobian by finite
             differences with the wide steps P_b,j -> 0, exact for an affine board only when no top heat is clipped and the hottest cells do not move), projected
             on [0, P] and with step halving, solves the coupled system (measured on random boards of 2 to 4 parts: median 8 to 9 solves, 90 % within 25, at most 57).
    @param problem The Problem (not modified; owns the heaters and their top paths).
    @param pr Working copy of the problem whose heater powers are set here to the board powers.
    @param totals Power dissipated by every part in W (fixed during this solve).
    @param once Function pr -> (SteadyResult, (h_top, h_bottom) or None) that solves the board.
    @param active Indices of the parts with a top path and a junction (the others send all their power into the board).
    @return Tuple (SteadyResult, hh, board powers in W, number of board solves, converged flag).
    """
    count = [0]

    def evaluate(x):
        # One board solve with the board powers x of the active parts; returns the residuals g_i and the solution
        board = list(totals)
        for k, xi in zip(active, x):
            board[k] = float(xi)
        for h, pw in zip(pr.heaters, board):
            h.power = pw
        res, hh = once(pr)
        count[0] += 1
        rows = heater_stats(res, problem, totals)
        g = np.array([board[k] - totals[k] + part_split(problem.heaters[k], rows[k]["t_max"], totals[k], res.ambient)[1] for k in active])
        return g, res, hh, board

    scale = np.array([totals[k] for k in active])
    tol = 1e-5                                               # Relative to the part's power: far below the 0.1 K that matters
    best = None                                              # (worst relative residual, res, hh, board)

    def keep(g, res, hh, board):
        nonlocal best
        err = float(np.max(np.abs(g) / scale))
        if best is None or err < best[0]:
            best = (err, res, hh, board)
        return err

    if len(active) == 1:
        p = scale[0]
        g_hi, res, hh, board = evaluate(np.array([p]))       # All the power into the board: the first iterate of the old loop, g >= 0
        if keep(g_hi, res, hh, board) > tol:
            g_lo, res, hh, board = evaluate(np.array([0.0]))                # Nothing into the board: g <= 0
            if keep(g_lo, res, hh, board) > tol:
                glo, ghi, g_lo_v, g_hi_v, side = 0.0, p, float(g_lo[0]), float(g_hi[0]), 0
                for _ in range(40):
                    x = ghi - g_hi_v * (ghi - glo) / (g_hi_v - g_lo_v)      # Secant (regula falsi) between the ends of the bracket
                    g, res, hh, board = evaluate(np.array([x]))
                    if keep(g, res, hh, board) <= tol or ghi - glo < 1e-9 * p:
                        break
                    gv = float(g[0])
                    if gv > 0:                                               # Root below x: the upper end moves
                        ghi, g_hi_v = x, gv
                        if side == 1:
                            g_lo_v *= 0.5                                    # Illinois: halve the retained end so the bracket keeps shrinking
                        side = 1
                    else:
                        glo, g_lo_v = x, gv
                        if side == -1:
                            g_hi_v *= 0.5
                        side = -1
    else:
        n = len(active)
        x = scale.copy()
        g0, res, hh, board = evaluate(x)
        keep(g0, res, hh, board)
        if best[0] > tol:
            jac = np.empty((n, n))
            for j in range(n):
                xj = x.copy()
                xj[j] = 0.0
                gj, res, hh, board = evaluate(xj)
                keep(gj, res, hh, board)
                jac[:, j] = (g0 - gj) / scale[j]                        # dg/dP_b,j over the whole range
            g = g0
            for _ in range(40):
                try:
                    step = np.linalg.solve(jac, -g)
                except np.linalg.LinAlgError:
                    break
                lam = 1.0
                for _ in range(6):                                       # Halve the step until the projected trial does not make the residual worse
                    xn = np.clip(x + lam * step, 0.0, scale)
                    gn, res, hh, board = evaluate(xn)
                    err = keep(gn, res, hh, board)
                    if np.max(np.abs(gn) / scale) <= np.max(np.abs(g) / scale) or lam < 0.1:
                        break
                    lam *= 0.5
                if err <= tol:
                    break
                dx, dg = xn - x, gn - g
                if float(dx @ dx) > 0:
                    jac = jac + np.outer(dg - jac @ dx, dx) / float(dx @ dx)  # Broyden "good" update
                x, g = xn, gn
    err, res, hh, board = best
    # The best iterate is returned (for a converged run it is the last one); the board powers pair with it
    return res, hh, board, count[0], err <= 10 * tol


def _solve_with_tc(problem, name, options, computed):
    """!
    @brief Solve one model, iterating on the powers when a heater has a power temperature coefficient or a top path.
    @details P = P0 (1 + tc (Tj - 25 degC)) with Tj the junction (or the hottest board point under a part without theta); with a top path (theta_sa) the part sends
             part of P to the ambient through the top and only the rest enters the board (analysis.part_split).
             The power coefficient is a fixed-point loop around the solve, like the computed heat transfer coefficients: it stops when the powers change by less than
             1e-5 (relative), or reports a thermal runaway when the device passes 1500 degC or the power grows 50 times (no stable operating point; the slope of the loop
             alpha P0 R is the physical runaway condition); after 80 iterations without either it warns that the powers did not settle.
             The split of a part with a top path is not a fixed-point loop: for the powers of the parts it is the root of a monotone scalar equation per part, solved
             by _top_path_split (secant / quasi-Newton), because the fixed-point iteration diverges when the board under the part resists more than the top path.
             With both, the power coefficient loop goes around the top-path solve. Without either it is a plain solve.
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
    runaway, settled, split_ok, solves = False, False, True, 0
    change = 0.0
    # The parts are solved again and again with other powers (top-path split, power coefficient): with fixed face coefficients the board matrix repeats,
    # and its LU is reused within this block (FVM and FDM direct solve; fvm.factor_reuse)
    with fvm.factor_reuse():
        for it in range(1, 81):
            # Parts whose top heat must be solved for: a top path, a junction to hang it on, and some power
            active = [k for k, h in enumerate(problem.heaters) if tops[k] and h.junction_theta() > 0 and totals[k] > 0]
            if active:
                res, hh, board, n, ok = _top_path_split(problem, pr, totals, once, active)
                solves += n
                split_ok = split_ok and ok
            else:
                for h, pw in zip(pr.heaters, totals):
                    h.power = pw
                res, hh = once(pr)
                solves += 1
            new_total = []
            for h, row, b, tc in zip(problem.heaters, heater_stats(res, problem, totals), base, tcs):
                device = row["t_junction"] if row["t_junction"] is not None else row["t_max"]
                total = max(b * (1.0 + tc * (device - 25.0)), 0.0) if tc else b
                new_total.append(total)
                runaway = runaway or device > 1500.0 or (b > 0 and total > 50.0 * b)
            change = max((abs(a - c) / max(c, 1e-9) for a, c in zip(new_total, totals)), default=0.0)
            if runaway or change < 1e-5:
                settled = not runaway
                break                                                   # `totals` still pairs with the board power of the last solve
            totals = new_total
    res.extras["power_tc_iterations"] = float(it)
    res.extras["top_path_solves"] = float(solves)
    res.extras["thermal_runaway"] = float(runaway)
    if runaway:
        res.warnings.append("no stable operating point: the power grows faster with temperature than the board removes heat (thermal runaway)")
    elif not settled:
        # Close to runaway the fixed point converges slowly; the result is the last iterate, not the operating point
        res.warnings.append(f"the powers of the parts did not settle in {it} iterations (last relative change {num(change)}): "
                            "the board is close to thermal runaway and the temperatures are underestimated")
    if not split_ok:
        res.warnings.append("the top-path split did not converge: the heat taken by the top of a part and the heat entering the board are not consistent "
                            "(the junction temperatures may be wrong)")
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
        aux = simulate(steady, SolverOptions(models=("fvm",), cell_mm=max(sim.options.cell_mm, 2.0), laminate_s_max_mm=sim.options.laminate_s_max_mm,
                                           laminate_n_max=sim.options.laminate_n_max))
    except ValueError:
        return ref
    return aux.reference


# Note of the Results summary when the heat transfer coefficients are computed (once per run)
CONVECTION_NOT_MEASURED_NOTE = ("the computed heat transfer coefficients are published correlations of a plate in open air and have not been compared "
                                "with a measured copper board (the conduction is checked against independent solvers); treat the absolute temperature "
                                "as uncertain by the uncertainty of h, or fit the convection multiplier to a measurement")


def _part_warnings(sim):
    """!
    @brief Warnings after the solves, once per simulation: junction above its limit, a theta that is probably not a junction-to-pad value, unused coefficients,
           the plate, channel and Lumped-zone checks and the low face Rayleigh number of a vertical board (checks.check_low_rayleigh).
    @param sim Simulation with its results.
    @return List of strings.
    """
    out = []
    runaway = any(r.extras.get("thermal_runaway") for r in sim.results.values())
    for row, h in zip(sim.heater_rows(), sim.problem.heaters):
        if row["margin_k"] is not None and row["margin_k"] < 0 and not runaway:
            out.append(f"{row['name']}: the junction reaches {row['t_junction'] if row['t_junction'] is not None else row['t_max']:.1f} degC, "
                       f"{-row['margin_k']:.1f} K above its limit of {num(row['tj_max'])} degC (power limit {row['p_limit_w']:.2f} W with this board)")
        if h.is_component() and h.theta > 0 and row["power_board_w"] * h.theta > max(row["t_max"] - sim.reference.ambient, 0.0) > 0:
            out.append(f"{row['name']}: theta x P = {row['power_board_w'] * h.theta:.1f} K is larger than the board's own rise under the part "
                       f"({row['t_max'] - sim.reference.ambient:.1f} K): check that theta is a junction-to-pad number (theta_JC(bot), theta_J-L) and not theta_JA")
    out += check_lumped_zones(sim.problem, sim.results.get("lumped"))
    flux_result = _block_flux_result(sim)
    out += check_thick_plates(sim.problem, sim.heater_rows(), flux_result)
    # The block temperature of the reference model itself when it has one (FVM, FDM, 3D solid); the auxiliary FVM only for the Lumped and Analytic
    out += check_fin_channels(sim.problem, sim.reference if "block_T" in sim.reference.arrays else flux_result)
    if sim.problem.board.h_mode == "computed":
        # Once per simulation, from the face means of the reference model (the coefficients of its last Picard step, within 0.01 W/m2K), so that the
        # five models do not repeat it; the bottom face of a one-layer board is its last laminate node, as in _solve_computed_h
        ref = sim.reference
        info = convection.board_h(sim.problem.board, ref.layer_mean[0], ref.extras.get("bottom_face_mean", ref.layer_mean[-1]))[2]
        out += check_low_rayleigh(sim.problem.board, info)
        # One short, calm line per run: the correlations are not checked against a measured copper board (docs/theory.md 8)
        out.append(CONVECTION_NOT_MEASURED_NOTE)
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
        res.equivalent_scale = s                           # The plots can draw the field as solved (plots.draw_field) and the gradient uses the solved spacing
        if res.t_max_location is not None:
            layer, x, y = res.t_max_location
            res.t_max_location = (layer, x / s, y / s)
        res.warnings.append(f"the board has an outline: computed on a rectangle of the same area (box and positions scaled by {s:.3f}) and stretched back onto the real box; "
                            "the application can show that rectangle as solved (Equiv. rect. above the map); "
                            "expect a few percent of difference, more for parts near the edge or in a narrow arm; the FVM, FDM and 3D solid use the real shape")
        return res
    if name == "fvm":
        return fvm.solve_steady(problem, cell_mm=o.cell_mm, method=o.linear_solver, memory_limit=memory.limit_bytes(o.memory_fraction))
    if name == "fdm":
        return fdm.solve_steady(problem, cell_mm=o.cell_mm)
    if name == "solid3d":
        return solid3d.solve_steady(problem, cell_mm=o.cell_mm, memory_fraction=o.memory_fraction)
    if name == "lumped":
        return lumped.solve_steady(problem, rings=o.lumped_rings, cell_mm=lumped.cell_for(problem, o.cell_mm))
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
        res.warnings.append(f"the top-face Rayleigh number {num(info['top']['rayleigh'], 2)} is outside 10.00E3 to 100.00E9, "
                            "where the natural-convection correlation was fitted; the coefficient is an extrapolation")
    if problem.board.orientation == "horizontal" and not 1e2 <= info["bottom"]["rayleigh"] <= 1e9:
        # The face turned down uses a 1/5 law whose sources cover 40 to 8e3 (numerical strip), 10 to 1.25e8 (scattered experiments) and 1.25e5 to 1.25e8 on A/P
        # (Fujii-Imura); the 1e4 to 1e9 of Incropera's 0.52 is recalled, not confirmed. Boards sit at 1e2 to 5e6: a small board at a few kelvin falls below
        res.warnings.append(f"the bottom-face (turned down) Rayleigh number {num(info['bottom']['rayleigh'], 2)} is outside 100.00 to 1.00E9, "
                            "where the law of the face turned down has published support; the coefficient is an extrapolation")
    if problem.board.orientation == "vertical" and problem.board.natural_form == "laminar" and info["top"]["rayleigh"] > 1e9:
        # The laminar form of Churchill and Chu is meant for Ra below 1e9 (a board of about 0.5 m or more); the general form covers the whole range
        res.warnings.append(f"the Rayleigh number {num(info['top']['rayleigh'], 2)} is above 1.00E9, outside the laminar form of the vertical-plate correlation: "
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
    options = copy.deepcopy(options) if options else SolverOptions()
    options.models = (model,)
    with laminate.using(*options.laminate_params()):                  # The board of the project: its laminate rule, as in simulate()
        return _calibrate_convection(problem, measured_c, options, heater)


def _calibrate_convection(problem, measured_c, options, heater):
    """!
    @brief Body of calibrate_convection(), run with the laminate numbers of the options in force.
    @param problem A Problem (it is not modified).
    @param measured_c Measured steady temperature in degC.
    @param options SolverOptions (a private copy) with the one model to run in models.
    @param heater Name of the heater whose footprint maximum was measured; None for the board maximum.
    @return Tuple (multiplier, model temperature with it in degC).
    @throws ValueError If the measured value is not between the temperatures with multipliers 0.1 and 10.
    """
    from .analysis import heater_stats
    model = options.models[0]
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
        raise ValueError(f"the measured {num(measured_c)} degC is outside what a multiplier between 0.1 and 10 can give "
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
    with laminate.using(*options.laminate_params()):
        return _step_response(problem, model, options)


# The step response of the decision is computed at a cell of at least this size, as before, unless a part with a profile is smaller than a few cells (response_cell_mm)
RESPONSE_CELL_MM = 2.0

# Finest cell of the step response of a small part (mm); the same floor as Auto (suggest_cell_mm)
RESPONSE_CELL_FLOOR_MM = 0.25


def response_cell_mm(problem, model, options):
    """!
    @brief Cell of the step response behind the average-or-resolve decision, finer for a small part.
    @details The response used to be computed at ``max(cell, 2 mm)`` whatever the parts: a 2 mm part is one cell and its swing is already 0.67 of the truth at 0.1 Hz (0.37 to 0.51
             at 1 Hz), so a small part was averaged although its wave exceeded the budget (research/fast-wave-oscillation 8.3). The cell is now at most a quarter of the narrow side of
             the smallest part with a profile (about four cells across), not finer than RESPONSE_CELL_FLOOR_MM, not coarser than the old one, and enlarged by a quarter at a time until the
             memory guard says "ok" for a transient of the model (the response needs one factorisation per stage, like an animation).
    @note The cost is that of a finer transient: on a 100 x 80 mm board with a 2 mm part (cell 0.5 mm) the response took 5.9 s and 0.33 GB on two layers and 22 s and 1.1 GB on
          four, against 0.1 and 0.5 s at 2 mm (docs/validation.md 37.3); a 0.5 mm part on the four-layer board asks for 0.25 mm, which the memory guard estimates at 6.9 GB and
          accepts ("ok" below 60 % of 16 GB). With copper under the part the closed-form floor already covers the fast waves, so the finer cell matters for slow waves and for
          bare laminate.
    @see docs/theory.md 10.5 item 4, research/fast-wave-oscillation INTEGRATION.md D.
    @param problem A Problem.
    @param model "fvm" or "fdm".
    @param options SolverOptions (cell, memory fraction, laminate numbers).
    @return Cell size in millimetres.
    """
    base = max(options.cell_mm, RESPONSE_CELL_MM)
    sizes = [min(np.ptp(h.polygon[:, 0]), np.ptp(h.polygon[:, 1])) * 1000.0 for h in problem.heaters if h.profile is not None]
    if not sizes:
        return base
    cell = min(base, max(min(sizes) / 4.0, RESPONSE_CELL_FLOOR_MM))
    while cell < base:
        verdicts = memory.check(problem, (model,), cell, fraction=options.memory_fraction, transient=True, base=memory.BASE_DEFAULT, refuse="return", quiet=True,
                                laminate_params=options.laminate_params())
        if all(v.verdict == "ok" for v in verdicts):
            break
        cell = min(cell * 1.25, base)                              # The memory wins over the resolution: coarser until it fits, never beyond the old cell
    return cell


def _step_response(problem, model, options):
    """!
    @brief Body of step_response(), run with the laminate numbers of the options in force.
    @param problem A Problem with at least one heater.
    @param model "fvm", "fdm", "lumped" or "analytic".
    @param options SolverOptions.
    @return profiles.StepResponse.
    """
    if model in ("fvm", "fdm"):
        cell = response_cell_mm(problem, model, options)
        return (profiles.step_response_fvm if model == "fvm" else profiles.step_response_fdm)(problem, cell_mm=cell)
    if model == "lumped":
        t, z, r = lumped.step_responses(problem, rings=options.lumped_rings, cell_mm=lumped.cell_for(problem, options.cell_mm))
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
                                                               lumped.cell_for(p, o.cell_mm))
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
    # The laminate numbers of the run apply to every network, count and memory estimate made below (laminate.using)
    with laminate.using(*options.laminate_params()), uicontext.using_ui(options.ui):     # The texts of the warnings follow the front end
        return _simulate(problem, options, progress)


def _simulate(problem, options, progress):
    """!
    @brief Body of simulate(), run with the laminate numbers of the options in force.
    @param problem A Problem.
    @param options Validated SolverOptions.
    @param progress Optional callback progress(message, fraction).
    @return Simulation.
    """
    problem.validate()
    # The memory guard: before any array of the size of a model is made. A refused 3D solid next to other models is skipped with a warning (the others still
    # answer); any other refusal raises MemoryGuardError with the cell that fits.
    verdicts = memory.check(problem, options.models, options.cell_mm, fraction=options.memory_fraction, refuse="return")
    skipped = set()
    for v in verdicts:
        if v.verdict == "refuse":
            if v.model == "solid3d" and len(options.models) > 1:
                skipped.add(v.model)
            else:
                raise memory.MemoryGuardError(v.message)
    guard_warnings = [f"the 3D solid was not run: {v.message}" if v.verdict == "refuse" else v.message for v in verdicts if v.message]
    # The time simulation of a power profile (profiles.run_fvm / run_fdm at the cell of the run) holds a step factor while the next one is built: about twice a
    # steady solve (measured 1.7 times the law on the profile example at 0.5 mm). Checked now, before the steady solves; a refusal leaves the steady results and
    # says why the time simulation was not run (the step responses run on a cell of at least 2 mm and are smaller).
    profile_verdicts = (memory.check(problem, tuple(m for m in options.models if m in ("fvm", "fdm")), options.cell_mm, fraction=options.memory_fraction,
                                     factor=memory.PROFILE_FACTOR, refuse="return") if problem.has_profiles() else [])
    profile_refused = next((v for v in profile_verdicts if v.verdict == "refuse"), None)
    guard_warnings += [v.message for v in profile_verdicts if v.exceeds_available and v.verdict != "refuse"]
    sim = Simulation(problem=problem, options=options, problem_warnings=check_input(problem, options.models, options.cell_mm)
                     + guard_warnings)
    steady_problem = problem.steady_copy(options.steady_power) if problem.has_profiles() else problem
    computed = problem.board.h_mode == "computed"
    n = len(options.models) + (1 if problem.has_profiles() else 0)
    for k, name in enumerate(options.models):
        if name in skipped:
            continue                                      # Refused by the memory guard (warning already in the list)
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
    for name, r in sim.results.items():
        # Imported copper (copper.py): the Lumped, Analytic and 3D solid read only the cell fill, the layered models the face conductances; each result says so
        r.warnings.extend(copper.model_warnings(problem, name, options.cell_mm))
    sim.part_warnings = _part_warnings(sim) if sim.results else []
    if computed:
        ref = next((m for m in MODEL_NAMES + COMPARISON_MODELS if m in options.models))
        # Later stages (time simulation, animation) use the coefficients of the reference model, fixed during the cycle
        sim.effective_problem = copy.deepcopy(problem)
        sim.effective_problem.board.h_mode = "manual"
        sim.effective_problem.board.h_top, sim.effective_problem.board.h_bottom = sim.h_used[ref]
    if problem.has_profiles():
        if profile_refused is not None:
            sim.profile_error = f"time simulation not run: {profile_refused.message}"
        else:
            _run_profiles(sim, progress, len(options.models) / n)
    memory.log_peak(verdicts + profile_verdicts)                               # Measured peak of the process next to the estimate: the check of the law on other machines
    if progress:
        progress("Done", 1.0)
    return sim
