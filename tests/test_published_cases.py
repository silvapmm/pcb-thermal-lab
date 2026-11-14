#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_published_cases.py
@brief The published plate cases that the documents quote, run through the program's own models (audit of 2.8.0, REVIEW_A1.md section 4, items T1 to T5).
@details Each test pins two things: a one-sided limit against the printed number (the program reads the published plate low, never above it, and the
         amount is the documented one) and a narrow band on the program's own value, so that a model change that moves a number is seen and
         re-baselined on purpose. The independent solver is NOT run here: the references are the printed numbers of the papers and the exact thin-plate
         series (research/published-cases-followup 7). The heavier cases (T6 to T8: Yovanovich-Muzychka-Culham Table 2, Lemczyk Table 4, the coupon
         base stack) run only with PCBT_PUBLISHED_FULL=1, as part of the release gate. Every case takes under a few seconds.
         The printed numbers of Muzychka, Culham and Yovanovich (2003) were compared with the page images of the paper (Tables 1 to 4 and the text of cases 1 to 3,
         printed pp 182 to 184). Seri Lee (1998) is a web article that is not in the local library: its numbers are those read through a page converter
         (research/theory/BIBLIOGRAPHY.md [EC1998Spreading], status S, numbers R), not checked on an image.
         Not written here (audit items left open, with the reason): REVIEW_L4L9 T2, the disc against a radial solver (the review's radial solver is not committed;
         it has to be moved under tests/helpers first); REVIEW_A2 T2, equation 50 of Muzychka, Yovanovich and Culham (2004) for one row of the small-part table (the
         closed form exists in research/paper-case-studies/lib/flux_channel.py, but the quantity to compare, source mean against the program's peak with the face
         term, is the open point 4 of that review and must be decided first); T6 to T8 below.
