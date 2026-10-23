"""!
@file make_figures.py
@brief Pictures of the model comparison, written to figures/ (committed, linked from the README files).

@details The numbers come from running the studies of this folder and reading the tables they print.
         fig_01: error of the four other models against the FVM on 19 scenarios; fig_02: the example board against the grid spacing for the FVM, both FDM samplings and the 3D solid;
         fig_03: the solvers (direct, CG, SOR with a residual rule and with the original step rule) on several boards.
Usage: python research/models-comparison/scripts/make_figures.py   (from the repository root; about 2 minutes)
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


def run(script):
    """!
    @brief Run one study of this folder and return what it prints.
    @param script File name of the study.
    @return str Standard output.
    """
    return subprocess.run([sys.executable, str(HERE / script)], capture_output=True, text=True, check=True).stdout


def table(text, start):
    """!
    @brief The header and the rows of the Markdown table whose header line starts with `start`.
    @param text Output of a study.
    @param start Beginning of the header line.
    @return tuple (list of str, list of list of str).
    """
    lines = text.splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.startswith(start))
    head = [c.strip() for c in lines[i].strip("|").split("|")]
    rows = []
    j = i + 2
    while j < len(lines) and lines[j].startswith("|"):
        rows.append([c.strip() for c in lines[j].strip("|").split("|")])
        j += 1
    return head, rows


def pct(cell):
    """!
    @brief The percentage in parentheses of a cell such as "90.27 (+0.2 %)".
    @param cell Table cell.
    @return float The number.
    """
    return float(re.search(r"\(([+-]?\d+\.\d) %\)", cell).group(1))


def fig_scenarios(text):
    """!
    @brief Error of FDM, 3D solid, Lumped and Analytic against the FVM on every scenario.
    @param text Output of validation_study.py.
    @return None.
    """
    head, rows = table(text, "| Scenario")
    names = [r[0] for r in rows]
    fig, ax = plt.subplots(figsize=(13, 6))
    y = np.arange(len(rows))
    for k, (name, col, mk) in enumerate((("FDM", "#6b7280", "o"), ("3D solid", "#059669", "s"), ("Lumped", "#d97706", "^"), ("Analytic", "#1d4ed8", "D"))):
        ax.plot([pct(r[2 + k]) for r in rows], y, mk, color=col, label=name, ms=6)
    ax.set_yticks(y); ax.set_yticklabels(names, fontsize=8); ax.invert_yaxis()
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Error of the temperature rise against the FVM (%)")
    ax.set_title("19 scenarios, 1 mm cells: the models stay within a few percent except where the copper edge crosses the heater (warned)", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "fig_01_models_against_the_fvm.png", dpi=110)
    plt.close(fig)


def fig_grid(text):
    """!
    @brief Maximum temperature of the example board against the grid spacing.
    @param text Output of validation_study.py.
    @return None.
    """
    head, rows = table(text, "| Spacing")
    sp = [float(r[0]) for r in rows]
    fig, ax = plt.subplots(figsize=(7, 4.4))
    for k, (name, col) in enumerate((("FVM", "#1f2937"), ("FDM (area sampling)", "#6b7280"), ("FDM (point sampling, classic)", "#d97706"), ("3D solid", "#059669"))):
        v = [(float(r[1 + k]) if r[1 + k] != "-" else np.nan) for r in rows]
        ax.plot(sp, v, "o-", color=col, label=name)
    ax.set_xscale("log", base=2); ax.invert_xaxis()
    ax.set_xticks(sp); ax.set_xticklabels([f"{s:g}" for s in sp])
    ax.set_xlabel("Grid spacing (mm)"); ax.set_ylabel("Tmax of the example board (°C)")
    ax.set_title("The FVM converges monotonically; the FDM jumps by about ±0.5 °C with the grid", fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_grid_convergence_of_the_models.png", dpi=110)
    plt.close(fig)


def fig_solvers():
    """!
    @brief Difference to the direct solver for CG and the two SOR stopping rules, on every board.
    @return None.
    """
    head, rows = table(run("solver_equivalence.py"), "| Board")
    boards = list(dict.fromkeys(r[0] for r in rows))
    solvers = [("cg (Jacobi)", "CG", "#6b7280"), ("SOR, residual", "SOR, residual 1e-9", "#059669"), ("SOR, step", "SOR, step 0.01 K (original rule)", "#b91c1c")]
    x = np.arange(len(boards))
    fig, ax = plt.subplots(figsize=(11, 4.6))
    for k, (key, lab, col) in enumerate(solvers):
        v = []
        for b in boards:
            r = next(rr for rr in rows if rr[0] == b and rr[1].startswith(key))
            v.append(max(float(r[3]), 1e-13))
        ax.bar(x + (k - 1) * 0.27, v, 0.27, color=col, label=lab)
    ax.set_yscale("log")
    ax.set_xticks(x); ax.set_xticklabels([b.replace(", ", ",\n", 1) for b in boards], fontsize=7)
    ax.set_ylabel("Max abs difference to the direct solver (K)")
    ax.set_title("Same answer with a residual stopping rule (1e-9 K or better); wrong by 2.7 to 16 K with the original step rule", fontsize=9)
    ax.legend(fontsize=8, loc="center left")
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_solver_equivalence.png", dpi=110)
    plt.close(fig)


def main():
    """!
    @brief Make the three figures.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    text = run("validation_study.py")
    fig_scenarios(text)
    fig_grid(text)
    fig_solvers()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
