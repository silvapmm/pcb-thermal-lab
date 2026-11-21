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


def test_release_date_is_the_same_in_every_document():
    """!
    @brief The release date of the current version is written in four places and they agree (docs/versions.md A1, step 7: the date is the day of the tag).
    @return None.
    """
    v = re.escape(pcbthermal.__version__)
    places = {
        "CHANGELOG.md heading": (ROOT / "CHANGELOG.md", rf"^## \[{v}\] - (\d{{4}}-\d{{2}}-\d{{2}})$"),
        "README.md version line": (ROOT / "README.md", rf"^- \*\*{v}\*\* \((\d{{4}}-\d{{2}}-\d{{2}})\)"),
        "docs/versions.md summary": (ROOT / "docs" / "versions.md", rf"^## Summary of the current version \({v}, (\d{{4}}-\d{{2}}-\d{{2}})\)$"),
        "docs/versions.md heading": (ROOT / "docs" / "versions.md", rf"^## {v} - (\d{{4}}-\d{{2}}-\d{{2}}):"),
    }
    dates = {}
    for where, (path, pattern) in places.items():
        found = re.search(pattern, path.read_text(encoding="utf-8"), flags=re.MULTILINE)
        assert found, f"{where} must give the release date of {pcbthermal.__version__} as YYYY-MM-DD"
        dates[where] = found.group(1)
    assert len(set(dates.values())) == 1, f"the release date differs between the documents: {dates} (set all four to the day of the tag)"


def _badge(name):
    """!
    @brief Read one shields.io badge of the README: its image URL.

    @param name  Badge label as written in the alt text, for example "Version".
    @return str The badge URL, or an empty string when the badge is missing.
    """
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    found = re.search(r"!\[" + name + r"\]\((https://img\.shields\.io/badge/\S+?)\)(?=\s|\]|$)", text)
    return found.group(1) if found else ""


def test_readme_version_badge_equals_the_version():
    expected = f"https://img.shields.io/badge/version-{pcbthermal.__version__}-4f46e5"
    assert _badge("Version") == expected, (
        f"README version badge must be {expected}: update it with the version bump")


def test_readme_tests_badge_equals_the_recorded_battery():
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    # The maintainer rewrites this sentence after every battery: anchor only on its bold label and take the first
    # "<count> passed" of the same paragraph, with or without a thousands separator (4284, 4 284, 4,284)
    paragraph = re.search(r"\*\*Current state of the battery\*\*:([^\n]*)", claude)
    assert paragraph, ("CLAUDE.md section 14 lost its '**Current state of the battery**:' line; the README tests "
                       "badge is read from it (keep the bold label, or change this test with it)")
    recorded = re.search(r"(\d{1,3}(?:[ ,  ]?\d{3})*)\s+passed", paragraph.group(1))
    assert recorded, ("the '**Current state of the battery**:' line of CLAUDE.md section 14 must give the battery "
                      "as '<count> passed' (for example 'gave 4284 passed, 12 skipped')")
    count = re.sub(r"\D", "", recorded.group(1))
    expected = f"https://img.shields.io/badge/tests-{count}%20passed-2da44e"
    assert _badge("Tests") == expected, (
        f"README tests badge must be {expected}: when a battery is recorded, update the README badge "
        "together with CLAUDE.md section 14 and docs/versions.md 'How each version was tested'")


def test_readme_static_badges_keep_their_form():
    assert _badge("Python") == "https://img.shields.io/badge/python-3.13-3776ab"
    assert _badge("Licence") == "https://img.shields.io/badge/licence-MIT-blue"
    assert _badge("Platforms") == "https://img.shields.io/badge/platforms-macOS%20(tested)%20%7C%20Windows%20%7C%20Linux%20(CI%20self--test)-555"


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
