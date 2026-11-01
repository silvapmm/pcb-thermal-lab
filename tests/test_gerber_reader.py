#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_gerber_reader.py
@brief Tests of the Gerber reader and rasteriser of pcbthermal.gerber on synthetic files written by the test, with areas and positions known in closed form.
@details Covers the standard apertures, macros with arithmetic, rotated shapes, regions with holes, arcs (multi- and single-quadrant), step and repeat, clear polarity, units and
         zero formats, the X2 object attributes kept apart, the refusals (file and feature named), the pixel and sample-spacing rule, the tiled rasteriser against a single tile, and the
         property that the coverage sum equals the area within one pixel of perimeter.
"""

import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))

import gerber_text as gt  # noqa: E402
from pcbthermal import gerber as G  # noqa: E402
from pcbthermal.gerber import macros, raster  # noqa: E402

PIX = 0.05


def render(text, x0=-1.0, y0=1.0, w=None, h=None, pix=PIX, ss=4, name="t.gbr"):
    """!
    @brief Parse a text and rasterise it on a window.
    @param text Gerber text.
    @param x0 Left edge of the window (mm).
    @param y0 Top edge (mm).
    @param w Width (mm).
    @param h Height (mm).
    @param pix Pixel (mm).
    @param ss Supersampling.
    @param name File name.
    @return tuple (coverage array, window, layer).
    """
    layer = G.parse_layer(text, name)
    win = G.Window(x0, y0, w, h)
    return G.rasterize(layer, win, pix, ss), win, layer


def area_and_centroid(cov, win, pix=PIX):
    """!
    @brief Area and centroid of a coverage raster.
    @param cov Coverage (uint8).
    @param win Window.
    @param pix Pixel (mm).
    @return tuple (area mm2, cx, cy).
    """
    f = cov / 255.0
    area = f.sum() * pix * pix
    ii, jj = np.indices(f.shape)
    cx = win.x_left + ((jj + 0.5) * f).sum() / f.sum() * pix
    cy = win.y_top - ((ii + 0.5) * f).sum() / f.sum() * pix
    return area, cx, cy


def test_circle_flash_area_and_position():
    text = gt.header("%ADD10C,2.0*%\n") + gt.flash(3.0, 2.0) + gt.end()
    cov, win, _ = render(text, 0, 5, 6, 5)
    a, cx, cy = area_and_centroid(cov, win)
    assert a == pytest.approx(math.pi, rel=2e-3)
    assert (cx, cy) == (pytest.approx(3.0, abs=0.01), pytest.approx(2.0, abs=0.01))


def test_rectangle_obround_polygon_apertures():
    text = gt.header("%ADD10R,3.0X1.5*%\n%ADD11O,4.0X2.0*%\n%ADD12P,2.0X6*%\n") + gt.flash(2, 2, 10) + gt.flash(7, 2, 11) + gt.flash(12, 2, 12) + gt.end()
    cov, win, _ = render(text, 0, 4, 14, 4)
    left, mid, right = cov[:, :int(4.5 / PIX)], cov[:, int(4.5 / PIX):int(9.5 / PIX)], cov[:, int(9.5 / PIX):]
    assert left.sum() / 255 * PIX ** 2 == pytest.approx(4.5, rel=2e-3)
    assert mid.sum() / 255 * PIX ** 2 == pytest.approx(math.pi + 4.0, rel=2e-3)             # obround: disc of diameter 2 plus a 2 x 2 body
    assert right.sum() / 255 * PIX ** 2 == pytest.approx(1.5 * math.sqrt(3) * 1.0 ** 2, rel=3e-3)   # regular hexagon, circumradius 1


def test_aperture_with_hole():
    text = gt.header("%ADD10C,2.0X1.0*%\n%ADD11R,3.0X2.0X1.0*%\n") + gt.flash(2, 2, 10) + gt.flash(6, 2, 11) + gt.end()
    cov, win, _ = render(text, 0, 4, 8, 4)
    assert cov.sum() / 255 * PIX ** 2 == pytest.approx(math.pi * (1 - 0.25) + (6.0 - math.pi * 0.25), rel=3e-3)


def test_line_with_round_aperture_is_a_capsule():
    text = gt.header("%ADD10C,0.4*%\n") + gt.line(1, 1, 11, 1) + gt.end()
    cov, win, _ = render(text, 0, 2, 12, 2)
    assert cov.sum() / 255 * PIX ** 2 == pytest.approx(10 * 0.4 + math.pi * 0.2 ** 2, rel=5e-3)


def test_line_with_rectangular_aperture_is_the_hull():
    text = gt.header("%ADD10R,0.6X0.2*%\n") + gt.line(1, 1, 5, 1) + gt.end()
    cov, win, _ = render(text, 0, 2, 7, 2)
    assert cov.sum() / 255 * PIX ** 2 == pytest.approx(4.6 * 0.2, rel=5e-3)


def test_region_with_a_clear_cutout():
    text = gt.header() + "%LPD*%\n" + gt.region([(1, 1), (11, 1), (11, 11), (1, 11)]) + "%LPC*%\n" + gt.region([(4, 4), (8, 4), (8, 8), (4, 8)]) + gt.end()
    cov, win, _ = render(text, 0, 12, 12, 12)
    assert cov.sum() / 255 * PIX ** 2 == pytest.approx(100 - 16, rel=1e-3)


def test_polarity_order_matters():
    big = gt.region([(1, 1), (5, 1), (5, 5), (1, 5)])
    small = gt.region([(2, 2), (3, 2), (3, 3), (2, 3)])
    dark_then_clear = gt.header() + "%LPD*%\n" + big + "%LPC*%\n" + small + gt.end()
    clear_then_dark = gt.header() + "%LPC*%\n" + small + "%LPD*%\n" + big + gt.end()
    a = render(dark_then_clear, 0, 6, 6, 6)[0].sum() / 255 * PIX ** 2
    b = render(clear_then_dark, 0, 6, 6, 6)[0].sum() / 255 * PIX ** 2
    assert a == pytest.approx(15.0, rel=2e-3) and b == pytest.approx(16.0, rel=2e-3)


def test_full_circle_arc_multi_quadrant():
    # A ring: a circle of radius 5 drawn with G75 and a 0.2 mm round aperture
    text = (gt.header("%ADD10C,0.2*%\n") + "G75*\nD10*\nG01*\n" + f"X{gt.num(11)}Y{gt.num(6)}D02*\nG03*\nX{gt.num(11)}Y{gt.num(6)}I{gt.num(-5)}J{gt.num(0)}D01*\n" + gt.end())
    cov, win, _ = render(text, 0, 12, 12, 12)
    assert cov.sum() / 255 * PIX ** 2 == pytest.approx(2 * math.pi * 5 * 0.2, rel=5e-3)
    a, cx, cy = area_and_centroid(cov, win)
    assert (cx, cy) == (pytest.approx(6.0, abs=0.02), pytest.approx(6.0, abs=0.02))


def test_quarter_arcs_both_directions_and_single_quadrant():
    # Counter-clockwise quarter from (5, 0) to (0, 5) around the origin, then the same quarter clockwise, then in G74 with unsigned offsets
    ccw = gt.header("%ADD10C,0.2*%\n") + "G75*\nD10*\n" + f"X{gt.num(6)}Y{gt.num(1)}D02*\nG03*\nX{gt.num(1)}Y{gt.num(6)}I{gt.num(-5)}J{gt.num(0)}D01*\n" + gt.end()
    cw = gt.header("%ADD10C,0.2*%\n") + "G75*\nD10*\n" + f"X{gt.num(1)}Y{gt.num(6)}D02*\nG02*\nX{gt.num(6)}Y{gt.num(1)}I{gt.num(0)}J{gt.num(-5)}D01*\n" + gt.end()
    single = gt.header("%ADD10C,0.2*%\n") + "G74*\nD10*\n" + f"X{gt.num(6)}Y{gt.num(1)}D02*\nG03*\nX{gt.num(1)}Y{gt.num(6)}I{gt.num(5)}J{gt.num(0)}D01*\n" + gt.end()
    expected = (math.pi / 2) * 5 * 0.2 + math.pi * 0.1 ** 2
    for text in (ccw, cw, single):
        cov, win, _ = render(text, 0, 8, 8, 8)
        assert cov.sum() / 255 * PIX ** 2 == pytest.approx(expected, rel=1.5e-2)
        a, cx, cy = area_and_centroid(cov, win)
        # The centroid of a quarter arc of radius 5 around (1, 1) is at 2 r / pi from the centre, along the diagonal
        assert cx == pytest.approx(1 + 5 * 2 * math.sqrt(2) / math.pi / math.sqrt(2) * 1.0, abs=0.03)
        assert cx == pytest.approx(cy, abs=0.02)


def test_step_and_repeat_grid():
    text = gt.header("%ADD10R,1.0X1.0*%\n") + "%SRX3Y2I5.0J4.0*%\n" + gt.flash(1, 1) + "%SR*%\n" + gt.end()
    layer = G.parse_layer(text, "sr.gbr")
    assert len(layer.ops) == 6
    xs = sorted({round(op[2][1], 6) for op in layer.ops})
    ys = sorted({round(op[2][2], 6) for op in layer.ops})
    assert xs == [1.0, 6.0, 11.0] and ys == [1.0, 5.0]
    cov, win, _ = render(text, 0, 7, 13, 7)
    assert cov.sum() / 255 * PIX ** 2 == pytest.approx(6.0, rel=1e-3)


def test_step_and_repeat_closed_by_next_block_and_end_of_file():
    text = gt.header("%ADD10R,1.0X1.0*%\n") + "%SRX2Y1I4.0J0*%\n" + gt.flash(1, 1) + "%SRX1Y1I0J0*%\n" + gt.flash(1, 4) + gt.end()
    layer = G.parse_layer(text, "sr2.gbr")
    assert len(layer.ops) == 3                                          # two copies of the first block, one flash outside


def test_macro_with_arithmetic_and_rotation():
    # A centre-line rectangle of width 2 x $1 and height $2 + 1, rotated 30 degrees about its centre: the area does not change
    text = gt.header("%AMBOX*21,1,$1x2,$2+1,0,0,30*%\n%ADD10BOX,2.0X1.0*%\n") + gt.flash(4, 4) + gt.end()
    cov, win, _ = render(text, 0, 8, 8, 8)
    a, cx, cy = area_and_centroid(cov, win)
    assert a == pytest.approx(4.0 * 2.0, rel=3e-3)
    assert (cx, cy) == (pytest.approx(4.0, abs=0.01), pytest.approx(4.0, abs=0.01))
    # The rotated rectangle has its long axis 30 degrees from x: the second moment shows it
    f = cov / 255.0
    ii, jj = np.indices(f.shape)
    x = win.x_left + (jj + 0.5) * PIX - cx
    y = win.y_top - (ii + 0.5) * PIX - cy
    ixx, iyy, ixy = (f * x * x).sum(), (f * y * y).sum(), (f * x * y).sum()
    angle = 0.5 * math.degrees(math.atan2(2 * ixy, ixx - iyy))
    assert angle == pytest.approx(30.0, abs=0.6)


def test_macro_variables_defined_in_the_macro_and_clear_primitive():
    # Outer disc diameter $1, an inner hole of diameter $1/2 made by exposure 0: area = pi (r^2 - (r/2)^2)
    text = gt.header("%AMRING*1,1,$1,0,0*\n1,0,$2,0,0*\n$3=$1/2*%\n%ADD10RING,4.0X2.0*%\n") + gt.flash(3, 3) + gt.end()
    cov, win, _ = render(text, 0, 6, 6, 6)
    assert cov.sum() / 255 * PIX ** 2 == pytest.approx(math.pi * (4 - 1), rel=3e-3)


def test_macro_vector_line_outline_polygon_and_thermal_primitives():
    prims = "20,1,0.5,0,0,3,0,0*\n"                                        # vector line of width 0.5 and length 3
    text = gt.header(f"%AML*{prims}%\n%ADD10L*%\n") + gt.flash(1, 1) + gt.end()
    cov, win, _ = render(text, 0, 3, 6, 3)
    assert cov.sum() / 255 * PIX ** 2 == pytest.approx(3 * 0.5, rel=3e-3)
    tri = "%AMT*4,1,3,0,0,2,0,0,2,0,0,0*%\n%ADD11T*%\n"                    # right triangle with legs 2: area 2
    cov, win, _ = render(gt.header(tri) + gt.flash(1, 1, 11) + gt.end(), 0, 4, 5, 4)
    assert cov.sum() / 255 * PIX ** 2 == pytest.approx(2.0, rel=5e-3)
    pol = "%AMP6*5,1,6,0,0,2,0*%\n%ADD12P6*%\n"                            # hexagon, circumscribed diameter 2
    cov, win, _ = render(gt.header(pol) + gt.flash(2, 2, 12) + gt.end(), 0, 4, 4, 4)
    assert cov.sum() / 255 * PIX ** 2 == pytest.approx(1.5 * math.sqrt(3), rel=4e-3)
    th = "%AMTH*7,0,0,4,2,0.5,0*%\n%ADD13TH*%\n"                           # thermal: ring between d 2 and 4 with two gaps of 0.5
    cov, win, _ = render(gt.header(th) + gt.flash(3, 3, 13) + gt.end(), 0, 6, 6, 6)
    ring = math.pi * (4 - 1)
    assert cov.sum() / 255 * PIX ** 2 < ring and cov.sum() / 255 * PIX ** 2 > ring - 4 * 0.5 * 1.0 - 0.3


def test_macro_expression_is_parsed_not_evaluated():
    assert macros.evaluate("$1x2+$2/4-(1+1)", {1: 3.0, 2: 8.0}) == pytest.approx(6.0)
    assert macros.evaluate("-$1+--2", {1: 5.0}) == pytest.approx(-3.0)
    for bad in ("__import__('os').system('x')", "9**9**9**9", "1;2", "(1+2"):
        with pytest.raises(G.GerberError):
            macros.evaluate(bad, {})


def test_units_inch_and_formats():
    inch = "%FSLAX24Y24*%\n%MOIN*%\n%ADD10C,0.1*%\nD10*\nX10000Y20000D03*\nM02*\n"                  # 1 inch, 2 inch; circle 0.1 inch
    layer = G.parse_layer(inch, "in.gbr")
    kind, dark, (ap, x, y) = layer.ops[0]
    assert (x, y) == (pytest.approx(25.4), pytest.approx(50.8)) and ap.p[0] == pytest.approx(2.54)
    trailing = "%FSTAX25Y25*%\n%MOMM*%\n%ADD10C,1*%\nD10*\nX1234Y5D03*\nM02*\n"                      # trailing zeros omitted: 12.34000 and 50.00000
    (_, _, (_, x, y)) = G.parse_layer(trailing, "tz.gbr").ops[0]
    assert (x, y) == (pytest.approx(12.34), pytest.approx(50.0))
    g70 = "%FSLAX23Y23*%\nG70*\n%ADD10C,0.1*%\nD10*\nX1000Y1000D03*\nM02*\n"
    (_, _, (ap, x, y)) = G.parse_layer(g70, "g70.gbr").ops[0]
    assert x == pytest.approx(25.4) and ap.p[0] == pytest.approx(2.54)


def test_modal_coordinates_without_d_code_and_decimal_coordinates():
    text = gt.header("%ADD10C,1*%\n") + "D10*\nX2000000Y2000000D02*\nX4000000D01*\nY4000000*\nM02*\n"
    layer = G.parse_layer(text, "m.gbr")
    strokes = [op for op in layer.ops if op[0] == "stroke"]
    assert len(strokes) == 2 and strokes[1][2][3:] == (pytest.approx(4.0), pytest.approx(4.0))
    dec = "%FSLAX24Y24*%\n%MOMM*%\n%ADD10C,1*%\nD10*\nX1.5Y2.5D03*\nM02*\n"
    (_, _, (_, x, y)) = G.parse_layer(dec, "d.gbr").ops[0]
    assert (x, y) == (1.5, 2.5)


def test_image_polarity_negative_inverts_inside_the_window():
    text = gt.header("%ADD10R,2.0X2.0*%\n%IPNEG*%\n") + gt.flash(2, 2) + gt.end()
    cov, win, _ = render(text, 0, 4, 4, 4)
    assert cov.sum() / 255 * PIX ** 2 == pytest.approx(16 - 4, rel=1e-3)


def test_x2_attributes_are_kept_apart():
    text = (gt.header("%TF.FileFunction,Copper,L1,Top*%\n%TF.FilePolarity,Positive*%\n%TA.AperFunction,SMDPad,CuDef*%\n%ADD10R,1.0X1.0*%\n%TA.AperFunction,Conductor*%\n%ADD11C,0.2*%\n%TD*%\n")
            + "%TO.N,GND*%\n%TO.C,U1*%\n%TO.P,U1,3*%\n" + gt.flash(1, 1, 10) + "%TO.N,VCC*%\n%TO.C,R5*%\n%TO.P,R5,1*%\n" + gt.flash(3, 1, 10)
            + "%TD.P*%\n%TD.C*%\n" + gt.flash(5, 1, 10) + "%TD*%\n" + gt.flash(7, 1, 10) + gt.end())
    layer = G.parse_layer(text, "x2.gbr")
    assert layer.file_function == ["Copper", "L1", "Top"] and layer.attributes["FilePolarity"] == ["Positive"]
    assert layer.apertures[10].func == "SMDPad,CuDef" and layer.apertures[11].func == "Conductor"
    f = layer.flashes()
    assert [(p.net, p.ref, p.pin) for p in f] == [("GND", "U1", ("U1", "3")), ("VCC", "R5", ("R5", "1")), ("VCC", None, None), (None, None, None)]
    assert layer.net_names() == ["GND", "VCC"] and layer.references() == ["U1", "R5"]


def test_attribute_comment_form_is_read():
    text = gt.header() + "G04 #@! TF.FileFunction,Copper,L2,Inr*\n%ADD10C,1*%\n" + gt.flash(1, 1) + gt.end()
    assert G.parse_layer(text, "c.gbr").file_function == ["Copper", "L2", "Inr"]


def test_net_filter_draws_only_the_wanted_net():
    text = gt.header("%ADD10R,1.0X1.0*%\n") + "%TO.N,A*%\n" + gt.flash(1, 1) + "%TO.N,B*%\n" + gt.flash(3, 1) + gt.end()
    layer = G.parse_layer(text, "n.gbr")
    win = G.Window(0, 2, 4, 2)
    only_a = G.rasterize(layer, win, PIX, 4, nets=["A"])
    assert only_a.sum() / 255 * PIX ** 2 == pytest.approx(1.0, rel=1e-3) and only_a[:, int(2 / PIX):].sum() == 0


@pytest.mark.parametrize("snippet,feature", [
    ("%ABD100*%\n%ADD10C,1*%\n%AB*%\n", "AB"),
    ("%LMX*%\n", "LM"),
    ("%LR90*%\n", "LR"),
    ("%LS2*%\n", "LS"),
    ("%AMMOI*6,0,0,2,0.1,0.1,2,0.1,2,0*%\n%ADD10MOI*%\nD10*\nX0Y0D03*\n", "moire"),
    ("%ADD10Rect-W1-H2,1*%\n", "non-standard"),
    ("G91*\n", "G91"),
    ("%OFA1.0B2.0*%\n", "image offset"),
    ("%MIA1B0*%\n", "image mirror"),
    ("%SFA2.0B2.0*%\n", "image scale"),
    ("%IR90*%\n", "image rotation"),
    ("%ASAYBX*%\n", "axis select"),
])
def test_unsupported_features_are_refused_with_file_and_feature(snippet, feature):
    text = "%FSLAX46Y46*%\n%MOMM*%\n" + snippet + "M02*\n"
    with pytest.raises(G.UnsupportedFeatureError) as exc:
        G.parse_layer(text, "board-F_Cu.gbr")
    assert exc.value.file == "board-F_Cu.gbr" and feature in exc.value.feature
    assert "board-F_Cu.gbr" in str(exc.value)
    assert isinstance(exc.value, NotImplementedError) and isinstance(exc.value, G.GerberError)


def test_malformed_files_raise_gerber_error():
    with pytest.raises(G.GerberError):
        G.parse_layer("%FSLAX46Y46*%\nD11*\nX1Y1D03*\n", "x.gbr")                  # aperture used before definition
    with pytest.raises(G.GerberError):
        G.parse_layer("%FSXYZ*%\n", "x.gbr")
    with pytest.raises(G.GerberError):
        G.parse_layer("%FSLAX46Y46*%\n%ADD10C*%\n", "x.gbr")


def test_thin_line_is_lost_at_a_coarse_sample_spacing_and_the_check_says_so():
    # The Ucamco "two square boxes" case: a 0.01 mm line, perimeter 40 mm in total
    sq = gt.line(1, 1, 11, 1) + gt.line(11, 1, 11, 11) + gt.line(11, 11, 1, 11) + gt.line(1, 11, 1, 1)
    text = gt.header("%ADD10C,0.01*%\n") + sq + gt.end()
    layer = G.parse_layer(text, "thin.gbr")
    assert layer.thinnest_feature_mm() == pytest.approx(0.01)
    warn = G.check_sample_spacing(layer, 0.05, 2)
    assert warn and "thin.gbr" in warn and "0.01" in warn
    assert G.check_sample_spacing(layer, 0.05, 4) is not None
    pix = G.suggest_pixel_mm(layer.thinnest_feature_mm(), 4)
    assert pix == pytest.approx(0.02) and G.check_sample_spacing(layer, pix, 4) is None
    win = G.Window(0, 12, 12, 12)
    exact = 40 * 0.01 + math.pi * 0.005 ** 2
    cov = G.rasterize(layer, win, pix, 4)
    assert G.coverage_area_mm2(cov, pix) == pytest.approx(exact, rel=0.25)


def test_suggest_pixel_and_check_for_a_layer_without_widths():
    assert G.suggest_pixel_mm(None) is None
    layer = G.parse_layer(gt.header() + gt.region([(0, 0), (1, 0), (1, 1)]) + gt.end(), "r.gbr")
    assert layer.thinnest_feature_mm() is None and G.check_sample_spacing(layer, 0.1) is None


def test_tiles_give_the_same_raster_as_one_tile(monkeypatch):
    text = (gt.header("%ADD10C,0.3*%\n%ADD11R,2.0X1.0*%\n") + gt.line(0.5, 0.5, 19.5, 11.5) + gt.line(0.5, 11.5, 19.5, 0.5)
            + gt.flash(10, 6, 11) + gt.region([(2, 2), (8, 2), (5, 9)]) + "%LPC*%\n" + gt.region([(4, 3), (6, 3), (5, 5)]) + gt.end())
    layer = G.parse_layer(text, "tiles.gbr")
    win = G.Window(0, 12, 20, 12)
    one = G.rasterize(layer, win, 0.1, 4)
    monkeypatch.setattr(raster, "TILE_SUBPIXELS", 40)                            # 10 x 10 pixel tiles: every shape crosses several
    many = G.rasterize(layer, win, 0.1, 4)
    assert np.array_equal(one, many)


def test_coverage_sum_equals_the_area_within_one_pixel_of_perimeter():
    # Random convex quadrilaterals: exact area by the shoelace formula, the coverage sum must be within perimeter x pixel
    rng = np.random.default_rng(7)
    pix = 0.1
    for _ in range(12):
        c = rng.uniform(4, 8, 2)
        ang = np.sort(rng.uniform(0, 2 * np.pi, 5))
        rad = rng.uniform(1.0, 3.0, 5)
        pts = np.column_stack([c[0] + rad * np.cos(ang), c[1] + rad * np.sin(ang)])
        x, y = pts[:, 0], pts[:, 1]
        exact = 0.5 * abs(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))
        perimeter = np.hypot(np.diff(np.r_[x, x[0]]), np.diff(np.r_[y, y[0]])).sum()
        if exact < 0.5:
            continue
        text = gt.header() + gt.region(list(map(tuple, pts))) + gt.end()
        layer = G.parse_layer(text, "q.gbr")
        for ss in (1, 4):
            cov = G.rasterize(layer, G.Window(0, 12, 12, 12), pix, ss)
            assert abs(G.coverage_area_mm2(cov, pix) - exact) <= perimeter * pix


def test_coverage_is_one_byte_and_full_pixels_are_255():
    text = gt.header("%ADD10R,2.0X2.0*%\n") + gt.flash(2, 2) + gt.end()
    cov, win, _ = render(text, 0, 4, 4, 4, pix=0.1)
    assert cov.dtype == np.uint8 and cov.max() == 255 and cov[20, 20] == 255 and cov[0, 0] == 0


def test_empty_layer_and_window_outside_the_copper():
    layer = G.parse_layer(gt.header() + gt.end(), "e.gbr")
    assert layer.bbox() is None
    assert G.rasterize(layer, G.Window(0, 1, 1, 1), 0.1).sum() == 0
    layer2 = G.parse_layer(gt.header("%ADD10C,1*%\n") + gt.flash(50, 50) + gt.end(), "f.gbr")
    assert G.rasterize(layer2, G.Window(0, 1, 1, 1), 0.1).sum() == 0
    with pytest.raises(ValueError):
        G.window_of(None)


def test_memory_estimate_grows_with_pixels_and_layers_and_holds_one_byte_per_pixel():
    win = G.Window(0, 100, 100, 100)
    a = G.estimate_raster_bytes(win, 0.1, 1)
    b = G.estimate_raster_bytes(win, 0.1, 4)
    c = G.estimate_raster_bytes(win, 0.05, 4)
    assert a.pixels_per_layer == 1000 * 1000 and a.held_bytes == 1_000_000 and b.held_bytes == 4_000_000
    assert c.held_bytes == 4 * b.held_bytes and c.peak_bytes > b.peak_bytes
    assert b.working_bytes == c.working_bytes                                   # the tile makes the working memory independent of the board
    with_ops = G.estimate_raster_bytes(win, 0.1, 1, n_ops=100000)
    assert with_ops.peak_bytes - a.peak_bytes == 100000 * raster.BYTES_PER_OP


def test_working_memory_of_the_rasteriser_stays_under_its_estimate():
    import tracemalloc
    # A 100 x 80 mm board with a long diagonal, a big pour with a hole and many pads: the traced peak (numpy allocations included) must stay under the working estimate
    body = gt.line(1, 1, 99, 79) + gt.region([(5, 5), (95, 5), (95, 75), (5, 75)]) + "%LPC*%\n" + gt.region([(20, 20), (60, 20), (60, 50), (20, 50)]) + "%LPD*%\n"
    pads = "".join(gt.flash(5 + 3 * i, 3 + 5 * j, 11) for i in range(25) for j in range(14))
    layer = G.parse_layer(gt.header("%ADD10C,0.3*%\n%ADD11R,1.0X1.0*%\n") + body + pads + gt.end(), "mem.gbr")
    win = G.Window(0, 80, 100, 80)
    est = G.estimate_raster_bytes(win, 0.1, 1, 4)
    tracemalloc.start()
    cov = G.rasterize(layer, win, 0.1, 4)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert cov.sum() > 0 and peak < est.working_bytes + est.held_bytes
