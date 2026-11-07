#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the published-cases follow-up, drawn from the JSON files that the studies write in out/ (run the studies first).
@details Writes figures/fig_05_table2_strip.png, fig_06_program_on_the_strip_cell.png, fig_07_lemczyk_tables.png, fig_08_coupon_program.png, fig_09_shen_via_arrays.png and fig_10_near_edge_sweeps.png.
         Run from the repository root after the studies: .venv/bin/python research/published-cases-followup/scripts/make_figures.py
"""

import json
from pathlib import Path

import _bootstrap
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402

import series as S                       # noqa: E402

OUT = _bootstrap.OUT
FIG = _bootstrap.FIGURES
COL = {"fvm": "#1f77b4", "fvm@0.25": "#1f77b4", "fdm": "#2ca02c", "fdm@0.25": "#2ca02c", "solid3d": "#d62728", "lumped": "#9467bd", "analytic": "#ff7f0e", "ref": "k"}


def load(name):
    """!
    @brief Read one JSON of out/.
    @param name File name.
    @return Parsed content.
    """
    return json.loads((OUT / name).read_text())


def fig05():
    """!
    @brief Table 2 of Yovanovich, Muzychka and Culham: the four curves, the printed points and the independent solver.
    @return None.
    """
    eps = np.linspace(0.01, 0.9, 90)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    ax[0].plot(eps, [S.psi_isoflux(e, 20000) for e in eps], label="isoflux, eq. 24", color="#1f77b4")
    ax[0].plot(eps, [S.psi_parabolic(e, 20000) for e in eps], label="parabolic, eq. 28", color="#2ca02c")
    ax[0].plot(eps, [S.psi_equivalent_isothermal(e, 20000) for e in eps], label="equivalent isothermal, eq. 26", color="#ff7f0e")
    ax[0].plot(eps, [S.psi_true_isothermal(e) for e in eps], label="true isothermal, eq. 27", color="k", ls="--")
    pe = (0.02, 0.04, 0.06, 0.08, 0.10, 0.20, 0.40, 0.60, 0.80)
    ax[0].plot(pe, (1.1377, 0.9172, 0.7883, 0.6970, 0.6263, 0.4083, 0.1984, 0.0882, 0.0255), "o", color="#1f77b4", mfc="none", label="Table 2 (printed)")
    b = [r for r in load("table2_strip.json")["B"] if "fv_isoflux" in r]
    ax[0].plot([r["eps"] for r in b], [r["fv_isoflux"] for r in b], "x", color="r", label="independent 2D solve, isoflux")
    ax[0].plot([r["eps"] for r in b], [r["fv_iso"] for r in b], "+", color="r", label="independent 2D solve, isothermal")
    ax[0].set_yscale("log")
    ax[0].set_xlabel("relative strip size eps = a / c")
    ax[0].set_ylabel("psi = k R_s")
    ax[0].legend(fontsize=7)
    ax[0].set_title("Table 2 (semi-infinite channel)", fontsize=9)
    e = np.array([0.02, 0.2, 0.4, 0.6, 0.8])
    ax[1].plot(e, [0.5 * (S.psi_isoflux(x) + S.psi_equivalent_isothermal(x)) for x in e], "s-", label="[Eq. (24) + Eq. (26)] / 2 (as the heading says)", color="#ff7f0e")
    ax[1].plot(e, [0.5 * (S.psi_isoflux(x) + S.psi_true_isothermal(x)) for x in e], "o-", label="[Eq. (24) + Eq. (27)] / 2", color="#1f77b4")
    ax[1].plot(e, (1.120, 0.3911, 0.1838, 0.0779, 0.0208), "k^", ms=8, mfc="none", label="Table 3 row, printed")
    ax[1].set_yscale("log")
    ax[1].set_xlabel("eps")
    ax[1].legend(fontsize=7)
    ax[1].set_title("Table 3: the printed 'average of (24) and (26)' is the average of (24) and (27)", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig_05_table2_strip.png", dpi=105)
    plt.close(fig)


def fig06():
    """!
    @brief The program's models against equation 23 as the slab gets thicker.
    @return None.
    """
    rows = load("table2_strip.json")["C"]
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for ax, bi in zip(axs, (2.0, 2.5e4)):
        for eps, ls in ((0.2, "-"), (0.6, "--")):
            sel = sorted([r for r in rows if r["bi"] == bi and r["eps"] == eps], key=lambda r: r["tau"])
            taus = [r["tau"] for r in sel]
            for key, col, lab in (("fvm@0.5", COL["fvm"], "fvm 0.5 mm"), ("fvm@0.25*", "#17becf", "fvm 0.25 mm, 16 sub-gaps"), ("fdm@0.25", COL["fdm"], "fdm 0.25 mm"), ("solid3d@0.5", COL["solid3d"], "solid3d 4 slabs"),
                                  ("solid3d@0.5*", "#e377c2", "solid3d 16 slabs"), ("analytic@0.5", COL["analytic"], "analytic"), ("lumped@0.5", COL["lumped"], "lumped")):
                ax.plot(taus, [r["models"][key]["err_pct"] for r in sel], ls, marker="o", color=col, label=lab if eps == 0.2 else None)
        ax.axhline(0, color="k", lw=0.6)
        ax.set_xscale("log")
        ax.set_ylim(-100, 100)
        ax.set_xlabel("relative thickness tau = t / c")
        ax.set_title(f"Bi = {bi:g} (solid: eps 0.2, dashed: eps 0.6)", fontsize=9)
    axs[0].set_ylabel("error of psi against equation 23, %")
    axs[0].legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(FIG / "fig_06_program_on_the_strip_cell.png", dpi=105)
    plt.close(fig)


def fig07():
    """!
    @brief Lemczyk and others: Q_c of Table 1 with h1 = 0 and with Bi1 = 0.001, and the two readings of the R of Table 4.
    @return None.
    """
    d = load("lemczyk.json")
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    t1 = d["table1"]
    x = np.arange(len(t1))
    ax[0].plot(x, [r["printed"][2] for r in t1], "ko", mfc="none", ms=9, label="Q_c printed")
    ax[0].plot(x, [r["qc_h1_0"] for r in t1], "s", color="#d62728", label="solver, h1 = 0 (the text)")
    ax[0].plot(x, [r["qc_bi1_001"] for r in t1], "+", color="#1f77b4", ms=10, label="solver, Bi1 = 0.001")
    ax[0].set_yscale("log")
    ax[0].set_xlabel("row of Table 1")
    ax[0].set_ylabel("Q_c, W")
    ax[0].legend(fontsize=8)
    ax[0].set_title("Case (c): the printed numbers are those of Bi1 = 0.001", fontsize=9)
    t4 = d["table4"]
    w = [r["wl"] for r in t4]
    ax[1].plot(w, [r["printed"][0] for r in t4], "ko", mfc="none", ms=9, label="R printed (3-layer board)")
    ax[1].plot(w, [r["strip"] for r in t4], "s-", color="#d62728", label="solver: mean over the strip")
    ax[1].plot(w, [r["face"] for r in t4], "+-", color="#1f77b4", ms=10, label="solver: mean over the whole top face")
    ax[1].set_xlabel("w / L1")
    ax[1].set_ylabel("R, K/W (full cell)")
    ax[1].legend(fontsize=8)
    ax[1].set_title("Table 4: the printed R is the mean of the top face", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig_07_lemczyk_tables.png", dpi=105)
    plt.close(fig)


def fig08():
    """!
    @brief The coupon: R_solid of the solver and of the program's models on the base stack.
    @return None.
    """
    d = load("coupon_program.json")
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    for a, stack, title in ((ax[0], "base", "Base stack (FR-4 / Cu / FR-4 / Cu / FR-4)"), (ax[1], "case2", "Case 2 (Cu / FR-4 / Cu)")):
        rows = d[stack]
        eps = [r["eps"] for r in rows]
        for m in ("fvm", "fdm", "solid3d", "lumped", "analytic"):
            a.plot(eps, [r["models"][m][2] for r in rows], "o-", color=COL[m], label=m)
        a.axhline(0, color="k", lw=0.6)
        a.set_xscale("log")
        a.set_xlabel("epsilon = source area / board area")
        a.set_ylabel("R_solid of the model against the solver (same conditions), %")
        a.set_title(title, fontsize=9)
    ax[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fig_08_coupon_program.png", dpi=105)
    plt.close(fig)


def fig09():
    """!
    @brief The via arrays: equation 4, the unit cells and the program's models.
    @return None.
    """
    d = load("shen_vias.json")
    rows = d["C"]["rows"]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    lab = [f"{r['phi'] * 1e3:g} {r['filler'][:3]}" for r in rows]
    x = np.arange(len(rows))
    ax[0].plot(x, [r["eq4"] / r["unit_cell_ideal"] - 1 for r in rows], "ks", label="Shen eq. (4)")
    ax[0].plot(x, [r["unit_cell_paper"] / r["unit_cell_ideal"] - 1 for r in rows], "o", mfc="none", color="gray", label="unit cell of the paper")
    for key, col, name in (("fvm@p/3", COL["fvm"], "fvm"), ("fdm@p/3", COL["fdm"], "fdm"), ("solid3d@p/3", COL["solid3d"], "solid3d"), ("lumped@p/3", COL["lumped"], "lumped"), ("analytic@p/3", COL["analytic"], "analytic")):
        ax[0].plot(x, [r["models"][key] / r["unit_cell_ideal"] - 1 for r in rows], "o", color=col, label=name)
    ax[0].axhline(0, color="k", lw=0.6)
    ax[0].set_xticks(x)
    ax[0].set_xticklabels(lab, rotation=45, fontsize=7)
    ax[0].set_ylabel("R against the unit cell of the layered idealisation")
    ax[0].set_xlabel("via diameter (mm) and filler")
    ax[0].legend(fontsize=7, ncol=2)
    ax[0].set_title("Array resistance of 8 x 8 (6 x 6) vias", fontsize=9)
    a = d["A"]
    s = np.linspace(0.05e-3, 1.5e-3, 300)
    import study_shen_vias as SH
    for k, name, col in ((SH.K_AIR, "air", "#1f77b4"), (SH.K_SOLDER, "solder", "#d62728")):
        ax[1].plot(s * 1e3, [SH.theta_n(p, 0.2e-3, k) * 1e3 for p in s], color=col, label=f"eq. 5, {name}")
        po = SH.phi_opt(0.2e-3, k)
        ax[1].plot(po * 1e3, SH.theta_n(po, 0.2e-3, k) * 1e3, "o", color=col)
    ax[1].set_xlabel("via diameter, mm (s = 0.2 mm)")
    ax[1].set_ylabel("normalised resistance x 1e3")
    ax[1].legend(fontsize=8)
    ax[1].set_title(f"optimal diameters: {a['air']['phi_opt_eq7'] * 1e3:.3f} and {a['solder']['phi_opt_eq7'] * 1e3:.3f} mm (printed about 0.25 and 0.8)", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig_09_shen_via_arrays.png", dpi=105)
    plt.close(fig)


def fig10():
    """!
    @brief The source near an edge and near a corner: the error of each model against the exact thin plate.
    @return None.
    """
    d = load("near_edge.json")
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for ax, key, title in ((axs[0], "sweep_edge", "gap to one edge (source centred along it)"), (axs[1], "sweep_corner", "diagonal gap to the corner")):
        rows = d[key]
        g = [r["gap_mm"] for r in rows]
        for m in ("fvm", "fdm", "solid3d", "analytic", "lumped"):
            ax.plot(g, [100 * (r["models"][m][1] / r["series"][1] - 1) for r in rows], "o-", color=COL[m], label=m + " (footprint mean)")
        ax.plot(g, [100 * (r["models"]["lumped"][0] / r["series"][0] - 1) for r in rows], "o--", color=COL["lumped"], alpha=0.5, label="lumped (hottest point)")
        ax.axhline(0, color="k", lw=0.6)
        ax.set_xlabel("gap between the source and the edge / corner, mm")
        ax.set_title(title, fontsize=9)
    axs[0].set_ylabel("Rc of the model against the exact thin plate, %")
    axs[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig_10_near_edge_sweeps.png", dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Draw the data figures.
    @return None.
    """
    FIG.mkdir(exist_ok=True)
    for f in (fig05, fig06, fig07, fig08, fig09, fig10):
        f()


if __name__ == "__main__":
    main()
