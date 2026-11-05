#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_paper_review_checks.py
@brief Checks of the review made after the conversion of the papers: do three statements of the sources hold against the program?

Question (docs/paper-review-after-ocr.md, sections 3 and 4):
(1) Horizontal faces. The program uses Nu = 0.54 Ra^(1/4) (face up) and 0.27 Ra^(1/4) (face down) on L = A/P. Yovanovich and Jafarpur (1993, MHTL report,
    pages 7 and 8) quote the theoretical laminar results summarised by Goldstein and Lau (1983) as Nu = C Ra^(1/5) on L = A/P: face up C 0.560 to 0.688
    (square plate 0.603), face down C 0.44 to 0.527 (mean 0.475 at Pr 0.71); Lienhard (6.00, eq. 8.37a, book p 436) gives the Raithby-Hollands face-up law
    0.560 Ra^(1/4) / [1 + (0.492/Pr)^(9/16)]^(4/9) with the thick-layer correction 8.37b, for 1 < Ra < 1e7. Ratios of the program's laws to these, by Ra.
(2) Edge loss of the Analytic. The cosine series assumes insulated edges (analytic.py) and drops the edge loss h_side. Muzychka, Yovanovich and Culham
    (2003, AIAA 2003-4188, p 5, eqs. 27 to 29; journal version JTHT 20 (2) 2006) move the edge loss to the cooled face, h_eff A_b = h A_b + h_e A_e,
    when the edge is near the base temperature (thin plate). The program's FVM and Analytic on uniform two-layer boards, as they are and with the edge
    loss folded into h_top and h_bottom (the problem is changed in memory; the program is not edited).
(3) Culham, Yovanovich and Lemczyk (2000), Table 2 (p 237): the printed "difference (%)" column against the two printed temperatures.

