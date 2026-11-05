#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures_literature.py
@brief Figures of the cut-cell literature check: the reproduction of Johansen and Colella's Problem 1 and the film boundary on a disc in four cut-cell schemes.
@details fig_13: published against reproduced errors of the Poisson problem on the flower (data). fig_14: a cut cell with the four treatments drawn (nodes, the link, the
         film) and the error of the four schemes against the closed form of a round sheet with a Robin film. Numbers come from `lib/jc_poisson.py` and `lib/sheet_robin.py`
         (a few seconds). The numbering continues that of `make_figures.py` (the next free numbers are 13 and 14); this script may be folded into it.
Usage: .venv/bin/python research/rotated-square-3d/scripts/make_figures_literature.py   (from the repository root)
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, HERE)

import jc_poisson as jc                  # noqa: E402
import sheet_robin as sr                 # noqa: E402
from study_cutcell_sources import JC_TABLE   # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "figures")
COL = {"program": "#c0392b", "aperture": "#1f77b4", "aperture+bochkov": "#17becf", "links": "#2ca02c", "links+strip": "#9467bd"}


def fig_jc():
    """!
    @brief Published and reproduced errors of Problem 1 against the number of cells.
    @return None.
    """
    sizes = (40, 80, 160, 320, 640)
    res = [jc.solve(n) for n in sizes]
    fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.8))
    ax[0].loglog(sizes, [JC_TABLE[n]["xi_inf"] for n in sizes], "s", mfc="none", ms=9, color="k", label="published, max error (Table II)")
    ax[0].loglog(sizes, [r["xi_inf"] for r in res], "o-", ms=4, color="#1f77b4", label="reproduced, max error")
    ax[0].loglog(sizes, [JC_TABLE[n]["xi_1"] for n in sizes], "s", mfc="none", ms=9, color="gray", label="published, 1-norm error")
    ax[0].loglog(sizes, [r["xi_1_mean"] for r in res], "o-", ms=4, color="#2ca02c", label="reproduced, 1-norm error")
    ax[0].loglog(sizes, [5.85e-5 * (40.0 / n) ** 2 for n in sizes], ":", color="gray", label="slope -2")
    ax[0].set_xlabel("cells per unit length N")
    ax[0].set_ylabel("solution error")
    ax[0].set_title("Solution error, Problem 1")
    ax[0].legend(fontsize=7)
    ax[1].loglog(sizes, [JC_TABLE[n]["tau_p"] for n in sizes], "s", mfc="none", ms=9, color="k", label="published, cut cells (kappa tau)")
    ax[1].loglog(sizes, [r["tau_partial_inf"] for r in res], "o-", ms=4, color="#c0392b", label="reproduced, cut cells")
    ax[1].loglog(sizes, [JC_TABLE[n]["tau_i"] for n in sizes], "s", mfc="none", ms=9, color="gray", label="published, whole cells (tau)")
    ax[1].loglog(sizes, [r["tau_full_inf"] for r in res], "o-", ms=4, color="#ff7f0e", label="reproduced, whole cells")
    ax[1].set_xlabel("cells per unit length N")
    ax[1].set_title("Truncation error (first order at cut cells)")
    ax[1].legend(fontsize=7)
    fig.suptitle("Johansen and Colella, Problem 1 (flower, Dirichlet): the report's Tables I and II against the independent implementation", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_13_jc_published_vs_reproduced.png"), dpi=105)
    plt.close(fig)


def fig_schemes():
    """!
    @brief The four treatments of a cut cell drawn, and their error on a round sheet with a Robin rim film.
    @return None.
    """
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.2), gridspec_kw={"width_ratios": [1.0, 1.25]})
    a = ax[0]
    # A cut cell (unit square) with a curved outline: the open part is the lower left, the circle centre far to the lower left
    th = np.linspace(0, 2 * np.pi, 400)
    cx, cy, rr = -1.2, -1.6, 2.2
    a.fill_between([0, 1], [0, 0], [1, 1], color="#eeeeee", zorder=0)
    xs, ys = cx + rr * np.cos(th), cy + rr * np.sin(th)
    mask = (xs > -0.2) & (xs < 1.2) & (ys > -0.2) & (ys < 1.2)
    a.plot(xs[mask], ys[mask], color="k", lw=2)
    gx, gy = np.meshgrid(np.linspace(0, 1, 120), np.linspace(0, 1, 120))
    inside = (gx - cx) ** 2 + (gy - cy) ** 2 <= rr ** 2
    a.contourf(gx, gy, inside.astype(float), levels=[0.5, 1.5], colors=["#cfe3f6"], zorder=1)
    a.plot([0, 1, 1, 0, 0], [0, 0, 1, 1, 0], color="gray", lw=1)
    cxn, cyn = gx[inside].mean(), gy[inside].mean()
    a.plot(0.5, 0.5, "o", color=COL["program"], ms=9, label="node of the program and of 'aperture' (cell centre)")
    a.plot(cxn, cyn, "s", color=COL["links"], ms=9, label="node of 'links' (centroid of the open part)")
    # Aperture of the faces
    a.plot([0, 0], [0, 1], color="#1f77b4", lw=4, alpha=0.6)
    a.plot([0, 1], [0, 0], color="#1f77b4", lw=4, alpha=0.6)
    a.annotate("face open\n(aperture a)", xy=(0.0, 0.5), xytext=(-0.55, 0.62), fontsize=7, arrowprops=dict(arrowstyle="->"))
    a.annotate("film on the outline\n(length L in the cell)", xy=(0.8, 0.55), xytext=(0.45, 1.12), fontsize=7, arrowprops=dict(arrowstyle="->"))
    a.annotate("", xy=(0.5, 0.5), xytext=(cxn, cyn), arrowprops=dict(arrowstyle="<->", color="gray"))
    a.text(0.18, 0.36, "centre to\ncentroid", fontsize=6, color="gray")
    a.set_xlim(-0.65, 1.3)
    a.set_ylim(-0.2, 1.35)
    a.set_aspect("equal")
    a.axis("off")
    a.legend(loc="upper left", fontsize=6, bbox_to_anchor=(-0.05, 0.0))
    a.set_title("A cell the outline cuts (blue: the sheet)\nprogram: link = harmonic mean of S x cover over the centre distance;\naperture: a S;  links: a S over the centroid distances;  links+strip: + conduction to the outline", fontsize=7)
    # Error against the cells per radius
    radius, S, G, q, H = 0.01, 0.05, 20.0, 1000.0, 5.0
    t_ref = float(sr.disc_exact(0.0, radius, S, G, H, q))
    b = ax[1]
    ns = (5, 10, 20, 40)
    offs = [(0.0, 0.0), (0.37, 0.21), (0.5, 0.5)]
    for sc in sr.SCHEMES:
        worst = []
        for n_r in ns:
            dx = radius / n_r
            w = 0.0
            for off in offs:
                centre = (off[0] * dx, off[1] * dx)
                shape = sr.Shape(radius, dx, centre=centre)
                try:
                    res = sr.solve(shape, S, G, H, q, sc)
                except ValueError:
                    w = np.nan                                     # the film of Bochkov and Gibou is not defined on this grid
                    continue
                px, py = (shape.cx, shape.cy) if sc == "program" else (res["px"], res["py"])
                ex = sr.disc_exact(np.hypot(px - centre[0], py - centre[1]), radius, S, G, H, q)
                w = max(w, float(np.nanmax(np.where(shape.kap > 1 - 1e-9, np.abs(res["T"] - ex), 0.0))))
            worst.append(100.0 * w / t_ref)
        b.loglog(ns, worst, "o-", color=COL[sc], label=sc)
    b.loglog(ns, [30.0 * (5.0 / n) for n in ns], ":", color="gray", label="slope -1")
    b.loglog(ns, [3.0 * (5.0 / n) ** 2 for n in ns], "--", color="gray", label="slope -2")
    b.set_xlabel("cells per radius")
    b.set_ylabel("worst error in the whole cells (% of the highest rise)")
    b.set_title("Round sheet, Robin film on the rim (H = 5 W/m K), worst of three\nshifts of the sheet against the grid", fontsize=8)
    b.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_14_cut_cell_schemes_film_boundary.png"), dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig_jc()
    fig_schemes()
