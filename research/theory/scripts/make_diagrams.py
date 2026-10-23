"""!
@file make_diagrams.py
@brief Pictures for the theory (folder research/theory) of every model of `docs/theory.md` and for the models and analyses that are planned (`docs/roadmap.md`): what each equation or method does, drawn.
@details Pure drawing and textbook formulas (no program, no data); the numbers quoted are those of `docs/theory.md`, `docs/roadmap.md` and `docs/research.md`. Curves that are only
         illustrative (shape, not value) say so in their caption. Writes figures/fig_01 to fig_16.
         Run: .venv/bin/python research/theory/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np
from matplotlib.patches import Circle, Polygon, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"
CU = "#c97a2b"


def fvm_cell(path):
    """!
    @brief Draw the cell-centred finite volume: the unknown at the centre, the four lateral faces as two half cells in series (harmonic mean), the vertical and ambient conductances, and the matrix row they make (theory section 2).
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(15, 5.2, 1, 3, ratios=[1.3, 1.1, 0.9])
    a = axs[0]
    a.set_xlim(0, 10); a.set_ylim(0, 8); a.set_aspect("equal")
    for i in range(3):
        for j in range(3):
            a.add_patch(Rectangle((1 + 2.6 * i, 1 + 2.2 * j), 2.6, 2.2, fc="#f3d9b1" if (i, j) != (1, 1) else "#ffe9a8", ec="k"))
            a.plot(2.3 + 2.6 * i, 2.1 + 2.2 * j, "ko", ms=3)
    a.text(5.1, 3.0, "θ(i,j)", ha="center", fontsize=9, fontweight="bold")
    for (x0, y0, x1, y1, t) in ((6.4, 3.2, 7.6, 3.2, "Gx"), (3.8, 3.2, 2.7, 3.2, "Gx"), (5.1, 4.7, 5.1, 5.5, "Gy"), (5.1, 2.0, 5.1, 1.2, "Gy")):
        dk.arrow(a, x0, y0, x1, y1, color=dk.HEAT, label="")
        a.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.25, t, ha="center", fontsize=8, color=dk.HEAT)
    a.text(5, 7.6, "plan: heat balance of one cell through its four faces", ha="center", fontsize=9, fontweight="bold")
    a = axs[1]
    a.set_xlim(0, 10); a.set_ylim(0, 8)
    a.text(5, 7.6, "one face = two half cells in series", ha="center", fontsize=9, fontweight="bold")
    dk.box(a, 0.3, 4.6, 2.0, 1.0, "θ1", "#ffe9a8"); dk.box(a, 7.7, 4.6, 2.0, 1.0, "θ2", "#f3d9b1")
    dk.resistor(a, 2.3, 5.0, 5.1, "Δx/(2 S1 Δy)"); dk.resistor(a, 5.0, 7.7, 5.1, "Δx/(2 S2 Δy)")
    a.text(5, 3.3, "G = 2 S1 S2 / (S1 + S2) · Δy/Δx\nthe harmonic mean: a copper / FR-4 edge\nis a series, not an average", ha="center", fontsize=8.5)
    a.text(5, 1.4, "vertical: Gz = kΔxΔy/d + Σ vias k_cu A_via/d\nambient: G_amb = h Δx Δy", ha="center", fontsize=8.5)
    a = axs[2]
    a.set_xlim(0, 10); a.set_ylim(0, 8)
    a.text(5, 7.6, "the matrix row", ha="center", fontsize=9, fontweight="bold")
    n = 5
    for i in range(n):
        for j in range(n):
            on = abs(i - j) <= 1 or abs(i - j) == 2 and False
            a.add_patch(Rectangle((1.2 + 1.3 * j, 5.4 - 1.0 * i), 1.3, 1.0, fc="#e8e8e8" if not on else ("#f4b6b6" if i == j else "#cfe3f5"), ec="grey", lw=0.5))
    a.text(5, 0.6, "K = D − A: symmetric, positive definite M-matrix\n(D = row sums + ambient; A = face conductances ≥ 0)\nmaximum principle, unique solution, Σ G_amb θ = Σ Q", ha="center", va="top", fontsize=8)
    dk.save(fig, path, "FVM: the balance of a cell, the face as two half cells, the matrix (theory section 2)")


