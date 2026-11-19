#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief The three drawings of DESIGN.md (D1 the time-step scheme, D2 the profile runner, D3 the first seconds), written to `figures/` next to the note.
@details Run from the repository root: `.venv/bin/python releases/2.9.0/fem-transient/scripts/make_diagrams.py`. D1 and D2 are schematics whose curves are textbook formulas and
         the program's own plan rule (`profiles.plan_run`: `n_per = ceil(window / (shortest / 10))`, `dt = window / n_per`); D3 quotes three kinds of numbers: the step response
         of the two-layer board of `research/transient-reference-boards` 4.2 (read from that README), the arithmetic of DESIGN.md 3 and the output of the tiny check
         `check_first_seconds.py` (imported here, run again). Shapes come from `research/diagram_kit.py`. SI units.
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "research"))
sys.path.insert(0, HERE)
import diagram_kit as dk                                            # noqa: E402
import check_first_seconds as cfs                                   # noqa: E402

OUT = os.path.join(HERE, "..", "figures")
plt = dk.plt


def _path(name):
    """!
    @brief Output path of a figure, creating the folder.
    @param name File name.
    @return str Full path.
    """
    os.makedirs(OUT, exist_ok=True)
    return os.path.join(OUT, name)


def fig_01_time_step_scheme():
    """!
    @brief D1: the system and its step (flow), the factor per step of each scheme, and the time grid of a step response with the fine start.
    @return None.
    """
    fig = plt.figure(figsize=(11, 8))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.1])
    ax = fig.add_subplot(gs[0, :])
    ax.axis("off")
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 4)
    boxes = [("mesh + rho c per element\n(femmesh.build)", 0.1), ("assemble once\nA (K + films), M (rho c),\nF = [f_1 .. f_nh]", 2.6),
             ("per dt: B = M/dt + theta A\nfactor (n <= 30 000) or\npyamg hierarchy, ONE alive", 5.2), ("step: B T1 = (M/dt - (1-theta) A) T0\n+ (theta p1 + (1-theta) p0) F", 8.0),
             ("read-outs: Rcol T every step,\nRsurf T and the point max\nat the output frames", 10.9)]
    for text, x in boxes:
        dk.box(ax, x, 1.6, {0.1: 2.3, 2.6: 2.3, 5.2: 2.5, 8.0: 2.8}.get(x, 3.9), 1.6, text, size=7)
    for x0, x1 in ((2.4, 2.6), (4.9, 5.2), (7.7, 8.0), (10.8, 10.9)):
        dk.arrow(ax, x0, 2.4, x1, 2.4)
    dk.box(ax, 5.2, 0.1, 2.3, 0.9, "Rannacher: two implicit-Euler\nhalf steps at t = 0 only (CN)", color="#f4cccc", size=7)
    dk.arrow(ax, 6.4, 1.0, 6.4, 1.6, color=dk.HEAT)
    dk.box(ax, 8.0, 0.1, 2.3, 0.9, "stage change: new dt,\nold factor freed first", color="#f4cccc", size=7)
    dk.arrow(ax, 9.2, 1.0, 9.2, 1.6, color=dk.HEAT)
    ax.text(0.1, 3.7, "M dT/dt + A T = F p(t)   (T is the rise above the ambient; films are in A, no capacity)", fontsize=9, weight="bold")

    ax = fig.add_subplot(gs[1, 0])
    x = np.logspace(-3, 4, 300)
    ax.semilogx(x, np.exp(-x), "k", label="exact exp(-x)")
    ax.semilogx(x, 1.0 / (1.0 + x), label="implicit Euler: 1/(1+x), first order, tends to 0")
    ax.semilogx(x, (1.0 - 0.5 * x) / (1.0 + 0.5 * x), label="Crank-Nicolson: tends to -1, second order")
    ax.axhline(0, color="gray", lw=0.5)
    ax.set_xlabel("lambda dt (rate of a mode times the step)")
    ax.set_ylabel("factor per step")
    ax.set_title("a stiff mode (lambda dt >> 1) is damped by Euler,\nrings with alternating sign under CN: hence the start", fontsize=8)
    ax.legend(fontsize=6.5, loc="lower right")

    ax = fig.add_subplot(gs[1, 1])
    # time grid: the program's doubling stages (4 steps each); the FIRST stage is walked in steps of dt0/4 (16 steps, one extra factorisation) so that the first
    # output time has four steps behind it; the output times are the program's (the Difference view subtracts like for like)
    dt0 = 1000.0 / (4 * (2 ** 10 - 1))                              # DESIGN.md 3: t_end 1000 s, 10 stages, 4 steps per stage (fvm.transient_from_network rule)
    fine = dt0 / 4 * np.arange(1, 17)
    t, coarse = 4 * dt0, []
    for j in range(1, 10):
        for _ in range(4):
            t += dt0 * 2 ** j
            coarse.append(t)
    coarse = np.array(coarse)
    ax.semilogx(fine, np.full(fine.size, 1.0), "|", ms=14, color=dk.HEAT, label="start: first stage in 16 steps of dt0/4 (one extra factor)")
    ax.semilogx(np.r_[dt0 * np.arange(1, 5), coarse], np.zeros(4 + coarse.size), "|", ms=14, color="k", label="the program's output times: 10 stages x 4 steps, dt doubles")
    ax.axvline(0.3, color=dk.BLUE, ls="--", lw=1)
    ax.text(0.32, 0.5, "0.3 s", color=dk.BLUE, fontsize=7)
    ax.set_ylim(-0.6, 1.8)
    ax.set_yticks([])
    ax.set_xlabel("t (s), arithmetic for t_end = 1000 s: dt0 = %.3f s" % dt0)
    ax.set_title("time grid of a step response: one factorisation per stage (11 here)", fontsize=8)
    ax.legend(fontsize=6.5, loc="upper left")
    dk.save(fig, _path("fig_01_time_step_scheme.png"), "D1. FEM transient: the step and the time grid")


