#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_ring_diagnostic.py
@brief Why is the Lumped too cool near an edge: are the rings clipped by the board, and where does the ring-mean temperature go wrong?
@details A 5 mm part of 1 W on a 100 x 80 mm two-layer board at a gap of 0, 5 and 40 mm from the left side. For each ring of the program's network (the same cell, the same edges) the table gives the area
         of the ring, the contour length the network uses (area / thickness) against the half and full circle of the mean radius, the FVM mean rise of the same cells and the rise the Lumped
         assigns to the ring (program and with the potential links). Output: text, out/ring_diagnostic.json. Run from the repository root with PCBT_TREE set as for the other studies.
"""

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import boards as B  # noqa: E402
import variants as V  # noqa: E402
from pcbthermal import SolverOptions, simulate  # noqa: E402
from pcbthermal.fvm import Network  # noqa: E402


def rings_of(variant, p, cell):
    """!
    @brief Ring network of the heater of p as built by a variant of the Lumped.
    @param variant Variant name.
    @param p Problem.
    @param cell Cell in mm.
    @return (network dict, Network of the grid, coverage of the footprint).
    """
    m = V.load(variant)
    b = p.board
    nx = int(round(b.width * 1000.0 / cell))
    ny = int(round(b.height * 1000.0 / cell))
    net = Network(p, nx, ny, assemble=False, with_blocks=True, ladder=False, cut_cells=False)
    h = p.heaters[0]
    cov = m._footprint_coverage(net, h)
    return m._heater_network(net, cov, h.layer, h.power, 10, None, False), net, cov


def main():
    """!
    @brief Print the ring tables.
    @return None.
    """
    out = []
    cell = 0.5
    for gap in (0.0, 5.0, 40.0):
        side = 5.0
        pos = (gap + side / 2, 40.0)
        p = B.board(100.0, 80.0, side, pos, h_side=10.0)
        f = simulate(p, SolverOptions(models=("fvm",), cell_mm=cell)).results["fvm"]
        Tf = np.asarray(f.T)[0] - p.board.ambient
        rn, net, cov = rings_of("program", p, cell)
        rp, _, _ = rings_of("potlinks", p, cell)
        dist = rn["dist"]
        foot = cov > 0
        rho_max = float(dist.max())
        import pcbthermal.lumped as L
        edges = L.ring_edges(rho_max, net.dx, net.dy, 10, a_eq=L._equivalent_radius(foot, net.dx, net.dy))
        idx = np.where(foot, 0, 1 + np.minimum(np.searchsorted(edges[1:], dist, side="left"), len(edges) - 2))
        print(f"\n### gap {gap:g} mm (part 5 mm, FVM hottest {Tf.max():.2f} K, footprint mean {Tf[foot].mean():.2f} K)")
        print("| ring | mean distance mm | cells | area / (half annulus) | area / (full annulus) | FVM ring mean K | Lumped program K | potential links K |")
        print("| --: | --: | --: | --: | --: | --: | --: | --: |")
        rows = []
        used = [k for k in range(idx.max() + 1) if (idx == k).any()]
        for j, k in enumerate(used):
            sel = idx == k
            area = sel.sum() * net.dx * net.dy
            rho = float(dist[sel].mean())
            lo = 0.0 if k == 0 else edges[k - 1]
            hi = edges[k] if k < len(edges) else rho_max
            ann = np.pi * (max(hi, lo + 1e-9) ** 2 - lo ** 2) if k else float("nan")
            th_f = float(Tf[sel].mean())
            th_a = float(rn["theta"][0, j])
            th_b = float(rp["theta"][0, j])
            rows.append({"ring": j, "rho_mm": rho * 1e3, "cells": int(sel.sum()), "fvm": th_f, "program": th_a, "potlinks": th_b, "a_half": area / (0.5 * ann) if k else None, "a_full": area / ann if k else None})
            r = rows[-1]
            print(f"| {j} | {rho * 1e3:.1f} | {sel.sum()} | " + (f"{r['a_half']:.2f} | {r['a_full']:.2f}" if k else "- | -") + f" | {th_f:.2f} | {th_a:.2f} | {th_b:.2f} |")
        out.append({"gap": gap, "rows": rows})
    B.OUT.mkdir(exist_ok=True)
    (B.OUT / "ring_diagnostic.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
