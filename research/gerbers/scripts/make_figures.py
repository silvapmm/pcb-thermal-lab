"""!
@file make_figures.py
@brief Pictures of what the research does, written to figures/ (committed, linked from the README files): thin tracks on the pixel grid, nets and the Joule heat of one net on a synthetic board of our own, and the mapping of real copper (a window of the MIT-licensed Stormduino board) to cells.
@details Needs numpy, scipy, matplotlib, shapely and gerbonara. Run: .venv/bin/python research/gerbers/scripts/make_figures.py (from the repository root)
"""

import _bootstrap  # noqa: F401  (puts research/gerbers/lib on the import path)

import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap, LogNorm
from scipy import ndimage

import conduction as cd
import joule
import make_synthetic as ms
import native_gerber as ng
import our_board
import scenarios as sc
import windows
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
    fig, axs = plt.subplots(1, 3, figsize=(16, 5.6))
    ext = (cv_all.x0, cv_all.x0 + lab.shape[1] * pix, cv_all.y0 - lab.shape[0] * pix, cv_all.y0)
    axs[0].imshow(img, cmap=ListedColormap(cols), vmin=0, vmax=len(cols) - 1, interpolation="nearest", extent=ext)      # fixed limits: a net keeps its colour whichever labels occur
    axs[0].set_title(title or f"synthetic board with X2 net attributes: {len(nets)} nets (colours), grey would be copper with no net", fontsize=9)
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
    fig.tight_layout()
    fig.savefig(OUT / filename, dpi=110)
    plt.close(fig)


def fig_mapping():
    """!
    @brief One real window: the 0.1 mm copper mask, the fill fraction per 1 mm cell (today) and the ratio of the flow-based cell conductance to the arithmetic one.
    @return None.
    """
    windows.BOARDS = ["storm"]                                          # Stormduino (MIT): the only board whose licence allows a picture of it
    windows.FILE = windows.OUT / "windows_storm.npz"
    masks, meta = windows.load()
    k = 1
    mask = masks[k]
    S = cd.sheet_of(mask[::-1])
    n = 10                                                              # pixels per 1 mm cell
    a, b = float(S.max()), float(S.min())
    f = (cd.cell_blocks(S, n) == a).mean(axis=(2, 3))
    gx, gy = cd.dual_faces(S, n, 0)
    tot = np.zeros(f.shape); cnt = np.zeros(f.shape)
    tot[:, :-1] += gx; cnt[:, :-1] += 1; tot[:, 1:] += gx; cnt[:, 1:] += 1
    tot[:-1, :] += gy; cnt[:-1, :] += 1; tot[1:, :] += gy; cnt[1:, :] += 1
    flow = tot / cnt
    arith = cd.map_power(f, 1.0, a, b)
    fig, axs = plt.subplots(1, 3, figsize=(16, 5.4))
    axs[0].imshow(mask, cmap="copper", interpolation="nearest", extent=(0, 36, 0, 36))
    axs[0].set_title("Stormduino (MIT): 36 x 36 mm of real copper, 0.1 mm pixels", fontsize=9)
    im = axs[1].imshow(f[::-1], cmap="viridis", vmin=0, vmax=1, interpolation="nearest", extent=(0, 36, 0, 36))
    axs[1].set_title("copper fraction of each 1 mm cell (what the program uses today)", fontsize=9)
    fig.colorbar(im, ax=axs[1])
    im = axs[2].imshow((flow / arith)[::-1], cmap="RdBu", vmin=0.2, vmax=1.8, interpolation="nearest", extent=(0, 36, 0, 36))
    axs[2].set_title("flow-based / arithmetic cell conductance\nred (< 1): the fraction overestimates it (board too cool)\nblue (> 1): it underestimates it", fontsize=9)
    fig.colorbar(im, ax=axs[2])
    for ax in axs:
        ax.set_xlabel("mm")
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_copper_mapping_to_cells.png", dpi=110)
    plt.close(fig)


