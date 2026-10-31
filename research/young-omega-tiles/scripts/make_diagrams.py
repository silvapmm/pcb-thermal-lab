#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation of the two studies of this folder: the Jacobi and SOR iterations and where the Jacobi radius enters; the spectrum of the Jacobi matrix and the curve of the
       SOR radius against omega; the via lattice cell with the constriction at the barrel; the tile grid over a via array, the self-term and the tiles against an edge; the Krogh well in the
       rings of the Lumped model; the chain that builds the tile Green function and where its 64 modes are.
@details Figures 01 to 07 of figures/ (data figures 08 and later are drawn by make_figures.py). No study is run: only closed forms (Young's relation, the Krogh profile, the cosine
         spectrum of the Poisson matrix) and a 1D chain of 60 cells for the illustration of the Rayleigh quotient (marked as illustrative in the caption).
         Files: fig_01_jacobi_and_sor_iteration.png, fig_02_spectrum_and_omega_curve.png, fig_03_rayleigh_and_lanczos_picture.png, fig_04_via_lattice_cell_constriction.png,
         fig_05_tile_grid_over_a_via_array.png, fig_06_krogh_well_in_the_lumped_rings.png, fig_07_tile_green_function_chain.png.
         Usage: python research/young-omega-tiles/scripts/make_diagrams.py   (from the repository root).
"""

import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE.parents[1] / "lumped-analytic-vias" / "lib"))

import matplotlib                                                           # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                             # noqa: E402
from matplotlib.patches import Circle, Rectangle                            # noqa: E402

import diagram_kit as dk                                                    # noqa: E402
import young as yg                                                          # noqa: E402

OUT = HERE.parent / "figures"


def fig_jacobi_sor(path):
    """!
    @brief Flow from K to the sweep count, and the red-black colouring of the six-neighbour stencil.
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(13, 5.2, 1, 2, ratios=[1.25, 1])
    a.set_xlim(0, 10)
    a.set_ylim(0, 8)
    dk.box(a, 0.2, 6.6, 4.2, 1.1, "K = D - N\n(symmetric, positive definite)", "#cfe3f5")
    dk.box(a, 5.4, 6.6, 4.3, 1.1, "Jacobi matrix J = D$^{-1}$N\nsame spectrum as J$_s$ = D$^{-1/2}$N D$^{-1/2}$", "#dff0d8")
    dk.arrow(a, 4.4, 7.15, 5.4, 7.15)
    dk.box(a, 5.4, 4.7, 4.3, 1.2, "eigenvalues in pairs $\\pm\\mu$ (two-colourable graph)\n$\\rho_J$ = largest $\\mu$ = 1 - $\\lambda_{min}$(D$^{-1/2}$K D$^{-1/2}$)", "#fff2cc", bold=True)
    dk.arrow(a, 7.55, 6.6, 7.55, 5.9)
    dk.box(a, 5.4, 2.9, 4.3, 1.2, "Young: ($\\lambda$ + $\\omega$ - 1)$^2$ = $\\lambda\\omega^2\\mu^2$\n$\\omega_{opt}$ = 2 / (1 + $\\sqrt{1-\\rho_J^2}$)", "#fde0dc", bold=True)
    dk.arrow(a, 7.55, 4.7, 7.55, 4.1)
    dk.box(a, 5.4, 1.0, 4.3, 1.2, "sweeps $\\approx$ ln(tol) / ln($\\omega_{opt}$ - 1)\n(program: $\\omega$ = 2/(1+sin($\\pi$/n)) with n = longest side)", "#e8dff5")
    dk.arrow(a, 7.55, 2.9, 7.55, 2.2)
    dk.box(a, 0.2, 4.7, 4.3, 1.2, "estimate of $\\rho_J$ without the eigenvalues:\nRayleigh, Lanczos k, power, adaptive", "#fff2cc")
    dk.arrow(a, 4.5, 5.3, 5.4, 5.3, color="#d62728")
    dk.box(a, 0.2, 2.9, 4.3, 1.2, "cost: k products with K\n(a sweep = 2 products)", "#f4f4f4")
    dk.arrow(a, 2.35, 4.7, 2.35, 4.1)
    dk.box(a, 0.2, 1.0, 4.3, 1.2, "direct solve = the program's default\n(SOR is a comparison solver)", "#f4f4f4")
    dk.arrow(a, 2.35, 2.9, 2.35, 2.2)
    b.set_xlim(0, 8)
    b.set_ylim(0, 8)
    b.set_aspect("equal")
    for i in range(6):
        for j in range(6):
            red = (i + j) % 2 == 0
            b.add_patch(Rectangle((0.5 + i * 0.95, 1.6 + j * 0.95), 0.95, 0.95, facecolor="#f4b6b6" if red else "#555555", edgecolor="w"))
    ci, cj = 2, 2
    x0, y0 = 0.5 + ci * 0.95 + 0.475, 1.6 + cj * 0.95 + 0.475
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        dk.arrow(b, x0, y0, x0 + dx * 0.95, y0 + dy * 0.95, color="#1f77b4", width=2)
    b.text(4.0, 7.5, "red-black colouring: a red cell couples\nonly to black cells (and, across layers,\nto the other colour)", ha="center", fontsize=8)
    b.text(4.0, 0.7, "all reds at once, then all blacks:\nthe stencil is consistently ordered (Young's relation holds)", ha="center", fontsize=8)
    dk.save(fig, path, "Where the Jacobi spectral radius enters the SOR")


