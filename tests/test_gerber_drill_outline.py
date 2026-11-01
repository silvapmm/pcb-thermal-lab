#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_gerber_drill_outline.py
@brief Tests of the Excellon reader and of the board outline of pcbthermal.gerber on synthetic files with known holes, slots and areas.
@details Drills: metric and inch headers, leading and trailing zero formats, decimal coordinates, plating from the X2 comment and from the tool comments, tool diameters, repeat
         command, routed and canned slots, X2 Gerber drill layers and the refusals. Outline: a rectangle, a rounded rectangle (closed form with arcs), a board with a cut-out, a panel of two
         boards, a region outline, reversed segment order, a gap that makes the contour open (refusal naming the file and the gap) and the tolerance.
"""

import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))

import gerber_text as gt  # noqa: E402
from pcbthermal import gerber as G  # noqa: E402
from pcbthermal.gerber.outline import signed_area  # noqa: E402


def test_metric_drill_with_header_plating_and_two_tools():
    text = ("M48\n; #@! TF.FileFunction,Plated,1,4,PTH\nMETRIC,LZ\nT1C0.300\nT2C1.000\n%\nG90\nG05\nT1\nX10.5Y20.25\nX11.5Y20.25\nT2\nX30.0Y40.0\nM30\n")
    d = G.read_drill(text, "a-PTH.drl")
    assert d.plated is True and d.span == (1, 4) and d.tools == {1: 0.3, 2: 1.0}
    assert [(h.x, h.y, h.diameter, h.plated) for h in d.holes] == [(10.5, 20.25, 0.3, True), (11.5, 20.25, 0.3, True), (30.0, 40.0, 1.0, True)]
    assert not any(h.is_slot for h in d.holes)


def test_nonplated_function():
    d = G.read_drill("M48\n; #@! TF.FileFunction,NonPlated,1,4,NPTH\nMETRIC\nT1C3.2\n%\nT1\nX1.0Y2.0\nM30\n", "a-NPTH.drl")
    assert d.plated is False and d.holes[0].plated is False and d.holes[0].diameter == pytest.approx(3.2)


def test_altium_type_comment_and_tool_comment_plating():
    d = G.read_drill("M48\n;TYPE=NON_PLATED\nMETRIC\nT1C0.5\n%\nT1\nX1.0Y1.0\nM30\n", "x.drl")
    assert d.plated is False
    t = "M48\n;T01 Holesize 1. = 12.000000 MILS PLATED\n;T02 Holesize 2. = 100.000000 MILS NON_PLATED\nINCH,TZ\n%\nT01\nX010000Y020000\nT02\nX030000Y040000\nM30\n"
    d2 = G.read_drill(t, "x.drl")
    assert [(round(h.diameter, 4), h.plated) for h in d2.holes] == [(0.3048, True), (2.54, False)]
    # INCH, TZ with the default 2.4 format: trailing zeros kept, so "010000" is 01.0000 inch
    assert d2.holes[0].x == pytest.approx(25.4) and d2.holes[0].y == pytest.approx(50.8)


def test_zero_suppression_formats_and_default_formats():
    lz = G.read_drill("M48\nMETRIC,LZ,000.000\nT1C1\n%\nT1\nX012345Y1\nM30\n", "lz.drl")          # leading zeros kept, trailing omitted: 012.345 and 100.000
    assert (lz.holes[0].x, lz.holes[0].y) == (pytest.approx(12.345), pytest.approx(100.0))
    tz = G.read_drill("M48\nMETRIC,TZ,000.000\nT1C1\n%\nT1\nX12345Y1000\nM30\n", "tz.drl")         # trailing zeros kept, leading omitted: 12.345 and 1.000
    assert (tz.holes[0].x, tz.holes[0].y) == (pytest.approx(12.345), pytest.approx(1.0))
    inch = G.read_drill("M48\nINCH\nT1C0.02\n%\nT1\nX010000Y020000\nM30\n", "in.drl")             # default 2.4
    assert inch.holes[0].x == pytest.approx(25.4) and inch.tools[1] == pytest.approx(0.508)
    m72 = G.read_drill("M48\nM72\nT1C0.02\n%\nT1\nX1.0Y1.0\nM30\n", "m72.drl")
    assert m72.holes[0].x == pytest.approx(25.4)


def test_modal_coordinates_and_repeat():
    d = G.read_drill("M48\nMETRIC\nT1C1\n%\nT1\nX10.0Y5.0\nX20.0\nY6.0\nR3X2.0Y0\nM30\n", "m.drl")
    assert [(h.x, h.y) for h in d.holes] == [(10, 5), (20, 5), (20, 6), (22, 6), (24, 6), (26, 6)]


def test_slots_routed_and_canned():
    text = "M48\nMETRIC\nT1C0.8\n%\nT1\nG00X10.0Y10.0\nM15\nG01X14.0Y10.0\nM16\nG05\nX30.0Y30.0\nX40.0Y1.0G85X40.0Y5.0\nM30\n"
    d = G.read_drill(text, "s.drl")
    slots = [h for h in d.holes if h.is_slot]
    assert len(d.holes) == 3 and len(slots) == 2
    assert (slots[0].x, slots[0].y, slots[0].x_end, slots[0].y_end, slots[0].diameter) == (10.0, 10.0, 14.0, 10.0, 0.8)
    assert (slots[1].x, slots[1].y, slots[1].x_end, slots[1].y_end) == (40.0, 1.0, 40.0, 5.0)


def test_x2_gerber_drill_layer():
    text = ("%FSLAX46Y46*%\n%MOMM*%\n%TF.FileFunction,Plated,1,4,PTH*%\n%ADD10C,0.6*%\n%ADD11C,1.0*%\nD10*\nX1000000Y2000000D03*\nD11*\n"
            "X5000000Y5000000D02*\nX9000000Y5000000D01*\nM02*\n")
    d = G.read_drill(text, "drill.gbr")
    assert d.plated is True and d.span == (1, 4)
    assert (d.holes[0].diameter, d.holes[0].is_slot) == (pytest.approx(0.6), False)
    assert d.holes[1].is_slot and d.holes[1].x_end == pytest.approx(9.0)


@pytest.mark.parametrize("text,feature", [
    ("M48\nMETRIC\nT1C1\n%\nT1\nICI\nX1Y1\nM30\n", "incremental"),
    ("M48\nMETRIC\nT1C1\n%\nT1\nG00X1Y1\nM15\nG02X3Y3I1J0\nM16\nM30\n", "arcs"),
    ("M48\nMETRIC\nT1C1\n%\nM25\nT1\nX1Y1\nM01\nM30\n", "pattern"),
    ("M48\nT1C1\n%\nT1\nX1Y1\nM30\n", "unit"),
])
def test_drill_refusals_name_the_file_and_the_feature(text, feature):
    with pytest.raises(G.UnsupportedFeatureError) as exc:
        G.read_drill(text, "bad.drl")
    assert exc.value.file == "bad.drl" and feature in exc.value.feature


def test_tool_without_a_diameter_is_an_error():
    with pytest.raises(G.GerberError, match="T2"):
        G.read_drill("M48\nMETRIC\nT1C1\n%\nT2\nX1Y1\nM30\n", "bad.drl")


# ---------------------------------------------------------------------------------------------------------------------------------
# Outline
# ---------------------------------------------------------------------------------------------------------------------------------

def rect_lines(x0, y0, x1, y1):
    """!
    @brief The four sides of a rectangle as draws.
    @param x0 Left (mm).
    @param y0 Bottom (mm).
    @param x1 Right (mm).
    @param y1 Top (mm).
    @return str Gerber text.
    """
    return gt.line(x0, y0, x1, y0) + gt.line(x1, y0, x1, y1) + gt.line(x1, y1, x0, y1) + gt.line(x0, y1, x0, y0)


def test_rectangle_outline_area_bbox_and_orientation():
    text = gt.header("%ADD10C,0.1*%\n") + rect_lines(5, 10, 55, 40) + gt.end()
    o = G.read_outline(text, "Edge.Cuts.gbr")
    assert len(o.polygons) == 1 and o.polygons[0].holes == []
    assert o.area_mm2 == pytest.approx(50 * 30) and o.bbox == (5, 10, 55, 40)
    x, y = o.polygons[0].outer[:, 0], o.polygons[0].outer[:, 1]
    assert 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y) > 0                # counter-clockwise


def test_zero_width_aperture_and_segments_in_scrambled_and_reversed_order():
    sides = [gt.line(55, 10, 5, 10), gt.line(5, 40, 5, 10), gt.line(55, 40, 55, 10), gt.line(5, 40, 55, 40)]       # reversed directions, scrambled order
    text = gt.header("%ADD10C,0*%\n") + "".join(sides) + gt.end()
    assert G.read_outline(text, "o.gbr").area_mm2 == pytest.approx(1500)


def test_rounded_rectangle_with_arcs_matches_the_closed_form():
    w, h, r = 40.0, 20.0, 3.0
    n = gt.num
    t = gt.header("%ADD10C,0.1*%\nG75*\nD10*\n")
    t += f"X{n(r)}Y{n(0)}D02*\nG01*\nX{n(w - r)}Y{n(0)}D01*\nG03*\nX{n(w)}Y{n(r)}I{n(0)}J{n(r)}D01*\nG01*\nX{n(w)}Y{n(h - r)}D01*\nG03*\nX{n(w - r)}Y{n(h)}I{n(-r)}J{n(0)}D01*\n"
    t += f"G01*\nX{n(r)}Y{n(h)}D01*\nG03*\nX{n(0)}Y{n(h - r)}I{n(0)}J{n(-r)}D01*\nG01*\nX{n(0)}Y{n(r)}D01*\nG03*\nX{n(r)}Y{n(0)}I{n(r)}J{n(0)}D01*\n" + gt.end()
    o = G.read_outline(t, "round.gbr")
    exact = w * h - (4 - math.pi) * r * r
    assert o.area_mm2 == pytest.approx(exact, rel=5e-4)                              # the chord error of 0.005 mm makes the polygon slightly smaller
    assert o.area_mm2 <= exact


def test_board_with_a_cutout_and_a_circular_hole():
    hole = f"G75*\nD10*\nX{gt.num(30)}Y{gt.num(25)}D02*\nG03*\nX{gt.num(30)}Y{gt.num(25)}I{gt.num(-2)}J{gt.num(0)}D01*\n"       # a circle of radius 2 centred at (28, 25)
    text = gt.header("%ADD10C,0.1*%\n") + rect_lines(0, 0, 50, 40) + rect_lines(5, 5, 15, 10) + hole + gt.end()
    o = G.read_outline(text, "h.gbr")
    assert len(o.polygons) == 1 and len(o.polygons[0].holes) == 2
    assert o.area_mm2 == pytest.approx(2000 - 50 - math.pi * 4, rel=1e-3)
    assert all(signed_area(h) < 0 for h in o.polygons[0].holes)          # clockwise


def test_panel_of_two_boards_and_an_island_in_a_cutout():
    text = gt.header("%ADD10C,0.1*%\n") + rect_lines(0, 0, 20, 20) + rect_lines(30, 0, 50, 20) + gt.end()
    o = G.read_outline(text, "p.gbr")
    assert len(o.polygons) == 2 and o.area_mm2 == pytest.approx(800)
    nested = gt.header("%ADD10C,0.1*%\n") + rect_lines(0, 0, 40, 40) + rect_lines(5, 5, 35, 35) + rect_lines(10, 10, 20, 20) + gt.end()
    o2 = G.read_outline(nested, "n.gbr")
    assert len(o2.polygons) == 2 and o2.area_mm2 == pytest.approx(1600 - 900 + 100)           # board, cut-out, island on its own


def test_region_outline_is_taken_as_a_contour():
    text = gt.header() + gt.region([(0, 0), (30, 0), (30, 10), (0, 10)]) + gt.end()
    assert G.read_outline(text, "r.gbr").area_mm2 == pytest.approx(300)


def test_open_contour_is_refused_with_file_gap_and_position():
    sides = gt.line(0, 0, 50, 0) + gt.line(50, 0, 50, 40) + gt.line(50, 40, 0, 40) + gt.line(0, 40, 0, 0.05)              # a gap of 0.05 mm in the last side
    text = gt.header("%ADD10C,0.1*%\n") + sides + gt.end()
    with pytest.raises(G.OutlineError) as exc:
        G.read_outline(text, "Gap-Edge_Cuts.gbr")
    msg = str(exc.value)
    assert "Gap-Edge_Cuts.gbr" in msg and "not a closed contour" in msg and "0.05" in msg
    # A tolerance larger than the gap closes it
    assert G.read_outline(text, "Gap.gbr", tol_mm=0.06).area_mm2 == pytest.approx(2000, rel=1e-3)


def test_branching_and_empty_profile_are_refused():
    t = gt.header("%ADD10C,0.1*%\n") + rect_lines(0, 0, 10, 10) + gt.line(5, 5, 5, 0) + gt.end()                                # a stray spur touching the side: three segments at one joint
    with pytest.raises(G.OutlineError):
        G.read_outline(t, "b.gbr")
    with pytest.raises(G.OutlineError, match="no closed contour"):
        G.read_outline(gt.header("%ADD10C,0.1*%\n") + gt.flash(1, 1) + gt.end(), "f.gbr")
