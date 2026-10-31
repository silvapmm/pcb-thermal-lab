#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_s4_tile.py
@brief S4, the tile of the Analytic via correction: error of the via effect against the tile size and the number of modes of the tile Green function, on boards with a known answer.
@details Question: why is the correction of `research/lumped-analytic-vias` sensitive to the tile (1 mm good, 1.5 mm up to -40 %, 2 mm +21 %), and what rule makes it automatic?
         Part 1 (unit cell, the only effect is the constriction): the lattice cell of pitch 0.8 to 8 mm, copper fill; the reference is the fine-grid layered solver, the second
                 reference the one-cell closed form with the Krogh wells (`study_causes.one_cell`: no program, no tile); columns: the closed form, the program's Analytic, and the corrected
                 Analytic with a fixed tile of 0.4 to 2.5 mm.
         Part 2 (the simple boards): lone via, row, 3 x 3 arrays, thermal pad: the same tile sweep, with the program's 64 modes of G and with c = 2 modes per tile.
         Part 3 (modes against board size): the 5 x 5 pad on boards of 30, 60 and 100 mm at tiles of 0.5 and 1 mm and modes of G of 64 (the program), and 2 W / tile; error and time.
         Every error is 100 (E_model / E_ref - 1), E the via effect T_max(no via) - T_max(with via).
Usage: python research/young-omega-tiles/scripts/study_s4_tile.py [--quick]   (from the repository root; the references on a 1/16 mm grid take minutes; --quick uses 4 tiles and fewer boards).
       Results go to out/s4_tile.json.
