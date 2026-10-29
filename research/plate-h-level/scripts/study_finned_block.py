#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_finned_block.py
@brief The plate level against the channel effect: the finned block of `research/fin-channel` with the isolated-plate coefficient of each level, and with the channel composite whose plate limit is 0.59 or the exact 0.5157.

@details Question: at the gaps where the channel effect of `research/fin-channel` matters (2.5 to 20 mm) how large is the change of the rise caused by the choice of the plate
         level, and is it of the same size? The block is the one of `research/fin-channel/scripts/study_program_finned_block.py` (60 x 40 mm two-layer board, 3 W, aluminium block
         40 x 30 x 3 mm, fins 15 x 1.5 mm, FVM 1 mm, vertical channels of 40 mm, convection only), run with the program's own code and the in-memory patches of
         `research/fin-channel/lib/program_patch.py`:

         * "uniform, level X": every face of the fins and the base has the coefficient of an isolated vertical plate of the channel length at the block temperature, level X of
           `lib/levels.py` (iterated with the block temperature), the program's fin model;
         * "channel 0.59": the composite of Bar-Cohen and Rohsenow as written in the Waterloo review (plate limit 0.59);
         * "channel exact": the same composite with the plate limit replaced by the exact boundary-layer coefficient 0.5157 (the fully developed limit 24 is unchanged).

         Results go to out/finned_block.json; the review added the decomposition of the -0.1 % of `fin-channel` at 6.5 mm (out/fin_channel_decomposition.json).