def fig_board_thermal():
    """!
    @brief The IC board of our own (our_board.py) as a thermal problem: 1 W under the IC, border held at 0 K, h = 10 W/m2K. The temperature rise resolved pixel by pixel, and the difference of the 1 mm cell models (fill fraction today, flow-based faces) from it.
    @return None.
    """
    layer = ng.Layer(our_board.gerber_text())
    cv = ng.Canvas(0.0, our_board.SIZE, our_board.SIZE, our_board.SIZE, 0.1)
    layer.draw(cv)
    S = cd.sheet_of(cv.mask[::-1])
    power, fixed, (y0, y1, x0, x1) = sc.box_scenario(S.shape, 0.1, 6.0)
    ref = sc.pixel_reference(S, 0.1, power, 10.0, fixed)
    n = 10
    cy, cx = S.shape[0] // n, S.shape[1] // n
    pw = power.reshape(cy, n, cx, n).sum(axis=(1, 3))
    fx = cd.cell_blocks(fixed, n).mean(axis=(2, 3)) >= 0.5
    ref_cells = ref.reshape(cy, n, cx, n).mean(axis=(1, 3))
    faces = sc.coarse_faces(S, n, cd.S_CU, cd.S_LAM)
    fig, axs = plt.subplots(1, 3, figsize=(16, 5.4))
    ext = (0, our_board.SIZE, 0, our_board.SIZE)
    im = axs[0].imshow(ref[::-1], cmap="inferno", interpolation="nearest", extent=ext)
    axs[0].contour(cv.mask[::-1].astype(float), levels=[0.5], colors="w", linewidths=0.3, extent=ext, origin="lower")
    axs[0].set_title("resolved temperature rise (K): 1 W under the IC, border at 0 K", fontsize=9)
    fig.colorbar(im, ax=axs[0])
    for ax, key, label in ((axs[1], "fill fraction (today)", "fill fraction per 1 mm cell (today)"), (axs[2], "flow-based faces", "flow-based faces on 1 mm cells")):
        gx, gy = faces[key]
        T = sc.solve_general(gx, gy, 1.0, pw, 10.0, fx)
        d = T - ref_cells
        im = ax.imshow(d[::-1], cmap="RdBu_r", vmin=-15, vmax=15, interpolation="nearest", extent=ext)
        ax.set_title(f"{label}: difference from the resolved field (K)\nheater mean {100 * (T[y0 // n:y1 // n, x0 // n:x1 // n].mean() / ref[y0:y1, x0:x1].mean() - 1):+.1f} %", fontsize=9)
        fig.colorbar(im, ax=ax)
    for ax in axs:
        ax.set_xlabel("mm")
    fig.tight_layout()
    fig.savefig(OUT / "fig_05_ic_board_thermal.png", dpi=110)
    plt.close(fig)


