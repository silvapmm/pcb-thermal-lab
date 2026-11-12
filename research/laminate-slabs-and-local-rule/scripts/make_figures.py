#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures 04 to 06 and 08 (the review) of research/laminate-slabs-and-local-rule from the JSON files of the studies in out/ (run the studies first).
@details Fig. 4: error of the FVM against the reference versus unknowns (default, global, local rules) for S = 2 mm and 5 mm bare boards (study_local_rule.py, first and second rounds).
         Fig. 5: error against the 3D solver of the edge variants (study_edge_film.py). Fig. 6: error of the 3D solid against the reference versus slabs (study_solid_slices.py).
         Fig. 8: the review's checks (study_review_checks.py, all parts, and study_local_rule.py --round2).
         Usage: .venv/bin/python research/laminate-slabs-and-local-rule/scripts/make_figures.py   (from the repository root).
"""

import json

import numpy as np
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
OUT, FIG = HERE / "out", HERE / "figures"


def fig_local():
    """!
    @brief Figure 04: error against cost of the laminate rules on the thick-laminate cases.
    @return None
    """
    rows = json.loads((OUT / "study_local_rule.json").read_text()) + json.loads((OUT / "study_local_rule2.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
    marks = {"default": ("o", "k"), "G(0.2,8)": ("s", "#888"), "G(0.1,16)": ("D", "#1f77b4"), "L1 t.10/.05 cap16": ("^", "#d62728"), "L6 t.05/.05 cap16": ("v", "#2ca02c")}
    for ax, pad in zip(axes, (False, True)):
        for r in rows:
            if r["pad"] != pad or r["err"] is None or r["cfg"] not in marks or r["W"] != 20.0:
                continue
            m, c = marks[r["cfg"]]
            ax.scatter(r["cost_u"], r["err"], marker=m, color=c, s=28, label=r["cfg"])
        h, l = ax.get_legend_handles_labels()
        ax.legend(dict(zip(l, h)).values(), dict(zip(l, h)).keys(), fontsize=7)
        ax.axhline(0, color="k", lw=0.5)
        ax.axhspan(-3, 3, color="#2ca02c", alpha=0.08)
        ax.set_xlabel("unknowns / unknowns of the default rule")
        ax.set_title(("bare laminate (vs eq. 50 or extrapolated 3D)" if not pad else "copper pad (vs extrapolated 3D, else vs G(0.1,16))"), fontsize=9)
    axes[0].set_ylabel("error of R' (%)")
    fig.suptitle("Fig. 4  Error against cost, S = 2 and 5 mm on 20 mm, t = 0.8 to 3.2 mm, FVM 0.25 mm (green band: +-3 %)", fontsize=10)
    fig.savefig(FIG / "fig_04_local_rule_cost_error.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_edge():
    """!
    @brief Figure 05: error of the edge variants against the 3D solver.
    @return None
    """
    rows = json.loads((OUT / "study_edge_film.json").read_text())
    keys = ("default", "fill0.9999", "edge m1", "eta")
    fig, ax = plt.subplots(figsize=(11, 4.4))
    w = 0.2
    for i, k in enumerate(keys):
        ax.bar([j + (i - 1.5) * w for j in range(len(rows))], [100 * (r[k] / r["r3d8"] - 1) for r in rows], w, label=k)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels([f"L{r['layers']} t{r['t']}\nhs{r['hs']:g}\n{r['pos']}" for r in rows], fontsize=6)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_ylabel("hottest rise vs 3D solver (%)")
    ax.legend(fontsize=7)
    ax.set_title("Fig. 5  Edge film: the program, nodes everywhere (fill 0.9999), nodes at the edge (margin 1), efficiency eta (FVM 0.5 mm)", fontsize=9)
    fig.savefig(FIG / "fig_05_edge_variants.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_solid():
    """!
    @brief Figure 06: 3D solid error against the number of slabs.
    @return None
    """
    rows = json.loads((OUT / "study_solid_slices.json").read_text())["part1"]
    fig, ax = plt.subplots(figsize=(7, 4.4))
    for key in sorted({(r["S"], r["t"], r["pad"]) for r in rows if r["ref"]}):
        pts = [(r["n"], 100 * (r["R"] / r["ref"] - 1)) for r in rows if (r["S"], r["t"], r["pad"]) == key]
        ax.plot(*zip(*pts), "o-", label=f"S{key[0]:g} t{key[1]:g} {'pad' if key[2] else 'bare'}")
    ax.set_xscale("log", base=2)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel("slabs per gap")
    ax.set_ylabel("error of R' (%), face term added, 0.25 mm cell")
    ax.legend(fontsize=7)
    ax.set_title("Fig. 6  3D solid against the extrapolated reference", fontsize=9)
    fig.savefig(FIG / "fig_06_solid_slabs_error.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_review():
    """!
    @brief Figure 08 (review): (a) the error of the local rule, the global (0.1, 16) and the default against the cell, S = 2 mm, 3.2 mm board, bare and pad; (b) the edge nodes against
           their band width at 0.5 and 1 mm, 3.2 mm board, h_side 200, against the 3D solver at 1 mm (out/study_review_checks.json and out/study_local_rule2.json).
    @return None
    """
    rv = json.loads((OUT / "study_review_checks.json").read_text())
    r2 = json.loads((OUT / "study_local_rule2.json").read_text())
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    ax = axes[0]
    names = {"default": ("default", "k", "o"), "G(0.1,16)": ("G(0.1,16)", "#1f77b4", "D"), "L6": ("L6 t.05/.05 cap16", "#2ca02c", "v")}
    for pad, ls in ((False, "-"), (True, "--")):
        for key, (cfg, col, mk) in names.items():
            pts = [(0.25, next(r["err"] for r in r2 if r["S"] == 2.0 and r["t"] == 3.2 and r["pad"] == pad and r["cfg"] == cfg))]
            pts += [(row["cell"], row["out"][key][0]) for row in rv["cells"] if row["S"] == 2.0 and row["t"] == 3.2 and row["pad"] == pad]
            pts.sort()
            ax.plot(*zip(*pts), ls=ls, marker=mk, color=col, label=f"{key}, {'pad' if pad else 'bare'}")
    ax.axhline(0, color="k", lw=0.5)
    ax.axhspan(-3, 3, color="#2ca02c", alpha=0.08)
    ax.set_xlabel("cell (mm); the part is 2 mm")
    ax.set_ylabel("error of R' (%) against the extrapolated 3D")
    ax.set_title("(a) local rule against the cell, S = 2 mm, t = 3.2 mm", fontsize=9)
    ax.legend(fontsize=7)
    ax = axes[1]
    for row, col in zip(rv["edge"], ("#d62728", "#1f77b4")):
        for cell, ls in ((0.5, "-"), (1.0, "--")):
            ms, es = [], []
            for k, v in row["out"].items():
                if k.endswith(f" {cell}") and k.startswith("edge"):
                    m = int(k.split("(")[1].split()[0]) if "band" in k else int(k.split()[1][1:])
                    ms.append(m)
                    es.append(100 * (v / row["ref_1mm"] - 1))
            o = np.argsort(ms)
            ax.plot(np.array(ms)[o], np.array(es)[o], ls=ls, marker="o", color=col, label=f"{row['pos']}, {cell} mm")
            ax.axhline(100 * (row["out"][f"everywhere {cell}"] / row["ref_1mm"] - 1), color=col, ls=ls, lw=0.7, alpha=0.6)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_xlabel("band of edge nodes (cells beyond the border cell; thin lines: nodes everywhere)")
    ax.set_ylabel("hottest rise against the 3D solver (%)")
    ax.set_title("(b) edge nodes against the band, 3.2 mm, h_side 200 (the program: -14.3 / -5.7 %)", fontsize=9)
    ax.legend(fontsize=7)
    fig.suptitle("Fig. 8  Review: the local rule at the cells a user runs, and the edge band", fontsize=10)
    fig.savefig(FIG / "fig_08_review_cells_and_band.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig_local()
    fig_edge()
    fig_solid()
    fig_review()
