#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_gerber_components.py
@brief Tests of `pcbthermal/gerber/components.py`, the Gerber X3 component layer: synthetic layers written from the annotated example of the specification (every outline type, an arc, a height in inches,
       a bottom part, duplicates, attributes in any order), the rotation rule top and bottom, the heat-source order, the link to synthetic paste and copper layers, the detection by content, and, when the
       research data are present, the counts of the three Ucamco/KiCad samples (434 components, 1711 pins, 370 of 370 SMD parts linked to the paste by `TO.C`).
@details Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_gerber_components.py`.
"""

import math
import os
from pathlib import Path

import pytest

from pcbthermal.gerber import components as xc
from pcbthermal.gerber import detect_file, parse_layer, read_layer
from pcbthermal.gerber import parts as P
from pcbthermal.gerber.errors import GerberError

DATA = Path(os.environ.get("PCBT_REAL_BOARDS", "/Volumes/SSD/PROJETOS/pcb-thermal-lab/.claude/worktrees/agent-aa828a7a970c19021/research/gerber-real-boards/data"))


def heat_shape(part, paste_hull=None):
    """!
    @brief The heat polygon of a part and its source name (see `components.heat_polygon`).
    @param part Component.
    @param paste_hull Hull of the paste openings or None.
    @return tuple (polygon, source).
    """
    return xc.heat_polygon(part, paste_hull)


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
    (c,) = xc.parse_components(text)
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
    (c,) = xc.parse_components(text)
    assert c.origin == pytest.approx((25.4, 50.8))
    assert c.height_mm == pytest.approx(2.54)


def test_arc_outline_is_cut_into_chords():
    """!@brief A courtyard with a G03 quarter-circle corner: the polyline stays closed and its area matches the rounded rectangle."""
    # Rounded rectangle 4 x 2 with corner radius 0.5, counter-clockwise: lines G01, corners G03
    t = HEAD.format(layer=1, side="Top") + "D10*\n%TO.C,U1*%\nX0Y0D03*\nD11*\nG75*\nG01*\n"
    t += f"X{mm(-1.5)}Y{mm(-1)}D02*\nX{mm(1.5)}Y{mm(-1)}D01*\nG03*\nX{mm(2)}Y{mm(-0.5)}I0J{mm(0.5)}D01*\nG01*\nX{mm(2)}Y{mm(0.5)}D01*\n"
    t += f"G03*\nX{mm(1.5)}Y{mm(1)}I{mm(-0.5)}J0D01*\nG01*\nX{mm(-1.5)}Y{mm(1)}D01*\nG03*\nX{mm(-2)}Y{mm(0.5)}I0J{mm(-0.5)}D01*\nG01*\nX{mm(-2)}Y{mm(-0.5)}D01*\n"
    t += f"G03*\nX{mm(-1.5)}Y{mm(-1)}I{mm(0.5)}J0D01*\nM02*\n"
    (c,) = xc.parse_components(t)
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
    ps = xc.parse_components(text)
    poly, src = heat_shape(ps[0])
    assert src == "Body" and xc.polygon_area(poly) == pytest.approx(6.25)
    assert heat_shape(ps[1])[1] == "Courtyard"
    poly, src = heat_shape(ps[2])
    assert src == "pins" and xc.polygon_area(poly) == pytest.approx(1.2 * 0.2)
    assert heat_shape(ps[3]) == (None, "none")
    assert xc.duplicate_references(ps) == ["U4"]
    ps[1].outlines.clear()
    ps[1].pins = [xc.Pin("1", "", 9, -1), xc.Pin("2", "", 11, -1), xc.Pin("3", "", 11, 1)]
    assert heat_shape(ps[1])[1] == "pins"


def test_attributes_are_a_dictionary_read_at_the_object():
    """!@brief Review regression: the characteristics may come before `.C` (attribute order is free, page 165 to 167), pins are attached by the reference of `.P` even after a `TD`
    (page 158 asks only `.P` on a pin), and a writer that puts the outlines in a second pass with `.C` repeated gives one part, not a duplicate."""
    t = HEAD.format(layer=1, side="Top")
    # R1: characteristics first, then .C; pins after a TD with .P only
    t += f"D10*\n%TO.CRot,90*%\n%TO.CMnt,SMD*%\n%TO.C,R1*%\nX{mm(1)}Y{mm(2)}D03*\n%TD*%\n"
    # R2: an ordinary part
    t += part("R2", 10, 0, 0, [(1, 9.5, 0), (2, 10.5, 0)])
    # The pins of R1 come late, named by .P only
    t += f"D12*\n%TO.P,R1,1,A*%\nX{mm(1)}Y{mm(1.5)}D03*\nD13*\n%TO.P,R1,2,K*%\nX{mm(1)}Y{mm(2.5)}D03*\n%TD*%\n"
    # Second pass: the courtyard of R1 with .C repeated
    sq = square(1, 2, 1, 2)
    t += f"D11*\n%TO.C,R1*%\nX{mm(sq[0][0])}Y{mm(sq[0][1])}D02*\n" + "".join(f"X{mm(x)}Y{mm(y)}D01*\n" for x, y in sq[1:]) + "%TD*%\nM02*\n"
    ps = xc.parse_components(t)
    assert [p.ref for p in ps] == ["R1", "R2"] and not xc.duplicate_references(ps)
    r1, r2 = ps
    assert r1.rotation == 90.0 and r1.mount == "SMD" and r1.origin == pytest.approx((1, 2))
    assert [(q.number, q.name) for q in r1.pins] == [("1", "A"), ("2", "K")] and r1.pins[0].key
    assert [q.number for q in r2.pins] == ["1", "2"]
    assert xc.polygon_area(r1.outlines["Courtyard"][0]) == pytest.approx(2.0)


def test_two_outline_types_drawn_without_a_move_are_two_loops():
    """!@brief Review regression: a change of aperture ends an outline (page 157: draws connect only when consecutive), so a body drawn right after the courtyard is not appended to it."""
    t = HEAD.format(layer=1, side="Top") + f"D10*\n%TO.C,U1*%\nX0Y0D03*\nD11*\nX{mm(-2)}Y{mm(-2)}D02*\n"
    t += "".join(f"X{mm(x)}Y{mm(y)}D01*\n" for x, y in [(2, -2), (2, 2), (-2, 2), (-2, -2)])
    t += "D14*\n" + "".join(f"X{mm(x)}Y{mm(y)}D01*\n" for x, y in [(-1, -2), (-1, 2), (-2, 2), (-2, -2)]) + "M02*\n"
    (c,) = xc.parse_components(t)
    assert xc.polygon_area(c.outlines["Courtyard"][0]) == pytest.approx(16.0)
    assert xc.polygon_area(c.outlines["Body"][0]) == pytest.approx(4.0)


def test_bottom_rule_matches_the_drawing_of_the_specification():
    """!@brief Page 166 drawing (SOIC-8 at 0 degrees): on the bottom the pin-1 mark is on the right, seen from the top; at 10 degrees both sides turn counter-clockwise."""
    pin1 = [(-2.7, 1.9)]                                    # pin 1 upper left of a top part at rotation zero
    top = xc.Component("U", side="top", origin=(0.0, 0.0), rotation=0.0)
    bot = xc.Component("U", side="bottom", origin=(0.0, 0.0), rotation=0.0)
    assert xc.to_board(top, pin1)[0][0] < 0 < xc.to_board(bot, pin1)[0][0]
    for side in ("top", "bottom"):
        c = xc.Component("U", side=side, origin=(0.0, 0.0), rotation=10.0)
        (x, y), = xc.to_board(c, [(3.0, 0.0) if side == "top" else (-3.0, 0.0)])
        assert y > 0 and x > 0                              # the right end of the part goes up: counter-clockwise seen from the top


def test_no_format_statement_is_an_error():
    """!@brief A file with no FS statement is refused."""
    with pytest.raises(GerberError):
        xc.parse_components("%TF.FileFunction,Component,L1,Top*%\n")


def test_heat_polygon_order_body_lead2lead_paste_footprint_courtyard_pins():
    """!@brief The order Body, Lead2Lead, paste hull, Footprint, Courtyard, pin hull: each one wins when the ones before it are absent."""
    c = xc.Component("U1", origin=(0.0, 0.0))
    c.pins = [xc.Pin("1", "", -1, -1), xc.Pin("2", "", 1, -1), xc.Pin("3", "", 1, 1)]
    paste = [(-0.8, -0.8), (0.8, -0.8), (0.8, 0.8), (-0.8, 0.8)]
    c.outlines = {"Courtyard": [square(0, 0, 4, 4)], "Footprint": [square(0, 0, 3, 3)], "Lead2Lead": [square(0, 0, 2.2, 2.2)], "Body": [square(0, 0, 2.5, 2.5)]}
    assert xc.heat_polygon(c, paste)[1] == "Body"
    del c.outlines["Body"]
    assert xc.heat_polygon(c, paste)[1] == "Lead2Lead"
    del c.outlines["Lead2Lead"]
    poly, src = xc.heat_polygon(c, paste)
    assert src == "paste" and xc.polygon_area(poly) == pytest.approx(2.56)
    assert xc.heat_polygon(c, None)[1] == "Footprint"
    del c.outlines["Footprint"]
    assert xc.heat_polygon(c, None)[1] == "Courtyard"
    del c.outlines["Courtyard"]
    assert xc.heat_polygon(c, None)[1] == "pins"
    assert xc.heat_polygon(xc.Component("U9", origin=(0, 0)), None) == (None, "none")


def test_mount_types_decide_the_heat_source_candidates():
    """!@brief Only SMD is a candidate; TH, Pressfit, Other, Fiducial and an unknown value are listed without a source."""
    for mount, smd in (("SMD", True), ("TH", False), ("Pressfit", False), ("Other", False), ("Fiducial", False), ("", False), ("Surface", False)):
        assert xc.Component("X", mount=mount).is_smd is smd


def paste_with_refs(rects):
    """!
    @brief A paste layer of rectangles with `TO.C`.
    @param rects List of (ref, cx, cy, w, h).
    @return Layer.
    """
    t = "%TF.FileFunction,Paste,Top*%\n%FSLAX46Y46*%\n%MOMM*%\n%LPD*%\n"
    for ref, cx, cy, w, h in rects:
        pts = [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2), (cx - w / 2, cy - h / 2)]
        t += f"%TO.C,{ref}*%\nG36*\nX{mm(pts[0][0])}Y{mm(pts[0][1])}D02*\n" + "".join(f"X{mm(x)}Y{mm(y)}D01*\n" for x, y in pts[1:]) + "G37*\n%TD*%\n"
    return parse_layer(t + "M02*\n")


def test_link_paste_and_link_copper_on_synthetic_layers():
    """!@brief The paste is linked by `TO.C` (parts without paste and references nobody has are reported), the copper by `TO.P` with the offset of the pin from the pad."""
    text = HEAD.format(layer=1, side="Top")
    text += part("R1", 10, 0, 0, [(1, 9.5, 0), (2, 10.5, 0)])
    text += part("J1", 20, 0, 0, [(1, 20, 0)])
    text += part("U1", 30, 0, 0, [(1, 29, 0)])
    comps = xc.parse_components(text + "M02*\n")
    lay = paste_with_refs([("R1", 9.5, 0, 0.5, 0.6), ("R1", 10.5, 0, 0.5, 0.6), ("U1", 29, 0, 0.5, 0.5), ("Z9", 50, 0, 1, 1)])
    pl = xc.link_paste(comps, lay)
    assert sorted(pl.by_ref) == ["R1", "U1"] and len(pl.by_ref["R1"]) == 2
    assert [c.ref for c in pl.without_paste] == ["J1"] and pl.unknown_refs == ["Z9"]
    cu = parse_layer("%TF.FileFunction,Copper,L1,Top*%\n%FSLAX46Y46*%\n%MOMM*%\n%ADD10C,0.5*%\nD10*\n%TO.P,R1,1*%\n" + f"X{mm(9.5)}Y0D03*\n%TO.P,R1,2*%\nX{mm(10.5)}Y{mm(0.02)}D03*\n"
                     + f"%TO.P,J1,1*%\nX{mm(20)}Y0D03*\n%TO.P,Q7,1*%\nX{mm(40)}Y0D03*\n%TD*%\nM02*\n")
    cl = xc.link_copper(comps, [cu])
    assert sorted(cl.by_ref) == ["J1", "R1"] and cl.unknown_refs == ["Q7"]
    assert (cl.pins_matched, cl.pins_total) == (3, 4) and cl.max_offset_mm == pytest.approx(0.02)


def test_detection_by_content_not_by_name():
    """!@brief A component layer is recognised by its file function, or by a ComponentMain aperture; the name `pnp_top.gbr` alone is not enough."""
    assert xc.is_component_layer(HEAD.format(layer=1, side="Top"))
    assert xc.is_component_layer("%FSLAX46Y46*%\n%TA.AperFunction,ComponentMain*%\n%ADD10C,0.3*%\n")
    assert not xc.is_component_layer("%FSLAX46Y46*%\n%TF.FileFunction,Copper,L1,Top*%\n%ADD10C,0.3*%\n")


def test_build_parts_with_an_x3_layer_uses_it_and_notes_the_placement_differences():
    """!@brief `build_parts` with components: source "x3" for every part, the paste hull as the shape of an SMD part, the Courtyard for a through-hole part, and a note where the placement file differs."""
    text = HEAD.format(layer=1, side="Top")
    text += part("R1", 10, 0, 0, [(1, 9.5, 0), (2, 10.5, 0)], court=square(10, 0, 3, 2))
    text += part("J1", 20, 0, 0, [(1, 20, 0)], court=square(20, 0, 4, 4)).replace("CMnt,SMD", "CMnt,TH")
    comps = xc.parse_components(text + "M02*\n")
    lay = paste_with_refs([("R1", 9.5, 0, 0.5, 0.6), ("R1", 10.5, 0, 0.5, 0.6)])
    placement = [dict(ref="R1", value="", package="", x=10.9, y=0, rot=0, side="top"), dict(ref="Q9", value="", package="", x=0, y=0, rot=0, side="top")]
    res = P.build_parts({"top": lay}, placement, comps)
    by = {p.designator: p for p in res.parts}
    assert set(by) == {"R1", "J1"} and all(p.from_file["source"] == "x3" for p in by.values())
    assert by["R1"].from_file["shape_source"] == "paste" and by["R1"].shape == "hull" and by["R1"].from_file["value"] == "VR1" and by["R1"].from_file["mount"] == "SMD"
    assert by["J1"].from_file["shape_source"] == "Courtyard" and by["J1"].from_file["mount"] == "TH" and by["J1"].shape == "outline"
    note = res.info["x3_vs_placement"]
    assert note["only_x3"] == ["J1"] and note["only_placement"] == ["Q9"] and note["moved"] == [("R1", 0.9)]
    box = P.build_parts({"top": lay}, None, comps, shape="box")
    assert next(p for p in box.parts if p.designator == "R1").shape == "box"


needs_data = pytest.mark.skipif(not (DATA / "stickhub" / "compF.gbr").exists(), reason="the research boards are not in " + str(DATA))


def read_board(folder):
    """!
    @brief Read the component, paste and copper layers of a sample board by the detected function.
    @param folder Board folder.
    @return tuple (components, paste dict, copper layers).
    """
    comps, paste, copper = [], {}, []
    for f in sorted(folder.glob("*.gbr")):
        fn = detect_file(f)
        if fn.kind == "component":
            comps += xc.read_components(f)
        elif fn.kind == "paste":
            paste[fn.side] = read_layer(f)
        elif fn.kind == "copper":
            copper.append(read_layer(f))
    return comps, paste, copper


@needs_data
def test_the_three_kicad_samples_reproduce_the_counts_of_the_research():
    """!@brief 434 components, 1711 pins, SMD 370 / TH 60 / Other 4, 370 of 370 SMD parts linked to their paste by `TO.C`, 64 without paste, every pin on the copper pad of the same `TO.P` at 0.0 mm."""
    folders = [DATA / "stickhub", DATA / "ucamco" / "x3_coldfire", DATA / "ucamco" / "x3_liion"]
    n = pins = smd = linked = nopaste = 0
    mounts = {}
    for folder in folders:
        comps, paste, copper = read_board(folder)
        assert not xc.duplicate_references(comps)
        res = P.build_parts(paste, None, comps, copper)
        n += len(comps)
        pins += sum(len(c.pins) for c in comps)
        smd += sum(c.is_smd for c in comps)
        for c in comps:
            mounts[c.mount] = mounts.get(c.mount, 0) + 1
        every = {p.designator: p for p in res.parts + res.listed}
        linked += sum(1 for c in comps if c.is_smd and every[c.ref].from_file["n_openings"] > 0)
        nopaste += sum(1 for c in comps if every[c.ref].from_file["n_openings"] == 0)
        assert res.info["copper"]["pins_matched"] == res.info["copper"]["pins_total"] and res.info["copper"]["max_offset_mm"] == pytest.approx(0.0, abs=1e-6)
        assert not res.info["unknown_refs"]
    assert (n, pins, smd, linked, nopaste) == (434, 1711, 370, 370, 64)
    assert mounts == {"SMD": 370, "TH": 60, "Other": 4}


@needs_data
def test_stickhub_counts_and_the_bottom_part_frame():
    """!@brief StickHub top: 35 parts, all with origin, courtyard and pins; bottom 51 parts, 50 courtyards; the diode D4 at -90 degrees has pin 1 above the origin; the copper names C38, J1 and JP1 that the layers do not."""
    for f, n, with_court in (("compF.gbr", 35, 35), ("compB.gbr", 51, 50)):
        ps = xc.read_components(DATA / "stickhub" / f)
        assert len(ps) == n and sum(1 for p in ps if p.outlines.get("Courtyard")) == with_court
        assert all(p.origin for p in ps) and not xc.duplicate_references(ps) and all(p.height_mm is None for p in ps)
    d4 = next(p for p in xc.read_components(DATA / "stickhub" / "compF.gbr") if p.ref == "D4")
    assert d4.rotation == -90.0 and d4.pins[0].number == "1" and d4.pins[0].y > d4.origin[1]
    comps, paste, copper = read_board(DATA / "stickhub")
    assert xc.link_copper(comps, copper).unknown_refs == ["C38", "J1", "JP1"]
