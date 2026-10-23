"""!
@file chain_study.py
@brief Several thermal levels in one chain: junction, pad, board, interface, metal block under the board, and on the other side the package top, interface and heatsink.

@details The junction is one extra unknown joined to the footprint cells by 1/theta (the block-and-plate of JESD15-3) and to the ambient through the top chain
         theta_JC(top) + interface/A + heatsink; the block under the board is the Heatsink layer of the program (interface, lateral conduction, exposed surface).
         The coefficients of the board faces are kept constant (the values the computed-h iteration gives for the board alone) so that the cases are comparable.

Usage: python research/component-heatsink/scripts/chain_study.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))
sys.path.insert(0, HERE)

import numpy as np                                                    # noqa: E402
import scipy.sparse as sp                                             # noqa: E402
import scipy.sparse.linalg as spla                                    # noqa: E402

import component_study as cs                                          # noqa: E402
from pcbthermal import fvm                                            # noqa: E402


def chain(part, h, theta_down, r_top=None, block=None, pad=25.0, cell=0.5):
    """!
    @brief Solve the board with the part as a junction node and, optionally, a top chain and a metal block under the board.
    @param part Entry of component_study.PARTS.
    @param h Tuple (h_top, h_bottom) in W/m2K kept constant.
    @param theta_down Junction-to-pad resistance in K/W.
    @param r_top Total resistance from the junction to the ambient through the package top in K/W (None: no top path).
    @param block None or (thickness mm, interface in K cm2/W, side mm) of an aluminium block centred under the board.
    @param pad Copper pad side in mm.
    @param cell Cell size in mm.
    @return Dict with Tj, the junction-to-pad power split and the share of the heat that leaves through the block.
    """
    p = cs.part_board(part, pad)
    p.board.h_mode = "manual"
    p.board.h_top, p.board.h_bottom = h
    if block:
        t, r, side = block
        c = p.board.width * 500.0
        p.add_heatsink(2, 0.0, rect=(c - side / 2, c - side / 2, c + side / 2, c + side / 2), thickness_mm=t, contact_r=r * 1e-4)
    nx, ny = int(round(p.board.width * 1000 / cell)), int(round(p.board.height * 1000 / cell))
    net = fvm.Network(p, nx, ny)
    K = net.K.tolil()
    n = K.shape[0]
    w = net.Qw[0].ravel()
    assert w.size == n
    K.resize((n + 1, n + 1))
    g = w / theta_down
    for i in np.flatnonzero(w):
        K[i, i] += g[i]
        K[n, n] += g[i]
        K[i, n] -= g[i]
        K[n, i] -= g[i]
    if r_top:
        K[n, n] += 1.0 / r_top
    rhs = np.zeros(n + 1)
    rhs[n] = part["p"]
    x = spla.spsolve(K.tocsc(), rhs, permc_spec="MMD_AT_PLUS_A")
    tj = float(x[n] + p.board.ambient)
    q_top = float(x[n] / r_top) if r_top else 0.0
    q_block = float(net.g_block.ravel() @ x[:n]) if block else 0.0
    return {"tj": tj, "top": q_top / part["p"], "block": q_block / part["p"]}


def main():
    """!
    @brief Print the chain table for two parts.
    """
    for name in ("MOSFET CSD17308Q3 (SON 3.3x3.3)", "LDO TPS7A47 (QFN-20 5x5)"):
        part = cs.PARTS[name]
        h = cs.run(part, 25.0)["h"]
        area_cm2 = part["w"] * part["h"] / 100.0
        r_paste = 0.5 / area_cm2                                 # Default paste 0.5 K cm2/W over the package top
        r_top = part["thtop"] + r_paste + 12.0
        print(f"\n{name}, {part['p']:g} W, pad 25 mm, h = {h[0]:.1f} / {h[1]:.1f} W/m2K; top chain = theta_JC(top) {part['thtop']:g} + paste {r_paste:.1f} + heatsink 12 = {r_top:.1f} K/W")
        print("| Case | Tj [degC] | heat through the top | heat through the block |\n| :-- | --: | --: | --: |")
        for label, rt, blk in (("board only", None, None), ("+ block 30x30x3 mm, paste 0.5", None, (3.0, 0.5, 30.0)),
                               ("+ block, gap pad 5 K cm2/W", None, (3.0, 5.0, 30.0)), ("+ top heatsink with paste", r_top, None),
                               ("+ both (block with paste and top heatsink)", r_top, (3.0, 0.5, 30.0))):
            r = chain(part, h, part["th"], rt, blk)
            print(f"| {label} | {r['tj']:.1f} | {100 * r['top']:.0f} % | {100 * r['block']:.0f} % |", flush=True)


if __name__ == "__main__":
    main()
