"""!
@file make_diagrams.py
@brief Pictures for the theory (folder research/theory) of every model of `docs/theory.md` and for the models and analyses that are planned (`docs/roadmap.md`): what each equation or method does, drawn.
@details Pure drawing and textbook formulas (no program, no data); the numbers quoted are those of `docs/theory.md`, `docs/roadmap.md` and `docs/research.md`. Curves that are only
         illustrative (shape, not value) say so in their caption. Writes figures/fig_01 to fig_30.
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
    a.text(5, 0.8, "steady state only; the cost grows with layers × cells;\nrefused above 250 000 unknowns (the other models still run)", ha="center", fontsize=8, style="italic")
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
    a.text(6, 0.7, "each ring: vertical Gz and ambient conductance to ground\n(vias, heatsinks, edges enter at their real positions);\nrings narrower than a cell are merged", ha="center", fontsize=8)
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
    a.plot(dT, 1.3 * dT ** 0.25, color=dk.HEAT, label="natural convection ∝ ΔT^¼ (general form; laminar optional)")
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
    dk.save(fig, path, "The virtual JEDEC test (done for two datasheet boards, more cases planned) and the known-power reference (planned)  (roadmap, docs/calculators.md 2.1 and 2.4)")


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
    a.text(6, 0.7, "planned: a component library by part number (θJC, θJB, ψJB, size, mass; processor presets with lid and paste);\nalready in the program: typical θ by package family (library package_theta, Preferences)", ha="center", fontsize=8)
    dk.save(fig, path, "Planned: board and power list import, passive areas, component library by part number (roadmap)")


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
    a.text(5, 5.0, "no gradient across a copper layer;\nthe gap is a 1D resistance (no spreading inside it:\n0.4 to 2 % against the 3D solid);\nthe air coefficients act on the outer layer node;\na one-layer board gets two laminate nodes\nunder its copper (laminate.py)", ha="center", fontsize=8.5)
    a.text(5, 2.0, "energy balance: Σ h∫θ dA + edge losses = Σ P\nevery result reports it", ha="center", fontsize=8.5, fontweight="bold")
    dk.save(fig, path, "The layered idealisation: nodes, gaps, faces and the energy balance (theory section 1.2)")


def air_gap(path):
    """!
    @brief Plot the heat transfer coefficient across an air gap under a block that does not touch the board: conduction of still air k/g plus radiation between parallel faces, with the values of the table of docs/research.md R3 and the gap above which natural convection starts.
    @param path Output file.
    @return None.
    """
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.8), gridspec_kw={"width_ratios": [1, 1.2]})
    a = axs[0]; a.axis("off"); a.set_xlim(0, 10); a.set_ylim(0, 8)
    dk.layer(a, 0.6, 1.0, 8.8, 0.4, CU); dk.layer(a, 0.6, 1.4, 8.8, 0.9, dk.FR4)
    dk.layer(a, 0.6, 3.6, 8.8, 0.9, dk.METAL, "block", size=8)
    dk.layer(a, 3.4, 2.3, 3.2, 1.3, "#f3d9b1", "interface\n(contact)", size=7)
    for x in (1.3, 2.2, 7.4, 8.3):
        dk.arrow(a, x, 3.55, x, 2.35, color=dk.HEAT, width=1.0)
    a.text(1.8, 4.9, "outside the contact:\nthe board face is not insulated", ha="center", fontsize=8)
    a.annotate("", (0.35, 3.6), (0.35, 2.3), arrowprops={"arrowstyle": "<->"}); a.text(0.15, 2.95, "g", fontsize=9, ha="right")
    a.text(5, 7.4, "a gap g between the board and the block", ha="center", fontsize=9, fontweight="bold")
    a.text(5, 6.2, "h = k_air / g  +  h_rad,   h_rad = 4 sigma T^3 / (1/e1 + 1/e2 - 1)", ha="center", fontsize=8)
    a.text(5, 0.3, "natural convection in the gap only above the critical Rayleigh number (1708):\nconduction rules for gaps up to about 7 mm at 60 K and 12 mm at 20 K", ha="center", fontsize=8)
    a = axs[1]
    g = np.linspace(0.3, 14, 200)
    k = 0.028
    a.loglog(g, k / (g * 1e-3), color=dk.BLUE, label="conduction of still air, k/g (k = 0.028 W/mK)")
    a.loglog(g, k / (g * 1e-3) + 6, color=dk.HEAT, label="+ radiation 6 W/m2K (anodised block, emissivity 0.8)")
    a.loglog(g, k / (g * 1e-3) + 0.7, color="#2ca02c", label="+ radiation 0.7 W/m2K (bare aluminium, emissivity 0.1)")
    for gg, hh in ((0.5, 57), (1, 29), (2, 15), (5, 6)):
        a.plot(gg, hh, "ks", ms=6)
        a.annotate(f"{hh}", (gg, hh), (gg * 1.08, hh * 1.15), fontsize=8)
    a.axvspan(7, 12, color="grey", alpha=0.2)
    a.text(8.0, 40, "natural convection\nstarts here", fontsize=8)
    a.set_xlabel("gap g (mm)"); a.set_ylabel("h across the gap (W/m2K)")
    a.set_title("the gap coefficient (black squares: the values of the table in docs/research.md R3)", fontsize=9)
    a.legend(fontsize=7.5, loc="lower left"); a.grid(alpha=0.3, which="both")
    dk.save(fig, path, "A block that does not touch the board: conduction and radiation across the gap (research notes R3)")


def level_chain(path):
    """!
    @brief Draw the chain of levels of a part with a heatsink on top and a block under the board: junction, package top, interface, heatsink, board, interface, block, with the heat split (docs/research.md R5).
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(15, 5.4, 1, 2, ratios=[1, 1.15])
    a = axs[0]; a.set_xlim(0, 10); a.set_ylim(0, 9)
    dk.layer(a, 0.5, 1.6, 9, 0.35, CU); dk.layer(a, 0.5, 1.95, 9, 0.8, dk.FR4)
    dk.layer(a, 2.2, 0.9, 5.6, 0.2, "#f3d9b1"); dk.layer(a, 1.4, 0.2, 7.2, 0.7, dk.METAL, "block under the board", size=7)
    dk.box(a, 3.9, 2.9, 2.2, 0.9, "package", "#d9d9d9", size=8); dk.box(a, 4.45, 3.15, 1.1, 0.35, "J", "#f4b6b6", size=7)
    dk.layer(a, 3.9, 3.9, 2.2, 0.15, "#f3d9b1")
    dk.layer(a, 3.6, 4.05, 2.8, 0.8, dk.METAL, "heatsink", size=8)
    for x in (3.8, 4.5, 5.2, 5.9):
        dk.layer(a, x, 4.85, 0.12, 1.1, dk.METAL)
    dk.arrow(a, 5.0, 3.3, 5.0, 3.88, color=dk.HEAT); dk.arrow(a, 5.0, 3.15, 5.0, 2.6, color=dk.HEAT)
    a.text(7.2, 3.4, "up: theta_JC(top)\n+ interface/A + theta_SA", fontsize=7.5)
    a.text(7.2, 2.1, "down: theta, board,\nfaces, block", fontsize=7.5)
    a.text(5, 8.2, "the levels of one part", ha="center", fontsize=9, fontweight="bold")
    a = axs[1]; a.set_xlim(0, 12); a.set_ylim(0, 9)
    a.text(6, 8.4, "the same as a network (every level one conductance)", ha="center", fontsize=9, fontweight="bold")
    dk.box(a, 0.3, 4.0, 1.2, 1.0, "J", "#f4b6b6")
    dk.resistor(a, 1.5, 3.7, 6.6, "theta_JC(top)"); dk.resistor(a, 3.7, 5.9, 6.6, "R''/A"); dk.resistor(a, 5.9, 8.1, 6.6, "theta_SA")
    dk.box(a, 8.7, 6.2, 1.6, 0.8, "air", dk.AIR)
    a.plot([0.9, 0.9], [5.0, 6.6], "k"); a.plot([0.9, 1.5], [6.6, 6.6], "k")
    dk.resistor(a, 1.5, 3.7, 2.4, "theta (footprint)"); a.plot([0.9, 0.9], [4.0, 2.4], "k"); a.plot([0.9, 1.5], [2.4, 2.4], "k")
    dk.box(a, 3.7, 2.0, 2.2, 0.8, "board cells", "#cfe3f5"); dk.box(a, 6.4, 2.0, 1.8, 0.8, "faces h", "#cfe3f5")
    dk.resistor(a, 5.9, 6.4, 2.4); dk.box(a, 8.7, 2.0, 1.6, 0.8, "air", dk.AIR); dk.resistor(a, 8.2, 8.7, 2.4)
    dk.arrow(a, 4.8, 2.0, 4.8, 1.2); dk.box(a, 3.7, 0.2, 2.2, 0.9, "interface + block", "#e8e8e8", size=7)
    a.text(8.0, 0.8, "the heat from J splits in the inverse ratio of the two chains;\nthe effects are not additive:\ntop heatsink 37 K, block 9 K, both 40 K (MOSFET example)", fontsize=7.5, ha="center")
    dk.save(fig, path, "Many levels in a chain: package, interface, board, interface, metal (research notes R5; the top path with a junction node is in the program, analysis.part_split)")


