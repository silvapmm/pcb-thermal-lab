#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_gerber_spec.py
@brief Independent tests of pcbthermal.gerber written by the reviewer from the Ucamco Gerber layer format specification (revision 2026.05) and from hostile inputs.
@details The tests of test_gerber_reader.py were written from the executor's own reading of the specification; these check the weak spots the review found against the
         text of the specification and against closed forms: the single-quadrant example of the specification (G74), the zero-length G74 arc against the full G75 circle,
         the rotation of every macro primitive about the macro origin (the specification's Triangle_30 example), the vertex of a polygon and the gaps of a thermal,
         the step order of a step and repeat (first Y, then X), draws with a rectangle (exact hull) and the refusal of draws with other apertures, the attribute
         deletion (TD) of a user attribute, M00, encodings (byte order mark, CR line ends), and the limits for hostile files: every failure is a GerberError
         (never a raw exception, never a hang), including a small deterministic fuzz of mutated files, and the raster window is bounded.
"""

import io
import math
import os
import random
import sys
import zipfile

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))

import gerber_text as gt  # noqa: E402
from pcbthermal import gerber as G  # noqa: E402
from pcbthermal.gerber import macros, parser, raster  # noqa: E402


def render(text, win, pix=0.02, ss=2):
    """!
    @brief Parse and rasterise a text.
    @param text Gerber text.
    @param win  Window.
    @param pix  Pixel (mm).
    @param ss   Supersampling.
    @return tuple (coverage as a fraction 0..1, area mm2, centroid x, centroid y).
    """
    cov = G.rasterize(G.parse_layer(text, "spec.gbr"), win, pix, ss) / 255.0
    area = cov.sum() * pix * pix
    ii, jj = np.indices(cov.shape)
    cx = win.x_left + ((jj + 0.5) * cov).sum() / max(cov.sum(), 1e-12) * pix
    cy = win.y_top - ((ii + 0.5) * cov).sum() / max(cov.sum(), 1e-12) * pix
    return cov, area, cx, cy


def at(cov, win, x, y, pix=0.02):
    """!
    @brief Coverage of the pixel that holds a point.
    @param cov Coverage fraction.
    @param win Window.
    @param x   X (mm).
    @param y   Y (mm).
    @param pix Pixel (mm).
    @return float Coverage 0..1.
    """
    return cov[int((win.y_top - y) / pix), int((x - win.x_left) / pix)]


MACRO = "%FSLAX46Y46*%\n%MOMM*%\n%AM{name}*{body}*%\n%ADD10{name}*%\nD10*\nX0Y0D03*\nM02*\n"


# ----------------------------------------------------------------------------------------------------------------------------------
# Arcs: the single-quadrant example of the specification (section 8.x, 'Single-quadrant arc mode (G74)')
# ----------------------------------------------------------------------------------------------------------------------------------

def test_single_quadrant_example_of_the_specification():
    # Four counter-clockwise quarter arcs of radius 4 around (7, 6) with unsigned offsets, then two draws through the centre (format 2.2, mm)
    text = ("%FSLAX22Y22*%\n%MOMM*%\n%ADD10C,0.5*%\nG74*\nD10*\nX1100Y600D02*\nG03*\nX700Y1000I400J0D01*\nX300Y600I0J400D01*\nX700Y200I400J0D01*\n"
            "X1100Y600I0J400D01*\nX300D02*\nG01*\nX1100D01*\nX700Y200D02*\nY1000D01*\nM02*\n")
    win = G.Window(2, 11.5, 10, 10)
    cov, area, cx, cy = render(text, win)
    # Exact area of the union (ring of radius 4 and width 0.5, two capsules of length 8), by a vector union (shapely, 2000 segments per quarter): 19.8108 mm2
    assert area == pytest.approx(19.8108, rel=3e-3)
    assert (cx, cy) == (pytest.approx(7.0, abs=1e-3), pytest.approx(6.0, abs=1e-3))
    # Every quarter is on the circle of radius 4 around (7, 6): the points at 45 degrees are copper, the centre of each quadrant away from the lines is not
    for ang in (45, 135, 225, 315):
        x, y = 7 + 4 * math.cos(math.radians(ang)), 6 + 4 * math.sin(math.radians(ang))
        assert at(cov, win, x, y) == 1.0
        assert at(cov, win, 7 + 2 * math.cos(math.radians(ang)), 6 + 2 * math.sin(math.radians(ang))) == 0.0


def test_single_quadrant_clockwise_quarters_make_the_same_ring():
    text = ("%FSLAX22Y22*%\n%MOMM*%\n%ADD10C,0.5*%\nG74*\nD10*\nX1100Y600D02*\nG02*\nX700Y200I400J0D01*\nX300Y600I0J400D01*\nX700Y1000I400J0D01*\n"
            "X1100Y600I0J400D01*\nM02*\n")
    _, area, cx, cy = render(text, G.Window(2, 11.5, 10, 10))
    assert area == pytest.approx(2 * math.pi * 4 * 0.5, rel=2e-3)
    assert (cx, cy) == (pytest.approx(7.0, abs=1e-3), pytest.approx(6.0, abs=1e-3))


def test_start_equal_to_end_is_a_dot_in_g74_and_a_full_circle_in_g75():
    # The specification's own pair of examples: radius 5, aperture 0.5
    base = "%FSLAX22Y22*%\n%MOMM*%\n%ADD10C,0.5*%\nD10*\nG01*\nX0Y600D02*\n{mode}*\nG02*\nX0Y600I500J0D01*\nM02*\n"
    win = G.Window(-1, 12, 12, 12)
    _, dot, cx, cy = render(base.format(mode="G74"), win)
    assert dot == pytest.approx(math.pi * 0.25 ** 2, rel=2e-2) and (cx, cy) == (pytest.approx(0.0, abs=0.01), pytest.approx(6.0, abs=0.01))
    _, ring, cx, cy = render(base.format(mode="G75"), win)
    assert ring == pytest.approx(2 * math.pi * 5 * 0.5, rel=2e-3) and (cx, cy) == (pytest.approx(5.0, abs=0.01), pytest.approx(6.0, abs=0.01))


def test_multi_quadrant_offsets_are_signed():
    # G75: the centre is the start plus (I, J) with their signs; a half circle from (5, 0) to (-5, 0) counter-clockwise around the origin goes through (0, 5)
    text = gt.header("%ADD10C,0.2*%\n") + f"G75*\nD10*\nX{gt.num(5)}Y0D02*\nG03*\nX{gt.num(-5)}Y0I{gt.num(-5)}J0D01*\n" + gt.end()
    win = G.Window(-6, 6, 12, 12)
    cov, area, _, cy = render(text, win)
    assert at(cov, win, 0, 5) == 1.0 and at(cov, win, 0, -5) == 0.0 and cy > 3.0
    assert area == pytest.approx(math.pi * 5 * 0.2 + math.pi * 0.1 ** 2, rel=3e-3)


# ----------------------------------------------------------------------------------------------------------------------------------
# Macro primitives (section 4.5.1): parameter order and rotation about the macro origin
# ----------------------------------------------------------------------------------------------------------------------------------

def test_triangle_30_example_of_the_specification():
    body = "4,1,3,\n1,-1,\n1,1,\n2,1,\n1,-1,\n30"
    win = G.Window(-3, 3, 6, 6)
    _, area, cx, cy = render(MACRO.format(name="Triangle_30", body=body), win, pix=0.005)
    a = math.radians(30)
    gx, gy = 4 / 3, 1 / 3                                                     # centroid of (1,-1), (1,1), (2,1) before the rotation about the origin
    assert area == pytest.approx(1.0, rel=2e-3)
    assert (cx, cy) == (pytest.approx(gx * math.cos(a) - gy * math.sin(a), abs=2e-3), pytest.approx(gx * math.sin(a) + gy * math.cos(a), abs=2e-3))


@pytest.mark.parametrize("name,body,area,centre", [
    ("CL", "21,1,2,1,3,0,90", 2.0, (0.0, 3.0)),                              # centre line: centre (3, 0) turned 90 degrees about the origin, not about itself
    ("VL", "20,1,0.5,1,0,3,0,90", 1.0, (0.0, 2.0)),                          # vector line from (1, 0) to (3, 0), turned 90 degrees
    ("CI", "1,1,1,2,0,90", math.pi / 4, (0.0, 2.0)),                         # circle with the optional rotation of its centre
    ("PO", "5,1,3,1,0,2,90", 3 * math.sqrt(3) / 4, (0.0, 1.0)),              # polygon: the centre turns too
])
def test_macro_primitives_rotate_about_the_macro_origin(name, body, area, centre):
    _, a, cx, cy = render(MACRO.format(name=name, body=body), G.Window(-4, 5, 8, 9), pix=0.01)
    assert a == pytest.approx(area, rel=4e-3)
    assert (cx, cy) == (pytest.approx(centre[0], abs=3e-3), pytest.approx(centre[1], abs=3e-3))


def test_polygon_first_vertex_is_on_the_rotated_x_axis():
    win = G.Window(-1.5, 1.5, 3, 3)
    cov, _, _, _ = render(MACRO.format(name="TRI", body="5,1,3,0,0,2,0"), win)
    assert at(cov, win, 0.9, 0.0) == 1.0 and at(cov, win, -0.9, 0.0) == 0.0          # a vertex at (1, 0), an edge at x = -0.5
    cov, _, _, _ = render(MACRO.format(name="TRI", body="5,1,3,0,0,2,90"), win)
    assert at(cov, win, 0.0, 0.9) == 1.0 and at(cov, win, 0.0, -0.9) == 0.0
    cov, _, _, _ = render("%FSLAX46Y46*%\n%MOMM*%\n%ADD10P,2X3X180*%\nD10*\nX0Y0D03*\nM02*\n", win)    # the standard polygon aperture: same convention
    assert at(cov, win, -0.9, 0.0) == 1.0 and at(cov, win, 0.9, 0.0) == 0.0


def test_thermal_gaps_lie_on_the_axes_and_turn_with_the_rotation():
    win = G.Window(-1.2, 1.2, 2.4, 2.4)
    cov, _, _, _ = render(MACRO.format(name="TH", body="7,0,0,2,1.2,0.3,0"), win)
    r = 0.8                                                                    # mid-ring radius
    assert at(cov, win, r, 0) == 0.0 and at(cov, win, 0, r) == 0.0                     # gaps on the axes
    assert at(cov, win, r / math.sqrt(2), r / math.sqrt(2)) == 1.0
    cov, _, _, _ = render(MACRO.format(name="TH", body="7,0,0,2,1.2,0.3,45"), win)
    assert at(cov, win, r / math.sqrt(2), r / math.sqrt(2)) == 0.0 and at(cov, win, r, 0) == 1.0


def test_exposure_off_only_acts_inside_the_macro():
    # The specification's SquareWithHole example: the draw under the hole stays visible
    text = ("%FSLAX26Y26*%\n%MOMM*%\n%AMSquareWithHole*\n21,1,10,10,0,0,0*\n1,0,5,0,0*%\n%ADD10SquareWithHole*%\n%ADD11C,1*%\nG01*\n%LPD*%\nD11*\n"
            "X-8000000Y-2000000D02*\nX8000000Y2000000D01*\nD10*\nX0Y0D03*\nM02*\n")
    win = G.Window(-9, 9, 18, 18)
    cov, _, _, _ = render(text, win, pix=0.05)
    assert at(cov, win, 0.0, 0.0, 0.05) == 1.0                                          # the draw through the hole
    assert at(cov, win, 0.0, 2.0, 0.05) == 0.0                                          # the hole elsewhere
    assert at(cov, win, 4.0, 4.0, 0.05) == 1.0


# ----------------------------------------------------------------------------------------------------------------------------------
# Step and repeat (section 4.12), draws, attributes, formats
# ----------------------------------------------------------------------------------------------------------------------------------

def test_step_and_repeat_steps_first_in_y_then_in_x():
    # Block: a dark square at the origin and a clear square one step left and one step up. Stepping Y first, the copy (1, 0) clears the copy (0, 1) drawn
    # before it, so 3 squares stay; stepping X first would leave 4. The specification: "step the complete block first in Y and then in X".
    sq = lambda x, y: gt.region([(x - 0.4, y - 0.4), (x + 0.4, y - 0.4), (x + 0.4, y + 0.4), (x - 0.4, y + 0.4)])
    text = gt.header() + "%SRX2Y2I1.0J1.0*%\n%LPD*%\n" + sq(0, 0) + "%LPC*%\n" + sq(-1, 1) + "%SR*%\n" + gt.end()
    win = G.Window(-2, 3, 4, 4)
    cov, area, _, _ = render(text, win)
    assert area == pytest.approx(3 * 0.64, rel=1e-3)
    assert at(cov, win, 0, 1) == 0.0 and at(cov, win, 1, 1) == 1.0 and at(cov, win, 1, 0) == 1.0 and at(cov, win, 0, 0) == 1.0


def test_step_and_repeat_copies_keep_the_object_attributes():
    text = gt.header("%ADD10C,0.5*%\n") + "%TO.N,GND*%\n%SRX3Y1I2.0J0*%\n" + gt.flash(0, 0) + "%SR*%\n" + gt.end()
    assert [f.net for f in G.parse_layer(text, "sr.gbr").flashes()] == ["GND"] * 3


def test_rectangle_draw_is_the_exact_hull_at_any_angle():
    # Hull of a w x h rectangle swept along a segment of length L at angle t: w h + L (w |sin t| + h |cos t|)
    w, h, L = 0.6, 0.2, 7.0
    for deg in (0, 30, 45, 77, 90):
        t = math.radians(deg)
        x1, y1 = 1 + L * math.cos(t), 1 + L * math.sin(t)
        text = gt.header(f"%ADD10R,{w}X{h}*%\n") + gt.line(1, 1, x1, y1) + gt.end()
        _, area, _, _ = render(text, G.Window(0, 9, 9, 9), pix=0.01)
        assert area == pytest.approx(w * h + L * (w * abs(math.sin(t)) + h * abs(math.cos(t))), rel=4e-3), deg       # 45 degrees: edges along the sample diagonals, -0.23 %


@pytest.mark.parametrize("aperture", ["O,1X2", "P,1X6", "C,1X0.5"])
def test_draws_with_apertures_other_than_the_solid_circle_or_rectangle_are_refused(aperture):
    if aperture.startswith("C"):
        # A circle with a hole is still the circle aperture: the parser draws its solid disc (the specification allows only solid circles for draws)
        layer = G.parse_layer(gt.header(f"%ADD10{aperture}*%\n") + gt.line(0, 0, 1, 0) + gt.end(), "d.gbr")
        assert len(layer.ops) == 1
        return
    with pytest.raises(G.UnsupportedFeatureError) as exc:
        G.parse_layer(gt.header(f"%ADD10{aperture}*%\n") + gt.line(0, 0, 1, 0) + gt.end(), "d.gbr")
    assert "non-circular" in exc.value.feature
    with pytest.raises(G.UnsupportedFeatureError):
        G.parse_layer(MACRO.format(name="M1", body="1,1,1,0,0").replace("X0Y0D03*", "X0Y0D02*\nX1000000Y0D01*"), "m.gbr")


def test_identity_aperture_transformations_are_accepted_others_refused():
    for cmd in ("LMN", "LR0", "LR0.0", "LS1", "LS1.0"):
        layer = G.parse_layer(gt.header(f"%{cmd}*%\n%ADD10C,1*%\n") + gt.flash(0, 0) + gt.end(), "id.gbr")
        assert len(layer.ops) == 1
    for cmd in ("LMX", "LMXY", "LR45", "LS0.5"):
        with pytest.raises(G.UnsupportedFeatureError):
            G.parse_layer(gt.header(f"%{cmd}*%\n") + gt.end(), "tr.gbr")


def test_attribute_deletion_of_a_user_attribute_keeps_the_standard_ones():
    text = gt.header("%ADD10C,0.5*%\n") + "%TO.N,GND*%\n%TO.C,U1*%\n%TOMyAttr,x*%\n%TDMyAttr*%\n" + gt.flash(0, 0) + "%TD.N*%\n" + gt.flash(1, 0) + gt.end()
    f = G.parse_layer(text, "td.gbr").flashes()
    assert [(p.net, p.ref) for p in f] == [("GND", "U1"), (None, "U1")]


def test_separate_x_and_y_formats_and_both_zero_omissions():
    lead = "%FSLAX24Y35*%\n%MOMM*%\n%ADD10C,1*%\nD10*\nX-12345Y-123456D03*\nM02*\n"
    (_, _, (_, x, y)) = G.parse_layer(lead, "l.gbr").ops[0]
    assert (x, y) == (pytest.approx(-1.2345), pytest.approx(-1.23456))
    trail = "%FSTAX24Y35*%\n%MOMM*%\n%ADD10C,1*%\nD10*\nX-12Y-123D03*\nM02*\n"                  # 12 -> 12.0000, 123 -> 123.00000
    (_, _, (_, x, y)) = G.parse_layer(trail, "t.gbr").ops[0]
    assert (x, y) == (pytest.approx(-12.0), pytest.approx(-123.0))


def test_m00_ends_the_file_and_a_truncated_file_is_flagged():
    body = gt.header("%ADD10C,1*%\n") + gt.flash(0, 0)
    stop = G.parse_layer(body + "M00*\n" + gt.flash(5, 5), "m00.gbr")
    assert len(stop.ops) == 1 and stop.ended
    assert G.parse_layer(body + gt.end(), "ok.gbr").ended
    cut = G.parse_layer(body + gt.flash(5, 5)[:9], "cut.gbr")
    assert not cut.ended


def test_byte_order_mark_and_line_ends():
    text = gt.header("%ADD10C,1*%\n") + gt.flash(1.5, 2.5) + gt.end()
    for variant in ("﻿" + text, text.replace("\n", "\r\n"), text.replace("\n", "\r"), "﻿" + text.replace("\n", "\r\n")):
        (_, _, (_, x, y)) = G.parse_layer(variant, "e.gbr").ops[0]
        assert (x, y) == (pytest.approx(1.5), pytest.approx(2.5))


def test_files_on_disk_are_read_as_utf8_whatever_the_locale(tmp_path):
    p = tmp_path / "latin.gbr"
    p.write_bytes(b"\xef\xbb\xbf" + (gt.header("G04 caf\xe9*\n%ADD10C,1*%\n") + gt.flash(1, 1) + gt.end()).encode("latin-1"))
    layer = G.read_layer(p)                                                    # a BOM and a Latin-1 byte in a comment
    assert len(layer.ops) == 1 and layer.ops[0][2][1] == pytest.approx(1.0)


# ----------------------------------------------------------------------------------------------------------------------------------
# Hostile inputs: every failure is a GerberError, nothing hangs, the window is bounded
# ----------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("expr", ["(" * 60 + "1" + ")" * 60, "-" * 60 + "1", "9" * 400, "1" + "+1" * 600, "9" * 300 + "x" + "9" * 300])
def test_hostile_macro_expressions_are_gerber_errors(expr):
    with pytest.raises(G.GerberError):
        macros.evaluate(expr, {})


def test_moderate_nesting_is_still_fine():
    assert macros.evaluate("(" * 20 + "$1" + ")" * 20 + "x--2", {1: 1.5}) == pytest.approx(3.0)


@pytest.mark.parametrize("snippet", [
    "%AMX*$a=1*1,1,1,0,0*%\n%ADD10X*%\n",                                     # a variable name that is not a number
    "%AMX*abc,1,1,0,0*%\n%ADD10X*%\n",                                        # a primitive code that is not a number
    "%AMX*4,1,10,0,0,1,0,1,1,0*%\n%ADD10X*%\n",                               # an outline that announces more vertices than it writes
    "%AMX*4,1,99999999999999999,0,0,0*%\n%ADD10X*%\n",                        # a hostile vertex count (must not build a huge index range)
    "%AMX*4,1,-1,0,0,0*%\n%ADD10X*%\n",
    "%AMX*5,1,0,0,0,1,0*%\n%ADD10X*%\n",                                      # polygon with 0 vertices (a division by zero when drawn)
    "%AMX*5,1,13,0,0,1,0*%\n%ADD10X*%\n",
    "%AMX*1,2,1,0,0*%\n%ADD10X*%\n",                                          # exposure 2
    "%ADD10P,1X0*%\n", "%ADD10P,1X2.5*%\n", "%ADD10C,-1*%\n", "%ADD10C," + "9" * 400 + "*%\n", "%ADD10C,1.2.3*%\n",
    "%ADD10C,1*%\nD10*\nX.Y0D03*\n", "%ADD10C,1*%\nD10*\nX1.2.3Y0D03*\n", "%ADD10C,1*%\nD10*\nX" + "9" * 400 + "Y0D03*\n",
    "X0Y0D03*\n",                                                             # a flash before any aperture
    "%ADD10C,1*%\n%SRX100000Y100000I1J1*%\nD10*\nX0Y0D03*\n%SR*%\n",         # a step and repeat that would make 1e10 copies
])
def test_malformed_and_hostile_files_raise_gerber_error(snippet):
    with pytest.raises(G.GerberError) as exc:
        G.parse_layer("%FSLAX46Y46*%\n%MOMM*%\n" + snippet + "M02*\n", "hostile.gbr")
    assert "hostile.gbr" in str(exc.value)


def test_operation_limit_and_step_and_repeat_limit(monkeypatch):
    monkeypatch.setattr(parser, "MAX_OPERATIONS", 50)
    many = gt.header("%ADD10C,0.1*%\n") + "".join(gt.flash(i * 0.2, 0) for i in range(60)) + gt.end()
    with pytest.raises(G.GerberError, match="operations"):
        G.parse_layer(many, "many.gbr")
    sr = gt.header("%ADD10C,0.1*%\n") + "%SRX8Y8I1J1*%\n" + gt.flash(0, 0) + "%SR*%\n" + gt.end()
    with pytest.raises(G.GerberError, match="step and repeat"):
        G.parse_layer(sr, "sr.gbr")


def test_a_flash_far_away_cannot_make_an_enormous_raster():
    text = "%FSLAX66Y66*%\n%MOMM*%\n%ADD10C,1*%\nD10*\nX0Y0D03*\nX999999999000000Y0D03*\nM02*\n"     # a flash at 1e9 mm
    layer = G.parse_layer(text, "far.gbr")
    with pytest.raises(G.GerberError, match="larger than the limit"):
        G.rasterize(layer, G.window_of(layer.bbox()), 0.1)
    with pytest.raises(G.GerberError):
        G.rasterize(layer, G.Window(0, 1, float("inf"), 1), 0.1)
    # The window of the board is fine: the far flash is simply outside it
    assert G.coverage_area_mm2(G.rasterize(layer, G.Window(-1, 1, 2, 2), 0.05), 0.05) == pytest.approx(math.pi / 4, rel=1e-2)


def test_fuzzed_files_fail_only_with_gerber_errors():
    # 120 deterministic mutations of small files built by the test (insertions of syntax characters and hostile tokens, deletions, duplications, truncation)
    seeds = [gt.header("%ADD10C,0.3*%\n%ADD11R,1X0.5*%\n%AMBOX*21,1,$1,$2,0,0,$3*%\n%ADD12BOX,1X2X30*%\n") + gt.line(0, 0, 3, 2) + gt.flash(1, 1, 11)
             + gt.flash(2, 1, 12) + "%SRX2Y2I3J3*%\n" + gt.region([(0, 0), (1, 0), (1, 1)]) + "%SR*%\nG75*\nD10*\nX0Y0D02*\nG03*\nX2000000Y0I1000000J0D01*\n" + gt.end(),
             "M48\nMETRIC,TZ,000.000\nT1C0.8\n%\nT1\nX1000Y2000\nR3X500\nG00X0Y0\nM15\nG01X5000Y0\nM16\nX1Y1G85X2Y2\nM30\n"]
    junk = ["%", "*", "X", "Y", "D", "G", "-", ".", "9" * 30, "(", "$1", "%SRX999Y999I1J1*%", "G36*", "%LPC*%", "\x00", "﻿", "\r", "G74*", ",", "x", "R99999999"]
    rng = random.Random(20261101)
    for k in range(120):
        src = seeds[k % 2]
        t = list(src)
        for _ in range(rng.randint(1, 10)):
            i = rng.randrange(len(t) + 1)
            r = rng.random()
            if r < 0.4:
                t.insert(i, rng.choice(junk))
            elif r < 0.7 and t:
                del t[min(i, len(t) - 1):min(i + rng.randint(1, 20), len(t))]
            else:
                j = rng.randrange(len(t) + 1)
                t[i:i] = t[j:j + rng.randint(1, 80)]
        text = "".join(t)
        try:
            if k % 2:
                G.read_drill(text, "f.drl")
            else:
                layer = G.parse_layer(text, "f.gbr")
                if layer.bbox():
                    b = layer.bbox()
                    G.rasterize(layer, G.Window(b[0], b[3], max(min(b[2] - b[0], 50), 0.1), max(min(b[3] - b[1], 50), 0.1)), 0.2, 2)
        except G.GerberError:
            pass


def test_drill_repeat_and_malformed_numbers_are_gerber_errors(monkeypatch):
    from pcbthermal.gerber import excellon
    monkeypatch.setattr(excellon, "MAX_HOLES", 100)
    with pytest.raises(G.GerberError, match="repeat"):
        G.read_drill("M48\nMETRIC\nT1C0.8\n%\nT1\nX1.0Y1.0\nR1000X0.1\nM30\n", "r.drl")
    with pytest.raises(G.GerberError):
        G.read_drill("M48\nMETRIC\nT1C0.8.8\n%\nT1\nX1.0Y1.0\nM30\n", "c.drl")
    d = G.read_drill("﻿M48\nMETRIC\nT1C0.8\n%\nT1\nX1.0Y2.0\nM30\n", "bom.drl")             # a BOM must not hide METRIC
    assert [(h.x, h.y, h.diameter) for h in d.holes] == [(1.0, 2.0, 0.8)]


# ----------------------------------------------------------------------------------------------------------------------------------
# Rasteriser: the sampling rule; outline; detector; archive
# ----------------------------------------------------------------------------------------------------------------------------------

def test_spacing_warning_matches_the_suggested_pixel():
    layer = G.parse_layer(gt.header("%ADD10C,0.03*%\n") + gt.line(0, 0, 5, 0) + gt.end(), "w.gbr")
    assert G.check_sample_spacing(layer, 4 * 0.03 / 2, 4) is None                         # the suggested pixel
    assert G.check_sample_spacing(layer, 4 * 0.03 / 1.5, 4) is not None                  # between one and two spacings: up to 98 % off, so a warning
    # At the suggested pixel the worst alignment of an axis-aligned band of the thinnest width misses at most half of it, and positions average out
    errs = []
    for off in np.linspace(0, 0.015, 7):
        t = gt.header("%ADD11R,10X0.03*%\n") + gt.flash(5, 1 + off, 11) + gt.end()
        cov = G.rasterize(G.parse_layer(t, "b.gbr"), G.Window(-0.5, 2, 11, 2), 0.06, 4)
        errs.append(G.coverage_area_mm2(cov, 0.06) / 0.3 - 1)
    assert max(abs(e) for e in errs) <= 0.5 + 1e-6 and abs(np.mean(errs)) < 0.2


def test_outline_with_segments_shorter_than_the_tolerance_still_closes():
    # A 10 x 10 square whose corners are written as runs of tiny segments (as some tools write splines): the chain must close, the area must be kept
    pts = [(0, 0), (10, 0), (10, 10), (0, 10)]
    text = gt.header("%ADD10C,0.1*%\n") + "D10*\nG01*\n" + f"X{gt.num(0)}Y{gt.num(0)}D02*\n"
    for k in range(4):
        x1, y1 = pts[(k + 1) % 4]
        x0, y0 = pts[k]
        # most of the side, then five pieces of 0.002 mm into the corner
        ex, ey = x1 - 0.01 * np.sign(x1 - x0), y1 - 0.01 * np.sign(y1 - y0)
        text += f"X{gt.num(ex)}Y{gt.num(ey)}D01*\n"
        for s in range(1, 6):
            text += f"X{gt.num(ex + (x1 - ex) * s / 5)}Y{gt.num(ey + (y1 - ey) * s / 5)}D01*\n"
    out = G.read_outline(text + gt.end(), "spline.gbr")
    assert len(out.polygons) == 1 and out.area_mm2 == pytest.approx(100.0, rel=1e-4)


@pytest.mark.parametrize("name,kind,side", [
    ("bottle-F_Cu.gbr", "copper", "top"), ("gasmask-F_Cu.gbr", "copper", "top"), ("edge-sensor-F_Cu.gbr", "copper", "top"),
    ("bot-controller-F_Mask.gbr", "soldermask", "top"), ("topology-B_Paste.gbr", "paste", "bottom"), ("board-In1_Cu.g2", "copper", "inner"),
    ("board-drl_map.gbr", "other", None), ("Gerber_DrillDrawingLayer.GDD", "other", None), ("Drill Drawing - Top.gbr", "other", None),
    ("board-F_Fab.gbr", "other", "top"), ("Bottom Layer.gbr", "copper", "bottom"), ("project_bottom.gtl", "copper", "top"),
])
def test_name_detection_pitfalls(name, kind, side):
    f = G.detect_function(name)
    assert (f.kind, f.side) == (kind, side)
    if name == "board-In1_Cu.g2":
        assert f.index == 1                                                     # KiCad's own suffix, not the Protel extension number


def _zip(entries):
    """!
    @brief A ZIP file in memory.
    @param entries List of (name, text).
    @return bytes.
    """
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for n, t in entries:
            z.writestr(n, t)
    return b.getvalue()


def test_archive_duplicate_names_are_refused_case_variants_are_listed():
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")                                         # zipfile warns about the duplicate name it is asked to write
        dup = _zip([("a.gbr", "x"), ("a.gbr", "y")])
        slash = _zip([("d/a.gbr", "x"), ("d\\a.gbr", "y")])
    for data in (dup, slash):
        with pytest.raises(G.UnsafeArchiveError, match="two members"):
            G.GerberArchive(data)
    names = [m.name for m in G.inspect_archive(_zip([("A.GTL", "x"), ("a.gtl", "y")]))]
    assert sorted(names) == ["A.GTL", "a.gtl"]                                  # nothing is extracted, so case variants cannot collide on disk


def test_damaged_archives_fail_only_with_unsafe_archive_errors():
    good = _zip([("a-F_Cu.gbr", "%FSLAX46Y46*%\n" * 200), ("b.drl", "M48\nMETRIC\n%\nT1C1\nX1Y1\nM30\n")])
    rng = random.Random(7)
    for _ in range(150):
        d = bytearray(good)
        for _ in range(rng.randint(1, 20)):
            d[rng.randrange(len(d))] = rng.randrange(256)
        if rng.random() < 0.3:
            d = d[:rng.randrange(len(d))]
        try:
            with G.GerberArchive(bytes(d)) as a:
                for n in a.names():
                    a.read_head(n)
                    a.read_text(n)
        except G.UnsafeArchiveError:
            pass


def test_tiles_give_the_same_raster_with_rectangle_draws_arcs_macros_and_negative_image(monkeypatch):
    body = (gt.header("%ADD10R,0.6X0.2*%\n%ADD11C,0.3*%\n%AMBOX*21,1,$1,$2,0,0,$3*%\n%ADD12BOX,1.5X0.7X30*%\n") + gt.line(0.5, 0.5, 19.5, 11.0, 10)
            + "D11*\nG75*\n" + f"X{gt.num(15)}Y{gt.num(6)}D02*\nG03*\nX{gt.num(15)}Y{gt.num(6)}I{gt.num(-4)}J0D01*\nG01*\n"
            + "".join(gt.flash(1 + 2.3 * i, 3 + 1.1 * (i % 5), 12) for i in range(8)) + "%LPC*%\n" + gt.region([(4, 3), (9, 3), (6, 9)]) + gt.end())
    for text in (body, body.replace("%MOMM*%\n", "%MOMM*%\n%IPNEG*%\n")):
        layer = G.parse_layer(text, "tiles.gbr")
        win = G.Window(0, 12, 20, 12)
        monkeypatch.setattr(raster, "TILE_SUBPIXELS", 2048)
        one = G.rasterize(layer, win, 0.05, 4)
        monkeypatch.setattr(raster, "TILE_SUBPIXELS", 28)                       # 7 x 7 pixel tiles
        assert np.array_equal(one, G.rasterize(layer, win, 0.05, 4))
