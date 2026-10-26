"""!
@file plots.py
@brief Matplotlib figures shared by the command line tool and the GUI.

@details Every `draw_*` function renders into a Figure it is given (no pyplot, no global state), so
the GUI can embed the figure in a Qt canvas and the command line can save it to a file. The
`plot_*` and `save_*` wrappers create an off-screen Figure and write a PNG or GIF.
"""

import functools

import numpy as np
from matplotlib import ticker
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from .geometry import points_in_polygon
from .numfmt import num

CMAPS = ("inferno", "hot", "viridis", "plasma", "magma", "turbo", "coolwarm")


def engineering_ticks(fig):
    """!
    @brief Write the tick labels of every numeric axis of a figure with the number format of the program (plain decimal in the window, engineering notation outside it).
    @param fig Matplotlib figure (axes and colour bars included).
    @return The figure.
    @note Category axes (the labels of a bar chart) keep their own labels; the unit stays in the axis label.
    """
    def label(value, _pos):
        return num(value, 4)

    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            if isinstance(axis.get_major_formatter(), (ticker.ScalarFormatter, ticker.LogFormatter)):
                axis.set_major_formatter(ticker.FuncFormatter(label))
    return fig


def _with_engineering_ticks(draw):
    """!
    @brief Decorator of the draw_* functions: after drawing, give the axes the number format of the program.
    @param draw A function whose first argument is the figure.
    @return The wrapped function with the same name, documentation and result.
    """
    @functools.wraps(draw)
    def wrapper(fig, *args, **kwargs):
        """!
        @brief Draw, then format the ticks.
        @param fig Figure.
        @param args Positional arguments of the drawing function.
        @param kwargs Keyword arguments of the drawing function.
        @return What the drawing function returns.
        """
        result = draw(fig, *args, **kwargs)
        engineering_ticks(fig)
        return result
    return wrapper


def new_figure(width=7.0, height=4.5):
    """!
    @brief Create an off-screen figure that can be saved without a display.
    @param width Width in inches.
    @param height Height in inches.
    @return Figure with an Agg canvas attached.
    """
    fig = Figure(figsize=(width, height), layout="constrained")
    FigureCanvasAgg(fig)
    return fig


def _off_board(field, problem, dx, dy):
    """!
    @brief The field with the samples that lie off a non-rectangular board replaced by NaN (drawn blank).
    @param field Array (ny, nx) of cell or node values.
    @param problem The Problem (board outline).
    @param dx Spacing along x in metres.
    @param dy Spacing along y in metres.
    @return The same array for a rectangular board, a copy with NaN outside the outline otherwise.
    """
    b = problem.board
    if not b.has_outline():
        return field
    xs, ys, _ = _field_axes(field, problem, dx, dy)
    X, Y = np.meshgrid(xs / 1000.0, ys / 1000.0)
    return np.where(points_in_polygon(X, Y, b.outline), field, np.nan)


def _outline(ax, problem, layer):
    """!
    @brief Draw heater, heatsink, zone and via outlines of one layer on an axis (coordinates in mm).
    @param ax Matplotlib axis.
    @param problem The Problem that owns the elements.
    @param layer 0-based layer index.
    """
    if problem.board.has_outline():
        o = np.vstack([problem.board.outline, problem.board.outline[:1]]) * 1000.0
        ax.plot(o[:, 0], o[:, 1], color="white", lw=1.4)
    for z in problem.zones:
        if z.layer == layer:
            p = np.vstack([z.polygon, z.polygon[:1]]) * 1000.0
            ax.plot(p[:, 0], p[:, 1], color="#7ee787", lw=0.8, ls="-", alpha=0.6)
    for h in problem.heaters:
        if h.layer == layer:
            p = np.vstack([h.polygon, h.polygon[:1]]) * 1000.0
            ax.plot(p[:, 0], p[:, 1], color="white", lw=1.2, ls="--")
    for s in problem.heatsinks:
        if s.layer == layer:
            p = np.vstack([s.polygon, s.polygon[:1]]) * 1000.0
            ax.plot(p[:, 0], p[:, 1], color="cyan", lw=1.2, ls=":")
    if problem.vias:
        ax.plot([v.x * 1000.0 for v in problem.vias], [v.y * 1000.0 for v in problem.vias], "k.", ms=3)