def plate_spreading(path):
    """!
    @brief Plot the extra resistance of the base plate of a heatsink under a small source as a share of the top chain, with the values of the table of docs/research.md R8, and draw the section with the spreading in the base.
    @param path Output file.
    @return None.
    """
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.8), gridspec_kw={"width_ratios": [1, 1.2]})
    a = axs[0]; a.axis("off"); a.set_xlim(0, 10); a.set_ylim(0, 8)
    dk.layer(a, 1, 1.5, 8, 0.8, dk.METAL, "base plate", size=8)
    dk.box(a, 4.2, 0.4, 1.6, 0.9, "source", "#f4b6b6", size=8)
    for x0, x1 in ((4.6, 2.2), (5.4, 7.8), (4.8, 3.6), (5.2, 6.4)):
        a.annotate("", (x1, 2.4), (x0, 1.35), arrowprops={"arrowstyle": "->", "color": dk.HEAT, "connectionstyle": "arc3,rad=0.25"})
    for x in (1.8, 3.0, 4.2, 5.4, 6.6, 7.8):
        dk.arrow(a, x, 2.4, x, 4.2, color=dk.BLUE, width=1.0)
    a.text(5, 5.0, "film to the air over the whole top (the catalogue theta_SA)", ha="center", fontsize=8)
    a.text(5, 7.2, "spreading in the base under a small source", ha="center", fontsize=9, fontweight="bold")
    a.text(5, 6.3, "extra resistance = R(plate) - R(catalogue test source)", ha="center", fontsize=8)
    a = axs[1]
    names = ["Al 1 mm", "Al 3 mm", "Cu 3 mm", "steel 1 mm", "steel 3 mm"]
    s33 = [3.6, 1.6, 0.9, 13.5, 6.1]
    s5 = [3.2, 1.3, 0.7, 12.0, 5.0]
    x = np.arange(len(names))
    a.bar(x - 0.2, s33, 0.4, color="#1f77b4", label="3.3 mm source (chain 46.6 K/W)")
    a.bar(x + 0.2, s5, 0.4, color="#ff7f0e", label="5 mm source (chain 41 K/W)")
    a.set_xticks(x); a.set_xticklabels(names); a.set_ylabel("share of the top chain (%)")
    a.set_title("base spreading as a share of the whole top chain (table of research notes R8)", fontsize=9)
    a.legend(fontsize=8); a.grid(alpha=0.3, axis="y")
    dk.save(fig, path, "Heatsink on a component: plate or only K/W? (research notes R8)")


