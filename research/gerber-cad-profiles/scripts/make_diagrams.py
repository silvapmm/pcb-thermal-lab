#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Diagrams of the CAD-profile investigation: the recognition flow and the differences between tools (file names, bottom-side X sign, outline).
@details Pure drawing, no data and no program (the numbers written on the pictures are the ones the README quotes from the studies);
         shapes from research/diagram_kit.py.  Writes figures/fig_01_recognition_flow.png, fig_02_tool_differences.png and
         fig_03_bottom_x_sign.png.  Run from the repository root: .venv/bin/python research/gerber-cad-profiles/scripts/make_diagrams.py
"""
import sys
from pathlib import Path

from matplotlib.patches import Polygon, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"


def recognition_flow(path):
    """!
    @brief Markers -> profile -> conventions -> user override.
    @param path  Output file.
    @return None
    """
    fig, ax = dk.canvas(12, 5.6)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5.6)
    dk.box(ax, 0.1, 3.9, 2.3, 1.4, "files of the set\n(names and the first\n8 kB of each)", "#cfe3f5")
    dk.box(ax, 3.0, 4.35, 2.5, 0.95, "Gerber: X2\nTF.GenerationSoftware,\nbanner comments", "#d8ecd0", size=7)
    dk.box(ax, 3.0, 3.2, 2.5, 0.95, "drill: header comments\n(; DRILL file {KiCad..,\n; Version : LOCAL ..)", "#d8ecd0", size=7)
    dk.box(ax, 3.0, 2.05, 2.5, 0.95, "support files: .gpf, .EXTREP,\nREAD-ME, ODB++ misc/info,\nplacement headers", "#d8ecd0", size=7)
    dk.box(ax, 3.0, 0.9, 2.5, 0.95, "file names and\nextensions\n(weak: weight 1 to 8)", "#fbe3b6", size=7)
    for y in (4.82, 3.67, 2.52, 1.37):
        dk.arrow(ax, 2.4, 4.6, 3.0, y)
    dk.box(ax, 6.1, 2.6, 2.1, 1.7, "score per profile\n(table cad_markers.json)\nweight 9+ = decisive\n(names itself)", "#fbe3b6", bold=True)
    for y in (4.82, 3.67, 2.52, 1.37):
        dk.arrow(ax, 5.5, y, 6.1, 3.45)
    dk.box(ax, 8.7, 3.9, 3.2, 1.4, "profile + confidence + evidence\nhigh | mixed | medium | low |\ndeclared | unknown", "#f4b6b6", bold=True)
    dk.arrow(ax, 8.2, 3.45, 8.7, 4.4)
    dk.box(ax, 8.7, 2.1, 3.2, 1.3, "import window shows:\n'Detected: Altium Designer 24.5\n(TF.GenerationSoftware) [change...]'", "#e8e8e8")
    dk.arrow(ax, 10.3, 3.9, 10.3, 3.4)
    dk.box(ax, 8.7, 0.2, 3.2, 1.5, "the profile sets defaults only:\nlayer names, drill dialect,\noutline rule, paste/TO.C,\nplacement columns", "#d8ecd0")
    dk.arrow(ax, 10.3, 2.1, 10.3, 1.7, label="user choice wins", size=7)
    ax.text(6.05, 0.35, "no marker at all -> 'unknown program':\ngeneric conventions (X2 if present, else names)", fontsize=7.5, ha="center")
    dk.save(fig, path, "From the files to the CAD profile (schematic)")


def tool_differences(path):
    """!
    @brief A picture of what differs between tools, from the sample files: names of the top copper, the outline and the paste, the X2 and TO.C columns.
    @param path  Output file.
    @return None
    """
    rows = [
        ("KiCad", "proj-F_Cu.gbr", "proj-Edge_Cuts.gbr", "proj-F_Paste.gbr", "yes", "mm 4.6", "FileFunction always"),
        ("Altium", "proj.GTL  (.G1..)", "proj.GM1 / .GKO", "proj.GTP", "GenSoftware only", "in 2.5 / mm 4.4", "Layer_Physical_Order"),
        ("EAGLE / Fusion", "copper_top.gbr", "profile.gbr", "solderpaste_top.gbr", "X2 from v9", "mm 3.4", "X2 FileFunction"),
        ("Allegro / OrCAD", "TOP.art  (lyr2.art)", "none seen", "PASTE_TOP.art", "no", "in 2.5", "Film Name comment"),
        ("Xpedition", "EtchLayerTop.gdo", "BoardOutlline.gdo", "SolderPasteTop.gdo", "no", "in 2.4", "G04 Layer name"),
        ("PADS", "Top.pho (Layer2.pho)", "(not in set)", "(SMT.pho = mask)", "no", "in 3.5", "G04 PADS banner"),
        ("EasyEDA", "Gerber_TopLayer.GTL", "Gerber_BoardOutline.GKO", "..TopPasteMaskLayer.GTP", "no", "mm 4.5", "G04 Layer: name"),
        ("DipTrace", "proj_Top.gbr", "proj_BoardOutline.gbr", "proj_TopPaste.gbr", "partly", "in 2.6", "G04 DipTrace"),
        ("Proteus", "x - CADCAM Top Copper.GBR", "CADCAM Mechanical 1 / Slot *", "x - CADCAM Top SMT Paste", "yes", "mm 4.5", "FileFunction always"),
        ("Zuken (emulated)", "Conductive-1.fph", "(not in set)", "MetalMask-A.fph", "no", "mm 4.6", "M00, G54D, no comments"),
    ]
    head = ("tool", "top copper", "outline", "top paste", "X2 attributes", "format", "layer told by")
    fig, ax = dk.canvas(13, 5.2)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 5.2)
    xs = [0.1, 1.9, 4.4, 6.9, 9.3, 10.6, 11.9]
    for x, h in zip(xs, head):
        ax.text(x, 4.95, h, fontsize=8, fontweight="bold", va="center")
    for i, r in enumerate(rows):
        y = 4.45 - i * 0.43
        if i % 2 == 0:
            ax.add_patch(Rectangle((0.0, y - 0.2), 13.0, 0.4, facecolor="#f1f1f1", edgecolor="none"))
        for x, c in zip(xs, r):
            ax.text(x, y, c, fontsize=7, va="center", family="monospace" if x not in (xs[0], xs[4]) else None)
    ax.text(0.1, 0.05, "Names, outline file and number format as found in the sample files (README 3, 4); * = name seen in a search listing, not in a downloaded set; 'format' is the %FS integer.decimal digits.",
            fontsize=7, style="italic")
    dk.save(fig, path, "What differs between tools in the files that matter to the import")


def bottom_x_sign(path):
    """!
    @brief The bottom-side X of a placement file: written as is or negated, the same KiCad version in both boards (isastm and cmm2).
    @param path  Output file.
    @return None
    """
    fig, axs = dk.canvas(11, 4.2, ncols=3)
    for ax in axs:
        ax.set_xlim(-6.5, 6.5)
        ax.set_ylim(-4.5, 4.5)
        ax.set_aspect("equal")
        ax.axis("on")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.add_patch(Rectangle((-5, -3.5), 10, 7, facecolor="#9bbf8a", edgecolor="k", alpha=0.35))
        ax.axhline(0, color="#888", lw=0.5)
        ax.axvline(0, color="#888", lw=0.5)
    # panel 1: the part on the bottom seen through the board (what the Gerber frame holds)
    a = axs[0]
    a.add_patch(Rectangle((2.6, 1.4), 1.6, 0.8, facecolor="#d62728", edgecolor="k"))
    a.text(3.4, 2.5, "C13 (bottom)\nin the Gerber\nframe: x = +3.4", ha="center", fontsize=7)
    a.set_title("1  where the part is in the Gerber frame", fontsize=8)
    # panel 2: file written as is
    a = axs[1]
    a.add_patch(Rectangle((2.6, 1.4), 1.6, 0.8, facecolor="#d62728", edgecolor="k"))
    a.plot([3.4], [1.8], "k+")
    a.text(3.4, 2.5, "file: PosX = +3.4\n'as is'\n(cmm2: 10 parts fit,\n0 negated)", ha="center", fontsize=7)
    a.set_title("2  option off: written as is", fontsize=8)
    # panel 3: negated
    a = axs[2]
    a.add_patch(Rectangle((2.6, 1.4), 1.6, 0.8, facecolor="#d62728", edgecolor="k"))
    a.plot([-3.4], [1.8], "b+")
    a.annotate("", xy=(-3.4, 1.8), xytext=(3.4, 1.8), arrowprops=dict(arrowstyle="->", color="b"))
    a.text(0, -2.2, "file: PosX = -3.4  'negated X'\n(isastm: 0 parts fit as is,\n6 negated)", ha="center", fontsize=7)
    a.set_title("3  option on: bottom X negated", fontsize=8)
    dk.save(fig, path, "Bottom-side X in a KiCad placement file: same program, either sign (schematic; counts from study_parts.py)")


def main():
    """!
    @brief Draw all the diagrams.
    @return int Exit code.
    """
    OUT.mkdir(exist_ok=True)
    recognition_flow(OUT / "fig_01_recognition_flow.png")
    tool_differences(OUT / "fig_02_tool_differences.png")
    bottom_x_sign(OUT / "fig_03_bottom_x_sign.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
