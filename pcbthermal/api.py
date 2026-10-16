"""!
@file api.py
@brief Public entry point: SolverOptions in, Simulation out.

@details One call runs any combination of the three models on a Problem and returns a
Simulation object that holds the results, the timings and helpers to compare, export and
plot them:

    from pcbthermal import Problem, simulate, SolverOptions

    p = Problem.new(width_mm=100, height_mm=80, layers=4)
    p.add_full_copper().add_heater(1, 4.0, rect=(30, 35, 40, 45), name="U1", theta_jb=8.0)
    sim = simulate(p, SolverOptions(models=("fvm", "lumped"), cell_mm=1.0))
    print(sim.to_markdown())
    sim.save("results")
"""

import csv
import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, Optional, Tuple

from . import analytic, fvm, lumped
from .analysis import heater_stats, hotspots, zone_stats
from .model import Problem
from .results import SteadyResult

MODEL_NAMES = ("fvm", "lumped", "analytic")


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
    analytic_local_corrections: bool = True      # Treat vias and sinks locally (Green's function update)
    hotspot_c: float = 100.0                     # Temperature limit used for hotspot detection (degC)

    def validate(self):
        """!
        @brief Check the values.
        @throws ValueError If a value is out of range or a model name is unknown.
        """
        bad = [m for m in self.models if m not in MODEL_NAMES]
        if bad or not self.models:
            raise ValueError(f"models must be a non-empty subset of {MODEL_NAMES}, got {self.models}")
        if not 0.05 <= self.cell_mm <= 50:
            raise ValueError("cell_mm must be between 0.05 and 50")
        if self.linear_solver not in ("direct", "cg", "sor"):
            raise ValueError("linear_solver must be 'direct', 'cg' or 'sor'")
        if self.lumped_rings < 3 or self.analytic_modes < 20:
            raise ValueError("lumped_rings must be >= 3 and analytic_modes >= 20")

    def to_dict(self):
        """!
        @brief JSON-ready dictionary.
        @return Dict of the options.
        """
        d = asdict(self)
        d["models"] = list(self.models)
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

    @property
    def reference(self):
        """!
        @brief The most trustworthy result available (FVM if it was run).
        @return SteadyResult.
        """
        return self.results.get("fvm") or next(iter(self.results.values()))

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
        lines = ["| Model | Tmax [°C] | Tmean [°C] | ΔT [K] | Rθ [K/W] | Power [W] | Balance | Error vs " +
                 self.reference.model + " | Time [s] |",
                 "| :-- | --: | --: | --: | --: | --: | --: | --: | --: |"]
        for r in self.table():
            lines.append(f"| {r['model']} | {r['t_max_c']:.2f} | {r['t_mean_c']:.2f} | {r['delta_t_k']:.2f} | "
                         f"{r['r_theta_k_per_w']:.3f} | {r['power_in_w']:.3f} | {r['energy_balance']:+.0e} | "
                         f"{r['error_vs_reference'] * 100:+.1f} % | {r['seconds']:.2f} |")
        for name, res in self.results.items():
            for w in res.warnings:
                lines.append(f"\n> **{name}**: {w}")
        return "\n".join(lines) + "\n"

    def to_text(self):
        """!
        @brief The comparison table as aligned plain text, followed by the warnings.
        @return String.
        """
        head = f"{'model':9s} {'Tmax C':>8s} {'Tmean C':>8s} {'dT K':>8s} {'Rth K/W':>8s} {'P W':>7s} {'balance':>9s} " \
               f"{'vs ' + self.reference.model:>9s} {'time s':>7s}"
        lines = [head, "-" * len(head)]
        for r in self.table():
            lines.append(f"{r['model']:9s} {r['t_max_c']:8.2f} {r['t_mean_c']:8.2f} {r['delta_t_k']:8.2f} "
                         f"{r['r_theta_k_per_w']:8.3f} {r['power_in_w']:7.3f} {r['energy_balance']:+9.0e} "
                         f"{r['error_vs_reference'] * 100:+8.1f}% {r['seconds']:7.2f}")
        for name, res in self.results.items():
            for w in res.warnings:
                lines.append(f"WARNING ({name}): {w}")
        return "\n".join(lines) + "\n"

    def report(self):
        """!
        @brief Plain-text report with the table, hotspots, zones and heaters (reference model).
        @return String.
        """
        ref = self.reference
        lines = [f"PCB thermal report: {self.problem.name}",
                 f"Board {self.problem.board.width * 1000:.1f} x {self.problem.board.height * 1000:.1f} mm, "
                 f"{self.problem.board.layers} layers, ambient {self.problem.board.ambient:g} degC, "
                 f"total power {self.problem.total_power():.3f} W", "", self.to_text()]
        if ref.T is not None:
            lines.append(f"Reference model: {ref.model}")
            hs = hotspots(ref, self.options.hotspot_c)
            lines.append(f"Hotspots above {self.options.hotspot_c:g} degC: {len(hs)}")
            for h in hs[:10]:
                lines.append(f"  layer {h['layer']}: {h['t_max']:.1f} degC at ({h['x_mm']:.1f}, {h['y_mm']:.1f}) mm, "
                             f"{h['area_mm2']:.1f} mm2")
            for h in heater_stats(ref, self.problem):
                tj = f", junction {h['t_junction']:.1f} degC" if h["t_junction"] is not None else ""
                lines.append(f"Heater {h['name']} (layer {h['layer']}, {h['power_w']:.2f} W): "
                             f"mean {h['t_mean']:.1f}, max {h['t_max']:.1f} degC{tj}")
            for z in zone_stats(ref, self.problem):
                lines.append(f"Zone {z['name']} (layer {z['layer']}): mean {z['t_mean']:.1f}, "
                             f"max {z['t_max']:.1f}, min {z['t_min']:.1f} degC")
        return "\n".join(lines) + "\n"

    def to_dict(self):
        """!
        @brief JSON-ready summary of the whole simulation.
        @return Dict with options, table and per-model summaries.
        """
        return {"problem": self.problem.name, "options": self.options.to_dict(), "table": self.table(),
                "models": {k: r.summary() for k, r in self.results.items()}}

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
        if plots:
            from . import plots
            for name, r in self.results.items():
                if r.T is not None:
                    plots.plot_fields(r, self.problem, path(f"fields_{name}.png"))
            if len(self.results) > 1:
                plots.plot_comparison(self.results, path("comparison.png"))
            plots.plot_profiles(self.results, self.problem, path("profiles.png"))
        return written


def _run_model(problem, name, o):
    """!
    @brief Run one model with the matching options.
    @param problem The Problem.
    @param name Model name.
    @param o SolverOptions.
    @return SteadyResult.
    """
    if name == "fvm":
        return fvm.solve_steady(problem, cell_mm=o.cell_mm, method=o.linear_solver)
    if name == "lumped":
        return lumped.solve_steady(problem, rings=o.lumped_rings, cell_mm=min(max(o.cell_mm, 0.5), 1.0))
    return analytic.solve_steady(problem, cell_mm=min(max(o.cell_mm, 0.5), 1.0), n_terms=o.analytic_modes,
                                 local_corrections=o.analytic_local_corrections)


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
    sim = Simulation(problem=problem, options=options)
    n = len(options.models)
    for k, name in enumerate(options.models):
        if progress:
            progress(f"Solving {name}", k / n)
        t0 = time.time()
        sim.results[name] = _run_model(problem, name, options)
        sim.seconds[name] = time.time() - t0
    if progress:
        progress("Done", 1.0)
    return sim