def fig_02_profile_runner():
    """!
    @brief D2: the profile runner (profiles.run_windows) with the FEM adapter, and the exact step-mean power of an unaligned square wave.
    @return None.
    """
    fig = plt.figure(figsize=(11, 8))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.15, 1.0])
    ax = fig.add_subplot(gs[0, :])
    ax.axis("off")
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 6.5)
    dk.box(ax, 0.1, 4.6, 3.3, 1.5, "profiles.decide + plan_run\n(shared by every model)\nwindow, n_per, dt, resolved heaters", size=7.5)
    dk.box(ax, 4.2, 4.6, 3.8, 1.5, "run_fem(problem, decisions, options,\ncell_mm, progress) -> ProfileResult\nmemory.check(transient) first", size=7.5, color="#cfe3f5", bold=True)
    dk.box(ax, 8.8, 4.6, 3.6, 1.5, "_FEMAdapter.begin:\nsolve_many([p_avg, p_init, p_peak])\n-> steady_average_max, steady_peak_max", size=7.5)
    dk.box(ax, 13.0, 4.6, 2.9, 1.5, "prepare(dt):\nB = M/dt + theta A\nONE factor for the run", size=7.5)
    for a, b in ((3.4, 4.2), (8.0, 8.8), (12.4, 13.0)):
        dk.arrow(ax, a, 5.35, b, 5.35)
    dk.box(ax, 0.1, 2.2, 4.6, 1.7, "per step (run_windows loop):\nP = exact mean of every wave over the step\nadvance(state, dt, P)  [F @ P is the load]", size=7.5)
    dk.box(ax, 5.4, 2.2, 4.4, 1.7, "observe(state): hottest column value\nand per heater (Rcol T)\nframe(state), peak_values(state)", size=7.5)
    dk.box(ax, 10.5, 2.2, 5.4, 1.7, "after each window: peak and minimum repeat?\n(stable_c) -> stop; progress per window,\ncancel per step (FemCancelled)", size=7.5)
    for a, b in ((4.7, 5.4), (9.8, 10.5)):
        dk.arrow(ax, a, 3.05, b, 3.05)
    dk.box(ax, 0.1, 0.1, 7.6, 1.5, "FEM adds nothing to the plan: dt, n_per and the steps are those of the FVM and FDM,\nso the curves are compared step for step (campaign rule: same theta, same grid)", color="#fff2cc", size=7.5)
    dk.box(ax, 8.3, 0.1, 7.6, 1.5, "not used: the face terms of _FVMAdapter (the FEM resolves\nthe laminate under a part); part face peak = point series", color="#fff2cc", size=7.5)

    ax = fig.add_subplot(gs[1, 0])
    period, duty = 1.0, 0.33
    shortest = duty * period
    n_per = max(math.ceil(period / (shortest / 10.0)), 20)             # profiles.plan_run
    dt = period / n_per
    edges = np.arange(n_per + 1) * dt
    on = lambda t: ((t % period) < duty * period) * 1.0                # noqa: E731
    tf = np.linspace(0, period, 2000)
    mean = np.array([np.mean(on(np.linspace(a, b, 400, endpoint=False))) for a, b in zip(edges[:-1], edges[1:])])
    ax.plot(tf, on(tf), color="gray", lw=1.2, label="the wave (duty 0.33)")
    ax.step(edges, np.r_[mean, mean[-1]], where="post", color=dk.HEAT, lw=1.6, label="power the step receives: exact mean")
    ax.set_xlabel("t / period")
    ax.set_ylabel("power factor")
    k = int(np.argmax((mean > 0) & (mean < 1)))
    ax.annotate("edge inside step %d:\nmean %.2f" % (k + 1, mean[k]), (edges[k] + dt / 2, mean[k]), (0.55, 0.75), fontsize=7, arrowprops={"arrowstyle": "->"})
    ax.set_title("n_per = %d, dt = period/%d: the edge is not on a step boundary" % (n_per, n_per), fontsize=8)
    ax.legend(fontsize=7, loc="upper right")

    ax = fig.add_subplot(gs[1, 1])
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    rows = [("steady states\n(3 right-hand sides)", "direct: 1 factor, 3 back substitutions\nCG: 1 hierarchy, 3 solves"),
            ("every step", "2 matvecs + 1 solve with B\n(no assembled right-hand matrix)"),
            ("every window", "frames at stride n_per // frames:\nsurface Rsurf T only there"),
            ("what is stored", "T, T_prev, work vectors: 3 to 4 x 8 B\nper unknown; frames n_out x L x ny x nx")]
    for i, (a, b) in enumerate(rows):
        y = 4.7 - 1.5 * i
        dk.box(ax, 0.1, y, 3.6, 1.1, a, size=7.5)
        dk.box(ax, 4.0, y, 5.9, 1.1, b, size=7.5, color="#e2efda")
    dk.save(fig, _path("fig_02_profile_runner.png"), "D2. FEM transient: the profile runner and its adapter")


