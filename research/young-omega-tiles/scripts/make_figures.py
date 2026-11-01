#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of research/young-omega-tiles from the JSON files that the studies write in out/ (figures 01 to 07 are drawn by make_diagrams.py).
@details 08 sweeps against omega on a plate: measured, predicted by Young's relation, the program's omega, Young's and the estimates (study_s3_exact part D);
         09 Lanczos and Rayleigh error of 1 - rho_J against the steps on plates with even and uneven losses (study_s3_exact part C);
         10 the estimate error against the type of board of the program (study_s3_boards part 1);
         11 the cost of the estimate against the solve: seconds against the grid (study_s3_boards part 3);
         12 error of the Analytic via effect against the tile size on the unit cells and the simple boards (study_s4_tile parts 1 and 2);
         13 the rules against the measured plateau: tile chosen against the nearest-neighbour distance, and mean / max error of every rule (study_s4_rule);
         14 modes of the tile Green function against the board size (study_s4_tile part 3);
         15 cost of the correction against the number of vias: unknowns, seconds, memory (study_s4_arrays);
         16 error against the number of vias for Lumped and Analytic, before and after (study_s4_arrays);
         17 Lumped lone via: error against the distance and the number of rings (study_s4_lumped part 1);
         18 the copper-fill gain of the example board and its denser arrays in every model (study_s4_example).
         A figure whose JSON is missing is skipped with a message. Usage: python research/young-omega-tiles/scripts/make_figures.py (from the repository root, after the studies).
"""

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import matplotlib                                                           # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                             # noqa: E402

import outio                                                                # noqa: E402

OUT = HERE.parent / "figures"


def get(name):
    """!
    @brief Read a result file or None.
    @param name Name in out/.
    @return The object or None.
    """
    try:
        return outio.load(name)
    except FileNotFoundError:
        print("missing out/%s.json: figure skipped" % name)
        return None


def save(fig, name):
    """!
    @brief Save a figure into figures/.
    @param fig Figure.
    @param name File name.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=110)
    plt.close(fig)
    print("wrote", name)


def fig_sweeps_omega():
    """!
    @brief Figure 08.
    @return None.
    """
    d = get("s3_exact")
    if not d:
        return
    c = d["D_curve"]
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    w = [p["omega"] for p in c["curve"] if p["sweeps"]]
    ax.semilogy(w, [p["sweeps"] for p in c["curve"] if p["sweeps"]], "o-", label="measured (independent red-black SOR)")
    ax.semilogy([p["omega"] for p in c["curve"]], [p["predicted"] for p in c["curve"]], "--", label="asymptotic rate from Young's relation")
    ax.axvline(c["omega_young"], color="#2ca02c", label=f"Young {c['omega_young']:.4f}")
    ax.axvline(c["omega_program"], color="#d62728", label=f"program's formula {c['omega_program']:.4f}")
    ax.set_xlabel("$\\omega$")
    ax.set_ylabel("sweeps to 1e-9")
    ax.set_title(c["case"])
    ax.legend(fontsize=8)
    save(fig, "fig_08_sweeps_against_omega.png")


def fig_lanczos_k():
    """!
    @brief Figure 09.
    @return None.
    """
    d = get("s3_exact")
    if not d:
        return
    ks = (2, 3, 5, 10, 20)
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for r in d["C"]:
        y = [100 * ((1 - r[f"lanczos{k}"]) / (1 - r["rho"]) - 1) for k in ks]
        ax.semilogy(ks, np.maximum(np.abs(y), 1e-6), "o-", label=r["case"])
        ax.semilogy([1], [max(abs(100 * ((1 - r["rq"]) / (1 - r["rho"]) - 1)), 1e-6)], "s", color=ax.lines[-1].get_color())
    ax.set_xlabel("Lanczos steps (square: Rayleigh bound = 1 product)")
    ax.set_ylabel("error of 1 - $\\rho_J$ (%)")
    ax.legend(fontsize=6)
    save(fig, "fig_09_lanczos_error_against_steps.png")


