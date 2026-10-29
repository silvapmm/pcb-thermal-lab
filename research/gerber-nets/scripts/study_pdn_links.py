#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_pdn_links.py
@brief The electrical side of an electro-thermal run on the rectangle board: a 5 V source, a current sink and a ferrite-bead link between two separate pieces of copper of one net, and where the heat is made.
@details Pieces (rect_board.py, edges on the cells): the large pad with its 2 mm track and the 8 x 8 mm pad (one piece), the 12 x 4 mm rectangle (a second piece of the same net, joined to the first only by the link), the
         floating 6 x 6 mm square and the thin 0.5 mm track (no terminal: no current). Elements: 5 V at the large pad, a link of 0.1 ohm (a ferrite bead or a shunt) from the 8 x 8 pad to the rectangle, a 1.5 A sink at the other
         end of the rectangle. Reports the voltage at the load, the heat of the copper of every piece and of the link, and checks the energy balance. The heat of the copper is added to the thermal grid with joule.to_cells.
         Run: .venv/bin/python research/gerber-nets/scripts/study_pdn_links.py (from the repository root; seconds). Figure 11 is made from out/pdn_links.npz by make_figures.py.
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-nets in order)

import numpy as np

import joule
import pdn
import rect_board as rb
from paths import OUT

PIX = 0.2
RS = joule.RHO_CU_20C / 35e-6                      # ohm per square, 35 um copper


def box(x0, y0, x1, y1, shape):
    """!
    @brief A rectangular terminal as a pixel mask.
    @param x0 Left (mm).
    @param y0 Bottom (mm).
    @param x1 Right (mm).
    @param y1 Top (mm).
    @param shape Mask shape (rows from the bottom).
    @return numpy.ndarray Boolean mask.
    """
    m = np.zeros(shape, bool)
    m[int(round(y0 / PIX)):int(round(y1 / PIX)), int(round(x0 / PIX)):int(round(x1 / PIX))] = True
    return m


def scenario(v=5.0, amps=1.5, ohms=0.1):
    """!
    @brief Solve the scenario.
    @param v Source voltage (V).
    @param amps Load current (A).
    @param ohms Resistance of the link (ohm).
    @return tuple (mask, result dict, terminals dict).
    """
    mask = rb.mask(0.0, PIX)
    t = {"vin": box(5, 10, 7, 12, mask.shape), "out_pad": box(34, 14, 36, 16, mask.shape),
         "rect_a": box(24, 5, 26, 9, mask.shape), "load": box(14, 5, 16, 9, mask.shape)}
    el = [("vsource", "vin", v), ("link", "out_pad", "rect_a", ohms), ("isink", "load", amps)]
    return mask, pdn.solve(mask, RS, t, el), t


def main():
    """!
    @brief Run the scenario, print the report and save out/pdn_links.npz.
    @return None.
    """
    mask, r, t = scenario()
    p = mask.shape
    piece = {"large pad + track + 8x8 pad": box(5, 10, 36, 20, p) & mask, "12 x 4 rectangle (second piece)": box(14, 5, 26, 9, p) & mask,
             "floating 6 x 6 square": box(20, 22, 26, 28, p) & mask, "thin 0.5 mm track": box(2, 3, 38, 3.5, p) & mask}
    print(f"sheet resistance {RS * 1e3:.3f} mohm/square (35 um copper), 5 V source, 1.5 A load, link 0.1 ohm")
    print(f"voltage at the load terminal: {np.nanmean(r['V'][t['load']]):.4f} V (drop {5 - np.nanmean(r['V'][t['load']]) :.4f} V: {5 - np.nanmean(r['V'][t['load']]) - 0.15:.4f} V in the copper and 0.150 V across the link)")
    for k, m in piece.items():
        print(f"  heat of the copper: {k:34s} {r['q'][m].sum() * 1e3:8.3f} mW; nan (floating) pixels {int(np.isnan(r['V'][m]).sum())} of {int(m.sum())}")
    print(f"  heat of the link: {r['p_links'] * 1e3:.1f} mW ({r['links'][0][2]:.3f} A)")
    print(f"power of the source {r['p_source'] * 1e3:.3f} mW = copper {r['p_copper'] * 1e3:.3f} + link {r['p_links'] * 1e3:.3f} + load {r['p_sinks'] * 1e3:.3f} mW (the load is 4.84 V x 1.5 A, the power of the IC); difference {(r['p_source'] - r['p_copper'] - r['p_links'] - r['p_sinks']) * 1e3:.5f} mW")
    cells = joule.to_cells(r["q"], int(round(1.0 / PIX)))
    print(f"copper heat on the 1 mm cells of the thermal grid: total {cells.sum() * 1e3:.3f} mW, hottest cell {cells.max() * 1e3:.3f} mW")
    np.savez(OUT / "pdn_links.npz", V=r["V"], q=r["q"], mask=mask)


if __name__ == "__main__":
    main()
