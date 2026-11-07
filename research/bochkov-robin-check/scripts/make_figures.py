#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures of the data: convergence of the schemes on the triangle and the disc (fig 01) and the stiff-edge behaviour (fig 02).
@details Needs `out/convergence.json` from `study_triangle_disc.py`; the stiff sweep is recomputed here (about a minute).
         Run from the repository root: `.venv/bin/python research/bochkov-robin-check/scripts/make_figures.py`.
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
import robin2d as R  # noqa: E402

FIG = os.path.join(HERE, "..", "figures")
COL = {"nofilm": "#888888", "bg_nokink": "#c07000", "bg": "#1f5fa8", "film": "#2a9d4a"}


def fig_convergence():
    """!
    @brief Figure 01: error against h on the triangle and the disc (solution and gradient).
    @return None
    """
    with open(os.path.join(HERE, "..", "out", "convergence.json")) as fh:
        res = json.load(fh)
    fig, ax = plt.subplots(2, 2, figsize=(9, 7))
    for r, name in enumerate(("triangle", "disc")):
        for c, (col, lab) in enumerate(((2, "solution"), (3, "gradient"))):
            a = ax[r, c]
            for sch, rows in res[name].items():
                h = [x[1] for x in rows]
                a.loglog(h, [x[col] for x in rows], "o-", color=COL[sch], label=sch, ms=4)
            h = np.array([x[1] for x in res[name]["bg"]])
            for p, ls in ((1, ":"), (2, "--")):
                a.loglog(h, 0.6 * (h / h[0]) ** p * res[name]["bg"][0][col] / 1.0, "k" + ls, lw=0.7, label=f"order {p}")
            a.set_title(f"{name}: L-inf error of the {lab}")
            a.set_xlabel("h")
            a.grid(True, which="both", alpha=0.3)
    ax[0, 0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_01_convergence.png"), dpi=130)
    plt.close(fig)


def fig_stiff():
    """!
    @brief Figure 02: error of the schemes on the disc against the cell Biot number alpha h / mu.
    @return None
    """
    cfgs = [("nofilm", dict(scheme="nofilm")), ("eq. 1.14 (no floor)", dict(scheme="bg")), ("film, floor 0.25", dict(scheme="film", floor=0.25))]
    sh = [(-0.5 + (a + 0.5) / 3, -0.5 + (b + 0.5) / 3) for a in range(3) for b in range(3)]
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    cols = ["#888888", "#1f5fa8", "#2a9d4a"]
    for (name, kw), col in zip(cfgs, cols):
        xs, ys = [], []
        for s in (0.3, 1, 3, 10, 30, 100, 1e3, 1e4):
            dom = R.disc_domain(s)
            for n in (33,):
                h = 2.0 / (n - 1)
                xs.append(s * 3 * h)
                ys.append(max(R.errors(dom, R.solve(dom, n, shift=x, **kw))[0] for x in sh))
        ax.loglog(xs, ys, "o-", color=col, label=name)
    ax.axvline(1.0, color="k", ls=":", lw=0.8)
    ax.set_xlabel("alpha_max h / mu (cell Biot number), n = 33")
    ax.set_ylabel("L-inf error of the solution")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_02_stiff_edge.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_convergence()
    fig_stiff()
