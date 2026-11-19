#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the planned FEM transient (no data, no program): the section with the capacity of every element, the mass matrix, the time methods, the time grid and the
       edges, the solver strategy, the read-outs, the validation map and the memory stages. Run from the repository root:
       `.venv/bin/python releases/2.9.0/fem-transient/scripts/make_diagrams.py`; it writes `figures/fig_NN_*.png` next to the note (the branch runs it; the planning
       pass did not).
@details Every picture is a schematic: the numbers on it are labels or hand arithmetic of `DESIGN.md`, never a result. Shapes come from `research/diagram_kit.py`.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "research"))
import diagram_kit as dk                                            # noqa: E402

OUT = os.path.join(HERE, "..", "figures")


def _path(name):
    """!
    @brief Output path of a figure, creating the folder.
    @param name File name.
    @return str Full path.
    """
    os.makedirs(OUT, exist_ok=True)
    return os.path.join(OUT, name)


def fig_01_section():
    """!
    @brief The cross-section as the FEM sees it in time: elements with their capacity, via, block, films and the three heat paths.
    @return None.
    """
    fig, ax = dk.canvas(9, 5)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    dk.layer(ax, 0.5, 4.6, 9, 0.3, dk.COPPER, "copper slab, rho c = f rho_cu cp_cu + (1-f) rho c laminate")
    for k in range(3):
        dk.layer(ax, 0.5, 3.6 + 0.3 * k, 9, 0.3, "#c9d8a8", "dielectric gap element, rho c of the gap" if k == 1 else "")
    dk.layer(ax, 0.5, 3.3, 9, 0.3, dk.COPPER, "copper slab (bottom)")
    dk.layer(ax, 4.2, 3.3, 0.5, 1.6, dk.COPPER, "")
    dk.box(ax, 4.0, 5.1, 1.0, 0.5, "part: source, no mass", color="#f4cccc")
    dk.layer(ax, 6.5, 2.4, 2.5, 0.9, dk.METAL, "metal block + pad")
    dk.arrow(ax, 4.5, 5.1, 4.5, 4.95, color=dk.HEAT, label="p(t) F")
    dk.arrow(ax, 2.0, 5.2, 2.0, 5.9, color=dk.BLUE, label="film h (top), no capacity")
    dk.arrow(ax, 2.0, 3.2, 2.0, 2.5, color=dk.BLUE, label="film h (bottom)")
    ax.text(0.5, 1.6, "heat paths: stored in M dT/dt, conducted through A, lost through the films", fontsize=8)
    dk.save(fig, _path("fig_01_transient_section.png"), "FEM transient: the capacity of every element (schematic)")


def fig_02_mass():
    """!
    @brief Lumped against consistent mass of one hexahedron, drawn as a 1D bar.
    @return None.
    """
    fig, axs = dk.canvas(9, 3.6, ncols=2)
    for ax, kind in zip(axs, ("lumped: rho c V / 8 at each corner", "consistent: the corner couples with its 7 neighbours")):
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 3)
        dk.box(ax, 0.5, 0.8, 3, 1.2, kind, color="#cfe3f5")
        if kind.startswith("consistent"):
            dk.arrow(ax, 1.0, 2.1, 3.0, 2.1, label="M_ij != 0", style="<->")
        else:
            dk.arrow(ax, 1.0, 2.1, 1.0, 2.6, label="M_ii only")
    dk.save(fig, _path("fig_02_mass_matrix.png"), "Mass matrix of a Q1 element (schematic)")


def fig_03_time_methods():
    """!
    @brief Amplification factors of implicit Euler, Crank-Nicolson and BDF2 against lambda dt (textbook curves).
    @return None.
    """
    fig, ax = dk.plt.subplots(figsize=(7, 4))
    x = np.logspace(-3, 4, 300)
    ax.semilogx(x, np.exp(-x), "k", label="exact exp(-x)")
    ax.semilogx(x, 1.0 / (1.0 + x), label="implicit Euler (theta 1)")
    ax.semilogx(x, (1.0 - 0.5 * x) / (1.0 + 0.5 * x), label="Crank-Nicolson (theta 1/2): tends to -1")
    ax.set_xlabel("lambda dt (illustrative, textbook formulas)")
    ax.set_ylabel("factor per step")
    ax.legend(fontsize=7)
    dk.save(fig, _path("fig_03_time_methods.png"), "Time methods on a stiff mode (illustrative)")


