#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures 3 and 4 from the cache of `study_transient_boards.py`: the error of every model's step response against the finite-element reference in time (3), and the error of
       the time to 63 % and of the wave peak and swing by model and cell (4); figure 5 from the cache of `study_review_checks.py` (the checks of the review). Run with the program's interpreter from the repository root after the study scripts:
       `.venv/bin/python research/transient-reference-boards/scripts/make_figures.py`.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import matplotlib                                                        # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                          # noqa: E402
import numpy as np                                                       # noqa: E402
import refboards as R                                                    # noqa: E402

FIG = os.path.join(HERE, "..", "figures")
COL = {"fvm": "C0", "fdm": "C1", "lumped": "C2", "analytic": "C3"}


def main():
    """!
    @brief Draw figures 3 and 4.
    @return None.
    """
    res = json.load(open(os.path.join(HERE, "..", "out", "boards.json")))
    rows = json.load(open(os.path.join(HERE, "..", "out", "rows.json")))
    fig, axs = plt.subplots(1, 5, figsize=(18, 3.6), sharey=True)
    for ax, name in zip(axs, R.BOARDS):
        fe = max((v for k, v in res.items() if k.startswith(f"fem|{name}|")), key=lambda v: v["n"])
        t = np.geomspace(0.1, 0.9 * R.T_END[name], 200)
        zr = np.interp(np.log(t), np.log(fe["t"][1:]), fe["hot"][1:])
        for model in COL:
            v = res.get(f"prog|{name}|{model}|0.5")
            if v is None or "error" in v:
                continue
            zm = np.interp(np.log(t), np.log(v["t"]), v["z"])
            ax.semilogx(t, 100 * (zm / zr - 1), color=COL[model], label=model)
        v = res.get(f"prog|{name}|fvm|2.0")
        ax.semilogx(t, 100 * (np.interp(np.log(t), np.log(v["t"]), v["z"]) / zr - 1), color="C0", ls=":", label="fvm 2 mm")
        ax.axhline(0, color="k", lw=.5)
        ax.set_title(name, fontsize=9)
        ax.set_xlabel("t (s)")
        ax.set_ylim(-40, 12)
    axs[0].set_ylabel("model / FEM - 1 (%), hottest point")
    axs[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_03_step_errors.png"), dpi=130)
    fig, axs = plt.subplots(1, 3, figsize=(15, 3.8))
    keys = [("t63_hot", "time to 63 % (%)"), ("peak", "wave peak (%)"), ("swing", "wave swing (%)")]
    w = 0.2
    for ax, (key, title) in zip(axs, keys):
        for i, model in enumerate(COL):
            xs, ys = [], []
            for j, name in enumerate(R.BOARDS):
                r = rows.get(f"{name}|{model}|0.5")
                if r is not None:
                    xs.append(j + (i - 1.5) * w)
                    ys.append(r[key])
            ax.bar(xs, ys, w, color=COL[model], label=model)
        ax.set_xticks(range(len(R.BOARDS)))
        ax.set_xticklabels(R.BOARDS, fontsize=8)
        ax.axhline(0, color="k", lw=.5)
        ax.set_title(title + ", cell 0.5 mm", fontsize=9)
    axs[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_04_t63_wave_errors.png"), dpi=130)
    review(res)


def review(res):
    """!
    @brief Figure 5: (a) `two2`, the finite-element copper node and the mean of the column copper plus half gap against the program's node; (b) `vias`, the Analytic read at its own
           point and at the hottest cell of its steady solve against the finite elements and the FVM; (c) the plan of `vias` with the two points.
    @param res Cache of the study.
    @return None (nothing drawn when the review cache is absent).
    """
    path = os.path.join(HERE, "..", "out", "review.json")
    if not os.path.exists(path):
        return
    rv = json.load(open(path))
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.2), gridspec_kw={"width_ratios": [1.2, 1.2, 0.8]})
    ax = axs[0]
    sl = rv["slab|two2|0.5"]
    ax.semilogx(sl["t"], sl["hot"], "k-", label="FEM, copper under the part (the study's quantity)")
    ax.semilogx(sl["t"], sl["slab"], "k--", label="FEM, mean of copper + half gap under it")
    v = res["prog|two2|fvm|0.5"]
    ax.semilogx(v["t"], v["z"], color="C0", label="program FVM 0.5 mm, layer node")
    ax.set_xlim(0.05, 300)
    ax.set_ylim(0, 35)
    ax.set_xlabel("t (s)")
    ax.set_ylabel("rise (K/W)")
    ax.set_title("(a) two2: what one node per layer holds", fontsize=9)
    ax.legend(fontsize=7)
    ax = axs[1]
    fe = max((w for k, w in res.items() if k.startswith("fem|vias|")), key=lambda w: w["n"])
    t = np.geomspace(0.1, 300, 200)
    zr = np.interp(np.log(t), np.log(fe["t"][1:]), fe["hot"][1:])
    fv = res["prog|vias|fvm|0.5"]
    ax.semilogx(t, 100 * (np.interp(np.log(t), np.log(fv["t"]), fv["z"]) / zr - 1), color="C0", label="FVM 0.5 mm")
    for key, ls, lab in (("asis", "-", "Analytic, its own point (as is)"), ("fixed", "--", "Analytic, hottest cell of its steady solve (copy)")):
        a = rv["analytic"][f"vias|0.5|{key}"]
        ax.semilogx(t, 100 * (np.interp(np.log(t), np.log(a["t"]), a["z"]) / zr - 1), color="C3", ls=ls, label=lab)
    ax.axhline(0, color="k", lw=.5)
    ax.set_xlabel("t (s)")
    ax.set_ylabel("model / FEM - 1 (%)")
    ax.set_title("(b) vias: the Analytic read at two points", fontsize=9)
    ax.legend(fontsize=7)
    ax = axs[2]
    info = rv["analytic"]["info"]
    ax.add_patch(plt.Rectangle((7, 7), 6, 6, fill=False, color="r", lw=1.5))
    for x in (8.8, 9.6, 10.4, 11.2):
        for y in (8.8, 9.6, 10.4, 11.2):
            ax.add_patch(plt.Circle((x, y), 0.15, color="0.4"))
    ax.plot(*info["own_point_mm"], "C3o", label="own point of the Analytic transient (hottest without the vias)")
    ax.plot(*info["steady_hottest_mm"], "C3s", mfc="none", ms=9, label="hottest cell of its steady solve (with the vias)")
    ax.set_xlim(5, 15)
    ax.set_ylim(5, 15)
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_title("(c) vias: part (red), 4 x 4 vias, the two points", fontsize=9)
    ax.legend(fontsize=6, loc="lower center")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_05_review_checks.png"), dpi=130)


if __name__ == "__main__":
    main()