def fig_board_types():
    """!
    @brief Figure 10.
    @return None.
    """
    d = get("s3_boards")
    if not d:
        return
    recs = d["part1"]
    names = ["Rayleigh", "Lanczos 3", "Lanczos 5", "Lanczos 10", "Lanczos 20", "power 200"]
    fig, ax = plt.subplots(figsize=(11, 5))
    w = 0.13
    for i, n in enumerate(names):
        ax.bar(np.arange(len(recs)) + i * w, [max(r["estimates"][n]["err_1mrho_pct"], 1e-3) for r in recs], w, label=n)
    ax.set_yscale("log")
    ax.set_xticks(np.arange(len(recs)) + 2.5 * w)
    ax.set_xticklabels([r["label"] for r in recs], rotation=30, ha="right", fontsize=7)
    ax.set_ylabel("error of 1 - $\\rho_J$ (%), positive = safe side")
    ax.legend(fontsize=7)
    save(fig, "fig_10_estimate_error_against_board_type.png")


def fig_cost():
    """!
    @brief Figure 11.
    @return None.
    """
    d = get("s3_boards")
    if not d:
        return
    p = d["part3"]
    N = [r["N"] for r in p]
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for key, lab in (("t_direct", "direct solve"), ("t_sor_program", "SOR, program's omega"), ("t_sor_young", "SOR, Young's omega"), ("t_lanczos10", "estimate: Lanczos 10"), ("t_rq", "estimate: Rayleigh")):
        ax.loglog(N, [r[key] for r in p], "o-", label=lab)
    ax.set_xlabel("unknowns")
    ax.set_ylabel("seconds")
    ax.legend(fontsize=8)
    save(fig, "fig_11_cost_of_the_estimate.png")


def fig_tile_error():
    """!
    @brief Figure 12.
    @return None.
    """
    d = get("s4_tile")
    if not d:
        return
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.8))
    for r in d["unit"]:
        t = sorted(float(k) for k in r["tiles"])
        a.plot(t, [r["tiles"][str(x)] for x in t], "o-", label=f"pitch {r['pitch']} mm")
    a.axhspan(-3, 3, color="#dddddd", alpha=0.5)
    a.set_xlabel("tile (mm)")
    a.set_ylabel("error of the via effect (%)")
    a.set_title("unit cell of a lattice")
    a.legend(fontsize=7)
    for r in d["simple"]:
        if r["modes_c"] != 0:
            continue
        t = sorted(float(k) for k in r["tiles"])
        b.plot(t, [r["tiles"][str(x)] for x in t], "o-", label=r["label"])
    b.axhspan(-3, 3, color="#dddddd", alpha=0.5)
    b.set_xlabel("tile (mm)")
    b.set_title("simple boards (64 modes of G)")
    b.legend(fontsize=6)
    save(fig, "fig_12_error_against_the_tile.png")


def fig_rules():
    """!
    @brief Figure 13.
    @return None.
    """
    d = get("s4_rule")
    if not d:
        return
    res = d["simple"] + d["dense"]
    rules = list(dict.fromkeys(r["rule"] for r in res))
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.8))
    mean = [np.mean([abs(r["err"]) for r in res if r["rule"] == n]) for n in rules]
    mx = [np.max([abs(r["err"]) for r in res if r["rule"] == n]) for n in rules]
    x = np.arange(len(rules))
    a.bar(x - 0.2, mean, 0.4, label="mean |error|")
    a.bar(x + 0.2, mx, 0.4, label="max |error|")
    a.set_xticks(x)
    a.set_xticklabels(rules, rotation=40, ha="right", fontsize=7)
    a.set_ylabel("%")
    a.legend()
    for n in rules:
        pts = [(r["d_nn_mm"], r["tile_mm"]) for r in res if r["rule"] == n and np.isfinite(r["d_nn_mm"] or np.nan)]
        if pts:
            b.plot(*zip(*sorted(pts)), "o-", ms=3, label=n)
    b.set_xlabel("median nearest-neighbour distance (mm)")
    b.set_ylabel("tile chosen (mm)")
    b.set_xscale("log")
    b.legend(fontsize=6)
    save(fig, "fig_13_tile_rules.png")


def fig_modes():
    """!
    @brief Figure 14.
    @return None.
    """
    d = get("s4_tile")
    if not d:
        return
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for t in sorted({r["tile"] for r in d["modes"]}):
        for c, ls in ((0.0, "--"), (2.0, "-")):
            pts = sorted((r["side"], r["err"]) for r in d["modes"] if r["tile"] == t and r["modes_c"] == c)
            if pts:
                ax.plot(*zip(*pts), ls, marker="o", label=f"tile {t} mm, " + ("64 modes" if c == 0 else "2 W/t modes"))
    ax.set_xlabel("board side (mm)")
    ax.set_ylabel("error of the via effect (%)")
    ax.legend(fontsize=7)
    save(fig, "fig_14_modes_against_board_size.png")


