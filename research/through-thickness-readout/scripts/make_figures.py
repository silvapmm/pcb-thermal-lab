#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the through-thickness investigation: fig_03 the surface error of case 2 against the number of sub-layers (options A, B, C), fig_04 the 3D difference over the bound and the
       parabolic read-out against t/a, fig_05 the size of the through-thickness term on the harness boards.
@details Needs out/options.json (study_options.py), out/sweep.json (study_sweep.py) and out/frozen.json (study_frozen_impact.py). The numbering is shared with make_diagrams.py.
         Run from the repository root: .venv/bin/python research/through-thickness-readout/scripts/make_figures.py
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "..", "figures")
OUT = os.path.join(HERE, "..", "out")
COL = {"fvm": "#1f77b4", "fdm": "#2ca02c", "analytic": "#d62728", "lumped": "#9467bd", "solid3d": "#ff7f0e"}


def _load(name):
    """!
    @brief Read a JSON output.
    @param name File name in out/.
    @return The parsed object.
    """
    with open(os.path.join(OUT, name)) as f:
        return json.load(f)


def fig_03():
    """!
    @brief Error of the surface read-out of source 2 (25 W) against the number of sub-layers, per model, with the option A lines.
    """
    d = _load("options.json")
    ref = d["surf"][1]
    fig, ax = plt.subplots(figsize=(6.8, 4.3))
    for key, mod in (("fvm", "fvm"), ("fdm", "fdm"), ("analytic", "analytic"), ("lumped", "lumped")):
        ns = sorted(int(k.split("|")[1]) for k in d["layered"] if k.startswith(key + "|"))
        ax.plot(ns, [d["layered"][f"{key}|{n}"]["surface_B"][1] - ref for n in ns], "o-", color=COL[mod], label=f"{key.upper()} B")
    ns = sorted(int(k) for k in d["solid"])
    ax.plot(ns, [d["solid"][str(n)]["surface_C"][1] - ref for n in ns], "s--", color=COL["solid3d"], label="3D solid C")
    a1 = d["layered"]["fvm|1"]
    ax.axhline(a1["surface_A_bound"][1] - ref, color="gray", ls=":", label="A with the bound q''t/2k (FVM)")
    ax.axhline(a1["surface_A_parabola"][1] - ref, color="k", ls="-.", label="A parabola (FVM)")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xscale("log", base=2)
    ax.set_xticks([1, 2, 4, 8])
    ax.set_xticklabels(["1", "2", "4", "8"])
    ax.set_xlabel("sub-layers (slabs) through the 10 mm plate")
    ax.set_ylabel("surface of source 2 minus the 3D surface (K)")
    ax.set_title("Muzychka et al. 2003 case 2, 25 W source: surface read-out error", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_03_case2_options.png"), dpi=105)
    plt.close(fig)


def fig_04():
    """!
    @brief 3D difference over the bound against t/a, and the parabolic read-out over the 3D difference.
    """
    rows = _load("sweep.json")["sweep"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 4.2))
    for k, mk in ((385.0, "o"), (150.0, "s"), (50.0, "^")):
        for a, col in ((4.0, "#1f77b4"), (10.0, "#2ca02c"), (20.0, "#d62728")):
            r = [x for x in rows if x["k"] == k and x["a_mm"] == a]
            ta = [x["t_mm"] / a for x in r]
            a1.plot(ta, [x["d3"] / x["bound"] for x in r], mk + "-", color=col, ms=4, lw=0.7, label=None)
            a2.plot(ta, [x["parabola"] / x["d3"] for x in r], mk + "-", color=col, ms=4, lw=0.7)
    a1.axhline(2.0 / 3.0, color="gray", ls=":")
    a1.text(0.0012, 0.68, "2/3: heat spreads inside the plate", fontsize=7)
    a1.axhline(1.0, color="gray", ls="--")
    a1.text(0.0012, 1.02, "1: bound (column fed on top, cooled below)", fontsize=7)
    a1.set_xscale("log")
    a1.set_xlabel("t / a  (thickness over source side)")
    a1.set_ylabel("3D (surface - column mean) / bound q'' t / 2k")
    a1.set_ylim(0, 1.15)
    # Proxy handles: one entry per source side (colour) and one per conductivity (marker), so that every marker of the plot is explained
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], color=c, lw=1.5, label=f"a {a:.0f} mm") for a, c in ((4.0, "#1f77b4"), (10.0, "#2ca02c"), (20.0, "#d62728"))]
    handles += [Line2D([], [], color="gray", marker=m, ls="none", label=f"k {k:.0f} W/mK") for k, m in ((385.0, "o"), (150.0, "s"), (50.0, "^"))]
    a1.legend(handles=handles, fontsize=7, title="colour = source side; marker = k", title_fontsize=7, ncol=2)
    a2.axhline(1.0, color="k", lw=0.8)
    a2.axvline(0.5, color="gray", ls=":")
    a2.text(0.52, 2.5, "t/a = 0.5", fontsize=7)
    a2.set_xscale("log")
    a2.set_xlabel("t / a")
    a2.set_ylabel("parabolic read-out / 3D difference")
    a2.set_title("the parabola is within 7 % up to t/a = 0.5 and overshoots beyond", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_04_thickness_sweep.png"), dpi=105)
    plt.close(fig)


def fig_05():
    """!
    @brief Largest through-thickness bound of the harness boards in millikelvin and in % of the rise.
    """
    d = _load("frozen.json")
    names = list(d)
    fig, ax = plt.subplots(figsize=(8.5, 4.0))
    ax.bar(range(len(names)), [1e3 * d[n]["bound_K"] for n in names], color="#1f77b4")
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=70, ha="right", fontsize=7)
    ax.set_ylabel("q'' t / (2 k) of the hottest heater (mK)")
    ax.set_title("35 um copper: the through-thickness term is a few millikelvin (at most 0.005 % of the rise)", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_05_harness_bounds.png"), dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_03()
    fig_04()
    fig_05()
    print("figures written")
