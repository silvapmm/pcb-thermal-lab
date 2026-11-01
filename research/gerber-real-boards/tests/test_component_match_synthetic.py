#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_component_match_synthetic.py
@brief Tests of the envelope rule of `lib/component_match.py` on synthetic boards whose answer is known (added by the review): rotations by 0, 90, 180, 270 and 45 degrees, pads far from the origin,
       the smallest envelope winning, the bottom-side X convention detected from the openings, and two limits kept as markers (an origin offset of the placement file, a part missing from it).
@details The openings are placed from the KiCad library pad positions of each footprint (from memory, M: C_0402_1005Metric pads at +-0.48 mm, C_0603_1608Metric at +-0.775 mm,
         SOIC-8_3.9x4.9mm_P1.27mm at x +-2.475 mm and y +-0.635, +-1.905 mm, SOT-223-3_TabPin2 pins at x -3.15 mm, y -2.3, 0, 2.3 mm and the tab at x +3.15 mm), not from the envelope table of the rule,
         so the test is not circular. Rotation: counter-clockwise positive, Y up (the KiCad position file and the Gerber frame). No data folder is needed.
         Run: `.venv/bin/python -m pytest -q research/gerber-real-boards/tests/test_component_match_synthetic.py`.
"""

import math

import component_match as cm

## Local pad centres (mm) of the footprints, KiCad library (memory).
PADS = {
    "C_0402_1005Metric": [(-0.48, 0.0), (0.48, 0.0)],
    "C_0603_1608Metric": [(-0.775, 0.0), (0.775, 0.0)],
    "SOIC-8_3.9x4.9mm_P1.27mm": [(sx * 2.475, y) for sx in (-1, 1) for y in (-1.905, -0.635, 0.635, 1.905)],
    "SOT-223-3_TabPin2": [(-3.15, -2.3), (-3.15, 0.0), (-3.15, 2.3), (3.15, 0.0)],
}


def part(ref, package, x, y, rot, side="top"):
    """!
    @brief A part of a placement file.
    @param ref designator
    @param package footprint name
    @param x X of the origin in mm
    @param y Y of the origin in mm
    @param rot rotation in degrees, counter-clockwise
    @param side top or bottom
    @return dict as read by pnp.read_placement
    """
    return dict(ref=ref, package=package, value="", x=x, y=y, rot=rot, side=side)


def openings(p, mirror=False):
    """!
    @brief The paste openings of a part on the board, with the designator they belong to (the known answer).
    @param p part dict (its true position)
    @param mirror True: the footprint is mirrored in X (a bottom-side part seen from the top)
    @return list of opening dicts (x, y, side, truth)
    """
    a = math.radians(p["rot"])
    out = []
    for u, v in PADS[p["package"]]:
        u = -u if mirror else u
        out.append(dict(x=p["x"] + u * math.cos(a) - v * math.sin(a), y=p["y"] + u * math.sin(a) + v * math.cos(a), side=p["side"], truth=p["ref"]))
    return out


def score(parts, pads, tol=0.3):
    """!
    @brief Run the rule and compare with the known answer.
    @param parts placement as the file writes it
    @param pads openings with their truth
    @param tol tolerance of the envelope in mm
    @return tuple (correct, wrong, unassigned)
    """
    _, bypad = cm.improved_match(parts, pads, tol=tol)
    ok = sum(1 for i, r in bypad.items() if pads[i]["truth"] == r)
    return ok, len(bypad) - ok, len(pads) - len(bypad)


def test_two_pad_parts_at_every_quarter_turn_and_at_45_degrees():
    # Five passives 1.6 mm apart (closer than the 0.6 mm link of the prototype would keep apart once grown): each opening to its own part
    parts = [part(f"C{i}", "C_0402_1005Metric", 1.6 * i, 0.0, rot) for i, rot in enumerate((0, 90, 180, 270))] + [part("C9", "C_0603_1608Metric", 8.0, 0.0, 45)]
    pads = [q for p in parts for q in openings(p)]
    assert score(parts, pads) == (len(pads), 0, 0)


def test_pads_far_from_the_origin_and_the_smallest_envelope_wins():
    # SOIC-8 at 90 degrees and SOT-223 at 270: the pads are 2.5 to 3.2 mm from the origin (the prototype's 0.8 mm pick missed both on the RP2040 board);
    # a 0402 under the SOIC body sits inside the SOIC envelope and must keep its own two openings
    parts = [part("U2", "SOIC-8_3.9x4.9mm_P1.27mm", 10.0, 10.0, 90), part("U1", "SOT-223-3_TabPin2", 25.0, 10.0, 270), part("C5", "C_0402_1005Metric", 10.0, 10.0, 0)]
    pads = [q for p in parts for q in openings(p)]
    assert score(parts, pads) == (14, 0, 0)


def test_the_sign_of_the_rotation_matters_only_off_the_quarter_turns():
    # Centred envelopes are symmetric: a file that writes the rotation with the other sign changes nothing at 0, 90, 180, 270 degrees...
    quarter = [part(f"C{i}", "C_0402_1005Metric", 2.0 * i, 0.0, rot) for i, rot in enumerate((0, 90, 180, 270))]
    pads = [q for p in quarter for q in openings(p)]
    assert score([dict(p, rot=-p["rot"]) for p in quarter], pads) == (8, 0, 0)
    # ...but at 45 degrees the envelope lies across the pads (the one 45-degree 0603 of cmm2 loses its two openings the same way)
    c45 = [part("C9", "C_0603_1608Metric", 0.0, 0.0, 45)]
    pads45 = openings(c45[0])
    assert score(c45, pads45, tol=0.2) == (2, 0, 0)
    assert score([dict(c45[0], rot=-45)], pads45, tol=0.2) == (0, 0, 2)


def test_the_bottom_x_convention_is_detected_from_the_openings():
    # Bottom-side parts, mirrored footprints; one file writes the board X (cmm2), the other the negated X (isastm)
    true = [part("C1", "C_0402_1005Metric", 30.0, -40.0, 90, "bottom"), part("C2", "C_0402_1005Metric", 34.0, -49.0, 180, "bottom"),
            part("U3", "SOIC-8_3.9x4.9mm_P1.27mm", 40.0, -45.0, 0, "bottom")]
    pads = [q for p in true for q in openings(p, mirror=True)]
    conv, n_as, n_neg = cm.bottom_convention(true, pads)
    assert conv == "as is" and n_as == len(pads) and n_neg == 0
    negated = [dict(p, x=-p["x"]) for p in true]
    conv, n_as, n_neg = cm.bottom_convention(negated, pads)
    assert conv == "negated X" and n_as == 0 and n_neg == len(pads)
    assert score(cm.apply_bottom_convention(negated, conv), pads) == (len(pads), 0, 0)
    # Read as written, the negated file finds nothing on the bottom (the 6 isastm openings of C13, C17 and C36)
    assert score(negated, pads) == (0, 0, len(pads))


def test_limit_an_origin_offset_gives_wrong_designators_silently():
    # A row of 0402 at a 2 mm pitch and a placement file whose origin is 2 mm off in X: every opening goes to the neighbour, and the
    # rule cannot tell (registration of the placement file against the openings is needed, INTEGRATION 11)
    parts = [part(f"R{i}", "C_0402_1005Metric", 2.0 * i, 0.0, 0) for i in range(1, 6)]
    pads = [q for p in parts for q in openings(p)]
    ok, wrong, unassigned = score([dict(p, x=p["x"] + 2.0) for p in parts], pads)
    assert ok == 0 and wrong == 8 and unassigned == 2
    # Up to about half a pad pitch the tolerance absorbs it
    assert score([dict(p, x=p["x"] + 0.2) for p in parts], pads) == (10, 0, 0)


def test_limit_a_part_missing_from_the_placement_file_is_taken_by_a_neighbour():
    # The cmm2 case (J8 is in the paste but not in pos.csv; 9 of its openings went to the TSOP U2): an opening of an unlisted part that falls in a
    # listed envelope is taken by it. Kept as a marker of the limit; the proposal is to leave an opening unassigned when it is outside the pad
    # pattern of the part (a footprint library), which the name table cannot do
    soic = part("U2", "SOIC-8_3.9x4.9mm_P1.27mm", 0.0, 0.0, 0)
    missing = part("J8", "C_0402_1005Metric", 0.0, 2.45, 0)
    pads = openings(soic) + openings(missing)
    ok, wrong, unassigned = score([soic], pads)
    assert ok == 8 and wrong == 2 and unassigned == 0
