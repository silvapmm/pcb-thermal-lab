#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief The data figures of the surface read-out investigation, drawn from the outputs of the studies (out/plates_0.5.json, out/harness_2.0.json, out/transient.json): fig_04 the plates, fig_05 the Lumped bound, fig_06 the transient, fig_07 the harness offsets.
@details Run the studies first (study_steady_plates.py 0.5, study_harness_boards.py 2.0, study_transient.py), then: .venv/bin/python research/surface-readout-models/scripts/make_figures.py. The figures quote only numbers that the README holds.
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out")
FIG = os.path.join(HERE, "..", "figures")


def load(name):
    """!
    @brief Read one output file of the studies.
    @param name File name in out/.
    @return The decoded JSON.
    """
    with open(os.path.join(OUT, name)) as f:
        return json.load(f)


def fig_04_plates():
    """!
    @brief Error of every read-out against the independent 3D surface, in units of the true through-thickness term, on the eight plates.
    """
    rows = load("plates_0.5.json")
    keys = [("surf_fvm", "FVM parabola", "#7f7f7f"), ("surf_fem", "FEM (computed)", "#2ca02c"), ("par_lumped", "Lumped parabola (rule F)", "#ff7f0e"), ("bound_lumped", "Lumped upper bound", "#d62728"),
            ("par_analytic", "Analytic (rule F)", "#9467bd"), ("surf_solid1", "3D solid, 1 slab (rule S)", "#8c564b"), ("surf_solid4", "3D solid, 4 slabs", "#17becf"), ("surf_solid8", "3D solid, 8 slabs", "#1f77b4")]
    fig, ax = plt.subplots(figsize=(12, 5.2))
    w = 0.1
    x = np.arange(len(rows))
    for i, (k, lab, col) in enumerate(keys):
        v = [(r[k] - r["ref_surf"]) / (r["ref_surf"] - r["ref_col"]) for r in rows]
        ax.bar(x + (i - 3.5) * w, v, w, label=lab, color=col)
    ax.axhline(0, color="k", lw=0.8)
    ax.axhline(1, color="gray", lw=0.6, ls=":")
    ax.set_xticks(x)
    ax.set_xticklabels([r["name"].replace(", ", "\n", 1) for r in rows], fontsize=7)
    ax.set_ylabel("(estimate - independent surface) / (independent surface - independent column)", fontsize=8)
    ax.set_ylim(-0.4, 1.6)
    ax.legend(fontsize=7, ncol=4, loc="upper right")
    ax.set_title("Error of each surface read-out in units of the true through-thickness term (plates at 0.5 mm; + is hot; the bound lies between 0 and about 1 above)", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_04_plates.png"), dpi=105)
    plt.close(fig)


def fig_05_bound():
    """!
    @brief Left: the bound q'' t / 2k against the true term on the plates; right: the Lumped column error against the FEM column on the harness boards, with the bound drawn (it is invisible).
    """
    pl = load("plates_0.5.json")
    ha = [r for r in load("harness_2.0.json") if r.get("col_fem") is not None and "col_lumped" in r]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [1, 1.5]})
    term = np.array([r["ref_surf"] - r["ref_col"] for r in pl])
    bnd = np.array([r["bound_lumped"] - r["col_lumped"] for r in pl])
    a1.loglog(term, bnd, "o", color="#d62728", label="plates (independent 3D term, q'' t / 2k)")
    lim = [term.min() * 0.7, bnd.max() * 1.5]
    a1.plot(lim, lim, "k-", lw=0.8, label="bound = term")
    a1.plot(lim, [0.5 * lim[0] * 2 / 3 * 3 / 1 for _ in lim], alpha=0)
    a1.set_xlabel("independent 3D: surface - column (K)", fontsize=8)
    a1.set_ylabel("q'' t / 2k (K)", fontsize=8)
    a1.legend(fontsize=7)
    a1.set_title("the bound is above the true term on every plate", fontsize=9)
    names = [f"{r['board'][:16]}/{r['part'][:4]}" for r in ha]
    dcol = np.array([r["col_lumped"] - r["col_fem"] for r in ha])
    order = np.argsort(dcol)
    a2.bar(range(len(ha)), dcol[order], color=["#d62728" if v < 0 else "#7f7f7f" for v in dcol[order]], label="Lumped column - FEM column (K)")
    a2.plot(range(len(ha)), np.array([ha[i]["bound_k"] for i in order]), "k.", ms=4, label="the bound q'' t / 2k (K): 0.001 to 0.004")
    a2.set_xticks(range(len(ha)))
    a2.set_xticklabels([names[i] for i in order], rotation=75, fontsize=6, ha="right")
    a2.axhline(0, color="k", lw=0.8)
    a2.legend(fontsize=7)
    a2.set_title("harness boards, 2 mm: Lumped column - FEM column (red: the bound is below the FEM surface)", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_05_bound.png"), dpi=105)
    plt.close(fig)


def fig_06_transient():
    """!
    @brief The transient: the parabola over the exact term against the Fourier number (step) and the rule's own error on square waves.
    """
    t = load("transient.json")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.8))
    cases = sorted({r["case"] for r in t["step"]})
    cols = ["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd"]
    for c, col in zip(cases, cols):
        rs = [r for r in t["step"] if r["case"] == c]
        a1.semilogx([r["Fo"] for r in rs], [r["par_off"] / r["ref_off"] for r in rs], "o-", color=col, label=c)
    a1.axhline(1.0, color="k", lw=0.8)
    a1.axvline(0.3, color="gray", ls=":", lw=1)
    a1.text(0.32, 4.5, "Fo = 0.3", fontsize=8, color="gray")
    a1.set_xlabel("Fourier number  alpha tau / t^2 of the thick layer", fontsize=8)
    a1.set_ylabel("parabola of the frame / exact surface - mean", fontsize=8)
    a1.set_title("power step: exact from Fo 0.3, an upper estimate below (5.7 at 0.003)", fontsize=9)
    a1.legend(fontsize=7)
    for c, col in zip(cases, cols):
        rs = [r for r in t["wave"] if r["case"] == c]
        a2.semilogx([r["T_over_tau"] for r in rs], [(r["par_peak_surf_err"] - r["col_peak_err"]) / r["ref_peak_off"] for r in rs], "o-", color=col, label=c)
    a2.axhline(0, color="k", lw=0.8)
    a2.set_xlabel("period / (t^2 / alpha), 50 % duty, last of six periods", fontsize=8)
    a2.set_ylabel("(parabola surface error - node error) / exact term", fontsize=8)
    a2.set_title("square wave: the error of the rule itself, in units of the term", fontsize=9)
    a2.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_06_transient.png"), dpi=105)
    plt.close(fig)


