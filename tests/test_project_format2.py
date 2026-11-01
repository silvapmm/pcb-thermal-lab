#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_project_format2.py
@brief Project file format 2: written only with imports, nested so that 2.4.x refuses it, .bak before the first migration, newer formats refused.
"""

import copy
import importlib.util
import json
import os
import subprocess
import sys

import pytest

from pcbthermal import __version__
from pcbthermal.examples import example_board
from pcbthermal.model import ImportFile, ImportPart, ImportRecord, ImportedCopper
from pcbthermal.project import (FORMAT_1, FORMAT_2, Project, ProjectFormatError, load_project, project_from_dict, project_to_dict,
                                save_project)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _record():
    """!
    @brief A small import record with every kind of field filled.
    @return ImportRecord.
    """
    return ImportRecord(
        name="boardX",
        files=[ImportFile("top.gtl", 1234, "ab" * 32, "copper"), ImportFile("holes.drl", 99, "cd" * 32, "drill")],
        box_mm=[0.0, 0.0, 40.0, 30.0],
        parts=[ImportPart("U1", "hull", [[1.0, 1.0], [5.0, 1.0], [5.0, 4.0]], 1.5, {"tj_max": 125.0, "use": True})],
        copper=ImportedCopper(0.05, True, [{"name": "F.Cu", "role": "top", "mask": {"kind": "binary", "shape": [2, 2], "data": "eJw="}}]),
        settings={"drill_units": "mm"}, warnings=["a warning"])


def _project(with_imports):
    """!
    @brief The example board as a Project, optionally with one import record.
    @param with_imports True to attach the record.
    @return Project.
    """
    return Project(problem=example_board(), imports=[_record()] if with_imports else [])


def test_format1_unchanged_without_imports(tmp_path):
    """!
    @brief A project with no imports is written as format 1 (indent 2, same keys and order as 2.4.5).
    @param tmp_path pytest folder.
    @return None.
    """
    p = tmp_path / "a.pcbt.json"
    save_project(p, _project(False))
    d = json.loads(p.read_text())
    assert d["format"] == FORMAT_1 and "imports" not in d and "project" not in d
    assert list(d)[-4:] == ["solver", "view", "format", "app_version"]
    assert p.read_text() == json.dumps(project_to_dict(_project(False)), indent=2)
    assert not (tmp_path / "a.pcbt.json.bak").exists()


def test_format1_open_save_stays_format1(tmp_path):
    """!
    @brief Opening a format 1 file and saving it again without imports keeps format 1 and the same bytes.
    @param tmp_path pytest folder.
    @return None.
    """
    p = tmp_path / "a.pcbt.json"
    save_project(p, _project(False))
    first = p.read_text()
    q = load_project(p)
    assert q.imports == []
    save_project(p, q)
    assert p.read_text() == first


def test_format2_layout_and_round_trip(tmp_path):
    """!
    @brief With imports the file is format 2, the format 1 project is nested, and every field comes back equal.
    @param tmp_path pytest folder.
    @return None.
    """
    p = tmp_path / "b.pcbt.json"
    prj = _project(True)
    save_project(p, prj)
    d = json.loads(p.read_text())
    assert d["format"] == FORMAT_2 and d["app_version"] == __version__
    assert "board" not in d and d["project"]["format"] == FORMAT_1 and "board" in d["project"]
    assert len(d["imports"]) == 1
    back = load_project(p)
    assert back.imports == prj.imports
    assert project_to_dict(back) == project_to_dict(prj)
    assert back.options.to_dict() == prj.options.to_dict() and back.view == prj.view


def test_snapshot_round_trip_keeps_imports():
    """!
    @brief The undo snapshot (dict round trip, no validation) keeps the imports.
    @return None.
    """
    prj = _project(True)
    snap = copy.deepcopy(project_to_dict(prj))
    assert project_from_dict(snap, validate=False).imports == prj.imports


def test_bak_before_first_format2_save(tmp_path):
    """!
    @brief The first format 2 save over a format 1 file keeps a .bak copy of the old bytes; the next saves do not touch it.
    @param tmp_path pytest folder.
    @return None.
    """
    p = tmp_path / "c.pcbt.json"
    save_project(p, _project(False))
    old = p.read_text()
    prj = load_project(p)
    prj.imports = [_record()]
    save_project(p, prj)
    bak = tmp_path / "c.pcbt.json.bak"
    assert bak.read_text() == old
    assert json.loads(p.read_text())["format"] == FORMAT_2
    bak.write_text("marker")
    save_project(p, prj)                                  # Already format 2: no new .bak
    assert bak.read_text() == "marker"
    save_project(tmp_path / "new.pcbt.json", prj)         # A new file has nothing to back up
    assert not (tmp_path / "new.pcbt.json.bak").exists()


def test_newer_format_refused_with_writer_version(tmp_path):
    """!
    @brief A file of format 3 is refused, and the message names the version that wrote it.
    @param tmp_path pytest folder.
    @return None.
    """
    p = tmp_path / "d.pcbt.json"
    p.write_text(json.dumps({"format": "pcbthermal-project-3", "app_version": "9.9.0", "project": {}}))
    with pytest.raises(ProjectFormatError, match=r"format 3.*9\.9\.0"):
        load_project(p)
    with pytest.raises(ProjectFormatError, match="newer version"):
        project_from_dict({"format": "pcbthermal-project-4"})
    with pytest.raises(ProjectFormatError):
        project_from_dict({"format": "something-else"})
    with pytest.raises(ProjectFormatError, match="project"):
        project_from_dict({"format": FORMAT_2, "imports": []})


def test_plain_native_dict_is_format_1():
    """!
    @brief A plain native dict (no format key) opens as format 1 with no imports.
    @return None.
    """
    from pcbthermal.model import problem_to_dict
    assert project_from_dict(problem_to_dict(example_board())).imports == []


def _frozen_245_reader():
    """!
    @brief The module project.py of the released tag v2.4.5, loaded under another name (relative imports resolve to the current package).
    @return module, or None if the tag is unavailable.
    """
    try:
        src = subprocess.run(["git", "show", "v2.4.5:pcbthermal/project.py"], cwd=ROOT, capture_output=True, text=True, check=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    spec = importlib.util.spec_from_loader("pcbthermal._project_245", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "pcbthermal"
    sys.modules[spec.name] = mod
    exec(compile(src, "project_245.py", "exec"), mod.__dict__)
    return mod


def test_frozen_245_reader_refuses_format2(tmp_path):
    """!
    @brief The reader of 2.4.5 cannot open a format 2 file (KeyError 'board'), so it can never drop the imports and save format 1 over them.
    @param tmp_path pytest folder.
    @return None.
    """
    old = _frozen_245_reader()
    if old is None:
        pytest.skip("tag v2.4.5 not available")
    p = tmp_path / "e.pcbt.json"
    save_project(p, _project(True))
    with pytest.raises(KeyError, match="board"):
        old.load_project(p)
    # Control: the same reader opens a format 1 file written by this program
    q = tmp_path / "f.pcbt.json"
    save_project(q, _project(False))
    assert old.load_project(q).problem.board.width == pytest.approx(example_board().board.width)
