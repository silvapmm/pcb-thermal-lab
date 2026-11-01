#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_x3_components.py
@brief Tests of the X3 component-layer reader (`lib/x3_components.py`): a synthetic layer written from the annotated example of the Gerber specification (rev 2026.05, pages 180 and 181) with
       every outline type, an arc, a height in inches and a bottom part; the rotation rule against a rotated footprint; the heat-shape preference; and, when the Ucamco samples are in data/, the counts.
"""

import math
from pathlib import Path

import pytest

import x3
import x3_components as xc

HERE = Path(__file__).resolve().parents[1]
DATA = HERE / "data"

HEAD = """%TF.GenerationSoftware,Test,Synthetic,1*%
%TF.FileFunction,Component,L{layer},{side}*%
%TF.FilePolarity,Positive*%
%FSLAX46Y46*%
%MOMM*%
%LPD*%
%TA.AperFunction,ComponentMain*%
%ADD10C,0.3*%
%TA.AperFunction,ComponentOutline,Courtyard*%
%ADD11C,0.1*%
%TA.AperFunction,ComponentOutline,Body*%
%ADD14C,0.1*%
%TA.AperFunction,ComponentPin*%
%ADD12P,0.36X4X0.0*%
%ADD13C,0.1*%
%TD*%
"""


def flat(pts):
    """!
    @brief Flatten a list of (x, y) for `pytest.approx`.
    @param pts List of (x, y).
    @return list of float.
    """
    return [c for p in pts for c in p]


def mm(v):
    """!
    @brief A length as the integer of the FSLAX46 format.
    @param v mm.
    @return str.
    """
    return str(int(round(v * 1e6)))


def part(ref, x, y, rot, pins, court=None, body=None, extra=""):
    """!
    @brief The text of one component in the layout of the specification's example.
    @param ref Reference designator.
    @param x Origin x (mm).
    @param y Origin y (mm).
    @param rot CRot (degrees).
    @param pins List of (number, x, y) in mm, board frame.
    @param court Closed polyline of the courtyard or None.
    @param body Closed polyline of the body or None.
    @param extra More attribute lines.
    @return str.
    """
    t = f"D10*\n%TO.C,{ref}*%\n%TO.CFtp,FP_{ref[0]}*%\n%TO.CVal,V{ref}*%\n%TO.CMnt,SMD*%\n%TO.CRot,{rot}*%\n{extra}X{mm(x)}Y{mm(y)}D03*\n"
    for ap, poly in (("D11", court), ("D14", body)):
        if poly:
            t += ap + "*\n" + f"X{mm(poly[0][0])}Y{mm(poly[0][1])}D02*\n"
            t += "".join(f"X{mm(px)}Y{mm(py)}D01*\n" for px, py in poly[1:])
    for k, (n, px, py) in enumerate(pins):
        t += ("D12*\n" if k == 0 else "D13*\n") + f"%TO.P,{ref},{n}*%\nX{mm(px)}Y{mm(py)}D03*\n"
    return t + "%TD*%\n"


def square(cx, cy, w, h):
    """!
    @brief Closed rectangle polyline.
    @param cx Centre x.
    @param cy Centre y.
    @param w Width.
    @param h Height.
    @return list of (x, y), first point repeated at the end.
    """
    return [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2), (cx - w / 2, cy - h / 2)]


def test_parse_fields_outlines_pins():
    """!@brief Reference, footprint, value, mount, rotation, origin, outlines by type, key pin, pin numbers (the reference is the first field of .P, the number the second)."""
    text = HEAD.format(layer=1, side="Top") + part("R301", 10, 20, -90, [(1, 10, 21), (2, 10, 19)], court=square(10, 20, 3, 2), body=square(10, 20, 2, 1.2), extra="%TO.CHgt,0.55*%\n") + "M02*\n"
    (c,) = xc.parse(text)
    assert (c.ref, c.side, c.layer, c.footprint, c.value, c.mount, c.rotation) == ("R301", "top", 1, "FP_R", "VR301", "SMD", -90.0)
    assert c.origin == pytest.approx((10, 20))
    assert [p.number for p in c.pins] == ["1", "2"] and c.pins[0].key and not c.pins[1].key
    assert set(c.outlines) == {"Courtyard", "Body"}
    assert xc.polygon_area(c.outlines["Courtyard"][0]) == pytest.approx(6.0)
    assert xc.polygon_area(c.outlines["Body"][0]) == pytest.approx(2.4)
    assert c.height_mm == pytest.approx(0.55)


def test_inch_file_converts_lengths_and_height():
    """!@brief A file in inches: coordinates and .CHgt come out in mm."""
    text = ("%TF.FileFunction,Component,L1,Top*%\n%FSLAX24Y24*%\n%MOIN*%\n%TA.AperFunction,ComponentMain*%\n%ADD10C,0.012*%\n%TD*%\nD10*\n%TO.C,C1*%\n%TO.CHgt,0.1*%\n"
            "X10000Y20000D03*\nM02*\n")
    (c,) = xc.parse(text)
    assert c.origin == pytest.approx((25.4, 50.8))
    assert c.height_mm == pytest.approx(2.54)


def test_arc_outline_is_cut_into_chords():
    """!@brief A courtyard with a G03 quarter-circle corner: the polyline stays closed and its area matches the rounded rectangle."""
    # Rounded rectangle 4 x 2 with corner radius 0.5, counter-clockwise: lines G01, corners G03
    t = HEAD.format(layer=1, side="Top") + "D10*\n%TO.C,U1*%\nX0Y0D03*\nD11*\nG75*\nG01*\n"
    t += f"X{mm(-1.5)}Y{mm(-1)}D02*\nX{mm(1.5)}Y{mm(-1)}D01*\nG03*\nX{mm(2)}Y{mm(-0.5)}I0J{mm(0.5)}D01*\nG01*\nX{mm(2)}Y{mm(0.5)}D01*\n"
    t += f"G03*\nX{mm(1.5)}Y{mm(1)}I{mm(-0.5)}J0D01*\nG01*\nX{mm(-1.5)}Y{mm(1)}D01*\nG03*\nX{mm(-2)}Y{mm(0.5)}I0J{mm(-0.5)}D01*\nG01*\nX{mm(-2)}Y{mm(-0.5)}D01*\n"
    t += f"G03*\nX{mm(-1.5)}Y{mm(-1)}I{mm(0.5)}J0D01*\nM02*\n"
    (c,) = xc.parse(t)
    loop = c.outlines["Courtyard"][0]
    assert loop[0] == pytest.approx(loop[-1])
    assert xc.polygon_area(loop) == pytest.approx(4 * 2 - (4 - math.pi) * 0.25, rel=2e-3)


def test_rotation_rule_top_and_bottom_round_trip():
    """!@brief to_board and to_local are inverse; a top part at -90 puts a pin that is at local (-0.45, 0) at (0, +0.45) from the origin (the StickHub diode); a bottom part has x flipped first."""
    top = xc.Component("D4", side="top", origin=(150.4, -96.75), rotation=-90.0)
    (b,) = xc.to_board(top, [(-0.45, 0.0)])
    assert b == pytest.approx((150.4, -96.75 + 0.45))
    for side in ("top", "bottom"):
        c = xc.Component("X", side=side, origin=(3.0, 4.0), rotation=37.0)
        pts = [(1.0, 0.5), (-2.0, 0.25)]
        assert flat(xc.to_local(c, xc.to_board(c, pts))) == pytest.approx(flat(pts))
    bot = xc.Component("Q", side="bottom", origin=(0.0, 0.0), rotation=0.0)
    assert xc.to_board(bot, [(1.0, 0.5)])[0] == pytest.approx((-1.0, 0.5))


def test_same_footprint_two_rotations_gives_one_frame():
    """!@brief The rule undoes the rotation of a footprint placed at 0 and 90 degrees: the local pin sets agree."""
    fp = [(-0.5, 0.0), (0.5, 0.0)]
    parts = []
    for ref, rot in (("R1", 0.0), ("R2", 90.0), ("R3", 180.0)):
        c = xc.Component(ref, side="top", origin=(5.0, 5.0), rotation=rot)
        c.pins = [xc.Pin(str(k + 1), "", x, y) for k, (x, y) in enumerate(xc.to_board(c, fp))]
        parts.append(c)
    ref = [p for p in xc.to_local(parts[0], parts[0].pin_points())]
    for p in parts[1:]:
        assert flat(xc.to_local(p, p.pin_points())) == pytest.approx(flat(ref))


def test_heat_shape_preference_and_fallbacks():
    """!@brief Body beats the courtyard; with only pins the hull; two collinear pins give a box grown by 0.1 mm; a bare component gives none; duplicates are reported."""
    text = HEAD.format(layer=1, side="Top")
    text += part("U1", 0, 0, 0, [(1, -1, -1), (2, 1, -1), (3, 1, 1), (4, -1, 1)], court=square(0, 0, 4, 4), body=square(0, 0, 2.5, 2.5))
    text += part("U2", 10, 0, 0, [(1, 9, -1), (2, 11, -1), (3, 11, 1)], court=square(10, 0, 5, 5))
    text += part("U3", 20, 0, 0, [(1, 19.5, 0), (2, 20.5, 0)])
    text += part("U4", 30, 0, 0, [])
    text += part("U4", 40, 0, 0, [])
    ps = xc.parse(text)
    poly, src = xc.heat_shape(ps[0])
    assert src == "Body" and xc.polygon_area(poly) == pytest.approx(6.25)
    assert xc.heat_shape(ps[1])[1] == "Courtyard"
    poly, src = xc.heat_shape(ps[2])
    assert src == "pins" and xc.polygon_area(poly) == pytest.approx(1.2 * 0.2)
    assert xc.heat_shape(ps[3]) == (None, "none")
    assert xc.duplicate_references(ps) == ["U4"]
    ps[1].outlines.clear()
    ps[1].pins = [xc.Pin("1", "", 9, -1), xc.Pin("2", "", 11, -1), xc.Pin("3", "", 11, 1)]
    assert xc.heat_shape(ps[1])[1] == "pins"


def test_no_format_statement_is_an_error():
    """!@brief A file with no FS statement is refused."""
    with pytest.raises(ValueError):
        xc.parse("%TF.FileFunction,Component,L1,Top*%\n")


@pytest.mark.skipif(not (DATA / "stickhub" / "compF.gbr").exists(), reason="the Ucamco X3 samples are not downloaded")
def test_stickhub_counts_and_agreement_with_the_regex_reader():
    """!@brief StickHub top: 35 parts, all with origin, courtyard and pins, the same references and pins as the earlier regex reader; bottom 51 parts, 50 courtyards."""
    for f, n, with_court in (("compF.gbr", 35, 35), ("compB.gbr", 51, 50)):
        path = DATA / "stickhub" / f
        ps = xc.parse(path.read_text(errors="replace"))
        old = x3.components(path)
        assert len(ps) == n and [p.ref for p in ps] == [o["ref"] for o in old]
        assert sum(len(p.pins) for p in ps) == sum(len(o["pins"]) for o in old)
        assert sum(1 for p in ps if p.outlines.get("Courtyard")) == with_court
        assert all(p.origin for p in ps) and not xc.duplicate_references(ps)
        assert all(p.height_mm is None for p in ps)
    # The diode D4 of the specification-style layout: pin 1 above the origin for CRot -90
    d4 = next(p for p in xc.parse((DATA / "stickhub" / "compF.gbr").read_text()) if p.ref == "D4")
    assert d4.rotation == -90.0 and d4.pins[0].number == "1" and d4.pins[0].y > d4.origin[1]
