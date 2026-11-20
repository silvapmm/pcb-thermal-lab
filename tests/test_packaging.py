#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_packaging.py
@brief The files of `packaging/` and the build workflow: source-level checks that need no PyInstaller and no network (the build itself is run by hand and in Actions).
"""

import importlib.util
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
PKG = ROOT / "packaging"
WORKFLOW = ROOT / ".github" / "workflows" / "build-release.yml"


def load(name):
    """!
    @brief Import a script of packaging/ by its path (it is not a package).
    @param name File name without .py.
    @return The module.
    """
    spec = importlib.util.spec_from_file_location(f"packaging_{name}", PKG / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_entry_opens_the_window_by_default_and_keeps_commands():
    """No argument and a project path or a gui option mean the window; a command or a top-level option is passed on."""
    entry = load("entry")
    assert entry.arguments([]) == ["gui"]
    assert entry.arguments(["board.pcbt.json"]) == ["gui", "board.pcbt.json"]
    assert entry.arguments(["--selftest", "--selftest-out", "r.txt"]) == ["gui", "--selftest", "--selftest-out", "r.txt"]
    assert entry.arguments(["run", "x.json"]) == ["run", "x.json"]
    assert entry.arguments(["--version"]) == ["--version"]
    assert entry.arguments(["-psn_0_12345"]) == ["gui"]
    from pcbthermal import cli

    sub = next(a for a in cli.build_parser()._actions if a.dest == "command" or hasattr(a, "choices") and a.choices and "run" in a.choices)
    assert set(entry.COMMANDS) == set(sub.choices)


def test_entry_calls_freeze_support_first():
    """multiprocessing.freeze_support() is the first statement after the import of multiprocessing (a frozen spawn child would open a second window without it)."""
    body = [ln for ln in (PKG / "entry.py").read_text(encoding="utf-8").split('"""', 2)[2].splitlines() if ln.strip() and not ln.strip().startswith("#")]
    assert body[0] == "import multiprocessing" and body[1].startswith("multiprocessing.freeze_support()")


