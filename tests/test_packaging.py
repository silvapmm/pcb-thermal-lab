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
                "PySide6/Qt/translations/qt_de.qm", "PCB Thermal Lab.app/Contents/Resources/PySide6/Qt/translations/qtbase_fr.qm",
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
    assert "ATTACH_QT_SOURCE" not in workflow and "attach-source" not in workflow     # The Qt source is always on the release: no switch
    assert "--release" in workflow and "check_release.py" in release and "qt-source/*" in release and "--json assets" in release


def test_workflow_checks_the_tag_and_runs_the_selftest(workflow):
    """The tag without the v must equal the version of the program; the three systems, the Linux Qt libraries and the Windows wait are in."""
    assert "GITHUB_REF_NAME#v" in workflow and "exit 1" in workflow
    for needle in ("windows-latest", "ubuntu-22.04", "macos-latest", "libegl1", "libxkbcommon-x11-0", "libxcb-cursor0", "Start-Process", "-Wait", "-PassThru", "ExitCode",
                   "--selftest"):
        assert needle in workflow


def test_build_pins_are_exact_and_the_second_contact_is_given_and_guarded(tmp_path, monkeypatch):
    """The build requirements pin PySide6-Essentials, shiboken6 and PyInstaller with ==; the second contact is the published address and an empty one stops every build."""
    import pcbthermal
    build = load("build")
    pins = build.pinned_versions()
    assert {"pyside6_essentials", "shiboken6", "pyinstaller"} <= set(pins)
    assert pins["pyside6_essentials"] == pins["shiboken6"]
    assert build.SECOND_CONTACT == "silva.pmm@gmail.com" == pcbthermal.__contact__
    monkeypatch.setattr(build, "SECOND_CONTACT", None)
    for args in (["--release"], []):
        with pytest.raises(SystemExit):
            build.main(args)
    monkeypatch.setattr(build, "qt_versions", lambda: ("6.12.0", "6.12.0"))
    with pytest.raises(ValueError):
        build.write_notice_files(tmp_path, True)


def test_source_offer_names_the_attached_tarballs_and_the_second_contact(tmp_path, monkeypatch):
    """SOURCE-OFFER.txt says the tarballs are attached to the release and gives the Issues page and the e-mail address, in a trial and a release build; no TODO text."""
    build = load("build")
    monkeypatch.setattr(build, "qt_versions", lambda: ("6.12.0", "6.12.0"))
    for release in (False, True):
        build.write_notice_files(tmp_path, release)
        text = (tmp_path / "SOURCE-OFFER.txt").read_text(encoding="utf-8")
        assert "attached to the release page" in text and "qtbase-everywhere-src-6.12.0.tar.xz" in text
        assert "https://github.com/silvapmm/pcb-thermal-lab/issues" in text and "Pedro Silva (PMS Labs)" in text
        assert "by e-mail at silva.pmm@gmail.com" in text and "TODO" not in text
        assert "silva.pmm@gmail.com" in (tmp_path / "NOTICE.txt").read_text(encoding="utf-8")


