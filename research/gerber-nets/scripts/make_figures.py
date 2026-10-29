"""!
@file make_figures.py
@brief The pictures of phase 3: tracks at any angle on the pixel grid, nets and Joule heat (synthetic board and our IC board), and the electrical prototype with a link.
@details Figures are committed on purpose (the README files link to them); the caches they read are in out/ and are made by the studies. Run: .venv/bin/python research/gerber-nets/scripts/make_figures.py (from the repository root).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-nets in order)

import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap, LogNorm
from scipy import ndimage

import joule
import native_gerber as ng
import our_board
from nets import disc, net_pads

from paths import FIGURES as OUT, OUT as CACHE                           # kept in the repository on purpose: the README files link to them


def labelled_cmap(n, seed=1):
    """!
    @brief Colour map with a random colour per label and black for the background.
    @param n Number of labels.
    @param seed Random seed.
    @return ListedColormap.
    """
    rng = np.random.default_rng(seed)
    cols = rng.uniform(0.25, 1.0, (n + 1, 3))
    cols[0] = (0.08, 0.08, 0.08)
    return ListedColormap(cols)


def fig_angles():
    """!
    @brief Thin tracks at an angle on three pixel sizes, coloured by 4-connected piece.
    @return None.
    """
    import make_synthetic as ms                                      # gerbonara writes the tracks: imported here so that the rest of this module (and study_references.py) runs without it
    cases = [(0.1, 30), (0.2, 30), (0.2, 45)]
    pixels = (0.1, 0.05, 0.025)
    fig, axs = plt.subplots(len(cases), len(pixels), figsize=(10, 9))
    for i, (w, ang) in enumerate(cases):
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        obj, geom = ms.line(1.0, 1.0, 1.0 + 30 * ca, 1.0 + 30 * sa, w)
        gf, _ = ms.build([(obj, geom, True)])
        ms.OUT.mkdir(parents=True, exist_ok=True)
        gf.save(ms.OUT / "fig_tmp.gbr")
        layer = ng.Layer((ms.OUT / "fig_tmp.gbr").read_text())
        bb = layer.bbox()
        cx, cy = 1.0 + 15 * ca, 1.0 + 15 * sa                       # a 2 x 2 mm window at the middle of the track
        for j, pix in enumerate(pixels):
            cv = ng.Canvas(cx - 1.0, cy + 1.0, 2.0, 2.0, pix)
            layer.draw(cv)
            lab, n = ndimage.label(cv.mask)
            ax = axs[i, j]
            ax.imshow(lab, cmap=labelled_cmap(n), interpolation="nearest", extent=(0, 2, 0, 2))
            ax.set_title(f"w = {w} mm, {ang} deg, pixel {pix} mm\n{w / pix:.0f} px across, {n} piece{'s' if n != 1 else ''} in this 2 mm", fontsize=9)
            ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("A thin track at an angle on the pixel grid (colour = one 4-connected piece)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "fig_01_angles_pixel_grid.png", dpi=110)
    plt.close(fig)


def synthetic_nets_gerber():
    """!
    @brief A small synthetic Gerber of our own with X2 net attributes (`%TO.N,<net>*%` ended by `%TD*%`): three nets on a 40 x 26 mm board, round apertures only, 6 decimals in mm.
    @details VIN: a 0.8 mm track with a 0.25 mm neck in the middle and a 0.4 mm dead-end spur, a pad at each end; SIG: a 0.3 mm track with a kink, a pad at each end; GND: a 1.6 mm track with three pads.
    @return Gerber text.
    """
    def c(v):
        """!@brief A length in mm as the integer of a 4.6 coordinate. @param v Length (mm). @return String of digits."""
        return str(int(round(v * 1e6)))

    def path(points):
        """!@brief A track through points with the current aperture. @param points List of (x, y) in mm. @return Gerber lines."""
        out = f"X{c(points[0][0])}Y{c(points[0][1])}D02*\n"
        return out + "".join(f"X{c(x)}Y{c(y)}D01*\n" for x, y in points[1:])

    def flash(points):
        """!@brief Flashes of the current aperture. @param points List of (x, y) in mm. @return Gerber lines."""
        return "".join(f"X{c(x)}Y{c(y)}D03*\n" for x, y in points)

    t = "%FSLAX46Y46*%\n%MOMM*%\n"
    for num, d in ((10, 0.8), (11, 0.25), (12, 0.4), (13, 2.4), (14, 0.3), (15, 1.6), (16, 1.2)):
        t += f"%ADD{num}C,{d}*%\n"
    t += "%TO.N,VIN*%\nD10*\n" + path([(3, 4), (14, 4)]) + "D11*\n" + path([(14, 4), (24, 4)]) + "D10*\n" + path([(24, 4), (37, 4)])
    t += "D12*\n" + path([(10, 4), (10, 10)]) + "D13*\n" + flash([(3, 4), (37, 4)]) + "%TD*%\n"
    t += "%TO.N,SIG*%\nD14*\n" + path([(3, 20), (15, 20), (20, 15), (25, 20), (37, 20)]) + "D16*\n" + flash([(3, 20), (37, 20)]) + "%TD*%\n"
    t += "%TO.N,GND*%\nD15*\n" + path([(3, 12.5), (37, 12.5)]) + "D13*\n" + flash([(3, 12.5), (20, 12.5), (37, 12.5)]) + "%TD*%\n"
    return t + "M02*\n"


def fig_nets(text=None, target="VIN", filename="fig_02_nets_and_joule.png", title=None, pix=0.05):
    """!
    @brief A synthetic board of our own coloured by net, and the potential and Joule heat of one net at 1 A between its two farthest pads.
    @param text Gerber text (default: the small board of figure 02).
    @param target Net to solve.
    @param filename Output file name in figures/.
    @param title Title of the first panel (default: the generic one).
    @param pix Pixel size (mm).
    @return None.
    """
    layer = ng.Layer(synthetic_nets_gerber() if text is None else text)
    bb = layer.bbox()
    # Anchor the pixel lattice so that no track edge falls exactly on a pixel centre (a tie that would make a 0.25 mm neck 0.30 mm wide, README 4.23): pixel centres at multiples of 0.05 mm in y and at odd multiples of 0.025 mm in x
    x_left, y_top = np.floor((bb[0] - 0.2) / pix) * pix, (np.ceil((bb[3] + 0.2) / pix) + 0.5) * pix
    w, h = bb[2] + 0.2 - x_left, y_top - (bb[1] - 0.2)
    cv_all = ng.Canvas(x_left, y_top, w, h, pix)
    layer.draw(cv_all)
    lab, ncomp = ndimage.label(cv_all.mask)
    nets = layer.net_names()
    owner = {}
    for net in nets:
        cv = ng.Canvas(x_left, y_top, w, h, pix)
        layer.draw(cv, [net])
        for c in np.unique(lab[cv.mask & (lab > 0)]):
            owner.setdefault(int(c), set()).add(net)
    idx = {n: k + 1 for k, n in enumerate(nets)}
    img = np.zeros(lab.shape, int)
    for c, v in owner.items():
        if len(v) == 1:
            img[lab == c] = idx[next(iter(v))]
    img[(lab > 0) & (img == 0)] = len(nets) + 1                         # copper without a net: grey
    cm = plt.get_cmap("tab20")(np.linspace(0, 1, 20))
    cols = np.vstack([[0.08, 0.08, 0.08, 1], [cm[k % 20] for k in range(len(nets))], [[0.55, 0.55, 0.55, 1]]])
    # Constrained layout: with equal-aspect images and two colour bars tight_layout shifted the first panel out of the figure and cut its title
    fig, axs = plt.subplots(1, 3, figsize=(16, 5.6), layout="constrained")
    ext = (cv_all.x0, cv_all.x0 + lab.shape[1] * pix, cv_all.y0 - lab.shape[0] * pix, cv_all.y0)
    axs[0].imshow(img, cmap=ListedColormap(cols), vmin=0, vmax=len(cols) - 1, interpolation="nearest", extent=ext)      # fixed limits: a net keeps its colour whichever labels occur
    axs[0].set_title(title or f"synthetic board with X2 net attributes: {len(nets)} nets (colours),\ngrey would be copper with no net", fontsize=9)
    # Joule heat of one net: the largest piece of the target net with two or more pads, between its two farthest pads, 1 A
    net = target
    pads = np.array(net_pads(layer, net))
    pieces = [c for c, v in owner.items() if v == {net}]
    sizes = np.bincount(lab.ravel())
    best = max((c for c in pieces if sum(lab[int((cv_all.y0 - p[1]) / pix), int((p[0] - cv_all.x0) / pix)] == c for p in pads) >= 2), key=lambda c: sizes[c])
    pa = np.array([p for p in pads if lab[int((cv_all.y0 - p[1]) / pix), int((p[0] - cv_all.x0) / pix)] == best])
    d = np.hypot(pa[:, None, 0] - pa[None, :, 0], pa[:, None, 1] - pa[None, :, 1])
    i, j = np.unravel_index(d.argmax(), d.shape)
    mask = lab == best
    src = disc(mask.shape, cv_all, pa[i][0], pa[i][1], 0.25) & mask
    snk = disc(mask.shape, cv_all, pa[j][0], pa[j][1], 0.25) & mask
    r, v, q = joule.solve_net(mask, joule.resistivity(20.0) / 35e-6, src, snk, 1.0)
    ys, xs = np.where(mask)
    y0, y1, x0, x1 = max(ys.min() - 20, 0), ys.max() + 20, max(xs.min() - 20, 0), xs.max() + 20
    ext2 = (cv_all.x0 + x0 * pix, cv_all.x0 + x1 * pix, cv_all.y0 - y1 * pix, cv_all.y0 - y0 * pix)
    im = axs[1].imshow(np.where(mask, v, np.nan)[y0:y1, x0:x1], cmap="viridis", interpolation="nearest", extent=ext2)
    axs[1].set_title(f"net {net}: potential at 1 A, R = {r * 1000:.0f} mOhm (35 um copper)", fontsize=9)
    fig.colorbar(im, ax=axs[1], label="V")
    im = axs[2].imshow(np.where(mask, q / pix ** 2 * 1000.0, np.nan)[y0:y1, x0:x1], cmap="inferno", interpolation="nearest", extent=ext2, norm=LogNorm(vmin=max(q.max() / pix ** 2 * 1000.0 * 1e-3, 1e-12), vmax=q.max() / pix ** 2 * 1000.0))
    axs[2].set_title(f"Joule heat density, total {q.sum() * 1000:.0f} mW (= I2R); pads are the dots", fontsize=9)
    fig.colorbar(im, ax=axs[2], label="mW / mm2")
    for ax in axs[1:]:
        ax.plot(pa[:, 0], pa[:, 1], "w.", ms=3)
        ax.plot([pa[i][0], pa[j][0]], [pa[i][1], pa[j][1]], "wo", ms=7, mfc="none")
    fig.savefig(OUT / filename, dpi=110)
    plt.close(fig)


def fig_pdn_links():
    """!
    @brief The electrical scenario on the rectangle board (needs out/pdn_links.npz from study_pdn_links.py): potential and Joule heat of the copper with a 5 V source, a 1.5 A load and a 0.1 ohm link between two pieces of one net.
    @return None.
    """
    path = CACHE / "pdn_links.npz"
    if not path.exists():
        print("figure 04 skipped: run study_pdn_links.py first")
        return
    d = np.load(path)
    V, q, mask = d["V"], d["q"], d["mask"]
    ext = (0, 40, 0, 30)
    fig, axs = plt.subplots(1, 2, figsize=(14, 5))
    pot = np.ma.masked_where(~mask | np.isnan(V), V)
    im = axs[0].imshow(pot, origin="lower", extent=ext, cmap="viridis", interpolation="nearest")
    axs[0].imshow(np.ma.masked_where(~(mask & np.isnan(V)), np.ones(mask.shape)), origin="lower", extent=ext, cmap="Greys", vmin=0, vmax=2, interpolation="nearest")
    fig.colorbar(im, ax=axs[0], fraction=0.046, label="V")
    axs[0].set_title("potential: 5 V at the source pad; the grey pieces are floating (no pad: no current)", fontsize=9)
    heat = np.ma.masked_where(~mask | (q <= 0), np.log10(np.maximum(q, 1e-12)))
    im = axs[1].imshow(heat, origin="lower", extent=ext, cmap="inferno", interpolation="nearest")
    fig.colorbar(im, ax=axs[1], fraction=0.046, label="log10 of W per pixel (0.2 mm)")
    axs[1].set_title(f"Joule heat of the copper: {q.sum() * 1e3:.1f} mW in all; the 0.1 ohm link makes 225 mW", fontsize=9)       # from the cache (the text said 12.6 mW until the review)
    for a in axs:
        a.annotate("5 V in", (6, 11), (6, 24), color="k", fontsize=8, arrowprops={"arrowstyle": "->"})    # the label sits on the white page in both panels: white text there was invisible
        a.annotate("0.1 ohm link\n(bead)", (31, 15.0), (29, 24.5), color="c", fontsize=8, arrowprops={"arrowstyle": "->", "color": "c"})
        a.annotate("1.5 A load", (15, 7), (4, 5), color="c", fontsize=8, arrowprops={"arrowstyle": "->", "color": "c"})
        a.plot([35, 25], [15, 7], color="c", linestyle=":", linewidth=1.2)
        a.set_xlabel("mm")
    fig.tight_layout()
    fig.savefig(OUT / "fig_04_pdn_links.png", dpi=105)
    plt.close(fig)


def fig_network_diagram():
    """!
    @brief Diagrams of the electrical prototype: pieces of one net joined by a link, the equivalent circuit with the numbers of the scenario, the pixel network of a piece of copper and the energy balance.
    @return None.
    """
    from matplotlib.patches import Rectangle, FancyBboxPatch
    fig, axs = plt.subplots(2, 2, figsize=(16, 9.4))
    # 1. pieces of copper, terminals, link, floating piece
    ax = axs[0, 0]
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 10)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((0.5, 3), 6, 4, facecolor="#e0a458", edgecolor="k"))
    ax.add_patch(Rectangle((6.5, 4.5), 4, 1, facecolor="#e0a458", edgecolor="k"))
    ax.add_patch(Rectangle((12.5, 3), 6, 4, facecolor="#e0a458", edgecolor="k"))
    ax.add_patch(Rectangle((7.5, 8), 3, 1.5, facecolor="0.8", edgecolor="k", linestyle="--"))
    ax.add_patch(Rectangle((1, 4.2), 1.6, 1.6, facecolor="#2ca02c", edgecolor="k"))
    ax.add_patch(Rectangle((16.4, 4.2), 1.6, 1.6, facecolor="#d62728", edgecolor="k"))
    ax.add_patch(Rectangle((10.0, 4.5), 0.5, 1.0, facecolor="#1f77b4", edgecolor="k"))
    ax.add_patch(Rectangle((12.5, 4.5), 0.5, 1.0, facecolor="#1f77b4", edgecolor="k"))
    ax.text(1.8, 5.0, "5 V\nsource", ha="center", va="center", fontsize=7, color="w")
    ax.text(17.2, 5.0, "1.5 A\nsink", ha="center", va="center", fontsize=7, color="w")
    ax.annotate("", (12.5, 5.0), (10.5, 5.0), arrowprops={"arrowstyle": "-", "linewidth": 0})
    ax.text(11.5, 2.0, "link: 0.1 ohm\n(bead, shunt,\njumper, fuse)", ha="center", va="top", fontsize=8, color="#1f77b4")      # below the gap, clear of piece B
    ax.plot([10.5, 12.5], [5.0, 5.0], color="#1f77b4", linewidth=2, linestyle=":")
    ax.text(3.5, 7.4, "piece A (one net)", ha="center", fontsize=8)
    ax.text(15.5, 7.4, "piece B (the same net)", ha="center", fontsize=8)
    ax.text(9, 9.75, "floating piece: no pad of a source or a load, no current, no heat", ha="center", va="bottom", fontsize=7, color="0.3")      # above the box, not across it
    ax.set_title("1. one net in several pieces: the copper does not join A and B;\na part does (the link). Currents are inputs per pad", fontsize=9)
    # 2. equivalent circuit
    ax = axs[0, 1]
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 8)
    ax.axis("off")
    def res(x0, x1, y, label, color="k"):
        """!
        @brief A resistor symbol.
        @param x0 Left.
        @param x1 Right.
        @param y Height.
        @param label Text.
        @param color Colour.
        @return None.
        """
        ax.plot([x0, x0 + 0.5], [y, y], color=color)
        ax.add_patch(Rectangle((x0 + 0.5, y - 0.35), x1 - x0 - 1, 0.7, fill=False, edgecolor=color, linewidth=1.5))
        ax.plot([x1 - 0.5, x1], [y, y], color=color)
        ax.text((x0 + x1) / 2, y + 0.7, label, ha="center", fontsize=8, color=color)
    ax.add_patch(plt.Circle((1.2, 4), 0.7, fill=False, linewidth=1.5))
    ax.text(1.2, 4, "5 V", ha="center", va="center", fontsize=8)
    ax.plot([1.9, 3], [4, 4], color="k")
    res(3, 7, 4, "copper A\n(10.1 mW)")
    res(7, 11, 4, "link 0.1 ohm\n(225 mW)", "#1f77b4")
    res(11, 15, 4, "copper B\n(2.2 mW)")
    ax.plot([15, 16.3], [4, 4], color="k")
    ax.annotate("", (17.8, 2.4), (17.8, 5.6), arrowprops={"arrowstyle": "->", "linewidth": 2, "color": "#d62728"})
    ax.plot([16.3, 17.8, 17.8], [4, 4, 5.6], color="k")
    ax.text(18.2, 4, "1.5 A\nload\n7263 mW", fontsize=8, color="#d62728", va="center")
    ax.plot([1.2, 1.2, 17.8, 17.8], [3.3, 1.8, 1.8, 2.4], color="k")
    ax.text(9.5, 1.2, "return (ground)", ha="center", fontsize=8)
    ax.text(9.5, 7.1, "the load takes V at its pad x I = 4.84 V x 1.5 A: that is the power of the IC", ha="center", fontsize=8)
    ax.set_title("2. the equivalent circuit of the scenario (values of the prototype)", fontsize=9)
    # 3. pixel network
    ax = axs[1, 0]
    ax.set_xlim(-0.5, 8.5)
    ax.set_ylim(-0.5, 5.5)
    ax.set_aspect("equal")
    ax.axis("off")
    for i in range(9):
        for j in range(6):
            if i < 8:
                ax.plot([i, i + 1], [j, j], color="#b8651b", linewidth=1.6)
            if j < 5:
                ax.plot([i, i], [j, j + 1], color="#b8651b", linewidth=1.6)
            ax.plot(i, j, "o", color="k", markersize=3)
    ax.add_patch(FancyBboxPatch((-0.3, 1.7), 0.6, 1.6, boxstyle="round,pad=0.05", facecolor="#2ca02c", alpha=0.7))
    ax.add_patch(FancyBboxPatch((7.7, 1.7), 0.6, 1.6, boxstyle="round,pad=0.05", facecolor="#d62728", alpha=0.7))
    ax.text(3.9, -0.45, "each link is the sheet resistance Rs = rho / t = 0.48 mohm per square (35 um copper);\nthe pad terminal is one node tied to the pixels under it", ha="center", fontsize=8)
    ax.set_title("3. inside a piece: a mesh of resistors, one per pixel pair;\nthe pad terminals hold the potential or take the current", fontsize=9)
    # 4. energy balance
    ax = axs[1, 1]
    import study_pdn_links as spl                                         # the numbers of the scenario, solved here (they were typed in until the review)
    r = spl.scenario()[1]
    names = ["source (5 V x 1.5 A)", "load: the IC (4.84 V x 1.5 A)", "link 0.1 ohm", "copper (all pieces)", "|balance error|"]
    vals = [round(v * 1e3, 4) for v in (r["p_source"], r["p_sinks"], r["p_links"], r["p_copper"], abs(r["p_source"] - r["p_copper"] - r["p_links"] - r["p_sinks"]))]
    ax.barh(names[::-1], vals[::-1], color=["#999999", "#e0a458", "#1f77b4", "#d62728", "#2ca02c"])
    for k, v in enumerate(vals[::-1]):
        ax.text(v * 1.1, k, f"{v:.4g} mW", va="center", fontsize=8)
    ax.set_xscale("log")
    ax.set_xlim(1e-4, 1e5)
    ax.set_xlabel("power (mW, log scale)")
    ax.set_title("4. the energy balance closes: source = copper + link + load\n(the copper is 0.16 % of the power; the link 3 %; the IC the rest)", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_05_network_diagram.png", dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Make the figures of this investigation.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_angles()
    fig_nets()
    fig_nets(our_board.gerber_text(), "S1", "fig_03_ic_board_nets_and_joule.png", f"our IC board (our_board.py):\n{our_board.N_SIG} signal nets on circular arcs and GND (nine colours)", pix=0.025)
    fig_pdn_links()
    fig_network_diagram()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
