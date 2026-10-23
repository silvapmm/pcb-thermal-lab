"""!
@file make_figures.py
@brief Pictures of the via-fill study, written to figures/ (committed, linked from the README files).

@details fig_01: thermal resistance of one 0.3 mm via through 1.6 mm for every fill; fig_02: maximum temperature of the example board for every fill;
         fig_03: resistance of one via against its diameter, open barrel against copper fill. Needs numpy, matplotlib and the repository's dependencies.
Usage: python research/via-fill/scripts/make_figures.py   (from the repository root; about 1 minute)
"""

import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))      # repository root
from pcbthermal import SolverOptions, simulate                           # noqa: E402
from pcbthermal.examples import example_board                            # noqa: E402
from pcbthermal.model import VIA_FILLS, Via                              # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "figures"          # kept in the repository on purpose: the README files link to them
K_CU, PLATING, LENGTH = 385.0, 25e-6, 1.6e-3                # copper conductivity (W/mK), plating thickness (m), board thickness (m)
COLOURS = ["#6b7280", "#9ca3af", "#d97706", "#b45309"]      # open, resin, paste, copper


def via_resistance(diameter, k_fill):
    """!
    @brief Thermal resistance of one via barrel along its axis.
    @param diameter Barrel outer diameter in m.
    @param k_fill Conductivity of the fill in W/mK (0 = open).
    @return float Resistance in K/W.
    """
    v = Via(0.0, 0.0, diameter, False, "", k_fill)
    return LENGTH / (K_CU * v.thermal_area(PLATING, K_CU))


def fig_resistance():
    """!
    @brief Bar chart of the resistance of one 0.3 mm via for every fill.
    @return None.
    """
    names = [f[0].split(",")[0] for f in VIA_FILLS]
    r = [via_resistance(0.3e-3, f[1]) for f in VIA_FILLS]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(names, r, color=COLOURS[:len(names)])
    for b, v in zip(bars, r):
        ax.text(b.get_x() + b.get_width() / 2, v + 3, f"{v:.0f} K/W", ha="center", fontsize=9)
    ax.set_ylabel("Resistance of one via (K/W)")
    ax.set_title("One 0.3 mm via through 1.6 mm: only a copper fill changes the heat path", fontsize=10)
    ax.set_ylim(0, max(r) * 1.15)
    fig.tight_layout()
    fig.savefig(OUT / "fig_01_via_resistance_by_fill.png", dpi=110)
    plt.close(fig)


def fig_board():
    """!
    @brief Maximum temperature of the example board (3 x 3 vias under U1) for every fill.
    @return None.
    """
    names, t = [], []
    for label, k, _note in VIA_FILLS:
        p = example_board()
        for v in p.vias:
            v.filled, v.fill_k = False, k
        names.append(label.split(",")[0])
        t.append(simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"].t_max)
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(names, t, color=COLOURS[:len(names)])
    for b, v in zip(bars, t):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.15, f"{v:.2f} °C ({v - t[0]:+.2f} K)", ha="center", fontsize=8)
    ax.set_ylim(min(t) - 2, max(t) + 1.5)
    ax.set_ylabel("Maximum temperature (°C)")
    ax.set_title("Example board, FVM 0.5 mm: a copper-filled via cools the part by about 4 K", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_example_board_by_fill.png", dpi=110)
    plt.close(fig)


def fig_diameter():
    """!
    @brief Resistance of one via against its diameter, open barrel and copper fill.
    @return None.
    """
    d = np.linspace(0.2e-3, 0.8e-3, 40)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(d * 1e3, [via_resistance(x, 0.0) for x in d], color=COLOURS[0], label="open barrel (25 µm plating)")
    ax.plot(d * 1e3, [via_resistance(x, 385.0) for x in d], color=COLOURS[3], label="copper fill")
    ax.set_xlabel("Via diameter (mm)")
    ax.set_ylabel("Resistance (K/W), 1.6 mm board")
    ax.set_yscale("log")
    ax.grid(alpha=0.3, which="both")
    ax.legend()
    ax.set_title("Resistance of one via against its diameter", fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_resistance_against_diameter.png", dpi=110)
    plt.close(fig)


def main():
    """!
    @brief Make the three figures.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_resistance()
    fig_board()
    fig_diameter()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
