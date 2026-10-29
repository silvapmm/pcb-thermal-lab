#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief The data figures of the zone-union investigation, drawn from the JSON files that the studies write in out/ (run the studies first, see README 'How to run').
@details Writes to figures/ with the numbering shared with make_diagrams.py: fig_07_cases_error, fig_08_strip_sweep, fig_09_sampling, fig_10_cost, fig_11_real_board, fig_12_hatched_union.
         Run from the repository root: .venv/bin/python research/zone-union/scripts/make_figures.py
"""

import _bootstrap  # noqa: F401  (import paths)

import json

import matplotlib.pyplot as plt
import numpy as np

import diagram_kit as dk
import variant
from paths import FIGURES, OUT

variant.use(True)


def load(name):
    """!
    @brief Read a JSON file of out/.
    @param name File name.
    @return Parsed content.
    """
    return json.loads((OUT / name).read_text())


def fig_07():
    """!
    @brief Error of the peak rise against the independent solver for the cases with resolved copper: old rule against the per-point union, FVM and FDM, 1 mm cells.
    @return None.
    """
    var, dev, ref = load("cases_variant.json"), load("cases_develop.json"), load("cases_reference.json")
    names = [n for n in var if n in ref and not n.startswith("hatch") and not n.startswith("frame") and n != "one zone"]
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 5.4), sharey=True)
    for ax, model in zip(axs, ("fvm", "fdm")):
        old, new = [], []
        for n in names:
            rv = ref[n].get("0.125/2", ref[n]["0.25/8"])["max"]
            old.append(100 * (dev[n]["1.0"]["develop"][model] / rv - 1))
            new.append(100 * (var[n]["1.0"]["max_point"][model] / rv - 1))
        y = np.arange(len(names))
        ax.barh(y + 0.2, old, 0.38, color="#d62728", label="old rule (the program as it is)")
        ax.barh(y - 0.2, new, 0.38, color="#1f77b4", label="per-point union")
        ax.set_yticks(y)
        ax.set_yticklabels([n.replace("two zones meeting", "2 zones, joint") for n in names], fontsize=7)
        ax.invert_yaxis()
        ax.axvline(0, color="k", linewidth=0.6)
        ax.set_xlabel(f"peak-rise error vs independent solver (%), {model.upper()}", fontsize=8)
        ax.grid(axis="x", alpha=0.3)
    axs[0].legend(fontsize=8, loc="center right")
    dk.save(fig, FIGURES / "fig_07_cases_error.png", "Solid copper drawn as pieces, 1 mm cells: the old rule against the resolved copper")


def fig_08():
    """!
    @brief Error of the old rule against the strip width and the joint phase.
    @return None.
    """
    dev, var = load("strips_develop.json"), load("strips_variant.json")
    ws = sorted({float(k.split("/")[0]) for k in dev if k != "base"})
    shifts = sorted({float(k.split("/")[1]) for k in dev if k != "base"})
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4), sharey=False)
    for ax, model in zip(axs, ("fvm", "fdm")):
        for sh, c in zip(shifts, ("#1f77b4", "#ff7f0e", "#2ca02c")):
            ys = [100 * (dev[f"{w}/{sh}"]["develop"][model] / dev["base"][model] - 1) for w in ws]
            ax.plot(ws, ys, "o-", color=c, label=f"joint shifted by {sh} of the strip width")
        ax.plot(ws, [100 * (var[f"{w}/0.0"]["max_point"][model] / dev["base"][model] - 1) for w in ws], "k--", label="per-point union (all shifts)")
        ax.set_xscale("log")
        ax.set_xlabel("strip width (mm); cells of 1 mm")
        ax.set_ylabel(f"peak-rise error against one zone (%), {model.upper()}, old rule")
        ax.grid(alpha=0.3)
    axs[0].legend(fontsize=7)
    dk.save(fig, FIGURES / "fig_08_strip_sweep.png", "How much the old rule loses: abutting strips of every width against one zone of the same copper")


def fig_09():
    """!
    @brief Sampling: fill error and peak error against the sub-samples per side and cell.
    @return None.
    """
    d = load("study_sampling.json")
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.4))
    S = [2, 3, 4, 8, 16]
    for cell, c in zip(("0.5", "1.0", "2.0"), ("#1f77b4", "#ff7f0e", "#2ca02c")):
        axs[0].plot(S, [d["fill"][cell][str(s)][1] for s in S], "o-", color=c, label=f"cell {cell} mm")
        axs[1].plot(S, [d["peak"][cell][str(s)] for s in S], "o-", color=c, label=f"cell {cell} mm")
        axs[1].axhline(d["peak_old"][cell], color=c, linestyle=":", linewidth=1)
    axs[0].set_ylabel("mean |fill error| of a cell (worst of 16 gap positions)")
    axs[1].set_ylabel("FVM peak-rise error (% of the rise)")
    axs[1].text(2.2, d["peak_old"]["2.0"] * 1.05, "dotted: old rule", fontsize=7)
    for ax in axs:
        ax.set_xscale("log", base=2)
        ax.set_xticks(S)
        ax.set_xticklabels([str(s) for s in S])
        ax.set_yscale("log")
        ax.set_xlabel("sub-samples per cell side")
        ax.grid(alpha=0.3, which="both")
        ax.legend(fontsize=8)
    dk.save(fig, FIGURES / "fig_09_sampling.png", "Two zones 0.25 mm apart cut at 4 angles: the lattice against 64 x 64 points per cell")


def fig_10():
    """!
    @brief Time and peak memory of the three ways to combine the zones.
    @return None.
    """
    d = load("study_cost.json")
    keys = [k for k in d if "/" in k]
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.6))
    x = np.arange(len(keys))
    for i, (lab, c) in enumerate((("old", "#d62728"), ("point", "#1f77b4"), ("exact", "#7f7f7f"))):
        t = [d[k][lab][0] for k in keys]
        m = [d[k][lab][1] for k in keys]
        axs[0].bar(x + (i - 1) * 0.27, t, 0.26, color=c, label={"old": "old rule", "point": "per-point union", "exact": "polygon union (shapely)"}[lab])
        axs[1].bar(x + (i - 1) * 0.27, m, 0.26, color=c)
    for ax in axs:
        ax.set_xticks(x)
        ax.set_xticklabels([k.replace("/", "\n") for k in keys], fontsize=7)
        ax.set_yscale("log")
        ax.grid(axis="y", alpha=0.3, which="both")
        ax.set_xlabel("sample points / zones in the drawing")
    axs[0].set_ylabel("time of the zone fill (s)")
    axs[1].set_ylabel("peak numpy memory (MB)")
    axs[0].legend(fontsize=7)
    dk.save(fig, FIGURES / "fig_10_cost.png", "Cost of the zone fill (one layer; blank bars: not run)")


def fig_11():
    """!
    @brief A window of the Stormduino: the resolved copper, the cell fill under the old rule and the union, and the errors of the five models.
    @return None.
    """
    import real_board
    import reference
    import study_real_board as srb
    import zone_rules as zr
    objs, wins = srb.windows()
    x0, y0, _ = wins[2]
    w = real_board.window(objs, x0, y0, srb.SIZE)
    p = srb.build(w, None)
    n, dxm = 24, 1e-3
    res = reference.raster([q * 1e-3 for q in w[0]], 96, 96, 0.25e-3, 4)
    old = zr.combine(p.zones, 2, n, n, dxm, dxm, 4, "max_cell")[0]
    new = zr.combine(p.zones, 2, n, n, dxm, dxm, 4, "max_point")[0]
    fig, axs = plt.subplots(1, 4, figsize=(13, 3.9))
    ext = (0, 24, 0, 24)
    axs[0].imshow(res, origin="lower", extent=ext, cmap="copper_r", vmin=0, vmax=1)
    axs[0].set_title("resolved copper, top layer (0.25 mm)", fontsize=8)
    axs[1].imshow(old, origin="lower", extent=ext, cmap="viridis", vmin=0, vmax=1)
    axs[1].set_title("cell fill, old rule (1 mm cells)", fontsize=8)
    im = axs[2].imshow(new, origin="lower", extent=ext, cmap="viridis", vmin=0, vmax=1)
    axs[2].set_title("cell fill, per-point union", fontsize=8)
    d = axs[3].imshow(new - old, origin="lower", extent=ext, cmap="magma")
    axs[3].set_title("union minus old rule", fontsize=8)
    fig.colorbar(d, ax=axs[3], fraction=0.046)
    fig.colorbar(im, ax=axs[2], fraction=0.046)
    for a in axs:
        a.add_patch(plt.Rectangle((9, 9), 6, 6, fill=False, edgecolor="r", linewidth=1.2))
    dk.save(fig, FIGURES / "fig_11_real_board.png", f"Stormduino window x={x0:.0f}, y={y0:.0f} drawn as {len(w[0])} polygons on the top layer (red: the 6 x 6 mm part)")


def fig_12():
    """!
    @brief The change that a second hatched zone brings: independent solver on the stripes against the rules.
    @return None.
    """
    hat, ref = load("cases_hatch.json"), load("cases_reference.json")
    base = "hatch: one zone of vertical stripes (fill 0.5)"
    names = [n for n in hat if n != base and "over a solid" not in n]
    rules = ("max_point", "prob", "sum_clip", "priority")
    fig, ax = plt.subplots(figsize=(9.5, 4.3))
    x = np.arange(len(names))
    rm = lambda n: ref[n]["0.125/2"]["mean"]
    ax.bar(x - 0.3, [100 * (rm(n) / rm(base) - 1) for n in names], 0.12, color="k", label="independent solver on the stripes")
    for i, (r, c) in enumerate(zip(rules, ("#1f77b4", "#2ca02c", "#d62728", "#9467bd"))):
        ax.bar(x - 0.15 + 0.12 * (i + 1), [100 * (hat[n][r] / hat[base][r] - 1) for n in names], 0.12, color=c, label=r)
    ax.set_xticks(x)
    ax.set_xticklabels([n.replace("hatch: ", "").replace(" (", "\n(") for n in names], fontsize=7)
    ax.set_ylabel("change of the mean heater rise by the second zone (%)")
    ax.legend(fontsize=7)
    ax.grid(axis="y", alpha=0.3)
    dk.save(fig, FIGURES / "fig_12_hatched_union.png", "Two hatched zones of fill 0.5: no rule is right for all three overlaps, the zones look the same to the models")


if __name__ == "__main__":
    FIGURES.mkdir(parents=True, exist_ok=True)
    for f in (fig_07, fig_08, fig_09, fig_10, fig_11, fig_12):
        f()
        print("drawn", f.__name__)
