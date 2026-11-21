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

import pcbthermal

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
    for needle in ('"pcbthermal/data"', '"pcbthermal/help"', '"ico"', '"licenses"', 'collect_submodules("pyamg", filter=lambda name: ".tests" not in name)', "SOURCE-OFFER.txt",
                   "BUILD-INFO.txt", "copy_metadata", "UNUSED_PLUGINS.search", "unreferenced_libraries(a.binaries", "bindepend.get_imports"):
        assert needle in spec
    for module in ("tools", "research", "releases", "tests", "PySide6.QtWebEngineCore", "PySide6.QtPdf", "PySide6.QtQuick", "PySide6.QtGraphs", "PySide6.QtHttpServer",
                   "PySide6.QtLottie", "PySide6.QtNetworkAuth", "PySide6.QtCanvasPainter", "PySide6.QtQmlCompiler", "PySide6.QtQuick3D", "PySide6.QtVirtualKeyboard",
                   "readline"):
        assert f'"{module}"' in spec
    assert "exclude_binaries=True" in spec and "onefile" not in spec.lower()      # One folder: the Qt libraries stay replaceable files
    # The icons are the committed files of ico/ (the old size-named .ico files no longer exist)
    assert '"ico" / "pcb-board.ico"' in spec and '"ico" / "pcb-board.icns"' in spec
    assert "256x256" not in spec and "make_icns" not in (PKG / "build.py").read_text(encoding="utf-8")
    assert (PKG.parent / "ico" / "pcb-board.ico").exists() and (PKG.parent / "ico" / "pcb-board.icns").exists()


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


def test_replacing_qt_text_has_the_macos_facts_of_the_real_swap_test(tmp_path, monkeypatch):
    """REPLACING-QT.txt says what a real library swap on macOS arm64 (2.9.0 trial package) showed: pip needs Python 3.10 or newer (the system python3 is 3.9), the file inside
    a framework is Versions/A/<Name>, Apple silicon refuses a library with no or a non-matching signature, the wheel's own signature may start without re-signing but breaks the
    seal, so both codesign commands are always run, and the --deep one signs the replaced binding .so files too."""
    build = load("build")
    monkeypatch.setattr(build, "qt_versions", lambda: ("6.12.0", "6.12.0"))
    build.write_notice_files(tmp_path, False)
    text = " ".join((tmp_path / "REPLACING-QT.txt").read_text(encoding="utf-8").split())   # one line: the wrapping is not part of the claim
    for must in ("These wheels are for Python 3.10 or newer", "pip looks for the wheels of the Python it runs on", "system `python3` of macOS is 3.9",
                 "Versions/A/<Name>", "QtGui.framework/Versions/A/QtGui", "no signature or with a signature that does not match its content",
                 # each failure is tied to its own case: the test saw 'missing code signature' for an unsigned file and exit 137 only for a signed file with changed bytes
                 "with no signature the start fails with 'missing code signature'",
                 "a signed file whose bytes were changed) the program is killed with no message (exit code 137)",
                 "should be Python 3.13",
                 "may start without this step", "nested code is modified or invalid", "so always run the two commands",
                 'codesign --force --sign - "PCB Thermal Lab.app/Contents/Frameworks/PySide6/Qt/lib/QtGui.framework"',
                 'codesign --force --deep --sign - "PCB Thermal Lab.app"', "also signs the binding .so files you replaced"):
        assert must in text, must


EXECUTABLES = {"windows-x64": "PCB-Thermal-Lab.exe", "linux-x64": "PCB-Thermal-Lab", "macos-arm64": "PCB Thermal Lab.app/Contents/MacOS/PCB-Thermal-Lab"}


def package_archive(system):
    """!
    @brief The archive name of a fake package of version 9.9.9.
    @param system One of check_release.SYSTEMS.
    @return str.
    """
    return f"PCB-Thermal-Lab-9.9.9-{system}" + (".tar.gz" if system.startswith("linux") else ".zip")


