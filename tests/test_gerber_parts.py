#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_gerber_parts.py
@brief Tests of `pcbthermal/gerber/parts.py`: placement files, paste openings, the envelope matching rule, the bottom-side convention, the frame check, the click, `build_parts`, the re-import merge
       and `ImportPart.from_file`; synthetic boards with a known answer first, then the real boards of the research (skipped when their git-ignored data folder is absent).
@details The openings of the synthetic boards are placed from the KiCad library pad positions of each footprint (from memory: C_0402 pads at +-0.48 mm, C_0603 at +-0.775 mm, SOIC-8 at x +-2.475 mm
         and y +-0.635, +-1.905 mm, SOT-223 pins at x -3.15 mm and the tab at x +3.15 mm), not from the envelope table of the rule, so the test is not circular. Rotation: counter-clockwise positive, Y up.
         Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_gerber_parts.py`.
"""

import json
import math
import os
from pathlib import Path

import pytest

from pcbthermal.gerber import parse_layer, read_layer
from pcbthermal.gerber import parts as P
from pcbthermal.model import ImportPart

## The git-ignored boards of the research (placement files, paste layers); the tests that need them skip when the folder is absent.
DATA = Path(os.environ.get("PCBT_REAL_BOARDS", "/Volumes/SSD/PROJETOS/pcb-thermal-lab/.claude/worktrees/agent-aa828a7a970c19021/research/gerber-real-boards/data"))

PADS = {
    "C_0402_1005Metric": [(-0.48, 0.0), (0.48, 0.0)],
    "C_0603_1608Metric": [(-0.775, 0.0), (0.775, 0.0)],
    "SOIC-8_3.9x4.9mm_P1.27mm": [(sx * 2.475, y) for sx in (-1, 1) for y in (-1.905, -0.635, 0.635, 1.905)],
    "SOT-223-3_TabPin2": [(-3.15, -2.3), (-3.15, 0.0), (-3.15, 2.3), (3.15, 0.0)],
}
SIZE = {"C_0402_1005Metric": (0.5, 0.55), "C_0603_1608Metric": (0.8, 0.95), "SOIC-8_3.9x4.9mm_P1.27mm": (1.95, 0.6), "SOT-223-3_TabPin2": (2.0, 1.5)}


def part(ref, package, x, y, rot, side="top"):
    """!
    @brief A part of a placement file.
    @param ref Designator.
    @param package Footprint name.
    @param x X of the origin in mm.
    @param y Y of the origin in mm.
    @param rot Rotation in degrees (counter-clockwise).
    @param side "top" or "bottom".
    @return dict as read by `read_placement`.
    """
    return dict(ref=ref, package=package, value="", x=x, y=y, rot=rot, side=side)


def pad_polys(p, mirror=False):
    """!
    @brief The paste openings of a part on the board as rotated rectangles (the known answer).
    @param p Part dict (its true position).
    @param mirror True: the footprint is mirrored in X (a bottom-side part seen from the top).
    @return list of polygons [(x, y) x 4] in mm.
    """
    a = math.radians(p["rot"])
    c, s = math.cos(a), math.sin(a)
    w, h = SIZE[p["package"]]
    out = []
    for u, v in PADS[p["package"]]:
        u = -u if mirror else u
        corners = [(u - w / 2, v - h / 2), (u + w / 2, v - h / 2), (u + w / 2, v + h / 2), (u - w / 2, v + h / 2)]
        out.append([(p["x"] + cu * c - cv * s, p["y"] + cu * s + cv * c) for cu, cv in corners])
    return out


def fmt(v):
    """!
    @brief A millimetre as an integer of the FSLAX46 format.
    @param v Length in mm.
    @return str.
    """
    return str(int(round(v * 1e6)))


def paste_text(polys, side="Top", refs=None):
    """!
    @brief The text of a paste layer: every polygon a region, optionally with a `TO.C` reference.
    @param polys List of polygons.
    @param side "Top" or "Bot".
    @param refs List of references (one per polygon) or None.
    @return str.
    """
    t = f"%TF.FileFunction,Paste,{side}*%\n%FSLAX46Y46*%\n%MOMM*%\n%LPD*%\n"
    for k, poly in enumerate(polys):
        if refs:
            t += f"%TO.C,{refs[k]}*%\n"
        t += "G36*\n" + f"X{fmt(poly[0][0])}Y{fmt(poly[0][1])}D02*\n" + "".join(f"X{fmt(x)}Y{fmt(y)}D01*\n" for x, y in poly[1:] + poly[:1]) + "G37*\n"
        if refs:
            t += "%TD*%\n"
    return t + "M02*\n"


def layer_of(parts_list, side="top", with_refs=False, mirror=False):
    """!
    @brief A parsed paste layer holding the openings of some parts.
    @param parts_list Parts (true positions).
    @param side "top" or "bottom".
    @param with_refs True: write `TO.C` per opening.
    @param mirror True: bottom-side footprints.
    @return tuple (Layer, list of (designator) per polygon in file order).
    """
    polys, refs = [], []
    for p in parts_list:
        for poly in pad_polys(p, mirror):
            polys.append(poly)
            refs.append(p["ref"])
    return parse_layer(paste_text(polys, "Top" if side == "top" else "Bot", refs if with_refs else None)), refs


def score(parts_list, layer, truth, side="top", tol=0.3):
    """!
    @brief Run the rule and compare with the known answer.
    @param parts_list Placement as the file writes it.
    @param layer Paste Layer.
    @param truth Designator of each polygon of the layer, in file order.
    @param side Side of the layer.
    @param tol Envelope tolerance in mm.
    @return tuple (correct, wrong, unassigned).
    """
    ops = P.read_openings(layer, side, by_ref=False)
    # The openings are read in raster order; the truth of an opening is that of the polygon that holds its centre
    _, bypad = P.match_envelope(parts_list, ops, tol)
    ok = wrong = 0
    for i, r in bypad.items():
        ok += truth_of(layer, truth, ops[i]) == r
        wrong += truth_of(layer, truth, ops[i]) != r
    return ok, wrong, len(ops) - len(bypad)


def truth_of(layer, truth, opening):
    """!
    @brief The designator of the polygon of a layer that holds the centre of an opening.
    @param layer Paste Layer (its operations are the polygons, in file order).
    @param truth Designator of each region, in file order.
    @param opening Opening.
    @return str.
    """
    boxes = layer.op_boxes()
    for k, b in enumerate(boxes):
        if b[0] - 0.03 <= opening.x <= b[2] + 0.03 and b[1] - 0.03 <= opening.y <= b[3] + 0.03:
            return truth[k]
    return None


# ------------------------------------------------------------------------------------------------------------------------------ placement files
def test_kicad_text_report_with_inch_unit_and_quoted_value():
    """!@brief A KiCad `.pos` with `## Unit = inch` and a quoted value that holds a blank is read in mm."""
    text = ("### Module positions - created on 2026 ###\n## Unit = inch, Angle = deg.\n## Side : All\n# Ref     Val       Package               PosX       PosY       Rot  Side\n"
            'R1  "10 k"  R_0402_1005Metric  1.000000  -2.000000  90.000000  top\nC2  100n  C_0603_1608Metric  0.500000  0.250000  180.000000  bottom\n## End\n')
    a, b = P.parse_placement(text)
    assert (a["ref"], a["value"], a["package"], a["side"]) == ("R1", "10 k", "R_0402_1005Metric", "top")
    assert (a["x"], a["y"], a["rot"]) == pytest.approx((25.4, -50.8, 90.0))
    assert b["side"] == "bottom" and b["x"] == pytest.approx(12.7)


