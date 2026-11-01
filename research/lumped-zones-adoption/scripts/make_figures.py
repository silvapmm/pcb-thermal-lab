#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the adoption study, drawn from the JSON files that the studies leave in out/ (a figure whose file is missing is skipped with a message).
@details Files: fig_05_error_by_variant.png (study 1: mean and maximum error of E for the program and the zone variants, by set), fig_06_error_by_board.png (study 1: the error of every board of
         the family and the held-out set, program against the two zone variants), fig_07_raster.png (study 3), fig_08_footprint_potentials.png (study 5), fig_09_edge_and_offcentre.png (study 4, with the review's percent of the rise), fig_10_hottest_temperature_check.png (the review: the hottest temperature with and without conducting vias, study_review.py), fig_14_profile_zones_against_fvm.png (study 7), fig_15_shen_case_results.png (study 8), fig_16_3d_barrels_check.png (study 9).
         Numbers are those the scripts printed; the captions in the README say what each panel shows.
Usage: python research/lumped-zones-adoption/scripts/make_figures.py [--new]   (from the repository root, after the studies; --new draws only figures 14 to 16).
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


def fig_profile(path, simple, full):
    """!
    @brief The square-wave profile with the zones against the FVM: the error of the peak on the three boards at three periods (with the control of the unpatched adapter) and over the 93 boards at 1 s.
    @param path Output file.
    @param simple Content of profile_simple.json.
    @param full Content of profile_all.json or None.
    @return None.
    """
    fig, axs = plt.subplots(1, 2 if full else 1, figsize=(13 if full else 7, 4.6))
    axs = np.atleast_1d(axs)
    a = axs[0]
    names = [("P245", "program", "#7f7f7f"), ("Z_none", "zones", "#1f77b4"), ("Z_unpatched", "zones, program's adapter (control)", "#d62728")]
    x = np.arange(len(simple))
    for k, (n, lab, col) in enumerate(names):
        a.bar(x + (k - 1) * 0.27, [r["err"][n]["peak"] for r in simple], 0.27, color=col, label=lab)
    a.set_xticks(x)
    a.set_xticklabels([f"{r['label'].replace(' in ', chr(10))}\n{r['period']:g} s" for r in simple], fontsize=5.5, rotation=0)
    a.axhline(0, color="k", lw=0.6)
    a.set_ylabel("error of the peak against the FVM\n(percent of the average steady rise)")
    a.set_title("three boards, three periods", fontsize=9)
    a.legend(fontsize=7)
    if full:
        b = axs[1]
        for n, lab, col in names[:2]:
            e = np.sort([r["err"][n]["peak"] for r in full])
            b.plot(np.arange(len(e)), e, ".", color=col, label=f"{lab}: mean abs {np.mean(np.abs(e)):.1f} %, max {np.max(np.abs(e)):.1f} %")
        b.axhline(0, color="k", lw=0.6)
        b.set_xlabel("boards, sorted by the error")
        b.set_ylabel("error of the peak (percent of the rise)")
        b.set_title(f"{len(full)} boards, period 1 s", fontsize=9)
        b.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_shen(path, d):
    """!
    @brief The Shen case: the resistance of the via array against the via diameter (equation 4 for two pads, the CFD markers read from the plot, the unit-cell solver, the program) and the models at 0.25 mm.
    @param path Output file.
    @param d Content of shen.json.
    @return None.
    """
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.5, 4.6))
    f = d["fig18a"]
    a.plot([r[0] for r in f], [r[1] for r in f], "D", mfc="none", color="#d62728", label="CFD, Fig. 18(a) (read from the plot)")
    a.plot([r[0] for r in f], [r[2] for r in f], "-", color="#7f7f7f", label="eq. (4), 5.6 mm pad, floor count")
    a.plot([r[0] for r in f], [r[3] for r in f], "-", color="#1f77b4", label="eq. (4), 5.0 mm pad (inferred), l w / (phi + s)^2")
    sw = d["sweep"]
    a.plot([r[0] for r in sw], [r[2] for r in sw], "s-", color="#2ca02c", label="unit-cell solver, 5.6 mm pad")
    a.plot([r[0] for r in sw], [r[4]["fvm"] for r in sw], "o--", color="#ff7f0e", label="program FVM 0.1 mm, 5.6 mm pad")
    a.set_xlabel("via diameter (mm)")
    a.set_ylabel("thermal resistance of the via array (K/W)")
    a.set_title("air-filled vias, Pattern I", fontsize=9)
    a.legend(fontsize=6.5)
    rows = [r for r in d["models"] if r[1] in (0.1, 0.2, 1.0, 0.05)]
    ref = d["solver"]["ref"]
    labels = [f"{r[0]} {r[1]:g}" for r in rows]
    b.bar(np.arange(len(rows)), [100 * (r[3] / ref - 1) for r in rows], color="#1f77b4")
    b.set_xticks(np.arange(len(rows)))
    b.set_xticklabels(labels, rotation=60, fontsize=7)
    b.axhline(0, color="k", lw=0.6)
    b.set_ylabel("against the unit-cell solver (%)")
    b.set_title(f"12 x 12 board: solver {ref:.3f} K/W, eq. (4) {d['eq4']:.3f}, CFD 1.86", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_barrels(path, rows):
    """!
    @brief Errors against the 3D solver with the barrels drawn: the via effect and the hottest rise of the program, the zones and the FVM on six boards.
    @param path Output file.
    @param rows Content of barrels_3d.json.
    @return None.
    """
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.6))
    keys = [("e_p", "t_p", "program", "#7f7f7f"), ("e_z", "t_z", "zones", "#1f77b4"), ("e_f", "t_f", "FVM 0.25 mm", "#2ca02c")]
    x = np.arange(len(rows))
    for k, (ke, kt, lab, col) in enumerate(keys):
        a.bar(x + (k - 1) * 0.27, [r["err"][ke] for r in rows], 0.27, color=col, label=lab)
        b.bar(x + (k - 1) * 0.27, [r["err"][kt] for r in rows], 0.27, color=col, label=lab)
    tick = [f"{'off centre' if r['label'].startswith('5x5') else r['label'].split(' ')[0]}\n{'Cu' if r['fill'] else 'open'}" for r in rows]
    for ax, t in ((a, "via effect E: error against the 3D solver (%)"), (b, "hottest rise: error against the 3D solver (%)")):
        ax.set_xticks(x)
        ax.set_xticklabels(tick, fontsize=7)
        ax.axhline(0, color="k", lw=0.6)
        ax.set_title(t, fontsize=9)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Draw the data figures that have their data (`--new`: only the figures 14 to 16 of this pass; the figures 5 to 10 are those of the earlier run and are kept).
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    only_new = "--new" in sys.argv
    d = None if only_new else load("zones_on_245.json")
    if d:
        fig_variants(OUT / "fig_05_error_by_variant.png", d)
        fig_by_board(OUT / "fig_06_error_by_board.png", d)
    d = None if only_new else load("raster.json")
    if d:
        fig_raster(OUT / "fig_07_raster.png", d)
    d = None if only_new else load("footprint_potential.json")
    if d:
        fig_potentials(OUT / "fig_08_footprint_potentials.png", d)
    review = None if only_new else load("review.json")
    d = None if only_new else load("edge_offcentre.json")
    if d:
        fig_edge(OUT / "fig_09_edge_and_offcentre.png", d, review)
    if review:
        fig_absolute(OUT / "fig_10_hottest_temperature_check.png", review)
    simple = load("profile_simple.json")
    if simple:
        fig_profile(OUT / "fig_14_profile_zones_against_fvm.png", simple, load("profile_all.json"))
    d = load("shen.json")
    if d:
        fig_shen(OUT / "fig_15_shen_case_results.png", d)
    d = load("barrels_3d.json")
    if d:
        fig_barrels(OUT / "fig_16_3d_barrels_check.png", d)


if __name__ == "__main__":
    main()
