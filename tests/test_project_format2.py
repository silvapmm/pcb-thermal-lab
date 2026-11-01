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


def _released_program(tag, folder):
    """!
    @brief Extract the package `pcbthermal` of a released tag into a folder (`git archive`), to run the real released code.
    @param tag Release tag, for example "v2.4.5".
    @param folder Destination folder.
    @return str, the folder to put on PYTHONPATH, or None if git or the tag is unavailable.
    """
    try:
        archive = subprocess.run(["git", "archive", tag, "pcbthermal"], cwd=ROOT, capture_output=True, check=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    import io
    import tarfile
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(folder, filter="data")
    return str(folder)


_OLD_READER = r"""
import sys, json
from pcbthermal import __version__
from pcbthermal.project import load_project
try:
    load_project(sys.argv[1])
    print(json.dumps({"version": __version__, "opened": True}))
except Exception as exc:
    print(json.dumps({"version": __version__, "opened": False, "error": type(exc).__name__, "text": str(exc)}))
"""


@pytest.mark.parametrize("tag", ["v2.4.0", "v2.4.5"])
def test_released_program_refuses_format2(tmp_path, tag):
    """!
    @brief The REAL released program (its package extracted from the tag and run in its own process) cannot open a format 2 file: its reader
           raises KeyError('board') (the window shows "Cannot open file", the command line an error), so it never drops the imports and
           saves format 1 over them; the file is left untouched. 2.4.0 and 2.4.5 bracket the 2.4.x readers (project.py is the same text in
           2.4.0 to 2.4.2 and in 2.4.3 to 2.4.5).
    @param tmp_path pytest folder.
    @param tag Release tag.
    @return None.
    """
    rel = _released_program(tag, tmp_path / "rel")
    if rel is None:
        pytest.skip(f"tag {tag} not available")
    f2 = tmp_path / "e.pcbt.json"
    save_project(f2, _project(True))
    before = f2.read_bytes()
    f1 = tmp_path / "f.pcbt.json"
    save_project(f1, _project(False))
    env = dict(os.environ, PYTHONPATH=rel, PCBTHERMAL_CONFIG=str(tmp_path / "cfg"))
    out = {}
    for name, path in (("f2", f2), ("f1", f1)):
        res = subprocess.run([sys.executable, "-c", _OLD_READER, str(path)], cwd=str(tmp_path), env=env, capture_output=True, text=True, timeout=120)
        out[name] = json.loads(res.stdout.strip().splitlines()[-1])
    assert out["f2"]["version"] == tag[1:]
    assert out["f2"] == {"version": tag[1:], "opened": False, "error": "KeyError", "text": "'board'"}
    assert out["f1"]["opened"]                                     # Control: the same released reader opens a format 1 file of this program
    assert f2.read_bytes() == before


def test_unknown_keys_of_format2_survive_a_save(tmp_path):
    """!
    @brief Forward compatibility: keys a later 2.x writes (top level, record, file, part, copper) are kept and written back by this version.
    @param tmp_path pytest folder.
    @return None.
    """
    d = project_to_dict(_project(True))
    d["future_top"] = {"a": 1}
    rec = d["imports"][0]
    rec["future_record"] = [1, 2]
    rec["files"][0]["future_file"] = "x"
    rec["parts"][0]["future_part"] = {"both_shapes": [[0, 0]]}
    rec["copper"]["future_copper"] = 3
    p = tmp_path / "g.pcbt.json"
    p.write_text(json.dumps(d))
    prj = load_project(p)
    save_project(p, prj)
    back = json.loads(p.read_text())
    assert back["future_top"] == {"a": 1}
    r = back["imports"][0]
    assert r["future_record"] == [1, 2] and r["files"][0]["future_file"] == "x"
    assert r["parts"][0]["future_part"] == {"both_shapes": [[0, 0]]} and r["copper"]["future_copper"] == 3
    # A key this version writes itself is not overridden by a kept one
    assert back["format"] == FORMAT_2 and back["app_version"] == __version__


def test_record_fields_of_the_design(tmp_path):
    """!
    @brief The record holds what INTEGRATION.md 3 and 10 list (files by name, size, hash and function; box; parts by designator with shape,
           polygon, power, footprint, side and edits; plated holes; settings; warnings; copper masks) and they round-trip.
    @param tmp_path pytest folder.
    @return None.
    """
    rec = _record()
    rec.holes = [{"x_mm": 1.0, "y_mm": 2.0, "d_mm": 0.3, "kind": "via"}]
    rec.parts[0].footprint, rec.parts[0].side = "SOIC-8", "top"
    p = tmp_path / "h.pcbt.json"
    save_project(p, Project(problem=example_board(), imports=[rec]))
    back = load_project(p).imports[0]
    assert back == rec
    assert back.holes[0]["kind"] == "via" and back.parts[0].footprint == "SOIC-8" and back.parts[0].side == "top"


@pytest.mark.parametrize("text, words", [
    ("[1, 2]", "not a PCB Thermal Lab project"),
    ('{"format": "pcbthermal-project-2", "proj', "not valid JSON"),
    ('{"format": "pcbthermal-project-0"}', "unknown project format"),
    ('{"format": 2}', "unknown project format"),
    ('{"format": "pcbthermal-project-2", "project": {}, "imports": {}}', "not a list"),
    ('{"format": "pcbthermal-project-2", "project": {}, "imports": [{"parts": [1]}]}', "malformed"),
    ('{"format": "pcbthermal-project-2", "project": {}, "imports": [{"files": [{"size": "big"}]}]}', "malformed"),
    ('{"format": "pcbthermal-project-2", "project": [], "imports": []}', "project"),
])
def test_malformed_files_are_refused_with_a_message(tmp_path, text, words):
    """!
    @brief Damaged or hand-edited files raise ProjectFormatError with a readable reason (never a bare KeyError or AttributeError).
    @param tmp_path pytest folder.
    @param text File content.
    @param words Words the message must contain.
    @return None.
    """
    p = tmp_path / "m.pcbt.json"
    p.write_text(text)
    with pytest.raises(ProjectFormatError, match=words):
        load_project(p)


def test_file_without_format_key_reads_as_format1(tmp_path):
    """!
    @brief A plain native file (no "format" key) on disk opens as format 1, through load_project and load_problem.
    @param tmp_path pytest folder.
    @return None.
    """
    from pcbthermal.model import load_problem, problem_to_dict
    p = tmp_path / "n.json"
    p.write_text(json.dumps(problem_to_dict(example_board())))
    assert load_project(p).imports == []
    assert load_problem(p).board.width == pytest.approx(example_board().board.width)


def test_load_problem_reads_format2(tmp_path):
    """!
    @brief `load_problem` (used by the transient and convergence commands) reads a format 2 file and refuses a newer one.
    @param tmp_path pytest folder.
    @return None.
    """
    from pcbthermal.model import load_problem
    p = tmp_path / "o.pcbt.json"
    save_project(p, _project(True))
    assert load_problem(p).board.width == pytest.approx(example_board().board.width)
    p.write_text(json.dumps({"format": "pcbthermal-project-3", "app_version": "3.0.0"}))
    with pytest.raises(ProjectFormatError, match="3.0.0"):
        load_problem(p)


@pytest.mark.parametrize("command", ["run", "transient", "convergence", "solvers"])
def test_cli_refuses_newer_format_with_exit_code_2(tmp_path, capsys, command):
    """!
    @brief Every command that reads a project prints one error line (no traceback) and returns 2 for a newer format.
    @param tmp_path pytest folder.
    @param capsys pytest capture.
    @param command CLI command.
    @return None.
    """
    from pcbthermal.cli import main
    p = tmp_path / "q.pcbt.json"
    p.write_text(json.dumps({"format": "pcbthermal-project-3", "app_version": "3.0.0", "project": {}}))
    assert main([command, str(p)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("error: this project file is format 3, written by PCB Thermal Lab 3.0.0") and "Traceback" not in err


def test_save_is_atomic_and_keeps_the_old_file_on_error(tmp_path, monkeypatch):
    """!
    @brief A value that cannot be written, or a failure at the rename, leaves the old file whole and no temporary file behind.
    @param tmp_path pytest folder.
    @param monkeypatch pytest helper.
    @return None.
    """
    p = tmp_path / "s.pcbt.json"
    save_project(p, _project(False))
    old = p.read_bytes()
    bad = _project(False)
    bad.view = {"x": object()}                                   # Not JSON: json.dump used to fail half-way through the file
    with pytest.raises(TypeError):
        save_project(p, bad)
    assert p.read_bytes() == old
    def broken_replace(src, dst):
        raise OSError("disk gone")
    monkeypatch.setattr(os, "replace", broken_replace)
    with pytest.raises(OSError, match="disk gone"):
        save_project(p, _project(True))
    monkeypatch.undo()
    assert p.read_bytes() == old
    assert sorted(f.name for f in tmp_path.iterdir()) == ["s.pcbt.json", "s.pcbt.json.bak"]   # The .bak of the migration, no temporary file


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits and symbolic links")
def test_save_keeps_permissions_links_and_refuses_read_only(tmp_path):
    """!
    @brief The atomic save keeps the permission bits of the file, writes through a symbolic link (the link stays), gives a new file the
           permissions of the umask, and does not replace a read-only file.
    @param tmp_path pytest folder.
    @return None.
    """
    import stat
    p = tmp_path / "t.pcbt.json"
    save_project(p, _project(False))
    mask = os.umask(0)
    os.umask(mask)
    assert stat.S_IMODE(p.stat().st_mode) == 0o666 & ~mask
    os.chmod(p, 0o640)
    save_project(p, _project(False))
    assert stat.S_IMODE(p.stat().st_mode) == 0o640
    link = tmp_path / "link.pcbt.json"
    link.symlink_to(p)
    save_project(link, _project(True))
    assert link.is_symlink() and json.loads(p.read_text())["format"] == FORMAT_2
    assert (tmp_path / "t.pcbt.json.bak").exists()               # The copy sits next to the real file
    os.chmod(p, 0o440)
    before = p.read_bytes()
    try:
        if os.access(p, os.W_OK):                                # Running as root: permission bits do not stop the owner
            pytest.skip("running with privileges that ignore read-only files")
        with pytest.raises(PermissionError):
            save_project(p, _project(False))
        assert p.read_bytes() == before
    finally:
        os.chmod(p, 0o640)


def test_backup_names_and_format2_to_format1(tmp_path):
    """!
    @brief An existing .bak is never overwritten (.bak2 is used), a format 2 file replaced by a project without imports is copied first, and a
           format 1 save over a format 1 file makes no copy.
    @param tmp_path pytest folder.
    @return None.
    """
    p = tmp_path / "u.pcbt.json"
    save_project(p, _project(False))
    (tmp_path / "u.pcbt.json.bak").write_text("user's own backup")
    assert save_project(p, _project(False)) is None
    first = p.read_text()
    made = save_project(p, _project(True))
    assert made == str(tmp_path / "u.pcbt.json.bak2") and (tmp_path / "u.pcbt.json.bak2").read_text() == first
    assert (tmp_path / "u.pcbt.json.bak").read_text() == "user's own backup"
    with_imports = p.read_text()
    made = save_project(p, _project(False))                      # Format 2 -> 1: the imports would be gone, keep the file
    assert made == str(tmp_path / "u.pcbt.json.bak3") and (tmp_path / "u.pcbt.json.bak3").read_text() == with_imports
    assert json.loads(p.read_text())["format"] == FORMAT_1
