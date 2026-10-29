"""!
@file diagram_kit.py
@brief Small drawing helpers shared by the `make_diagrams.py` scripts of the research folders: boxes, arrows, a layer stack and a resistor, in plain matplotlib (no data, no program).
@details Every research folder keeps its schematic diagrams in `scripts/make_diagrams.py` and writes them to its own `figures/`; this module only holds the shapes they have in common.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle           # noqa: E402

COPPER = "#e0a458"
FR4 = "#9bbf8a"
METAL = "#b9c4cc"
AIR = "#dbe9f7"
HEAT = "#d62728"
BLUE = "#1f77b4"


def canvas(width, height, nrows=1, ncols=1, ratios=None):
    """!
    @brief A figure with empty axes (no frame) for a schematic.
    @param width Figure width (inches).
    @param height Figure height (inches).
    @param nrows Rows of axes.
    @param ncols Columns of axes.
    @param ratios Optional width ratios of the columns.
    @return tuple (figure, axes array or one axes).
    """
    fig, axs = plt.subplots(nrows, ncols, figsize=(width, height), gridspec_kw={"width_ratios": ratios} if ratios else None)
    for ax in (axs.ravel() if hasattr(axs, "ravel") else [axs]):
        ax.axis("off")
    return fig, axs


def box(ax, x, y, w, h, text, color="#cfe3f5", bold=False, size=8):
    """!
    @brief A rounded box with a centred text.
    @param ax Axes.
    @param x Left.
    @param y Bottom.
    @param w Width.
    @param h Height.
    @param text Label.
    @param color Fill colour.
    @param bold True for a thick border.
    @param size Font size.
    @return None.
    """
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.1", facecolor=color, edgecolor="k", linewidth=2 if bold else 0.9))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size)


def arrow(ax, x0, y0, x1, y1, color="k", style="->", width=1.4, label="", size=7):
    """!
    @brief An arrow with an optional label at its middle.
    @param ax Axes.
    @param x0 Start x.
    @param y0 Start y.
    @param x1 End x.
    @param y1 End y.
    @param color Colour.
    @param style Matplotlib arrow style.
    @param width Line width.
    @param label Optional text.
    @param size Font size of the label.
    @return None.
    """
    ax.annotate("", (x1, y1), (x0, y0), arrowprops={"arrowstyle": style, "linewidth": width, "color": color})
    if label:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.12, label, ha="center", fontsize=size, color=color, style="italic")


def layer(ax, x, y, w, h, color, text="", size=7):
    """!
    @brief A rectangle of a layer stack (copper, laminate, metal) with a label.
    @param ax Axes.
    @param x Left.
    @param y Bottom.
    @param w Width.
    @param h Height.
    @param color Fill colour.
    @param text Optional label centred in it.
    @param size Font size.
    @return None.
    """
    ax.add_patch(Rectangle((x, y), w, h, facecolor=color, edgecolor="k", linewidth=0.8))
    if text:
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size)


def resistor(ax, x0, x1, y, label="", color="k", size=7):
    """!
    @brief A resistor symbol on a horizontal wire.
    @param ax Axes.
    @param x0 Left end of the wire.
    @param x1 Right end of the wire.
    @param y Height.
    @param label Text above.
    @param color Colour.
    @param size Font size.
    @return None.
    """
    ax.plot([x0, x0 + 0.25], [y, y], color=color)
    ax.add_patch(Rectangle((x0 + 0.25, y - 0.18), x1 - x0 - 0.5, 0.36, fill=False, edgecolor=color, linewidth=1.4))
    ax.plot([x1 - 0.25, x1], [y, y], color=color)
    if label:
        ax.text((x0 + x1) / 2, y + 0.35, label, ha="center", fontsize=size, color=color)


def save(fig, path, title=None):
    """!
    @brief Tighten, optionally title, save and close a figure.
    @param fig Figure.
    @param path Output path.
    @param title Optional suptitle.
    @return None.
    """
    if title:
        fig.suptitle(title, fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95) if title else None)
    fig.savefig(path, dpi=105)
    plt.close(fig)