def continuum(path):
    """!
    @brief Draw the continuum problem of theory section 1.1: the conduction equation in the board and in a block, the exchange with the air on every face, the edges, and the heater as a uniform power over a footprint.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 5.2, 1, 2)
    a = axs[0]; a.set_xlim(0, 12); a.set_ylim(0, 9)
    a.add_patch(Polygon([[1.5, 2.0], [8.5, 2.0], [10.5, 3.6], [3.5, 3.6]], fc=dk.FR4, ec="k"))
    a.add_patch(Polygon([[1.5, 2.0], [3.5, 3.6], [3.5, 2.9], [1.5, 1.3]], fc="#c8dcb9", ec="k"))
    a.add_patch(Polygon([[1.5, 1.3], [8.5, 1.3], [8.5, 2.0], [1.5, 2.0]], fc="#b4cca3", ec="k"))
    a.add_patch(Polygon([[4.4, 2.5], [5.8, 2.5], [6.2, 2.85], [4.8, 2.85]], fc="#f4b6b6", ec="k"))
    a.text(5.3, 2.67, "q", ha="center", va="center", fontsize=8)
    for x, y in ((3.3, 3.0), (6.8, 3.2), (8.4, 2.6)):
        dk.arrow(a, x, y + 0.2, x, y + 1.8, color=dk.HEAT)
    a.text(8.2, 5.4, "-k dT/dn = h (T - T_amb)\nh = h_conv + h_rad", fontsize=8.5)
    dk.arrow(a, 9.6, 1.6, 11.3, 1.6, color=dk.HEAT); a.text(10.4, 1.9, "h_side", fontsize=8, ha="center")
    a.text(6, 8.2, "the board (and any block) as a solid", ha="center", fontsize=9, fontweight="bold")
    a = axs[1]; a.set_xlim(0, 10); a.set_ylim(0, 9)
    a.text(5, 8.2, "what the equations say", ha="center", fontsize=9, fontweight="bold")
    a.text(5, 6.4, "rho c dT/dt = div(k grad T) + q", ha="center", fontsize=12)
    a.text(5, 4.9, "k is a tensor: (k_ip, k_ip, k_th) for FR-4, k_cu for copper, k for a metal block", ha="center", fontsize=8.5)
    a.text(5, 3.8, "faces: exchange with the air by convection and radiation, h in W/m2K", ha="center", fontsize=8.5)
    a.text(5, 2.7, "edges: h_side, or insulated", ha="center", fontsize=8.5)
    a.text(5, 1.6, "sources: the power P of a heater spread uniformly over a footprint (a polygon on one layer)", ha="center", fontsize=8.5)
    a.text(5, 0.5, "steady state: dT/dt = 0", ha="center", fontsize=8.5, style="italic")
    dk.save(fig, path, "The continuum problem (theory section 1.1)")


def coverage(path):
    """!
    @brief Draw how a footprint polygon becomes the source vector of a heater: each cell is sampled on an s x s lattice, the coverage is the fraction of samples inside the polygon (even-odd test), and the power is shared in proportion, so it is exact for any grid (theory section 1.3). The coverages are computed here for a triangle.
    @param path Output file.
    @return None.
    """
    import matplotlib.pyplot as plt
    from matplotlib.path import Path as MPath
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw={"width_ratios": [1.3, 1]})
    tri = np.array([[1.3, 1.2], [5.6, 2.1], [2.7, 5.4]])
    poly = MPath(tri)
    n = 7
    s = 8
    cov = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            xs = i + (np.arange(s) + 0.5) / s
            ys = j + (np.arange(s) + 0.5) / s
            X, Y = np.meshgrid(xs, ys)
            cov[j, i] = poly.contains_points(np.c_[X.ravel(), Y.ravel()]).mean()
    a = axs[0]
    a.imshow(cov, origin="lower", extent=(0, n, 0, n), cmap="Reds", vmin=0, vmax=1.2)
    for i in range(n + 1):
        a.axhline(i, color="grey", lw=0.5); a.axvline(i, color="grey", lw=0.5)
    a.add_patch(Polygon(tri, fill=False, ec="k", lw=2))
    xs = 3 + (np.arange(s) + 0.5) / s
    ys = 2 + (np.arange(s) + 0.5) / s
    X, Y = np.meshgrid(xs, ys)
    inside = poly.contains_points(np.c_[X.ravel(), Y.ravel()])
    a.scatter(X.ravel()[inside], Y.ravel()[inside], s=5, c="k"); a.scatter(X.ravel()[~inside], Y.ravel()[~inside], s=5, c="w", edgecolors="k", linewidths=0.4)
    for i in range(n):
        for j in range(n):
            if cov[j, i] > 0:
                a.text(i + 0.5, j + 0.5, f"{cov[j, i]:.2f}", ha="center", va="center", fontsize=7, color="k" if cov[j, i] < 0.7 else "w")
    a.set_xlim(0, n); a.set_ylim(0, n); a.set_aspect("equal"); a.set_xticks([]); a.set_yticks([])
    a.set_title("coverage of each cell: fraction of the 8 x 8 samples inside the footprint\n(the cell at the lower right shows its samples: black inside, white outside)", fontsize=9)
    a = axs[1]; a.axis("off"); a.set_xlim(0, 10); a.set_ylim(0, 9)
    a.text(5, 8.3, "from coverage to source", ha="center", fontsize=9, fontweight="bold")
    a.text(5, 6.6, "Q_i = P c_i / sum(c)", ha="center", fontsize=13)
    a.text(5, 5.0, "the weights sum to 1: the power is exact\nwhatever the grid", ha="center", fontsize=9)
    a.text(5, 3.4, f"here: sum of the coverages = {cov.sum():.2f} cells,\nthe triangle has area {0.5 * abs((tri[1, 0] - tri[0, 0]) * (tri[2, 1] - tri[0, 1]) - (tri[1, 1] - tri[0, 1]) * (tri[2, 0] - tri[0, 0])):.2f} cells", ha="center", fontsize=9)
    a.text(5, 1.6, "a footprint smaller than a sample sends all the power\nto the cell of its centroid\ncopper fill of a cell: f = max over zones (c_zone x fill)", ha="center", fontsize=8.5)
    dk.save(fig, path, "Sources and geometry: sub-sampled coverage and an exact power (theory section 1.3)")


def ladder(path):
    """!
    @brief Draw the verification ladder of theory section 11: the checks from exact solutions up to the comparison between models, with the results of docs/theory.md, and the rung that is still missing (a physical board).
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(14, 6.4)
    ax.set_xlim(0, 14); ax.set_ylim(0, 8.2)
    rungs = [
        ("exact answers", "energy balance 1e-12 to 1e-9 on every board; the RC solution of a uniform board (Euler 1st order, Crank-Nicolson 2nd); closed form of the power loop 0.05 K; 1D series circuit 1e-6 K", "#d9efd0"),
        ("solvers against each other", "direct, CG and SOR agree to 1e-8 K on five boards", "#d9efd0"),
        ("published solutions", "Yovanovich's table within 0.7 to 0.8 % (2 % at epsilon 0.1); plate model +0.6 % (Seri Lee); convection correlations 1 to 3 %", "#cfe3f5"),
        ("independent 3D solutions", "3D solid and a finite-element solid: layered models within 0.4 to 2.2 % (FVM); 3D solid 0.2 % on three boards, +-4 % on a heater-sized pad;\nan independent solver in the tests: coupon within 0.2 % (FVM, 3D solid, Analytic), 1.2 % (FDM)", "#cfe3f5"),
        ("models against each other", "20 scenarios, four models and the 3D solid (the Lumped and Analytic models fail in known cases and the input checks warn)", "#f3d9b1"),
        ("a physical board", "NOT DONE: no model has been compared with measurements; calibrate_convection fits one measurement", "#f4b6b6"),
    ]
    for k, (t, d, c) in enumerate(rungs):
        y = 6.9 - 1.2 * k
        dk.box(ax, 0.3 + 0.35 * k, y, 3.2, 0.9, t, c, size=8, bold=(k == 5))
        ax.text(4.0 + 0.35 * k, y + 0.45, d, va="center", fontsize=7.8)
    dk.arrow(ax, 0.1, 0.4, 0.1, 7.8, color="grey")
    ax.text(0.0, 8.0, "more independent, more convincing", fontsize=8, color="grey")
    dk.save(fig, path, "The verification ladder (theory section 11)")


