"""!
@file test_inner_copper.py
@brief Inner copper weight of the typical stack-up templates: 0.5 oz (15.2 um, default, unchanged) and 1 oz (35 um, derived).
"""

import copy
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.model import load_stackup_templates, stackup_template
from pcbthermal.project import Project, load_project, save_project

# Board thickness of the 1 oz variant in um: the shipped total plus (35 - 15.2) um per inner layer (research/stackup README 4.5 and 4.6)
TOTALS_1OZ = {4: 1625.8, 6: 1679.2, 8: 1718.9, 10: 2158.4, 12: 2598.1}


def _gap_um(d):
    """!
    @brief Thickness of one template dielectric entry.
    @param d Entry (a single sheet or a list of sheets).
    @return Thickness in um.
    """
    return sum(s["thickness_um"] for s in d["sheets"]) if "sheets" in d else d["thickness_um"]


def _planes_board(n, oz):
    """!
    @brief The example board reshaped to n layers with a full plane on every inner layer and the template of the given inner copper weight.
    @param n Number of copper layers.
    @param oz Inner copper weight (0.5 or 1).
    @return Problem.
    """
    p = example_board()
    top = [z for z in p.zones if z.layer == 0]
    bottom = [z for z in p.zones if z.layer == 3]
    plane = copy.deepcopy([z for z in p.zones if z.layer == 1][0])
    for z in bottom:
        z.layer = n - 1                                     # The bottom plane goes to the last layer (it was lost on boards of more than 4 layers in an earlier study)
    inner = []
    for l in range(1, n - 1):
        z = copy.deepcopy(plane)
        z.layer = l
        inner.append(z)
    p.zones = top + bottom + inner
    p.board.layers = n
    for s in p.heatsinks:
        s.layer = 0 if s.layer == 0 else n - 1
    p.board.dielectrics = []
    p.board.template_inner_oz = oz
    p.board.apply_template()
    return p


def test_default_is_the_shipped_template_unchanged():
    for n in range(1, 13):
        assert stackup_template(n) == stackup_template(n, inner_oz=0.5)
    assert "derived" not in stackup_template(4)
    assert stackup_template(4)["copper_um"] == [35, 15.2, 15.2, 35]


def test_one_oz_variant_keeps_the_dielectrics():
    for n, total in TOTALS_1OZ.items():
        base, v = stackup_template(n), stackup_template(n, inner_oz=1)
        assert v["copper_um"] == [35] * n and len(v["dielectrics"]) == n - 1
        assert v["dielectrics"] == base["dielectrics"]                                   # Every dielectric of the template unchanged
        assert v["total_thickness_um"] == pytest.approx(base["total_thickness_um"] + (35 - 15.2) * (n - 2))
        assert v["total_thickness_um"] == pytest.approx(total, abs=0.05)
        assert sum(v["copper_um"]) + sum(_gap_um(d) for d in v["dielectrics"]) == pytest.approx(v["total_thickness_um"])    # The layers add up
        assert v["derived"] and "not a fabricator" in v["name"] and "dielectric_scale" not in v
    assert "JLC04161H" in stackup_template(4)["name"] and "derived" in stackup_template(4, inner_oz=1)["name"]
    # Fewer than three layers have no inner copper, and an unlisted count (5) is derived the same way
    assert stackup_template(2, inner_oz=1) == stackup_template(2)
    assert stackup_template(5, inner_oz=1)["copper_um"] == [35] * 5
    with pytest.raises(ValueError):
        stackup_template(4, inner_oz=2)


def test_board_applies_the_variant(tmp_path):
    b = Problem.new(50, 50, 6).board
    b.make_advanced()
    b.apply_template()
    t0 = b.total_thickness()
    cu0, d0 = list(b.copper_thickness), [d.thickness for d in b.dielectrics]
    b.template_inner_oz = 1.0
    b.apply_template()
    assert len(b.dielectrics) == 5 and [d.thickness for d in b.dielectrics] == pytest.approx(d0)
    assert b.total_thickness() == pytest.approx(t0 + 4 * 19.8e-6) and b.thickness == pytest.approx(b.total_thickness())
    assert b.copper_thickness == pytest.approx([35e-6] * 6) and cu0[1] == pytest.approx(15.2e-6)
    b.template_inner_oz = 0.5
    b.apply_template()
    assert b.copper_thickness == pytest.approx(cu0) and b.total_thickness() == pytest.approx(t0)   # Going back restores the default exactly


def test_json_round_trip_and_old_files(tmp_path):
    p = Problem.new(50, 50, 4)
    p.board.make_advanced()
    path = str(tmp_path / "default.pcbt.json")
    save_project(path, Project(p))
    with open(path) as fh:
        assert "template_inner_oz" not in fh.read()                  # The default is not written: saved files stay identical
    assert load_project(path).problem.board.template_inner_oz == 0.5  # A file without the key loads as before
    p.board.template_inner_oz = 1.0
    p.board.apply_template()
    path2 = str(tmp_path / "oz1.pcbt.json")
    save_project(path2, Project(p))
    q = load_project(path2).problem.board
    assert q.template_inner_oz == 1.0 and q.copper_thickness == pytest.approx([35e-6] * 4)
    p.board.template_inner_oz = 3.0
    with pytest.raises(ValueError):
        p.validate()


def test_user_template_file_keeps_working(tmp_path):
    data = copy.deepcopy(load_stackup_templates())
    data["templates"]["4"]["name"] = "my 4 layers"
    path = tmp_path / "stackups.json"
    path.write_text(json.dumps(data))
    t = stackup_template(4, str(path), inner_oz=1)
    assert t["name"].startswith("my 4 layers") and t["copper_um"] == [35] * 4


def test_sheets_and_three_layers(tmp_path):
    # A gap of several sheets keeps its sheets; the Board combines them into one gap of the same thickness
    data = copy.deepcopy(load_stackup_templates())
    t4 = data["templates"]["4"]
    core = t4["dielectrics"][1]["thickness_um"]
    t4["dielectrics"][1] = {"kind": "core", "sheets": [{"thickness_um": core - 300.0, "material": "FR-4 (standard)"},
                                                       {"thickness_um": 300.0, "material": "FR-4 (standard)"}]}
    path = tmp_path / "stackups.json"
    path.write_text(json.dumps(data))
    base, v = stackup_template(4, str(path)), stackup_template(4, str(path), inner_oz=1)
    assert v["dielectrics"] == base["dielectrics"]
    b = Problem.new(50, 50, 4).board
    b.make_advanced()
    b.template_inner_oz = 1.0
    b.apply_template(str(path))
    assert b.dielectrics[1].thickness == pytest.approx(core * 1e-6) and b.total_thickness() == pytest.approx(v["total_thickness_um"] * 1e-6)
    # Three layers (generic template) have one inner layer: it is changed as well
    t3 = stackup_template(3, inner_oz=1)
    assert t3["copper_um"] == [35.0] * 3 and t3["derived"]
    assert t3["total_thickness_um"] == pytest.approx(stackup_template(3)["total_thickness_um"] + 19.8)


@pytest.mark.parametrize("n", [4, 6])
def test_one_oz_inner_planes_cool_the_example_board(n):
    opt = SolverOptions(models=("fvm",), cell_mm=4.0)                 # A coarse cell: only the difference between the two variants matters
    t05 = simulate(_planes_board(n, 0.5), opt).results["fvm"].t_max
    t10 = simulate(_planes_board(n, 1.0), opt).results["fvm"].t_max
    assert 5.0 < t05 - t10 < 10.0                                     # The study has 6.9 K (4 layers) and 7.5 K (6 layers) at 2 mm
