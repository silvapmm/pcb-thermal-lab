#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures with the measured numbers of research/fem-amg-thin-layers, read from out/ (variants.jsonl, extras.jsonl, frozen_*.json): fig_03 setup and solve seconds per variant, fig_04 total
       time against the default as a function of the unknown count, with the 29 frozen records.
@details Run the studies first (README section 5). Run (repository root): .venv/bin/python research/fem-amg-thin-layers/scripts/make_figures.py
"""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402

FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(FOLDER, "out")


def rows():
    """!
    @brief All measured (case, variant) rows of variants.jsonl and extras.jsonl; the first row of a pair wins.
    @return dict (case, variant) -> row.
    """
    d = {}
    for name in ("variants.jsonl", "extras.jsonl"):
        path = os.path.join(OUT, name)
        if not os.path.exists(path):
            continue
        for line in open(path):
            r = json.loads(line)
            if "total_s" in r:
                d.setdefault((r["case"], r["variant"]), r)
    return d


def fig_03(d):
    """!
    @brief Stacked bars (setup, solve) per variant for the example board at 2 mm and 1 mm, with the iteration count above each bar.
    @param d Rows from `rows`.
    @return None.
    """
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    for ax, case in zip(axes, ("example_2mm", "example_1mm")):
        items = sorted([(v, r) for (c, v), r in d.items() if c == case and v not in ("ilu", "colblock_amg_mult", "rs", "sym_t0.25") and r.get("converged", True)], key=lambda t: t[1]["total_s"])
        names = [v for v, _ in items]
        setup = [r["setup_s"] for _, r in items]
        solve = [r["solve_s"] for _, r in items]
        ax.bar(range(len(names)), setup, color="#c0392b", label="setup")
        ax.bar(range(len(names)), solve, bottom=setup, color="#1f4e79", label="CG solve")
        for i, (_, r) in enumerate(items):
            ax.text(i, r["total_s"], f"{r['iterations']} it\n{r['total_s']:.1f} s", ha="center", va="bottom", fontsize=6)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=60, ha="right", fontsize=7)
        ax.set_ylabel("seconds")
        ax.set_title(f"{case}: {items[0][1]['n']} unknowns (sorted by total; rs and sym_t0.25 off the scale, see README)", fontsize=8)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FOLDER, "figures", "fig_03_variants_setup_solve.png"), dpi=140)


def fig_04(d):
    """!
    @brief Total time of the two column-solve preconditioners divided by the program default, against the unknown count: the 29 frozen records (small dots) and the named cases (large markers).
    @param d Rows from `rows`.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for v, col in (("colblock", "#1f4e79"), ("colblock_amg", "#c0392b")):
        path = os.path.join(OUT, f"frozen_{v}.json")
        if os.path.exists(path):
            fr = [r for r in json.load(open(path)) if "n" in r]
            ax.scatter([r["n"] for r in fr], [r["total_s"] / r["base_total_s"] for r in fr], s=12, color=col, alpha=0.45, label=f"{v}: 29 frozen records")
        xs, ys = [], []
        for (c, vv), r in d.items():
            b = d.get((c, "base"))
            if vv == v and b:
                xs.append(r["n"])
                ys.append(r["total_s"] / b["total_s"])
        ax.scatter(xs, ys, s=60, color=col, marker="D", edgecolor="k", label=f"{v}: named cases")
    ax.axhline(1.0, color="k", lw=0.8)
    ax.axhline(0.75, color="g", lw=0.8, ls="--")
    ax.text(1.2e4, 0.76, "acceptance: 25 % lower", fontsize=7, color="g")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("unknowns")
    ax.set_ylabel("total time / total time of the default")
    ax.legend(fontsize=7)
    ax.set_title("Column solves against the program's default (setup + CG, same machine, same matrix)", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FOLDER, "figures", "fig_04_ratio_vs_size.png"), dpi=140)


if __name__ == "__main__":
    os.makedirs(os.path.join(FOLDER, "figures"), exist_ok=True)
    data = rows()
    fig_03(data)
    fig_04(data)