Run (from the repository root):  .venv/bin/python research/theory-sources/scripts/study_paper_review_checks.py   (about 10 s, under 300 MB)
"""
import logging
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)

from pcbthermal import api  # noqa: E402
from pcbthermal.model import Problem  # noqa: E402

PR_AIR = 0.71                                               # Prandtl number of air used by the sources quoted


def face_law_ratios(ras=(1e2, 3e2, 1e3, 3e3, 1e4, 3e4, 1e5)):
    """!
    @brief Ratio of the program's horizontal-face laws to the published laminar laws, by Rayleigh number on A/P.
    @param ras Rayleigh numbers on L = A/P (dimensionless).
    @return list of (Ra, up/GL square, up/RH 8.37, down/GL mean, down/GL low, down/GL high) ratios (dimensionless).
    """
    rows = []
    f_pr = (1.0 + (0.492 / PR_AIR) ** (9.0 / 16.0)) ** (4.0 / 9.0)     # Prandtl function of eq. 8.37a
    for ra in ras:
        up, down = 0.54 * ra ** 0.25, 0.27 * ra ** 0.25                 # program (convection.h_natural_horizontal)
        gl_up = 0.603 * ra ** 0.2                                       # Goldstein-Lau summary, square plate, face up (YJ1993 p 8)
        nu_rh = 0.560 * ra ** 0.25 / f_pr                               # Lienhard eq. 8.37a
        if nu_rh < 10.0:
            nu_rh = 1.4 / math.log(1.0 + 1.4 / nu_rh)     # Lienhard eq. 8.37b, thick boundary layer
        rows.append((ra, up / gl_up, up / nu_rh, down / (0.475 * ra ** 0.2), down / (0.44 * ra ** 0.2), down / (0.527 * ra ** 0.2)))
    return rows


def edge_case(width, height, src, h_side, fold, cell=1.0):
    """!
    @brief Maximum rise of the FVM and the Analytic on a uniform two-layer board, optionally with the edge loss folded into the faces.
    @param width Board width in mm.
    @param height Board height in mm.
    @param src Side of the centred square source in mm (2 W on layer 1).
    @param h_side Edge coefficient in W/m2K (None = insulated).
    @param fold True to add h_side * edge area / (2 * face area) to h_top and h_bottom and insulate the edge (Muzychka 2003, eq. 29).
    @param cell Cell size in mm.
    @return dict model key -> maximum rise in K.
    """
    p = Problem.new(width_mm=width, height_mm=height, layers=2, thickness_mm=1.6, copper_um=35.0, h_top=10.0, h_bottom=10.0, h_side=h_side)
    p.add_zone(1, rect=(0, 0, width, height))
    p.add_zone(2, rect=(0, 0, width, height))
    p.add_heater(1, 2.0, rect=(width / 2 - src / 2, height / 2 - src / 2, width / 2 + src / 2, height / 2 + src / 2))
    b = p.board
    if fold and h_side:
        # The edge strip of area perimeter x thickness is shared equally by the two faces
        add = h_side * 2 * (b.width + b.height) * b.total_thickness() / (2 * b.width * b.height)
        b.h_top += add
        b.h_bottom += add
        b.h_side = None
    sim = api.simulate(p, api.SolverOptions(cell_mm=cell, models=("fvm", "analytic")))
    return {k: sim.results[k].t_max - b.ambient for k in ("fvm", "analytic")}


def culham_table2():
    """!
    @brief Recompute the difference column of Table 2 of Culham, Yovanovich and Lemczyk (2000) from its two temperature columns.
    @return list of (h label, Lasance, current model, printed %, recomputed %).
    """
    rows = [("1", 455.0, 455.3, 0.07), ("10", 62.4, 62.5, 0.16), ("100", 22.6, 22.8, 0.88), ("1000", 18.2, 18.4, 1.10),
            ("1e4", 17.4, 17.7, 1.72), ("1e6", 16.7, 17.1, 2.40), ("1e8", 16.7, 17.1, 2.40), ("500/10/10/10", 25.9, 26.0, 0.39),
            ("10/10/500/500", 32.1, 28.5, 6.0), ("10/500/10/10", 21.7, 22.0, 1.38), ("1e9 top", 25.4, 25.5, 0.39),
            ("1e9 bot", 20.2, 20.3, 0.50), ("1e9 side, lead", 19.1, 18.2, -4.71)]
    return [(lab, a, b, pr, 100.0 * (b - a) / a) for lab, a, b, pr in rows]


def main():
    """!
    @brief Print the three checks.
    @return None.
    """
    logging.disable(logging.WARNING)
    print("(1) horizontal faces: program law / published law, Pr 0.71, L = A/P")
    print("      Ra   up/GL-square  up/RH-8.37  down/GL-0.475  down/GL-0.44  down/GL-0.527")
    for ra, a, b, c, d, e in face_law_ratios():
        print(f"{ra:8.0e}  {a:12.3f}  {b:10.3f}  {c:13.3f}  {d:12.3f}  {e:13.3f}")
    print("(2) Analytic edge loss: maximum rise (K), 2 W, uniform 2-layer board, h 10/10, h_side 10 W/m2K, FVM 1 mm")
    print(" board    src   FVM     Analytic  (An-FVM)/FVM | folded: FVM   Analytic  (An-FVM)/FVM | insulated: FVM  Analytic")
    for w, h in ((40, 30), (60, 40), (100, 80)):
        for src in (5, 20):
            base = edge_case(w, h, src, 10.0, False)
            fold = edge_case(w, h, src, 10.0, True)
            ins = edge_case(w, h, src, None, False)
            print(f"{w:3d}x{h:<3d} {src:4d} {base['fvm']:7.3f} {base['analytic']:9.3f} {100 * (base['analytic'] / base['fvm'] - 1):+9.2f} % |"
                  f" {fold['fvm']:9.3f} {fold['analytic']:9.3f} {100 * (fold['analytic'] / fold['fvm'] - 1):+9.2f} % |"
                  f" {ins['fvm']:9.3f} {ins['analytic']:9.3f}")
    print("(3) Culham, Yovanovich, Lemczyk (2000) Table 2: printed and recomputed difference")
    for lab, a, b, pr, rc in culham_table2():
        flag = "" if abs(pr - rc) < 0.05 else "   <- does not follow from the printed temperatures"
        print(f"  {lab:16s} {a:7.1f} {b:7.1f} printed {pr:+6.2f} % recomputed {rc:+6.2f} %{flag}")


if __name__ == "__main__":
    main()