def test_jlcpcb_csv_with_unit_suffixes_and_generic_csv_with_header_units():
    """!@brief JLCPCB columns (`Mid X` with `mm`), a semicolon CSV with decimal commas and `(mil)` in the header, and a tab file are all read."""
    jlc = "Designator,Val,Package,Mid X,Mid Y,Rotation,Layer\nC1,100n,C_0402,12.5mm,3.25mm,270,T\nU1,MCU,QFN,100mil,0mil,0,B\n"
    a, b = P.parse_placement(jlc)
    assert (a["x"], a["y"], a["rot"]) == pytest.approx((12.5, 3.25, 270.0)) and a["side"] == "top"
    assert (b["x"], b["y"], b["side"]) == (pytest.approx(2.54), 0.0, "bottom")
    semi = "RefDes;Comment;Footprint;X (mil);Y (mil);Rotation;Side\nR1;1k;0603;1000,5;200;90;Top\n"
    (r,) = P.parse_placement(semi)
    assert (r["x"], r["y"]) == pytest.approx((1000.5 * 0.0254, 200 * 0.0254))
    tab = "Ref\tX\tY\tRot\tSide\nQ1\t1.5\t-2.5\t45\tBottom\n"
    (q,) = P.parse_placement(tab)
    assert (q["x"], q["y"], q["rot"], q["side"]) == (1.5, -2.5, 45.0, "bottom")
    with pytest.raises(ValueError):
        P.parse_placement("foo,bar\n1,2\n")
    with pytest.raises(ValueError):
        P.parse_placement("Ref,X,Y\nR1,abc,2\n")