def make_package(folder, system, drop=(), extra=(), offer=None):
    """!
    @brief Write a small package archive with the documents check_release.py looks for.
    @param folder Where to write it.
    @param system One of check_release.SYSTEMS.
    @param drop Members (relative to the package folder) to leave out.
    @param extra Further members (relative to the package folder) to add.
    @param offer Text of SOURCE-OFFER.txt (default: one with both contacts).
    @return pathlib.Path of the archive.
    """
    import io
    import tarfile
    import zipfile
    check = load("check_release")
    top = f"PCB-Thermal-Lab-9.9.9-{system}"
    texts = {m: "text" for m in check.REQUIRED + (EXECUTABLES[system],)}
    if system.startswith("windows"):
        texts["PCB-Thermal-Lab-cli.exe"] = "exe"
    texts["SOURCE-OFFER.txt"] = offer if offer is not None else f"Contact: the Issues page, {check.build.ISSUES_URL}, or by e-mail at {check.build.SECOND_CONTACT}"
    texts["NOTICE.txt"] = f"Contact: {check.build.SECOND_CONTACT}"
    texts.update({m: "x" for m in extra})
    path = folder / package_archive(system)
    members = {f"{top}/{m}": t.encode() for m, t in texts.items() if m not in drop}
    if path.suffix == ".zip":
        with zipfile.ZipFile(path, "w") as z:
            for name, data in members.items():
                z.writestr(name, data)
    else:
        with tarfile.open(path, "w:gz") as t:
            for name, data in members.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                t.addfile(info, io.BytesIO(data))
    return path


def test_check_release_looks_inside_the_archives(tmp_path):
    """Every package must carry the LGPL documents and the licences at the top, its program (and the console program on Windows), no forbidden file, and the
    written offer with both contacts (the trial packages of 2.8.0 still had the TODO text and the Linux one GNU Readline: both are refused)."""
    check = load("check_release")
    results = {s: {"folder": f"PCB-Thermal-Lab-9.9.9-{s}", "executable": EXECUTABLES[s], "os": s.split("-")[0]} for s in check.SYSTEMS}
    for system in check.SYSTEMS:
        assert check.archive_problems(make_package(tmp_path, system), results[system]) == [], system
    assert any("NOTICE.txt is missing" in p for p in check.archive_problems(make_package(tmp_path, "linux-x64", drop=("NOTICE.txt",)), results["linux-x64"]))
    assert any("PCB-Thermal-Lab-cli.exe" in p for p in check.archive_problems(make_package(tmp_path, "windows-x64", drop=("PCB-Thermal-Lab-cli.exe",)),
                                                                             results["windows-x64"]))
    assert any("THIRD-PARTY-NOTICES" in p for p in check.archive_problems(make_package(tmp_path, "macos-arm64", drop=("licenses/Qt/THIRD-PARTY-NOTICES.txt",)),
                                                                         results["macos-arm64"]))
    assert any("must not be shipped" in p for p in check.archive_problems(make_package(tmp_path, "linux-x64", extra=("_internal/libreadline.so.8",)),
                                                                         results["linux-x64"]))
    todo = "Contact: the Issues page, https://github.com/silvapmm/pcb-thermal-lab/issues\n(TODO second contact: ...)"
    assert any("written offer" in p for p in check.archive_problems(make_package(tmp_path, "windows-x64", offer=todo), results["windows-x64"]))
    assert check.archive_problems(make_package(tmp_path, "linux-x64", extra=("licenses/Qt/libreadline-notice.so",)), results["linux-x64"]) == []


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
        make_package(tmp_path, system)
        res = {"version": "9.9.9", "qt": "6.12.0", "pyside": "6.12.0", "archive": package_archive(system), "source_assets": names, "os": system.split("-")[0],
               "folder": f"PCB-Thermal-Lab-9.9.9-{system}", "executable": EXECUTABLES[system]}
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
    for bad in ("_internal/PySide6/opengl32sw.dll", "_internal/PySide6/Qt/plugins/platformthemes/libqgtk3.so", "_internal/libgtk-3.so.0",
                "_internal/libreadline.so.8"):                       # GNU Readline is GPL-3.0 (the Linux trial build of 2.8.0 carried it through CPython's readline module)
        assert build.FORBIDDEN.search(bad), bad
    assert not build.FORBIDDEN.search("_internal/PySide6/Qt/plugins/platformthemes/libqxdgdesktopportal.so")
    for unused in ("PySide6/Qt/plugins/platforms/libqvnc.so", "PySide6/plugins/generic/qtuiotouchplugin.dll", "PySide6/Qt/plugins/generic/libqtuiotouchplugin.so"):
        assert build.UNUSED_PLUGINS.search(unused), unused
    for used in ("PySide6/Qt/plugins/platforms/libqxcb.so", "PySide6/plugins/platforms/qwindows.dll", "PySide6/Qt/plugins/generic/libqevdevmouseplugin.so"):
        assert not build.UNUSED_PLUGINS.search(used), used


