#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cause.py
@brief Why does the FDM read a copper edge held inside the board colder than the FVM? Controlled ablations on copies of `fdm.py` (the program is not edited).
@details Prints the tables of README 3 and 4 (and writes `out/cause.json` for the figures):
         * A. the 10 mm four-layer plate (`research/strong-edge-laminate`), copper 0.5 mm inside the wall, hottest rise against the finite-element limit of an independent finite-element
           comparison, cell 0.25 and 0.5 mm, h_side 10 / 200 / 1000: FVM, FDM harmonic (the program with `face_fill=False`, as the study found it), FDM with faces from the cell fill (the program as adopted, `face_fill=True`), and the same with the laminate rule at one and eight
           sub-gaps (the laminate rule is not the cause when the gap between the columns does not change);
         * B. the same board with the h_side film switched off in the FDM (h_side 0.001), and with the film off on the laminate nodes only;
         * C. the 20 mm square of the comparison, aligned, with a plain rectangle and with an explicit rectangular outline (cut-cell treatment), copper 1.2 mm inside, cell 0.6, 0.5
           and 0.4 mm, heater mean rise against the finite-element limit;
         * D. the position of the copper edge against the grid (cell 0.25 mm, inset 0.30 to 0.625 mm), against the FVM at 0.0625 mm;
         * E. (review) the plate with the copper to the wall, hottest rise against the finite-element limit, laminate rule at one, two (shipped) and eight sub-gaps,
           cells 0.25 and 0.125 mm: the wall terms (edge film on the laminate nodes, half-volume edge nodes, corner nodes) of the FDM against those of the FVM;
         * F. (review) the via effect (hottest rise without the via minus with it) on the plate with the copper to the wall, via 0.16 and 3 mm from the wall, cell 0.25 mm, against the
           finite-element effect: the FVM with and without the mirror image of the edge (`viawell.image_walls` emptied), the FDM harmonic and with the face fill.
         Run from the repository root: `.venv/bin/python research/fdm-inset-edge/scripts/study_cause.py [A|B|C|D ...]` (about 2 minutes, under 1 GB).
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))

import boards as B                                            # noqa: E402
import fdm_variant                                            # noqa: E402
from pcbthermal import fdm, fvm, laminate, viawell            # noqa: E402

OUT = os.path.join(HERE, "..", "out", "cause.json")
HARM = fdm_variant.harmonic()                                # the program before the adopted face fill
FACE = fdm                                                   # the program as adopted (face fill on)


def run(model, problem, cell, n=None, kind="max"):
    """!
    @brief One run, optionally with a fixed number of laminate sub-gaps.
    @param model Module with solve_steady.
    @param problem Problem.
    @param cell Cell in mm.
    @param n Sub-gaps per gap (None: the shipped rule).
    @param kind "max" or "mean".
    @return Rise in K.
    """
    if n is None:
        return B.read(model, problem, cell, kind)
    with laminate.using(1e-6 if n > 2 else 0.4e-3, n):
        return B.read(model, problem, cell, kind)


def table_a(res):
    """!
    @brief Ablations on the strong-edge plate with the copper inset.
    @param res Result dict.
    @return None.
    """
    print("A. plate, copper 0.5 mm in, hottest rise, error % against the finite-element limit")
    print(f"{'cell':>5s} {'h':>6s} | {'FVM':>7s} {'FDM':>7s} {'face':>7s} | n=1: {'FVM':>7s} {'FDM':>7s} {'face':>7s} | n=8: {'FVM':>7s} {'FDM':>7s} {'face':>7s}")
    for cell in (0.5, 0.25):
        for h in (10.0, 200.0, 1000.0):
            fem = B.FEM_PLATE_INSET[h]
            row = []
            for n in (None, 1, 8):
                row += [B.err(run(m, B.plate(h, 0.5), cell, n), fem) for m in (fvm, HARM, FACE)]
            res[f"A|{cell}|{h}"] = row
            print(f"{cell:5.2f} {h:6.0f} | " + " ".join(f"{v:+7.2f}" for v in row[:3]) + " |       " + " ".join(f"{v:+7.2f}" for v in row[3:6]) + " |       " + " ".join(f"{v:+7.2f}" for v in row[6:]))


def table_b(res):
    """!
    @brief The film off: the in-plane copper-edge term alone.
    @param res Result dict.
    @return None.
    """
    print("B. plate, copper 0.5 mm in, cell 0.25: edge film nearly off (h_side 0.001) against the FVM at 0.0625 mm with the same film")
    ref = run(fvm, B.plate(0.001, 0.5), 0.0625)
    row = [B.err(run(m, B.plate(0.001, 0.5), 0.25), ref) for m in (fvm, HARM, FACE)]
    res["B|film_off"] = row
    print("   h_side 0.001: FVM %+.2f FDM %+.2f face %+.2f %% (reference %.3f K)" % (*row, ref))