def fig_03_first_seconds():
    """!
    @brief D3: the first seconds: what the node of each model holds, what the models read (numbers of transient-reference-boards 4.2), and the error against the step count.
    @return None.
    """
    fig = plt.figure(figsize=(12, 4.8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 1.1, 1.1])
    ax = fig.add_subplot(gs[0, 0])
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    dk.layer(ax, 0.3, 6.2, 4.3, 0.35, dk.COPPER, "")
    dk.layer(ax, 0.3, 3.0, 4.3, 3.2, dk.FR4, "")
    ax.text(2.45, 4.6, "FR-4 gap\n(0.765 mm per side,\ntwo layers)", ha="center", fontsize=7)
    dk.layer(ax, 0.3, 2.65, 4.3, 0.35, dk.COPPER, "")
    ax.text(2.45, 2.0, "FVM: one node =\ncopper + half gap", ha="center", fontsize=7)
    ax.add_patch(plt.Rectangle((0.3, 3.0), 4.3, 3.55, fill=False, ec=dk.BLUE, lw=1.6, ls="--"))
    dk.layer(ax, 5.4, 6.2, 4.3, 0.35, dk.COPPER, "")
    for k in range(6):
        dk.layer(ax, 5.4, 3.0 + 0.53 * k, 4.3, 0.53, dk.FR4, "")
    dk.layer(ax, 5.4, 2.65, 4.3, 0.35, dk.COPPER, "")
    ax.text(7.55, 2.0, "FEM: copper slab +\ngap elements", ha="center", fontsize=7)
    ax.annotate("column read-out =\nvolume mean over\nthe copper slab", (7.55, 6.38), (5.6, 7.4), fontsize=6.5, arrowprops={"arrowstyle": "->"})
    dk.arrow(ax, 2.45, 7.9, 2.45, 6.65, color=dk.HEAT)
    dk.arrow(ax, 7.55, 7.9, 7.55, 6.65, color=dk.HEAT)
    ax.text(5.0, 0.3, "the step heats the copper first; the gap follows\nafter (0.765 mm)^2 / 1.8e-7 = 3.3 s", ha="center", fontsize=7)

    ax = fig.add_subplot(gs[0, 1])
    t = np.array([0.3, 1.0, 3.0, 10.0])
    fem = np.array([4.99, 7.58, 10.11, 13.07])                       # transient-reference-boards 4.2: finite-element copper under the part, K/W
    fvm = np.array([2.08, 5.31, 9.18, 12.88])                        # same table: the program's layer node (FVM)
    ax.semilogx(t, fem, "o-", color=dk.BLUE, label="FEM copper under the part (reference)")
    ax.semilogx(t, fvm, "s--", color=dk.HEAT, label="program, one node per layer")
    for a, b, c in zip(t, fem, fvm):
        ax.text(a, c - 0.9, "%+.0f %%" % (100 * (c / b - 1)), fontsize=7, ha="center", color=dk.HEAT)
    ax.set_xlabel("t after the step (s)")
    ax.set_ylabel("rise per watt (K/W), two-layer board, 10 mm part")
    ax.set_title("first seconds of the two-layer board\n(numbers of transient-reference-boards 4.2)", fontsize=8)
    ax.legend(fontsize=6.5, loc="lower right")
    ax.set_ylim(0, 15)

    ax = fig.add_subplot(gs[0, 2])
    x = cfs.graded_nodes()
    n = 12
    for scheme, style, lab in (("euler", "s-", "implicit Euler"), ("cn", "^-", "Crank-Nicolson, no start"), ("cn_rannacher", "o-", "CN + 2 Euler half steps")):
        ts, T = cfs.run(x, scheme, True, [0.24] * n)
        err = 100 * (T / (2 * np.sqrt(ts / np.pi) / cfs.EFF) - 1)
        ax.plot(np.arange(1, n + 1), err, style, ms=4, label=lab)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_ylim(-14, 28)
    ax.set_xlabel("steps since the switch-on")
    ax.set_ylabel("face temperature error against 2q sqrt(t/pi)/e (%)")
    ax.set_title("1D semi-infinite solid, consistent mass, 45 nodes\n(check_first_seconds.py; same curve for any dt)", fontsize=8)
    ax.legend(fontsize=6.5)
    dk.save(fig, _path("fig_03_first_seconds.png"), "D3. FEM transient: the first seconds")


def main():
    """!
    @brief Draw the three figures.
    @return None.
    """
    for f in (fig_01_time_step_scheme, fig_02_profile_runner, fig_03_first_seconds):
        f()


if __name__ == "__main__":
    main()