def test_libraries_left_by_a_dropped_plugin_are_pruned():
    """The libraries collected only for a binary the spec dropped (the GTK 3 theme: GTK, cairo, Pango, ATK) go; what a kept binary links, directly or not, stays;
    libpython (opened by name by the bootloader), extension modules and plug-ins are never pruned. The graph is a cut of the Linux trial build of 2.8.0."""
    build = load("build")
    links = {"PySide6/Qt/plugins/platforms/libqxcb.so": ["libQt6XcbQpa.so.6"], "PySide6/Qt/lib/libQt6XcbQpa.so.6": ["libxcb-cursor.so.0", "libQt6DBus.so.6"],
             "PySide6/Qt/lib/libQt6DBus.so.6": ["libdbus-1.so.3"], "libdbus-1.so.3": ["libsystemd.so.0"], "libxcb-cursor.so.0": [], "libsystemd.so.0": [],
             "libatk-bridge-2.0.so.0": ["libatk-1.0.so.0", "libdbus-1.so.3"], "libatk-1.0.so.0": [], "libpangocairo-1.0.so.0": ["libcairo.so.2"], "libcairo.so.2": [],
             "libpython3.13.so.1.0": [], "PySide6/QtCore.abi3.so": ["libQt6Core.so.6"], "PySide6/Qt/lib/libQt6Core.so.6": [], "PySide6/Qt/lib/libQt6Network.so.6": [],
             "numpy.libs/libscipy_openblas64_-4b78795a.so": []}
    binaries = [(dest, "/src/" + dest, "BINARY") for dest in links]
    dropped = build.unreferenced_libraries(binaries, lambda src: links[src[len("/src/"):]])
    assert dropped == {"libatk-bridge-2.0.so.0", "libatk-1.0.so.0", "libpangocairo-1.0.so.0", "libcairo.so.2", "PySide6/Qt/lib/libQt6Network.so.6"}
    assert not build.prunable_library("libpython3.13.so.1.0") and not build.prunable_library("PySide6/Qt/plugins/platforms/libqxcb.so")
    assert not build.prunable_library("numpy/_core/_multiarray_umath.cpython-313-x86_64-linux-gnu.so") and build.prunable_library("libX11.so.6")


def test_native_libraries_need_a_notice_and_a_release_build_stops_without_one(tmp_path):
    """Qt, a wheel's vendored libraries, CPython and the libraries its notices cover, ICU and the Microsoft run-time have their notice in the package; a library
    of the build machine (Linux) does not, and a release build stops on it while a trial build only reports it."""
    build = load("build")
    covered = ["_internal/PySide6/Qt/lib/libQt6Core.so.6", "_internal/PySide6/Qt/lib/libicuuc.so.73", "_internal/numpy.libs/libscipy_openblas64_-4b78795a.so",
               "_internal/pillow.libs/libjpeg-6dc8d115.so.62.4.0", "PCB Thermal Lab.app/Contents/Frameworks/PIL/__dot__dylibs/libwebp.7.dylib",
               "_internal/libpython3.13.so.1.0", "_internal/python313.dll", "_internal/python3.dll", "_internal/libffi-8.dll", "_internal/libffi.so.8",
               "_internal/libexpat.so.1", "_internal/libz.so.1", "_internal/VCRUNTIME140_1.dll", "_internal/ucrtbase.dll", "_internal/api-ms-win-crt-math-l1-1-0.dll",
               "_internal/numpy.libs/msvcp140-a4c2229bdc2a2a630acdc095b4d86008.dll", "_internal/PySide6/MSVCP140_2.dll",
               "_internal/numpy/_core/_multiarray_umath.cpython-313-x86_64-linux-gnu.so", "_internal/_ctypes.pyd", "_internal/PySide6/pyside6.abi3.dll"]
    uncovered = ["_internal/libX11.so.6", "_internal/libglib-2.0.so.0", "_internal/libstdc++.so.6", "_internal/libreadline.so.8"]
    assert build.uncovered_native_libraries(covered + uncovered + ["LICENSE", "_internal/base_library.zip"]) == sorted(uncovered)
    pkg = tmp_path / "pkg"
    for rel in covered[:3] + uncovered[:1]:
        (pkg / rel).parent.mkdir(parents=True, exist_ok=True)
        (pkg / rel).write_text("x")
    assert build.check_notices(pkg, release=False) == ["_internal/libX11.so.6"]
    with pytest.raises(SystemExit):
        build.check_notices(pkg, release=True)
    (pkg / uncovered[0]).unlink()
    assert build.check_notices(pkg, release=True) == []