def fig_spectrum(path):
    """!
    @brief The Jacobi spectrum of a plate and the SOR radius against omega.
    @param path Output file.
    @return None.
    """
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.4))
    n = 42
    p = np.arange(1, n + 1)
    mu = np.sort(((np.cos(p[:, None] * np.pi / (n + 1)) + np.cos(p[None, :] * np.pi / (n + 1))) / 2).ravel())
    a.hist(mu, bins=80, color="#7fb3d5")
    a.axvline(mu[-1], color="#d62728")
    a.axvline(-mu[-1], color="#d62728")
    a.annotate("$\\rho_J$ = cos($\\pi$/(n+1))", (mu[-1], 20), xytext=(0.15, 120), arrowprops=dict(arrowstyle="->"))
    a.set_xlabel("eigenvalue $\\mu$ of the Jacobi matrix (Poisson 5-point, n = 42: textbook case)")
    a.set_ylabel("count")
    a.set_title("symmetric spectrum; the gap 1 - $\\rho_J$ sets the sweeps")
    rho = 0.999806
    ws = np.linspace(1.0, 1.999, 500)
    r = [yg.rho_sor(float(w), rho) for w in ws]
    b.plot(ws, r, color="k")
    w_opt = yg.omega_young(rho)
    w_prog = 2 / (1 + math.sin(math.pi / 42))
    b.axvline(w_opt, color="#2ca02c", ls="--", label=f"Young {w_opt:.4f}")
    b.axvline(w_prog, color="#d62728", ls="--", label=f"program's formula {w_prog:.4f}")
    b.set_ylim(0.9, 1.0)
    b.set_xlabel("$\\omega$")
    b.set_ylabel("spectral radius of the SOR matrix")
    b.set_title("Young's relation for $\\rho_J$ = 0.999806 (3 x 3 array board, 42 cells)")
    b.legend()
    dk.save(fig, path)


