#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_nodes.py
@brief Study 3: where a gap of the zoned Lumped part comes from, node by node: the Lumped nodes A and C against the FVM (0.5 mm, same raster) averaged over the same cells, and the hottest point against where the FVM's hottest cell is.
@details For each selected case the FVM field at 0.5 mm (the Lumped's raster of a zoned board) is averaged over the core mask C and over the rest A of the footprint (the cells and
         weights the Lumped uses), and compared with the Lumped node values; the hottest footprint cell of the FVM is located (in C or in A, its distance to the footprint edge in mm);
         the Lumped peak is split into its three candidates. The FVM board without vias gives the baseline of every quantity.
Usage: python research/lumped-dense-via-group/scripts/study_nodes.py   (from the repository root; ONE process)
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import viastudy as v                                                          # noqa: E402
from pcbthermal import lumped, viaconstriction, fvm                           # noqa: E402
from pcbthermal.lumped import Network                                         # noqa: E402

CASES = [("base 8 mm, 5x5 @1.0", dict()), ("part 10, 8x8 @1.0", dict(part=10.0, n=8)), ("part 10, 8x8 @0.8", dict(part=10.0, n=8, pitch=0.8)),
         ("part 10, 5x5 @1.5 (4L)", dict(part=10.0, n=5, pitch=1.5, layers=4)), ("base, pitch 2.0", dict(pitch=2.0)), ("4L filled 8x8 @0.8, 8 mm", dict(layers=4, filled=True, n=8, pitch=0.8)),
         ("part 6, 3x3 @1.0", dict(part=6.0, n=3)), ("2L 8 mm, offset 3,3", dict(offset=(3.0, 3.0)))]


def one(label, kw):
    """!
    @brief One case: nodes against the FVM average over the same cells.
    @param label Name of the case.
    @param kw board() keywords.
    @return None (prints a line).
    """
    p = v.board(**kw)
    h = p.heaters[0]
    b = p.board
    cell = 0.5
    nx, ny = int(round(b.width * 1000 / cell)), int(round(b.height * 1000 / cell))
    net = Network(p, nx, ny, assemble=False, with_blocks=True, ladder=False, cut_cells=False)
    vias = viaconstriction.ViaSet(p)
    cov = lumped._footprint_coverage(net, h)
    ok = lumped.will_be_zoned(p, h, vias=vias)
    rn = lumped._heater_network(net, cov, h.layer, h.power, 10, vias, ok)
    amb = b.ambient
    th = rn["theta"]
    f = fvm.solve_steady(p, cell)
    T = f.T[0] - amb
    if "core" not in rn:
        print(f"| {label} | one node (not zoned) | node {th[0,0]:.2f} | FVM mean {np.average(T, weights=cov):.2f} |")
        return
    core = rn["core"]
    wa = cov * (~core)
    wc = cov * core
    a_f, c_f = np.average(T, weights=wa), np.average(T, weights=wc)
    peak_l = th[0, 0] + rn["peak_extra"]
    ij = np.unravel_index(np.argmax(np.where(cov > 0, T, -1e9)), T.shape)
    in_core = bool(core[ij])
    # Distance of the FVM hottest cell to the footprint edge
    xs = (np.arange(nx) + 0.5) * net.dx * 1000
    ys = (np.arange(ny) + 0.5) * net.dy * 1000
    poly = h.polygon * 1000
    x0, x1, y0, y1 = poly[:, 0].min(), poly[:, 0].max(), poly[:, 1].min(), poly[:, 1].max()
    d_edge = min(xs[ij[1]] - x0, x1 - xs[ij[1]], ys[ij[0]] - y0, y1 - ys[ij[0]])
    # The same on the board without vias
    q = v.board(**{**kw, "n": 0})
    T0 = fvm.solve_steady(q, cell).T[0] - amb
    print(f"| {label} | A: Lumped {th[0,0]:.2f} / FVM {a_f:.2f} ({100*(th[0,0]/a_f-1):+.1f} %) | C: Lumped {th[0,1]:.2f} / FVM {c_f:.2f} ({100*(th[0,1]/c_f-1):+.1f} %) | "
          f"A-C: Lumped {th[0,0]-th[0,1]:+.2f} / FVM {a_f-c_f:+.2f} | peak: Lumped {peak_l:.2f} (extra {rn['peak_extra']:.2f}) / FVM {T[ij]:.2f} at {'C' if in_core else 'A'}, {d_edge:.1f} mm from the edge "
          f"| no-via: mean {np.average(T0, weights=cov):.2f} peak {np.where(cov>0,T0,-1e9).max():.2f} | core {int(core.sum())} of {int((cov>0).sum())} cells |")


def main():
    """!
    @brief Run the cases.
    @return None.
    """
    for label, kw in CASES:
        one(label, kw)


if __name__ == "__main__":
    main()
