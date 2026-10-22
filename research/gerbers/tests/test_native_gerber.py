"""!
@file test_native_gerber.py
@brief The NumPy-only Gerber and Excellon reader on small files written by the tests: every area is compared with its analytic value.
"""

import math

import numpy as np
import pytest

import native_gerber as ng

HEAD = "%FSLAX36Y36*%\n%MOMM*%\n"


def mm(v):
    """!
    @brief A length in mm as the integer string of a 3.6 coordinate format.
    @param v Length (mm).
    @return String of digits.
    """
    return str(int(round(v * 1e6)))


def xy(x, y, d):
    """!
    @brief A coordinate block with a D code.
    @param x X (mm).
    @param y Y (mm).
    @param d D code (1 draw, 2 move, 3 flash).
    @return String.
    """
    return f"X{mm(x)}Y{mm(y)}D0{d}*\n"


def area(text, tmp_path, box=(0.0, 30.0, 30.0, 30.0), pix=0.02):
    """!
    @brief Draw a Gerber text on a window and return the copper area.
    @param text File content.
    @param tmp_path pytest temp dir.
    @param box Window (x_left, y_top, width, height) in mm.
    @param pix Pixel size (mm).
    @return Area in mm2.
    """
    p = tmp_path / "t.gbr"
    p.write_text(text)
    m = ng.render(p, box[0], box[1], box[2], box[3], pix)
    return float(m.sum() * pix * pix)


def test_standard_apertures(tmp_path):
    """!@brief Circle, rectangle, obround and hexagon flashes give their analytic areas. @param tmp_path pytest temp dir. @return None."""
    t = HEAD + "%ADD10C,2.0*%\n%ADD11R,2.0X1.0*%\n%ADD12O,3.0X1.0*%\n%ADD13P,2.0X6*%\nD10*\n" + xy(5, 25, 3) + "D11*\n" + xy(10, 25, 3) + "D12*\n" + xy(15, 25, 3) + "D13*\n" + xy(20, 25, 3) + "M02*\n"
    expected = math.pi + 2.0 + (1.0 * 2.0 + math.pi * 0.25) + 3 * math.sqrt(3) / 2
    assert area(t, tmp_path) == pytest.approx(expected, rel=0.01)


def test_aperture_hole(tmp_path):
    """!@brief A circular aperture with a hole is a ring. @param tmp_path pytest temp dir. @return None."""
    t = HEAD + "%ADD10C,4.0X2.0*%\nD10*\n" + xy(10, 20, 3) + "M02*\n"
    assert area(t, tmp_path) == pytest.approx(math.pi * (4 - 1), rel=0.01)


def test_draws_with_round_and_rectangular_apertures(tmp_path):
    """!@brief A stroke with a round aperture is a capsule; with a rectangular one it is the swept rectangle. @param tmp_path pytest temp dir. @return None."""
    t = HEAD + "%ADD10C,0.2*%\n%ADD11R,0.4X0.2*%\nG01*\nD10*\n" + xy(1, 28, 2) + xy(9, 28, 1) + "D11*\n" + xy(1, 25, 2) + xy(9, 25, 1) + "M02*\n"
    assert area(t, tmp_path) == pytest.approx(8 * 0.2 + math.pi * 0.01 + 8.4 * 0.2, rel=0.02)


def test_arc_in_multi_and_single_quadrant_mode(tmp_path):
    """!@brief A quarter circle drawn counter-clockwise (G75 with signed offsets and G74 with unsigned ones) has the length of the arc times the width. @param tmp_path pytest temp dir. @return None."""
    r, w = 5.0, 0.2
    expected = (math.pi * r / 2) * w + math.pi * (w / 2) ** 2
    for mode, i, j in (("G75", -r, 0.0), ("G74", r, 0.0)):
        t = HEAD + "%ADD10C,0.2*%\nG01*\nD10*\n" + mode + "*\n" + xy(15 + r, 5, 2) + f"G03*\nX{mm(15)}Y{mm(5 + r)}I{mm(i)}J{mm(j)}D01*\nM02*\n"
        assert area(t, tmp_path) == pytest.approx(expected, rel=0.02)


def test_region_and_region_with_an_arc(tmp_path):
    """!@brief G36 regions: a square and a half disc. @param tmp_path pytest temp dir. @return None."""
    sq = HEAD + "G36*\n" + xy(1, 1, 2) + xy(3, 1, 1) + xy(3, 3, 1) + xy(1, 3, 1) + xy(1, 1, 1) + "G37*\nM02*\n"
    assert area(sq, tmp_path) == pytest.approx(4.0, rel=0.01)
    half = HEAD + "G75*\nG36*\n" + xy(5, 10, 2) + xy(15, 10, 1) + "G03*\n" + f"X{mm(5)}Y{mm(10)}I{mm(-5)}J{mm(0)}D01*\nG37*\nM02*\n"
    assert area(half, tmp_path) == pytest.approx(math.pi * 25 / 2, rel=0.01)