def orientation(path):
    """!
    @brief Draw the board orientations the program knows (horizontal with layer 1 up, vertical) and plot the Nusselt number against the Rayleigh number of the three natural-convection laws (hot face up, hot face down, vertical plate), the laws of theory section 8 with air properties held constant (illustrative).
    @param path Output file.
    @return None.
    """
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.0), gridspec_kw={"width_ratios": [1.1, 1]})
    a = axs[0]; a.axis("off"); a.set_xlim(0, 12); a.set_ylim(0, 9)
    for x0, lab in ((0.5, "hot face up"), (4.3, "hot face down")):
        dk.layer(a, x0, 3.0, 3.0, 0.3, dk.FR4, size=7)
        a.text(x0 + 1.5, 2.4, lab, ha="center", fontsize=8)
    for x in (1.0, 2.0, 3.0):
        dk.arrow(a, x, 3.4, x, 5.0, color=dk.HEAT, width=1.2)
    for x in (4.8, 5.8, 6.8):
        dk.arrow(a, x, 2.9, x, 1.5, color=dk.HEAT, width=0.8)
    a.text(2.0, 5.4, "layer 1 looks up:\nthe upper face loses more", ha="center", fontsize=7.5)
    a.text(5.8, 1.0, "the last layer looks down", ha="center", fontsize=7.5)
    dk.layer(a, 9.2, 1.2, 0.3, 4.2, dk.FR4)
    for y in (2.0, 3.2, 4.4):
        dk.arrow(a, 9.6, y, 9.6, y + 1.0, color=dk.HEAT, width=1.0); dk.arrow(a, 9.1, y, 9.1, y + 1.0, color=dk.HEAT, width=1.0)
    a.text(9.4, 0.5, "vertical:\nboth faces alike", ha="center", fontsize=7.5)
    a.text(6, 8.3, "the two orientations of the Board panel", ha="center", fontsize=9, fontweight="bold")
    a.text(6, 7.0, "typed coefficients ignore the orientation; tilted boards are not considered;\na colder-than-air face swaps up and down", ha="center", fontsize=8)
    a = axs[1]
    Ra = np.logspace(3, 10, 200)
    Pr = 0.71
    up = np.where(Ra <= 1e7, 0.54 * Ra ** 0.25, 0.15 * Ra ** (1 / 3))
    down = 0.27 * Ra ** 0.25
    vert = (0.825 + 0.387 * Ra ** (1 / 6) / (1 + (0.492 / Pr) ** (9 / 16)) ** (8 / 27)) ** 2
    a.loglog(Ra, up, color=dk.HEAT, label="horizontal, hot face up")
    a.loglog(Ra, down, color=dk.BLUE, label="horizontal, hot face down (half of face up at the same Ra)")
    a.loglog(Ra, vert, color="#2ca02c", label="vertical plate (Churchill and Chu, general form; laminar form optional), Pr = 0.71")
    a.set_xlabel("Rayleigh number"); a.set_ylabel("Nusselt number")
    a.set_title("the laws of the program (theory section 8)", fontsize=9)
    a.legend(fontsize=7.5); a.grid(alpha=0.3, which="both")
    dk.save(fig, path, "Board orientation, kept simple (models section 18)")