def test_check_release_compares_the_packages_and_the_source(tmp_path):
    """The release job's check: equal Qt and PySide versions in the three results, and every source tarball present."""
    import hashlib
    import json
    check = load("check_release")
    names = ["qtbase-everywhere-src-6.12.0.tar.xz", "pyside-setup-everywhere-src-6.12.0.tar.xz"]
    (tmp_path / "qt-source").mkdir()
    for n in names:
        (tmp_path / "qt-source" / n).write_text("x" + n)
    (tmp_path / "qt-source" / "QT-SOURCE-SHA256.txt").write_text("".join(f"{hashlib.sha256(('x' + n).encode()).hexdigest()}  {n}\n" for n in names))
    for system in check.SYSTEMS:
        (tmp_path / f"PCB-Thermal-Lab-9.9.9-{system}.zip").write_text("x")
        res = {"version": "9.9.9", "qt": "6.12.0", "pyside": "6.12.0", "archive": f"PCB-Thermal-Lab-9.9.9-{system}.zip", "source_assets": names}
        (tmp_path / f"BUILD-RESULT-{system}.json").write_text(json.dumps(res))
    assert check.check(tmp_path) == [] and check.check(tmp_path, "9.9.9") == []
    assert any("the tag says 9.9.8" in p for p in check.check(tmp_path, "9.9.8"))          # The packages must be the version of the tag
    (tmp_path / "qt-source" / names[1]).write_text("tampered")
    assert any("SHA-256 differs" in p for p in check.check(tmp_path))                     # A tarball that is not the one whose sum was checked at download
    (tmp_path / "qt-source" / names[1]).write_text("x" + names[1])
    newer = json.loads((tmp_path / "BUILD-RESULT-linux-x64.json").read_text())
    for system in check.SYSTEMS:                                                          # All three agree with each other but not with the tarballs' version
        (tmp_path / f"BUILD-RESULT-{system}.json").write_text(json.dumps(dict(newer, qt="6.12.1", pyside="6.12.1")))
    assert any("not the source of version 6.12.1" in p for p in check.check(tmp_path))
    for system in check.SYSTEMS:
        (tmp_path / f"BUILD-RESULT-{system}.json").write_text(json.dumps(newer))
    assert check.main([str(tmp_path), "--version", "v9.9.9"]) == 0 and check.main([str(tmp_path), "--version", "9.9.8"]) == 1
    bad = json.loads((tmp_path / "BUILD-RESULT-linux-x64.json").read_text())
    bad["pyside"] = "6.12.1"
    (tmp_path / "BUILD-RESULT-linux-x64.json").write_text(json.dumps(bad))
    assert any("pyside differs" in p for p in check.check(tmp_path))
    (tmp_path / "qt-source" / names[0]).unlink()
    assert any(names[0] in p for p in check.check(tmp_path))


def test_release_notes_list_the_source_tarballs():
    """The notes of a release name the Qt and PySide versions, the attached tarballs and the checksum file."""
    notes = load("release_notes")
    text = notes.source_section("6.12.0", "6.12.0", ["qtbase-everywhere-src-6.12.0.tar.xz"])
    assert "Qt 6.12.0" in text and "qtbase-everywhere-src-6.12.0.tar.xz" in text and "QT-SOURCE-SHA256.txt" in text


def test_gpl_text_is_the_spdx_text():
    """The GPL-3.0 text is the byte-exact SPDX text (its checksum and source are recorded in licenses/Qt/SOURCES.txt)."""
    import hashlib
    qt = PKG / "licenses" / "Qt"
    digest = hashlib.sha256((qt / "GPL-3.0.txt").read_bytes()).hexdigest()
    assert digest in (qt / "SOURCES.txt").read_text(encoding="utf-8")


def test_release_notes_of_a_pre_release_fall_back_to_unreleased(tmp_path):
    """A pre-release version without its own section takes the Unreleased section; a final version without a section still fails."""
    notes = load("release_notes")
    log = tmp_path / "CHANGELOG.md"
    log.write_text("# Changelog\n\n## [Unreleased]\n\nnew things\n\n## [2.8.0] - x\n\nold\n", encoding="utf-8")
    out = tmp_path / "notes.md"
    assert notes.main(["2.9.0rc1", "--changelog", str(log), "-o", str(out)]) == 0 and out.read_text(encoding="utf-8") == "new things\n"
    assert notes.main(["2.9.0", "--changelog", str(log), "-o", str(out)]) == 1


def test_licence_set_is_what_ships(monkeypatch, tmp_path):
    """The licences quoted are the run-time closure plus PyInstaller itself (its bootloader is in the program), never the requirements of the build tools."""
    build = load("build")

    class Dist:
        """!
        @brief A fake installed distribution.
        """

        def __init__(self, name, requires=()):
            """!
            @param name Distribution name.
            @param requires Requirement lines.
            """
            self.metadata, self.requires = {"Name": name}, list(requires)

    fakes = [Dist("numpy"), Dist("scipy", ["numpy>=2"]), Dist("pyamg", ["numpy", "scipy"]), Dist("matplotlib", ["numpy", "packaging"]), Dist("packaging"),
             Dist("PySide6_Essentials", ["shiboken6==6.12.0"]), Dist("shiboken6"), Dist("pyinstaller", ["altgraph", "macholib", "setuptools", "pyinstaller-hooks-contrib", "packaging"]),
             Dist("altgraph"), Dist("macholib", ["altgraph"]), Dist("setuptools"), Dist("pyinstaller-hooks-contrib", ["setuptools"])]
    monkeypatch.setattr(build.metadata, "distributions", lambda path=None: fakes)
    names = set(build.bundled_distributions(tmp_path))
    assert {"numpy", "scipy", "pyamg", "matplotlib", "packaging", "pyside6_essentials", "shiboken6", "pyinstaller"} <= names
    assert not names & {"altgraph", "macholib", "setuptools", "pyinstaller_hooks_contrib"}