# The shared libraries at the top of the Linux trial package of 2.8.0 (Actions run on ubuntu-22.04, FILES-linux-x64.txt, names only), plus libreadline
LINUX_TOP_LEVEL_LIBRARIES = """libX11-xcb.so.1 libX11.so.6 libXau.so.6 libXcomposite.so.1 libXcursor.so.1 libXdamage.so.1 libXdmcp.so.6 libXext.so.6 libXfixes.so.3 libXi.so.6
libXinerama.so.1 libXrandr.so.2 libXrender.so.1 libatk-1.0.so.0 libatk-bridge-2.0.so.0 libatspi.so.0 libblkid.so.1 libbrotlicommon.so.1 libbrotlidec.so.1 libbsd.so.0
libbz2.so.1.0 libcairo-gobject.so.2 libcairo.so.2 libcap.so.2 libcom_err.so.2 libdatrie.so.1 libdbus-1.so.3 libepoxy.so.0 libexpat.so.1 libffi.so.8 libfontconfig.so.1
libfreetype.so.6 libfribidi.so.0 libgcc_s.so.1 libgcrypt.so.20 libgdk_pixbuf-2.0.so.0 libgio-2.0.so.0 libglib-2.0.so.0 libgmodule-2.0.so.0 libgobject-2.0.so.0
libgpg-error.so.0 libgraphite2.so.3 libgssapi_krb5.so.2 libgthread-2.0.so.0 libharfbuzz.so.0 libjpeg.so.8 libk5crypto.so.3 libkeyutils.so.1 libkrb5.so.3
libkrb5support.so.0 liblz4.so.1 liblzma.so.5 libmd.so.0 libmount.so.1 libpango-1.0.so.0 libpangocairo-1.0.so.0 libpangoft2-1.0.so.0 libpcre.so.3 libpcre2-8.so.0
libpixman-1.so.0 libpng16.so.16 libpython3.13.so.1.0 libreadline.so.8 libselinux.so.1 libstdc++.so.6 libsystemd.so.0 libthai.so.0 libtinfo.so.6 libuuid.so.1
libxcb-cursor.so.0 libxcb-glx.so.0 libxcb-icccm.so.4 libxcb-image.so.0 libxcb-keysyms.so.1 libxcb-randr.so.0 libxcb-render-util.so.0 libxcb-render.so.0
libxcb-shape.so.0 libxcb-shm.so.0 libxcb-sync.so.1 libxcb-util.so.1 libxcb-xfixes.so.0 libxcb-xkb.so.1 libxkbcommon-x11.so.0 libxkbcommon.so.0 libz.so.1
libzstd.so.1""".split()
LINUX_SHIPPED = {"libexpat.so.1", "libffi.so.8", "libpython3.13.so.1.0", "libz.so.1", "libxcb-cursor.so.0", "libxcb-icccm.so.4", "libxcb-image.so.0",
                 "libxcb-keysyms.so.1", "libxcb-render-util.so.0", "libxcb-util.so.1", "libxkbcommon-x11.so.0", "libxkbcommon.so.0"}


def test_linux_leaves_the_desktop_libraries_to_the_system_and_ships_only_what_it_documents():
    """On the real Linux file list of the trial run, 75 of 87 top-level libraries are left to the system (GLib, D-Bus, systemd, libgcrypt, fontconfig, FreeType, libpng,
    libstdc++, zstd, lz4, the X11 and base xcb libraries, GNU Readline, ...) and 12 ship: libpython, what the CPython notices cover (libffi, expat, zlib) and the xcb-util
    and xkbcommon libraries, which have their notice under licenses/_system; the shipped ones leave no library without a notice."""
    build = load("build")
    assert len(LINUX_TOP_LEVEL_LIBRARIES) == 87
    shipped = {n for n in LINUX_TOP_LEVEL_LIBRARIES if not build.left_to_system(n)}
    assert shipped == LINUX_SHIPPED
    assert {"libstdc++.so.6", "libglib-2.0.so.0", "libdbus-1.so.3", "libsystemd.so.0", "libgcrypt.so.20", "libfontconfig.so.1", "libfreetype.so.6", "libpng16.so.16",
            "libzstd.so.1", "liblz4.so.1", "libX11.so.6", "libxcb-xkb.so.1", "libreadline.so.8"} <= set(LINUX_TOP_LEVEL_LIBRARIES) - shipped
    assert build.uncovered_native_libraries(["_internal/" + n for n in shipped]) == []
    # What the rule never touches: a library inside a folder, an extension module, a library of a wheel and the Qt libraries
    for dest in ("PySide6/Qt/lib/libicuuc.so.73", "PySide6/Qt/plugins/platforms/libqxcb.so", "numpy.libs/libscipy_openblas64_-4b78795a.so", "lib-dynload/_ssl.cpython-313-x86_64-linux-gnu.so",
                 "PIL/_imaging.cpython-313-x86_64-linux-gnu.so", "base_library.zip", "PCB-Thermal-Lab"):
        assert not build.left_to_system(dest), dest