# ------------------------------------------------------------------------------------------------------------------------------ openings
def test_openings_of_a_region_and_the_touching_references_stay_apart():
    """!@brief Two rectangles of 1 x 0.5 mm: area, centroid, box and hull; two openings of different `TO.C` that touch are two with `by_ref` and one without."""
    a = [(0, 0), (1, 0), (1, 0.5), (0, 0.5)]
    b = [(1, 0), (2, 0), (2, 0.5), (1, 0.5)]                    # shares the edge x = 1 with a
    lay = parse_layer(paste_text([a, b], "Top", ["R1", "R2"]))
    ops = P.read_openings(lay, "top", by_ref=True)
    assert sorted(o.ref for o in ops) == ["R1", "R2"]
    o1 = next(o for o in ops if o.ref == "R1")
    assert o1.area == pytest.approx(0.5, abs=0.06) and (o1.x, o1.y) == pytest.approx((0.5, 0.25), abs=0.03)
    assert o1.bbox == pytest.approx((0.0, 0.0, 1.0, 0.5), abs=0.06)
    assert len(o1.hull) >= 4
    one = P.read_openings(lay, "top", by_ref=False)
    assert len(one) == 1 and one[0].ref is None and one[0].area == pytest.approx(1.0, abs=0.1)


def test_the_click_takes_the_largest_opening_under_the_point():
    """!@brief A small opening inside the box of a large one: a click on the small one's hull takes the large opening only when the point is outside the small one; the largest wins where they overlap in tolerance."""
    big = [(0, 0), (4, 0), (4, 4), (0, 4)]
    small = [(5, 1), (5.5, 1), (5.5, 1.5), (5, 1.5)]
    lay = parse_layer(paste_text([big, small]))
    ops = P.read_openings(lay, "top")
    assert len(ops) == 2
    i = P.opening_at(ops, 2.0, 2.0)
    assert ops[i].area > 10
    j = P.opening_at(ops, 5.25, 1.25)
    assert ops[j].area < 1
    assert P.opening_at(ops, 8.0, 8.0) is None
    assert P.opening_at(ops, 2.0, 2.0, side="bottom") is None
    # Just outside the small opening, inside the finger tolerance
    assert P.opening_at(ops, 5.58, 1.25) == j


def test_shape_options_hull_box_largest_and_the_hull_of_a_turned_pattern():
    """!@brief Box and hull of two pads: equal for a rectangular pattern; for a pattern turned by 45 degrees the box is larger than the hull."""
    p0 = part("C1", "C_0603_1608Metric", 0.0, 0.0, 0)
    lay, _ = layer_of([p0])
    ops = P.read_openings(lay, "top")
    box, hull = P.shape_polygon(ops, "box"), P.shape_polygon(ops, "hull")
    assert polygon_area(box) == pytest.approx(polygon_area(hull), rel=0.02)
    p45 = part("C1", "C_0603_1608Metric", 0.0, 0.0, 45)
    lay, _ = layer_of([p45])
    ops = P.read_openings(lay, "top")
    assert polygon_area(P.shape_polygon(ops, "box")) > 1.5 * polygon_area(P.shape_polygon(ops, "hull"))
    assert polygon_area(P.shape_polygon(ops, "largest")) < polygon_area(P.shape_polygon(ops, "hull"))
    with pytest.raises(ValueError):
        P.shape_polygon(ops, "circle")


