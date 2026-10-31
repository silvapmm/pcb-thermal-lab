#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the via-group investigation, drawn from the JSON files that the studies write in out/ (and from two short solves).
@details Files (numbering continues after the diagrams 01 to 05 of make_diagrams.py):
         fig_06_family_errors.png         error of E of the Lumped variants against the share of the footprint that the vias cover (`study_family.py`);
         fig_07_best_group_factor.png     the factor on the group term that would make E exact, per board (the oracle scan: no fixed factor fits);
         fig_08_zone_temperatures.png     the temperatures of the rest of the footprint (A) and of the core (C) in every layer, the reference against the series group term and the zones;
         fig_09_example_board.png         the example board of the program with arrays under U1 (`study_example_board.py`);
         fig_10_fish_microspreading.png   the reproduction of the published unit cell (`study_fish_case.py`);
         fig_11_cell_link_exact.png       the cell problem against the two closed forms (`study_cell_link.py`).
Usage: python research/lumped-via-groups/scripts/make_figures.py   (from the repository root, after the studies; missing inputs are skipped with a message).
"""

import json
import math
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FOLDER = HERE.parent
sys.path.insert(0, str(FOLDER / "lib"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(FOLDER.parent / "lumped-analytic-vias" / "lib"))
sys.path.insert(0, str(FOLDER.parent))

import matplotlib                                                           # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                             # noqa: E402

OUT = FOLDER / "figures"
COLORS = {"L_prog": "#999999", "L_nn": "#1f77b4", "L_grp0": "#d62728", "L_loss": "#ff7f0e", "L_zone": "#2ca02c", "L_ring": "#9467bd", "L_out": "#8c564b"}


def _load(name):
    """!
    @brief Read a JSON file of out/.
    @param name File name.
    @return The data, or None if the file is missing.
    """
    p = FOLDER / "out" / name
    if not p.exists():
        print("missing", p)
        return None
    return json.load(open(p))


def fig_family(path):
    """!
    @brief Error of E against the core share, one panel per fill.
    @param path Output file.
    @return None.
    """
    rows = _load("family.json")
    if rows is None:
        return
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for ax, fill, lab in zip(axs, (0.0, 385.0), ("open barrels", "copper-filled")):
        sel = [r for r in rows if r["spec"].get("fill", 0.0) == fill]
        for n in ("L_prog", "L_nn", "L_grp0", "L_zone"):
            x = [r["ref"]["core_share"] for r in sel]
            y = [100 * (r["E"][n] / r["ref"]["E"] - 1) for r in sel]
            ax.scatter(x, y, s=22, color=COLORS[n], label=n, alpha=0.85)
        ax.axhline(0, color="k", lw=0.8)
        ax.axhspan(-10, 10, color="#2ca02c", alpha=0.07)
        ax.set_title(lab)
        ax.set_xlabel("share of the footprint covered by the via core (reference)")
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("error of the via effect E, %  (+: model cooler)")
    axs[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_best_factor(path):
    """!
    @brief The factor on the group term that makes E exact against the core share.
    @param path Output file.
    @return None.
    """
    import study_family as sf
    rows = _load("family.json")
    if rows is None:
        return
    fig, ax = plt.subplots(figsize=(7, 4.6))
    for fill, c, lab in ((0.0, "#1f77b4", "open"), (385.0, "#d62728", "copper")):
        pts = []
        for r in rows:
            if r["spec"].get("fill", 0.0) != fill:
                continue
            bf = sf.best_factor(r)
            pts.append((r["ref"]["core_share"], 1.2 if bf is None else bf, bf is None))
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], color=c, label=lab, s=24)
    ax.axhline(1.0, color="k", lw=0.8)
    ax.text(0.02, 1.02, "full group term", fontsize=8)
    ax.text(0.02, 0.02, "micro well only", fontsize=8)
    ax.set_ylim(-0.05, 1.3)
    ax.set_xlabel("share of the footprint covered by the via core")
    ax.set_ylabel("factor on the group term for exact E\n(1.2: no factor in 0 to 1 does it)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_zone_temperatures(path):
    """!
    @brief Temperatures of A and C per layer for two boards: reference, series group term, zones.
    @param path Output file.
    @return None.
    """
    import harness as hz
    import lumped_groups as lg
    import lumped_zones as lz
    import program_cases as pc
    import refs
    from pcbthermal import lumped
    pc.load_libraries()
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, spec in zip(axs, (dict(layers=4, n=5, pitch=1.2, fill=385.0, src=10.0), dict(layers=4, n=5, pitch=1.2, fill=385.0, src=14.0))):
        spec = {**refs.DEFAULT, **spec}
        ref = refs.reference(spec)
        p = refs.make_problem(spec)
        layers = np.arange(1, spec["layers"] + 1)
        ax.plot(layers, ref["ann"], "k-o", label="reference, rest of the footprint (A)")
        ax.plot(layers, ref["core"], "k--s", label="reference, core (C)")
        with lz.patched():
            lumped.solve_steady(p, 10, 0.5)
            th = lz.LAST["theta"]
        ax.plot(layers, th[:, 0] + 25.0 - 25.0, color=COLORS["L_zone"], marker="o", ls="-", label="zones, A")
        ax.plot(layers, th[:, 1], color=COLORS["L_zone"], marker="s", ls="--", label="zones, C")
        with lg.patched(macro="all"):
            r = lumped.solve_steady(p, 10, 0.5)
        T = r.T - 25.0
        c = spec["side"] * 1e-3 / 2
        x = (np.arange(T.shape[2]) + 0.5) * r.dx
        m = (np.abs(x[None, :] - c) < spec["src"] * 1e-3 / 2) & (np.abs(x[:, None] - c) < spec["src"] * 1e-3 / 2)
        ax.plot(layers, [T[k][m].mean() for k in range(spec["layers"])], color=COLORS["L_grp0"], marker="^", label="series group term, footprint mean")
        ax.set_title(f"5 x 5 copper vias at 1.2 mm under a {spec['src']:.0f} mm source")
        ax.set_xlabel("copper layer")
        ax.set_ylabel("temperature rise, K")
        ax.set_xticks(layers)
        ax.grid(alpha=0.3)
    axs[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_example(path):
    """!
    @brief Error of E on the example board with arrays under U1, by variant.
    @param path Output file.
    @return None.
    """
    rows = _load("real_boards.json")
    if rows is None:
        return
    names = ["L_prog", "L_nn", "L_grp0", "L_out", "L_zone"]
    labels = [f"{r['board'].replace('example, ', '')} {'Cu' if r['fill'] else 'open'}" for r in rows]
    fig, ax = plt.subplots(figsize=(12, 4.6))
    w = 0.16
    for k, n in enumerate(names):
        ax.bar(np.arange(len(rows)) + (k - 2) * w, [100 * (r["E"][n] / r["E_ref"] - 1) for r in rows], w, color=COLORS.get(n, "#777777"), label=n)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(np.arange(len(rows)))
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("error of E against the corrected FVM, %")
    ax.legend(fontsize=8, ncol=5)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_fish(path):
    """!
    @brief The reproduction of the microspreading resistance of the published via cell against the correlation of the dissertation.
    @param path Output file.
    @return None.
    """
    import axisym_cell as ax_cell
    P, a, L = 100e-6, 30e-6, 500e-6
    phi = math.pi * a * a / (P * P)
    r1d = L / (P * P * (phi * 400.0 + 1.0 - phi))
    hs = np.logspace(0, 7, 15)
    rmsp = [ax_cell.unit_cell_resistance(a, P, L, 400.0, 1.0, h_top=h) - r1d for h in hs]
    fig, ax = plt.subplots(figsize=(7, 4.6))
    ax.semilogx(hs, rmsp, "o-", label="independent solver (this folder)")
    ax.semilogx(hs, 1240.0 / (1.0 + (hs * P / (1.0 * 15.5)) ** 0.96), "k--", label="correlation of Fish (2017), eq. 49")
    ax.set_xlabel("heat transfer coefficient on the top face, W/m2K")
    ax.set_ylabel("microspreading resistance, K/W")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_cell_exact(path):
    """!
    @brief The finite-difference cell problem against the lossless and lossy closed forms.
    @param path Output file.
    @return None.
    """
    import constriction as cr
    import study_cell_link as scl
    S, a = 0.0136, 5.6e-3
    fig, ax = plt.subplots(figsize=(7, 4.6))
    xs = np.linspace(0.02, 3.0, 20)
    for rho, c in ((0.15, "#1f77b4"), (0.3, "#2ca02c"), (0.6, "#d62728")):
        ex = [scl.exact_link(S, S * (x / a) ** 2, rho * a, a) for x in xs]
        ax.plot(xs, [cr.krogh(S, a, rho * a) / e for e in ex], color=c, ls="--", label=f"lossless Krogh / exact, r_c/a = {rho}")
        ax.plot(xs, [cr.cell_with_loss(S, S * (x / a) ** 2, rho * a, a, 1.0)["R_c"] / e for x, e in zip(xs, ex)], color=c, ls="-", label=f"lossy closed form / exact, r_c/a = {rho}")
    ax.set_xlabel("a / lambda")
    ax.set_ylabel("closed form / finite-difference cell problem")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Draw all the data figures that have their inputs.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_family(OUT / "fig_06_family_errors.png")
    fig_best_factor(OUT / "fig_07_best_group_factor.png")
    fig_zone_temperatures(OUT / "fig_08_zone_temperatures.png")
    fig_example(OUT / "fig_09_example_board.png")
    fig_fish(OUT / "fig_10_fish_microspreading.png")
    fig_cell_exact(OUT / "fig_11_cell_link_exact.png")


if __name__ == "__main__":
    main()