def fig_rayleigh(path):
    """!
    @brief Illustration (a 1D chain of 60 cells): the dominant eigenvector of the Jacobi matrix with an uneven loss against the uniform trial vector of the Rayleigh bound and a Ritz vector.
    @param path Output file.
    @return None.
    """
    n = 60
    loss = np.full(n, 1e-4)
    loss[:6] = 4e-3
    K = yg.plate_matrix(1, 1, n, 1.0, 1.0, 0.0, loss.reshape(1, 1, n)).toarray()
    d = np.diag(K)
    As = K / np.sqrt(np.outer(d, d))
    w, v = np.linalg.eigh(As)
    x = v[:, 0] / np.sqrt(d)
    x = x / x.max()
    rho_exact = 1 - w[0]
    rq = 1 - np.ones(n) @ K @ np.ones(n) / d.sum()
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.2))
    a.plot(np.arange(n), x, label="dominant eigenvector of the Jacobi matrix (temperature-like profile)")
    a.plot(np.arange(n), np.ones(n), "--", label="trial vector of the Rayleigh bound (uniform)")
    a.set_xlabel("cell along a 1D plate (cooled hard at the left end)")
    a.set_ylabel("relative value")
    a.legend(fontsize=7)
    a.set_title("ILLUSTRATION: the uniform vector is exact on an evenly cooled plate, close otherwise")
    hist = yg.lanczos_top(lambda y: y - (K @ (y / np.sqrt(d))) / np.sqrt(d), np.sqrt(d), 12)
    b.plot(range(1, 13), [1 - h for h in hist], "o-", label="Lanczos Ritz value, 1 - $\\rho$")
    b.axhline(1 - rho_exact, color="k", ls="--", label="exact 1 - $\\rho_J$")
    b.axhline(1 - rq, color="#d62728", ls=":", label="Rayleigh bound (k = 1 product)")
    b.set_yscale("log")
    b.set_xlabel("Lanczos steps (products with K)")
    b.set_title("ILLUSTRATION: Ritz values approach from below, so $\\omega$ stays below the optimum")
    b.legend(fontsize=7)
    dk.save(fig, path)


def fig_lattice_cell(path):
    """!
    @brief The via lattice cell: plan view with the heat converging radially on the barrel, the section with the resistance chain, and the temperature profile (Krogh).
    @param path Output file.
    @return None.
    """
    import constriction as cr
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(14, 4.6), gridspec_kw={"width_ratios": [1, 1.1, 1]})
    R, ar = 1.0, 0.12
    a.set_aspect("equal")
    a.add_patch(Circle((0, 0), R, facecolor="#f6e3c4", edgecolor="k"))
    a.add_patch(Circle((0, 0), ar, facecolor="#b87333", edgecolor="k"))
    for th in np.linspace(0, 2 * np.pi, 16, endpoint=False):
        a.annotate("", xy=(ar * 1.4 * math.cos(th), ar * 1.4 * math.sin(th)), xytext=(0.95 * R * math.cos(th), 0.95 * R * math.sin(th)), arrowprops=dict(arrowstyle="->", color="#d62728"))
    a.set_xlim(-1.15, 1.15)
    a.set_ylim(-1.15, 1.15)
    a.set_title("PLAN of one plane: the heat of the cell\nconverges on the barrel (radius a)")
    a.text(0, -1.12, "cell radius R = p / $\\sqrt{\\pi}$ (Wigner-Seitz disc of the lattice)", ha="center", fontsize=7)
    b.axis("off")
    b.set_xlim(0, 10)
    b.set_ylim(0, 8)
    for k, y in enumerate((6.4, 4.4, 2.4, 0.4)):
        dk.layer(b, 0.5, y, 9, 0.5, dk.COPPER, f"plane {k + 1}", 7)
    for y in (5.0, 3.0, 1.0):
        dk.layer(b, 0.5, y, 9, 1.4 - 0.0, dk.FR4, "", 7)
    dk.layer(b, 4.7, 0.4, 0.6, 6.5, "#b87333", "", 7)
    for y in (6.65, 4.65, 2.65, 0.65):
        dk.resistor(b, 1.0, 4.7, y + 0.25, "")             # the well sits in the plane, between the area mean and the barrel wall
    b.text(2.8, 7.5, "constriction $R_c$ per plane\n$(\\ln(R/r_t)-3/4)/(2\\pi S)$", ha="center", fontsize=7, color="#d62728")
    b.text(6.3, 3.5, "barrel $k_{Cu}A/d$\nper gap", fontsize=7)
    b.set_title("SECTION: the models carried only the barrel;\nthe constriction in series is the missing resistance")
    r = np.linspace(ar, R, 200)
    S = 1.0
    t = (R ** 2 * np.log(r / ar) - (r ** 2 - ar ** 2) / 2) / (2 * math.pi * S * (R ** 2 - ar ** 2))
    c.plot(r, t, color="k")
    mean = cr.krogh(S, R, ar) + 0.0
    c.axhline(mean, color="#1f77b4", ls="--", label="area mean (what a ring or a tile carries)")
    c.axhline(0, color="#d62728", ls=":", label="wall of the barrel")
    c.set_xlabel("r (cell radius = 1)")
    c.set_ylabel("temperature above the wall per watt of the via (S = 1)")
    c.legend(fontsize=7)
    c.set_title("PROFILE (closed form): mean minus wall = $R_c$")
    dk.save(fig, path)


