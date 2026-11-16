#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_jedec_board_readings.py
@brief How the JEDEC 2s2p row of the calculator validation depends on how the test board is read: the board of `calculator_validation.py` against the board as
       ROHM 64AN113E table 2 prints it (a 74.2 mm plane of 70 um on the backside, thermal vias joined to layers 1, 2 and 4 only).

@details Question: the calculator validation and validation 29.2 draw the JESD51-7 2s2p board with no bottom copper and with the nine thermal vias joined to every
         layer; the page of ROHM 64AN113E (PDF page 3, table 2 and NOTE1, read on the page image in the 2.8.0 audit) prints a backside copper of
         74.2 x 74.2 mm, 70 um, and vias "connected to 1, 2 and 4 layers of copper foil". Four boards separate the two differences:
         A as drawn (no bottom copper, vias to every layer), B the bottom plane only, C the board as printed (bottom plane, layer 3 not joined: an anti-pad of
         0.7 mm square around each via in the second plane), D layer 3 not joined but no bottom plane. For each board: the model RθJA at 1 W (junction = hottest
         board point under the heater + θJC(bot) 1.7 K/W x 1 W, computed h), the power the calculator returns for the datasheet's 32.5 K/W at 0.5 mm, and the
         three heater shapes of validation 29.2 (exposed pad 3.15 mm, body 5 mm, body with leads 5.8 mm) at 1 mm.
         The rim rule of the program (`viawell.rim_copper_shares`) uncouples a layer whose copper touches none of the 48 rim samples of the drill, so the
         anti-pad of board C and D removes layer 3 from the barrel exactly as NOTE1 says.
         Peak memory under 1.5 GB at 0.5 mm (FVM only). About 3 minutes.

Usage: .venv/bin/python research/power-calculator/scripts/study_jedec_board_readings.py [--quick]   (--quick: the 1 mm shapes are skipped)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)

import numpy as np                                                        # noqa: E402

from pcbthermal import api, analysis                                      # noqa: E402
from calculator_validation import jedec_2s2p_board, recovered             # noqa: E402

CX, CY = 57.15, 38.1          # Centre of the part on the board, mm
PLANE = 37.1                  # Half side of the 74.2 mm planes, mm
ANTI = 0.35                   # Half side of the anti-pad square around a via in plane 2 (layer 3), mm
VIA_X = (CX - 1.2, CX, CX + 1.2)
VIA_Y = (CY - 1.2, CY, CY + 1.2)


def board(bottom_plane, layer3_joined, side_mm=3.15):
    """!
    @brief The JEDEC 2s2p board of `calculator_validation.py` with the two readings of ROHM 64AN113E switched on or off.
    @param bottom_plane True for a 74.2 x 74.2 mm plane of 70 um on layer 4 (the backside copper of table 2).
    @param layer3_joined False to cut an anti-pad around each thermal via in the second plane (layer 3), as NOTE1 joins the vias to layers 1, 2 and 4.
    @param side_mm Side of the square heater in mm (3.15 exposed pad, 5.0 body, 5.8 body with leads).
    @return Problem (computed heat transfer coefficients, 1 W, θ 1.7 K/W).
    """
    p = jedec_2s2p_board()
    theta = p.heaters[0].theta
    if not layer3_joined:
        # Rebuild layer 3 as the plane minus three horizontal bands through the via rows, and each band as the four pieces between the anti-pads
        p.zones[:] = [z for z in p.zones if z.layer != 2]                # Zones store the 0-based layer: 2 is layer 3, the second plane
        x0, x1, y0, y1 = CX - PLANE, CX + PLANE, CY - PLANE, CY + PLANE
        edges_y = [y0]
        for y in VIA_Y:
            edges_y += [y - ANTI, y + ANTI]
        edges_y.append(y1)
        for k in range(0, len(edges_y), 2):
            p.add_zone(3, rect=(x0, edges_y[k], x1, edges_y[k + 1]))
        for y in VIA_Y:
            xs = [x0]
            for x in VIA_X:
                xs += [x - ANTI, x + ANTI]
            xs.append(x1)
            for k in range(0, len(xs), 2):
                p.add_zone(3, rect=(xs[k], y - ANTI, xs[k + 1], y + ANTI))
    if bottom_plane:
        p.add_zone(4, rect=(CX - PLANE, CY - PLANE, CX + PLANE, CY + PLANE))
    if abs(side_mm - 3.15) > 1e-9:
        p.heaters.clear()
        s = side_mm / 2
        p.add_heater(1, 1.0, rect=(CX - s, CY - s, CX + s, CY + s), name="U1", theta=theta)
    return p