def test_the_shipped_system_libraries_have_their_notice_files_and_a_tag_build_stops_without_one(tmp_path):
    """Every shipped library group has a LICENSE under licenses/_system with the MIT/X11 permission text, the build copies them on Linux, and a library outside the
    list (a system library that was not excluded) makes a tag build stop."""
    build = load("build")
    for name in build.SHIPPED_SYSTEM_LIBRARIES:
        text = (PKG / "licenses" / "_system" / name / "LICENSE").read_text(encoding="utf-8")
        assert "Permission is hereby granted, free of charge" in text and "THE SOFTWARE IS PROVIDED" in text, name
    xcb = (PKG / "licenses" / "_system" / "xcb-util" / "LICENSE").read_text(encoding="utf-8")
    for lib in ("libxcb-util", "libxcb-cursor", "libxcb-image", "libxcb-keysyms", "libxcb-render-util", "libxcb-wm"):
        assert lib in xcb, lib
    pkg = tmp_path / "pkg"
    for rel in ("_internal/libxkbcommon.so.0", "_internal/libxcb-cursor.so.0", "_internal/libglib-2.0.so.0"):
        (pkg / rel).parent.mkdir(parents=True, exist_ok=True)
        (pkg / rel).write_text("x")
    assert build.check_notices(pkg, release=False) == ["_internal/libglib-2.0.so.0"]
    with pytest.raises(SystemExit):
        build.check_notices(pkg, release=True)


def test_a_linux_package_without_the_shipped_libraries_fails_the_build(tmp_path, monkeypatch):
    """The failure of the second trial: the build runner had no libxcb-cursor, PyInstaller collected nothing and the package could not start. A file list without it makes
    missing_shipped_libraries name it and check_shipped stop the build (trial or release); the full list passes; other systems are not checked."""
    build = load("build")
    full = [f"_internal/{n}" for n in LINUX_SHIPPED]
    assert build.missing_shipped_libraries(full) == []
    assert build.missing_shipped_libraries([p for p in full if "xcb-cursor" not in p]) == ["libxcb-cursor"]
    assert build.missing_shipped_libraries(["_internal/libxcb-cursor.so.0"]) == [n for n in build.REQUIRED_SHIPPED_LIBRARIES if n != "libxcb-cursor"]
    pkg = tmp_path / "pkg"
    for rel in full:
        if "xcb-cursor" not in rel:
            (pkg / rel).parent.mkdir(parents=True, exist_ok=True)
            (pkg / rel).write_text("x")
    monkeypatch.setattr(build.sys, "platform", "linux")
    with pytest.raises(SystemExit, match="libxcb-cursor"):
        build.check_shipped(pkg)
    (pkg / "_internal" / "libxcb-cursor.so.0").write_text("x")
    build.check_shipped(pkg)
    monkeypatch.setattr(build.sys, "platform", "darwin")
    build.check_shipped(tmp_path / "empty")


def test_spec_and_workflow_apply_the_system_policy_and_pin_python():
    """The spec drops the libraries left to the system before it prunes; the workflow pins Python to an exact patch release for all three systems and installs on the
    Linux runner the system packages and the shipped libraries (to be collected), then removes the shipped ones before the self-test; BUILD-INFO records the Python version."""
    spec = (PKG / "PCB-Thermal-Lab.spec").read_text(encoding="utf-8")
    assert spec.index("left_to_system(b[0])") < spec.index("unreferenced_libraries(a.binaries")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert re.search(r"python-version: '3\.13\.\d+'", workflow) and workflow.count("python-version") == 1
    apt = workflow.split("sudo apt-get install -y")[1].split("- name:")[0]
    # The build runner needs the libraries the package ships (PyInstaller collects only what is installed), and they are removed again before the self-test
    for shipped in ("libxcb-cursor0", "libxcb-icccm4", "libxcb-image0", "libxcb-keysyms1", "libxcb-render-util0", "libxcb-util1", "libxkbcommon-x11-0"):
        assert shipped in apt
        assert workflow.count(shipped) >= 2
    removal = workflow.split("Remove the shipped libraries from the runner")[1].split("- name:")[0]
    assert "apt-get remove -y $SHIPPED" in removal and "apt-get -s remove" in removal
    assert workflow.index("Remove the shipped libraries") < workflow.index("Self-test the packed program (Linux and macOS)")
    assert workflow.index("Build the package") < workflow.index("Remove the shipped libraries")
    for needed in ("libegl1", "libglib2.0-0", "libdbus-1-3", "libfontconfig1"):
        assert needed in apt
    assert "Python: {py}" in (PKG / "build.py").read_text(encoding="utf-8")