def _field_axes(field, problem, dx, dy):
    """!
    @brief Sample positions and image extent of a field that holds either cell values or values at grid points.
    @details A node field (finite-difference model) has one more sample than the board has cells along each axis.
    @param field Array (ny, nx).
    @param problem The Problem (board size).
    @param dx Spacing along x in metres.
    @param dy Spacing along y in metres.
    @return Tuple (xs_mm, ys_mm, extent_mm) with extent = [x0, x1, y0, y1] of the image.
    """
    ny, nx = field.shape
    b = problem.board
    nodes = nx == int(round(b.width / dx)) + 1 and ny == int(round(b.height / dy)) + 1
    off = 0.0 if nodes else 0.5
    xs, ys = (np.arange(nx) + off) * dx * 1000.0, (np.arange(ny) + off) * dy * 1000.0
    if nodes:
        ext = [-0.5 * dx * 1000.0, b.width * 1000.0 + 0.5 * dx * 1000.0, -0.5 * dy * 1000.0, b.height * 1000.0 + 0.5 * dy * 1000.0]
    else:
        ext = [0.0, b.width * 1000.0, 0.0, b.height * 1000.0]
    return xs, ys, ext


@_with_engineering_ticks
def draw_field(fig, field, problem, dx, dy, title="", cmap="inferno", vmin=None, vmax=None,
               layer=0, outline=True, marker=None, hotspot=None, label="Temperature (°C)"):
    """!
    @brief Draw one layer of a scalar field over the board, with outlines and a colour bar.
    @param fig Target Figure (cleared first).
    @param field Array (ny, nx) of the layer to show.
    @param problem The Problem (board size and outlines).
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param title Axes title.
    @param cmap Matplotlib colormap name.
    @param vmin Lower colour limit (default: field minimum).
    @param vmax Upper colour limit (default: field maximum).
    @param layer 0-based layer used for the outlines.
    @param outline If True draw zones, heaters, heatsinks and vias.
    @param marker Optional (x_m, y_m) of a marker, for example the hottest point.
    @param hotspot Optional temperature; the contour at that level is drawn in magenta.
    @param label Colour bar label.
    @return The axes.
    """
    fig.clear()
    ax = fig.add_subplot(111)
    b = problem.board
    field = _off_board(field, problem, dx, dy)
    xs, ys, ext = _field_axes(field, problem, dx, dy)
    im = ax.imshow(field, origin="lower", cmap=cmap, extent=ext,
                   vmin=np.nanmin(field) if vmin is None else vmin,
                   vmax=np.nanmax(field) if vmax is None else vmax)
    if hotspot is not None and np.nanmax(field) > hotspot > np.nanmin(field):
        ax.contour(xs, ys, field, levels=[hotspot], colors="#ff00cc", linewidths=1.2)
    if outline:
        _outline(ax, problem, layer)
    if marker is not None:
        ax.plot(marker[0] * 1000, marker[1] * 1000, "c+", ms=12, mew=1.5)
    ax.set_xlim(0, b.width * 1000)
    ax.set_ylim(0, b.height * 1000)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10)
    fig.colorbar(im, ax=ax, label=label, shrink=0.85)
    return ax


@_with_engineering_ticks
def draw_block(fig, result, problem, face, cmap="inferno"):
    """!
    @brief Temperature of the metal block of one face (where there is no block the board map is not shown).
    @param fig Target Figure (cleared first).
    @param result A SteadyResult with block temperatures (FVM or FDM).
    @param problem The Problem.
    @param face 0 for the block on the top face, 1 for the bottom face.
    @param cmap Colormap name.
    """
    tag = "top" if face == 0 else "bottom"
    names = [k for k in ("block_top_max", "block_bottom_max") if k in result.extras]
    which = [k.split("_")[1] for k in names].index(tag) if f"block_{tag}_max" in result.extras else None
    fig.clear()
    ax = fig.add_subplot(111)
    if which is None:
        ax.text(0.5, 0.5, "This model has no metal block", ha="center", va="center", transform=ax.transAxes)
        return
    field = np.where(result.arrays["block_cov"][which] > 0, result.arrays["block_T"][which], np.nan)
    draw_field(fig, field, problem, result.dx, result.dy, cmap=cmap, layer=0 if face == 0 else problem.board.layers - 1,
               title=f"{result.model.upper()} - metal block ({tag} face): mean {result.extras[f'block_{tag}_mean']:.1f} °C, "
                     f"max {result.extras[f'block_{tag}_max']:.1f} °C", label="Block temperature (°C)")