def rth(p, cell_mm):
    """!
    @brief Model RθJA at 1 W: the junction temperature the program reports (hottest board point under the heater + θ P) minus the ambient.
    @param p Problem.
    @param cell_mm Cell size in mm.
    @return tuple (RθJA in K/W, the same without the face term in K/W, the rim shares of the centre via per layer, RθJA with the MEAN board temperature under the heater in
            place of the hottest point in K/W: the datasheet's θJC(bot) is defined to the pad, which the cold plate of the JEDEC test holds nearly isothermal).
    """
    from pcbthermal import viawell
    sim = api.simulate(p, api.SolverOptions(models=("fvm",), cell_mm=cell_mm))
    r = sim.results["fvm"]
    row = analysis.heater_stats(r, p)[0]
    node = analysis._footprint_stats(r, np.asarray(p.heaters[0].polygon), 0, None, face=False)[1]
    centre = min(p.vias, key=lambda v: (v.x - CX * 1e-3) ** 2 + (v.y - CY * 1e-3) ** 2)   # The vias are stored in metres
    shares = viawell.rim_copper_shares(p, centre, p.board.layers, viawell._zone_index(p, p.board.layers))
    return row["t_junction"] - r.ambient, node + p.heaters[0].theta - r.ambient, shares, row["t_mean"] + p.heaters[0].theta - r.ambient


def main():
    """!
    @brief Print the table of the four readings (0.5 mm, model RθJA and the calculator's power for 32.5 K/W) and the heater shapes at 1 mm.
    """
    quick = "--quick" in sys.argv
    cases = (("A as drawn (no bottom copper, vias to every layer)", False, True),
             ("B bottom plane 74.2 mm 70 um, vias to every layer", True, True),
             ("C as ROHM 64AN113E prints it (bottom plane, vias to layers 1, 2, 4)", True, False),
             ("D no bottom copper, vias to layers 1, 2, 4", False, False))
    print("| Board | rim share of the centre via per layer | model RθJA at 1 W, 0.5 mm (K/W) | the same with the pad mean (K/W) | calculator for 32.5 K/W (W) | error |")
    print("| :-- | :-- | --: | --: | --: | --: |")
    for label, bottom, joined in cases:
        p = board(bottom, joined)
        t, _, shares, tm = rth(p, 0.5)
        out = recovered(board(bottom, joined), 32.5, 0.5)
        print(f"| {label} | {' / '.join(f'{s:.2f}' for s in shares)} | {t:.2f} | {tm:.2f} | {out['power_w']:.3f} | {100 * (out['power_w'] - 1):+.1f} % |", flush=True)
    if quick:
        return
    print("\nHeater shapes of validation 29.2 (1 mm, computed h, 1 W; RθJA = hottest point under the heater + 1.7 K/W, node value without the face term in brackets)")
    print("| Board | exposed pad 3.15 mm | body 5 mm | body with leads 5.8 mm |")
    print("| :-- | --: | --: | --: |")
    for label, bottom, joined in cases:
        cells = []
        for side in (3.15, 5.0, 5.8):
            t, tn, _, _ = rth(board(bottom, joined, side), 1.0)
            cells.append(f"{t:.1f} ({tn:.1f})")
        print(f"| {label} | " + " | ".join(cells) + " |", flush=True)


if __name__ == "__main__":
    main()