def fig_07_harness():
    """!
    @brief Surface minus column on the harness parts, in mK, for the FEM, the FVM, the two rule-F models and the bound.
    """
    ha = [r for r in load("harness_2.0.json") if r.get("off_fem") is not None]
    x = np.arange(len(ha))
    fig, ax = plt.subplots(figsize=(12, 4.8))
    w = 0.16
    series = [("off_fem", "FEM (computed)", "#2ca02c"), ("off_fvm", "FVM parabola", "#7f7f7f"), ("d_lumped", "Lumped rule F", "#ff7f0e"), ("d_analytic", "Analytic rule F", "#9467bd"), ("bound_k", "bound q'' t / 2k", "#d62728")]
    for i, (k, lab, col) in enumerate(series):
        ax.bar(x + (i - 2) * w, [1e3 * r[k] if r.get(k) is not None else 0.0 for r in ha], w, label=lab, color=col)
    ax.set_yscale("symlog", linthresh=1.0)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r['board'][:18]}/{r['part'][:4]}" for r in ha], rotation=75, fontsize=6, ha="right")
    ax.set_ylabel("surface - column (mK)", fontsize=8)
    ax.legend(fontsize=7, ncol=5)
    ax.set_title("harness boards (35 um copper, 2 mm cell): every read-out is a few mK; the FEM's 105 mK on drawn_ell is the bare laminate under the part, which the bound does not contain", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_07_harness.png"), dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_04_plates()
    fig_05_bound()
    fig_06_transient()
    fig_07_harness()
    print("figures written to", FIG)