def fdm_nodes(path):
    """!
    @brief Draw the node-centred control volumes of the FDM (full inside, half on an edge, a quarter at a corner) against the cells of the FVM.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 5.0, 1, 2)
    n = 4
    for a, kind in zip(axs, ("fvm", "fdm")):
        a.set_xlim(-0.5, n + 0.5); a.set_ylim(-0.8, n + 0.9); a.set_aspect("equal")
        if kind == "fvm":
            for i in range(n):
                for j in range(n):
                    a.add_patch(Rectangle((i, j), 1, 1, fc="#f3d9b1", ec="k"))
                    a.plot(i + 0.5, j + 0.5, "ko", ms=4)
            a.set_title("FVM: unknown at the cell centre; the board edge is a cell face", fontsize=9)
        else:
            for i in range(n + 1):
                for j in range(n + 1):
                    x0, x1 = max(i - 0.5, 0), min(i + 0.5, n)
                    y0, y1 = max(j - 0.5, 0), min(j + 0.5, n)
                    full = (x1 - x0) * (y1 - y0)
                    col = "#f3d9b1" if full == 1 else ("#cfe3f5" if full == 0.5 else "#f4b6b6")
                    a.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=col, ec="k", lw=0.6))
                    a.plot(i, j, "ko", ms=4)
            a.text(2, -0.6, "orange: full volume · blue: half on an edge · red: a quarter at a corner", ha="center", fontsize=8)
            a.set_title("FDM: unknown at the node; the nodes include the board edge", fontsize=9)
    dk.save(fig, path, "FVM cells and FDM control volumes (theory sections 2 and 3)")


def solid3d(path):
    """!
    @brief Draw the 3D solid: real slabs for each copper layer and several for each laminate gap, a via as a copper rod, a metal block, and the harmonic mean of half-cell resistances (theory section 4).
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 5.2, 1, 2, ratios=[1.6, 1])
    a = axs[0]
    a.set_xlim(0, 12); a.set_ylim(0, 8)
    y = 1.0
    for k in range(3):
        dk.layer(a, 0.5, y, 9, 0.35, CU)
        y += 0.35
        if k < 2:
            for s in range(4):
                dk.layer(a, 0.5, y, 9, 0.38, dk.FR4)
                a.plot([0.5, 9.5], [y, y], color="k", lw=0.3)
                y += 0.38
    a.add_patch(Rectangle((5.0, 1.0), 0.4, y - 1.0, fc=CU, ec="k"))
    a.text(5.2, 0.5, "via: rod of the barrel's copper area", ha="center", fontsize=8)
    dk.layer(a, 6.8, y, 2.4, 0.9, dk.METAL, "metal block", size=8)
    dk.box(a, 1.6, y + 0.3, 1.6, 0.6, "heater", "#f4b6b6")
    a.text(10.2, 3.0, "3 copper layers:\none slab each\n\n4 laminate slabs\nper gap", fontsize=8, va="center")
    a.text(5, 7.4, "section of the structured grid", ha="center", fontsize=9, fontweight="bold")
    a = axs[1]
    a.set_xlim(0, 10); a.set_ylim(0, 8)
    a.text(5, 7.4, "conductance of two cells", ha="center", fontsize=9, fontweight="bold")
    dk.box(a, 0.3, 4.6, 2.2, 1.0, "cell 1\n(k1, volume average)", "#cfe3f5", size=7); dk.box(a, 7.5, 4.6, 2.2, 1.0, "cell 2\n(k2)", "#cfe3f5", size=7)
    dk.resistor(a, 2.5, 5.0, 5.1, "half cell 1"); dk.resistor(a, 5.0, 7.5, 5.1, "half cell 2")
    a.text(5, 3.0, "harmonic mean of the half-cell resistances;\nmaterial of a cell = volume average of what it holds\n(the tiled-conductivity method)", ha="center", fontsize=8)
    a.text(5, 0.8, "steady state only; the cost grows with layers × cells", ha="center", fontsize=8, style="italic")
    dk.save(fig, path, "3D solid: slabs, a via as a rod, a block, the conductance of two cells (theory section 4)")


def lumped_rings(path):
    """!
    @brief Draw the rings of the Lumped model: the distance of every cell to the footprint cut in geometric rings, the resistor chain with the vertical and ambient conductances, and the superposition of heaters.
    @param path Output file.
    @return None.
    """
    from scipy import ndimage
    fig, axs = dk.canvas(15, 5.0, 1, 3, ratios=[1, 1.2, 1])
    n = 80
    m = np.ones((n, n), bool)
    m[34:46, 28:52] = False                                         # the footprint (distance 0 inside)
    d = ndimage.distance_transform_edt(m)
    edges = np.array([0, 1, 2.5, 5, 9, 15, 25, 45])
    ring = np.digitize(d, edges[1:])
    a = axs[0]
    a.imshow(ring, cmap="YlOrBr_r", origin="lower")
    a.contour(d, levels=edges[1:], colors="k", linewidths=0.5)
    a.text(40, 40, "heater\n(ring 0)", ha="center", va="center", fontsize=8)
    a.set_title("rings by distance from the footprint", fontsize=9)
    a = axs[1]
    a.set_xlim(0, 12); a.set_ylim(0, 6)
    dk.box(a, 0.2, 2.6, 1.4, 0.8, "ring 0", "#f4b6b6", size=8)
    for k in range(1, 4):
        dk.resistor(a, 1.6 + 2.6 * (k - 1), 3.4 + 2.6 * (k - 1), 3.0, f"R{k}")
        dk.box(a, 3.4 + 2.6 * (k - 1), 2.6, 1.0 if k < 3 else 0.9, 0.8, f"ring {k}", "#f3d9b1", size=8)
        dk.arrow(a, 3.9 + 2.6 * (k - 1), 2.6, 3.9 + 2.6 * (k - 1), 1.3, color=dk.BLUE)
    a.text(6, 0.7, "each ring: vertical Gz and ambient conductance to ground\n(vias, heatsinks, edges enter at their real positions)", ha="center", fontsize=8)
    a.text(6, 5.3, "lateral resistance between ring means:\nheat crosses the offset contours", ha="center", fontsize=8.5, fontweight="bold")
    a = axs[2]
    a.set_xlim(0, 10); a.set_ylim(0, 8)
    a.text(5, 7.4, "superposition", ha="center", fontsize=9, fontweight="bold")
    for x, c in ((2.4, "#f4b6b6"), (7.2, "#f4b6b6")):
        a.add_patch(Circle((x, 5.0), 1.2, fc=c, ec="k"))
    a.text(2.4, 5.0, "θ_A", ha="center"); a.text(7.2, 5.0, "θ_B", ha="center")
    a.text(4.8, 5.0, "+", fontsize=16, ha="center", va="center")
    dk.arrow(a, 5, 3.6, 5, 2.6)
    a.text(5, 1.6, "linear problem: one small dense system per heater,\nthe board is the sum of the heaters", ha="center", fontsize=8)
    dk.save(fig, path, "Lumped: rings, the resistor chain, superposition of the heaters (theory section 5)")