@_with_engineering_ticks
def draw_fields(fig, result, problem, cmap="inferno"):
    """!
    @brief All layers side by side with a shared colour scale.
    @param fig Target Figure (cleared first).
    @param result A SteadyResult with a field.
    @param problem The Problem.
    @param cmap Colormap name.
    """
    fig.clear()
    T = np.stack([_off_board(t, problem, result.dx, result.dy) for t in result.T])
    L = T.shape[0]
    vmin, vmax = float(np.nanmin(T)), float(np.nanmax(T))
    b = problem.board
    axes = fig.subplots(1, L, squeeze=False)[0]
    im = None
    for l, ax in enumerate(axes):
        _, _, ext = _field_axes(T[l], problem, result.dx, result.dy)
        im = ax.imshow(T[l], origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, extent=ext)
        ax.set_xlim(0, b.width * 1000)
        ax.set_ylim(0, b.height * 1000)
        _outline(ax, problem, l)
        ax.set_title(f"Layer {l + 1}  (mean {result.layer_mean[l]:.1f} °C)", fontsize=9)
        ax.set_xlabel("x (mm)")
        ax.set_aspect("equal")
        if l == 0:
            ax.set_ylabel("y (mm)")
    loc = result.t_max_location
    if loc is not None and loc[0] < L:
        axes[loc[0]].plot(loc[1] * 1000, loc[2] * 1000, "c+", ms=10)
    fig.colorbar(im, ax=list(axes), label="Temperature (°C)", shrink=0.9)
    fig.suptitle(f"{result.model.upper()}: Tmax {result.t_max:.1f} °C, Rθ {result.r_theta:.2f} K/W, "
                 f"power balance {num(result.balance_error, sign=True)}", fontsize=10)


@_with_engineering_ticks
def draw_profile(fig, results, problem, layer=0, axis="x", position_mm=None):
    """!
    @brief Temperature along a line through the board for every model.
    @param fig Target Figure (cleared first).
    @param results Dict {model: SteadyResult}.
    @param problem The Problem.
    @param layer 0-based layer.
    @param axis "x" for a horizontal cut at y = position, "y" for a vertical cut at x = position.
    @param position_mm Cut position in mm (default: the hottest point of the reference model).
    """
    fig.clear()
    ax = fig.add_subplot(111)
    b = problem.board
    ref = results.get("fvm") or next(iter(results.values()))
    if position_mm is None and ref.t_max_location is not None:
        position_mm = (ref.t_max_location[2] if axis == "x" else ref.t_max_location[1]) * 1000.0
    position_mm = position_mm if position_mm is not None else (b.height if axis == "x" else b.width) * 500.0
    for name, r in results.items():
        if r.T is None:
            continue
        T = _off_board(r.T[min(layer, r.T.shape[0] - 1)], problem, r.dx, r.dy)
        xs, ys = r.coords()
        if axis == "x":
            i = int(np.argmin(np.abs(ys * 1000.0 - position_mm)))
            ax.plot(xs * 1000, T[i], label=name)
        else:
            j = int(np.argmin(np.abs(xs * 1000.0 - position_mm)))
            ax.plot(ys * 1000, T[:, j], label=name)
    ax.set_xlabel(("x" if axis == "x" else "y") + " (mm)")
    ax.set_ylabel(f"Layer {layer + 1} temperature (°C)")
    ax.set_title(f"Cut along {axis} at {'y' if axis == 'x' else 'x'} = {position_mm:.1f} mm", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend()


@_with_engineering_ticks
def draw_comparison(fig, results):
    """!
    @brief Bar chart comparing the maximum and mean temperature of the models.
    @param fig Target Figure (cleared first).
    @param results Dict {model: SteadyResult}.
    """
    fig.clear()
    ax = fig.add_subplot(111)
    names = list(results)
    x = np.arange(len(names))
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


@_with_engineering_ticks
def draw_bars(fig, labels, series, ylabel="Temperature (°C)", title=""):
    """!
    @brief Grouped bar chart, for example heater or zone temperatures.
    @param fig Target Figure (cleared first).
    @param labels Category names.
    @param series Dict {series name: list of values (nan allowed)}.
    @param ylabel Y axis label.
    @param title Chart title.
    """
    fig.clear()
    ax = fig.add_subplot(111)
    n = max(len(series), 1)
    x = np.arange(len(labels))
    width = 0.8 / n
    for k, (name, vals) in enumerate(series.items()):
        vals = [np.nan if v is None else v for v in vals]
        ax.bar(x + (k - (n - 1) / 2) * width, vals, width, label=name)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8)


