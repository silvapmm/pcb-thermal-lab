#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figure 1 of the study: the section of the edge with the heat paths, and the errors of the plate and of the via effect against the edge coefficient (from the caches).
@details Run from the repository root after run_ref.py and run_prog.py: `.venv/bin/python research/strong-edge-laminate/scripts/make_figures.py`. Writes figures/fig_01_strong_edge.png.
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                     # noqa: E402
from matplotlib.patches import Rectangle                            # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as an                                                # noqa: E402

HS = (10, 200, 500, 1000, 2000)
fig, ax = plt.subplots(1, 3, figsize=(15, 4.4))

# panel 1: section near the wall (not to scale in z): four copper planes, laminate gaps cut into sub-gaps, film on the wall, via 0.16 mm from it
a = ax[0]
a.set_xlim(0, 10); a.set_ylim(-1, 8.5); a.set_aspect("equal"); a.axis("off")
for i in range(4):
    y = 7 - i * 2.2
    a.add_patch(Rectangle((0, y), 8.0, 0.25, color="#b87333"))
    if i < 3:
        for s in range(3):
            a.add_patch(Rectangle((0, y - 0.55 * (s + 1) - 0.0), 8.0, 0.5, fc="#d8e2c0", ec="#889070", lw=0.5))
a.add_patch(Rectangle((7.55, -0.3), 0.3, 7.8, color="#7a4a20"))
a.annotate("", xy=(9.8, 4), xytext=(8.1, 4), arrowprops=dict(arrowstyle="->", color="tab:blue", lw=2))
a.text(8.2, 4.3, "film h_side\non copper and\nevery laminate\nsub-slab", fontsize=8, color="tab:blue")
a.text(0.1, -0.9, "section at the wall (not to scale): the 3D reference cuts each gap into 8 to 32 slabs;\nthe program's default cuts it into 2 (0.487 mm gaps, s_max 0.4 mm)", fontsize=7)
a.set_title("1  what is compared")

for k, (title, fn) in enumerate((("2  plate alone: program against 3D, cell 0.25 mm", "plate"), ("3  via effect at 0.16 mm: program against 3D, cell 0.25 mm", "via"))):
    b = ax[k + 1]
    for n, lab in ((None, "2 sub-gaps (default)"), (4, "4"), (8, "8"), (16, "16"), (32, "32")):
        ys = []
        for h in HS:
            if fn == "plate":
                r, p = an.ref(h), an.prg(h, 0.25, n)
                ys.append(100 * (p / r - 1))
            else:
                e = an.eff(an.ref(h), an.ref(h, via="cyl"))
                p = an.eff(an.prg(h, 0.25, n), an.prg(h, 0.25, n, 0.16))
                ys.append(100 * (p / e - 1))
        b.plot(HS, ys, "o-", label=lab)
    b.axhline(0, color="k", lw=0.6)
    b.axvline(200, color="gray", ls=":", lw=0.8)
    b.set_xscale("log"); b.set_xlabel("h_side, W/m2K"); b.set_ylabel("error against the 3D reference, %")
    b.set_title(title, fontsize=9); b.grid(alpha=0.3)
    if k == 0:
        b.legend(fontsize=7, title="laminate sub-gaps")
fig.tight_layout()
os.makedirs(os.path.join(os.path.dirname(HERE), "figures"), exist_ok=True)
fig.savefig(os.path.join(os.path.dirname(HERE), "figures", "fig_01_strong_edge.png"), dpi=110)