def analytic_modes(path):
    """!
    @brief Draw the cosine modes of the Analytic model, the convergence of the series for a rectangular source, and the tiles of the local via and heatsink corrections.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(15, 5.0, 1, 3)
    x = np.linspace(0, 1, 120)
    X, Y = np.meshgrid(x, x)
    sub = axs[0].inset_axes([0, 0, 1, 1]); axs[0].axis("off")
    sub.axis("off")
    for k, (m, n) in enumerate(((1, 0), (0, 1), (1, 1), (2, 1))):
        ia = axs[0].inset_axes([0.02 + 0.5 * (k % 2), 0.55 - 0.5 * (k // 2), 0.44, 0.40])
        ia.imshow(np.cos(m * np.pi * X) * np.cos(n * np.pi * Y), cmap="RdBu_r", origin="lower")
        ia.set_xticks([]); ia.set_yticks([]); ia.set_title(f"mode ({m},{n})", fontsize=8)
    axs[0].text(0.5, 1.06, "the board as a sum of cosines (insulated edges)", ha="center", fontsize=9, fontweight="bold", transform=axs[0].transAxes)
    axs[0].text(0.5, -0.04, "each mode decouples: a·(g + k·λ_mn) = q_mn", ha="center", fontsize=8, transform=axs[0].transAxes)
    a = axs[1]
    a.axis("on")
    src = (x > 0.4) & (x < 0.6)
    for M, col in ((2, "#1f77b4"), (5, "#2ca02c"), (20, "#d62728")):
        th = np.zeros_like(x)
        for m in range(M + 1):
            q = (1 if m == 0 else 2 * (np.sin(m * np.pi * 0.6) - np.sin(m * np.pi * 0.4)) / (m * np.pi))
            th += q * np.cos(m * np.pi * x) / (1.0 + 400 * (m * np.pi / 10) ** 2 / 100)
        a.plot(x, th, color=col, label=f"{M + 1} modes")
    a.legend(fontsize=8); a.set_xlabel("position along the board (fraction)"); a.set_ylabel("temperature rise (arbitrary units)")
    a.set_title("the series for a strip source: few modes, the smooth part\n(illustrative shape)", fontsize=9)
    a.grid(alpha=0.3)
    a = axs[2]
    a.set_xlim(0, 10); a.set_ylim(0, 8)
    for i in range(6):
        for j in range(6):
            col = "#f3d9b1"
            if (i, j) == (2, 3): col = "#cfe3f5"
            if (i, j) in ((4, 1), (4, 2)): col = "#b9c4cc"
            a.add_patch(Rectangle((1 + 1.3 * i, 0.8 + 1.0 * j), 1.3, 1.0, fc=col, ec="grey", lw=0.6))
    a.text(3.6, 4.4, "via", ha="center", fontsize=8); a.text(6.9, 2.4, "heatsink", ha="center", fontsize=7)
    a.text(5, 7.4, "tiles: the local corrections", ha="center", fontsize=9, fontweight="bold")
    a.text(5, 0.1, "uniform solution + Green-function (Woodbury) update\nonly on the tiles with a via or a heatsink", ha="center", fontsize=8)
    dk.save(fig, path, "Analytic: modes, convergence of the series, tiles for vias and heatsinks (theory section 6)")


def theta_method(path):
    """!
    @brief Plot the amplification factor of the theta method against the product of rate and step (why implicit Euler and Crank-Nicolson are stable), and the geometric stages of the time step.
    @param path Output file.
    @return None.
    """
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.8))
    z = np.logspace(-2, 3, 400)
    a = axs[0]
    a.semilogx(z, np.exp(-z), "k", lw=2, label="exact exp(−λΔt)")
    a.semilogx(z, 1 / (1 + z), color="#1f77b4", label="implicit Euler (ϑ = 1)")
    a.semilogx(z, (1 - 0.5 * z) / (1 + 0.5 * z), color="#d62728", label="Crank-Nicolson (ϑ = 1/2)")
    a.semilogx(z, 1 - z, "--", color="grey", label="explicit Euler (ϑ = 0): unstable above 2")
    a.axhline(0, color="k", lw=0.5); a.axhline(-1, color="k", lw=0.5, ls=":")
    a.set_ylim(-1.5, 1.1)
    a.set_xlabel("λ Δt (rate of the mode × time step)"); a.set_ylabel("factor per step")
    a.set_title("every mode is multiplied by a factor of modulus below 1\n(implicit Euler: robust; Crank-Nicolson: second order, rings at large steps)", fontsize=9)
    a.legend(fontsize=8); a.grid(alpha=0.3, which="both")
    a = axs[1]
    r, per = 3, 4
    dts = [0.01 * r ** j for j in range(10)]
    t = 0.0
    for j, dt in enumerate(dts):
        for _ in range(per):
            a.plot([t, t + dt], [j, j], "-", color="#1f77b4", lw=3)
            a.plot([t, t], [j - 0.2, j + 0.2], "k-", lw=0.8)
            t += dt
    a.set_xscale("log"); a.set_xlim(0.008, t * 1.5)
    a.set_xlabel("time (arbitrary units)"); a.set_ylabel("stage j")
    a.set_title("step responses: stages with Δt_j = Δt₀ r^j (r = 3, four steps per stage)\none LU factorisation per stage; fine steps early, coarse late", fontsize=9)
    a.grid(alpha=0.3, which="both")
    dk.save(fig, path, "Time stepping: the theta method and the geometric stages (theory section 2)")


def heat_transfer(path):
    """!
    @brief Draw the heat transfer coefficients: a board face losing heat by convection and radiation, the way each depends on the temperature (illustrative shapes) and the Picard loop that finds them.
    @param path Output file.
    @return None.
    """
    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(15, 5.0))
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1.1, 1])
    a = fig.add_subplot(gs[0]); a.axis("off"); a.set_xlim(0, 10); a.set_ylim(0, 8)
    dk.layer(a, 1, 2.0, 8, 0.5, dk.FR4, "board", size=9)
    for x in (2.5, 5, 7.5):
        dk.arrow(a, x, 2.7, x, 5.2, color=dk.HEAT)
        dk.arrow(a, x + 0.5, 2.7, x + 0.9, 5.4, color="#e377c2", style="->")
    a.text(5, 6.2, "convection (arrows up)", ha="center", fontsize=8.5, color=dk.HEAT)
    a.text(5, 5.7, "radiation (to the surroundings)", ha="center", fontsize=8.5, color="#e377c2")
    a.text(5, 1.0, "h_face = h_convection + h_radiation\nper face, from the mean face temperature", ha="center", fontsize=8.5)
    a.text(5, 7.4, "one coefficient per face", ha="center", fontsize=9, fontweight="bold")
    a = fig.add_subplot(gs[1])
    dT = np.linspace(1, 80, 100)
    a.plot(dT, 1.3 * dT ** 0.25, color=dk.HEAT, label="natural convection ∝ ΔT^¼")
    Ta = 298.15
    Ts = Ta + dT
    a.plot(dT, 0.9 * 5.67e-8 * (Ts ** 2 + Ta ** 2) * (Ts + Ta), color="#e377c2", label="radiation, emissivity 0.9")
    a.set_xlabel("face temperature above the ambient (K)"); a.set_ylabel("h (W/m²K)")
    a.set_title("both grow with the temperature (illustrative values):\na constant h overstates the rise at high power and understates it at low power", fontsize=9)
    a.legend(fontsize=8); a.grid(alpha=0.3)
    a = fig.add_subplot(gs[2]); a.axis("off"); a.set_xlim(0, 10); a.set_ylim(0, 8)
    dk.box(a, 2.5, 6.4, 5, 1.0, "guess h per face", "#cfe3f5")
    dk.box(a, 2.5, 4.4, 5, 1.0, "solve the board (any model)", "#cfe3f5")
    dk.box(a, 2.5, 2.4, 5, 1.0, "mean face temperature → new h", "#cfe3f5")
    dk.box(a, 2.5, 0.4, 5, 1.0, "h changed less than the tolerance?\nyes: done", "#e8e8e8", size=7)
    for y in (6.4, 4.4, 2.4):
        dk.arrow(a, 5, y, 5, y - 0.6)
    a.annotate("", (8.4, 6.9), (8.4, 0.9), arrowprops={"arrowstyle": "->", "connectionstyle": "arc3,rad=-0.4", "color": "grey"})
    a.text(9.3, 4, "no: again", rotation=90, va="center", fontsize=8, color="grey")
    a.text(5, 7.7, "Picard loop (outside the models)", ha="center", fontsize=9, fontweight="bold")
    dk.save(fig, path, "Heat transfer coefficients: two mechanisms, their growth, the loop (theory section 8)")


def part_runaway(path):
    """!
    @brief Plot the fixed point of the power that depends on temperature (stable intersection and thermal runaway), with the series chain of the junction above the pad.
    @param path Output file.
    @return None.
    """
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1, 1.2, 1.2]})
    a = axs[0]; a.axis("off"); a.set_xlim(0, 10); a.set_ylim(0, 8)
    dk.layer(a, 1, 1.0, 8, 0.35, CU); dk.layer(a, 1, 1.35, 8, 1.0, dk.FR4)
    dk.box(a, 3.0, 2.6, 4, 0.9, "package", "#d9d9d9"); dk.box(a, 4.2, 3.6, 1.6, 0.6, "junction", "#f4b6b6", size=7)
    dk.arrow(a, 5, 3.6, 5, 2.4, color=dk.HEAT, label="")
    a.text(5.4, 2.0, "P θ", fontsize=8, color=dk.HEAT)
    a.text(5, 5.2, "Tj = T_pad,max + P θ_part", ha="center", fontsize=9)
    a.text(5, 0.2, "θ must be junction-to-pad:\nθJA and θJB would count the\nmaker's board twice", ha="center", fontsize=8, va="top")
    a.text(5, 7.4, "worst case: all the power enters the board", ha="center", fontsize=8.5, fontweight="bold")
    P0, alpha, Ta = 10.0, 0.004, 25.0
    T = np.linspace(25, 260, 200)
    for a_, R, ttl in ((axs[1], 10.0, "stable: αR P₀ < 1"), (axs[2], 30.0, "runaway: αR P₀ ≥ 1")):
        P_of_T = P0 * (1 + alpha * (T - 25))
        a_.plot(T, P_of_T, color=dk.HEAT, label="power P(Tj) = P₀[1 + α(Tj − 25)]")
        a_.plot(T, (T - Ta) / R, color=dk.BLUE, label="what the board removes: (Tj − T_amb)/R")
        if alpha * R * P0 < 1:
            Tf = Ta + R * P0 / (1 - alpha * R * P0) * 1.0
            a_.plot(Tf, (Tf - Ta) / R, "ko"); a_.annotate("fixed point\nΔT = P₀R/(1 − αP₀R)", (Tf, (Tf - Ta) / R), (Tf - 110, (Tf - Ta) / R + 9), fontsize=8, arrowprops={"arrowstyle": "->"})
        else:
            a_.text(40, 22, "no intersection: the power grows\nfaster than the board removes it", fontsize=8)
        a_.set_ylim(0, 30); a_.set_xlabel("junction temperature (°C)"); a_.set_ylabel("power (W)")
        a_.set_title(ttl + " (illustrative numbers)", fontsize=9); a_.legend(fontsize=7, loc="lower right"); a_.grid(alpha=0.3)
    dk.save(fig, path, "Parts: the junction in series, and the fixed point of a power that grows with temperature (theory section 9)")


def profile_decision(path):
    """!
    @brief Draw the power profile logic: a square wave with the response of the hottest point, the oscillation in °C, and the average-or-resolve decision against the shared threshold.
    @param path Output file.
    @return None.
    """
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.8))
    t = np.linspace(0, 6, 1200)
    per, duty = 1.0, 0.3
    P = ((t % per) < duty * per).astype(float)
    tau = 0.8
    dt = t[1] - t[0]
    th = np.zeros_like(t)
    for i in range(1, len(t)):
        th[i] = th[i - 1] + dt * (P[i] - th[i - 1]) / tau
    a = axs[0]
    a.plot(t, P, color=dk.HEAT, label="power P(t): square wave")
    a.plot(t, th, color=dk.BLUE, label="hottest point (first-order response)")
    a.axhline(duty, color="grey", ls="--", lw=0.8, label="average power")
    a.set_xlabel("time (periods)"); a.set_ylabel("arbitrary units"); a.legend(fontsize=7)
    a.set_title("the temperature oscillates around the average; the start is the steady\nstate of the average power (illustrative first-order response)", fontsize=8.5)
    a.grid(alpha=0.3)
    a = axs[1]
    osc = np.array([0.15, 0.3, 0.45, 1.2, 2.6, 4.0])
    cum = np.cumsum(osc)
    thr = 1.0
    cols = ["#2ca02c" if c <= thr else "#d62728" for c in cum]
    a.bar(range(len(osc)), osc, color=cols)
    a.plot(range(len(osc)), cum, "ko-", label="cumulative oscillation")
    a.axhline(thr, color="k", ls="--"); a.text(5.2, thr + 0.1, "threshold (1 °C default)", ha="right", fontsize=8)
    a.set_xlabel("heaters sorted by oscillation"); a.set_ylabel("oscillation (°C), illustrative")
    a.set_title("green: averaged (smallest first while the budget lasts)\nred: resolved in time", fontsize=8.5)
    a.legend(fontsize=7); a.grid(alpha=0.3)
    a = axs[2]; a.axis("off"); a.set_xlim(0, 10); a.set_ylim(0, 8)
    for k, (per_, c) in enumerate(((2, "#cfe3f5"), (3, "#f3d9b1"))):
        for j in range(12 // per_):
            a.add_patch(Rectangle((1 + j * per_ * 0.7, 6.3 - 1.4 * k), per_ * 0.7 * 0.5, 0.7, fc=c, ec="k", lw=0.5))
    a.text(5, 7.6, "window = least common multiple of the periods", ha="center", fontsize=9, fontweight="bold")
    a.text(5, 3.0, "windows repeat until peak and valley change\nby less than 0.1 °C; step Δt = a tenth of the\nshortest stretch; the power of a step is\nthe exact mean of the profile over the step", ha="center", fontsize=8.5)
    a.text(5, 0.6, "one-shot tables are always resolved", ha="center", fontsize=8, style="italic")
    dk.save(fig, path, "Power profiles: the response, the average-or-resolve decision, the window (theory section 10)")


def metal_block(path):
    """!
    @brief Draw the metal block of theory section 7: heat enters only where the block overlaps copper, the laminate in series elsewhere, the fin efficiency, and the Schur complement tile idea of the Lumped and Analytic equivalents.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(15, 5.0, 1, 3)
    a = axs[0]; a.set_xlim(0, 10); a.set_ylim(0, 8)
    dk.layer(a, 0.5, 1.5, 9, 0.3, CU); dk.layer(a, 0.5, 1.8, 9, 0.7, dk.FR4)
    dk.layer(a, 3.0, 2.5, 4.0, 0.2, "#f3d9b1", "interface sheet", size=6)
    dk.layer(a, 3.0, 2.7, 4.0, 1.0, dk.METAL, "metal block", size=8)
    for x in (3.4, 4.2, 5.0, 5.8, 6.5):
        dk.layer(a, x, 3.7, 0.2, 1.4, dk.METAL)
    dk.arrow(a, 5, 1.5, 5, 0.6, color=dk.HEAT)
    a.text(5, 7.4, "block on the board", ha="center", fontsize=9, fontweight="bold")
    a.text(5, 6.2, "copper under the block: the heat goes up through\nthe interface; elsewhere through the laminate\n(intersection of the planes)", ha="center", fontsize=7.5)
    a = axs[1]; a.set_xlim(0, 10); a.set_ylim(0, 8)
    a.text(5, 7.4, "plate fin", ha="center", fontsize=9, fontweight="bold")
    dk.layer(a, 3.0, 0.8, 0.5, 5.0, dk.METAL)
    a.plot([3.25, 3.25], [0.8, 5.8], "k:", lw=0.8)
    for y, w in ((1.0, 1.0), (2.2, 0.8), (3.4, 0.55), (4.6, 0.35)):
        dk.arrow(a, 3.5, y + 0.2, 3.5 + w * 2.0, y + 0.2, color=dk.HEAT, width=1.2)
    a.text(5.8, 0.4, "heat to the air per height falls\nwith the temperature along the fin", ha="center", fontsize=8)
    a.text(7.4, 4.0, "η = tanh(mL)/(mL)", fontsize=11)
    a.text(7.4, 3.2, "no channel choking between\nthe fins (a warning)", fontsize=8)
    a = axs[2]; a.set_xlim(0, 10); a.set_ylim(0, 8)
    a.text(5, 7.4, "Lumped / Analytic: keep the lateral conduction", ha="center", fontsize=9, fontweight="bold")
    dk.box(a, 0.5, 4.8, 3.9, 1.4, "Lumped: the block is one\nmore layer of the ring network", "#cfe3f5", size=8)
    dk.box(a, 5.6, 4.8, 3.9, 1.4, "Analytic: Schur complement\non the tile graph of the\nGreen-function correction", "#cfe3f5", size=8)
    a.text(5, 2.8, "an equivalent coefficient (isothermal block) is 8 to 31 % off:\nthe block spreads the heat of the pad centre to the whole pad", ha="center", fontsize=8.5)
    a.text(5, 1.0, "means 2.0 % / 1.1 % (Lumped / Analytic) against the FVM", ha="center", fontsize=8, style="italic")
    dk.save(fig, path, "Metal blocks: the block on the board, a plate fin, the equivalents of the Lumped and Analytic models (theory section 7)")