def fig_gerber_render():
    """!
    @brief The Gerber of our IC board drawn like a Gerber viewer shows it: copper on the board, plated holes, net names at the test points, and a close-up of the IC with its pads and thermal vias (0.0125 mm pixels).
    @return None.
    """
    layer = ng.Layer(our_board.gerber_text())
    green, gold = np.array([0.04, 0.26, 0.13]), np.array([0.86, 0.62, 0.27])
    fig, axs = plt.subplots(1, 2, figsize=(14, 6.4), gridspec_kw={"width_ratios": [1.0, 1.0]})
    for ax, (x0, y0, size, pix) in zip(axs, ((0.0, 0.0, our_board.SIZE, 0.025), (14.0, 14.0, 12.0, 0.0125))):
        cv = ng.Canvas(x0, y0 + size, size, size, pix)
        layer.draw(cv)
        img = np.where(cv.mask[..., None], gold, green)
        ax.imshow(img, extent=(x0, x0 + size, y0, y0 + size), interpolation="nearest")
        for x, y, d in our_board.holes():
            if x0 - 1 < x < x0 + size + 1 and y0 - 1 < y < y0 + size + 1:
                ax.add_patch(plt.Circle((x, y), d / 2.0, facecolor="#101010", edgecolor="none"))
        ax.set_xlim(x0, x0 + size)
        ax.set_ylim(y0, y0 + size)
        ax.set_xlabel("mm")
    for k in range(our_board.N_SIG):
        x, y = our_board.end_point(k)
        axs[0].annotate(our_board.net_name(k), (x, y), textcoords="offset points", xytext=(5, 5), color="w", fontsize=8)
        px, py = our_board.ic_pad(k)
        axs[1].annotate(our_board.net_name(k), (px, py), textcoords="offset points", xytext=(6, 6), color="w", fontsize=8)
    axs[0].annotate("GND ring and spoke", (our_board.CX - 14, our_board.CY + 17.2), color="w", fontsize=8)
    axs[0].set_title("our IC board as a Gerber viewer would draw it: copper (gold), plated holes (black), 40 x 40 mm", fontsize=9)
    axs[1].set_title("close-up of the IC: exposed pad with four thermal vias and eight pads (12 x 12 mm)", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_06_ic_board_gerber_render.png", dpi=110)
    plt.close(fig)


def fig_import_end_to_end():
    """!
    @brief The import path end to end on two boards (needs out/import_end_to_end.npz from study_import_end_to_end.py): the copper and holes imported from the files, the temperature of the top layer resolved at the pixel grid, and the difference of the program as it is and of the imported path from it.
    @return None.
    """
    path = CACHE / "import_end_to_end.npz"
    if not path.exists():
        print("figure 07 skipped: run study_import_end_to_end.py first")
        return
    d = np.load(path)
    fig, axs = plt.subplots(2, 4, figsize=(17, 8.6))
    for r, (tag, name) in enumerate((("storm", "Stormduino (MIT), 2 layers, 109 plated holes"), ("ours", "our IC board, 1 layer, 16 plated holes"))):
        cov, holes, hx = d[f"{tag}_cov"], d[f"{tag}_holes"], d[f"{tag}_heater"]
        ref, today, imp = d[f"{tag}_fine"], d[f"{tag}_today"], d[f"{tag}_flow_coverage"]
        h, w = ref.shape
        ext = (0, w, 0, h)
        green, gold = np.array([0.04, 0.26, 0.13]), np.array([0.86, 0.62, 0.27])
        axs[r, 0].imshow(np.where(cov[..., None] > 0.5, gold, green), extent=ext, interpolation="nearest")      # the mask has 10 pixels per mm, the board h x w mm
        for x, y, dd in holes:
            axs[r, 0].add_patch(plt.Circle((x, y), max(dd, 0.35) / 2.0 + 0.2, facecolor="#101010", edgecolor="w", linewidth=0.3))
        axs[r, 0].add_patch(plt.Rectangle((hx[0] - 3, hx[1] - 3), 6, 6, fill=False, edgecolor="c", linewidth=1.2))
        axs[r, 0].set_title(f"{name}\ntop copper from the Gerber, holes from the drill file, heater (cyan)", fontsize=8)
        im = axs[r, 1].imshow(ref, origin="lower", extent=ext, cmap="inferno")
        axs[r, 1].set_title("temperature rise of the top layer (K)\nreference: the program on the pixel grid (0.1 mm)", fontsize=8)
        fig.colorbar(im, ax=axs[r, 1], fraction=0.046)
        lim = 0.15 * ref.max()
        for c, (fld, label) in enumerate(((today, "the program as it is (one zone per cell, fill = copper fraction)"), (imp, "imported path (flow-based faces, coverage mask)")), start=2):
            sl = (slice(int(hx[1] - 3), int(hx[1] + 3)), slice(int(hx[0] - 3), int(hx[0] + 3)))
            err = 100 * (fld[sl].mean() / ref[sl].mean() - 1)
            im = axs[r, c].imshow(fld - ref, origin="lower", extent=ext, cmap="RdBu_r", vmin=-lim, vmax=lim)
            axs[r, c].set_title(f"{label}\ndifference from the reference (K); heater mean {err:+.1f} %", fontsize=8)
            fig.colorbar(im, ax=axs[r, c], fraction=0.046)
        for c in range(4):
            axs[r, c].set_xlabel("mm")
    fig.tight_layout()
    fig.savefig(OUT / "fig_07_import_end_to_end.png", dpi=105)
    plt.close(fig)


def fig_import_setup():
    """!
    @brief The set-up of the end-to-end runs (needs out/import_end_to_end.npz): where the 6 x 6 mm heater is on each board, the holes, a 20 mm window round the heater with the 1 mm thermal cells, the copper fraction per cell that the program uses today, and the reference temperature in the window.
    @return None.
    """
    path = CACHE / "import_end_to_end.npz"
    if not path.exists():
        print("figure 08 skipped: run study_import_end_to_end.py first")
        return
    d = np.load(path)
    fig, axs = plt.subplots(2, 4, figsize=(17, 8.6))
    green, gold = np.array([0.04, 0.26, 0.13]), np.array([0.86, 0.62, 0.27])
    for r, (tag, name) in enumerate((("storm", "Stormduino (MIT)"), ("ours", "our IC board"))):
        cov, holes, hx, ref = d[f"{tag}_cov"], d[f"{tag}_holes"], d[f"{tag}_heater"], d[f"{tag}_fine"]
        h, w = ref.shape
        x0, x1 = max(0, int(hx[0] - 10)), min(w, int(hx[0] + 10))
        y0, y1 = max(0, int(hx[1] - 10)), min(h, int(hx[1] + 10))
        rgb = np.where(cov[..., None] > 0.5, gold, green)
        # overview: whole board, window (white) and heater (cyan)
        a = axs[r, 0]
        a.imshow(rgb, extent=(0, w, 0, h), interpolation="nearest")
        for x, y, dd in holes:
            a.add_patch(plt.Circle((x, y), max(dd, 0.35) / 2.0 + 0.2, facecolor="#101010", edgecolor="w", linewidth=0.3))
        a.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, edgecolor="w", linewidth=1.0, linestyle="--"))
        a.add_patch(plt.Rectangle((hx[0] - 3, hx[1] - 3), 6, 6, fill=False, edgecolor="c", linewidth=1.4))
        a.set_title(f"{name}: top copper, {len(holes)} plated holes (black)\nwindow 20 x 20 mm (dashed), heater 6 x 6 mm, 1 W (cyan)", fontsize=8)
        # zoom with the 1 mm thermal cells
        a = axs[r, 1]
        a.imshow(rgb[::-1][h * 10 - y1 * 10: h * 10 - y0 * 10][:, x0 * 10: x1 * 10] if False else rgb[(h - y1) * 10:(h - y0) * 10, x0 * 10:x1 * 10], extent=(x0, x1, y0, y1), interpolation="nearest")
        for x, y, dd in holes:
            if x0 <= x <= x1 and y0 <= y <= y1:
                a.add_patch(plt.Circle((x, y), max(dd, 0.35) / 2.0, facecolor="#101010", edgecolor="w", linewidth=0.3))
        a.set_xticks(range(x0, x1 + 1)); a.set_yticks(range(y0, y1 + 1)); a.grid(color="w", linewidth=0.3, alpha=0.6)
        a.tick_params(labelsize=5)
        a.add_patch(plt.Rectangle((hx[0] - 3, hx[1] - 3), 6, 6, fill=False, edgecolor="c", linewidth=1.6))
        a.set_title("window with the 1 mm cells of the thermal grid\n(copper from the 0.1 mm mask; heater = 6 x 6 cells)", fontsize=8)
        # copper fraction per cell: what the program's one-zone-per-cell path would use
        frac = cov.reshape(h, 10, w, 10).mean(axis=(1, 3))[::-1]
        a = axs[r, 2]
        im = a.imshow(frac[h - y1:h - y0, x0:x1], extent=(x0, x1, y0, y1), cmap="viridis", vmin=0, vmax=1, interpolation="nearest")
        a.add_patch(plt.Rectangle((hx[0] - 3, hx[1] - 3), 6, 6, fill=False, edgecolor="w", linewidth=1.4))
        a.set_title(f"copper fraction per cell (the program's fill today)\nmean under the heater {frac[int(hx[1]-3):int(hx[1]+3), int(hx[0]-3):int(hx[0]+3)].mean():.2f}", fontsize=8)
        fig.colorbar(im, ax=a, fraction=0.046)
        # reference temperature in the window
        a = axs[r, 3]
        im = a.imshow(ref[y0:y1, x0:x1], origin="lower", extent=(x0, x1, y0, y1), cmap="inferno", interpolation="nearest")
        a.add_patch(plt.Rectangle((hx[0] - 3, hx[1] - 3), 6, 6, fill=False, edgecolor="c", linewidth=1.4))
        a.set_title(f"reference temperature rise (K), max {ref.max():.0f} K\nheater block mean {ref[int(hx[1]-3):int(hx[1]+3), int(hx[0]-3):int(hx[0]+3)].mean():.0f} K", fontsize=8)
        fig.colorbar(im, ax=a, fraction=0.046)
        for c in range(4):
            axs[r, c].set_xlabel("mm")
    fig.suptitle("Set-up of the end-to-end runs: heater 6 x 6 mm, 1 W on the top layer; 10 W/m2K on both faces; insulated edges; 1.6 mm board, 35 um copper; plated holes as vias", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_08_import_setup.png", dpi=105)
    plt.close(fig)


def fig_models_our_board():
    """!
    @brief The five models of the program on our IC board (needs out/models_our_board.npz from study_models_our_board.py): the mean rise of the heater from the fine mask and from the four cell mappings, and the error of each mapping against the model's own fine run.
    @return None.
    """
    path = CACHE / "models_our_board.npz"
    if not path.exists():
        print("figure 09 skipped: run study_models_our_board.py first")
        return
    d = np.load(path)
    models, maps, truth, coarse = list(d["models"]), list(d["maps"]), d["truth"], d["coarse"]
    fig, axs = plt.subplots(1, 2, figsize=(14, 5))
    x = np.arange(len(models))
    wd = 0.15
    cols = ["#222222", "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    series = [("fine mask (own truth)", truth)] + [(m, coarse[i]) for i, m in enumerate(maps)]
    for k, (lab, v) in enumerate(series):
        axs[0].bar(x + (k - 2) * wd, v, wd, label=lab, color=cols[k])
    axs[0].set_ylim(0, 160)                                                   # the 3D solid is far above (260 to 390 K) and is cut
    axs[0].set_xticks(x)
    axs[0].set_xticklabels(models)
    axs[0].set_ylabel("mean rise over the heater (K)")
    axs[0].set_title("our IC board, 1 W in 6 x 6 mm: the 3D solid (262 to 392 K) is cut", fontsize=9)
    axs[0].legend(fontsize=7)
    for k, i in enumerate(range(len(maps))):
        err = 100 * (coarse[i] / truth - 1)
        axs[1].bar(x + (k - 1.5) * 0.18, err, 0.18, label=maps[i], color=cols[k + 1])
    axs[1].axhline(0, color="k", linewidth=0.6)
    axs[1].set_xticks(x)
    axs[1].set_xticklabels(models)
    axs[1].set_ylabel("error against the model's own fine run (%)")
    axs[1].set_title("1 mm cells with the cell value of each mapping (positive = too hot)", fontsize=9)
    axs[1].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_09_models_our_board.png", dpi=105)
    plt.close(fig)


def fig_rect_board():
    """!
    @brief The board of squares and rectangles and the five models on it (needs out/models_rect_board_2l.npz and _1l.npz from study_models_rect_board.py): the layout with the heater, and the error of the program's own zones on 1 mm cells against each model's fine run for copper on the cell edges and between them.
    @return None.
    """
    p2, p1 = CACHE / "models_rect_board_2l.npz", CACHE / "models_rect_board_1l.npz"
    if not (p2.exists() and p1.exists()):
        print("figure 10 skipped: run study_models_rect_board.py 1 and 2 first")
        return
    import rect_board as rb
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.8), gridspec_kw={"width_ratios": [1.3, 1, 1]})
    a = axs[0]
    a.imshow(rb.mask(0.0), origin="lower", extent=(0, rb.W, 0, rb.H), cmap="YlOrBr", vmin=-0.2, vmax=1.3)
    for r in rb.rects(0.4):
        a.add_patch(plt.Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, edgecolor="k", linestyle="--", linewidth=0.7))
    hx = rb.heater(0.0)
    a.add_patch(plt.Rectangle((hx[0], hx[1]), hx[2] - hx[0], hx[3] - hx[1], fill=False, edgecolor="c", linewidth=1.6))
    a.set_xticks(range(0, 41, 5)); a.set_yticks(range(0, 31, 5)); a.grid(color="w", linewidth=0.3)
    a.set_title("rect_board: copper (gold), heater 6 x 6 mm 1 W (cyan);\nthe same copper moved 0.4 mm (dashed): off the 1 mm cell edges", fontsize=8)
    models = ["fvm", "fdm", "lumped", "analytic", "solid3d"]
    for ax, path, title in ((axs[1], p1, "one copper layer"), (axs[2], p2, "two layers (bottom empty)")):
        d = np.load(path)
        x = np.arange(len(models))
        for k, (tag, lab, col) in enumerate((("s0", "edges on the cells", "#2ca02c"), ("s4", "edges between cells (0.4 mm)", "#d62728"))):
            err = 100 * (d[f"{tag}_native"] / d[f"{tag}_truth"] - 1)
            ax.bar(x + (k - 0.5) * 0.35, err, 0.35, label=lab, color=col)
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_xticks(x); ax.set_xticklabels(models)
        ax.set_ylabel("program's own zones, 1 mm cells, against fine run (%)")
        ax.set_title(title, fontsize=9)
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_10_rect_board_models.png", dpi=105)
    plt.close(fig)


