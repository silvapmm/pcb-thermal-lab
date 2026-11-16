#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures of the case 2 investigation: the section of the plate with the through-thickness profile (fig_01), the error against h (fig_02) and the decomposition of the gap (fig_03).
@details Needs out/h_sweep.json (study_case2_h_sweep.py) and out/reproduce.json (study_case2_reproduce.py); fig_01 recomputes the column of the independent 3D solver.
         Run from the repository root: .venv/bin/python research/muzychka-case2-analytic/scripts/make_figures.py
"""

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import case2 as C  # noqa: E402
import layered3d as L  # noqa: E402

FIG = os.path.join(HERE, "..", "figures")
OUT = os.path.join(HERE, "..", "out")
COL = {"fvm": "#1f77b4", "fdm": "#2ca02c", "analytic": "#d62728", "lumped": "#9467bd", "solid3d": "#ff7f0e"}


def fig_section():
    """!
    @brief Fig 01: plan and section of the plate, and the temperature through the thickness under the 25 W source.
    @return None.
    """
    dx, n, ns = 0.5e-3, 100, 16
    rects = [tuple(v * 1e-3 for v in C.rect(c)) for c in C.CENTRES]
    res = L.solve(dx, n, n, [(C.T_MM * 1e-3, C.K_PLATE, ns)], rects, C.POWERS, 0.0, C.H_PAPER)
    T = res["T"] + C.AMB
    dz = np.array(res["dz"]) * 1e3
    zc = np.cumsum(dz) - dz / 2                                            # depth of the slab centres from the top face, mm
    j, i = int(round(12.5 / 0.5)), int(round(37.5 / 0.5))                  # centroid of source 2 (25 W) at (37.5, 12.5)
    col = T[:, j - 1:j + 1, i - 1:i + 1].mean(axis=(1, 2))
    top = C.AMB + float(res["surface_top"][j - 1:j + 1, i - 1:i + 1].mean())
    mean = float(np.average(col, weights=dz))
    fig, ax = plt.subplots(1, 3, figsize=(14, 4.2), gridspec_kw={"width_ratios": [1, 1.5, 1.1]})
    a = ax[0]
    a.set_aspect("equal")
    a.add_patch(plt.Rectangle((0, 0), 50, 50, fill=False, lw=1.5))
    for c, p in zip(C.CENTRES, C.POWERS):
        x0, y0, x1, y1 = C.rect(c)
        a.add_patch(plt.Rectangle((x0, y0), 10, 10, color="#d62728", alpha=0.55))
        a.text(c[0], c[1], f"{p:g} W", ha="center", va="center", color="white", fontsize=9)
    a.axhline(12.5, color="k", ls="--", lw=0.8)
    a.set_xlim(-2, 52), a.set_ylim(-2, 52)
    a.set_title("plan: 50 x 50 mm, four 10 x 10 mm sources\n(dashed: the section)", fontsize=9)
    a.set_xlabel("x, mm"), a.set_ylabel("y, mm")
    a = ax[1]
    a.set_aspect("equal")
    a.add_patch(plt.Rectangle((0, 0), 50, 10, color="#c8c8d0"))
    for c, p in zip(C.CENTRES[:2], C.POWERS[:2]):
        a.add_patch(plt.Rectangle((c[0] - 5, 10), 10, 1.2, color="#d62728"))
        for xo in np.linspace(-3.5, 3.5, 4):
            a.annotate("", xy=(c[0] + xo, 8.0), xytext=(c[0] + xo, 11.6), arrowprops=dict(arrowstyle="->", color="#d62728", lw=0.9))
        a.text(c[0], 12.0, f"{p:g} W", ha="center", fontsize=8, color="#d62728")
    for x in np.linspace(2, 48, 12):
        a.annotate("", xy=(x, -3.0), xytext=(x, 0), arrowprops=dict(arrowstyle="->", color="#1f77b4", lw=0.9))
    a.text(25, -4.6, "bottom: h = 400 W/m2K (top and sides adiabatic)", ha="center", fontsize=8, color="#1f77b4")
    a.axhline(5.0, color="k", lw=1.2, ls=":")
    a.text(25, 5.3, "one node per layer: at mid-thickness, the mean of the column", ha="center", fontsize=8)
    a.set_xlim(-2, 52), a.set_ylim(-6, 14)
    a.set_title("section y = 12.5 mm: plate 10 mm, k 150 W/mK; heat spreads down and sideways", fontsize=9)
    a.set_xlabel("x, mm")
    a = ax[2]
    a.plot(col, zc, "o-", color="#444", label="3D solver, column under the 25 W centroid")
    a.plot([top], [0], "s", color="#d62728", ms=8, label=f"surface {top:.2f} C (the paper: 103.82)")
    a.axvline(mean, color="#2ca02c", ls="--", label=f"layer mean {mean:.2f} C (3D solid, one node)")
    fvm = json.load(open(os.path.join(OUT, "reproduce.json")))["models"]["fvm_0.5"]["cen"][1]
    a.axvline(fvm, color="#1f77b4", ls="--", label=f"FVM / FDM / Analytic {fvm:.2f} C")
    a.invert_yaxis()
    a.set_xlabel("temperature, C"), a.set_ylabel("depth below the top face, mm")
    a.legend(fontsize=7, loc="lower right")
    a.set_title("through the thickness", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_01_case2_section.png"), dpi=140)
    plt.close(fig)


def fig_h():
    """!
    @brief Fig 02: error of every model against h, in K and in % of the rise, against the 3D surface.
    @return None.
    """
    d = json.load(open(os.path.join(OUT, "h_sweep.json")))
    hs = sorted(float(h) for h in d)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for m in COL:
        k = [d[str(h)]["models"][m]["e_surf"][1] for h in hs]
        r = [d[str(h)]["models"][m]["e_surf_pct"][1] for h in hs]
        ax[0].semilogx(hs, k, "o-", color=COL[m], label=m)
        ax[1].semilogx(hs, r, "o-", color=COL[m], label=m)
    for a, t in ((ax[0], "error in K (source 2, 25 W)"), (ax[1], "error in % of the rise")):
        a.axvline(400, color="grey", lw=0.8, ls=":")
        a.set_xlabel("bottom coefficient h, W/m2K"), a.set_title(t, fontsize=9)
        a.grid(alpha=0.3)
    ax[0].legend(fontsize=8, loc="center left")
    fig.suptitle("Case 2: model centroid minus the 3D surface centroid. The error in K does not depend on h; in % it grows with h (the rise falls)", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_02_case2_error_vs_h.png"), dpi=140)
    plt.close(fig)


def fig_decomp():
    """!
    @brief Fig 03: the gap between the paper and the FVM split into the through-thickness term and the film term, with the bound q'' t / (2k).
    @return None.
    """
    r = json.load(open(os.path.join(OUT, "reproduce.json")))["decomp"]
    x = np.arange(4)
    fig, a = plt.subplots(figsize=(6.5, 4))
    a.bar(x, r["through"], color="#d62728", label="surface minus layer mean (spreading-dependent)")
    a.bar(x, r["film"], bottom=r["through"], color="#1f77b4", label="layer mean minus the program (t/(2k) of the film)")
    a.plot(x, r["bound"], "k_", ms=22, mew=2, label="bound q'' t / (2 k) of the warning")
    a.set_xticks(x, [f"S{i + 1}\n{p:g} W" for i, p in enumerate(C.POWERS)])
    a.set_ylabel("K"), a.legend(fontsize=7), a.set_title("Case 2: where the 2.9 to 5.6 K come from (FVM, 0.5 mm)", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_03_case2_decomposition.png"), dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_section()
    fig_h()
    fig_decomp()