def foster_chain(path):
    """!
    @brief Plan: draw the package's thermal impedance Zth(t), the Foster RC chain that reproduces it, and a pulse train read from it (roadmap 1.11).
    @param path Output file.
    @return None.
    """
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1.2, 1, 1.2]})
    t = np.logspace(-4, 2, 300)
    R = [0.5, 1.0, 2.0]
    tau = [0.003, 0.1, 5.0]
    Z = sum(r * (1 - np.exp(-t / ta)) for r, ta in zip(R, tau))
    a = axs[0]
    a.loglog(t, Z, "k", lw=2, label="Zth(t) = Σ Ri (1 − e^(−t/τi))")
    for r, ta, c in zip(R, tau, ("#d62728", "#2ca02c", "#1f77b4")):
        a.loglog(t, r * (1 - np.exp(-t / ta)), color=c, lw=1, ls="--", label=f"stage τ = {ta} s")
    a.set_xlabel("time (s)"); a.set_ylabel("K/W (illustrative)"); a.legend(fontsize=7); a.grid(alpha=0.3, which="both")
    a.set_title("what the datasheet curve is", fontsize=9)
    a = axs[1]; a.axis("off"); a.set_xlim(0, 10); a.set_ylim(0, 8)
    a.text(5, 7.4, "Foster chain (series of R ∥ C)", ha="center", fontsize=9, fontweight="bold")
    for k in range(3):
        x = 0.8 + 2.9 * k
        a.plot([x, x + 0.4], [5.0, 5.0], "k"); a.plot([x + 0.4, x + 0.4], [4.2, 5.8], "k"); a.plot([x + 2.0, x + 2.0], [4.2, 5.8], "k")
        a.plot([x + 0.4, x + 2.0], [5.8, 5.8], "k"); a.plot([x + 0.4, x + 2.0], [4.2, 4.2], "k")
        a.add_patch(Rectangle((x + 0.8, 5.6), 0.8, 0.4, fc="w", ec="k")); a.text(x + 1.2, 6.2, f"R{k + 1}", ha="center", fontsize=8)
        a.plot([x + 0.8, x + 0.8, x + 1.6, x + 1.6], [4.2, 3.6, 3.6, 4.2], "k", lw=0)
        a.plot([x + 1.0, x + 1.0], [3.5, 4.0], "k"); a.plot([x + 1.4, x + 1.4], [3.5, 4.0], "k")
        a.text(x + 1.2, 3.0, f"C{k + 1}", ha="center", fontsize=8)
        a.plot([x + 2.0, x + 2.9], [5.0, 5.0], "k")
    a.text(5, 1.6, "stages are mathematical, not physical places;\nthe sum reproduces the curve at the junction only", ha="center", fontsize=8)
    a = axs[2]
    tt = np.linspace(0, 6, 1200)
    P = ((tt % 2.0) < 0.5).astype(float)
    th = np.zeros_like(tt)
    dt = tt[1] - tt[0]
    for i in range(1, len(tt)):
        th[i] = th[i - 1] + dt * (P[i] - th[i - 1]) / 1.2
    a.plot(tt, P, color=dk.HEAT, label="power pulses"); a.plot(tt, th, color=dk.BLUE, label="ΔTj = Zth ∗ P (convolution)")
    a.set_xlabel("time (arbitrary)"); a.legend(fontsize=8); a.grid(alpha=0.3)
    a.set_title("check of the time simulation: ΔTj = Zth(tp, D) · P (illustrative)", fontsize=9)
    dk.save(fig, path, "Planned: junction impedance Zth(t), the Foster chain and a pulse train (roadmap 1.11)")


