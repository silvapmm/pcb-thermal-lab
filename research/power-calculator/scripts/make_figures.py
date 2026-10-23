"""!
@file make_figures.py
@brief Pictures of the power calculator studies, written to figures/ (committed, linked from the README files).

@details The numbers come from running the studies of this folder and reading the tables they print.
         fig_01: the calculator against datasheet RθJA values; fig_02: error of the recovered power when the drawn board is not the real one; fig_03: the ways to reduce that error
         (known-power reference, two points) with a perfect and with a ±1 K reading.
Usage: python research/power-calculator/scripts/make_figures.py   (from the repository root; about 3 minutes)
"""

import re
import subprocess
import textwrap
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


def pct(cell):
    """!
    @brief First percentage in a table cell.
    @param cell Text such as "-22.9 %" or "+0.0 % (copper x2.00)".
    @return float The number.
    """
    return float(re.search(r"([+-]?\d+\.\d)\s*%", cell).group(1))


def rows(text, start):
    """!
    @brief Rows of the first Markdown table that follows a line starting with `start` (or the first table when start is empty).
    @param text Output of a study.
    @param start Beginning of the line before the table.
    @return list of lists of str.
    """
    lines = text.splitlines()
    i = next((k for k, ln in enumerate(lines) if ln.startswith(start)), 0) if start else 0
    i = next(k for k in range(i, len(lines)) if lines[k].startswith("| :--") or lines[k].startswith("| --")) + 1
    out = []
    while i < len(lines) and lines[i].startswith("|"):
        out.append([c.strip() for c in lines[i].strip("|").split("|")])
        i += 1
    return out


def fig_datasheets():
    """!
    @brief Error of the calculator on the datasheet boards.
    @return None.
    """
    r = rows(run("calculator_validation.py"), "")
    names = [x[0].split(",")[0][:30] + "\n" + (x[0].split(",", 1)[1][:34] if "," in x[0] else "") for x in r]
    err = [pct(x[4]) for x in r]
    fig, ax = plt.subplots(figsize=(10, 4.3))
    ax.bar(range(len(r)), err, color=["#b45309" if abs(e) > 10 else "#1d4ed8" for e in err])
    for k, e in enumerate(err):
        ax.text(k, e + (0.8 if e >= 0 else -2.2), f"{e:+.1f} %", ha="center", fontsize=9)
    ax.set_ylim(-6, 31)
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(range(len(r))); ax.set_xticklabels(names, fontsize=7)
    ax.set_ylabel("Error of the power returned for 1 W (%)")
    ax.set_title("Datasheet boards: within 2 to 3 %; a datasheet maximum (orange) is not a target", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_01_calculator_vs_datasheets.png", dpi=110)
    plt.close(fig)


def fig_board_errors():
    """!
    @brief Error of the recovered power for every way the drawn board can differ from the real one.
    @return None.
    """
    r = rows(run("power_from_top_study.py"), "| What is different")
    names = [x[0] for x in r]
    err = [pct(x[2]) for x in r]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    cols = ["#7c2d12" if "shortcut" in n else "#d97706" if ("copper" in n or "planes" in n or "vias" in n) else "#6b7280" for n in names]
    ax.barh(range(len(r)), err, color=cols)
    ax.set_yticks(range(len(r))); ax.set_yticklabels([textwrap.shorten(n.replace("datasheet shortcut P = (T_top - T_amb)/(theta_JA - psi_JT)", "datasheet shortcut"), 62) for n in names], fontsize=7); ax.invert_yaxis()
    ax.axvline(0, color="black", lw=0.8)
    for k, e in enumerate(err):
        ax.text(e + (1 if e >= 0 else -1), k, f"{e:+.1f} %", va="center", ha="left" if e >= 0 else "right", fontsize=7)
    ax.set_xlim(-60, 65)
    ax.set_xlabel("Error of the recovered power (%)")
    ax.set_title("Power from the top of the package: copper (orange) and the shortcut (brown) dominate", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_error_when_the_board_differs.png", dpi=110)
    plt.close(fig)


def fig_calibration():
    """!
    @brief Plain calculator, known-power reference and two-point fit, for a wrong copper and for ±1 K readings.
    @return None.
    """
    text = run("calculator_calibration_study.py")
    a = rows(text, "| Drawn board")
    b = rows(text, "| Error on the readings")
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.4))
    x = np.arange(len(a))
    for k, (name, col) in enumerate((("plain calculator", "#6b7280"), ("known-power reference", "#059669"), ("two points", "#d97706"))):
        v = [pct(r[k + 1]) for r in a]
        axs[0].bar(x + (k - 1) * 0.27, v, 0.27, color=col, label=name)
        for xi, vi in zip(x, v):
            axs[0].text(xi + (k - 1) * 0.27, vi - 2.5 if vi < -1 else 1.2, f"{vi:+.1f}", ha="center", fontsize=7)
    axs[0].set_xticks(x); axs[0].set_xticklabels([r[0] for r in a], fontsize=8)
    axs[0].set_ylabel("Error of the recovered power (%)")
    axs[0].set_title("Perfect readings, drawn copper wrong", fontsize=10); axs[0].legend(fontsize=8, loc="lower left")
    axs[0].set_ylim(-48, 6)
    axs[0].axhline(0, color="black", lw=0.8)
    x = np.arange(len(b))
    for k, (name, col) in enumerate((("plain calculator", "#6b7280"), ("known-power reference", "#059669"), ("two points", "#d97706"))):
        axs[1].bar(x + (k - 1) * 0.27, [pct(r[k + 1]) for r in b], 0.27, color=col, label=name)
    axs[1].set_xticks(x); axs[1].set_xticklabels([r[0].replace(", ", ",\n") for r in b], fontsize=7)
    axs[1].set_title("Half the copper, ±1 K on each thermocouple: the two-point fit is badly conditioned", fontsize=9)
    axs[1].axhline(0, color="black", lw=0.8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_ways_to_reduce_the_error.png", dpi=110)
    plt.close(fig)


def main():
    """!
    @brief Make the three figures.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_datasheets()
    fig_board_errors()
    fig_calibration()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