def fig_pdn_links():
    """!
    @brief The electrical scenario on the rectangle board (needs out/pdn_links.npz from study_pdn_links.py): potential and Joule heat of the copper with a 5 V source, a 1.5 A load and a 0.1 ohm link between two pieces of one net.
    @return None.
    """
    path = CACHE / "pdn_links.npz"
    if not path.exists():
        print("figure 11 skipped: run study_pdn_links.py first")
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
    axs[1].set_title("Joule heat of the copper: 12.6 mW in all; the 0.1 ohm link makes 225 mW", fontsize=9)
    for a in axs:
        a.annotate("5 V in", (6, 11), (6, 24), color="w" if a is axs[1] else "k", fontsize=8, arrowprops={"arrowstyle": "->"})
        a.annotate("0.1 ohm link\n(bead)", (31, 15.0), (29, 24.5), color="c", fontsize=8, arrowprops={"arrowstyle": "->", "color": "c"})
        a.annotate("1.5 A load", (15, 7), (4, 5), color="c", fontsize=8, arrowprops={"arrowstyle": "->", "color": "c"})
        a.plot([35, 25], [15, 7], color="c", linestyle=":", linewidth=1.2)
        a.set_xlabel("mm")
    fig.tight_layout()
    fig.savefig(OUT / "fig_11_pdn_links.png", dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Make the three figures.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_angles()
    fig_nets()
    fig_mapping()
    fig_nets(our_board.gerber_text(), "S1", "fig_04_ic_board_nets_and_joule.png", f"our IC board (our_board.py): {our_board.N_SIG} signal nets on circular arcs and GND (nine colours)", pix=0.025)
    fig_board_thermal()
    fig_gerber_render()
    fig_import_end_to_end()
    fig_import_setup()
    fig_models_our_board()
    fig_rect_board()
    fig_pdn_links()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