def heatsink_scaling(path):
    """!
    @brief Plan: draw the heatsink scenarios: the forced-convection factors on θSA (1, 0.31, 0.18, 0.10 at 0, 1, 2.5, 5 m/s), the natural convection scaling with the temperature rise, and the channel between fins (roadmap, heatsink air flow).
    @param path Output file.
    @return None.
    """
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.8), gridspec_kw={"width_ratios": [1, 1, 1.1]})
    a = axs[0]
    v = np.array([0, 1, 2.5, 5]); f = np.array([1, 0.31, 0.18, 0.10])
    a.plot(v, f, "o-", color=dk.BLUE)
    for x, y in zip(v, f): a.text(x + 0.1, y + 0.03, f"{y:g}", fontsize=8)
    a.set_xlim(-0.3, 5.8); a.set_xlabel("air speed (m/s)"); a.set_ylabel("θSA(v) / θSA(natural)"); a.set_title("forced convection: factor from the volumetric guide\n(an estimate: 15 % large heatsink, up to 50 % small)", fontsize=9); a.grid(alpha=0.3)
    a = axs[1]
    dT = np.linspace(10, 80, 50)
    a.plot(dT, (dT / 40) ** -0.25, color=dk.HEAT)
    a.set_xlabel("heatsink rise above the ambient (K)"); a.set_ylabel("θSA / θSA(40 K reference), illustrative")
    a.set_title("natural convection: θSA ∝ ΔT^−0.25\nfrom a reference rise", fontsize=9); a.grid(alpha=0.3)
    a = axs[2]; a.axis("off"); a.set_xlim(0, 10); a.set_ylim(0, 8)
    dk.layer(a, 0.8, 1.5, 8.4, 0.5, dk.METAL)
    for k, x in enumerate((1.4, 2.8, 4.2, 5.6, 7.0, 8.4)):
        dk.layer(a, x - 0.1, 2.0, 0.2, 3.2, dk.METAL)
    a.annotate("", (2.9, 6.0), (1.5, 6.0), arrowprops={"arrowstyle": "<->"}); a.text(2.2, 6.3, "pitch", ha="center", fontsize=8)
    a.text(5, 7.4, "from the geometry: channel between fins", ha="center", fontsize=9, fontweight="bold")
    a.text(5, 0.5, "too close: the boundary layers meet and choke the flow;\ntoo far: less area. Elenbaas / Bar-Cohen and Rohsenow\ncorrelation: not modelled or validated yet", ha="center", fontsize=8)
    dk.save(fig, path, "Planned: heatsink scenarios, air speed, temperature rise, fin spacing (roadmap, heatsink air flow)")