"""

import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "lumped-analytic-vias", "scripts"))

import outio                                                                # noqa: E402
import s4cases as sc                                                        # noqa: E402
import tilerule as tr                                                       # noqa: E402
import harness as hz                                                        # noqa: E402
import constriction as cr                                                   # noqa: E402
import program_cases as pc                                                  # noqa: E402

QUICK = "--quick" in sys.argv
TILES = (0.5, 1.0, 1.5, 2.5) if QUICK else (0.4, 0.5, 0.6, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5)
RES = {}


def err(e, e_ref):
    """!
    @brief Error of the via effect in percent.
    @param e Model effect in K.
    @param e_ref Reference effect in K.
    @return float.
    """
    return 100.0 * (e / e_ref - 1.0)


def modes_for(t_mm, board_mm, c):
    """!
    @brief Series modes M of the Analytic model large enough for the modes of G that the rule asks for.
    @param t_mm Tile in mm.
    @param board_mm Board side in mm.
    @param c Modes per tile (0: the program's).
    @return int.
    """
    return max(300, int(math.ceil(c * board_mm / t_mm)) + 8) if c > 0 else 300


def sweep(label, prob, e_ref, tiles, modes_c=0.0):
    """!
    @brief Errors of the corrected Analytic model for a list of fixed tiles.
    @param label Name of the board.
    @param prob Problem.
    @param e_ref Reference effect in K.
    @param tiles Tiles in mm.
    @param modes_c Modes of G per tile (0 = 64, the program's).
    @return dict tile -> error in percent.
    """
    q0 = hz.no_vias(prob)
    side = prob.board.width * 1e3
    out = {}
    for t in tiles:
        with tr.patched("fixed", t_mm=t, floor_mm=0.2, modes_c=modes_c, max_active=100000):
            out[t] = err(sc.effect(prob, "analytic", 0.5, modes_for(t, side, modes_c), 10, q0), e_ref)
    return out


def part1():
    """!
    @brief Unit cells: closed form, program, tile sweep.
    @return None.
    """
    print("## 1. Unit cell of a via lattice (2 layers, 0.3 mm drill, copper fill): error of the via effect against the tile (percent)\n")
    import study_causes as scz
    rows, out = [], []
    pitches = (1.0, 3.5, 8.0) if QUICK else (0.8, 1.0, 1.5, 2.0, 3.5, 5.0, 8.0)
    for item in [c for c in sc.corpus("simple") if c["kind"] == "unit" and c["pitch"] in pitches and c["layers"] == 2]:
        prob, p = item["problem"], item["pitch"]
        e_ref = sc.reference_e(prob, item["dx"], item["label"])
        par = pc.layer_parameters(prob)
        t0 = scz.one_cell(par, p * 1e-3, 1.0, False, no_via=True)
        e_cf = t0 - scz.one_cell(par, p * 1e-3, cr.ETA, True)
        q0 = hz.no_vias(prob)
        e_prog = sc.effect(prob, "analytic", 0.5, 300, 10, q0)
        sw = sweep(item["label"], prob, e_ref, TILES)
        rows.append([p, f"{e_ref:.3f}", f"{err(e_cf, e_ref):+.1f}", f"{err(e_prog, e_ref):+.1f}"] + [f"{sw[t]:+.1f}" for t in TILES])
        out.append({"pitch": p, "e_ref": e_ref, "closed_form_err": err(e_cf, e_ref), "program_err": err(e_prog, e_ref), "tiles": {str(t): v for t, v in sw.items()}})
    sc_hdr = ["pitch mm", "E_ref K", "closed form Krogh %", "Analytic program %"] + [f"tile {t} %" for t in TILES]
    outio.table(sc_hdr, rows)
    RES["unit"] = out


def part2():
    """!
    @brief The simple boards, program's 64 modes against 2 per tile.
    @return None.
    """
    print("## 2. The simple boards: error against the tile with 64 modes of G (the program) and with 2 modes per tile (percent)\n")
    rows, out = [], []
    for item in sc.corpus("simple"):
        if item["kind"] == "unit":
            continue
        prob = item["problem"]
        e_ref = sc.reference_e(prob, item["dx"], item["label"])
        d_nn, a = sc.nn_info(prob)
        base = {c: sweep(item["label"], prob, e_ref, TILES, c) for c in (0.0, 2.0)}
        for c, sw in base.items():
            rows.append([item["label"], f"{d_nn:.2f}" if math.isfinite(d_nn) else "-", f"{e_ref:.3f}", "64" if c == 0 else "2 W/t"] + [f"{sw[t]:+.1f}" for t in TILES])
            out.append({"label": item["label"], "d_nn_mm": d_nn, "e_ref": e_ref, "modes_c": c, "tiles": {str(t): v for t, v in sw.items()}})
    outio.table(["board", "d_nn mm", "E_ref K", "modes of G"] + [f"tile {t} %" for t in TILES], rows)
    RES["simple"] = out


def part3():
    """!
    @brief Modes against board size: the pad on boards of 30, 60 and 100 mm.
    @return None.
    """
    print("## 3. Modes of the tile Green function against the board size (5 x 5 pad, pitch 1.2 mm, copper fill): error and time\n")
    import cases as cs
    rows, out = [], []
    for side in ((30.0, 60.0) if QUICK else (30.0, 60.0, 100.0)):
        prob = cs.pad(4, 5, 1.2, 0.3, 385.0, side_mm=side, source_mm=6.0)
        dx = 1.0 / 16 if side <= 60 else 1.0 / 8
        e_ref = sc.reference_e(prob, dx, f"pad-side{side}")
        q0 = hz.no_vias(prob)
        for t in (0.5, 1.0):
            for c in (0.0, 1.0, 2.0):
                with tr.patched("fixed", t_mm=t, floor_mm=0.2, modes_c=c, max_active=100000):
                    m = modes_for(t, side, c)
                    t0 = time.perf_counter()
                    e = sc.effect(prob, "analytic", 0.5, m, 10, q0)
                    dt = time.perf_counter() - t0
                rows.append([side, t, "64" if c == 0 else f"{c:g} W/t", m, f"{err(e, e_ref):+.2f}", f"{dt:.1f}"])
                out.append({"side": side, "tile": t, "modes_c": c, "M": m, "err": err(e, e_ref), "seconds": dt})
    outio.table(["board mm", "tile mm", "modes of G", "M series", "error %", "seconds (both runs)"], rows)
    RES["modes"] = out


def main():
    """!
    @brief Run the parts and save.
    @return None.
    """
    sc.load_libraries()
    part1()
    part2()
    part3()
    print("saved", outio.save("s4_tile", RES))


if __name__ == "__main__":
    main()