def test_clear_polarity_and_negative_image(tmp_path):
    """!@brief A clear flash removes copper from a dark region; IPNEG inverts the image. @param tmp_path pytest temp dir. @return None."""
    t = HEAD + "%ADD10C,2.0*%\nG36*\n" + xy(5, 5, 2) + xy(9, 5, 1) + xy(9, 9, 1) + xy(5, 9, 1) + xy(5, 5, 1) + "G37*\n%LPC*%\nD10*\n" + xy(7, 7, 3) + "M02*\n"
    assert area(t, tmp_path, (0.0, 30.0, 30.0, 30.0)) == pytest.approx(16 - math.pi, rel=0.01)
    neg = "%IPNEG*%\n" + HEAD + "G36*\n" + xy(5, 5, 2) + xy(9, 5, 1) + xy(9, 9, 1) + xy(5, 9, 1) + xy(5, 5, 1) + "G37*\nM02*\n"
    assert area(neg, tmp_path, (0.0, 30.0, 30.0, 30.0)) == pytest.approx(900 - 16, rel=0.001)


def test_macros_with_variables_and_clear_exposure(tmp_path):
    """!@brief A centre-line macro with parameters, and a ring macro (a clear circle inside a dark one). @param tmp_path pytest temp dir. @return None."""
    t = (HEAD + "%AMBOX*21,1,$1,$2,0,0,0*%\n%AMRING*1,1,$1,0,0*1,0,$2,0,0*%\n%ADD10BOX,3.0X2.0*%\n%ADD11RING,4.0X2.0*%\n"
         "D10*\n" + xy(5, 25, 3) + "D11*\n" + xy(15, 25, 3) + "M02*\n")
    assert area(t, tmp_path) == pytest.approx(6.0 + math.pi * (4 - 1), rel=0.01)


def test_macro_arithmetic_and_rotation(tmp_path):
    """!@brief Variables defined with expressions, and a rotated rectangle keep their area. @param tmp_path pytest temp dir. @return None."""
    t = HEAD + "%AMTWO*$3=$1x2*21,1,$3,$2,0,0,30*%\n%ADD10TWO,1.5X1.0*%\nD10*\n" + xy(10, 15, 3) + "M02*\n"
    assert area(t, tmp_path) == pytest.approx(3.0 * 1.0, rel=0.02)


def test_trailing_zero_format_inches_and_step_and_repeat(tmp_path):
    """!@brief Trailing-zero omission, inch units and a 3 x 2 step and repeat of a circle. @param tmp_path pytest temp dir. @return None."""
    t = "%FSTAX24Y24*%\n%MOMM*%\n%ADD10C,1.0*%\nD10*\nX05Y05D03*\nM02*\n"            # "05" with trailing zeros omitted is 05.0000 = 5 mm
    p = tmp_path / "a.gbr"
    p.write_text(t)
    m = ng.render(p, 0.0, 10.0, 10.0, 10.0, 0.02)
    assert m[int((10 - 5) / 0.02), int(5 / 0.02)]
    inch = "%FSLAX24Y24*%\n%MOIN*%\n%ADD10C,0.1*%\nD10*\nX00000Y00000D03*\nM02*\n"
    p.write_text(inch)
    assert float(ng.render(p, -5.0, 5.0, 10.0, 10.0, 0.02).sum() * 0.02 ** 2) == pytest.approx(math.pi * (0.1 * 25.4 / 2) ** 2, rel=0.03)
    sr = HEAD + "%ADD10C,1.0*%\n%SRX3Y2I4.0J3.0*%\nD10*\n" + xy(2, 20, 3) + "%SR*%\nM02*\n"
    assert area(sr, tmp_path) == pytest.approx(6 * math.pi * 0.25, rel=0.01)


def test_unsupported_features_are_reported(tmp_path):
    """!@brief Aperture blocks, the moire primitive and an image mirror raise NotImplementedError instead of giving a wrong picture. @param tmp_path pytest temp dir. @return None."""
    for body in ("%ABD10*%\n", "%AMM*6,0,0,5,0.1,0.1,3,0.1,6.0,0*%\n%ADD10M*%\n", "%MIA1B0*%\n"):
        with pytest.raises(NotImplementedError):
            ng.Layer(HEAD + body + "M02*\n")


