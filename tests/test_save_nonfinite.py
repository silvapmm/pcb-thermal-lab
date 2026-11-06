#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_save_nonfinite.py
@brief A project that opens can always be saved and reopened: huge coordinates are refused at the loading boundary and the writer never emits Infinity or NaN.
@details The defect: a polygon coordinate of 1e308 mm was finite, so the project opened, but the conversion to metres and back (x 1000 on saving) overflowed
         to infinity, the file got `Infinity` and was refused on reopening. Three layers are tested: the loader (a clear ProjectFormatError naming the key
         path), the writer (a ValueError before the file is touched) and a property check (random magnitudes up to the bound: save, load, save is stable).
"""

import copy
import json
import os

import numpy as np
import pytest

from pcbthermal.fileschema import MAX_COORD_MM
from pcbthermal.examples import example_board
from pcbthermal.project import Project, ProjectFormatError, load_project, project_from_dict, project_to_dict, save_project

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _example_dict():
    """!
    @brief The example board as a project dict.
    @return dict.
    """
    return project_to_dict(Project(problem=example_board()))


@pytest.mark.parametrize("section", ["zones", "heaters"])
@pytest.mark.parametrize("value", [1e308, 1e7, -1e308, 2 * MAX_COORD_MM])
def test_huge_polygon_coordinate_is_refused_with_its_path(section, value):
    """!
    @brief A polygon coordinate beyond the bound is refused, naming the key path.
    @param section Key of the list.
    @param value Coordinate in mm.
    @return None.
    """
    d = _example_dict()
    d[section][0]["polygon_mm"][0][0] = value
    with pytest.raises(ProjectFormatError, match=rf"{section}\[0\]\.polygon_mm\[0\]"):
        project_from_dict(d)


@pytest.mark.parametrize("where", [("board", "width_mm"), ("vias", "x_mm")])
def test_huge_scalar_length_is_refused(where):
    """!
    @brief A board size or via position beyond the bound is refused.
    @param where Section and key.
    @return None.
    """
    d = _example_dict()
    target = d[where[0]] if where[0] == "board" else d[where[0]][0]
    target[where[1]] = 1e308
    with pytest.raises(ProjectFormatError, match=where[1]):
        project_from_dict(d)


def test_huge_other_number_is_refused():
    """!
    @brief A power of 1e300 W is refused (it would overflow later products).
    @return None.
    """
    d = _example_dict()
    d["heaters"][0]["power_w"] = 1e300
    with pytest.raises(ProjectFormatError, match="power_w"):
        project_from_dict(d)


def test_writer_refuses_non_finite_and_keeps_the_old_file(tmp_path):
    """!
    @brief A project that holds infinity fails before the write and the file on disk is untouched.
    @param tmp_path Temporary folder.
    @return None.
    """
    path = str(tmp_path / "a.pcbt.json")
    proj = Project(problem=example_board())
    save_project(path, proj)
    before = open(path, encoding="utf-8").read()
    proj.problem.zones[0].polygon[0][0] = np.inf
    with pytest.raises(ValueError, match="not a finite number"):
        save_project(path, proj)
    assert open(path, encoding="utf-8").read() == before
    assert not [f for f in os.listdir(tmp_path) if f != "a.pcbt.json"]


def test_written_files_never_contain_infinity_or_nan(tmp_path):
    """!
    @brief The saved text of every example is strict JSON.
    @param tmp_path Temporary folder.
    @return None.
    """
    for f in os.listdir(os.path.join(ROOT, "examples")):
        if f.endswith(".pcbt.json"):
            path = str(tmp_path / f)
            save_project(path, load_project(os.path.join(ROOT, "examples", f)))
            json.loads(open(path, encoding="utf-8").read(), parse_constant=lambda c: pytest.fail(f"{c} written"))


def test_random_magnitudes_up_to_the_bound_save_load_save_is_stable(tmp_path):
    """!
    @brief Property check: for random coordinates up to the bound, what opens can be saved, reopened and saved again with the same text.
    @param tmp_path Temporary folder.
    @return None.
    """
    rng = np.random.default_rng(20261106)
    base = _example_dict()
    for i in range(40):
        d = copy.deepcopy(base)
        mag = 10.0 ** rng.uniform(-6, np.log10(MAX_COORD_MM))     # Log-uniform magnitudes from a nanometre to the bound
        pt = d["zones"][0]["polygon_mm"][0]
        pt[0] = float(rng.choice([-1, 1]) * mag)
        pt[1] = float(rng.choice([-1, 1]) * mag * rng.uniform(0, 1))
        d["board"]["width_mm"] = float(max(d["board"]["width_mm"], mag))
        try:
            proj = project_from_dict(d, validate=False)
        except ProjectFormatError:
            pytest.fail(f"a coordinate within the bound was refused: {mag}")
        a, b = str(tmp_path / f"a{i}.json"), str(tmp_path / f"b{i}.json")
        save_project(a, proj)
        save_project(b, load_project(a))
        assert open(a, encoding="utf-8").read() == open(b, encoding="utf-8").read()


def test_a_gui_edit_that_makes_a_value_non_finite_or_absurd_is_undone(qtbot):
    """!
    @brief Document.edit refuses a result with an infinite, NaN or beyond-the-bound coordinate and leaves the project as it was (no undo step).
    @param qtbot pytest-qt fixture.
    @return None.
    """
    from pcbthermal.gui.document import Document
    doc = Document(Project(problem=example_board()))
    before = doc.snapshot()
    n = doc.stack.count()
    for bad in (np.inf, np.nan, 1e303, 2e3):          # 2e3 m is 2e6 mm, above the bound
        doc.set_props("heater", 0, polygon=np.asarray(doc.problem.heaters[0].polygon) + bad)
        assert doc.snapshot() == before and doc.stack.count() == n
    doc.move([("heater", 0)], 1e300, 0.0)                # The drag is clipped to the board: a legitimate edit, and the result can be saved and reopened
    project_from_dict(doc.snapshot())
    doc.stack.undo()
    assert doc.snapshot() == before
    n = doc.stack.count()
    doc.set_props("heater", 0, power=3.0)               # An ordinary edit still works
    assert doc.problem.heaters[0].power == 3.0 and doc.stack.count() == n + 1