def virtual_jedec(path):
    """!
    @brief Plan: draw the virtual JEDEC test (the datasheet's own board built in the program, to predict θJA, ΨJT and ΨJB and to recover a missing resistance) and the known-power reference of the Power calculator.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(15, 5.0, 1, 2)
    a = axs[0]; a.set_xlim(0, 12); a.set_ylim(0, 8)
    dk.box(a, 0.1, 5.4, 2.4, 1.2, "datasheet board\n(layers, copper,\nsize, still air)", dk.COPPER, size=8)
    dk.box(a, 3.2, 5.4, 2.4, 1.2, "build it in\nthe program", "#cfe3f5", size=8)
    dk.box(a, 6.3, 5.4, 2.4, 1.2, "run the models", "#cfe3f5", size=8)
    dk.box(a, 9.4, 5.4, 2.4, 1.2, "θJA, ΨJT, ΨJB", "#f4b6b6", size=8)
    for x in (2.5, 5.6, 8.7): dk.arrow(a, x, 6.0, x + 0.65, 6.0)
    dk.box(a, 6.6, 2.6, 5.2, 1.2, "compare with the datasheet\n(done for CSD17308Q3 and a 2s2p QFN)", "#e8e8e8", size=8)
    dk.arrow(a, 10.6, 5.4, 10.0, 3.9)
    dk.box(a, 0.2, 2.6, 5.2, 1.2, "or: θJA of a stated board\n→ recover a missing package resistance", "#e8e8e8", size=8)
    dk.arrow(a, 7.5, 5.4, 4.0, 3.9)
    a.text(6, 7.4, "virtual JEDEC test", ha="center", fontsize=9, fontweight="bold")
    a.text(6, 1.2, "more datasheet cases need their boards described", ha="center", fontsize=8, style="italic")
    a = axs[1]; a.set_xlim(0, 10); a.set_ylim(0, 8)
    import matplotlib.pyplot as plt
    ins = a.inset_axes([0.1, 0.25, 0.84, 0.58]); a.axis("off")
    P = np.linspace(0, 1, 20)
    ins.plot(P, 60 * P, color=dk.BLUE, label="model (copper unknown)")
    ins.plot(P, 75 * P, color=dk.HEAT, label="board (true)")
    ins.plot([0.5], [37.5], "ko"); ins.plot([0.5], [30], "ks")
    ins.annotate("reading at a\nknown power", (0.5, 37.5), (0.05, 55), fontsize=8, arrowprops={"arrowstyle": "->"})
    ins.set_xlabel("power (arbitrary)"); ins.set_ylabel("rise (K, illustrative)"); ins.legend(fontsize=7); ins.grid(alpha=0.3)
    a.text(5, 7.4, "known-power reference (calculator)", ha="center", fontsize=9, fontweight="bold", transform=a.transData)
    a.text(5, 0.0, "the same reading at a known power scales the model line:\n±5 % with ±1 K of reading error against −19 to −27 % without", ha="center", fontsize=8, transform=a.transData)
    dk.save(fig, path, "Planned: the virtual JEDEC test and the known-power reference (roadmap, docs/calculators.md 2.4)")


def import_to_power(path):
    """!
    @brief Plan: draw the import of a KiCad board and a BOM (power by designator onto footprints) and the passive areas as component types (cooled area, fixed-temperature contact, material patch).
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(15, 5.0, 1, 2)
    a = axs[0]; a.set_xlim(0, 12); a.set_ylim(0, 8)
    dk.box(a, 0.2, 5.6, 2.8, 1.2, ".kicad_pcb\n(outline, zones, tracks,\nvias, stack-up, footprints)", "#cfe3f5", size=7.5)
    dk.box(a, 0.2, 3.4, 2.8, 1.2, "BOM / CSV\nreference, power_w,\nθ, tj_max", "#f3d9b1", size=7.5)
    dk.box(a, 4.4, 4.5, 2.6, 1.4, "match by designator\n(U1, Q3, …)", "#e8e8e8", size=8)
    dk.box(a, 8.4, 4.5, 3.2, 1.4, "Problem: board, copper per\nlayer, vias, parts with power", "#f4b6b6", size=8)
    dk.arrow(a, 3.0, 6.2, 4.4, 5.5); dk.arrow(a, 3.0, 4.0, 4.4, 4.9); dk.arrow(a, 7.0, 5.2, 8.4, 5.2)
    a.text(6, 7.4, "board and power list", ha="center", fontsize=9, fontweight="bold")
    a.text(6, 2.2, "pure-Python S-expression parser, no KiCad needed;\nthe power can also come from a circuit simulation", ha="center", fontsize=8)
    a = axs[1]; a.set_xlim(0, 12); a.set_ylim(0, 8)
    a.add_patch(Rectangle((0.5, 1.5), 11, 5, fc=dk.FR4, ec="k"))
    a.add_patch(Rectangle((1.2, 4.2), 3.2, 1.7, fc="#bfe3ff", ec="k", ls="--")); a.text(2.8, 5.05, "cooled area\n(extra h)", ha="center", fontsize=8)
    a.add_patch(Rectangle((5.2, 4.2), 2.2, 1.7, fc="#b9c4cc", ec="k")); a.text(6.3, 5.05, "contact:\nfixed T", ha="center", fontsize=8)
    a.add_patch(Rectangle((8.2, 4.2), 2.6, 1.7, fc="#f4a6a6", ec="k")); a.text(9.5, 5.05, "material\npatch", ha="center", fontsize=8)
    a.text(6, 7.4, "passive areas as component types", ha="center", fontsize=9, fontweight="bold")
    a.text(6, 0.7, "a component library fills θJC, θJB, ψJB, size and mass\nby family or part number (processor presets with lid and paste)", ha="center", fontsize=8)
    dk.save(fig, path, "Planned: board and power list import, passive areas, component library (roadmap)")