def polygon_area(poly):
    """!
    @brief Shoelace area.
    @param poly List of (x, y).
    @return float.
    """
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, list(poly[1:]) + [poly[0]]))) / 2.0


def test_proximity_groups_are_a_fallback_that_merges_close_neighbours():
    """!@brief Two pads of one 0402 are one group; a second part 0.4 mm away joins it (the known fault of the fallback); a part 5 mm away is its own group."""
    parts = [part("C1", "C_0402_1005Metric", 0.0, 0.0, 0), part("C2", "C_0402_1005Metric", 0.0, 1.0, 0), part("C3", "C_0402_1005Metric", 0.0, 6.0, 0)]
    lay, _ = layer_of(parts)
    ops = P.read_openings(lay, "top")
    groups = P.proximity_groups(ops, link_mm=0.6)
    sizes = sorted(len(g) for g in groups)
    assert sizes == [2, 4]                                        # C1 and C2 (0.45 mm apart in y) merged; C3 alone


# ------------------------------------------------------------------------------------------------------------------------------ the envelope rule
def test_two_pad_parts_at_every_quarter_turn_and_at_45_degrees():
    """!@brief Five passives 1.6 mm apart at 0, 90, 180, 270 and 45 degrees: each opening goes to its own part."""
    parts = [part(f"C{i}", "C_0402_1005Metric", 1.6 * i, 0.0, rot) for i, rot in enumerate((0, 90, 180, 270))] + [part("C9", "C_0603_1608Metric", 8.0, 0.0, 45)]
    lay, truth = layer_of(parts)
    assert score(parts, lay, truth) == (10, 0, 0)


def test_pads_far_from_the_origin_and_the_smallest_envelope_wins():
    """!@brief A SOIC-8 at 90 degrees and a SOT-223 at 270 have pads 2.5 to 3.2 mm from the origin; a 0402 under the SOIC body keeps its own two openings."""
    parts = [part("U2", "SOIC-8_3.9x4.9mm_P1.27mm", 10.0, 10.0, 90), part("U1", "SOT-223-3_TabPin2", 25.0, 10.0, 270), part("C5", "C_0402_1005Metric", 10.0, 10.0, 0)]
    lay, truth = layer_of(parts)
    assert score(parts, lay, truth) == (14, 0, 0)


def test_the_sign_of_the_rotation_matters_only_off_the_quarter_turns():
    """!@brief A file with the opposite rotation sign changes nothing at the quarter turns; at 45 degrees it loses the openings."""
    quarter = [part(f"C{i}", "C_0402_1005Metric", 2.0 * i, 0.0, rot) for i, rot in enumerate((0, 90, 180, 270))]
    lay, truth = layer_of(quarter)
    assert score([dict(p, rot=-p["rot"]) for p in quarter], lay, truth) == (8, 0, 0)
    c45 = [part("C9", "C_0603_1608Metric", 0.0, 0.0, 45)]
    lay, truth = layer_of(c45)
    assert score(c45, lay, truth, tol=0.2) == (2, 0, 0)
    assert score([dict(c45[0], rot=-45)], lay, truth, tol=0.2) == (0, 0, 2)