def architecture(path):
    """!
    @brief Draw how the program is organised for a user of the API and the command line: the problem builder, the options, simulate (input checks, the models with the pieces they share, profiles and time, the warnings after the run), the results and what is saved, with the application, its calculation process and the command line (models section 7).
    @details Updated for the laminate nodes of one-layer boards (`laminate.py`), the thick-plate warning (`checks.check_thick_plates`), the natural convection form option (`Board.natural_form`), the inner copper option of the templates (`Board.template_inner_oz`), the outline cover and edge assignment (`geometry.edge_length_on_board`), the 3D solid size limit (`solid3d.MAX_CELLS`, 250 000 unknowns) and the power calculator (`inverse.py`).
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(15, 7.2)
    ax.set_xlim(0, 15); ax.set_ylim(0, 9.4)
    dk.box(ax, 0.2, 7.2, 3.4, 1.8, "Problem\n(board: stack-up, outline,\nnatural_form, template_inner_oz;\nzones, parts, vias, heatsinks)", "#cfe3f5", size=7.5)
    dk.box(ax, 0.2, 4.9, 3.4, 1.6, "SolverOptions\n(models, cell size, solver,\ncomputed h, profiles)", "#cfe3f5", size=7.5)
    dk.box(ax, 4.4, 5.0, 3.0, 3.6, "simulate()\n\n1 input checks (checks.py)\n2 run the models\n3 profile decision and\n   time simulation\n4 warnings after the run:\n   parts, thick plates", "#f3d9b1", size=7.5, bold=True)
    for k, (t, c) in enumerate((("FVM (reference)", "#d9efd0"), ("FDM", "#e8e8e8"), ("Lumped (LPTN)", "#e8e8e8"), ("Analytic", "#e8e8e8"), ("3D solid (steady; refused above\n250 000 unknowns, the others still run)", "#e8e8e8"))):
        dk.box(ax, 8.2, 8.0 - 1.05 * k, 3.1, 0.85, t, c, size=7)
    dk.box(ax, 12.2, 6.0, 2.6, 2.4, "Simulation\n\ntable, error against\nthe FVM, energy\nbalance, warnings", "#f4b6b6", size=7.5)
    dk.box(ax, 12.2, 3.3, 2.6, 1.6, "save()\nreport, JSON, CSV\nfields, figures", "#e8e8e8", size=7.5)
    for (x0, y0, x1, y1) in ((3.6, 8.1, 4.4, 7.4), (3.6, 5.7, 4.4, 6.2), (7.4, 7.0, 8.2, 7.6), (11.3, 7.3, 12.2, 7.2), (13.5, 6.0, 13.5, 4.9)):
        dk.arrow(ax, x0, y0, x1, y1)
    dk.box(ax, 0.2, 0.3, 3.6, 1.35, "command line: python -m pcbthermal\nrun, transient, solvers, calibrate,\nconvergence, convert, example, gui", "#d9d9d9", size=7)
    dk.box(ax, 4.2, 0.3, 3.6, 1.35, "application (PySide 6)\nruns a job in a separate process\n(jobs.py; cancel = terminate)", "#d9d9d9", size=7)
    dk.box(ax, 8.2, 0.3, 3.2, 1.35, "inverse.py: the power calculator\n(the board model run backwards,\nband with design terms)", "#d9d9d9", size=7)
    # The pieces that several models share
    dk.box(ax, 4.2, 1.95, 7.2, 1.55, "shared by the models: laminate.py (laminate nodes of a one-layer board), blocks.py (metal blocks),\nconvection.py (computed h, natural_form general or laminar), geometry.py (outline cover and edge\nassignment, edge_length_on_board), model.stackup_template (0.5 oz or 1 oz inner copper)", "#fbf1d6", size=7)
    ax.text(12.2, 2.3, "the sparse solvers must not run in\ntwo threads at once: the application\nserialises its calculations (one lock)", fontsize=7, va="center")
    for x in (2.0, 6.0):
        dk.arrow(ax, x, 1.65, 4.9 if x > 3 else 2.6, 4.9, color="grey")
    dk.save(fig, path, "Python API and command line: the flow from a problem to a report (models section 7)")


def legacy(path):
    """!
    @brief Plot the error on the temperature rise of the removed wxPython program and of the current models on the same example board (the table of docs/validation.md section 6), on a symmetric logarithmic axis.
    @param path Output file.
    @return None.
    """
    import matplotlib.pyplot as plt
    rows = [("old Analytic basic", 851), ("old Lumped basic", -88), ("old Analytic advanced", 55845), ("old Lumped advanced", 597),
            ("old FDM 10 mm", 64), ("old FDM 2 mm", -15), ("old FDM 1 mm", -32), ("old FDM 1 mm tight", -5.5),
            ("FVM 1 mm", 0.0), ("FDM 1 mm", -2.4), ("Lumped", -1.9), ("Analytic", -1.9)]
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.4), gridspec_kw={"width_ratios": [1.5, 1]})
    a = axs[0]
    names = [r[0] for r in rows]; vals = [r[1] for r in rows]
    cols = ["#d62728"] * 8 + ["#2ca02c"] * 4
    a.barh(range(len(rows)), vals, color=cols)
    a.set_xscale("symlog", linthresh=1.0); a.set_yticks(range(len(rows))); a.set_yticklabels(names, fontsize=8); a.invert_yaxis()
    a.axvline(0, color="k", lw=0.8)
    a.set_xlabel("error on the temperature rise (%, symmetric log axis)")
    a.set_title("same example board (reference 85.81 C): the removed program (red) and the current models (green)", fontsize=9)
    a.grid(alpha=0.3, axis="x", which="both")
    a = axs[1]; a.axis("off"); a.set_xlim(0, 10); a.set_ylim(0, 9)
    a.text(5, 8.4, "what went wrong in the old FDM", ha="center", fontsize=9, fontweight="bold")
    items = ["a stopping rule on the step size (false convergence):\n  the error grows when the mesh is refined (1 mm: -32 %)",
             "a heater power that depended on the grid\n  (10 mm mesh: 8.17 W injected for 5.50 W)",
             "no lateral conduction in FR-4; solid vias;\n  heatsinks on inner layers ignored",
             "boundary nodes with a full cell",
             "not the finite-difference idea: a correct FDM\n  lands within about 1 % of the FVM"]
    for k, t in enumerate(items):
        a.text(0.3, 7.2 - 1.4 * k, "- " + t, fontsize=8, va="center")
    dk.save(fig, path, "The removed wxPython program against the current one (validation section 6)")


def time_results(path):
    """!
    @brief Plot the time-dependent checks of docs/validation.md section 7: the maximum error of implicit Euler and Crank-Nicolson against the step (first and second order) and the hottest point after a power step in the FVM against the FDM and the Analytic model, with the values of that section.
    @param path Output file.
    @return None.
    """
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.8))
    a = axs[0]
    dts = np.array([1, 2, 4, 8.0])
    eul = np.array([3.06, 1.67, 0.87, 0.45]); cn = np.array([0.315, 0.077, 0.019, 0.005])
    a.loglog(dts, eul, "o-", color=dk.BLUE, label="implicit Euler")
    a.loglog(dts, cn, "s-", color=dk.HEAT, label="Crank-Nicolson")
    a.loglog(dts, eul[0] / dts, "--", color="grey", label="order 1"); a.loglog(dts, cn[0] / dts ** 2, ":", color="grey", label="order 2")
    a.set_xlabel("steps per original step (dt, dt/2, dt/4, dt/8)"); a.set_ylabel("maximum error over three time constants (K)")
    a.set_title("exact RC check (time constant 109.1 s, steady rise 40 K)", fontsize=9); a.legend(fontsize=7.5); a.grid(alpha=0.3, which="both")
    a = axs[1]
    t1 = np.array([0, 0.12, 0.82, 3.6, 15, 60, 120.0])
    fvm = [25.0, 30.4, 43.6, 53.3, 61.3, 70.7, 76.6]; fdm = [25.0, 30.3, 43.1, 52.7, 60.6, 70.0, 75.9]
    a.semilogx(np.maximum(t1, 0.05), fvm, "o-", color=dk.BLUE, label="FVM"); a.semilogx(np.maximum(t1, 0.05), fdm, "s--", color=dk.HEAT, label="FDM")
    a.set_xlabel("time (s)"); a.set_ylabel("hottest point (C)"); a.set_title("step animation, example board at 2 mm:\nFDM within 0.7 C of the FVM", fontsize=9)
    a.legend(fontsize=8); a.grid(alpha=0.3, which="both")
    a = axs[2]
    t2 = np.array([0, 0.12, 0.35, 0.82, 1.8, 3.6, 7.4, 15, 30, 60, 120.0])
    fv = [25.0, 30.5, 37.4, 44.0, 49.3, 53.7, 57.7, 61.7, 66.1, 71.2, 77.1]; an = [25.0, 30.6, 37.4, 43.4, 48.0, 52.0, 55.8, 59.8, 64.1, 69.4, 76.0]
    a.semilogx(np.maximum(t2, 0.05), fv, "o-", color=dk.BLUE, label="FVM"); a.semilogx(np.maximum(t2, 0.05), an, "^--", color="#2ca02c", label="Analytic (vias calibrated per heater)")
    a.set_xlabel("time (s)"); a.set_ylabel("hottest point (C)"); a.set_title("step animation, 4 W + 1.5 W at 1 mm:\nAnalytic within 2 C at every time", fontsize=9)
    a.legend(fontsize=8); a.grid(alpha=0.3, which="both")
    dk.save(fig, path, "Time-dependent results (validation section 7)")


def input_checks(path):
    """!
    @brief Draw the situations that the input checks warn about on one board: a heater partly outside, a heater with no copper under it, a copper edge across a footprint, a heater only a few cells wide, overlapping heaters, a via outside the board, a metal block with no copper under it (models section 3).
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(16, 6.2)
    ax.set_xlim(0, 17); ax.set_ylim(0, 8)
    ax.add_patch(Rectangle((0.5, 1.0), 9.0, 6.0, fc=dk.FR4, ec="k", lw=1.5))
    ax.add_patch(Rectangle((0.5, 1.0), 4.4, 3.2, fc=CU, ec="none", alpha=0.7))
    ax.add_patch(Rectangle((5.2, 4.6), 3.2, 2.0, fc=CU, ec="none", alpha=0.7))
    items = [
        (Rectangle((9.0, 5.6), 1.4, 1.0, fc="#f4b6b6", ec="k"), (9.7, 6.1), "1"),
        (Rectangle((1.0, 4.6), 1.2, 1.0, fc="#f4b6b6", ec="k"), (1.6, 5.1), "2"),
        (Rectangle((4.3, 2.2), 1.2, 1.0, fc="#f4b6b6", ec="k"), (4.9, 2.7), "3"),
        (Rectangle((6.6, 1.3), 0.22, 1.4, fc="#f4b6b6", ec="k"), (6.7, 2.0), "4"),
        (Rectangle((2.2, 1.4), 1.0, 0.8, fc="#f4b6b6", ec="k"), (2.7, 1.8), "5"),
        (Rectangle((2.7, 1.6), 1.0, 0.8, fc="#e8b6b6", ec="k"), (3.2, 2.0), ""),
    ]
    for patch, (x, y), n in items:
        ax.add_patch(patch)
    ax.text(9.7, 6.1, "1", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(1.6, 5.1, "2", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(4.9, 2.7, "3", ha="center", va="center", fontsize=9, fontweight="bold")
    ax.text(7.35, 2.0, "4", ha="left", va="center", fontsize=9, fontweight="bold")
    ax.text(2.2, 2.45, "5", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.add_patch(Circle((9.9, 2.5), 0.12, fc="k")); ax.text(10.15, 2.5, "6", va="center", fontsize=9, fontweight="bold")
    ax.add_patch(Rectangle((6.0, 4.8), 2.0, 1.4, fc=dk.METAL, ec="k", alpha=0.8)); ax.text(7.0, 5.5, "7", ha="center", va="center", fontsize=9, fontweight="bold")
    txt = ["1  heater partly outside the board: its power is moved onto the part inside",
           "2  no copper under a heater",
           "3  a copper edge or hatching crosses a footprint: Lumped and Analytic unreliable",
           "4  a heater only a few cells wide (the cell is larger than the part)",
           "5  overlapping heaters",
           "6  a via (or a zone) outside the board",
           "7  a metal block with no copper under it, or an almost perfect contact",
           "8  fins closer than the air gap that still air allows (metal block)",
           "9  after the run: a thick, poorly conducting plate or block under a part\n    (the surface can be hotter than the node: check_thick_plates)",
           "   and: zero total power; a 3D solid above 250 000 unknowns is not run"]
    for k, t in enumerate(txt):
        ax.text(10.7 if False else 9.9 + 0.0, 7.4 - 0.0, "", fontsize=1)
    for k, t in enumerate(txt):
        ax.text(0.5, 0.55 - 0.0 * k, "", fontsize=1)
    ax.text(10.9, 7.3, "what the checks warn about", fontsize=9, fontweight="bold", va="top")
    for k, t in enumerate(txt):
        ax.text(10.9, 6.7 - 0.62 * k, t, fontsize=7.2, va="top")
    ax.text(0.5, 0.3, "check_problem never blocks a run: each warning says what is wrong and what to do; they are also shown live under the Run button", fontsize=8, style="italic")
    dk.save(fig, path, "The input checks: what makes a result doubtful (models section 3)")


def curved_boards(path):
    """!
    @brief Draw a rounded corner as a polygon with 4, 8, 16 and 32 edges and plot the area lost against the number of edges, computed from the closed form of an inscribed polygon and compared with the values of docs/models.md section 14.
    @param path Output file.
    @return None.
    """
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.0), gridspec_kw={"width_ratios": [1.2, 1]})
    a = axs[0]; a.set_aspect("equal"); a.axis("off")
    r = 1.0
    for k, n in enumerate((4, 8, 16, 32)):
        ox = k * 2.6
        th = np.linspace(0, np.pi / 2, 200)
        a.plot(ox + r - r * np.cos(th), r - r * np.sin(th) * 0 + 0 * th + (r * np.sin(th)) - r + 0, color="#bbbbbb", lw=0)   # placeholder keeps the axes
        # corner at the origin of the local frame: arc centre (r, r), arc from (0, r) to (r, 0)
        ang = np.linspace(np.pi, 1.5 * np.pi, n + 1)
        px = ox + r + r * np.cos(ang); py = r + r * np.sin(ang)
        a.fill([ox + 0, *px, ox + 0], [0, *py, 0], color="#f3d9b1", ec="none")
        a.plot(ox + r + r * np.cos(np.linspace(np.pi, 1.5 * np.pi, 100)), r + r * np.sin(np.linspace(np.pi, 1.5 * np.pi, 100)), "k--", lw=0.8)
        a.plot(px, py, "o-", color=dk.HEAT, ms=3, lw=1.2)
        a.text(ox + 0.9, -0.35, f"{n} edges", ha="center", fontsize=8)
    a.set_title("the polygon lies inside the true arc and loses a sliver of area", fontsize=9)
    a = axs[1]
    n = np.array([4, 8, 16, 32])
    piece = (1 - (2 * n / np.pi) * np.sin(np.pi / (2 * n))) * (np.pi / 4) / (1 - np.pi / 4) * 100
    board = piece / 100 * 4 * (1 - np.pi / 4) * 144 / (2400 - 4 * (1 - np.pi / 4) * 144) * 100
    a.loglog(n, piece, "o-", color=dk.HEAT, label="corner piece (computed)")
    a.loglog(n, board, "s-", color=dk.BLUE, label="whole 60 x 40 mm board, 12 mm corners (computed)")
    for x, y in zip(n, [9.3, 2.4, 0.6, 0.15]): a.plot(x, y, "k^", ms=7)
    for x, y in zip(n, [0.51, 0.13, 0.03, 0.008]): a.plot(x, y, "kv", ms=7)
    a.plot([], [], "k^", label="values in docs/models.md 14 (piece)"); a.plot([], [], "kv", label="values in docs/models.md 14 (board)")
    a.set_xlabel("edges per corner"); a.set_ylabel("area error (%)")
    a.set_title("the closed form reproduces the values of the documentation", fontsize=9)
    a.legend(fontsize=7.5); a.grid(alpha=0.3, which="both")
    dk.save(fig, path, "Curved boards are polygons: edges against area error (models section 14)")


def prepreg(path):
    """!
    @brief Draw several sheets in one dielectric gap (a prepreg and a core) combined as resistances in series through the thickness and conductances in parallel in the plane, and plot the sensitivity of the rise to the stack-up numbers with the values of docs/models.md section 17.
    @param path Output file.
    @return None.
    """
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.0), gridspec_kw={"width_ratios": [1, 1.1]})
    a = axs[0]; a.axis("off"); a.set_xlim(0, 10); a.set_ylim(0, 9)
    dk.layer(a, 1.0, 6.2, 5.0, 0.35, CU, "copper", size=7)
    dk.layer(a, 1.0, 5.6, 5.0, 0.6, "#b8d8a6", "prepreg: t1, k1", size=7)
    dk.layer(a, 1.0, 3.2, 5.0, 2.4, dk.FR4, "core: t2, k2", size=7)
    dk.layer(a, 1.0, 2.85, 5.0, 0.35, CU, "copper", size=7)
    a.annotate("", (6.4, 6.55), (6.4, 2.85), arrowprops={"arrowstyle": "<->"}); a.text(6.6, 4.7, "gap = t1 + t2", fontsize=8)
    a.text(1.0, 8.2, "several sheets in one gap, one effective sheet:", fontsize=9, fontweight="bold")
    a.text(1.0, 7.5, "through:  k = sum(t) / sum(t / k)      (series)", fontsize=8.5)
    a.text(1.0, 1.9, "in plane:  k = sum(t k) / sum(t)      (parallel)", fontsize=8.5)
    a.text(1.0, 1.2, "density by thickness, specific heat by mass", fontsize=8.5)
    a.text(1.0, 0.4, "the pressed thickness counts, not the nominal one before lamination", fontsize=8, style="italic")
    a = axs[1]
    names = ["copper thickness +-15 %", "dielectric k +-30 % (with vias)", "dielectric k +-30 % (no vias)", "dielectric thickness +-10 %", "prepreg 0.25 against cores 0.35"]
    lo = [-5.0, -0.8, -2.3, -0.4, -0.1]; hi = [5.0, 1.0, 3.3, 0.4, 0.1]
    y = np.arange(len(names))
    a.barh(y, hi, color="#d62728", label="up"); a.barh(y, lo, color="#1f77b4", label="down")
    a.set_yticks(y); a.set_yticklabels(names, fontsize=8); a.invert_yaxis(); a.axvline(0, color="k", lw=0.8)
    a.set_xlabel("change of the temperature rise (%) for the plus and minus change of the number")
    a.set_title("how much each stack-up number matters (typical 4 layers, 3 W, nine vias)", fontsize=9); a.grid(alpha=0.3, axis="x")
    dk.save(fig, path, "Prepreg and sheets in a gap (models section 17)")