@_with_engineering_ticks
def draw_convergence(fig, rows):
    """!
    @brief Maximum temperature versus FVM cell size.
    @param fig Target Figure (cleared first).
    @param rows List of (cell_mm, t_max, seconds).
    """
    fig.clear()
    ax = fig.add_subplot(111)
    rows = sorted(rows)
    ax.plot([r[0] for r in rows], [r[1] for r in rows], "o-")
    ax.invert_xaxis()
    ax.set_xlabel("Cell size (mm)")
    ax.set_ylabel("Tmax (°C)")
    ax.set_title("FVM grid convergence")
    ax.grid(alpha=0.3)


@_with_engineering_ticks
def draw_transient(fig, tr):
    """!
    @brief Maximum and mean temperature versus time with the steady-state level.
    @param fig Target Figure (cleared first).
    @param tr A TransientResult.
    """
    fig.clear()
    ax = fig.add_subplot(111)
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


@_with_engineering_ticks
def draw_profile_series(fig, result, problem, limit_c=None):
    """!
    @brief Temperature of the last window versus time: the hottest point of the board and under every heater.
    @param fig Target Figure (cleared first).
    @param result A ProfileResult with a time simulation.
    @param problem The Problem (heater names).
    @param limit_c Optional temperature limit drawn as a line.
    """
    fig.clear()
    ax = fig.add_subplot(111)
    t = result.times - result.times[0]
    ax.plot(t, result.t_max, color="#888888", lw=4.0, alpha=0.5, zorder=1, label="hottest point of the board")
    for j, h in enumerate(problem.heaters):
        if h.profile is not None or len(problem.heaters) > 1:
            ax.plot(t, result.t_heaters[j], lw=1.0, label=h.name or f"Heater {j + 1}")
    ax.axhline(result.steady_average_max, color="#2a9d8f", ls="--", lw=1.0, label="steady, average power")
    ax.axhline(result.steady_peak_max, color="#e63946", ls=":", lw=1.0, label="steady, peak power (bound)")
    if limit_c is not None:
        ax.axhline(limit_c, color="#ff00cc", lw=1.2, label=f"limit {num(limit_c)} °C")
    ax.set_xlabel("Time in the last window (s)")
    ax.set_ylabel("Temperature (°C)")
    ax.set_title(f"{result.model.upper()}: peak {result.peak:.1f} °C, minimum {result.minimum:.1f} °C, "
                 f"oscillation {result.oscillation:.1f} °C", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)


@_with_engineering_ticks
def draw_peak_map(fig, result, problem, layer=0, cmap="inferno"):
    """!
    @brief Highest temperature reached at every point during the last window.
    @param fig Target Figure (cleared first).
    @param result A ProfileResult with a time simulation.
    @param problem The Problem.
    @param layer 0-based layer.
    @param cmap Colormap name.
    """
    draw_field(fig, result.peak_map[layer], problem, result.dx, result.dy, cmap=cmap, layer=layer,
               title=f"{result.model.upper()} - layer {layer + 1}: peak temperature during the cycle "
                     f"(max {float(result.peak_map[layer].max()):.1f} °C)", label="Peak temperature (°C)")


@_with_engineering_ticks
def draw_waveforms(fig, problem, cycles=2.0):
    """!
    @brief Power of every heater with a profile over a few periods of the slowest one.
    @param fig Target Figure (cleared first).
    @param problem The Problem.
    @param cycles Number of periods of the longest wave shown.
    """
    fig.clear()
    ax = fig.add_subplot(111)
    waves = [(i, h) for i, h in enumerate(problem.heaters) if h.profile is not None]
    if not waves:
        ax.text(0.5, 0.5, "No heater has a power profile", ha="center", va="center", transform=ax.transAxes)
        return
    # Show a few periods of the slowest repeating profile, or the whole length of a one-shot profile
    longest = max(h.profile.period for _, h in waves)
    span = (cycles if any(h.profile.repeat for _, h in waves) else 1.05) * longest
    t = np.linspace(0.0, span, 4000, endpoint=False)
    for i, h in waves:
        w = h.profile
        label = f"{h.name or f'Heater {i + 1}'}: average {w.average():.2f} W"
        iv = w.intervals()
        lo, hi = min(p for _, _, p in iv), max(p for _, _, p in iv)
        if w.repeat and span / w.period > 40:
            # Too many cycles to draw: show the swing as a band and the average as a line
            line, = ax.plot(t, np.full_like(t, w.average()), lw=1.4, label=label + f" (repeats at {num(1.0 / w.period)} Hz)")
            ax.fill_between(t, lo, hi, color=line.get_color(), alpha=0.18)
            continue
        edges = np.array([a for a, _, _ in iv])
        values = np.array([p for _, _, p in iv])
        phase = t % w.period if w.repeat else np.minimum(t, w.period - 1e-12)
        p = values[np.clip(np.searchsorted(edges, phase, side="right") - 1, 0, len(values) - 1)]
        if not w.repeat:
            p = np.where(t > w.period, values[-1], p)                       # The last power is held after the end
        ax.step(t, p, where="post", lw=1.4, label=label + ("" if w.repeat else " (one-shot)"))
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Power (W)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)