def fig_cost_vias():
    """!
    @brief Figure 15.
    @return None.
    """
    d = get("s4_arrays")
    if not d:
        return
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.6))
    for name in ("A_fin", "A_rule", "A_rule+modes"):
        rr = sorted((r["vias"], r["variants"][name]["unknowns"], r["variants"][name]["seconds"]) for r in d if r["pitch"] == 1.0)
        a.loglog([x[0] for x in rr], [x[1] for x in rr], "o-", label=name)
        b.loglog([x[0] for x in rr], [x[2] for x in rr], "o-", label=name)
    b.loglog([x["vias"] for x in d if x["pitch"] == 1.0], [x["variants"]["A_prog"]["seconds"] for x in d if x["pitch"] == 1.0], "k--", label="A_prog")
    a.set_xlabel("vias (pitch 1.0 mm)")
    a.set_ylabel("unknowns of the dense system")
    b.set_xlabel("vias (pitch 1.0 mm)")
    b.set_ylabel("seconds of the run with vias")
    a.legend(fontsize=7)
    b.legend(fontsize=7)
    save(fig, "fig_15_cost_against_the_number_of_vias.png")


def fig_error_vias():
    """!
    @brief Figure 16.
    @return None.
    """
    d = get("s4_arrays")
    if not d:
        return
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for ax, names, title in ((a, ("L_prog", "L_grp0"), "Lumped"), (b, ("A_prog", "A_fin", "A_rule", "A_rule+modes"), "Analytic")):
        for pitch, ls in ((1.0, "-"), (2.0, "--"), (3.5, ":")):
            for n in names:
                rr = sorted((r["vias"], r["variants"][n]["err"]) for r in d if r["pitch"] == pitch)
                if rr:
                    ax.plot(*zip(*rr), ls, marker="o", ms=3, label=f"{n}, pitch {pitch}")
        ax.set_xscale("log")
        ax.set_xlabel("vias")
        ax.set_title(title)
        ax.axhspan(-5, 5, color="#dddddd", alpha=0.5)
        ax.legend(fontsize=5)
    a.set_ylabel("error of the via effect (%)")
    save(fig, "fig_16_error_against_the_number_of_vias.png")


def fig_lone():
    """!
    @brief Figure 17.
    @return None.
    """
    d = get("s4_lumped")
    if not d:
        return
    names = ["program", "micro nn", "cluster (L_grp0)", "cluster, lone cap 2"]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for n in names:
        for rings, ls in ((6, ":"), (10, "-"), (24, "--")):
            pts = sorted((r["distance"], r["err"][n]) for r in d["lone"] if r["rings"] == rings)
            if pts:
                ax.plot(*zip(*pts), ls, marker="o", ms=3, label=f"{n}, {rings} rings")
    ax.set_xlabel("via distance from the source centre (mm)")
    ax.set_ylabel("error of the via effect (%)")
    ax.legend(fontsize=5, ncol=2)
    save(fig, "fig_17_lumped_lone_via_against_distance_and_rings.png")


def fig_example():
    """!
    @brief Figure 18.
    @return None.
    """
    d = get("s4_example")
    if not d:
        return
    cols = [k for k in d["arrays"][0] if k != "board"]
    fig, ax = plt.subplots(figsize=(11, 4.6))
    w = 0.25
    for i, rec in enumerate(d["arrays"]):
        ax.bar(np.arange(len(cols)) + i * w, [rec[c]["gain"] for c in cols], w, label=rec["board"])
    ax.set_xticks(np.arange(len(cols)) + w)
    ax.set_xticklabels(cols, rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("gain of the copper fill (K)")
    ax.legend(fontsize=8)
    save(fig, "fig_18_copper_fill_gain_example_board.png")


def main():
    """!
    @brief Draw every data figure whose results exist.
    @return None.
    """
    for f in (fig_sweeps_omega, fig_lanczos_k, fig_board_types, fig_cost, fig_tile_error, fig_rules, fig_modes, fig_cost_vias, fig_error_vias, fig_lone, fig_example):
        f()


if __name__ == "__main__":
    main()
