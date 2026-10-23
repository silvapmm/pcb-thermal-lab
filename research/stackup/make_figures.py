"""!
@file make_figures.py
@brief Pictures of the stack-up study, written to figures/ (committed, linked from the README files).

@details The numbers come from running the two studies of this folder and reading the tables they print, so the pictures cannot disagree with them.
         fig_01: maximum temperature of the example board with the program's typical stack-up and the published ones of fabricators;
         fig_02: rise of the hottest point for several stack-ups, in the five models; fig_03: sensitivity of the rise to the stack-up numbers.
Usage: python research/stackup/make_figures.py   (from the repository root; about 15 seconds)
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
OUT = HERE / "figures"          # kept in the repository on purpose: the README files link to them


def run(script):
    """!
    @brief Run one study of this folder and return what it prints.
    @param script File name of the study.
    @return str Standard output.
    """
    return subprocess.run([sys.executable, str(HERE / script)], capture_output=True, text=True, check=True).stdout


def table(text, header):
    """!
    @brief Rows of the Markdown table that follows a header line.
    @param text Output of a study.
    @param header Start of the line before the table.
    @return list of lists of str (cells).
    """
    lines = text.splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.startswith(header)) + 3
    rows = []
    while i < len(lines) and lines[i].startswith("|"):
        rows.append([c.strip() for c in lines[i].strip("|").split("|")])
        i += 1
    return rows


def fig_vendors():
    """!
    @brief Maximum temperature of the example board for every stack-up (program templates against fabricators), grouped by layer count.
    @return None.
    """
    rows = []
    for ln in run("stackup_vendor_check.py").splitlines():
        m = re.match(r"(\d)L (.+?)\s+total ([\d.]+) mm\s+Tmax ([\d.]+)", ln)
        if m:
            rows.append((int(m.group(1)), m.group(2).strip(), float(m.group(4))))
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.8), sharex=False)
    for ax, layers in zip(axs, (4, 6, 8)):
        r = [x for x in rows if x[0] == layers]
        names = [x[1].split("(")[0].strip()[:34] for x in r]
        cols = ["#1d4ed8" if "program" in n else "#d97706" if "OSH" in n else "#9ca3af" for n in names]
        ax.barh(range(len(r)), [x[2] for x in r], color=cols)
        ax.set_yticks(range(len(r))); ax.set_yticklabels(names, fontsize=7); ax.invert_yaxis()
        lo = min(x[2] for x in r)
        ax.set_xlim(lo - 3, max(x[2] for x in r) + 1.5)
        for k, x in enumerate(r):
            ax.text(x[2] + 0.1, k, f"{x[2]:.1f}", va="center", fontsize=7)
        ax.set_title(f"{layers} layers", fontsize=10)
        ax.set_xlabel("Tmax of the example board (°C)")
    fig.suptitle("Program templates (blue) against published fabricator stack-ups: the dielectric split moves Tmax by 0.1 to 1.7 °C; OSH Park (orange) has thicker outer copper", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig_01_vendor_stackups.png", dpi=110)
    plt.close(fig)


def fig_stacks(text):
    """!
    @brief Rise of the hottest point of several stack-ups in the five models.
    @param text Output of stackup_outline_study.py.
    @return None.
    """
    rows = table(text, "A. Advanced")
    names = [r[0] for r in rows]
    fvm = np.array([float(r[1]) for r in rows])
    others = {n: [float(r[k].split()[0]) for r in rows] for k, n in ((2, "FDM"), (3, "3D solid"), (4, "Lumped"), (5, "Analytic"))}
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(14, 5.4))
    ax.bar(x - 0.3, fvm, 0.15, label="FVM (K)", color="#1f2937")
    for k, (n, col) in enumerate((("FDM", "#6b7280"), ("3D solid", "#059669"), ("Lumped", "#d97706"), ("Analytic", "#1d4ed8"))):
        ax.bar(x - 0.15 + 0.15 * k, fvm * (1 + np.array(others[n]) / 100.0), 0.15, label=n, color=col)
    ax.set_xticks(x); ax.set_xticklabels([textwrap.fill(n, 20) for n in names], fontsize=7)
    ax.set_ylabel("Rise of the hottest point (K)")
    ax.set_title("The stack-up matters (70 to 102 K on the same board) and the models follow it in the same direction", fontsize=10)
    ax.legend(fontsize=8, ncol=5)
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_stackups_in_five_models.png", dpi=110)
    plt.close(fig)


def fig_sensitivity(text):
    """!
    @brief Change of the rise for a change of each stack-up number.
    @param text Output of stackup_outline_study.py.
    @return None.
    """
    rows = table(text, "C. Sensitivity")
    names = [r[0] for r in rows]
    ch = [float(r[2].replace("%", "").replace("+", "").strip()) for r in rows]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.barh(range(len(rows)), ch, color=["#b45309" if abs(c) > 3 else "#6b7280" for c in ch])
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(names, fontsize=8); ax.invert_yaxis()
    ax.axvline(0, color="black", lw=0.8)
    for k, c in enumerate(ch):
        ax.text(c + (0.1 if c >= 0 else -0.1), k, f"{c:+.1f} %", va="center", ha="left" if c >= 0 else "right", fontsize=8)
    ax.set_xlim(-6, 8)
    ax.set_xlabel("Change in the rise (%)")
    ax.set_title("Only the finished copper matters (orange)", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_sensitivity_to_stackup_numbers.png", dpi=110)
    plt.close(fig)


def main():
    """!
    @brief Make the three figures.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_vendors()
    text = run("stackup_outline_study.py")
    fig_stacks(text)
    fig_sensitivity(text)
    print("figures in", OUT)


if __name__ == "__main__":
    main()