def table_c(res):
    """!
    @brief The 20 mm aligned square, plain rectangle against an explicit outline.
    @param res Result dict.
    @return None.
    """
    print("C. 20 mm square, copper 1.2 mm in, heater mean rise, error % against the finite-element limit (plain rectangle / explicit outline)")
    for h in (200.0, 1000.0):
        fem = B.FEM_SQUARE_INSET[h]
        for cell in (0.6, 0.5, 0.4):
            row = []
            for ol in (False, True):
                p = B.square(h, 1.2, ol)
                row += [B.err(run(m, p, cell, None, "mean"), fem) for m in (fvm, HARM, FACE)]
            res[f"C|{h}|{cell}"] = row
            print(f"   h {h:6.0f} cell {cell:.1f}: plain FVM {row[0]:+6.2f} FDM {row[1]:+6.2f} face {row[2]:+6.2f} | outline FVM {row[3]:+6.2f} FDM {row[4]:+6.2f} face {row[5]:+6.2f}")


def table_d(res):
    """!
    @brief The position of the copper edge against the grid.
    @param res Result dict.
    @return None.
    """
    print("D. plate, cell 0.25 mm, copper edge at 'inset' mm, error % against the FVM at 0.0625 mm (hottest rise)")
    for h in (200.0, 1000.0):
        for inset in (0.30, 0.375, 0.45, 0.50, 0.55, 0.625):
            ref = run(fvm, B.plate(h, inset), 0.0625)
            row = [B.err(run(m, B.plate(h, inset), 0.25), ref) for m in (fvm, HARM, FACE)]
            res[f"D|{h}|{inset}"] = row
            print(f"   h {h:6.0f} inset {inset:5.3f}: FVM {row[0]:+6.2f} FDM {row[1]:+6.2f} face {row[2]:+6.2f}")


# Finite-element via effect E (K) of the same comparison, quoted: {(h_side, distance from the wall mm): E}; the via is a solid copper cylinder of 0.15 mm radius
FEM_VIA = {(200.0, 0.16): 1.579, (200.0, 3.0): 2.534, (1000.0, 0.16): 0.683, (1000.0, 3.0): 1.226}


def table_e(res):
    """!
    @brief Copper to the wall: the wall terms of the FDM and the FVM at one, two and eight sub-gaps.
    @param res Result dict.
    @return None.
    """
    print("E. plate, copper to the wall, hottest rise, error % against the finite-element limit (FVM / FDM harmonic / FDM face)")
    for h in (200.0, 1000.0):
        fem = B.FEM_PLATE_WALL[h]
        for cell in (0.25, 0.125):
            row = []
            for n in (1, None, 8):
                row += [B.err(run(m, B.plate(h, 0.0), cell, n), fem) for m in (fvm, HARM, FACE)]
            res[f"E|{h}|{cell}"] = row
            print(f"   h {h:6.0f} cell {cell:5.3f}: n=1 " + " ".join(f"{v:+6.2f}" for v in row[:3]) + " | shipped " + " ".join(f"{v:+6.2f}" for v in row[3:6])
                  + " | n=8 " + " ".join(f"{v:+6.2f}" for v in row[6:]), flush=True)


def table_f(res):
    """!
    @brief The via effect on the plate with the copper to the wall (the board of the finite-element via comparison), with the mirror image of the edge on and off in the FVM.
    @param res Result dict.
    @return None.
    """
    print("F. plate, copper to the wall, cell 0.25: via effect E error % against the finite-element E (FVM image on / off, FDM harmonic, FDM face)")
    keep = viawell.image_walls
    for (h, d), fe in FEM_VIA.items():
        row = []
        for m, img in ((fvm, True), (fvm, False), (HARM, True), (FACE, True)):
            if not img:
                viawell.image_walls = lambda *a, **k: []
            try:
                e = run(m, B.plate(h, 0.0), 0.25) - run(m, B.plate(h, 0.0, d), 0.25)
            finally:
                viawell.image_walls = keep
            row.append(100.0 * (e / fe - 1.0))
        res[f"F|{h}|{d}"] = row
        print(f"   h {h:6.0f} d {d:4.2f}: FVM {row[0]:+6.2f} FVM no image {row[1]:+6.2f} FDM harm {row[2]:+6.2f} FDM face {row[3]:+6.2f}", flush=True)


def main():
    """!
    @brief Run the requested tables.
    @return None.
    """
    which = sys.argv[1:] or ["A", "B", "C", "D", "E", "F"]
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    for w in which:
        {"A": table_a, "B": table_b, "C": table_c, "D": table_d, "E": table_e, "F": table_f}[w](res)
        json.dump(res, open(OUT, "w"), indent=1)


if __name__ == "__main__":
    main()