def fig_04_time_grid():
    """!
    @brief Time axis of a step response (doubling stages) and of a profile run (constant dt, unaligned edge).
    @return None.
    """
    fig, axs = dk.canvas(9, 4, nrows=2)
    ax = axs[0]
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 2)
    t = 0.2
    for j in range(7):
        ax.plot([t, t], [0.6, 1.2], "k", lw=1)
        t += 0.2 * 2 ** (j * 0.55)
    ax.text(0.2, 1.5, "step response: stages with the step doubling, one factor each, Rannacher half steps at t = 0", fontsize=8)
    ax = axs[1]
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 2)
    for k in range(13):
        ax.plot([k, k], [0.6, 1.0], "k", lw=0.8)
    ax.plot([4.4, 4.4], [0.2, 1.4], color=dk.HEAT, lw=2)
    ax.text(0.2, 1.6, "profile run: constant dt, exact step-mean power, the edge (red) falls inside a step", fontsize=8)
    dk.save(fig, _path("fig_04_time_grid_and_edges.png"), "Time grids (schematic)")


def fig_05_strategy():
    """!
    @brief Flow of one FEM transient run.
    @return None.
    """
    fig, ax = dk.canvas(10, 3.5)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    steps = ["mesh + rho c", "A, M, F", "per dt: factor or AMG hierarchy (one alive)", "step loop, warm start, progress, cancel", "Rcol T, Rsurf T", "TransientResult / ProfileResult"]
    for i, s in enumerate(steps):
        dk.box(ax, 0.2 + 1.95 * i, 1.4, 1.75, 1.2, s, size=7)
        if i:
            dk.arrow(ax, 0.2 + 1.95 * i - 0.2, 2.0, 0.2 + 1.95 * i, 2.0)
    dk.save(fig, _path("fig_05_solver_strategy.png"), "FEM transient: the flow of one run (schematic)")


def fig_06_readouts():
    """!
    @brief The three read-outs on the section at one instant.
    @return None.
    """
    fig, ax = dk.canvas(8, 3.6)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    dk.layer(ax, 0.5, 2.6, 9, 0.3, dk.COPPER, "top copper: column = volume mean over the slab (headline); surface = mean over its top face")
    dk.layer(ax, 0.5, 1.6, 9, 1.0, "#c9d8a8", "dielectric")
    dk.layer(ax, 0.5, 1.3, 9, 0.3, dk.COPPER, "bottom copper")
    ax.plot([4.5], [2.95], "o", color=dk.HEAT)
    ax.text(4.7, 3.2, "point: hottest node", fontsize=8)
    dk.save(fig, _path("fig_06_readouts_in_time.png"), "Read-outs of a frame (schematic)")


def fig_07_validation_map():
    """!
    @brief Which reference covers which case.
    @return None.
    """
    fig, ax = dk.canvas(10, 4)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5)
    cols = ["closed forms (RC, mode, slab, semi-infinite)", "research transient tool (port, plate, disc)", "FVM and FDM on the same boards", "windows: periodic state, energy"]
    for i, c in enumerate(cols):
        dk.box(ax, 0.3 + 2.9 * i, 2.0, 2.7, 1.4, c, size=7)
    dk.arrow(ax, 6.0, 1.9, 6.0, 1.0, label="FEM transient")
    dk.save(fig, _path("fig_07_validation_map.png"), "Validation plan (schematic)")


def fig_08_memory():
    """!
    @brief Stack of bytes per unknown by stage (hypothesis H4, unmeasured).
    @return None.
    """
    fig, ax = dk.plt.subplots(figsize=(7, 4))
    stages = ["assembly A", "assembly M", "B + hierarchy", "state + operators", "frames"]
    heights = [6.7, 6.7, 1.0, 0.8, 0.5]                              # kB per unknown: labels of the hypothesis, not data
    ax.bar(stages, heights, color="#9ecae1")
    ax.set_ylabel("kB per unknown (HYPOTHESIS H4, not measured)")
    ax.tick_params(axis="x", labelsize=7)
    dk.save(fig, _path("fig_08_memory_stages.png"), "Memory by stage (illustrative)")


def main():
    """!
    @brief Draw every figure.
    @return None.
    """
    for f in (fig_01_section, fig_02_mass, fig_03_time_methods, fig_04_time_grid, fig_05_strategy, fig_06_readouts, fig_07_validation_map, fig_08_memory):
        f()


if __name__ == "__main__":
    main()
