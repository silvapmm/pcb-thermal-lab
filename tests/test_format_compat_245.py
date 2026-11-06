#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_format_compat_245.py
@brief Project files across versions: the v2.4.5 program refuses a format 2 file cleanly and opens format 1; this tree opens 2.4.5 files unchanged.

The release-gate check that used to be done by hand. The old program is the tag `v2.4.5`, extracted with `git archive` into a temporary folder
and run in a subprocess of the same interpreter (`PYTHONPATH` = that folder, working directory = that folder, `pcbthermal.__version__` checked
in the subprocess so that the new tree cannot be used by mistake). No network. It runs only when `PCBT_COMPAT_V245=1` is set, so the whole battery stays light:

    PCBT_COMPAT_V245=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_format_compat_245.py

The always-run test checks that this tree reads the example boards' format 1 files and writes them back with the same content.
"""

import json
import os
import subprocess
import sys

import pytest

from pcbthermal.examples import example_board
from pcbthermal.model import ImportFile, ImportRecord
from pcbthermal.project import FORMAT_1, FORMAT_2, Project, load_project, project_to_dict, save_project

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG = "v2.4.5"
ENABLED = os.environ.get("PCBT_COMPAT_V245") == "1"

# Run in the old tree: the version is checked first, then the action named in argv
OLD_SCRIPT = r'''
import json, sys
import pcbthermal
assert pcbthermal.__version__ == "2.4.5", pcbthermal.__version__
from pcbthermal.project import Project, load_project, project_to_dict, save_project
action, path = sys.argv[1], sys.argv[2]
if action == "load":
    try:
        prj = load_project(path)
    except Exception as exc:
        print("REFUSED " + type(exc).__name__)
    else:
        print("OPENED " + json.dumps(project_to_dict(prj), sort_keys=True))
elif action == "write_all_elements":
    from pcbthermal.model import Problem, SquareWave
    p = Problem.new(width_mm=60, height_mm=40, layers=4, name="all-elements")
    p.add_zone(1, rect=(5, 5, 55, 35), name="zone")
    p.add_full_copper([2, 3, 4])
    p.add_heater(1, 2.0, rect=(10, 10, 18, 18), name="U1", theta=5.0)
    p.add_heater(1, 1.0, rect=(30, 10, 36, 16), name="U2")
    p.heaters[1].set_profile(SquareWave(p_on=2.0, period=1.0, duty=0.5))
    p.add_via(12.0, 12.0, diameter=0.3)
    p.add_via(14.0, 12.0, diameter=0.4)
    p.add_heatsink(4, 20.0, rect=(5, 5, 25, 25), name="sink")
    p.add_heatsink(4, 15.0, rect=(30, 20, 50, 35), name="block", thickness_mm=3.0, contact_r=5.0e-4)
    save_project(path, Project(problem=p))
'''


def _old_tree(tmp_path_factory):
    """!
    @brief Extract the tag v2.4.5 into a temporary folder.
    @param tmp_path_factory pytest factory of temporary folders.
    @return str Folder holding the old `pcbthermal` package.
    """
    dest = tmp_path_factory.mktemp("v245")
    archive = subprocess.run(["git", "archive", TAG, "pcbthermal"], cwd=ROOT, capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, check=True)
    return str(dest)


def _run_old(tree, action, path):
    """!
    @brief Run the old program on a file in a subprocess.
    @param tree Folder with the old package.
    @param action "load" or "write_all_elements".
    @param path Project file path.
    @return str Standard output of the subprocess.
    """
    env = dict(os.environ, PYTHONPATH=tree, QT_QPA_PLATFORM="offscreen")
    done = subprocess.run([sys.executable, "-c", OLD_SCRIPT, action, str(path)], cwd=tree, env=env, capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def _same_content(a, b):
    """!
    @brief Compare two project dictionaries ignoring the writer's version stamp.
    @param a First dictionary.
    @param b Second dictionary.
    @return bool True if they are equal.
    """
    a, b = dict(a), dict(b)
    for d in (a, b):
        d.pop("app_version", None)
    return a == b


@pytest.fixture(scope="module")
def old_tree(tmp_path_factory):
    """!
    @brief The v2.4.5 tree, built once per module; the test is skipped unless PCBT_COMPAT_V245=1.
    @param tmp_path_factory pytest factory of temporary folders.
    @return str Folder with the old package.
    """
    if not ENABLED:
        pytest.skip("set PCBT_COMPAT_V245=1 to run the old v2.4.5 program (extracted from the local git tag) against this tree")
    return _old_tree(tmp_path_factory)


def test_old_program_refuses_format2_without_touching_it(old_tree, tmp_path):
    """!
    @brief v2.4.5 cannot open a format 2 file written by this tree, and the file is byte-identical afterwards (no overwrite, no .bak).
    @param old_tree The old tree.
    @param tmp_path Temporary folder.
    @return None.
    """
    rec = ImportRecord(name="b", files=[ImportFile("top.gtl", 10, "ab" * 32, "copper")], box_mm=[0, 0, 100, 80])
    path = tmp_path / "imported.pcbt.json"
    save_project(path, Project(problem=example_board(), imports=[rec]))
    before = path.read_bytes()
    assert json.loads(before)["format"] == FORMAT_2 and "project" in json.loads(before)
    out = _run_old(old_tree, "load", path)
    assert out == "REFUSED KeyError"
    assert path.read_bytes() == before
    assert sorted(os.listdir(tmp_path)) == ["imported.pcbt.json"]


def test_old_program_opens_format1_of_this_tree(old_tree, tmp_path):
    """!
    @brief v2.4.5 opens the format 1 files this tree writes, with the same content.
    @param old_tree The old tree.
    @param tmp_path Temporary folder.
    @return None.
    """
    path = tmp_path / "plain.pcbt.json"
    save_project(path, Project(problem=example_board()))
    assert json.loads(path.read_text())["format"] == FORMAT_1
    out = _run_old(old_tree, "load", path)
    assert out.startswith("OPENED ")
    assert _same_content(json.loads(out[7:]), project_to_dict(load_project(path)))


def test_this_tree_opens_files_written_by_245(old_tree, tmp_path):
    """!
    @brief This tree opens the example boards and a project with every element type saved by v2.4.5, with identical content.
    @param old_tree The old tree.
    @param tmp_path Temporary folder.
    @return None.
    """
    path = tmp_path / "all.pcbt.json"
    _run_old(old_tree, "write_all_elements", path)
    files = [path] + [os.path.join(ROOT, "examples", n) for n in sorted(os.listdir(os.path.join(ROOT, "examples"))) if n.endswith(".pcbt.json")]
    for f in files:
        # The old program's own reading of the file (it fills the defaults the way 2.4.5 did) against this tree's reading
        old = _run_old(old_tree, "load", f)
        assert old.startswith("OPENED "), f
        assert _same_content(json.loads(old[7:]), project_to_dict(load_project(f))), f
    p = load_project(path).problem
    assert len(p.heaters) == 2 and len(p.vias) == 2 and len(p.heatsinks) == 2 and p.heaters[1].profile is not None


def test_example_boards_format1_round_trip_is_byte_stable(tmp_path):
    """!
    @brief Always run: this tree reads each example board (format 1) and writes it back with the same content and the same bytes at the second save.
    @param tmp_path Temporary folder.
    @return None.
    """
    folder = os.path.join(ROOT, "examples")
    names = [n for n in sorted(os.listdir(folder)) if n.endswith(".pcbt.json")]
    assert names
    for n in names:
        src = os.path.join(folder, n)
        out = tmp_path / n
        prj = load_project(src)
        save_project(out, prj)
        # The example files on disk predate some defaults, so compare the loaded content and then the bytes of a second save
        assert _same_content(project_to_dict(load_project(src)), project_to_dict(load_project(out))), n
        again = tmp_path / ("again_" + n)
        save_project(again, load_project(out))
        assert again.read_bytes() == out.read_bytes(), n
        b = json.loads(out.read_text())
        assert b["format"] == FORMAT_1 and not os.path.exists(str(out) + ".bak")


def test_old_program_refuses_a_package_without_touching_it(old_tree, tmp_path):
    """!
    @brief v2.4.5 cannot open a `.pcbtz` package written by this tree (a ZIP is not JSON), says so as an error, and the file is byte-identical afterwards.
    @param old_tree The old tree.
    @param tmp_path Temporary folder.
    @return None.
    """
    from pcbthermal import package as pkg
    path = tmp_path / "board.pcbtz"
    pkg.save_package(path, Project(problem=example_board()))
    before = path.read_bytes()
    out = _run_old(old_tree, "load", path)
    assert out.startswith("REFUSED")
    assert path.read_bytes() == before and sorted(os.listdir(tmp_path)) == ["board.pcbtz"]
