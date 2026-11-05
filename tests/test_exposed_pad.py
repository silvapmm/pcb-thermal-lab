#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_exposed_pad.py
@brief Tests of the exposed-pad heat source of an imported part (`parts.dominant_group`, the default shape 'auto', the X3 order, the re-import, the project file) and of its place in the
       import window (the radio, the dashed hull, the Source column).
@details The rule and its numbers are those of research/gerber-real-boards/docs/heater-shape-opinion.md section 6, measured on eleven parts of three open boards (RP2040 minimal design,
         ISASTM, CMM2; set `PCBT_REAL_BOARDS` to the folder of the boards for the tests that need them), not on a physical board.
         Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_exposed_pad.py`.
"""

import json
import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from pcbthermal.gerber import components as xc
from pcbthermal.gerber import parts as P
from pcbthermal.gerber import read_layer
from pcbthermal.model import ImportPart
from tests.test_gerber_parts import DATA, needs_data, polygon_area


def box_op(cx, cy, w, h, side="top"):
    """!
    @brief An opening that is a rectangle.
    @param cx Centre X (mm).
    @param cy Centre Y (mm).
    @param w Width (mm).
    @param h Height (mm).
    @param side "top" or "bottom".
    @return Opening.
    """
    hull = [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]
    return P.Opening(cx, cy, w * h, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), hull, side)


def qfn_openings(ep_windows=True):
    """!
    @brief The paste of a QFN-24: 24 pins of 0.25 x 0.8 mm at a pitch of 0.5 mm and an exposed pad of 2.6 mm as 2 x 2 windows of 1.1 mm (or none).
    @param ep_windows True: with the four windows.
    @return list of Opening.
    """
    ops = []
    for k in range(6):
        o = (k - 2.5) * 0.5
        ops += [box_op(o, 2.0, 0.25, 0.8), box_op(o, -2.0, 0.25, 0.8), box_op(2.0, o, 0.8, 0.25), box_op(-2.0, o, 0.8, 0.25)]
    if ep_windows:
        ops += [box_op(sx * 0.65, sy * 0.65, 1.1, 1.1) for sx in (-1, 1) for sy in (-1, 1)]
    return ops


def ring_part(n_small, small_area=0.4, big=1.0):
    """!
    @brief A square pad of `big` mm2 in the centre and `n_small` small pads on a ring of 3 mm radius (to set the paste share of the dominant group).
    @param n_small Number of small pads.
    @param small_area Area of each small pad (mm2).
    @param big Area of the central pad (mm2).
    @return list of Opening.
    """
    s = math.sqrt(big)
    ops = [box_op(0.0, 0.0, s, s)]
    w = math.sqrt(small_area)
    for k in range(n_small):
        a = 2 * math.pi * k / n_small
        ops.append(box_op(3 * math.cos(a), 3 * math.sin(a), w, w))
    return ops


def test_the_exposed_pad_of_a_synthetic_qfn_is_the_default_shape_and_the_hull_stays_elsewhere():
    """!@brief A QFN with its pad in four windows gets the hull of the four windows; a SOIC-8, a 0402 pair, a crystal pair, a USB micro-B pattern and a QFN without a pad keep the hull; a SOT-223 gets its tab."""
    qfn = qfn_openings()
    assert len(P.dominant_group(qfn)) == 4 and P.default_shape_kind(qfn) == "exposed"
    ep = P.shape_polygon(qfn, "auto")
    assert polygon_area(ep) == pytest.approx(2.4 ** 2, rel=1e-6) and polygon_area(P.shape_polygon(qfn, "hull")) > 3 * polygon_area(ep)
    assert P.shape_polygon(qfn, "exposed") == ep
    assert P.default_shape_kind(qfn_openings(ep_windows=False)) == "hull"
    soic = [box_op(sx * 2.475, y, 1.95, 0.6) for sx in (-1, 1) for y in (-1.905, -0.635, 0.635, 1.905)]
    pair0402 = [box_op(-0.48, 0, 0.5, 0.55), box_op(0.48, 0, 0.5, 0.55)]
    crystal = [box_op(-4.8, 0, 3.0, 3.9), box_op(4.8, 0, 3.0, 3.9)]
    # Six mounting pads that hold most of the paste but span the whole part, and five small pins: the hull ratio holds them out
    usb = [box_op(x, y, 1.5, 1.5) for x in (-5.0, 0.0, 5.0) for y in (-2.0, 2.0)] + [box_op(k * 0.65, 3.5, 0.4, 1.3) for k in range(-2, 3)]
    for name, ops in (("soic", soic), ("0402", pair0402), ("crystal", crystal), ("usb", usb)):
        assert P.dominant_group(ops) == [], name
        assert P.shape_polygon(ops, "auto") == P.shape_polygon(ops, "hull"), name
    sot = [box_op(-3.15, y, 1.0, 2.0) for y in (-2.3, 0.0, 2.3)] + [box_op(3.15, 0.0, 3.0, 3.3)]
    assert P.dominant_group(sot) == [sot[-1]] and P.default_shape_kind(sot) == "exposed"
    assert polygon_area(P.shape_polygon(sot, "auto")) == pytest.approx(3.0 * 3.3)
    assert P.default_shape_kind([box_op(0, 0, 1, 1)]) == "hull" and P.shape_polygon([], "auto") == []


def test_the_thresholds_of_the_exposed_pad_rule_are_held():
    """!@brief A paste share of 0.24 stays hull and 0.26 is exposed (the 0.25 line); an opening at 0.49 of the largest stays out of the group and at 0.51 is in (then all join: no pad); the constants are the opinion's."""
    assert (P.EXPOSED_MIN_AREA, P.EXPOSED_MIN_PASTE, P.EXPOSED_MAX_HULL) == (0.5, 0.25, 0.5)
    assert P.default_shape_kind(ring_part(8)) == "hull"          # 1.0 / (1.0 + 8 * 0.4) = 0.238
    assert P.default_shape_kind(ring_part(7)) == "exposed"       # 1.0 / (1.0 + 7 * 0.4) = 0.263
    assert len(P.dominant_group(ring_part(5, small_area=0.49))) == 1       # share 1.0 / 3.45 = 0.29
    assert P.dominant_group(ring_part(5, small_area=0.51)) == []
    # The hull ratio: a pad group spanning more than half of the part is not an exposed pad
    wide = [box_op(-4, 0, 2, 2), box_op(4, 0, 2, 2)] + [box_op(0, 1.0 + 0.1 * k, 0.5, 0.5) for k in range(2)]
    assert P.dominant_group(wide) == []


## The classification of the eleven parts of the study, from three open KiCad boards. U3 is the thin one: its paste share is 0.32 against the line of 0.25.
ELEVEN = {("rp2040", "U3"): "exposed", ("rp2040", "U1"): "exposed", ("isastm", "U5"): "exposed", ("isastm", "U15"): "exposed", ("cmm2", "U4"): "exposed",
          ("rp2040", "U2"): "hull", ("rp2040", "Y1"): "hull", ("rp2040", "R2"): "hull", ("rp2040", "C1"): "hull", ("rp2040", "J3"): "hull", ("isastm", "U14"): "hull"}


def _parts_of(name):
    """!
    @brief `build_parts` on a real board (placement file, both paste layers, the detected bottom convention).
    @param name Board folder in the research data.
    @return PartsResult.
    """
    folder = DATA / name
    layers = {s: read_layer(folder / fn) for s, fn in (("top", "pasteF.gbr"), ("bottom", "pasteB.gbr")) if (folder / fn).exists()}
    return P.build_parts(layers, P.read_placement(folder / "pos.csv"), bottom="auto")


@needs_data
def test_the_rule_classifies_the_eleven_parts_of_the_study():
    """!@brief The eleven parts of the study get the intended shape on the three open boards; of the 27 parts of the RP2040 board only U1 and U3 are exposed; the share of U3 is 0.32 and its group is a tenth of the part."""
    found = {}
    for board in ("rp2040", "isastm", "cmm2"):
        if not (DATA / board / "pos.csv").exists():
            pytest.skip(f"{board} not present")
        res = _parts_of(board)
        for p in res.parts:
            if (board, p.designator) in ELEVEN:
                found[(board, p.designator)] = p.shape
        if board == "rp2040":
            assert sorted(p.designator for p in res.parts if p.shape == "exposed") == ["U1", "U3"] and len(res.parts) == 27
            u3 = next(p for p in res.parts if p.designator == "U3")
            cx, cy = u3.from_file["position_mm"]
            ops = [o for o in res.openings if o.side == u3.side and abs(o.x - cx) < 4.2 and abs(o.y - cy) < 4.2]
            assert len(ops) == 60 and u3.from_file["n_openings"] == 60
            share = sum(o.area for o in P.dominant_group(ops)) / sum(o.area for o in ops)
            ratio = polygon_area(P.shape_polygon(ops, "exposed")) / polygon_area(P.shape_polygon(ops, "hull"))
            assert share == pytest.approx(0.32, abs=0.02) and ratio == pytest.approx(0.1, abs=0.02)
    assert found == ELEVEN


def test_x3_puts_the_exposed_pad_before_the_body_and_keeps_the_order_otherwise():
    """!@brief In an X3 part the exposed pad of the paste comes before Body; without a pad, or with an explicit hull or box, the order is Body, Lead2Lead, paste, ...; the part's shape name is 'exposed'."""
    c = xc.Component("U1", origin=(0.0, 0.0), side="top")
    c.outlines = {"Body": [[(-2.5, -2.5), (2.5, -2.5), (2.5, 2.5), (-2.5, 2.5)]]}
    qfn = qfn_openings()
    part, shapes = P._x3_part(c, qfn, "auto")
    assert part.shape == "exposed" and part.from_file["shape_source"] == "exposed" and polygon_area(part.polygon_mm) == pytest.approx(2.4 ** 2, rel=1e-6)
    assert set(shapes) == {"box", "hull", "exposed"}
    part, _ = P._x3_part(c, qfn, "hull")
    assert part.from_file["shape_source"] == "Body" and part.shape == "outline"
    part, _ = P._x3_part(c, qfn_openings(ep_windows=False), "auto")
    assert part.from_file["shape_source"] == "Body"
    assert xc.heat_polygon(c, None, [(0, 0), (1, 0), (1, 1)])[1] == "exposed"


def test_a_reimport_keeps_the_explicit_shape_and_rederives_only_the_default():
    """!@brief A QFN the user turned to the whole hull keeps it; a QFN left at the proposal follows the rule; a part of a project written before the rule (no `shape_rule`) keeps its stored hull and power."""
    ops = qfn_openings()
    new = P.part_from_openings("U1", ops, "auto", "paste only")
    assert new.shape == "exposed" and new.from_file["shape_rule"] == P.SHAPE_RULE
    shapes = {"U1": P.shape_set(ops)}
    # (1) the user chose the hull on this part
    user = P.part_from_openings("U1", ops, "hull", "paste only")
    user.power, user.edits = 0.5, {"shape_user": True}
    m = {p.designator: p for p in P.merge_parts([user], [new], shapes).parts}["U1"]
    assert m.shape == "hull" and m.power == 0.5 and polygon_area(m.polygon_mm) == pytest.approx(polygon_area(shapes["U1"]["hull"]))
    # (2) the part was at the proposal (written by this version): follows the new polygon
    same = P.part_from_openings("U1", ops, "auto", "paste only")
    same.power = 0.5
    m = {p.designator: p for p in P.merge_parts([same], [new], shapes).parts}["U1"]
    assert m.shape == "exposed" and m.power == 0.5
    # (3) a project written before the rule: no shape_rule, the hull was the default
    old = ImportPart("U1", "hull", [list(map(float, q)) for q in shapes["U1"]["hull"]], 0.7, {}, "", "top", {"source": "to.c+placement"})
    m = {p.designator: p for p in P.merge_parts([old], [new], shapes).parts}["U1"]
    assert m.shape == "hull" and m.power == 0.7 and m.polygon_mm == old.polygon_mm
    assert m.from_file["shape_rule"] == P.SHAPE_RULE                         # the new file data replaced the old, so the next re-import follows the rule


def test_old_part_shapes_load_unchanged_and_a_project_with_an_exposed_part_round_trips(tmp_path):
    """!@brief An ImportPart with shape hull, box, largest or outline is read back as written (no `from_file` is added); a part with the shape 'exposed' round-trips through a project of format 2."""
    from pcbthermal import load_project, save_project
    from pcbthermal.model import ImportRecord, Problem
    from pcbthermal.project import Project
    for kind in ("hull", "box", "largest", "outline", "exposed"):
        p = ImportPart("U1", kind, [[0, 0], [1, 0], [1, 1]], 0.5, {}, "", "top")
        q = ImportPart.from_dict(json.loads(json.dumps(p.to_dict())))
        assert q.shape == kind and q.to_dict() == p.to_dict() and "from_file" not in q.to_dict()
    part = P.part_from_openings("U2", qfn_openings(), "auto", "paste only")
    prob = Problem.new(width_mm=20, height_mm=20, layers=2)
    f = tmp_path / "p.pcbt.json"
    save_project(str(f), Project(problem=prob, imports=[ImportRecord(files=[], parts=[part])]))
    back = load_project(str(f)).imports[0].parts[0]
    assert back.shape == "exposed" and back.polygon_mm == part.polygon_mm and back.from_file["shape_rule"] == P.SHAPE_RULE


def test_an_exposed_pad_heater_reads_hotter_than_the_hull_of_the_part():
    """!@brief Run check: 1 W of the synthetic QFN on a small board with copper under it, FVM at 0.5 mm: the exposed pad reads more than 10 % hotter at the hottest point than the hull of all the openings (the study: +11 to +44 %)."""
    from pcbthermal import Problem, SolverOptions, simulate
    qfn = qfn_openings()
    rise = {}
    for kind in ("exposed", "hull"):
        poly = P.shape_polygon(qfn, kind)
        pr = Problem.new(width_mm=30, height_mm=30, layers=2)
        pr.add_zone(1, rect=(5, 5, 25, 25), fill=1.0)
        pr.add_zone(2, rect=(5, 5, 25, 25), fill=1.0)
        pr.add_heater(1, 1.0, polygon=[[15 + x, 15 + y] for x, y in poly], name="U1")
        sim = simulate(pr, SolverOptions(models=("fvm",), cell_mm=0.5))
        rise[kind] = float(sim.results["fvm"].T.max()) - pr.board.ambient
    assert rise["exposed"] > 1.10 * rise["hull"]


# ---------------------------------------------------------------------------------------------------------------------------------- the import window
def _session(tmp_path):
    """!
    @brief An import session with the synthetic board plus a QFN (U2).
    @param tmp_path Temporary folder.
    @return ImportSession with the parts built.
    """
    from pcbthermal.gui.import_session import ImportSession
    from tests.helpers.synthetic_board import make_board
    sx = ImportSession()
    sx.set_files(make_board(tmp_path / "fab", inner=0, qfn=True))
    sx.load()
    return sx


def test_the_session_proposes_the_pad_and_remembers_only_a_choice_that_differs_from_the_proposal(tmp_path):
    """!@brief U2 (QFN) starts as 'exposed' and offers the exposed radio; U1 (one opening) does not; choosing the hull on the QFN is the user's choice, choosing the pad again is not; the dashed hull is given for the pad only."""
    sx = _session(tmp_path)
    u2, u1 = sx.part("U2"), sx.part("U1")
    assert u2.shape == "exposed" and sx.default_shape(u2) == "exposed" and u1.shape == "hull"
    assert sx.shapes_of(u2) == ["hull", "box", "exposed", "largest"] and sx.shapes_of(u1) == ["hull", "box"]
    assert sx.shape_note(u2) == "exposed pad (proposed)" and sx.shape_note(u1) == "convex hull (proposed)"
    assert sx.part_hull(u2) is not None and sx.part_hull(u1) is None
    assert polygon_area(sx.part_hull(u2)) > 3 * polygon_area(u2.polygon_mm)
    sx.set_shape("U2", "hull")
    assert u2.shape == "hull" and u2.edits["shape_user"] is True and sx.shape_note(u2) == "convex hull (chosen by you)" and sx.part_hull(u2) is None
    sx.set_shape("U2", "exposed")
    assert u2.shape == "exposed" and u2.edits["shape_user"] is False
    sx.set_shape("U1", "hull")
    assert u1.edits["shape_user"] is False


def test_the_parts_page_has_the_exposed_radio_the_dashed_hull_and_the_source_note(qtbot, tmp_path):
    """!@brief Step 2: the QFN row says 'exposed pad (proposed)' in the Source column and its tooltip says why; selecting it checks the 'Exposed pad' radio; the hull radio of a SOT-23-like single pad leaves it disabled; the preview draws."""
    from pcbthermal.gui.import_window import ImportBoardWindow
    from tests.helpers.synthetic_board import make_board
    w = ImportBoardWindow()
    qtbot.addWidget(w)
    w.show()
    w.confirm = lambda *a: True
    w.notify = lambda title, text: pytest.fail(f"{title}: {text}")
    w.open_path(str(make_board(tmp_path / "fab", inner=0, qfn=True)))
    w.go(1)
    pg, sx = w.page2, w.session
    rows = [pg.table.item(r, 1).text() for r in range(pg.table.rowCount())]
    r2 = rows.index("U2")
    src = pg.table.item(r2, 3)
    assert "exposed pad (proposed)" in src.text() and "carries almost all the heat" in src.toolTip()
    assert "exposed" not in pg.table.item(rows.index("U1"), 3).text()
    assert pg.radios["exposed"].toolTip() and "Exposed pad" in pg.radios["exposed"].text()
    pg.table.selectRow(r2)
    assert pg.selected == "U2" and pg.radios["exposed"].isEnabled() and pg.radios["exposed"].isChecked() and "exposed pad or a tab" in pg.suggest.text()
    pg.preview.resize(500, 400)
    assert pg.preview.grab().toImage().width() > 0
    pg.radios["hull"].setChecked(True)
    assert sx.part("U2").shape == "hull" and "chosen by you" in sx.shape_note(sx.part("U2"))
    pg.table.selectRow(rows.index("U1"))
    assert not pg.radios["exposed"].isEnabled() and pg.radios["hull"].isChecked()
    sx.set_part("U2", power=1.0)
    w.go(2)
    assert w.do_import() is True
    assert [h.name for h in w.problem.heaters] == ["U2"]
    assert w.record.parts[[p.designator for p in w.record.parts].index("U2")].shape == "hull"