def test_qt_wheels_are_quoted_through_licenses_qt_on_every_system(monkeypatch, tmp_path):
    """A Qt wheel that carries LicenseRef-Qt-Commercial.txt (Windows) is quoted like the others: '(covered by Qt/)', no copy of the commercial note."""
    build = load("build")
    note = tmp_path / "site" / "shiboken6-6.12.0.dist-info" / "licenses" / "LicenseRef-Qt-Commercial.txt"
    note.parent.mkdir(parents=True)
    note.write_text("Licensees holding valid commercial Qt licenses")

    class Dist:
        """!
        @brief A fake installed distribution with one licence file.
        """

        metadata = {"Name": "shiboken6", "License-Expression": "LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only"}
        version = "6.12.0"
        files = [pathlib.PurePosixPath("shiboken6-6.12.0.dist-info/licenses/LicenseRef-Qt-Commercial.txt")]

        def locate_file(self, f):
            """!
            @brief Where a file of the distribution is.
            @param f Relative path.
            @return pathlib.Path.
            """
            return tmp_path / "site" / f

    import sys
    base = tmp_path / "base"
    stdlib = base / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}"
    stdlib.mkdir(parents=True)
    (stdlib / "LICENSE.txt").write_text("PSF")
    (base / "LICENSE.txt").write_text("PSF")
    monkeypatch.setattr(build.sys, "base_prefix", str(base))
    monkeypatch.setattr(build, "python_notices", lambda v: "notices")
    monkeypatch.setattr(build, "system_notices", lambda root: [])
    index = build.collect_licences(tmp_path / "staging", {"shiboken6": Dist()})
    assert "shiboken6-6.12.0: LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only; 0 licence file(s) (covered by Qt/)" in index
    assert not (tmp_path / "staging" / "licenses" / "shiboken6-6.12.0").exists()


def test_licence_texts_keep_their_bytes_on_every_checkout():
    """The licence texts are not converted to CRLF on a Windows checkout (the Windows trial package of 2.8.0 carried a GPL text whose SHA-256 was not the one
    licenses/Qt/SOURCES.txt records)."""
    assert "packaging/licenses/** -text" in (ROOT / ".gitattributes").read_text(encoding="utf-8").splitlines()


def test_workflow_pins_actions_and_attaches_the_source_first(workflow):
    """Every action is pinned to a commit; the source is uploaded before the packages; checksums use the flat names; pre-releases, the Windows console program and the Linux X server are covered."""
    uses = re.findall(r"uses:\s*(\S+)", workflow)
    assert uses and all(re.fullmatch(r"[\w-]+/[\w-]+@[0-9a-f]{40}", u) for u in uses), uses
    release = workflow.split("\n  release:")[1]
    assert release.index("files/qt-source/* --clobber") < release.index("files/PCB-Thermal-Lab-* files/SHA256SUMS.txt --clobber")
    assert "(cd qt-source && sha256sum *.tar.xz)" in release and "--version \"${GITHUB_REF_NAME#v}\"" in release
    assert "--prerelease" in release and "prerelease=true" in workflow
    assert "PCB-Thermal-Lab-cli.exe" in workflow and "xvfb-run -a" in workflow and "FILES-*.txt" in workflow


def test_only_the_qt_modules_the_program_imports_are_allowed():
    """A positive list of Qt modules: the three the program imports (and only those, checked in pcbthermal/), Svg and the Linux platform support are allowed; every GPL-3-only
    module and every other add-on (Graphs, Charts, Quick3D, SpatialAudio, Network, ...) is reported, whatever the file name style of the system."""
    build = load("build")
    imported = set()
    for path in (ROOT / "pcbthermal").rglob("*.py"):
        imported |= set(re.findall(r"(?:from|import)\s+PySide6\.(Qt\w+)", path.read_text(encoding="utf-8")))
    assert imported == {"QtCore", "QtGui", "QtWidgets"}
    assert {m for m in ("Core", "Gui", "Widgets") if m in build.ALLOWED_QT_MODULES} == {"Core", "Gui", "Widgets"}
    for bad in ("PySide6/Qt/lib/libQt6Graphs.so.6", "PySide6/Qt6Charts.dll", "PySide6/Qt/lib/QtQuick3D.framework/QtQuick3D", "PySide6/QtSpatialAudio.abi3.so",
                "PySide6/Qt6DataVisualization.dll", "PySide6/Qt/lib/libQt6HttpServer.so.6.12.0", "PySide6/Qt6NetworkAuth.dll", "PySide6/Qt6Network.dll"):
        assert build.unexpected_qt_modules([bad]), bad
    for good in ("PySide6/Qt/lib/libQt6Core.so.6", "PySide6/Qt/lib/libQt6Core.so.6.12.0", "PySide6/Qt6Gui.dll", "PySide6/QtWidgets.abi3.so",
                 "PySide6/Qt/lib/QtSvg.framework/QtSvg", "PySide6/Qt/lib/libQt6XcbQpa.so.6", "PySide6/Qt/lib/libQt6DBus.so.6", "PySide6/Qt/lib/libQt6WaylandClient.so.6",
                 "PySide6/Qt/plugins/platforms/libqxcb.so", "licenses/Qt/LGPL-3.0.txt"):
        assert not build.unexpected_qt_modules([good]), good
    # A licence folder is never a module
    assert not build.unexpected_qt_modules(["licenses/Qt/Qt6Graphs.dll"])


