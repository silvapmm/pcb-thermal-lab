"""!
@file plots.py
@brief Matplotlib figures for the command line tool (the only module that needs matplotlib).
"""

import numpy as np
import matplotlib

matplotlib.use("Agg")  # File output only: works without a display
import matplotlib.pyplot as plt


def _outline(ax, problem, layer):
    """!
    @brief Draw heater, sink and via outlines of one layer on an axis (coordinates in mm).
    @param ax Matplotlib axis.
    @param problem The Problem that owns the elements.
    @param layer 0-based layer index.
    """
    for h in problem.heaters:
        if h.layer == layer:
            p = np.vstack([h.polygon, h.polygon[:1]]) * 1000.0
            ax.plot(p[:, 0], p[:, 1], color="white", lw=1.2, ls="--")
    for s in problem.sinks:
        if s.layer == layer:
            p = np.vstack([s.polygon, s.polygon[:1]]) * 1000.0
            ax.plot(p[:, 0], p[:, 1], color="cyan", lw=1.2, ls=":")
    if problem.vias:
        ax.plot([v.x * 1000.0 for v in problem.vias], [v.y * 1000.0 for v in problem.vias],
                "k.", ms=3)


def plot_fields(result, problem, path):
    """!
    @brief Temperature map of every layer with a shared colour scale.
    @param result A SteadyResult with a field (fvm or analytic).
    @param problem The Problem (for the outlines and the board size).
    @param path Output PNG path.
    """
    T = result.T
    L = T.shape[0]
    b = problem.board
    fig, axes = plt.subplots(1, L, figsize=(4.6 * L + 1.2, 4.4), squeeze=False)
    vmin, vmax = float(T.min()), float(T.max())
    im = None
    for l in range(L):
        ax = axes[0, l]
        im = ax.imshow(T[l], origin="lower", cmap="inferno", vmin=vmin, vmax=vmax,
                       extent=[0, b.width * 1000, 0, b.height * 1000])
        _outline(ax, problem, l)
        ax.set_title(f"Layer {l + 1}  (mean {result.layer_mean[l]:.1f} °C)", fontsize=9)
        ax.set_xlabel("x (mm)")
        if l == 0:
            ax.set_ylabel("y (mm)")
    loc = result.t_max_location
    if loc is not None:
        axes[0, loc[0]].plot(loc[1] * 1000, loc[2] * 1000, "c+", ms=10)
    fig.colorbar(im, ax=axes.ravel().tolist(), label="Temperature (°C)", shrink=0.9)
    fig.suptitle(f"{result.model.upper()}: Tmax {result.t_max:.1f} °C, "
                 f"Rθ {result.r_theta:.2f} K/W, power balance {result.balance_error:+.1e}", fontsize=10)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_profiles(results, problem, path):
    """!
    @brief Temperature along x through the hottest row of the top layer, for every model.
    @param results Dict {model: SteadyResult}.
    @param problem The Problem.
    @param path Output PNG path.
    """
    b = problem.board
    fig, ax = plt.subplots(figsize=(7, 4))
    ref = results.get("fvm") or next(iter(results.values()))
    for name, r in results.items():
        if r.T is None:
            continue
        # Row of the global hottest cell of the reference result
        i = int(round(ref.t_max_location[2] / ref.dy - 0.5)) if ref.T is not None else r.T.shape[1] // 2
        i = min(max(int(i * ref.dy / r.dy), 0), r.T.shape[1] - 1)
        x = (np.arange(r.T.shape[2]) + 0.5) * r.dx * 1000
        ax.plot(x, r.T[0, i], label=name)
    lumped = results.get("lumped")
    if lumped is not None:
        # Ring temperatures are radial: draw them against the distance from the board centre
        rr = lumped.arrays["ring_radius_m"] * 1000
        ax.plot(b.width * 500 + rr, lumped.arrays["ring_temps_c"][0], "o--", ms=3, label="lumped (rings)")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("Top layer temperature (°C)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_comparison(results, path):
    """!
    @brief Bar chart comparing the maximum and mean temperature of the models.
    @param results Dict {model: SteadyResult}.
    @param path Output PNG path.
    """
    names = list(results)
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(x - 0.2, [results[n].t_max for n in names], 0.4, label="Tmax")
    ax.bar(x + 0.2, [results[n].t_mean for n in names], 0.4, label="Tmean")
    for k, n in enumerate(names):
        ax.text(k - 0.2, results[n].t_max + 0.5, f"{results[n].t_max:.1f}", ha="center", fontsize=8)
        ax.text(k + 0.2, results[n].t_mean + 0.5, f"{results[n].t_mean:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("Temperature (°C)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_convergence(rows, path):
    """!
    @brief Maximum temperature versus FVM cell size.
    @param rows List of (cell_mm, t_max, seconds).
    @param path Output PNG path.
    """
    rows = sorted(rows)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([r[0] for r in rows], [r[1] for r in rows], "o-")
    ax.invert_xaxis()
    ax.set_xlabel("Cell size (mm)")
    ax.set_ylabel("Tmax (°C)")
    ax.set_title("FVM grid convergence")
    ax.grid(alpha=0.3)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_transient(tr, path):
    """!
    @brief Maximum and mean temperature versus time with the steady-state level.
    @param tr A TransientResult.
    @param path Output PNG path.
    """
    fig, ax = plt.subplots(figsize=(7, 4))
    t = tr.times[1:]
    ax.semilogx(t, tr.t_max[1:], label="Tmax")
    ax.semilogx(t, tr.t_mean[1:], label="Tmean")
    ax.axhline(tr.steady_t_max, color="gray", ls="--", label="steady Tmax")
    tau = tr.time_constant()
    if np.isfinite(tau):
        ax.axvline(tau, color="C3", ls=":", label=f"63 % at {tau:.1f} s")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Temperature (°C)")
    ax.grid(alpha=0.3, which="both")
    ax.legend()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