def why_agree(path):
    """!
    @brief Draw why the FVM and the Analytic model give about the same numbers: they solve the same layered model (one exactly, one numerically), the real board differs from it by an error they share, and part of the agreement was tuned (validation section 4).
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(14, 5.6)
    ax.set_xlim(0, 14); ax.set_ylim(0, 8)
    dk.box(ax, 0.3, 3.2, 3.6, 1.8, "the layered model\n(sheets, vertical resistances,\none h per face)", "#cfe3f5", size=8.5, bold=True)
    dk.box(ax, 5.2, 5.6, 3.2, 1.5, "FVM: its numerical solution\n(mesh error 0.2 to 1 %)", "#d9efd0", size=8)
    dk.box(ax, 5.2, 3.5, 3.2, 1.5, "Analytic: its exact solution on\na uniform sheet; tuned to the FVM", "#d9efd0", size=8)
    dk.box(ax, 5.2, 1.0, 3.2, 1.6, "3D solid / finite elements:\nthe independent check\n(no tuning)", "#f3d9b1", size=8)
    dk.box(ax, 10.2, 3.2, 3.5, 1.8, "the real board", "#e8e8e8", size=9, bold=True)
    for (x0, y0, x1, y1) in ((3.9, 4.6, 5.2, 6.2), (3.9, 4.1, 5.2, 4.2), (10.2, 3.8, 8.4, 2.4), (13.0, 3.2, 8.4, 1.8)):
        dk.arrow(ax, x0, y0, x1, y1)
    ax.text(9.3, 6.6, "agree: two correct solutions\nof one model", fontsize=8, ha="left", color="#2a7d2a")
    ax.text(10.2, 6.1, "the model error (0.4 to 3 % against\nthe 3D solid) is shared by both", fontsize=8, ha="left")
    ax.text(0.3, 1.6, "they diverge where the geometry is not uniform\nnear a heater: pads, copper edges, corners", fontsize=8.5)
    ax.text(0.3, 0.5, "so 'FVM = more precise' does not hold in general:\nwhat the FVM has is freedom of geometry", fontsize=8.5, style="italic")
    dk.save(fig, path, "Why the FVM and the Analytic model agree (validation section 4)")


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
                                    ("multigrid_planned", multigrid), ("air_gap", air_gap), ("level_chain", level_chain),
                                    ("plate_spreading", plate_spreading), ("continuum", continuum), ("coverage", coverage),
                                    ("verification_ladder", ladder), ("orientation", orientation), ("architecture", architecture),
                                    ("legacy_vs_current", legacy), ("time_results", time_results), ("input_checks", input_checks),
                                    ("curved_boards", curved_boards), ("prepreg", prepreg), ("why_fvm_analytic_agree", why_agree)), start=1):
        fn(OUT / f"fig_{k:02d}_{name}.png")


if __name__ == "__main__":
    main()