Usage: .venv/bin/python research/plate-h-level/scripts/study_finned_block.py   (about 1 minute)
"""

import json
import os
import sys
from functools import partial

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(ROOT, "research", "fin-channel", "lib"))
sys.path.insert(0, os.path.join(ROOT, "research", "fin-channel", "scripts"))
sys.path.insert(0, os.path.join(ROOT, "research", "block-and-fins", "scripts"))

import channel as ch                                      # noqa: E402
import levels as L                                        # noqa: E402
import program_patch as pp                                # noqa: E402
from study_program_finned_block import case               # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
UNIFORM = ("general", "laminar", "bl", "mcadams")
C_EXACT = L.c_exact(0.71)


def solve_uniform(p, length, level, cell=1.0):
    """!
    @brief The program with the uniform coefficient of an isolated vertical plate of the given level, iterated with the block temperature (convection only).
    @param p Problem with a finned block.
    @param length Plate height (the channel length) in m.
    @param level One of levels.LEVELS.
    @param cell Cell size in mm.
    @return dict with rise (K), block_excess (K) and h (W/m2K).
    """
    theta = 40.0
    amb = float(p.board.ambient)
    for _ in range(12):
        h = L.h_vertical(level, amb + theta, amb, length)[0]
        p.board.h_top = p.board.h_bottom = h
        r = pp.solve_program(p, "fvm", cell)
        if abs(r["block_excess"] - theta) < 0.05:
            break
        theta = r["block_excess"]
    return {"rise": r["rise"], "block_excess": r["block_excess"], "h": h}


def row(gap_mm, length=0.040, power=3.0):
    """!
    @brief One gap: the rise with every uniform level and with the two channel composites.
    @param gap_mm Gap between the fins in mm.
    @param length Channel length in m.
    @param power Part power in W.
    @return dict.
    """
    out = {"gap_mm": gap_mm}
    for lv in UNIFORM:
        p = case(15.0, 1.5, gap_mm + 1.5, power)
        out["uniform_" + lv] = solve_uniform(p, length, lv)
    # The board faces keep the isolated-plate coefficient of the level that has the same plate limit as the composite (0.59 or the exact coefficient), the one of the
    # matching uniform run; research/fin-channel left the coefficient of its last uniform run on the board, which is the laminar form
    for key, lv, fun in (("channel_059", "mcadams", ch.nu_bcr), ("channel_exact", "bl", partial(ch.nu_bcr, c_bl=C_EXACT))):
        p = case(15.0, 1.5, gap_mm + 1.5, power)
        p.board.h_top = p.board.h_bottom = out["uniform_" + lv]["h"]
        out[key] = pp.solve_channel(p, length, "fvm", 1.0, nu_fun=fun)
    return out


def fin_channel_decomposition(gap_mm=6.5, length=0.040, power=3.0):
    """!
    @brief The -0.1 % of `research/fin-channel` at a gap taken apart (added by the review): board faces at the laminar form, as in `fin-channel`, and on the finned face
           (a) the laminar form (the baseline), (b) the plate 0.59 Ra_b^(1/4) with no channel, (c) the composite with its 0.59 (the run of `fin-channel`), (d) the `phi` form on
           the laminar coefficient (the channel effect alone).
    @param gap_mm Gap between the fins in mm.
    @param length Channel length in m.
    @param power Part power in W.
    @return dict with the four rises in K.
    """
    p = case(15.0, 1.5, gap_mm + 1.5, power)
    base = solve_uniform(p, length, "laminar")
    out = {"gap_mm": gap_mm, "laminar": base["rise"]}
    for key, fun in (("plate_059_fins", lambda ra: 0.59 * ra ** 0.25), ("channel_059_fins", ch.nu_bcr)):
        p = case(15.0, 1.5, gap_mm + 1.5, power)
        p.board.h_top = p.board.h_bottom = base["h"]
        out[key] = pp.solve_channel(p, length, "fvm", 1.0, nu_fun=fun)["rise"]
    p = case(15.0, 1.5, gap_mm + 1.5, power)
    p.board.h_top = p.board.h_bottom = base["h"]
    out["phi_laminar"] = pp.solve_phi(p, length, 1.0)["rise"]
    return out


def main():
    """!
    @brief Run the gaps, print the table and write out/finned_block.json.
    @return None.
    """
    rows = [row(g) for g in (2.5, 3.5, 4.5, 5.5, 6.5, 8.5, 10.5, 14.5, 20.5)]
    print(f"exact coefficient used for the composite: {C_EXACT:.4f}")
    print("rise of the hottest point (K), 40 mm channels, 3 W, convection only")
    print("| gap (mm) | uniform general | uniform laminar | uniform exact BL | uniform 0.59 | channel 0.59 | channel exact |")
    print("| --: | --: | --: | --: | --: | --: | --: |")
    for r in rows:
        print(f"| {r['gap_mm']:.1f} | " + " | ".join(f"{r[k]['rise']:.1f}" for k in ("uniform_general", "uniform_laminar", "uniform_bl", "uniform_mcadams", "channel_059", "channel_exact")) + " |")
    print("difference to the uniform laminar form (the program's baseline of research/fin-channel), %")
    for r in rows:
        base = r["uniform_laminar"]["rise"]
        print(f"gap {r['gap_mm']:.1f}: " + "  ".join(f"{k}: {100 * (r[k]['rise'] / base - 1):+.1f}" for k in ("uniform_general", "uniform_bl", "uniform_mcadams", "channel_059", "channel_exact")))
    # The configuration of research/fin-channel (board faces at the laminar form) taken apart at 6.5 mm
    d = fin_channel_decomposition()
    b = d["laminar"]
    print(f"fin-channel configuration at {d['gap_mm']} mm (board faces laminar): laminar {b:.1f} K; plate 0.59 on the fins {d['plate_059_fins']:.1f} K "
          f"({100 * (d['plate_059_fins'] / b - 1):+.1f} %); composite 0.59 on the fins {d['channel_059_fins']:.1f} K ({100 * (d['channel_059_fins'] / b - 1):+.1f} %, "
          f"{100 * (d['channel_059_fins'] / d['plate_059_fins'] - 1):+.1f} % from the plate 0.59); phi form on the laminar coefficient {d['phi_laminar']:.1f} K "
          f"({100 * (d['phi_laminar'] / b - 1):+.1f} %)")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "finned_block.json"), "w") as f:
        json.dump(rows, f, indent=1)
    with open(os.path.join(OUT, "fin_channel_decomposition.json"), "w") as f:
        json.dump(d, f, indent=1)


if __name__ == "__main__":
    main()
