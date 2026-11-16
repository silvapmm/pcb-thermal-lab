#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_format_compat_271.py
@brief A project saved with the finite-element comparison model ticked opens in v2.7.1 (the FEM is simply absent there), and what the older program does on a re-save.
@details The reader of v2.7.1 refuses a `models` list that names an unknown model (the whole project does not open), so this tree writes the FEM under the key
         `comparison_models` of the solver options (an older reader drops unknown keys) and leaves it out of `models`. The old program is the tag `v2.7.1`, extracted with
         `git archive` into a temporary folder and run in a subprocess (`PYTHONPATH` = that folder, its `pcbthermal.__version__` checked). It runs only when `PCBT_COMPAT_V271=1`
         is set, like the 2.4.5 check; the always-run tests read the written file and the round trip in this tree:

             PCBT_COMPAT_V271=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q tests/test_format_compat_271.py
"""

import json
import os
import subprocess
import sys

import pytest

from pcbthermal.api import SolverOptions
from pcbthermal.examples import example_board
from pcbthermal.project import Project, ProjectFormatError, load_project, save_project

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAG = "v2.7.1"
ENABLED = os.environ.get("PCBT_COMPAT_V271") == "1"

# Run in the old tree: the version is checked first, then the file is loaded, its models printed, and a re-save is read back
OLD_SCRIPT = r'''
import json, sys
import pcbthermal
assert pcbthermal.__version__ == "2.7.1", pcbthermal.__version__
from pcbthermal.project import load_project, save_project
path, out = sys.argv[1], sys.argv[2]
try:
    prj = load_project(path)
except Exception as exc:
    print("REFUSED " + type(exc).__name__ + ": " + str(exc))
else:
    save_project(out, prj)
    saved = json.load(open(out))
    print("OPENED " + json.dumps({"models": list(prj.options.models), "saved_solver_keys": sorted(saved["solver"])}))
'''


def _old_tree(tmp_path_factory):
    """!
    @brief Extract the tag v2.7.1 into a temporary folder.
    @param tmp_path_factory pytest factory of temporary folders.
    @return str Folder holding the old `pcbthermal` package.
    """
    dest = tmp_path_factory.mktemp("v271")
    archive = subprocess.run(["git", "archive", TAG, "pcbthermal"], cwd=ROOT, capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive.stdout, check=True)
    return str(dest)


def _run_old(tree, path, out):
    """!
    @brief Run the old program on a file in a subprocess.
    @param tree Folder with the old package.
    @param path Project file to load.
    @param out File the old program writes after loading (its re-save).
    @return str Standard output of the subprocess.
    """
    env = dict(os.environ, PYTHONPATH=tree, QT_QPA_PLATFORM="offscreen")
    done = subprocess.run([sys.executable, "-c", OLD_SCRIPT, str(path), str(out)], cwd=tree, env=env, capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


@pytest.fixture(scope="module")
def old_tree(tmp_path_factory):
    """!
    @brief The v2.7.1 tree, built once per module; the test is skipped unless PCBT_COMPAT_V271=1.
    @param tmp_path_factory pytest factory of temporary folders.
    @return str Folder with the old package.
    """
    if not ENABLED:
        pytest.skip("set PCBT_COMPAT_V271=1 to run the old v2.7.1 program (extracted from the local git tag) against this tree")
    return _old_tree(tmp_path_factory)


def _save(tmp_path, models, **kw):
    """!
    @brief Save the example board with the given models ticked.
    @param tmp_path Temporary folder.
    @param models Model keys.
    @param kw Other SolverOptions fields.
    @return Path of the project file.
    """
    path = tmp_path / "board.pcbt.json"
    save_project(path, Project(problem=example_board(), options=SolverOptions(models=models, **kw)))
    return path


def test_the_fem_is_saved_under_its_own_key_and_never_in_models(tmp_path):
    """!
    @brief The file lists the older models in `models`, the FEM in `comparison_models`, and a default FEM option writes nothing else.
    @param tmp_path Temporary folder.
    @return None.
    """
    d = json.loads(_save(tmp_path, ("fvm", "solid3d", "fem")).read_text())["solver"]
    assert d["models"] == ["fvm", "solid3d"] and d["comparison_models"] == ["fem"] and "comparison_only" not in d
    assert "fem_gap_elements" not in d and "fem_refine" not in d
    d = json.loads(_save(tmp_path, ("fvm", "fem"), fem_gap_elements=8, fem_refine=3.0).read_text())["solver"]
    assert d["fem_gap_elements"] == 8 and d["fem_refine"] == 3.0
    assert "comparison_models" not in json.loads(_save(tmp_path, ("fvm", "fdm")).read_text())["solver"]       # without the FEM the file is as before


def test_the_fem_alone_is_written_as_the_fvm_with_a_marker_and_reads_back_alone(tmp_path):
    """!
    @brief FEM only: `models` is ["fvm"] for an older reader, `comparison_only` tells this tree that the FEM was the whole selection.
    @param tmp_path Temporary folder.
    @return None.
    """
    path = _save(tmp_path, ("fem",))
    d = json.loads(path.read_text())["solver"]
    assert d["models"] == ["fvm"] and d["comparison_models"] == ["fem"] and d["comparison_only"] is True
    assert load_project(path).options.models == ("fem",)


@pytest.mark.parametrize("models", [("fvm", "fem"), ("fvm", "lumped", "analytic", "fdm", "solid3d", "fem"), ("lumped", "fem")])
def test_the_models_round_trip(tmp_path, models):
    """!
    @brief The ticked models, FEM included, are the same after a save and a load.
    @param tmp_path Temporary folder.
    @param models Model keys.
    @return None.
    """
    assert load_project(_save(tmp_path, models, fem_gap_elements=4)).options.models == models
    assert load_project(_save(tmp_path, models, fem_gap_elements=4)).options.fem_gap_elements == 4


@pytest.mark.parametrize("bad", [{"comparison_models": "fem"}, {"comparison_models": ["fvm"]}, {"comparison_models": [1]}, {"comparison_models": ["fem"], "comparison_only": "yes"},
                                 {"fem_gap_elements": 1}, {"fem_gap_elements": 99}, {"fem_gap_elements": True}, {"fem_refine": 0.5}, {"fem_refine": 9}, {"fem_refine": "2"},
                                 {"fem_refine": float("nan")}])
def test_hostile_values_are_refused_with_the_key_path(tmp_path, bad):
    """!
    @brief A malformed finite-element key is a ProjectFormatError that names the solver section, never a raw error.
    @param tmp_path Temporary folder.
    @param bad Keys put into the solver options of a saved file.
    @return None.
    """
    path = _save(tmp_path, ("fvm", "fem"))
    data = json.loads(path.read_text())
    data["solver"].update(bad)
    text = json.dumps(data).replace("NaN", "NaN")
    path.write_text(text)
    with pytest.raises(ProjectFormatError, match="solver"):
        load_project(path)


def test_the_old_program_opens_a_file_with_the_fem_ticked(old_tree, tmp_path):
    """!
    @brief v2.7.1 opens a project saved with the FEM ticked (the FEM is simply absent there), and its own re-save drops the keys it does not know.
    @param old_tree The old tree.
    @param tmp_path Temporary folder.
    @return None.
    """
    path = _save(tmp_path, ("fvm", "fdm", "fem"), fem_gap_elements=8)
    out = _run_old(old_tree, path, tmp_path / "resaved.pcbt.json")
    assert out.startswith("OPENED "), out
    info = json.loads(out[7:])
    assert info["models"] == ["fvm", "fdm"]                                  # the FEM is absent, nothing else changed
    assert "comparison_models" not in info["saved_solver_keys"] and "fem_gap_elements" not in info["saved_solver_keys"]   # documented: an older version drops the key on save
    # FEM only: the older program runs the FVM, this tree reads its own file back as FEM only
    only = _save(tmp_path, ("fem",))
    assert json.loads(_run_old(old_tree, only, tmp_path / "again.pcbt.json")[7:])["models"] == ["fvm"]