def test_release_notes_extracts_one_section():
    """The section of a version without its heading and without the next one; an unknown version gives nothing (exit code 1)."""
    notes = load("release_notes")
    text = "# Changelog\n\n## [Unreleased]\n\nnew\n\n## [2.8.0] - 2026-11-16\n\nline a\n\n### Fixed\n\nline b\n\n## [2.7.1] - x\n\nold\n"
    assert notes.extract(text, "2.8.0") == "line a\n\n### Fixed\n\nline b\n"
    assert notes.extract(text, "9.9.9") == ""
    real = notes.extract((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"), "2.8.0")
    assert real.startswith("**2.8.0 in short**") and "## [2.7.1]" not in real


def test_build_requirements_drop_the_tests_and_substitute_pyside():
    """The build installs the run-time lines only, with the Qt modules the program uses and not the add-ons."""
    build = load("build")
    lines = build.runtime_requirements()
    names = [re.match(r"[A-Za-z0-9._-]+", r).group(0).lower() for r in lines]
    assert not any(n.startswith("pytest") for n in names)
    assert "pyside6_essentials" in [n.replace("-", "_") for n in names] and "pyside6" not in names
    assert {"numpy", "scipy", "pyamg", "matplotlib"} <= set(names)
    assert build.package_name().startswith("PCB-Thermal-Lab-")


def test_spec_excludes_and_includes():
    """The spec ships the data, the user guide, the icon and the licences, includes pyamg, and keeps the unused Qt modules and the developer folders out."""
    spec = (PKG / "PCB-Thermal-Lab.spec").read_text(encoding="utf-8")
    for needle in ('"pcbthermal/data"', '"pcbthermal/help"', '"ico"', '"licenses"', 'collect_submodules("pyamg")', "SOURCE-OFFER.txt", "BUILD-INFO.txt", "copy_metadata"):
        assert needle in spec
    for module in ("tools", "research", "releases", "tests", "PySide6.QtWebEngineCore", "PySide6.QtPdf", "PySide6.QtQuick", "PySide6.QtGraphs", "PySide6.QtHttpServer",
                   "PySide6.QtLottie", "PySide6.QtNetworkAuth", "PySide6.QtCanvasPainter", "PySide6.QtQmlCompiler", "PySide6.QtQuick3D", "PySide6.QtVirtualKeyboard"):
        assert f'"{module}"' in spec
    assert "exclude_binaries=True" in spec and "onefile" not in spec.lower()      # One folder: the Qt libraries stay replaceable files


def test_qt_licence_texts_are_in_the_repository():
    """The LGPL and the GPL texts and the notices of Qt that every package ships."""
    qt = PKG / "licenses" / "Qt"
    assert "GNU LESSER GENERAL PUBLIC LICENSE" in (qt / "LGPL-3.0.txt").read_text(encoding="utf-8")
    assert "GNU GENERAL PUBLIC LICENSE" in (qt / "GPL-3.0.txt").read_text(encoding="utf-8")
    assert "MIT License" in (PKG / "licenses" / "_fallback" / "pyamg" / "LICENSE.txt").read_text(encoding="utf-8")      # The wheel of pyamg carries no licence file
    assert not (qt / "THIRD-PARTY-NOTICES.txt").exists()          # Made by the build from the Qt source tarballs (qt_sources.py), so that it matches the exact version


def test_forbidden_files_are_recognised():
    """The build refuses the GPL-3-only Qt modules, FFmpeg, QtPdf and its plug-in, WebEngine and the TLS plug-ins, and keeps the three modules the program uses."""
    build = load("build")
    for bad in ("PySide6/Qt/lib/QtGraphs.framework/QtGraphs", "PySide6/Qt/lib/libavcodec.so.61", "PySide6/Qt/plugins/imageformats/libqpdf.so", "PySide6/Qt6Pdf.dll",
                "PySide6/Qt/plugins/tls/libqopensslbackend.so", "PySide6/QtWebEngineCore.abi3.so", "PySide6/Qt6QuickControls2.dll", "PySide6/Qt6HttpServer.dll",
                "PySide6/Qt6VirtualKeyboard.dll", "PySide6/Qt6Lottie.dll", "PySide6/Qt6NetworkAuth.dll", "PySide6/Qt6Qml.dll"):
        assert build.FORBIDDEN.search(bad), bad
    for good in ("PySide6/QtCore.abi3.so", "PySide6/Qt6Gui.dll", "PySide6/Qt/lib/libQt6Widgets.so.6", "PySide6/Qt/plugins/platforms/libqxcb.so",
                 "PySide6/Qt/plugins/imageformats/libqjpeg.so", "numpy/_core/_multiarray_umath.so", "scipy/sparse/linalg/_dsolve/_superlu.so"):
        assert not build.FORBIDDEN.search(good), good


def test_qt_source_urls_and_notice_ids():
    """The release carries the tarballs of the exact version (the Linux-only qtwayland included) and the licence identifiers of an expression are split."""
    qt = load("qt_sources")
    names = [n for n, _ in qt.urls("6.12.0", "6.12.1", wayland=True)]
    assert names == ["qtbase-everywhere-src-6.12.0.tar.xz", "qtsvg-everywhere-src-6.12.0.tar.xz", "qtimageformats-everywhere-src-6.12.0.tar.xz",
                     "qtwayland-everywhere-src-6.12.0.tar.xz", "pyside-setup-everywhere-src-6.12.1.tar.xz"]
    assert all(u.startswith("https://download.qt.io/official_releases/") for _, u in qt.urls("6.12.0", "6.12.0"))
    assert qt._licence_ids("BSD-3-Clause AND (MIT OR Zlib)") == ["BSD-3-Clause", "MIT", "Zlib"]


@pytest.fixture(scope="module")
def workflow():
    """!
    @brief The text of the build workflow.
    @return str.
    """
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_triggers_and_gates(workflow):
    """Tags v* and the build-test branches trigger it; the release job runs only on a tag, holds the only write permission and never publishes or generates notes."""
    assert "tags: ['v*']" in workflow and "branches: ['build-test/**']" in workflow
    release = workflow.split("\n  release:")[1]
    assert "if: startsWith(github.ref, 'refs/tags/v')" in release
    assert workflow.count("contents: write") == 1 and "contents: write" in release
    assert workflow.startswith("#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.\n#  This code is licensed under the MIT License.")
    assert "--generate-notes" not in workflow and "--latest" not in workflow and "--draft" in release and "--notes-file" in release
    assert "secrets." not in workflow.replace("secrets.GITHUB_TOKEN", "")
    assert "packaging/release_notes.py" in release


def test_workflow_checks_the_tag_and_runs_the_selftest(workflow):
    """The tag without the v must equal the version of the program; the three systems, the Linux Qt libraries and the Windows wait are in."""
    assert "GITHUB_REF_NAME#v" in workflow and "exit 1" in workflow
    for needle in ("windows-latest", "ubuntu-22.04", "macos-latest", "libegl1", "libxkbcommon-x11-0", "libxcb-cursor0", "Start-Process", "-Wait", "-PassThru", "ExitCode",
                   "--selftest"):
        assert needle in workflow