def test_every_forbidden_family_is_in_the_forbidden_list_and_the_spec_excludes():
    """FORBIDDEN names the GPL-3-only Qt modules, FFmpeg, QtPdf, WebEngine, the TLS plug-ins and Readline; the spec excludes the same modules from the analysis."""
    build = load("build")
    for bad in ("Qt6Graphs", "Qt6Charts", "Qt6DataVisualization", "Qt6Quick3D", "Qt6HttpServer", "Qt6Lottie", "Qt6VirtualKeyboard", "Qt6CanvasPainter", "Qt6NetworkAuth",
                "Qt6QmlCompiler", "Qt6WebEngineCore", "Qt6Pdf", "libqpdf.so", "libavcodec.so.61", "libswscale.so.8", "libqopensslbackend.so", "plugins/tls/x", "libreadline.so.8"):
        assert build.FORBIDDEN.search(bad), bad
    spec = (PKG / "PCB-Thermal-Lab.spec").read_text(encoding="utf-8")
    for module in ("QtGraphs", "QtCharts", "QtDataVisualization", "QtQuick3D", "QtHttpServer", "QtLottie", "QtVirtualKeyboard", "QtCanvasPainter", "QtNetworkAuth",
                   "QtQmlCompiler", "QtWebEngineCore", "QtPdf", "QtSpatialAudio", "QtMultimedia"):
        assert f"PySide6.{module}" in spec, module
    assert "check_qt_modules(folder, args.release)" in (PKG / "build.py").read_text(encoding="utf-8")


def test_release_notes_have_a_first_run_section_with_the_checksums(tmp_path):
    """The draft notes keep the CHANGELOG section and add the macOS and Windows confirmations, the glibc requirement, the SHA-256 of each package, the versions of Qt and
    PySide and the pointer to REPLACING-QT.txt; the tarballs of the sums file are not repeated in the table; without a package line the call fails."""
    notes = load("release_notes")
    d1, d2, d3 = "a" * 64, "b" * 64, "c" * 64
    sums = f"{d1}  PCB-Thermal-Lab-2.9.0-windows-x64.zip\n{d2}  PCB-Thermal-Lab-2.9.0-linux-x64.tar.gz\n{d3}  PCB-Thermal-Lab-2.9.0-macos-arm64.zip\n{'d' * 64}  qtbase-everywhere-src-6.12.0.tar.xz\n"
    pairs = notes.package_sums(sums)
    assert [n for n, _ in pairs] == ["PCB-Thermal-Lab-2.9.0-windows-x64.zip", "PCB-Thermal-Lab-2.9.0-linux-x64.tar.gz", "PCB-Thermal-Lab-2.9.0-macos-arm64.zip"]
    text = notes.first_run_section(pairs, "6.12.0", "6.12.0")
    for must in ("Open Anyway", "Privacy & Security", "macOS 14", "authenticate", "More info", "Run anyway", "glibc 2.35", "Ubuntu 22.04", "Debian 12", "Fedora 36",
                 "Ubuntu 20.04", "Debian 11", "RHEL", "run from source", d1, d2, d3, "Qt 6.12.0", "PySide6 6.12.0", "REPLACING-QT.txt"):
        assert must in text, must
    assert "qtbase" not in text
    # With the real CHANGELOG: the section of the version is kept at the top and the new sections follow it
    log = tmp_path / "sums.txt"
    log.write_text(sums, encoding="utf-8")
    info = tmp_path / "info.json"
    info.write_text('{"qt": "6.12.0", "pyside": "6.12.0", "source_assets": ["qtbase-everywhere-src-6.12.0.tar.xz"]}', encoding="utf-8")
    out = tmp_path / "notes.md"
    changelog = ROOT / "CHANGELOG.md"
    version = pcbthermal.__version__                                                   # the version of the tree: after the bump its section exists and Unreleased is empty
    assert notes.main([version, "--changelog", str(changelog), "--build-result", str(info), "--sums", str(log), "-o", str(out)]) == 0
    body = out.read_text(encoding="utf-8")
    released = notes.extract(changelog.read_text(encoding="utf-8"), version)
    assert released.strip() and body.startswith(released) and body.index("## Qt and PySide source") < body.index("## First run") and d3 in body
    empty = tmp_path / "empty.txt"
    empty.write_text("nothing\n", encoding="utf-8")
    assert notes.main([version, "--changelog", str(changelog), "--build-result", str(info), "--sums", str(empty), "-o", str(out)]) == 1
    assert "--sums files/SHA256SUMS.txt" in WORKFLOW.read_text(encoding="utf-8")


