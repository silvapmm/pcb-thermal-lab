"""!
@file make_figures.py
@brief Pictures of the metal-block and fin studies, written to figures/ (committed, linked from the README files).

@details The numbers come from running the two studies of this folder and reading what they print.
         fig_01: the fin formula of the program against a 2D solution of one fin (24 cases); fig_02: error of the Lumped and Analytic models on the 74 block cases for the three
         approaches (mean and maximum); fig_03: the error of every case, earlier equivalent coefficient (Lumped) against the implemented block models (Lumped and Analytic).
Usage: python research/block-and-fins/scripts/make_figures.py   (from the repository root; about 20 seconds)
"""

import re
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "figures"          # kept in the repository on purpose: the README files link to them
METALS = {"aluminium": "#1d4ed8", "copper": "#b45309", "carbon steel": "#6b7280", "stainless": "#059669"}


def run(script):
    """!
    @brief Run one study of this folder and return what it prints.
    @param script File name of the study.
    @return str Standard output.
    """
    return subprocess.run([sys.executable, str(HERE / script)], capture_output=True, text=True, check=True).stdout


def fig_fins():
    """!
    @brief The formula of the fin ratio against the 2D solution, per metal, and the difference against the efficiency.
    @return None.
    """
    rows = []
    for ln in run("fin_validation.py").splitlines():
        c = [x.strip() for x in ln.strip("|").split("|")]
        if len(c) == 8 and c[0] in METALS:
            rows.append((c[0], float(c[4]), float(c[5]), float(c[6]), float(c[7].replace("%", ""))))
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.3))
    for m, col in METALS.items():
        r = [x for x in rows if x[0] == m]
        axs[0].plot([x[2] for x in r], [x[3] for x in r], "o", color=col, label=m)
        axs[1].plot([x[1] for x in r], [x[4] for x in r], "o", color=col, label=m)
    lim = [0.2, 6]
    axs[0].plot(lim, lim, "k--", lw=0.8)
    axs[0].set_xscale("log"); axs[0].set_yscale("log")
    for a in axs[0].xaxis, axs[0].yaxis:
        a.set_minor_formatter(plt.NullFormatter())
    axs[0].set_xlabel("2D solution of one fin (W/m/K)"); axs[0].set_ylabel("Formula of the program (W/m/K)")
    axs[0].set_title("Fin heat flow: formula against 2D (dashed: equal)", fontsize=10)
    axs[1].axhline(0, color="black", lw=0.8)
    axs[1].set_xlabel("Fin efficiency"); axs[1].set_ylabel("Difference (%)")
    axs[1].set_title(f"{len(rows)} cases, all within {max(abs(x[4]) for x in rows):.2f} %", fontsize=10)
    axs[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_01_fin_formula_against_2d.png", dpi=110)
    plt.close(fig)


def fig_blocks():
    """!
    @brief Summary and per-case errors of the block approaches in the Lumped and Analytic models.
    @return None.
    """
    text = run("block_equivalent_study.py")
    summ = {}
    for ln in text.splitlines():
        m = re.match(r"\s+(old|A|B|C) (Lumped|Analytic)\s+([\d.]+)\s+([\d.]+)", ln)
        if m:
            summ[(m.group(1), m.group(2))] = (float(m.group(3)), float(m.group(4)))
    cases = []
    for ln in text.splitlines():
        c = [x.strip() for x in ln.strip("|").split("|")]
        if len(c) == 6 and "/" in c[2] and re.match(r"[+-]?\d", c[2]):
            cases.append((c[0], float(c[2].split("/")[0]), float(c[2].split("/")[1]), float(c[5 - 1]), float(c[5])))
    fig, ax = plt.subplots(figsize=(8, 4.3))
    groups = (("earlier\nequivalent coefficient", "old"), ("coefficient on the contact\narea + annular fin", "A"), ("implemented\nblock model", None))
    x = np.arange(3)
    for k, (model, col) in enumerate((("Lumped", "#d97706"), ("Analytic", "#1d4ed8"))):
        mean = [summ[("old", model)][0], summ[("A", model)][0], summ[("B" if model == "Lumped" else "C", model)][0]]
        mx = [summ[("old", model)][1], summ[("A", model)][1], summ[("B" if model == "Lumped" else "C", model)][1]]
        ax.bar(x + (k - 0.5) * 0.36, mean, 0.34, color=col, label=f"{model} mean")
        ax.plot(x + (k - 0.5) * 0.36, mx, "k_", ms=18, mew=2)
    ax.set_xticks(x); ax.set_xticklabels([g[0] for g in groups], fontsize=8)
    ax.set_ylabel("Absolute error of Tmax (% of the FVM rise)")
    ax.set_title(f"Metal block in the Lumped and Analytic models, {len(cases)} cases (bar: mean, tick: maximum)", fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_block_approaches.png", dpi=110)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(12, 4))
    xs = np.arange(len(cases))
    ax.plot(xs, [c[1] for c in cases], "o", color="#9ca3af", label="Lumped, earlier equivalent coefficient")
    ax.plot(xs, [c[3] for c in cases], "o", color="#d97706", label="Lumped, block as a ring layer")
    ax.plot(xs, [c[4] for c in cases], "s", ms=4, color="#1d4ed8", label="Analytic, block as a tile graph")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("Case (block and pad geometry, thickness, metal, interface, fins)")
    ax.set_ylabel("Error of Tmax (%)")
    ax.set_title("Every case: the coefficient is hot (+), the block models stay within a few percent", fontsize=10)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_block_error_per_case.png", dpi=110)
    plt.close(fig)


def main():
    """!
    @brief Make the figures.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_fins()
    fig_blocks()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
