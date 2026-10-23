"""!
@file make_figures.py
@brief Pictures of what the research does, written to figures/ (committed, linked from the README files): thin tracks on the pixel grid, nets and the Joule heat of one net on a KiCad board, and the mapping of real copper to cells.
@details Needs numpy, scipy, matplotlib, shapely and gerbonara. Run: python make_figures.py
"""

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
import windows
from study_net_joule import disc, net_pads
from study_reader_conformance import DEST

OUT = Path(__file__).resolve().parent / "figures"          # kept in the repository on purpose: the README files link to them


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


def fig_nets():
    """!
    @brief The top copper of a KiCad board coloured by net, and the potential and Joule heat of one net at 1 A.
    @return None.
    """
    layer = ng.Layer((DEST / "zero-length-lines__charliewatch-v2.panel-F_Cu.gbr").read_text())
    bb = layer.bbox()
    pix = 0.05
    w, h = bb[2] - bb[0] + 0.4, bb[3] - bb[1] + 0.4
    cv_all = ng.Canvas(bb[0] - 0.2, bb[3] + 0.2, w, h, pix)
    layer.draw(cv_all)
    lab, ncomp = ndimage.label(cv_all.mask)
    nets = layer.net_names()
    owner = {}
    for net in nets:
        cv = ng.Canvas(bb[0] - 0.2, bb[3] + 0.2, w, h, pix)
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
    axs[0].imshow(img, cmap=ListedColormap(cols), interpolation="nearest", extent=ext)
    axs[0].set_title(f"top copper of a KiCad board: {len(nets)} nets (colours)\ngrey = copper with no net (a 428 mm2 zone fill)", fontsize=9)
    # Joule heat of one net: the largest piece of X9 with two or more pads, between its two farthest pads, 1 A
    net = "Board_0-/X9"
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
    axs[1].set_title(f"net {net.split('-')[-1]}: potential at 1 A, R = {r * 1000:.0f} mOhm (35 um copper)", fontsize=9)
    fig.colorbar(im, ax=axs[1], label="V")
    im = axs[2].imshow(np.where(mask, q / pix ** 2 * 1000.0, np.nan)[y0:y1, x0:x1], cmap="inferno", interpolation="nearest", extent=ext2, norm=LogNorm(vmin=max(q.max() / pix ** 2 * 1000.0 * 1e-3, 1e-12), vmax=q.max() / pix ** 2 * 1000.0))
    axs[2].set_title(f"Joule heat density, total {q.sum() * 1000:.0f} mW (= I2R); pads are the dots", fontsize=9)
    fig.colorbar(im, ax=axs[2], label="mW / mm2")
    for ax in axs[1:]:
        ax.plot(pa[:, 0], pa[:, 1], "w.", ms=3)
        ax.plot([pa[i][0], pa[j][0]], [pa[i][1], pa[j][1]], "wo", ms=7, mfc="none")
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_kicad_nets_and_joule.png", dpi=110)
    plt.close(fig)


def fig_mapping():
    """!
    @brief One real window: the 0.1 mm copper mask, the fill fraction per 1 mm cell (today) and the ratio of the flow-based cell conductance to the arithmetic one.
    @return None.
    """
    masks, meta = windows.load()
    k = 9
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
    axs[0].set_title(f"{meta[k][0]}: 36 x 36 mm of real copper, 0.1 mm pixels", fontsize=9)
    im = axs[1].imshow(f[::-1], cmap="viridis", vmin=0, vmax=1, interpolation="nearest", extent=(0, 36, 0, 36))
    axs[1].set_title("copper fraction of each 1 mm cell (what the program uses today)", fontsize=9)
    fig.colorbar(im, ax=axs[1])
    im = axs[2].imshow((flow / arith)[::-1], cmap="RdBu", vmin=0.2, vmax=1.8, interpolation="nearest", extent=(0, 36, 0, 36))
    axs[2].set_title("flow-based cell conductance / arithmetic one\nred (< 1): the fraction overestimates the conductance (board too cool)\nblue (> 1): it underestimates", fontsize=9)
    fig.colorbar(im, ax=axs[2])
    for ax in axs:
        ax.set_xlabel("mm")
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_copper_mapping_to_cells.png", dpi=110)
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
    print("figures in", OUT)


if __name__ == "__main__":
    main()