def test_packaging_readme_keeps_the_never_rules_and_states_the_glibc_requirement():
    """packaging/README.md and the README Download section say what the Linux package needs and what is never done."""
    text = (PKG / "README.md").read_text(encoding="utf-8")
    for rule in ("never add an EULA that forbids reverse engineering", "never check Qt file hashes at run time", "never switch to onefile", "glibc 2.35 or newer",
                 "Ubuntu 22.04+, Debian 12+, Fedora 36+", "run from source with pip"):
        assert rule in text, rule
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "glibc 2.35" in readme and "Ubuntu 20.04" in readme and "run from source" in readme


def test_build_step_always_enforces_the_checks_and_write_permission_stays_on_the_release_job():
    """The 'Build the package' step has no tag condition and always passes --release (a trial must fail where a tag would); contents: write is only on the release job."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    step = workflow[workflow.index("- name: Build the package"):]
    run = [line for line in step.splitlines() if line.strip().startswith("run:")][0]
    assert run.strip() == "run: python packaging/build.py --release"
    assert "startsWith" not in run
    assert workflow.count("contents: write") == 1
    assert workflow.index("contents: write") > workflow.index("release:")


def test_qt_module_list_refuses_network_accepts_opengl_and_is_closed_under_needs(tmp_path):
    """Network is not on the list (a release check names it); OpenGL is; every module an allowed one needs is allowed too."""
    build = load("build")
    assert "Network" not in build.ALLOWED_QT_MODULES and "OpenGL" in build.ALLOWED_QT_MODULES
    (tmp_path / "Qt6Network.dll").write_text("x")
    (tmp_path / "libQt6OpenGL.so.6").write_text("x")
    with pytest.raises(SystemExit, match="Network"):
        build.check_qt_modules(tmp_path, True)
    assert build.check_qt_modules(tmp_path, False) == ["Network"]
    (tmp_path / "Qt6Network.dll").unlink()
    assert build.check_qt_modules(tmp_path, True) == []
    for module, needs in build.QT_MODULE_NEEDS.items():
        assert module in build.ALLOWED_QT_MODULES
        assert set(needs) <= build.ALLOWED_QT_MODULES, module


def test_unused_qt_network_files_are_dropped_by_the_spec_pattern():
    """The pattern of the spec matches every QtNetwork entry of the three systems and nothing of the other modules."""
    build = load("build")
    for name in ("PySide6/Qt6Network.dll", "PySide6/Qt/lib/libQt6Network.so.6", "libQt6Network.so.6", "PySide6/Qt/lib/QtNetwork.framework/Versions/A/QtNetwork",
                 "PySide6/Qt/lib/QtNetwork.framework", "QtNetwork"):
        assert build.UNUSED_QT_LIBRARIES.search(name), name
    for name in ("PySide6/Qt6Core.dll", "libQt6OpenGL.so.6", "PySide6/QtNetworkAuth.abi3.so", "QtCore.framework/QtCore"):
        assert not build.UNUSED_QT_LIBRARIES.search(name), name


def test_a_broken_symbolic_link_stops_the_build(tmp_path):
    """check_symlinks fails on a link to a missing target and accepts a good one."""
    build = load("build")
    (tmp_path / "real.so").write_text("x")
    (tmp_path / "good.so.6").symlink_to("real.so")
    build.check_symlinks(tmp_path)
    (tmp_path / "libQt6Network.so.6").symlink_to("PySide6/Qt/lib/libQt6Network.so.6")
    with pytest.raises(SystemExit, match="libQt6Network.so.6"):
        build.check_symlinks(tmp_path)
