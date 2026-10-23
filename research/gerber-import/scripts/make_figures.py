"""!
@file make_figures.py
@brief The picture of phase 1: our IC board drawn from its Gerber by the independent reader.
@details Figures are committed on purpose (the README files link to them); the caches they read are in out/ and are made by the studies. Run: .venv/bin/python research/gerber-import/scripts/make_figures.py (from the repository root).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-import in order)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import native_gerber as ng
import our_board

from paths import FIGURES as OUT                           # kept in the repository on purpose: the README files link to them


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
    fig.savefig(OUT / "fig_01_gerber_render.png", dpi=110)
    plt.close(fig)


def main():
    """!
    @brief Make the figures of this investigation.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig_gerber_render()
    print("figures in", OUT)


if __name__ == "__main__":
    main()
