#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the CAD-profile study (the diagrams are drawn by make_diagrams.py; one numbering for both).
@details Figure 4: per tool known to gerbonara, the sample sets whose program is named right by our detector (banners and
         markers) and by gerbonara's own guess (file names and a few header patterns), from the same run as
         `study_gerbonara_crosscheck.py` (README 10.2). Needs the downloaded sets in `data/` and gerbonara (`.venv-research`).
         Run from the repository root: `.venv-research/bin/python research/gerber-cad-profiles/scripts/make_figures.py`.
"""
import os
import sys
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import cadprofiles as cp  # noqa: E402
import study_gerbonara_crosscheck as gc  # noqa: E402
import study_markers as sm  # noqa: E402

FIG = os.path.join(os.path.dirname(HERE), "figures")
# colours: two categorical slots of the reference palette (blue, amber) and the text inks
OURS, GERBONARA, INK, MUTED = "#2a78d6", "#c98500", "#0b0b0b", "#52514e"


def counts():
    """!
    @brief Sets per tool, and how many each method names right (tools gerbonara knows only).
    @return dict tool -> [sets, ours right, gerbonara right].
    """
    warnings.simplefilter("ignore")
    rows = [(rel, truth) for rel, truth, _ in sm.ROOTS]
    held = os.path.join(sm.DATA, "heldout")
    if os.path.isdir(held):
        rows += [("heldout/" + d, d.split("__")[0]) for d in sorted(os.listdir(held)) if os.path.isdir(os.path.join(held, d))]
    table = cp.load_table()
    out = {}
    for rel, truth in rows:
        root = os.path.join(sm.DATA, rel)
        if truth not in gc.KNOWN or not os.path.isdir(root):
            continue
        paths = gc.set_files(root)
        det = cp.detect_set(cp.read_heads(paths, root), table)
        gb, _ = gc.gerbonara_guess(paths)
        c = out.setdefault(truth, [0, 0, 0])
        c[0] += 1
        c[1] += det.profile == truth
        c[2] += gc.GB_TO_OURS.get(gb, gb) == truth
    return out


def fig_04(data):
    """!
    @brief Grouped horizontal bars: sets named right by our detector and by gerbonara, per tool, with the set count as the frame.
    @param data  Output of counts().
    @return str Path of the figure.
    """
    names = {"kicad": "KiCad", "altium": "Altium", "eagle": "EAGLE / Fusion", "allegro": "Allegro / OrCAD", "xpedition": "Xpedition",
             "pads": "PADS", "diptrace": "DipTrace", "geda": "gEDA", "target3001": "Target 3001", "zuken": "Zuken (emulated)"}
    tools = sorted(data, key=lambda t: (-data[t][0], t))
    fig, ax = plt.subplots(figsize=(8.0, 4.6))
    h = 0.36
    for i, t in enumerate(tools):
        n, ours, gb = data[t]
        y = len(tools) - 1 - i
        ax.barh(y + h / 2 + 0.01, ours, h, color=OURS, label="our detector (banners, markers)" if i == 0 else None)
        ax.barh(y - h / 2 - 0.01, gb, h, color=GERBONARA, label="gerbonara (file names)" if i == 0 else None)
        ax.text(n + 0.3, y, "%d of %d / %d of %d" % (ours, n, gb, n), va="center", fontsize=8, color=MUTED)
    ax.set_yticks(range(len(tools)))
    ax.set_yticklabels([names.get(t, t) for t in reversed(tools)], fontsize=9, color=INK)
    ax.set_xlabel("sample sets whose program is named right", fontsize=9, color=MUTED)
    ax.set_xlim(0, max(v[0] for v in data.values()) + 6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", color="#e4e3df", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    tot = [sum(v[k] for v in data.values()) for k in range(3)]
    ax.set_title("Which program wrote the set: %d of %d sets by the banners, %d of %d by the names" % (tot[1], tot[0], tot[2], tot[0]),
                 fontsize=10, color=INK)
    fig.tight_layout()
    path = os.path.join(FIG, "fig_04_detection_against_gerbonara.png")
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def main():
    """!
    @brief Draw the data figures.
    @return int Exit code.
    """
    print(fig_04(counts()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
