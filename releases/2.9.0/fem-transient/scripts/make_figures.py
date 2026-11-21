#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief The figure of the implemented FEM transient (fig_04): numbers printed by the PROGRAM, not by the design note's checks: the error of the face temperature of a semi-infinite solid
       against the closed form after 1 to 16 steps for the three schemes (`femcore.Stepper` on a graded 1D column), and the rise of the hottest copper cell of the two-layer reference
       board against time in the FEM and the FVM (first seconds to the plateau).
@details Shares the numbering of `make_diagrams.py` (fig_01 to fig_03 there, fig_04 here); the same figure is copied to `docs/images/fig_54_fem_time.png` for `docs/theory.md` 4b.
         Run from the repository root: `.venv/bin/python releases/2.9.0/fem-transient/scripts/make_figures.py` (a few seconds). Light. SI units.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, os.path.join(ROOT, "tests", "regression"))

import matplotlib                                                    # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                      # noqa: E402

OUT = os.path.join(HERE, "..", "figures")


def first_seconds_errors():
    """!
    @brief The error of the face temperature after 1, 2, 4, 8 and 16 steps for implicit Euler, Crank-Nicolson with the Rannacher start and without it, from the program's stepper.
    @return dict scheme label -> (steps array, error in percent array).
    """
    import test_fem_transient_closed_forms as t
    steps = np.array([1, 2, 4, 8, 16])
    out = {}
    for label, theta, start in (("implicit Euler", 1.0, False), ("Crank-Nicolson with the Rannacher start", 0.5, True), ("Crank-Nicolson, no start", 0.5, False)):
        out[label] = (steps, np.array([100.0 * t._face_error(int(s), theta, start) for s in steps]))
    return out


def board_rise():
    """!
    @brief The rise of the hottest column cell of the reference board per watt, FEM against FVM, on the nominal grid of the program (Crank-Nicolson).
    @return Tuple (times, fem rise, fvm rise, board name).
    """
    import regress_boards as B
    from pcbthermal import fem, fvm
    p = B.build("reference_board")
    amb, power = p.board.ambient, p.total_power()
    a = fem.solve_transient(p, 600.0, n_out=60, cell_mm=3.0, theta_scheme=0.5, gap_elements=6)
    b = fvm.solve_transient(p, 600.0, n_out=60, cell_mm=3.0, theta_scheme=0.5)
    return a.times[1:], (a.t_max[1:] - amb) / power, (b.t_max[1:] - amb) / power, "reference_board"


def main():
    """!
    @brief Draw fig_04 and copy it to docs/images.
    @return None.
    """
    os.makedirs(OUT, exist_ok=True)
    err = first_seconds_errors()
    t, f, v, name = board_rise()
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.3), constrained_layout=True)
    for (label, (s, e)), mk in zip(err.items(), "os^"):
        ax[0].plot(s, e, marker=mk, label=label)
    ax[0].axhline(0, color="k", lw=0.8)
    ax[0].set_xscale("log", base=2)
    ax[0].set_yscale("symlog", linthresh=0.1)
    ax[0].set_xlabel("steps since the flux was switched on")
    ax[0].set_ylabel("error of the face temperature, % of 2 q sqrt(t/pi)/e")
    ax[0].set_title("The first steps (program stepper, 1D column)", fontsize=10)
    ax[0].legend(fontsize=8)
    ax[1].semilogx(t, f, label="FEM (resolves the thickness)")
    ax[1].semilogx(t, v, "--", label="FVM (one node per layer)")
    ax[1].set_xlabel("time after the power step, s")
    ax[1].set_ylabel("hottest copper cell, K per W")
    ax[1].set_title(f"{name}, 3 mm cell, Crank-Nicolson", fontsize=10)
    ax[1].legend(fontsize=8)
    path = os.path.join(OUT, "fig_04_program_first_seconds.png")
    fig.savefig(path, dpi=150)
    print("written", path)
    import shutil
    shutil.copy(path, os.path.join(ROOT, "docs", "images", "fig_54_fem_time.png"))          # the figure of docs/theory.md 4b
    for tt, a, b in zip(t, f, v):
        if tt in t[[2, 8, 14, 20, 30, 45, 59]]:
            print(f"t = {tt:8.3f} s  FEM {a:.4f}  FVM {b:.4f} K/W")
    for label, (s, e) in err.items():
        print(label, [f"{x:.2f}" for x in e])


if __name__ == "__main__":
    main()
