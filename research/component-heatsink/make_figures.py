"""!
@file make_figures.py
@brief Pictures of the component, top path and heatsink studies, written to figures/ (committed, linked from the README files).

@details The numbers come from running the studies of this folder and reading the tables they print.
         fig_01: junction temperature of four real parts with no top path, a bare mould and a 12 K/W heatsink; fig_02: the program's top path against the junction-node prototype;
         fig_03: heatsink scenarios (fixed resistance against natural-convection scaling with the temperature rise, and forced air); fig_04: a metal block under the board by metal and interface.
Usage: python research/component-heatsink/make_figures.py   (from the repository root; about 1.5 minutes)
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


def num(cell):
    """!
    @brief First number in a table cell.
    @param cell Text such as "104.6 (0.6 %)" or "+2.7".
    @return float The number.
    """
    return float(re.search(r"[+-]?\d+\.?\d*", cell).group(0))


def fig_parts():
    """!
    @brief Junction temperature of four parts: board only, bare mould, 12 K/W heatsink.
    @return None.
    """
    head, rows = table(run("component_study.py"), "| Part | Level 1 Tj")
    names = [r[0].split("(")[0].strip() for r in rows]
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(10, 4.6))
    for k, (col, lab) in enumerate((("#6b7280", "no top path (all the power into the board)"), ("#d97706", "bare mould"), ("#1d4ed8", "12 K/W clip-on heatsink + paste"))):
        v = [num(r[k + 1]) for r in rows]
        ax.bar(x + (k - 1) * 0.27, v, 0.27, color=col, label=lab)
        for xi, vi, r in zip(x, v, rows):
            if k > 0:
                ax.text(xi + (k - 1) * 0.27, vi + 1.5, re.search(r"\((.*?)\)", r[k + 1]).group(1), ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=8)
    ax.set_ylabel("Junction temperature (°C)")
    ax.set_title("A bare mould carries about 1 % of the heat; a heatsink on top takes 41 to 51 % (labels: share of the heat through the top)", fontsize=9)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_01_parts_with_and_without_top_path.png", dpi=110)
    plt.close(fig)


def fig_prototype():
    """!
    @brief The program's top path against the junction-node prototype.
    @return None.
    """
    head, rows = table(run("top_path_study.py"), "| Part | Tj without top path")
    names = [r[0].split("(")[0].strip() for r in rows]
    x = np.arange(len(rows))
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
    axs[0].bar(x - 0.27, [num(r[1]) for r in rows], 0.27, color="#6b7280", label="no top path")
    axs[0].bar(x, [num(r[2]) for r in rows], 0.27, color="#1d4ed8", label="program (fixed-point loop)")
    axs[0].bar(x + 0.27, [num(r[4]) for r in rows], 0.27, color="#059669", label="junction-node prototype")
    axs[0].set_xticks(x); axs[0].set_xticklabels(names, fontsize=8); axs[0].set_ylabel("Tj (°C)"); axs[0].legend(fontsize=8)
    axs[0].set_title("Junction temperature", fontsize=10)
    axs[1].bar(x, [num(r[2]) - num(r[4]) for r in rows], 0.5, color="#1d4ed8")
    axs[1].axhline(0, color="black", lw=0.8)
    axs[1].set_xticks(x); axs[1].set_xticklabels(names, fontsize=8); axs[1].set_ylabel("Program minus prototype (K)")
    axs[1].set_title("The program is 0.4 to 0.8 K above the prototype", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_program_top_path_vs_node_prototype.png", dpi=110)
    plt.close(fig)


def fig_scenarios():
    """!
    @brief Heatsink scenarios: natural-convection scaling with the power, and forced air.
    @return None.
    """
    text = run("heatsink_convection_study.py")
    h1, r1 = table(text, "| Power [W]")
    h2, r2 = table(text, "| Air | sink R used")
    p = [num(r[0]) for r in r1]
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.2))
    axs[0].plot(p, [num(r[1]) for r in r1], "o-", color="#6b7280", label="fixed 12 K/W")
    axs[0].plot(p, [num(r[2]) for r in r1], "o-", color="#d97706", label="scaled with the temperature rise")
    axs[0].set_xlabel("Power (W)"); axs[0].set_ylabel("Tj (°C)"); axs[0].legend(fontsize=8)
    axs[0].set_title("MOSFET, 12 K/W heatsink: scaling matters at high power", fontsize=9)
    axs[1].plot(p, [num(r[3]) for r in r1], "s-", color="#1d4ed8")
    axs[1].axhline(12, color="#6b7280", ls="--", lw=1)
    axs[1].set_xlabel("Power (W)"); axs[1].set_ylabel("Heatsink resistance used (K/W)")
    axs[1].set_title("Natural-convection resistance against the power (dashed: the 12 K/W at a 75 K rise)", fontsize=9)
    labels = [r[0] for r in r2]
    axs[2].bar(labels, [num(r[2]) for r in r2], color="#1d4ed8")
    for k, r in enumerate(r2):
        axs[2].text(k, num(r[2]) + 0.3, f"R = {num(r[1]):.1f}", ha="center", fontsize=8)
    axs[2].set_ylim(60, 73)
    axs[2].set_ylabel("Tj (°C)")
    axs[2].set_title("Same heatsink, forced air (factors of the volumetric guide)", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_heatsink_convection_scenarios.png", dpi=110)
    plt.close(fig)


def fig_metal_interface():
    """!
    @brief Tj of the MOSFET with a metal block under the board, by metal and interface material.
    @return None.
    """
    head, rows = table(run("heatsink_study.py"), "| Metal | no block")
    cols = head[2:]
    data = np.array([[num(c) for c in r[2:]] for r in rows])
    fig, ax = plt.subplots(figsize=(11, 3.8))
    im = ax.imshow(data, cmap="viridis_r", aspect="auto")
    ax.set_xticks(range(len(cols))); ax.set_xticklabels([textwrap.fill(re.sub(r"\s*\[.*", "", c), 24) for c in cols], fontsize=7)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows], fontsize=8)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, f"{data[i, j]:.1f}", ha="center", va="center", color="white", fontsize=8)
    ax.set_title("MOSFET, 2 W, 3 mm block under the board: Tj (°C); no block 107.6 °C. The interface moves it by 2 K, the metal by 1 K", fontsize=9)
    fig.colorbar(im, ax=ax, label="°C")
    fig.tight_layout()
    fig.savefig(OUT / "fig_04_block_metal_and_interface.png", dpi=110)
    plt.close(fig)


def main():
    """!
    @brief Make the figures.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_parts()
    fig_prototype()
    fig_scenarios()
    fig_metal_interface()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
