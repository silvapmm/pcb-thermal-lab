#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_real_board_effect.py
@brief S2: the effect on the temperature of a board with 100 or more vias, the program against the recommended treatment, and its convergence with the cell.
@details For each board (Allegro 4-layer, Stormduino 2-layer, own via field of 100 and 900 vias) with full copper and the source on the densest window: the maximum rise T_max and the
         via effect E = T_max(no via) - T_max(via) at cells of --cells, for "program" and for the recommended treatment ("mw" = board-only footprint, no image unless --image), in the
         FVM and, with --fdm, the FDM. Because a board of this size has no resolved reference, the convergence is read against the finest cell (the claim of the study is that the
         recommended treatment changes less from 1 mm to the finest cell than the program does; the claim that it is right rests on S1 and on `point-via-convergence`).
         Also printed: the copper-fill gain (E with fill_k 385 minus E open) for the same boards, the number of vias whose footprint was cut by the board edge, and the share of
         the board's heat that leaves through the vias is not computed (the cut-footprint count is in the output of study_edge_outline.py). Heavy cases (unknowns above --max-unknowns) are skipped and printed as skipped.
         Run from the repository root: `.venv/bin/python research/via-real-board/scripts/study_real_board_effect.py [--cells 2 1 0.5 0.25] [--fdm] [--image]`.
"""

import _bootstrap  # noqa: F401  (puts the import paths of this investigation in order)

import argparse
import logging

import numpy as np

import paths
import real_board as rbd
import runs


def boards(skip_missing=True):
    """!
    @brief The boards of the study.
    @param skip_missing True: a board whose files are not found is left out with a message.
    @return list of (name, holes, width, height, layers).
    """
    out = []
    for name, spec in rbd.BOARDS.items():
        try:
            out.append((name,) + rbd.holes_of(name) + (spec["layers"],))
        except FileNotFoundError as e:
            if not skip_missing:
                raise
            print("skipped:", e)
    for n in (10, 30):
        out.append((f"own {n * n}",) + rbd.own_via_field(n) + (4,))
    return out


def main(argv=None):
    """!
    @brief Print T_max and E against the cell for every board and treatment.
    @param argv Command line.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", type=float, nargs="+", default=[2.0, 1.0, 0.5, 0.25])
    ap.add_argument("--fdm", action="store_true")
    ap.add_argument("--image", action="store_true", help="use the image of the edge in the recommended treatment")
    ap.add_argument("--max-unknowns", type=int, default=1_200_000)
    ap.add_argument("--save-maps", type=float, default=0.0, metavar="CELL_MM", help="save the top-layer fields (no via, program, recommended) of the Stormduino and the own field at this cell to out/maps_*.npz")
    a = ap.parse_args(argv)
    logging.disable(logging.WARNING)
    import program_cases as pc
    pc.load_libraries()
    mw = dict(runs.MW_IMAGE if a.image else runs.MW_BOARD)
    models = ["fvm"] + (["fdm"] if a.fdm else [])
    for name, holes, w, h, layers in boards():
        p = rbd.problem_from_holes(holes, w, h, layers=layers)
        if a.save_maps and name != "alleg":                                  # the Allegro board has no stated licence: no picture of it is made
            paths.OUT.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(paths.OUT / f"maps_{name.replace(' ', '_')}.npz", cell=a.save_maps, width=w, height=h, holes=np.array(holes),
                                none=runs.field(runs.without_vias(p), a.save_maps), program=runs.field(p, a.save_maps), recommended=runs.field(p, a.save_maps, mw))
        pf = rbd.problem_from_holes(holes, w, h, layers=layers, fill_k=385.0)
        print(f"\n## {name}: {len(holes)} holes, {w:.1f} x {h:.1f} mm, {layers} layers, source {p.heaters[0].power:g} W\n")
        print("| model | treatment | quantity | " + " | ".join(f"{c:g} mm" for c in a.cells) + " | change 1 mm to finest |")
        print("| :-- | :-- | :-- | " + " | ".join("--:" for _ in a.cells) + " | --: |")
        for model in models:
            for tname, var in (("program", runs.PROGRAM), ("mw", mw)):
                tm, ef, gain = [], [], []
                for c in a.cells:
                    if (w * h / c ** 2) * layers > a.max_unknowns:
                        tm.append(float("nan"))
                        ef.append(float("nan"))
                        gain.append(float("nan"))
                        continue
                    t0 = runs.rise(runs.without_vias(p), model, c)
                    t1 = runs.rise(p, model, c, var)
                    t2 = runs.rise(pf, model, c, var)
                    tm.append(t1)
                    ef.append(t0 - t1)
                    gain.append(t1 - t2)
                fmt = lambda xs: " | ".join("skipped" if x != x else f"{x:.2f}" for x in xs)       # noqa: E731
                i1 = a.cells.index(1.0) if 1.0 in a.cells else 0
                last = next((x for x in reversed(ef) if x == x), float("nan"))
                print(f"| {model} | {tname} | T_max rise (K) | {fmt(tm)} | |")
                print(f"| {model} | {tname} | via effect E (K) | {fmt(ef)} | {last - ef[i1]:+.2f} K |")
                print(f"| {model} | {tname} | copper-fill gain (K) | {fmt(gain)} | |", flush=True)


if __name__ == "__main__":
    main()