def multigrid(path):
    """!
    @brief Plan: draw the V-cycle of a multigrid solver (smooth, restrict, solve coarse, prolong, correct), the optional solver that pays above about 500 000 unknowns (roadmap, solvers).
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(15, 4.6, 1, 2, ratios=[1.4, 1])
    a = axs[0]; a.set_xlim(0, 12); a.set_ylim(0, 8)
    pts = [(1, 6.5), (3, 4.8), (5, 3.1), (6, 1.4), (7, 3.1), (9, 4.8), (11, 6.5)]
    for p, q in zip(pts[:-1], pts[1:]):
        dk.arrow(a, p[0], p[1], q[0], q[1], color="#1f77b4" if q[1] < p[1] else "#d62728")
    for k, (x, y) in enumerate(pts):
        a.plot(x, y, "ko")
    labs = ["fine grid\nsmooth", "restrict the residual", "", "coarse grid:\nsolve exactly", "", "prolong the correction", "smooth,\nfinished"]
    for (x, y), t in zip(pts, labs):
        a.text(x, y + 0.5, t, ha="center", fontsize=7.5)
    a.text(6, 7.6, "V-cycle (algebraic multigrid, e.g. pyamg)", ha="center", fontsize=9, fontweight="bold")
    a = axs[1]; a.set_xlim(0, 10); a.set_ylim(0, 8)
    a.text(5, 7.3, "when it pays", ha="center", fontsize=9, fontweight="bold")
    a.text(5, 4.6, "measured on the example board:\nabove about 500 000 unknowns\n987 000 unknowns: 8.0 s against 12.8 s for CG;\nthe direct solver does not fit in memory", ha="center", fontsize=8.5)
    a.text(5, 1.4, "optional dependency, chosen above a threshold;\nall solvers agree to 1e-8 K", ha="center", fontsize=8, style="italic")
    dk.save(fig, path, "Planned: multigrid, the V-cycle and when it pays (roadmap, solvers)")


def layered_idealisation(path):
    """!
    @brief Draw the layered idealisation of theory section 1.2 on a board section: each copper layer one node, the gap a 1D resistance, outer faces to the air, with the heat balance.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(15, 5.0, 1, 2, ratios=[1.3, 1])
    a = axs[0]; a.set_xlim(0, 12); a.set_ylim(0, 8)
    ys = [5.4, 3.4, 1.4]
    for k, y in enumerate(ys):
        dk.layer(a, 0.5, y, 8, 0.3, CU, f"copper {k + 1}: one node, sheet conductance S = k t", size=7)
        if k < 2:
            dk.layer(a, 0.5, y - 1.6, 8, 1.6, dk.FR4)
            dk.resistor(a, 8.7, 10.5, y - 0.7, "gap: d/k_th", size=7)
            a.plot([8.7, 8.7], [y, y - 0.7], "k", lw=0.8); a.plot([8.7, 8.7], [y - 1.6 + 0.3 + 0.3, y - 0.7], "k", lw=0.8)
    dk.arrow(a, 3, 5.9, 3, 7.0, color=dk.HEAT); a.text(3.5, 6.7, "h_top", fontsize=8, color=dk.HEAT)
    dk.arrow(a, 3, 1.4, 3, 0.4, color=dk.HEAT); a.text(3.5, 0.6, "h_bottom", fontsize=8, color=dk.HEAT)
    a.text(6, 7.7, "section: nodes, gaps and faces", ha="center", fontsize=9, fontweight="bold")
    a = axs[1]; a.set_xlim(0, 10); a.set_ylim(0, 8)
    a.text(5, 7.3, "what it assumes", ha="center", fontsize=9, fontweight="bold")
    a.text(5, 5.0, "no gradient across a copper layer;\nthe gap is a 1D resistance (no spreading inside it:\n0.4 to 2 % against the 3D solid);\nthe air coefficients act on the outer layer node", ha="center", fontsize=8.5)
    a.text(5, 2.0, "energy balance: Σ h∫θ dA + edge losses = Σ P\nevery result reports it", ha="center", fontsize=8.5, fontweight="bold")
    dk.save(fig, path, "The layered idealisation: nodes, gaps, faces and the energy balance (theory section 1.2)")


def main():
    """!
    @brief Draw and save every figure of this folder.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    for k, (name, fn) in enumerate((("layered_idealisation", layered_idealisation), ("fvm_cell", fvm_cell), ("fdm_nodes", fdm_nodes),
                                    ("solid3d_slabs", solid3d), ("lumped_rings", lumped_rings), ("analytic_modes", analytic_modes),
                                    ("theta_method", theta_method), ("heat_transfer", heat_transfer), ("part_runaway", part_runaway),
                                    ("profile_decision", profile_decision), ("metal_block", metal_block),
                                    ("foster_chain_planned", foster_chain), ("heatsink_scaling_planned", heatsink_scaling),
                                    ("virtual_jedec_planned", virtual_jedec), ("import_to_power_planned", import_to_power),
                                    ("multigrid_planned", multigrid)), start=1):
        fn(OUT / f"fig_{k:02d}_{name}.png")


if __name__ == "__main__":
    main()