def fig_tile_grid(path):
    """!
    @brief The tile grid over a 5 x 5 array: the program's tiles, the 1 mm tiles, the self-term, and the tiles against the edge of a source (aligned and not aligned).
    @param path Output file.
    @return None.
    """
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.8))
    pitch, n = 1.2, 5
    xs = (np.arange(n) - (n - 1) / 2) * pitch
    for ax, t, title in ((axs[0], 2.5, "program: tiles of 2.5 to 5 mm\n(a tile holds many vias; the mean of the tile is read)"),
                         (axs[1], 1.0, "corrected: tiles of 1 mm\n(self-term: the via is read at its wall, not at the tile mean)")):
        ax.set_aspect("equal")
        lim = 4.0
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        for g in np.arange(-lim, lim + 1e-9, t):
            ax.axvline(g, color="#bbbbbb", lw=0.6)
            ax.axhline(g, color="#bbbbbb", lw=0.6)
        for x in xs:
            for y in xs:
                ax.add_patch(Circle((x, y), 0.15, facecolor="#b87333", edgecolor="k", lw=0.5))
        ax.add_patch(Rectangle((-3, -3), 6, 6, fill=False, edgecolor="#d62728", lw=1.5, ls="--"))
        ax.set_title(title, fontsize=8)
    axs[1].text(0, -3.7, "pitch 1.2 mm, drill 0.3 mm; red dashed = a 6 mm source", ha="center", fontsize=7)
    ax = axs[2]
    ax.set_aspect("equal")
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 6)
    edge = 3.05
    ax.add_patch(Rectangle((edge, 0), 6 - edge, 6, facecolor="#f6c6c6", alpha=0.6))
    for t, col, lab in ((1.0, "#1f77b4", "tile 1.0 mm: edge on a tile line"), (1.5, "#2ca02c", "tile 1.5 mm: edge crosses a tile")):
        for g in np.arange(0, 6.01, t):
            ax.plot([g, g], [0, 6], color=col, lw=0.6 if t == 1.0 else 1.1, alpha=0.7)
    ax.plot([], [], color="#1f77b4", label="1.0 mm tiles")
    ax.plot([], [], color="#2ca02c", label="1.5 mm tiles")
    ax.axvline(edge, color="#d62728", lw=2, label="copper / source edge")
    ax.legend(fontsize=7, loc="lower left")
    ax.set_title("a tile that straddles an edge averages two\ndifferent temperatures (why the tile matters)", fontsize=8)
    dk.save(fig, path)