def test_icu_notice_follows_the_qt_wheel(monkeypatch, tmp_path):
    """The ICU licence is copied when the Qt wheel bundles ICU 73 (Linux), skipped when it bundles none, and another ICU major stops the build."""
    build = load("build")
    site = tmp_path / "site"
    lib = site / "PySide6" / "Qt" / "lib"
    lib.mkdir(parents=True)
    monkeypatch.setattr(build, "site_packages", lambda: site)
    out = tmp_path / "licenses"
    out.mkdir()
    assert build.system_notices(out) == [] and not (out / "ICU").exists()
    (lib / "libicuuc.so.73").write_text("x")
    assert [n for n, _ in build.system_notices(out)] == ["ICU"] and "UNICODE" in (out / "ICU" / "LICENSE").read_text(encoding="utf-8")
    (lib / "libicuuc.so.74").write_text("x")
    with pytest.raises(SystemExit):
        build.system_notices(out)


def test_file_list_names_native_libraries_outside_qt(tmp_path):
    """FILES.txt lists every file and, first, the native libraries that are neither Qt nor a Python extension module (each needs its notice)."""
    build = load("build")
    pkg = tmp_path / "PCB-Thermal-Lab-9.9.9-linux-x64"
    for rel in ("_internal/PySide6/Qt/lib/libQt6Core.so.6", "_internal/libffi.so.8", "_internal/numpy/_core/_multiarray_umath.cpython-313-x86_64-linux-gnu.so",
                "_internal/PySide6/QtCore.abi3.so", "LICENSE"):
        (pkg / rel).parent.mkdir(parents=True, exist_ok=True)
        (pkg / rel).write_text("x")
    assert build.write_file_list(pkg, tmp_path / "FILES.txt") == 5
    head = (tmp_path / "FILES.txt").read_text(encoding="utf-8").split("All files")[0]
    assert "libffi.so.8" in head and "libQt6Core" not in head and "_multiarray_umath" not in head and "QtCore.abi3" not in head


def test_files_without_attached_source_are_refused():
    """Mesa's software OpenGL (Windows) and the GTK 3 theme with its libraries (Linux) stay out: their source is not among the attached tarballs."""
    build = load("build")
    for bad in ("_internal/PySide6/opengl32sw.dll", "_internal/PySide6/Qt/plugins/platformthemes/libqgtk3.so", "_internal/libgtk-3.so.0"):
        assert build.FORBIDDEN.search(bad), bad
    assert not build.FORBIDDEN.search("_internal/PySide6/Qt/plugins/platformthemes/libqxdgdesktopportal.so")


def test_workflow_pins_actions_and_attaches_the_source_first(workflow):
    """Every action is pinned to a commit; the source is uploaded before the packages; checksums use the flat names; pre-releases, the Windows console program and the Linux X server are covered."""
    uses = re.findall(r"uses:\s*(\S+)", workflow)
    assert uses and all(re.fullmatch(r"[\w-]+/[\w-]+@[0-9a-f]{40}", u) for u in uses), uses
    release = workflow.split("\n  release:")[1]
    assert release.index("files/qt-source/* --clobber") < release.index("files/PCB-Thermal-Lab-* files/SHA256SUMS.txt --clobber")
    assert "(cd qt-source && sha256sum *.tar.xz)" in release and "--version \"${GITHUB_REF_NAME#v}\"" in release
    assert "--prerelease" in release and "prerelease=true" in workflow
    assert "PCB-Thermal-Lab-cli.exe" in workflow and "xvfb-run -a" in workflow and "FILES-*.txt" in workflow