# ------------------------------------------------------------------ file wrappers

def plot_profile_series(result, problem, path):
    """!
    @brief Save the temperature-versus-time plot of a time simulation.
    @param result A ProfileResult.
    @param problem The Problem.
    @param path Output PNG path.
    """
    fig = new_figure(7.5, 4.5)
    draw_profile_series(fig, result, problem)
    _save(fig, path)


def plot_peak_map(result, problem, path):
    """!
    @brief Save the peak-temperature map of the top layer.
    @param result A ProfileResult.
    @param problem The Problem.
    @param path Output PNG path.
    """
    fig = new_figure(6.5, 5.0)
    draw_peak_map(fig, result, problem)
    _save(fig, path)


def _save(fig, path, dpi=150):
    """!
    @brief Save a figure as PNG.
    @param fig Figure with an Agg canvas.
    @param path Output path.
    @param dpi Resolution.
    """
    fig.savefig(path, dpi=dpi)


def plot_fields(result, problem, path):
    """!
    @brief Save the all-layers temperature map.
    @param result A SteadyResult with a field.
    @param problem The Problem.
    @param path Output PNG path.
    """
    fig = new_figure(4.6 * result.T.shape[0] + 1.2, 4.6)
    draw_fields(fig, result, problem)
    _save(fig, path)


def plot_profiles(results, problem, path):
    """!
    @brief Save the temperature profile through the hottest row of the top layer.
    @param results Dict {model: SteadyResult}.
    @param problem The Problem.
    @param path Output PNG path.
    """
    fig = new_figure(7, 4)
    draw_profile(fig, results, problem)
    _save(fig, path)


def plot_comparison(results, path):
    """!
    @brief Save the model comparison bars.
    @param results Dict {model: SteadyResult}.
    @param path Output PNG path.
    """
    fig = new_figure(6, 4)
    draw_comparison(fig, results)
    _save(fig, path)


def plot_convergence(rows, path):
    """!
    @brief Save the grid convergence plot.
    @param rows List of (cell_mm, t_max, seconds).
    @param path Output PNG path.
    """
    fig = new_figure(6, 4)
    draw_convergence(fig, rows)
    _save(fig, path)


def plot_transient(tr, path):
    """!
    @brief Save the transient curves.
    @param tr A TransientResult.
    @param path Output PNG path.
    """
    fig = new_figure(7, 4)
    draw_transient(fig, tr)
    _save(fig, path)


def frame_spacing(tr, problem):
    """!
    @brief Sample spacing of the frames of a transient: cells for the FVM and Analytic, grid points for the FDM.
    @param tr A TransientResult.
    @param problem The Problem (board size).
    @return Tuple (dx, dy) in metres.
    """
    ny, nx = tr.frames.shape[2], tr.frames.shape[3]
    if tr.grid == "nodes":
        return problem.board.width / (nx - 1), problem.board.height / (ny - 1)
    return problem.board.width / nx, problem.board.height / ny


def save_transient_gif(tr, problem, path, layer=0, fps=8, cmap="inferno"):
    """!
    @brief Animated GIF of the temperature evolution of one layer in physical time.
    @details Frames come from the transient FVM solution (implicit time stepping of the same
             matrices as the steady solution), so the time shown is real time, not solver iterations.
    @param tr A TransientResult.
    @param problem The Problem.
    @param path Output GIF path.
    @param layer 0-based layer shown.
    @param fps Frames per second.
    @param cmap Colormap name.
    """
    from matplotlib.animation import PillowWriter

    vmin, vmax = tr.ambient, float(tr.frames[:, layer].max())
    fig = new_figure(6.2, 5.0)
    dx, dy = frame_spacing(tr, problem)
    writer = PillowWriter(fps=fps)
    with writer.saving(fig, path, dpi=90):
        for k in range(len(tr.times)):
            draw_field(fig, tr.frames[k, layer], problem, dx, dy, cmap=cmap, vmin=vmin, vmax=vmax,
                       layer=layer, title=f"Layer {layer + 1}  t = {tr.times[k]:.2f} s  "
                                          f"Tmax = {tr.t_max[k]:.1f} °C")
            writer.grab_frame()