"""

import os

import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))
import cut_cell_study as study                                  # noqa: E402

from pcbthermal import Problem, SolverOptions, blocks, fvm, simulate   # noqa: E402
from pcbthermal.model import Materials                          # noqa: E402

FULL = os.environ.get("PCBT_PUBLISHED_FULL") == "1"
AMB = 25.0   # Ambient of every Muzychka case in degC


def _centroid(field, dx, cx, cy):
    """!
    @brief Value of a cell field at a point: the mean of the four cells around it (the source centroids fall on cell corners).
    @param field Array (ny, nx) in any unit.
    @param dx Cell size in mm.
    @param cx X of the point in mm.
    @param cy Y of the point in mm.
    @return float The value.
    """
    i, j = int(round(cx / dx)), int(round(cy / dx))
    return float(field[j - 1:j + 1, i - 1:i + 1].mean())


def _sq(xc, yc, c):
    """!
    @brief Square of side c centred at a point.
    @param xc X of the centre in mm.
    @param yc Y of the centre in mm.
    @param c Side in mm.
    @return Tuple (x0, y0, x1, y1) in mm.
    """
    return (xc - c / 2, yc - c / 2, xc + c / 2, yc + c / 2)


def _plate(width, t_mm, k, h, sources, cell_mm):
    """!
    @brief A plate of the papers as the program represents it: one full copper layer of the plate thickness and conductivity on a laminate of 0.01 % of it.
    @details The film h is on the bottom face, the top and the edges are insulated.
    @param width Side of the square plate in mm.
    @param t_mm Plate thickness in mm.
    @param k Plate conductivity in W/mK.
    @param h Film coefficient of the bottom face in W/m2K.
    @param sources List of ((x0, y0, x1, y1) in mm, power in W).
    @param cell_mm Cell of the FVM in mm.
    @return Tuple (Simulation, centroid temperatures in degC, mean temperatures over each source in degC).
    """
    p = Problem.new(width, width, layers=1, thickness_mm=1.0001 * t_mm, copper_um=t_mm * 1e3, ambient=AMB, h_top=1e-6, h_bottom=h, h_side=None,
                    materials=Materials(k_copper=k))
    p.add_full_copper()
    for i, (r, pw) in enumerate(sources):
        p.add_heater(1, pw, rect=r, name=f"S{i}")
    return _read(p, width, sources, cell_mm)


def _read(p, width, sources, cell_mm):
    """!
    @brief Run the FVM on a problem and read the centroid and the mean temperature of every source.
    @param p Problem.
    @param width Board side in mm.
    @param sources List of ((x0, y0, x1, y1) in mm, power in W).
    @param cell_mm Cell of the FVM in mm.
    @return Tuple (Simulation, centroid temperatures in degC, mean temperatures in degC).
    """
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=cell_mm))
    t_map = np.asarray(sim.results["fvm"].T)[0]
    ny, nx = t_map.shape
    dx = width / nx
    xs, ys = (np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dx
    cen, mean = [], []
    for r, _ in sources:
        m = (xs[None, :] > r[0]) & (xs[None, :] < r[2]) & (ys[:, None] > r[1]) & (ys[:, None] < r[3])
        mean.append(float(t_map[m].mean()))
        cen.append(_centroid(t_map, dx, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2))
    return sim, cen, mean


def _thick_warnings(sim):
    """!
    @brief The thick-plate warnings of a simulation.
    @param sim Simulation.
    @return List of strings.
    """
    return [w for w in sim.warnings if "thick and poorly conducting" in w]


# ----------------------------------------------------------------------------------------------------------------------
# T1: Seri Lee's plate through the program's metal-block model
# ----------------------------------------------------------------------------------------------------------------------
LEE_PRINTED = {"centre": 0.66, "edge midpoint": 1.29, "corner": 2.38}      # Printed maximum constriction resistance Rc in K/W
LEE_SERIES = {"centre": 0.6637, "edge midpoint": 1.2799, "corner": 2.2700}  # Exact thin-plate series (research/published-cases-followup 7)


def _lee_problem(position):
    """!
    @brief Seri Lee's plate: an aluminium block 100 x 100 x 1.3 mm (k 200 W/mK) with a 25 x 25 mm 1 W source, R0 = 1 K/W on the fin side.
    @details The block covers a one-layer board whose copper and laminate carry no heat sideways and whose faces are adiabatic; the walls of a block take h_face + h_extra
             while Lee's sides are insulated, so the film comes from plate fins of a tiny face coefficient whose fin ratio brings the exposed face to 100 W/m2K.
    @param position "centre", "edge midpoint" or "corner".
    @return Problem.
    """
    side, src, h_film = 100.0, 25.0, 100.0
    c = (side - src) / 2
    rect = {"centre": (c, c, c + src, c + src), "edge midpoint": (c, 0.0, c + src, src), "corner": (0.0, 0.0, src, src)}[position]
    mat = Materials(k_copper=1.0, k_fr4_through=0.05, k_fr4_inplane=0.05)
    p = Problem.new(side, side, layers=1, thickness_mm=0.2, copper_um=5.0, h_top=0.0, h_bottom=0.0, h_side=None, materials=mat)
    p.add_zone(1, rect=(0, 0, side, side))
    p.add_heater(1, 1.0, rect=rect)
    p.add_heatsink(1, 0.0, rect=(0, 0, side, side), thickness_mm=1.3, k=200.0, contact_r=1e-9, fin_height_mm=50.0, fin_thickness_mm=0.1, fin_pitch_mm=1.0)
    s = p.heatsinks[0]
    lo, hi = 1e-3, h_film
    for _ in range(200):                                      # bisection on the face coefficient: h_face x fin ratio = h_film on the exposed face
        mid = np.sqrt(lo * hi)
        lo, hi = (lo, mid) if blocks.exposed_h(s, mid) > h_film else (mid, hi)
    p.board.h_top = mid
    return p


@pytest.mark.parametrize("position", list(LEE_PRINTED))
def test_t1_seri_lee_plate_through_the_block_model(position):
    """!
    @brief Seri Lee (Electronics Cooling, January 1998): Rc of a 100 x 100 x 1.3 mm plate with a 25 x 25 mm source at the centre, an edge and a corner.
    @details Source: Seri Lee, "Calculating spreading resistance in heat sinks", Electronics Cooling, January 1998; printed maximum constriction resistance
             0.66 / 1.29 / 2.38 K/W. The program's block model (blocks.py, FVM, 1 mm cell) reads Rc = maximum minus mean of the block temperature. Tolerance: within
             0.5 % of the exact thin-plate series 0.6637 / 1.2799 / 2.2700 (measured -0.13 / -0.07 / -0.05 %), and within +1 / -1.5 / -5.5 % of the printed values
             (measured +0.4 / -0.9 / -4.7 %); the corner must stay BELOW the printed 2.38 (one-sided, the printed corner is a rounded fit of the article).
             A failure of the first bound means the block layer no longer solves the plate it claims to; of the second, that the document statement 'within 5 % of Lee'
             has moved.
    @param position Source position name.
    @return None.
    """
    p = _lee_problem(position)
    t_block = np.asarray(fvm.solve_steady(p, cell_mm=1.0).arrays["block_T"])[0]
    rc = float(t_block.max() - t_block.mean())
    assert rc == pytest.approx(LEE_SERIES[position], rel=0.005)
    bounds = {"centre": (-0.015, 0.01), "edge midpoint": (-0.015, 0.01), "corner": (-0.055, 0.0)}[position]
    err = rc / LEE_PRINTED[position] - 1.0
    assert bounds[0] <= err <= bounds[1]
    if position == "corner":
        assert rc < LEE_PRINTED["corner"]


# ----------------------------------------------------------------------------------------------------------------------
# T2: Muzychka, Culham and Yovanovich (2003), case 3, the cross
# ----------------------------------------------------------------------------------------------------------------------
def test_t2_muzychka_cross_case_3():
    """!
    @brief Muzychka, Culham and Yovanovich, J. Electronic Packaging 125 (2003) 178-185, case 3: five 20 x 20 mm sources of 5 W in a cross on a 100 x 100 x 10 mm plate.
    @details k 50 W/mK, h 50 W/m2K on the bottom, ambient 25 degC; printed maximum temperature 80.61 degC at the centre. The FVM at 1 mm reads 79.44 +- 0.1 degC
             (one node through the thickness is the column mean): the shortfall is 0 to 2.5 % of the 55.6 K rise (measured 2.1 %), never above the paper.
             The thick-plate warning stays silent (bound 2.8 % of the rise, below the 5 % limit). A failure of the band means the model moved; a reading above 80.61
             would mean it now exceeds the surface value the paper reports (a double count of the film).
    @return None.
    """
    src = [(_sq(50, 50, 20), 5.0), (_sq(30, 50, 20), 5.0), (_sq(70, 50, 20), 5.0), (_sq(50, 30, 20), 5.0), (_sq(50, 70, 20), 5.0)]
    sim, cen, _ = _plate(100.0, 10.0, 50.0, 50.0, src, 1.0)
    assert cen[0] == pytest.approx(79.44, abs=0.1)
    shortfall = (80.61 - cen[0]) / (80.61 - AMB)
    assert 0.0 <= shortfall <= 0.025
    assert _thick_warnings(sim) == []


# ----------------------------------------------------------------------------------------------------------------------
# T3: case 2, the baseplate of a heat sink
# ----------------------------------------------------------------------------------------------------------------------
CASE2_SOURCES = [(_sq(12.5, 12.5, 10), 10.0), (_sq(37.5, 12.5, 10), 25.0), (_sq(12.5, 37.5, 10), 20.0), (_sq(37.5, 37.5, 10), 15.0)]
CASE2_PAPER = [97.40, 103.82, 101.28, 99.94]                  # Printed centroid temperatures in degC (Tables 3 and 4)
CASE2_COLUMN_MEAN = [95.35, 99.15, 97.49, 97.01]              # 3D surface centroid minus the through-thickness term (research/muzychka-case2-analytic 3), degC


def test_t3_muzychka_case_2_baseplate():
    """!
    @brief Muzychka, Culham and Yovanovich (2003), case 2 (Tables 3 and 4): a 50 x 50 x 10 mm baseplate, k 150 W/mK, h 400 W/m2K, four 10 x 10 mm sources of 10, 25, 20, 15 W.
    @details Printed centroids 97.40 / 103.82 / 101.28 / 99.94 degC (ambient 25 degC assumed, not printed). The FVM at 1 mm reads each centroid 2.5 to 6.0 K below the paper
             (measured 2.9 / 5.5 / 4.7 / 3.8 K), never above it; this is the documented thick-plate limit (through-thickness term plus the film on the node, research/
             muzychka-case2-analytic 3). The thick-plate warning fires on all four sources. With the film put through the half plate (h = 1/(1/400 + 0.01/300) = 394.74
             W/m2K in the input) the FVM reads the 3D column mean of the research within 0.15 K (measured 0.04 to 0.08 K), which proves the film term is the part of the
             gap that is not a bound. A failure of the shortfall band means the plate model moved; a failure of the column mean that the film treatment changed (expected
             when fix/face-film-half-slab removes the film term: then re-baseline with the reason).
    @return None.
    """
    sim, cen, _ = _plate(50.0, 10.0, 150.0, 400.0, CASE2_SOURCES, 1.0)
    for c, paper in zip(cen, CASE2_PAPER):
        assert 2.5 <= paper - c <= 6.0
    assert len(_thick_warnings(sim)) == 4
    _, cen_h, _ = _plate(50.0, 10.0, 150.0, 394.74, CASE2_SOURCES, 1.0)
    assert np.max(np.abs(np.asarray(cen_h) - np.asarray(CASE2_COLUMN_MEAN))) < 0.15


# ----------------------------------------------------------------------------------------------------------------------
# T4 and T5: case 1 (a) and case 1 (b)
# ----------------------------------------------------------------------------------------------------------------------
CASE1_SOURCES = [(_sq(90, 90, 25), 10.0), (_sq(210, 210, 25), 15.0)]


def test_t4_muzychka_case_1a_thick_plate():
    """!
    @brief Muzychka, Culham and Yovanovich (2003), case 1 (a): a 300 x 300 x 10 mm plate, k 10 W/mK, h 10 W/m2K on the bottom, two 25 x 25 mm sources of 10 W and 15 W.
    @details Printed centroids 84.97 and 108.43 degC (Table 1). The FVM at 2.5 mm reads them 8.4 % and 9.0 % of the paper's rise low, never above; bounds 7.9 to 8.9 %
             and 8.5 to 9.5 % (half a point around the measured values: a 1 % change of the plate model is seen); the thick-plate warning fires on both sources (bounds
             15 and 16 % of the rise). A failure means the thick-plate behaviour of the single node moved.
    @return None.
    """
    sim, cen, _ = _plate(300.0, 10.0, 10.0, 10.0, CASE1_SOURCES, 2.5)
    for c, paper, lo, hi in zip(cen, (84.97, 108.43), (0.079, 0.085), (0.089, 0.095)):
        short = (paper - c) / (paper - AMB)
        assert lo <= short <= hi
    assert len(_thick_warnings(sim)) == 2


def test_t5_muzychka_case_1b_spreader_layer():
    """!
    @brief Muzychka, Culham and Yovanovich (2003), case 1 (b), Table 2: case 1 (a) with a 2 mm layer of k 350 W/mK on top (spreader on a 10 mm k 10 W/mK substrate).
    @details Printed centroids 56.55 and 59.94 degC. The program maps the spreader as copper layer 1 over a dielectric gap of the substrate and a 1 um copper layer that
             carries the bottom film. The FVM at 2.5 mm reads within 0.3 % of the paper's rise (measured 0.14 % and 0.16 % low). A failure means the layered
             idealisation no longer reproduces the thin spreader on a thick substrate, the case where one node per layer is accurate.
    @return None.
    """
    mat = Materials(k_copper=350.0, k_fr4_through=10.0, k_fr4_inplane=10.0)
    p = Problem.new(300.0, 300.0, layers=2, thickness_mm=12.001, copper_um=2000.0, ambient=AMB, h_top=1e-6, h_bottom=10.0, h_side=None, materials=mat)
    p.board.copper_thickness = [2e-3, 1e-6]
    p.add_full_copper(layers=[1])
    p.add_full_copper(layers=[2], fill=1.0)
    for i, (r, pw) in enumerate(CASE1_SOURCES):
        p.add_heater(1, pw, rect=r, name=f"S{i}")
    _, cen, _ = _read(p, 300.0, CASE1_SOURCES, 2.5)
    for c, paper in zip(cen, (56.55, 59.94)):
        assert abs(paper - c) / (paper - AMB) <= 0.003


# ----------------------------------------------------------------------------------------------------------------------
# Independent-reference limits stored as numbers (REVIEW_A2 T1, REVIEW_L4L9 T1)
# ----------------------------------------------------------------------------------------------------------------------
FE_LIMIT_200, FE_LIMIT_1000 = 36.981, 24.332   # Finite-element limits (Richardson plus through-thickness correction) of the 10 x 10 mm plate in K, research/independent-fem-edge README 3(a)


def _strong_edge_plate(h_side):
    """!
    @brief The 10 x 10 mm, four-layer 1.6 mm plate (35 um copper to the wall, FR-4 0.3 W/mK, h_top 10, h_bottom 200 W/m2K, h_side as given) with a 0.5 W source of 3 x 2 mm.
    @param h_side Edge coefficient in W/m2K.
    @return Problem.
    """
    p = Problem.new(10.0, 10.0, 4, 1.6, 35.0, h_top=10.0, h_bottom=200.0, h_side=h_side, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, 5):
        p.add_zone(layer, rect=(0.0, 0.0, 10.0, 10.0))
    p.add_heater(1, 0.5, rect=(1, 4, 4, 6))
    return p


def test_a2_t1_strong_edge_plate_against_the_stored_finite_element_limit():
    """!
    @brief The four-layer 1.6 mm plate with a cooled edge against the stored finite-element limit (audit REVIEW_A2 T1).
    @details Reference: research/independent-fem-edge README 3(a): the hottest rise 36.981 K at h_side 200 and 24.332 K at 1000 W/m2K (Richardson limit of three plan meshes plus
             the through-thickness correction, 0.07 and 0.06 % band). The same README gives 36.975 / 24.338 K for the same board in section 6 (its corrected
             thickness term) and about 36.967 K from a uniform plan pair (section 7): the limits are known to about 0.05 %, far inside the bounds below. The FE value is
             the point maximum of the top face, the program's the hottest 0.25 mm cell mean (-0.13 / -0.20 % on the FE field, README 7); the bounds are on the
             stored numbers as the edge warnings quote them. The FVM at 0.25 mm with the default laminate sub-gaps reads 36.77 K (-0.57 %) and 23.48 K (-3.52 %), on
             the cool side; bounds: -1.0 to -0.2 % at 200 and -4.0 to -3.0 % at 1000 W/m2K (half a point around the measured values, both sides, so that an improvement
             or a worsening of about 1 % is seen; dropping the laminate edge band or the cut-cell film fails). A failure means the edge treatment of the laminate
             moved; re-baseline only with the reason and update the edge warning texts that quote these numbers.
    @return None.
    """
    for h_side, fe, lo, hi in ((200.0, FE_LIMIT_200, -0.010, -0.002), (1000.0, FE_LIMIT_1000, -0.040, -0.030)):
        rise = fvm.solve_steady(_strong_edge_plate(h_side), cell_mm=0.25).t_max - 25.0
        assert lo <= rise / fe - 1.0 <= hi


def test_l4l9_t1_the_cut_cell_peak_does_not_depend_on_the_film_floor(monkeypatch):
    """!
    @brief The FVM peak of the recessed turned square at 2000 W/m2K is the same for any value of fvm.EDGE_FILM_FLOOR (audit REVIEW_L4L9 T1).
    @details Board: tests/helpers/cut_cell_study.recessed_board (a 20 mm square turned 20 degrees, the top copper held 1.2 mm inside the outline), 1 mm cell. Measured: 98.075 degC
             for floors 0.05, 0.1, 0.25 and 0.5 (the floor is only a safety net since 2.7.0). `docs/theory.md` 2.1.1 states this independence. A failure means the floor binds
             again (a node outside the board by more than S / H), and the theory statement is false.
    @param monkeypatch pytest fixture.
    @return None.
    """
    peaks = []
    for floor in (0.05, 0.5):
        monkeypatch.setattr(fvm, "EDGE_FILM_FLOOR", floor)
        peaks.append(fvm.solve_steady(study.recessed_board(2000.0), cell_mm=1.0).t_max)
    assert peaks[0] == pytest.approx(peaks[1], abs=1e-6)
    assert peaks[0] == pytest.approx(98.075, abs=0.01)


# ----------------------------------------------------------------------------------------------------------------------
# T6 to T8: the release gate (PCBT_PUBLISHED_FULL=1)
# ----------------------------------------------------------------------------------------------------------------------
@pytest.mark.skipif(not FULL, reason="release gate: set PCBT_PUBLISHED_FULL=1")
@pytest.mark.xfail(strict=True, reason="T6 to T8 are not written: they need the study constructions of research/published-cases-followup moved under tests/helpers")
def test_t6_to_t8_are_the_release_gate_placeholder():
    """!
    @brief Placeholder of the release-gate cases T6 (Yovanovich-Muzychka-Culham Table 2), T7 (Lemczyk Table 4) and T8 (the coupon base stack).
    @details They need the study constructions of research/published-cases-followup (3.3, 5.3 and 4); they are written when that code is moved under tests/helpers.
             Until then the test is a strict xfail with the gate variable on, so that the gate reports them as missing instead of passing silently.
    @return None.
    """
    pytest.fail("T6 to T8 are not written yet: see REVIEW_A1.md section 4")
