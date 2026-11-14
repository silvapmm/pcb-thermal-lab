#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures 3 and 4 from the cache of `study_transient_boards.py`: the error of every model's step response against the finite-element reference in time (3), and the error of
       the time to 63 % and of the wave peak and swing by model and cell (4). Run with the program's interpreter from the repository root after the study scripts:
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


if __name__ == "__main__":
    main()