def test_excellon_metric_inch_comments_repeat_and_slots(tmp_path):
    """!@brief Excellon: decimal metric, inch with a comment table of sizes in mils, the R repeat command and a routed slot. @param tmp_path pytest temp dir. @return None."""
    metric = tmp_path / "m.drl"
    metric.write_text("M48\nMETRIC\nT1C0.800\nT2C1.000\n%\nG90\nT1\nX10.0Y20.0\nX11.5Y20.0\nT2\nX30.0Y40.0\nT0\nM30\n")
    h = ng.read_drill(metric)
    assert [(round(x, 3), round(y, 3), round(d, 3)) for x, y, d, _ in h] == [(10.0, 20.0, 0.8), (11.5, 20.0, 0.8), (30.0, 40.0, 1.0)]
    inch = tmp_path / "i.drl"
    inch.write_text(";T01 Holesize 1. = 12.000000 Tolerance = +0.000000/-0.000000 PLATED MILS Quantity = 3\n;T02 Holesize 2. = 125.000000 NON_PLATED MILS Quantity = 1\n"
                    "%\nG90\nT01\nX010000Y020000\nR02X-001000\nT02\nX030000Y040000\nM30\n")
    hi = ng.read_drill(inch)
    assert len(hi) == 4 and hi[0][2] == pytest.approx(12 * 0.0254) and hi[0][3] is True and hi[3][3] is False
    assert hi[0][0] == pytest.approx(1.0 * 25.4) and hi[2][0] == pytest.approx((1.0 - 0.2) * 25.4)         # 01.0000 in, then two repeats of -0.1000 in
    slot = tmp_path / "s.drl"
    slot.write_text("M48\nMETRIC\nT1C0.6\n%\nT1\nG00X10.0Y10.0\nM15\nG01X12.0Y10.0\nM16\nT0\nM30\n")
    hs = ng.read_drill(slot)
    assert len(hs) == 1 and hs[0][0] == pytest.approx(11.0) and hs[0][2] == pytest.approx(0.6)


def test_x2_attributes_and_the_layer_guess(tmp_path):
    """!@brief The X2 file function is read, and the file name is the fallback; silk, mask and unknown files give no copper role. @param tmp_path pytest temp dir. @return None."""
    x2 = tmp_path / "board-F_Cu.gbr"
    x2.write_text("%TF.FileFunction,Copper,L1,Top*%\n%TF.FilePolarity,Positive*%\n" + HEAD + "M02*\n")
    assert ng.Layer(x2.read_text()).attributes["FileFunction"] == ["Copper", "L1", "Top"]
    assert ng.classify(x2) == ("copper", "top", 1)
    inner = tmp_path / "a.gbr"
    inner.write_text("%TF.FileFunction,Copper,L3,Inr*%\n" + HEAD + "M02*\n")
    assert ng.classify(inner) == ("copper", "inr", 3)
    for name, expected in (("proj-F_Cu.gbr", ("copper", "top", None)), ("proj-B_Cu.gbr", ("copper", "bottom", None)), ("Gerber_TopLayer.GTL", ("copper", "top", None)),
                           ("x.GBL", ("copper", "bottom", None)), ("proj-Edge_Cuts.gbr", ("outline", None, None)), ("board.GKO", ("outline", None, None)),
                           ("proj-F_SilkS.gbr", (None, None, None)), ("proj-B_Mask.gbr", (None, None, None)), ("board.drl", ("drill", None, None)), ("README", (None, None, None))):
        f = tmp_path / name
        f.write_text(HEAD + "M02*\n")
        assert ng.classify(f) == expected, name


def test_macro_comment_statement(tmp_path):
    """!@brief A macro comment primitive ("0 text", no comma) is skipped. @param tmp_path pytest temp dir. @return None."""
    t = HEAD + "%AMBOX*0 a comment*21,1,2.0,1.0,0,0,0*%\n%ADD10BOX*%\nD10*\n" + xy(10, 15, 3) + "M02*\n"
    assert area(t, tmp_path) == pytest.approx(2.0, rel=0.02)


def test_region_after_an_arc_region_starts_straight(tmp_path):
    """!@brief A square region that follows a region closed with a G03 arc is a square (the interpolation mode is reset). @param tmp_path pytest temp dir. @return None."""
    circle = "G36*\n" + xy(5, 5, 2) + "G03*\nX" + mm(5) + "Y" + mm(5) + "I" + mm(2) + "J0D01*\nG37*\n"
    square = "G36*\n" + xy(15, 15, 2) + xy(18, 15, 1) + xy(18, 18, 1) + xy(15, 18, 1) + xy(15, 15, 1) + "G37*\n"
    assert area(HEAD + circle + square + "M02*\n", tmp_path) == pytest.approx(math.pi * 4.0 + 9.0, rel=0.02)


def test_nonstandard_aperture_is_reported_as_unsupported(tmp_path):
    """!@brief A CAD-specific aperture shape raises NotImplementedError, not a file error. @param tmp_path pytest temp dir. @return None."""
    with pytest.raises(NotImplementedError):
        ng.Layer(HEAD + "%ADD13Rect-W1650000-H1650000-RO1.500*%\nM02*\n")
