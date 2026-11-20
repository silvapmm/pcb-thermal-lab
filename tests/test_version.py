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


def _badge(name):
    """!
    @brief Read one shields.io badge of the README: its image URL.

    @param name  Badge label as written in the alt text, for example "Version".
    @return str The badge URL, or an empty string when the badge is missing.
    """
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    found = re.search(r"!\[" + name + r"\]\((https://img\.shields\.io/badge/[^)\s]+)\)", text)
    return found.group(1) if found else ""


def test_readme_version_badge_equals_the_version():
    expected = f"https://img.shields.io/badge/version-{pcbthermal.__version__}-4f46e5"
    assert _badge("Version") == expected, (
        f"README version badge must be {expected}: update it with the version bump")


def test_readme_tests_badge_equals_the_recorded_battery():
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    recorded = re.search(r"Current state of the battery\*\*: the last whole battery gave (\d+) passed", claude)
    assert recorded, "CLAUDE.md section 14 'Current state of the battery' sentence changed shape"
    expected = f"https://img.shields.io/badge/tests-{recorded.group(1)}%20passed-2da44e"
    assert _badge("Tests") == expected, (
        f"README tests badge must be {expected}: when a battery is recorded, update the README badge "
        "together with CLAUDE.md section 14 and docs/versions.md 'How each version was tested'")


def test_readme_static_badges_keep_their_form():
    assert _badge("Python") == "https://img.shields.io/badge/python-3.13-3776ab"
    assert _badge("Licence") == "https://img.shields.io/badge/licence-MIT-blue"
    assert _badge("Platforms") == "https://img.shields.io/badge/platforms-Windows%20%7C%20macOS%20%7C%20Linux-555"


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