def test_the_bottom_x_convention_is_detected_from_the_openings():
    """!@brief Bottom parts with mirrored footprints; one file writes the board X, the other the negated X; the detection picks the right one and a tie keeps the file."""
    true = [part("C1", "C_0402_1005Metric", 30.0, -40.0, 90, "bottom"), part("C2", "C_0402_1005Metric", 34.0, -49.0, 180, "bottom"),
            part("U3", "SOIC-8_3.9x4.9mm_P1.27mm", 40.0, -45.0, 0, "bottom")]
    lay, truth = layer_of(true, side="bottom", mirror=True)
    ops = P.read_openings(lay, "bottom")
    conv, n_as, n_neg = P.bottom_convention(true, ops)
    assert conv == "as is" and n_as == len(ops) and n_neg == 0
    negated = [dict(p, x=-p["x"]) for p in true]
    conv, n_as, n_neg = P.bottom_convention(negated, ops)
    assert conv == "negated X" and n_as == 0 and n_neg == len(ops)
    assert score(P.apply_bottom_convention(negated, conv), lay, truth, side="bottom") == (len(ops), 0, 0)
    assert score(negated, lay, truth, side="bottom") == (0, 0, len(ops))
    # No bottom parts, or a tie: the file as it is
    assert P.bottom_convention([part("C1", "C_0402_1005Metric", 0, 0, 0)], ops)[0] == "as is"


def test_island_board_far_from_the_origin():
    """!@brief A board 1500 mm from the origin (a panel, an island): the window is the layer's, the rule and `build_parts` find every part."""
    parts = [part("C1", "C_0402_1005Metric", 1500.0, -2300.0, 0), part("U1", "SOIC-8_3.9x4.9mm_P1.27mm", 1510.0, -2300.0, 270), part("Q1", "SOT-223-3_TabPin2", 1520.0, -2295.0, 180)]
    lay, truth = layer_of(parts)
    assert score(parts, lay, truth) == (14, 0, 0)
    res = P.build_parts({"top": lay}, parts)
    assert {p.designator: p.from_file["source"] for p in res.parts} == {"C1": "placement by position", "U1": "placement by position", "Q1": "placement by position"}
    assert not res.unmatched and not res.listed
    q = next(p for p in res.parts if p.designator == "Q1")
    xs = [pt[0] for pt in q.polygon_mm]
    assert 1515.5 < min(xs) and max(xs) < 1524.5


def test_limit_a_part_missing_from_the_placement_file_is_taken_by_a_neighbour_or_stays_unmatched():
    """!@brief The cmm2 case: an opening of an unlisted part inside a listed envelope is taken by it (marker of the limit); an opening outside every envelope stays unmatched."""
    soic = part("U2", "SOIC-8_3.9x4.9mm_P1.27mm", 0.0, 0.0, 0)
    near = part("J8", "C_0402_1005Metric", 0.0, 2.45, 0)         # pads in the tolerance zone of the SOIC envelope
    far = part("J9", "C_0402_1005Metric", 20.0, 0.0, 0)
    lay, truth = layer_of([soic, near, far])
    res = P.build_parts({"top": lay}, [soic])
    taken = next(p for p in res.parts if p.designator == "U2")
    assert taken.from_file["n_openings"] == 10                    # 8 own + 2 of J8 (the known limit)
    assert len(res.unmatched) == 2 and all(abs(o.x - 20.0) < 1 for o in res.unmatched)


def test_through_hole_part_without_paste_is_listed_not_an_error():
    """!@brief A pin header in the placement file with no paste opening is returned in `listed`, with no polygon."""
    c1 = part("C1", "C_0402_1005Metric", 0.0, 0.0, 0)
    hdr = part("J1", "PinHeader_1x04_P2.54mm_Vertical", 30.0, 0.0, 0)
    lay, _ = layer_of([c1])
    res = P.build_parts({"top": lay}, [c1, hdr])
    assert [p.designator for p in res.parts] == ["C1"]
    assert [p.designator for p in res.listed] == ["J1"] and res.listed[0].polygon_mm == [] and res.listed[0].from_file["source"] == P.SOURCE_NO_OPENING


