#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_program_finned_block.py
@brief How wrong is the program's finned block when the fins are close: the rise of the hottest point with the uniform coefficient of the program and with the channel coefficient.

@details Question: the program gives the exposed face of a finned block the coefficient `h_face x fin_ratio(h_face)` (uniform h on the fins). Between close fins the air
         in the channel is slowed (Elenbaas), so the coefficient is lower. This study runs the program's own finned block (the board of
         `research/block-and-fins/scripts/study_finned_block_all_models.py`: 60 x 40 mm, two layers, a 3 W part, a 40 x 30 mm aluminium block of 3 mm with fins, here with the
         fins on a **vertical** board, so that the channels are vertical) twice:

         * "program": the faces carry the coefficient of an isolated vertical plate of the height of the channels at the block temperature (Churchill and Chu, laminar form;
           what the program's computed-h mode would give; iterated with the block temperature);
         * "channel": the program's `blocks.exposed_h` is replaced in memory (lib/program_patch.py) by the channel coefficient of the composite correlation of Bar-Cohen and
           Rohsenow (lib/channel.py), also iterated with the block temperature.

         Convection only (no radiation, no emissivity: the radiation between fins is blocked too and is a separate item). Sweeps: gap between the fins, fin height, channel
         length, power, and the 3D solid against the FVM for a few gaps. Results are written to `research/fin-channel/out/program_study.json` for `make_figures.py`.

Usage: .venv/bin/python research/fin-channel/scripts/study_program_finned_block.py   (about 1 minute)
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(ROOT, "research", "block-and-fins", "scripts"))

from study_finned_block_all_models import board          # noqa: E402

import channel as ch                                      # noqa: E402
import program_patch as pp                                # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")


def case(height=15.0, thickness=1.5, pitch=8.0, power=3.0):
    """!
    @brief The block of the program's study with the given fins and part power, on a vertical board.
    @param height Fin height in mm.
    @param thickness Fin thickness in mm.
    @param pitch Fin pitch in mm.
    @param power Power of the part in W.
    @return Problem.
    """
    p = board((height, thickness, pitch))
    p.heaters[0].power = power
    return p


def solve_program_plate(p, length, model="fvm", cell=1.0):
    """!
    @brief The program with the uniform coefficient equal to that of an isolated vertical plate of height `length` at the block temperature (iterated).
    @param p Problem (its face coefficients are overwritten).
    @param length Height of the plate (the length of the channels) in m.
    @param model "fvm" or "solid3d".
    @param cell Cell size in mm.
    @return Dict with rise, block_excess, h (W/m2K).
    """
    theta = 40.0
    for _ in range(12):
        h = ch.h_plate_vertical(theta, length, p.board.ambient, "laminar")
        p.board.h_top = p.board.h_bottom = h
        r = pp.solve_program(p, model, cell)
        if abs(r["block_excess"] - theta) < 0.05:
            break
        theta = r["block_excess"]
    return {"rise": r["rise"], "block_excess": r["block_excess"], "h": h}


def row(height, thickness, pitch, power, length, model="fvm", cell=1.0):
    """!
    @brief One comparison: rise with the uniform plate coefficient and with the channel coefficient.
    @param height Fin height in mm.
    @param thickness Fin thickness in mm.
    @param pitch Fin pitch in mm.
    @param power Power in W.
    @param length Channel length in m.
    @param model "fvm" or "solid3d".
    @param cell Cell size in mm.
    @return Dict of numbers.
    """
    p = case(height, thickness, pitch, power)
    a = solve_program_plate(p, length, model, cell)
    s = p.heatsinks[0]
    from pcbthermal import blocks
    h_exp_prog = blocks.exposed_h(s, a["h"])
    b = pp.solve_channel(p, length, model, cell)
    c = pp.solve_phi(p, length, cell) if model == "fvm" else {"rise": float("nan"), "phi": float("nan")}
    return {"rise_phi": c["rise"], "d_phi_pct": 100 * (c["rise"] / a["rise"] - 1), "phi": c["phi"], "gap_mm": pitch - thickness, "height_mm": height, "thickness_mm": thickness, "length_mm": 1000 * length, "power": power, "model": model,
            "rise_program": a["rise"], "rise_channel": b["rise"], "d_pct": 100 * (b["rise"] / a["rise"] - 1), "theta_program": a["block_excess"], "theta_channel": b["block_excess"],
            "h_plate": a["h"], "h_exp_program": h_exp_prog, "h_exp_channel": b["h_exp"], "h_ch": b["h_ch"], "eta_ch": b["eta"], "ra_b": b["ra_b"], "ratio_hexp": b["h_exp"] / h_exp_prog}