def fig_krogh_rings(path):
    """!
    @brief The Krogh well in the Lumped rings: a lone via outside the footprint, the ring that carries it, the well per plane, and a dense array.
    @param path Output file.
    @return None.
    """
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 5), gridspec_kw={"width_ratios": [1.1, 1]})
    a.set_aspect("equal")
    a.set_xlim(-8, 8)
    a.set_ylim(-8, 8)
    for k, rr in enumerate((1.5, 2.6, 3.8, 5.2, 6.8)):
        a.add_patch(Circle((0, 0), rr, fill=False, edgecolor="#888888", lw=0.8))
    a.add_patch(Rectangle((-1.5, -1.5), 3, 3, facecolor="#f6c6c6", edgecolor="#d62728"))
    a.text(0, 0, "source", ha="center", fontsize=8)
    a.add_patch(Circle((4.4, 0.0), 0.18, facecolor="#b87333", edgecolor="k"))
    a.annotate("lone via in ring 4\n(ring mean temperature, one radius:\nthe angular gradient is lost)", (4.4, 0), xytext=(1.5, 5.6), arrowprops=dict(arrowstyle="->"), fontsize=8)
    for th in np.linspace(0, 2 * np.pi, 40):
        a.plot([3.8 * math.cos(th)], [3.8 * math.sin(th)], ".", color="#d62728", ms=2)
    a.set_title("PLAN: rings around the footprint; a via outside it sits in one ring", fontsize=9)
    b.axis("off")
    b.set_xlim(0, 10)
    b.set_ylim(0, 8)
    for k, y in enumerate((6.0, 4.0, 2.0)):
        dk.layer(b, 0.5, y, 4.0, 0.5, dk.COPPER, f"ring node, plane {k + 1}", 7)
        dk.resistor(b, 4.5, 7.5, y + 0.25, "$R_c$ well")
        b.add_patch(Rectangle((7.5, y + 0.1), 0.3, 0.3, facecolor="#b87333"))
    b.plot([7.65, 7.65], [2.1, 6.5], color="#b87333", lw=4)
    b.text(8.0, 4.3, "barrel", fontsize=8)
    b.text(0.5, 7.4, "$R_c$ = krogh(S, R$_{cell}$, a); R$_{cell}$ = nearest-neighbour disc (micro well)\n+ cluster disc ln(R/r$_{cl}$)/(2$\\pi$S) (macro well)", fontsize=8)
    b.set_title("SECTION / network: one well per plane in series with the barrel", fontsize=9)
    dk.save(fig, path)


def fig_green_chain(path):
    """!
    @brief The chain that builds the Analytic via correction and the places where the tile and the 64 modes act.
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(13, 4.6)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 6)
    steps = [("cosine series of the\nuniform board\n(M x N modes, 300)", 0.2, "#cfe3f5"), ("tile means y0\n(projection on tiles of size t)", 2.9, "#dff0d8"),
             ("tile response G\nfrom min(M, 64) modes:\nthe program's constant", 5.6, "#fde0dc"), ("+ self-term D\n(sink read at its wall)", 8.3, "#fff2cc"),
             ("(I + G C) y = y0\nC = vias between sheets\n(Nt L) unknowns", 11.0, "#e8dff5")]
    for text, x, col in steps:
        dk.box(ax, x, 2.6, 2.3, 1.8, text, col, size=8)
    for x in (2.5, 5.2, 7.9, 10.6):
        dk.arrow(ax, x, 3.5, x + 0.4, 3.5)
    ax.text(6.5, 1.5, "rule S4: tile t from the vias (d$_{nn}$, a), then M$_G$ $\\geq$ 2 W / t modes for G;\ncost ~ (Nt L)$^3$ for the solve and L$^2$ N$_g$ Nt$^2$ M$_g$ for G", ha="center", fontsize=9)
    ax.text(6.5, 5.3, "the board is cut in tiles only to couple the vias: the tile must resolve the cluster and stay larger than the barrel", ha="center", fontsize=9)
    dk.save(fig, path, "Analytic via correction: where the tile and the modes enter")


def main():
    """!
    @brief Draw every diagram.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    for fn, name in ((fig_jacobi_sor, "fig_01_jacobi_and_sor_iteration.png"), (fig_spectrum, "fig_02_spectrum_and_omega_curve.png"), (fig_rayleigh, "fig_03_rayleigh_and_lanczos_picture.png"),
                     (fig_lattice_cell, "fig_04_via_lattice_cell_constriction.png"), (fig_tile_grid, "fig_05_tile_grid_over_a_via_array.png"),
                     (fig_krogh_rings, "fig_06_krogh_well_in_the_lumped_rings.png"), (fig_green_chain, "fig_07_tile_green_function_chain.png")):
        fn(OUT / name)
        print("wrote", name)


if __name__ == "__main__":
    main()
