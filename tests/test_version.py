#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_version.py
@brief The release version is defined once and shown consistently everywhere.
"""

import pathlib
import re
import subprocess
import sys

import pytest

import pcbthermal
from pcbthermal import cli

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_version_is_semantic():
    assert re.fullmatch(r"\d+\.\d+\.\d+", pcbthermal.__version__)


def test_changelog_and_readme_mention_the_version():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{pcbthermal.__version__}]" in changelog
    assert pcbthermal.__version__ in (ROOT / "README.md").read_text(encoding="utf-8")


def test_command_line_reports_the_version(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert pcbthermal.__version__ in capsys.readouterr().out


def test_results_and_projects_record_the_version(tmp_path):
    from pcbthermal import Project, SolverOptions, save_project, simulate
    from pcbthermal.examples import example_board
    import json

    sim = simulate(example_board(), SolverOptions(models=("analytic",)))
    assert sim.to_dict()["version"] == pcbthermal.__version__
    assert pcbthermal.__version__ in sim.report()
    save_project(tmp_path / "p.pcbt.json", Project(problem=example_board()))
    assert json.loads((tmp_path / "p.pcbt.json").read_text())["app_version"] == pcbthermal.__version__
