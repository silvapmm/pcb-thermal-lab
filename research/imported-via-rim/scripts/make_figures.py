#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the imported-via-rim investigation, drawn from the outputs of the studies (run them first): the synthetic boards against the 3D reference and the real-board shifts.
@details Reads `out/synthetic_2L.json`, `out/synthetic_4L.json` (from `study_synthetic.py 2 1.0,0.5 0.5` and `study_synthetic.py 4 1.0,0.5 0.5`) and `out/real_<board>.json` (from
         `run_real_all.sh`; third-party boards of the local library, numbers only, no render). Writes `figures/fig_02_synthetic_against_reference.png` and
         `figures/fig_03_real_board_shift.png`. Run from the repository root: `.venv/bin/python research/imported-via-rim/scripts/make_figures.py`.
"""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                             # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")
FIG = os.path.join(HERE, "figures")
BOARDS = ["cmm2", "isastm", "oswlight", "rp2040", "co60"]


def synthetic():
    """!
    @brief Error of the hottest rise against the 3D reference, today and with the ray rule, every synthetic case, cells 1 and 0.5 mm.
    @return None.
    """
    labels, today, ray = [], [], []
    for n in (2, 4):
        d = json.load(open(os.path.join(OUT, f"synthetic_{n}L.json")))
        for case, row in d.items():
            for cell in ("1.0", "0.5"):
                r = row[cell]
                key = [k for k in r if k.startswith("ray")][0]
                labels.append(f"{n}L {case}\n{cell} mm")
                today.append(100 * (r["today"] / row["truth_max"] - 1))
                ray.append(100 * (r[key] / row["truth_max"] - 1))
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    x = range(len(labels))
    ax.bar([i - 0.2 for i in x], today, 0.4, label="today (full contact)", color="#d62728")
    ax.bar([i + 0.2 for i in x], ray, 0.4, label="ray rule, reach 0.5 mm", color="#1f77b4")
    ax.axhline(0, color="k", linewidth=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=6.5)
    ax.set_ylabel("hottest rise against the 3D reference (%)")
    ax.set_title("Synthetic 10 mm board, 4 x 4 vias under a 1 W part: below zero = too cool (unsafe)", fontsize=9)
    ax.legend(fontsize=7)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_02_synthetic_against_reference.png"), dpi=105)
    plt.close(fig)


def real():
    """!
    @brief Shift of the hottest rise of three parts per board, ray rule against today, cells 1 and 0.5 mm.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    for j, (cell, color) in enumerate((("1.0", "#d62728"), ("0.5", "#1f77b4"))):
        for i, b in enumerate(BOARDS):
            path = os.path.join(OUT, f"real_{b}.json")
            if not os.path.exists(path):
                continue
            runs = [r for r in json.load(open(path))["runs"] if f"{r['cell']:.1f}" == cell]
            ys = [100 * (r["fvm"]["mask rim"] / r["fvm"]["today"] - 1) for r in runs]
            ax.plot([i + (j - 0.5) * 0.2] * len(ys), ys, "o", color=color, label=f"cell {cell} mm" if i == 0 else None)
    ax.set_xticks(range(len(BOARDS)))
    ax.set_xticklabels(BOARDS)
    ax.set_ylabel("ray rule - today (% of the rise)")
    ax.set_title("Real imported boards, FVM, 1 W in one part: today reads cooler (unsafe side)", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_03_real_board_shift.png"), dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    synthetic()
    real()
