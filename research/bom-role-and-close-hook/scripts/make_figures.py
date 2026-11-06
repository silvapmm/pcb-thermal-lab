#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figure 04 from the data of `study_bom_roles.py`: the thermal role the text rule gives the parts of each board, and how often the three signals agree.
@details Reads out/bom_roles.json (run the study first). Run from the repository root: `.venv/bin/python research/bom-role-and-close-hook/scripts/make_figures.py`.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
import diagram_kit as dk  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

BASE = os.path.dirname(HERE)
COLORS = {"component": "#d62728", "source": "#e0a458", "none": "#9bbf8a", "unknown": "#555555"}


def fig_04():
    """!
    @brief Figure 04: stacked shares of the final role per board, and the agreement of the signal pairs over all boards.
    @return None.
    """
    d = json.load(open(os.path.join(BASE, "out", "bom_roles.json")))
    boards = [k for k in d if k not in ("ALL", "x3", "prefix", "bom")]
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.3), gridspec_kw={"width_ratios": [1.6, 1]})
    left = [0.0] * len(boards)
    for role in ("component", "source", "none", "unknown"):
        vals = [100.0 * d[k]["final"].get(role, 0) / d[k]["n"] for k in boards]
        a.barh(boards, vals, left=left, color=COLORS[role], label=role, edgecolor="k", linewidth=0.5)
        left = [l + v for l, v in zip(left, vals)]
    a.set_xlabel("share of the parts (%)")
    a.set_title("Role given by the text rule, per board (n in the README)")
    a.legend(loc="lower center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, -0.32))
    pairs = d["ALL"]["pairs"]
    names = list(pairs)
    pct = [100.0 * pairs[k][1] / max(pairs[k][0], 1) for k in names]
    b.bar(names, pct, color="#2471a3", edgecolor="k")
    for i, k in enumerate(names):
        b.text(i, pct[i] + 0.1, f"{pairs[k][1]}/{pairs[k][0]}", ha="center", fontsize=8)
    b.set_ylim(90, 101)
    b.set_ylabel("agreement where both signals decide (%)")
    b.set_title("Agreement is not accuracy (same tool wrote the names)", fontsize=9)
    plt.setp(b.get_xticklabels(), fontsize=8)
    dk.save(fig, os.path.join(BASE, "figures", "fig_04_role_shares.png"))


if __name__ == "__main__":
    os.makedirs(os.path.join(BASE, "figures"), exist_ok=True)
    fig_04()
