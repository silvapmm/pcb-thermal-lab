#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the adoption study, drawn from the JSON files that the studies leave in out/ (a figure whose file is missing is skipped with a message).
@details Files: fig_05_error_by_variant.png (study 1: mean and maximum error of E for the program and the zone variants, by set), fig_06_error_by_board.png (study 1: the error of every board of
         the family and the held-out set, program against the two zone variants), fig_07_raster.png (study 3), fig_08_footprint_potentials.png (study 5), fig_09_edge_and_offcentre.png (study 4, with the review's percent of the rise), fig_10_hottest_temperature_check.png (the review: the hottest temperature with and without conducting vias, study_review.py).
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


def _short(label):
    """!
    @brief Short tick label of a board of study 4 ("a 4 Cu": group, shift or offset, fill).
    @param label Board label of the study.
    @return str.
    """
    g = label[1]
    fill = "Cu" if label.endswith("Cu") else "open"
    if g == "a":
        v = label.split("shifted ")[1].split(" ")[0]
    elif g == "b":
        v = label.split("centre ")[1].split(",")[0].strip("(") + "," + label.split(", ")[1].strip(")")
    elif g == "c":
        v = label.split("under ")[1].split(",")[0]
    else:
        v = label.split("via ")[1].split(" ")[0]
    return f"{g} {v} {fill}"


def fig_edge(path, rows, review=None):
    """!
    @brief The boards of study 4: the error of the via effect (left) and, from the review, the same error in percent of the reference rise (right), grouped by kind.
    @param path Output file.
    @param rows Content of edge_offcentre.json.
    @param review Content of review.json (its "edge" rows) or None (then one panel).
    @return None.
    """
    # order: by group, copper then open inside each group, so that the groups read as blocks
    order = sorted(range(len(rows)), key=lambda i: (rows[i]["label"][1], rows[i]["label"].endswith("open"), i))
    rows = [rows[i] for i in order]
    edge = None
    if review and "edge" in review:
        by_label = {r["label"]: r for r in review["edge"]}
        edge = [by_label.get(r["label"]) for r in rows]
    ncol = 2 if edge else 1
    fig, axs = plt.subplots(1, ncol, figsize=(13, 5.2), squeeze=False)
    x = np.arange(len(rows))
    panels = [(axs[0, 0], [[r["err"][n] for r in rows] for n in ("P245", "Z_none")], "error of the via effect E, %\n(positive: the part too cool)", (-10, 10))]
    if edge:
        panels.append((axs[0, 1], [[e["pct"][n] for e in edge] for n in ("P245", "Z_none")], "error of the hottest temperature, % of the rise\n(positive: the part too cool)", (-5, 5)))
    for ax, (vp, vz), ylabel, band in [(p[0], p[1], p[2], p[3]) for p in panels]:
        ax.axhspan(*band, color="#e6e6e6", zorder=0)
        ax.axhline(0, color="k", lw=0.6)
        ax.plot(x - 0.15, vp, "s", ms=5, color=COLORS["P245"], label="program 2.4.5")
        ax.plot(x + 0.15, vz, "o", ms=5, color=COLORS["Z_none"], label="zones (Z_none)")
        prev = None
        for i, r in enumerate(rows):
            if prev is not None and r["label"][1] != prev:
                ax.axvline(i - 0.5, color="#999999", lw=0.8, ls="--")
            prev = r["label"][1]
        ax.set_xticks(x)
        ax.set_xticklabels([_short(r["label"]) for r in rows], rotation=90, fontsize=7)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.legend(fontsize=8, loc="upper right")
    axs[0, 0].set_title("a: 5x5 shifted (mm) under 12x12   b: off centre (mm)   c: footprint (mm)   d: 3x3 outside (mm)", fontsize=8)
    if edge:
        axs[0, 1].set_title("the same boards: kelvin of the error over the reference rise", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def fig_absolute(path, review):
    """!
    @brief The review's check of the hottest temperature on the 36 + 26 boards: program and zones with vias against the reference, and the zones with vias that conduct nothing against the no-via reference.
    @param path Output file.
    @param review Content of review.json.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.6), sharey=True)
    for ax, key, title in ((axs[0], "family", "36 boards of the family"), (axs[1], "holdout", "26 held-out boards")):
        rows = review["absolute"][key]["rows"]
        x = np.arange(len(rows))
        e_p = [r["err_P245"] for r in rows]
        e_z = [r["err_Z"] for r in rows]
        e_d = [100 * (r["Z_dead"] / r["ref_without"] - 1) for r in rows]
        ax.axhspan(-2, 2, color="#e6e6e6", zorder=0)
        ax.axhline(0, color="k", lw=0.6)
        ax.plot(x, e_p, "s", ms=4.5, color=COLORS["P245"], label="program, with vias")
        ax.plot(x, e_z, "o", ms=4.5, color=COLORS["Z_none"], label="zones, with vias")
        ax.plot(x, e_d, "v", ms=4.5, mfc="none", color=COLORS["Z_cap"], label="zones, vias that conduct nothing\n(against the no-via reference)")
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("board", fontsize=9)
    axs[0].set_ylabel("hottest temperature against the reference, %\n(negative: the part too cool)", fontsize=9)
    axs[1].legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=110)
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
    review = load("review.json")
    d = load("edge_offcentre.json")
    if d:
        fig_edge(OUT / "fig_09_edge_and_offcentre.png", d, review)
    if review:
        fig_absolute(OUT / "fig_10_hottest_temperature_check.png", review)


if __name__ == "__main__":
    main()
