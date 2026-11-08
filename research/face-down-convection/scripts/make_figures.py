#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures of the face-down study from the outputs of study_down_laws.py and study_down_board_effect.py.
@details Writes figures/fig_02_down_laws_over_ra.png and figures/fig_03_effect_on_the_hottest_rise.png. Run the two studies first.
Usage: .venv/bin/python research/face-down-convection/scripts/make_figures.py
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(BASE, "figures")
OUT = os.path.join(BASE, "out")


def main():
    """!
    @brief Draw figures 2 and 3.
    @return None.
    """
    d = json.load(open(os.path.join(OUT, "down_laws.json")))
    ra = np.array(d["ra"])
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ref = np.array(d["nu"]["program 0.27 Ra^1/4"])
    for n, v in d["nu"].items():
        if n.startswith("Rohsenow"):
            continue                                         # second-hand form not checked: left out of the picture
        ax.semilogx(ra, np.array(v) / ref, marker="o", ms=3, lw=2.5 if n.startswith("Incropera") else 1.2, label=n)
    ax.axvspan(5e2, 5e5, color="grey", alpha=0.12, label="Ra of 40-200 mm boards")
    ax.axhline(1, color="k", lw=0.8)
    ax.set_xlabel("Ra on L = A/P")
    ax.set_ylabel("Nu of the law / Nu of the program (0.27 Ra^1/4)")
    ax.set_title("Face turned down: published laws against the program")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_02_down_laws_over_ra.png"), dpi=130)
    e = json.load(open(os.path.join(OUT, "down_board_effect.json")))
    names = [r["board"] for r in e["boards"]]
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for k, (lv, lab) in enumerate((("incropera", "0.52 Ra^1/5"), ("gl_mean", "0.475 Ra^1/5"), ("vdi", "VDI"))):
        y = [100 * (r[f"rad|{lv}"]["rise"] / r["rad|program"]["rise"] - 1) for r in e["boards"]]
        ax.bar(x + (k - 1) * 0.27, y, 0.27, label=lab)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=70, ha="right", fontsize=7)
    ax.set_ylabel("change of the hottest rise (%)")
    ax.set_title("17 harness boards, computed h, FVM 2 mm, horizontal: rise with the 1/5 law against the program")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_03_effect_on_the_hottest_rise.png"), dpi=130)


if __name__ == "__main__":
    main()