def table(rows, cols, title):
    """!
    @brief Print rows as a markdown table.
    @param rows List of dicts.
    @param cols List of (key, header, format).
    @param title Heading text.
    @return None.
    """
    print(f"\n{title}")
    print("| " + " | ".join(c[1] for c in cols) + " |")
    print("| " + " | ".join(":--" if i == 0 else "--:" for i in range(len(cols))) + " |")
    for r in rows:
        print("| " + " | ".join(format(r[c[0]], c[2]) for c in cols) + " |")


def main():
    """!
    @brief Run the sweeps, print the tables and write the JSON for the figures.
    @return None.
    """
    os.makedirs(OUT, exist_ok=True)
    cols = [("gap_mm", "gap (mm)", ".1f"), ("ra_b", "Ra_b", ".1f"), ("h_plate", "h plate (W/m²K)", ".2f"), ("h_ch", "h channel", ".2f"), ("ratio_hexp", "h_exp channel / program", ".2f"),
            ("rise_program", "rise program (K)", ".1f"), ("rise_channel", "rise channel (K)", ".1f"), ("d_pct", "difference (%)", "+.1f"),
            ("phi", "phi", ".2f"), ("rise_phi", "rise phi form (K)", ".1f"), ("d_phi_pct", "difference of the phi form (%)", "+.1f")]
    data = {}
    data["gap"] = [row(15.0, 1.5, g + 1.5, 3.0, 0.040) for g in (1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 8.5, 10.5, 14.5, 20.5)]
    table(data["gap"], cols, "A. Gap between the fins (fins 15 x 1.5 mm, channels 40 mm, 3 W, FVM 1 mm)")
    data["height"] = [row(hh, 1.5, 8.0, 3.0, 0.040) for hh in (5.0, 10.0, 15.0, 20.0, 30.0)]
    table(data["height"], [("height_mm", "fin height (mm)", ".0f")] + cols[1:], "B. Fin height (gap 6.5 mm)")
    data["length"] = [row(15.0, 1.5, 8.0, 3.0, ll / 1000.0) for ll in (20.0, 40.0, 60.0, 100.0, 200.0)]
    table(data["length"], [("length_mm", "channel length (mm)", ".0f")] + cols[1:], "C. Channel length (gap 6.5 mm)")
    data["power"] = [row(15.0, 1.5, 8.0, pw, 0.040) for pw in (0.5, 1.0, 3.0, 6.0, 10.0)]
    table(data["power"], [("power", "power (W)", ".1f")] + cols[1:], "D. Power, that is, the temperature of the block (gap 6.5 mm)")
    data["solid3d"] = [row(15.0, 1.5, g + 1.5, 3.0, 0.040, "solid3d", 2.0) for g in (3.5, 6.5, 14.5)]
    fvm2 = [row(15.0, 1.5, g + 1.5, 3.0, 0.040, "fvm", 2.0) for g in (3.5, 6.5, 14.5)]
    table(data["solid3d"], cols[:8], "E. The 3D solid (2 mm cells)")
    table(fvm2, cols, "E'. The FVM on the same 2 mm cells")
    data["fvm2"] = fvm2
    # F. A typed coefficient: what a user who types h (radiation included) gets against the channel coefficient (convection only), gap 6.5 mm, channels 40 mm
    print("\nF. A typed uniform coefficient on both faces (gap 6.5 mm, channels 40 mm, 3 W, FVM 1 mm): the program against the channel coefficient (convection only)")
    print("| typed h (W/m²K) | rise program (K) | rise channel (K) | difference (%) | rise phi form (K) | difference of the phi form (%) |")
    print("| --: | --: | --: | --: | --: | --: |")
    typed = []
    for h in (6.0, 8.0, 10.0, 12.0):
        p = case(15.0, 1.5, 8.0, 3.0)
        p.board.h_top = p.board.h_bottom = h
        a = pp.solve_program(p)
        b = pp.solve_channel(p, 0.040)
        c = pp.solve_phi(p, 0.040)
        typed.append({"h": h, "rise_program": a["rise"], "rise_channel": b["rise"], "d_pct": 100 * (b["rise"] / a["rise"] - 1), "rise_phi": c["rise"], "d_phi_pct": 100 * (c["rise"] / a["rise"] - 1)})
        print(f"| {h:g} | {a['rise']:.1f} | {b['rise']:.1f} | {typed[-1]['d_pct']:+.1f} | {c['rise']:.1f} | {typed[-1]['d_phi_pct']:+.1f} |")
    data["typed"] = typed
    with open(os.path.join(OUT, "program_study.json"), "w") as f:
        json.dump(data, f, indent=1)


if __name__ == "__main__":
    main()
