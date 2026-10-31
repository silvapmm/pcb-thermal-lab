#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the adoption study, drawn from the JSON files that the studies leave in out/ (a figure whose file is missing is skipped with a message).
@details Files: fig_05_error_by_variant.png (study 1: mean and maximum error of E for the program and the zone variants, by set), fig_06_error_by_board.png (study 1: the error of every board of
         the family and the held-out set, program against the two zone variants), fig_07_raster.png (study 3), fig_08_footprint_potentials.png (study 5), fig_09_edge_and_offcentre.png (study 4).
         Numbers are those the scripts printed; the captions in the README say what each panel shows.
Usage: python research/lumped-zones-adoption/scripts/make_figures.py   (from the repository root, after the studies).
"""

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import matplotlib                                                           # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                             # noqa: E402

OUT = HERE.parent / "figures"
DATA = HERE.parent / "out"
COLORS = {"P245": "#7f7f7f", "Z_none": "#1f77b4", "Z_cap": "#d62728"}


def load(name):
    """!
    @brief Read a result file of out/.
    @param name File name.
    @return The JSON object, or None when the file is not there.
    """
    path = DATA / name
    if not path.exists():
        print("skipped (missing):", path)
        return None
    return json.load(open(path))


def fig_variants(path, data):
    """!
    @brief Mean and maximum absolute error of E by variant for the family and the held-out boards.
    @param path Output file.
    @param data Content of zones_on_245.json.
    @return None.
    """
    names = ["P245", "Z_none", "Z_cap", "Z_none_nomp", "Z_none_fr", "Z_cap_nocb"]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, key, title in zip(axs, ("family", "holdout"), ("36 boards of the family", "26 held-out boards")):
        rows = data[key]
        mean = [np.mean([abs(r["err"][n]) for r in rows]) for n in names]
        mx = [np.max([abs(r["err"][n]) for r in rows]) for n in names]
        x = np.arange(len(names))
        ax.bar(x - 0.2, mean, 0.4, label="mean |error|", color="#1f77b4")
        ax.bar(x + 0.2, mx, 0.4, label="max |error|", color="#ff7f0e")
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
        ax.axhline(10, color="k", lw=0.7, ls=":")
        ax.set_title(title, fontsize=9)
        ax.set_ylabel("error of the via effect, % of the reference")
    axs[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_by_board(path, data):
    """!
    @brief The error of every board for the program and the two zone variants, in the order of the family then the held-out set.
    @param path Output file.
    @param data Content of zones_on_245.json.
    @return None.
    """
    rows = data["family"] + data["holdout"]
    fig, ax = plt.subplots(figsize=(12, 4.2))
    x = np.arange(len(rows))
    for n in ("P245", "Z_none", "Z_cap"):
        ax.plot(x, [r["err"][n] for r in rows], "o-", ms=3, lw=0.6, color=COLORS[n], label=n)
    ax.axhspan(-10, 10, color="#dddddd", alpha=0.5)
    ax.axvline(len(data["family"]) - 0.5, color="k", lw=0.7)
    ax.set_xlabel("board (family, then held-out)")
    ax.set_ylabel("error of E, %  (positive: part too cool)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_raster(path, data):
    """!
    @brief Mean error of the program and the zone variant against the raster cell.
    @param path Output file.
    @param data Content of raster.json.
    @return None.
    """
    rows = data["family"]
    variants = [v for v in rows[0]["err"] if v != "P245"]
    cells = list(rows[0]["err"]["P245"].keys())
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for n, color in [("P245", COLORS["P245"])] + [(v, COLORS.get(v, "#1f77b4")) for v in variants]:
        ax.plot(range(len(cells)), [np.mean([abs(r["err"][n][c]) for r in rows]) for c in cells], "o-", color=color, label=n + " mean")
        ax.plot(range(len(cells)), [np.max([abs(r["err"][n][c]) for r in rows]) for c in cells], "s--", color=color, label=n + " max", alpha=0.6)
    ax.set_xticks(range(len(cells)))
    ax.set_xticklabels([c + (" mm" if c != "tied" else "") for c in cells])
    ax.set_ylabel("error of E, % of the reference (36 boards)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_potentials(path, rows):
    """!
    @brief Error of the stride and of the blocks against every cell, for the link term and the peak term of the footprint potentials.
    @param path Output file.
    @param rows Content of footprint_potential.json.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, (k, title) in zip(axs, ((lambda t: t[1] - t[0], "link term: phi_boundary - phi_mean"), (lambda t: t[0] - t[2], "peak term: phi_mean - phi_min"))):
        labels = [f"{r['kind']} {r['size']}\n{r['cell']:g}" for r in rows]
        st = [100 * (k(r["stride"]) / k(r["exact"]) - 1) for r in rows]
        bl = [100 * (k(r["block"]) / k(r["exact"]) - 1) for r in rows]
        x = np.arange(len(rows))
        ax.bar(x - 0.2, st, 0.4, label="stride (program)", color="#7f7f7f")
        ax.bar(x + 0.2, bl, 0.4, label="blocks", color="#d62728")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=6, rotation=90)
        ax.set_title(title, fontsize=9)
        ax.axhline(0, color="k", lw=0.6)
    axs[0].set_ylabel("error against every cell, %")
    axs[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_edge(path, rows):
    """!
    @brief The error of E of the boards of study 4 for the program and the zone variants.
    @param path Output file.
    @param rows Content of edge_offcentre.json.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(12, 4.4))
    x = np.arange(len(rows))
    for n in ("P245", "Z_none", "Z_cap"):
        ax.plot(x, [r["err"][n] for r in rows], "o-", ms=3, lw=0.6, color=COLORS[n], label=n)
    ax.axhspan(-10, 10, color="#dddddd", alpha=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels([r["label"].split(",")[0][:28] for r in rows], rotation=90, fontsize=5)
    ax.set_ylabel("error of E, %  (positive: part too cool)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Draw the data figures that have their data.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    d = load("zones_on_245.json")
    if d:
        fig_variants(OUT / "fig_05_error_by_variant.png", d)
        fig_by_board(OUT / "fig_06_error_by_board.png", d)
    d = load("raster.json")
    if d:
        fig_raster(OUT / "fig_07_raster.png", d)
    d = load("footprint_potential.json")
    if d:
        fig_potentials(OUT / "fig_08_footprint_potentials.png", d)
    d = load("edge_offcentre.json")
    if d:
        fig_edge(OUT / "fig_09_edge_and_offcentre.png", d)


if __name__ == "__main__":
    main()
