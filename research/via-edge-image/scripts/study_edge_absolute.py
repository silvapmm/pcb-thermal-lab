#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_edge_absolute.py
@brief The error of a via near a board edge in kelvin and as a share of the board rise (not only of the via effect), for strongly cooled edges, plus the 3D solid, the corner, an outline cut and the reference check at 1/32 mm.
@details The percentage of the via effect E misleads when the edge is cold: E falls to a few hundredths of a kelvin and its percentage error is large but irrelevant. This script prints
         the maximum rise without the via (reference), E (reference), and the error of T_max with the via in K and in per cent of the rise, for the program, the mirror image and the Robin image.
         Run from the repository root: `.venv/bin/python research/via-edge-image/scripts/study_edge_absolute.py [--part films|corner|outline|solid|reference|fdm]`.
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import paths  # noqa: E402,F401
import edge_hook as eh  # noqa: E402
import edge_reference as er  # noqa: E402
import program_cases as pc  # noqa: E402


def tmax(p, mode, cell, model="fvm"):
    """!
    @brief Maximum rise of a model with an edge treatment.
    @param p Problem.
    @param mode "program", "mirror" or "robin".
    @param cell Cell in mm.
    @param model Model key.
    @return float rise in K.
    """
    with eh.patched(mode):
        return pc.max_rise(p, model, cell)


def films(args):
    """!
    @brief Table of the errors in K and in per cent of the rise against the edge film.
    @param args Parsed arguments.
    @return None.
    """
    print("| h_side | d (mm) | rise no via (K) | E ref (K) | cell | program (K / % rise) | mirror | robin |")
    print("| --: | --: | --: | --: | --: | :-- | :-- | :-- |")
    for hs in args.h_side:
        for d in args.distances:
            p = er.edge_board(d, True, None, hs or None)
            r0 = er.reference_rise(p, 1 / 16, with_via=False)
            r1 = er.reference_rise(p, 1 / 16, with_via=True)
            for c in args.cells:
                cells = []
                for m in ("program", "mirror", "robin"):
                    e = tmax(p, m, c) - r1
                    cells.append(f"{e:+.3f} / {100 * e / r0:+.2f} %")
                print(f"| {hs:g} | {d:g} | {r0:.2f} | {r0 - r1:.3f} | {c:g} | " + " | ".join(cells) + " |", flush=True)


def corner(args):
    """!
    @brief The via near a corner (both walls), insulated and h_side 10.
    @param args Parsed arguments.
    @return None.
    """
    print("| h_side | d (mm) | E ref (K) | cell | program | mirror | robin |")
    print("| --: | --: | --: | --: | --: | --: | --: |")
    for hs in (0.0, 10.0):
        for d in (0.16, 0.3, 0.5, 2.0):
            p = er.edge_board(d, True, None, hs or None, corner=True)
            ref = er.via_effect_reference(p, 1 / 16)
            q = er.deepcopy_without_via(p)
            for c in args.cells:
                vals = []
                for m in ("program", "mirror", "robin"):
                    e = tmax(q, "program", c) - tmax(p, m, c)
                    vals.append(f"{100 * (e / ref - 1):+.1f} %")
                print(f"| {hs:g} | {d:g} | {ref:.3f} | {c:g} | " + " | ".join(vals) + " |", flush=True)


def outline(args):
    """!
    @brief The via near an outline cut at x = 7 mm (on a cell line) and 7.0625 mm (inside a cell).
    @param args Parsed arguments.
    @return None.
    """
    print("| cut x (mm) | d (mm) | E ref (K) | cell | program | mirror | robin |")
    print("| --: | --: | --: | --: | --: | --: | --: |")
    for xc in (7.0, 7.0625):
        for d in (0.16, 0.5, 1.0):
            p = er.edge_board(d, True, xc, None)
            ref = er.via_effect_reference(p, 1 / 16, xc)
            q = er.deepcopy_without_via(p)
            for c in args.cells:
                vals = []
                for m in ("program", "mirror", "robin"):
                    e = tmax(q, "program", c) - tmax(p, m, c)
                    vals.append(f"{100 * (e / ref - 1):+.1f} %")
                print(f"| {xc:g} | {d:g} | {ref:.3f} | {c:g} | " + " | ".join(vals) + " |", flush=True)


def solid(args):
    """!
    @brief The 3D solid (program rule, no edge treatment) against the layered reference: the layered idealisation and the footprint are mixed here, so this is a bound, not a measurement of the image.
    @param args Parsed arguments.
    @return None.
    """
    print("| d (mm) | E ref layered (K) | cell | 3D solid E (K) | difference |")
    print("| --: | --: | --: | --: | --: |")
    for d in (0.16, 0.5, 1.0, 4.0):
        p = er.edge_board(d, True, None, None)
        ref = er.via_effect_reference(p, 1 / 16)
        q = er.deepcopy_without_via(p)
        for c in (1.0, 0.5):
            e = pc.max_rise(q, "solid3d", c) - pc.max_rise(p, "solid3d", c)
            print(f"| {d:g} | {ref:.3f} | {c:g} | {e:.3f} | {100 * (e / ref - 1):+.1f} % |", flush=True)


def fdm(args):
    """!
    @brief The FDM (program, no edge treatment: its edge nodes are half volumes) against the layered reference for the via near an insulated edge.
    @param args Parsed arguments.
    @return None.
    """
    print("| d (mm) | E ref (K) | " + " | ".join(f"{c:g} mm" for c in (1.0, 0.5, 0.25)) + " |")
    print("| --: | --: | --: | --: | --: |")
    for d in (0.16, 0.3, 0.5, 1.0, 4.0):
        p = er.edge_board(d, True, None, None)
        ref = er.via_effect_reference(p, 1 / 16)
        q = er.deepcopy_without_via(p)
        row = [f"{100 * ((pc.max_rise(q, 'fdm', c) - pc.max_rise(p, 'fdm', c)) / ref - 1):+.1f} %" for c in (1.0, 0.5, 0.25)]
        print(f"| {d:g} | {ref:.3f} | " + " | ".join(row) + " |", flush=True)


def reference(args):
    """!
    @brief Convergence of the reference: E at 1/16 and 1/32 mm for the nearest via.
    @param args Parsed arguments.
    @return None.
    """
    for hs in (None, 1000.0):
        p = er.edge_board(0.16, True, None, hs)
        print(f"h_side {hs}: E(1/16 mm) = {er.via_effect_reference(p, 1 / 16):.4f} K, E(1/32 mm) = {er.via_effect_reference(p, 1 / 32):.4f} K", flush=True)


def main(argv=None):
    """!
    @brief Run the chosen part.
    @param argv Command line.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="films", choices=["films", "corner", "outline", "solid", "reference", "fdm"])
    ap.add_argument("--h-side", type=float, nargs="+", default=[0.0, 10.0, 1e3, 1e4, 1e5])
    ap.add_argument("--distances", type=float, nargs="+", default=[0.16, 0.5, 1.0])
    ap.add_argument("--cells", type=float, nargs="+", default=[1.0, 0.5])
    a = ap.parse_args(argv)
    logging.disable(logging.WARNING)
    pc.load_libraries()
    {"films": films, "corner": corner, "outline": outline, "solid": solid, "reference": reference, "fdm": fdm}[a.part](a)


if __name__ == "__main__":
    main()