def test_frame_check_proposes_the_offset_only_when_the_files_disagree():
    """!@brief Files that agree are not moved; a placement file 3.0 mm off in X and -2.0 mm in Y gets the offset that realigns it; `build_parts` warns and, given the offset, assigns every opening."""
    parts = [part(f"C{i}", "C_0402_1005Metric", 4.0 * (i % 6), 5.0 * (i // 6), (0, 90)[i % 2]) for i in range(24)]
    lay, truth = layer_of(parts)
    ops = P.read_openings(lay, "top")
    ok = P.frame_check(parts, ops)
    assert not ok["propose"] and ok["given"] == 1.0
    shifted = P.apply_offset(parts, 3.0, -2.0)
    fc = P.frame_check(shifted, ops)
    assert fc["propose"] and (fc["dx"], fc["dy"]) == pytest.approx((-3.0, 2.0), abs=0.1) and fc["best"] > fc["given"] + 0.3
    res = P.build_parts({"top": lay}, shifted)
    assert res.info["frame"]["propose"] and any("origin" in w for w in res.info["warnings"])
    res2 = P.build_parts({"top": lay}, shifted, offset=(fc["dx"], fc["dy"]))
    assert len(res2.parts) == 24 and not res2.unmatched


# ------------------------------------------------------------------------------------------------------------------------------ build_parts routes
def test_to_c_route_with_and_without_a_placement_entry_and_the_marked_fallback():
    """!@brief Openings with `TO.C`: a part in the placement file is "to.c+placement" (value and package from the file), a part not in it is "paste only"; unreferenced openings are unmatched or, as a marked fallback, P<n> groups."""
    c1 = part("C1", "C_0402_1005Metric", 0.0, 0.0, 0)
    c1["value"] = "100n"
    c2 = part("C2", "C_0402_1005Metric", 5.0, 0.0, 0)
    stray = part("X", "C_0402_1005Metric", 30.0, 0.0, 0)
    polys = pad_polys(c1) + pad_polys(c2) + pad_polys(stray)
    refs = ["C1", "C1", "C2", "C2", None, None]
    text = paste_text(polys[:4], "Top", refs[:4])
    # The stray pads carry no TO.C: appended after a TD
    text = text.replace("M02*\n", "") + "".join(f"G36*\nX{fmt(p[0][0])}Y{fmt(p[0][1])}D02*\n" + "".join(f"X{fmt(x)}Y{fmt(y)}D01*\n" for x, y in p[1:] + p[:1]) + "G37*\n" for p in polys[4:]) + "M02*\n"
    lay = parse_layer(text)
    res = P.build_parts({"top": lay}, [c1])
    src = {p.designator: p.from_file["source"] for p in res.parts}
    assert src == {"C1": "to.c+placement", "C2": "paste only"}
    c = next(p for p in res.parts if p.designator == "C1")
    assert c.from_file["value"] == "100n" and c.footprint == "C_0402_1005Metric" and c.shape == "hull" and len(c.polygon_mm) >= 4
    assert len(res.unmatched) == 2
    fb = P.build_parts({"top": lay}, [c1], proximity_fallback=True)
    assert not fb.unmatched and any(p.from_file.get("grouping") == "proximity" and p.designator == "P1" for p in fb.parts)
    box = P.build_parts({"top": lay}, [c1], shape="box")
    assert next(p for p in box.parts if p.designator == "C1").shape == "box"


def test_no_placement_file_leaves_every_opening_to_the_click():
    """!@brief Without TO.C and without a placement file no part is invented: the openings are returned, the click makes a part of the largest one under the point."""
    lay, _ = layer_of([part("C1", "C_0402_1005Metric", 0, 0, 0)])
    res = P.build_parts({"top": lay})
    assert not res.parts and len(res.unmatched) == 2
    i = P.opening_at(res.openings, res.openings[0].x, res.openings[0].y)
    h = P.part_from_openings("H1", [res.openings[i]])
    assert h.designator == "H1" and h.shape == "hull" and h.from_file["source"] == "paste only" and h.side == "top"


# ------------------------------------------------------------------------------------------------------------------------------ ImportPart and the merge
def test_import_part_from_file_is_written_only_when_not_empty_and_unknown_keys_survive():
    """!@brief `from_file` is omitted when empty (a format-2 file without file data is byte-identical), round-trips when set, and a key of a later version is kept."""
    p = ImportPart("U1", "hull", [[0, 0], [1, 0], [1, 1]], 0.5, {"role": "Source"}, "SOIC", "top")
    assert "from_file" not in p.to_dict()
    p.from_file = {"value": "MCU", "source": "x3", "height_mm": 1.2}
    d = json.loads(json.dumps(p.to_dict()))
    q = ImportPart.from_dict(d)
    assert q.from_file == p.from_file and q.edits == {"role": "Source"} and q.extra == {}
    d["future"] = {"a": 1}
    r = ImportPart.from_dict(d)
    assert r.extra == {"future": {"a": 1}} and r.to_dict()["future"] == {"a": 1} and r.from_file == p.from_file


def test_merge_keeps_edits_and_power_rewrites_from_file_and_keeps_orphans_off():
    """!@brief A re-import: same designator keeps power and `edits`, takes the new `from_file` and polygon; the user's shape is applied to the new openings; a missing part is an orphan until removed."""
    old = [ImportPart("C1", "box", [[0, 0], [1, 0], [1, 1], [0, 1]], 0.4, {"shape_user": True, "tj_max": 90}, "", "top", {"value": "old"}),
           ImportPart("C2", "hull", [[5, 5], [6, 5], [6, 6]], 0.1, {}, "", "top", {"value": "gone"}),
           ImportPart("C3", "hull", [[9, 9], [10, 9], [10, 10]], 0.0, {}, "", "top", {})]
    new_poly = [[0.5, 0], [2, 0], [2, 1]]
    new = [ImportPart("C1", "hull", new_poly, 0.0, {}, "", "top", {"value": "new", "source": "x3"}),
           ImportPart("C9", "hull", new_poly, 0.0, {}, "", "top", {"source": "x3"})]
    shapes = {"C1": {"box": [(0.5, 0), (2, 0), (2, 1), (0.5, 1)], "hull": new_poly}}
    m = P.merge_parts(old, new, shapes, remove=["C3"])
    by = {p.designator: p for p in m.parts}
    assert set(by) == {"C1", "C9", "C2"} and m.orphans == ["C2"]
    c1 = by["C1"]
    assert c1.power == 0.4 and c1.edits == {"shape_user": True, "tj_max": 90} and c1.from_file["value"] == "new"
    assert c1.shape == "box" and c1.polygon_mm[0] == [0.5, 0.0] and len(c1.polygon_mm) == 4         # the user's box, on the new openings
    assert by["C2"].from_file["orphan"] is True and by["C2"].power == 0.1 and by["C2"].from_file["value"] == "gone"
    rows = {r["ref"]: r for r in P.diff_parts(old, new)}
    assert rows["C9"]["change"] == "new" and rows["C2"]["change"] == "removed" and "moved" in rows["C1"]["change"]


def test_sha256_of_a_file(tmp_path):
    """!@brief The hash of a file is the SHA-256 of its bytes."""
    f = tmp_path / "a.gbr"
    f.write_bytes(b"abc")
    assert P.sha256_of(f) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


# ------------------------------------------------------------------------------------------------------------------------------ the real boards of the research
needs_data = pytest.mark.skipif(not (DATA / "rp2040" / "pos.csv").exists(), reason="the git-ignored research boards are not in " + str(DATA))


def real_counts(name, bottom="as is"):
    """!
    @brief The counts of one real board: parts with an opening, openings, and the openings against the `TO.C` truth.
    @param name Board folder.
    @param bottom "as is" or "auto" (the convention detected from the openings).
    @return dict parts, matched, openings, ok, wrong, missed (None when the paste has no TO.C), convention.
    """
    folder = DATA / name
    placement = P.read_placement(folder / "pos.csv")
    ops, truth = [], []
    for side, fn in (("top", "pasteF.gbr"), ("bottom", "pasteB.gbr")):
        if (folder / fn).exists():
            lay = read_layer(folder / fn)
            o = P.read_openings(lay, side, by_ref=False)
            ops += o
            boxes = [(lay.attrs(i).ref, lay.op_boxes()[i]) for i, op in enumerate(lay.ops) if op[1] and lay.attrs(i).ref]
            for q in o:
                c = [(n, b) for n, b in boxes if b[0] - 0.03 <= q.x <= b[2] + 0.03 and b[1] - 0.03 <= q.y <= b[3] + 0.03]
                truth.append(min(c, key=lambda t: (t[1][2] - t[1][0]) * (t[1][3] - t[1][1]))[0] if c else None)
    conv = P.bottom_convention(placement, ops)[0] if bottom == "auto" else "as is"
    byref, bypad = P.match_envelope(P.apply_bottom_convention(placement, conv), ops)
    out = dict(parts=len(placement), matched=len(byref), openings=len(ops), convention=conv, ok=None, wrong=None, missed=None)
    if any(truth):
        ok = sum(1 for i, r in bypad.items() if truth[i] == r)
        wrong = sum(1 for i, r in bypad.items() if truth[i] not in (None, r))
        out.update(ok=ok, wrong=wrong, missed=sum(1 for t in truth if t) - ok - wrong)
    return out


@needs_data
@pytest.mark.parametrize("name, parts, matched, openings, counts", [
    ("rp2040", 30, 27, 129, None),
    ("cmm2", 101, 99, 494, (453, 9, 32)),
    ("oswlight", 43, 43, 206, (126, 0, 80)),
])
def test_real_boards_reproduce_the_research_counts(name, parts, matched, openings, counts):
    """!@brief The envelope rule on three real boards gives the counts of the research (RP2040 27 of 30, cmm2 99 of 101 with 453 / 9 / 32, oswlight 43 of 43 with 126 / 0 / 80)."""
    r = real_counts(name)
    assert (r["parts"], r["matched"], r["openings"]) == (parts, matched, openings)
    if counts:
        assert (r["ok"], r["wrong"], r["missed"]) == counts


@needs_data
@pytest.mark.skipif(not (DATA / "isastm" / "pos.csv").exists(), reason="isastm not present")
def test_isastm_needs_the_bottom_convention_detected_from_the_openings():
    """!@brief isastm writes the bottom X negated: as written 130 of 134 parts and 738 / 0 / 34; with the detected convention 133 and 744 / 0 / 28; cmm2 of the same author is "as is"."""
    a = real_counts("isastm")
    assert (a["matched"], a["ok"], a["wrong"], a["missed"]) == (130, 738, 0, 34)
    b = real_counts("isastm", bottom="auto")
    assert b["convention"] == "negated X" and (b["parts"], b["matched"], b["openings"], b["ok"], b["wrong"], b["missed"]) == (134, 133, 772, 744, 0, 28)
    assert real_counts("cmm2", bottom="auto")["convention"] == "as is"


@needs_data
def test_real_board_build_parts_by_to_c_and_by_position_and_a_shifted_placement_file():
    """!@brief `build_parts` on cmm2: sources by `TO.C` agree with the envelope rule's source tags, and a placement file moved by 3 mm is flagged by the frame check with the opposite offset."""
    folder = DATA / "cmm2"
    placement = P.read_placement(folder / "pos.csv")
    layers = {"top": read_layer(folder / "pasteF.gbr"), "bottom": read_layer(folder / "pasteB.gbr")}
    res = P.build_parts(layers, placement)
    srcs = [p.from_file["source"] for p in res.parts]
    assert set(srcs) <= {"to.c+placement", "paste only"}                     # cmm2's paste carries TO.C
    assert srcs.count("to.c+placement") >= 90
    # The same layers without their TO.C designators: the envelope rule, 99 of 101 parts
    res2 = P.build_parts(layers, placement, use_refs=False)
    assert len(res2.parts) == 99 and {p.from_file["source"] for p in res2.parts} == {"placement by position"}
    assert len(res2.listed) == 2 and len(res2.openings) == 494
    shifted = P.apply_offset(placement, 3.0, -2.0)
    res3 = P.build_parts(layers, shifted, use_refs=False)
    assert res3.info["frame"]["propose"] and (res3.info["frame"]["dx"], res3.info["frame"]["dy"]) == pytest.approx((-3.0, 2.0), abs=0.15)
