#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_selftest.py
@brief The self-test of the program (`pcbthermal gui --selftest`) that the downloadable packages run: from source, in a fresh process.
"""

import os
import pathlib
import subprocess
import sys

from pcbthermal import __version__, cli, selftest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_selftest_runs_from_source_and_writes_its_report(tmp_path):
    """The whole self-test (imports, files, window, FVM solve through the spawn process, energy balance) passes and leaves its report in the file."""
    report = tmp_path / "report.txt"
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", PCBTHERMAL_CONFIG=str(tmp_path))
    done = subprocess.run([sys.executable, "-m", "pcbthermal", "gui", "--selftest", "--selftest-out", str(report)], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=180)
    text = report.read_text(encoding="utf-8")
    assert done.returncode == 0, done.stdout + done.stderr
    assert text.rstrip().endswith("SELFTEST OK")
    assert f"version={__version__}" in text and "frozen=False" in text
    assert "example board solved in the calculation process" in text and "energy balance closes" in text
    assert "FAIL" not in text


def test_gui_command_has_the_selftest_options():
    """The options exist on the gui command and default to off."""
    args = cli.build_parser().parse_args(["gui", "--selftest", "--selftest-out", "r.txt"])
    assert args.selftest is True and args.selftest_out == "r.txt"
    assert cli.build_parser().parse_args(["gui"]).selftest is False


def test_report_records_failures_and_the_file(tmp_path):
    """A failed step is listed in the summary; every line is also appended to the file."""
    path = tmp_path / "r.txt"
    rep = selftest.Report(str(path))
    assert rep.check("good step", True, "detail") is True
    assert rep.check("bad step", False, "why") is False
    assert rep.failures == ["bad step"]
    assert path.read_text(encoding="utf-8").splitlines() == ["ok   good step: detail", "FAIL bad step: why"]


def test_frozen_checks_are_skipped_from_source():
    """The package checks (licence files, forbidden folders) only apply to a frozen program; from source they add no line."""
    rep = selftest.Report()
    selftest.check_package(rep)
    assert rep.lines == []
