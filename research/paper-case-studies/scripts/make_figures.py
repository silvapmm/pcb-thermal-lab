#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of research/paper-case-studies. Figure 04 needs no study run (the plotted markers of Soleymani Koohbanani's Fig. 33 and equations 28 and 29); the figures of the results
       (05 onward) are listed in the README and are drawn from out/*.json once the studies have been run (this script then fails with a clear message, it does not invent data).
@details Files: fig_04_fig33_markers_against_eq28.png (always); fig_05_via_models_against_reference.png and fig_06_laminate_error_map.png (only when out/study_measured_vias.json and
         out/study_thick_laminate.json exist).
         Usage: .venv/bin/python research/paper-case-studies/scripts/make_figures.py   (from the repository root).
"""

import json
import sys

import _bootstrap
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402

import axisym_cell as AC                 # noqa: E402
import measured_data as MD               # noqa: E402


def fig_04():
    """!
    @brief The four measured markers of Fig. 33 (plot) against equations 28 and 29 evaluated for the samples of Table 9.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    for kind, color, fn in (("straight", "tab:blue", AC.k_overall_straight), ("staggered", "tab:green", AC.k_overall_staggered)):
        xs = np.linspace(0.8, 3.0, 60)
        ax.plot(xs, [fn(x * 1e-3, 0.65e-3, 0.61e-3) for x in xs], color=color, lw=1.2, label=f"eq. {28 if kind == 'straight' else 29}, D_o 0.65 / D_i 0.61 mm")
    for g, (kind, side, samples, x) in MD.ARRANGEMENTS.items():
        fn = AC.k_overall_straight if kind == "straight" else AC.k_overall_staggered
        vals = [fn(side * 1e-3, MD.TABLE_9[s][3] * 1e-3, MD.TABLE_9[s][2] * 1e-3) for s in samples]
        ax.plot([x] * len(vals), vals, "_", color="k", ms=12, mew=1.4)
        km, lo, hi = MD.FIG33_MEASURED[g]
        ax.errorbar([x], [km], yerr=None if lo is None else [[km - lo], [hi - km]], fmt="s" if kind == "straight" else "D", color="tab:red", capsize=3)
    ax.plot([], [], "_", color="k", ms=12, mew=1.4, label="eq. 28/29 for each sample of the group")
    ax.plot([], [], "s", color="tab:red", label="measured (read from the plot, +-0.2)")
    ax.set_xlabel("spacing between vias (mm)")
    ax.set_ylabel("through-plane conductivity (W/mK)")
    ax.legend(fontsize=7)
    ax.set_title("Fig. 33 of the thesis: four measured markers, nine samples", fontsize=9)
    fig.tight_layout()
    fig.savefig(_bootstrap.FIGURES / "fig_04_fig33_markers_against_eq28.png", dpi=105)
    plt.close(fig)


def fig_results():
    """!
    @brief The result figures, from the json files of the studies; refuses when they do not exist.
    @return None.
    @throws SystemExit If the studies have not been run.
    """
    needed = [_bootstrap.OUT / "study_measured_vias.json", _bootstrap.OUT / "study_thick_laminate.json"]
    missing = [p.name for p in needed if not p.exists()]
    if missing:
        raise SystemExit("result figures wait for the runs: missing out/" + ", out/".join(missing))
    via = json.load(open(needed[0]))
    lam = json.load(open(needed[1]))
    # Figure 05: error of every model against the solver with the same boundary condition, per sample
    rows = via["C"]
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for m in sorted({r["model"] for r in rows}):
        sel = [r for r in rows if r["model"] == m and r["grid_mm"] == min(x["grid_mm"] for x in rows if x["model"] == m and x["sample"] == r["sample"])]
        ax.plot([r["sample"] for r in sel], [r["err"] * 100 for r in sel], "o-", label=m)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("sample (Table 9)")
    ax.set_ylabel("resistance error against the unit-cell solver (%)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(_bootstrap.FIGURES / "fig_05_via_models_against_reference.png", dpi=105)
    plt.close(fig)
    # Figure 06: error of the layered model for each option pair, bare board
    rows = [r for r in lam["bare"] if r["model"] == "fvm" and r["cell"] == 0.25 and r["kxy"] == 0.9]
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for (s, n) in sorted({(r["s_max"], r["n_max"]) for r in rows}):
        sel = [r for r in rows if (r["s_max"], r["n_max"]) == (s, n)]
        ax.plot(range(len(sel)), [r["err_pct"] for r in sel], ".-", label=f"s_max {s}, n_max {n}")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("combination (S, t, h in the order of the table)")
    ax.set_ylabel("R' error against the 3D reference (%)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(_bootstrap.FIGURES / "fig_06_laminate_error_map.png", dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Draw figure 04 and, when the runs exist, the result figures.
    @return int Exit code.
    """
    _bootstrap.FIGURES.mkdir(exist_ok=True)
    fig_04()
    try:
        fig_results()
    except SystemExit as exc:
        print(exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
