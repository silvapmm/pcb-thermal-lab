#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file build.py
@brief Build the downloadable package of PCB Thermal Lab for the system it runs on: `python packaging/build.py`.
@details What it does, in order:
         1. makes its own virtual environment `packaging/.venv-build` and installs the run-time lines of `requirements.txt` (no tests; PySide6 is replaced by
            PySide6-Essentials, the same Qt modules without QtWebEngine and the other add-ons) and PyInstaller (`packaging/requirements-build.txt`);
         2. prepares the licence material (a staging folder): `licenses/Qt` (LGPL-3.0, GPL-3.0 and the Qt third-party notices made from the Qt source tarballs,
            `qt_sources.py`), the licence files of every bundled package copied from its `dist-info` (the build FAILS when one has none), `NOTICE.txt`,
            `SOURCE-OFFER.txt`, `REPLACING-QT.txt`, `BUILD-INFO.txt` (the exact versions) and, on macOS, the `.icns` icon;
         3. runs PyInstaller on `packaging/PCB-Thermal-Lab.spec` (one folder, not one file; a `.app` on macOS) and FAILS when the output holds a file of a Qt
            module or library that must not be shipped (GPL-3-only modules, FFmpeg, QtPdf, WebEngine, TLS plug-ins: `FORBIDDEN`);
         4. assembles `PCB-Thermal-Lab-<version>-<os>-<arch>/` (the program, `LICENSE`, `licenses/`, `SOURCE-OFFER.txt`, `BUILD-INFO.txt`), archives it
            (`.zip` on Windows and macOS, `.tar.gz` on Linux, which keeps the execute bits) and writes `SHA256SUMS.txt` and `BUILD-RESULT.json`;
         5. with `--selftest`, extracts the archive and runs `--selftest` of the program from it.
         Outputs are in `packaging/dist/` (the archive, `SHA256SUMS.txt`, `BUILD-RESULT.json`, `FILES.txt` (the file list, native libraries outside Qt first) and `qt-source/`, the exact Qt and PySide source that the release
         carries as assets, always) and `packaging/build/` (git-ignored). Nothing is uploaded or published here.
"""

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile
from datetime import date
from importlib import metadata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qt_sources  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "packaging"
VENV = PKG / ".venv-build"
DIST = PKG / "dist"
WORK = PKG / "build"
PRODUCT = "PCB-Thermal-Lab"
APP_NAME = "PCB Thermal Lab.app"
# The wheel "PySide6" pulls the add-ons (QtWebEngine alone is 645 MB); the program imports only QtCore, QtGui and QtWidgets, which PySide6-Essentials has
SUBSTITUTIONS = {"pyside6": "PySide6-Essentials"}
# Build tools whose own code goes into the program (the PyInstaller bootloader and run-time hooks): their licence is quoted, but NOT that of their requirements
# (altgraph, macholib, setuptools, pyinstaller-hooks-contrib run only at build time and are not in the package; checked in the Analysis table of a build)
BUILD_TOOLS = ("pyinstaller",)
# Native libraries that a Qt wheel brings for one system and whose source is not in the attached Qt tarballs: their licence text comes from
# packaging/licenses/_system/<name>/ (ICU, which QtCore links on Linux; the file is for the ICU major version named here, the build fails on another one)
SYSTEM_NOTICES = {"ICU": (re.compile(r"^libicu(data|uc|i18n)\.so\.(\d+)"), "73")}
# The incorporated-software notices of CPython (libmpdec, expat, libffi, zlib, mimalloc, HACL*, ...): the LICENSE file of the interpreter does NOT list them;
# they are in Doc/license.rst of the exact CPython release, fetched by the build (the build fails when it cannot be fetched)
PYTHON_NOTICES_URL = "https://raw.githubusercontent.com/python/cpython/v{version}/Doc/license.rst"
# Files that must not be in the package: the GPL-3-only Qt modules (a bundle containing one would have to be GPL-3), FFmpeg (Qt Multimedia), QtPdf (and the image-format
# plug-in that links it), WebEngine, the QML and Quick modules, the TLS plug-ins (OpenSSL), and the Qt translations (`.qm`: the program is English only, and their source, qttranslations, is not among the attached
# tarballs). The program imports QtCore, QtGui and QtWidgets only. Two more whose code is not in the attached Qt source: opengl32sw.dll (Windows: Mesa's software
# OpenGL, which a widgets program never loads) and the GTK 3 platform theme (Linux: it would bring the GTK, GLib, Pango and cairo libraries of the build machine).
FORBIDDEN = re.compile(r"Qt6?(WebEngine|Pdf|Multimedia|Graphs|Charts|DataVisualization|Quick|VirtualKeyboard|Lottie|HttpServer|NetworkAuth|Qml|CanvasPainter|Grpc|Mqtt|Coap)"
                       r"|libqpdf|qpdf\.|libav(codec|format|util|filter|device)|libsw(resample|scale)|qopenssl|/tls/|\\tls\\|\.qm$"
                       r"|opengl32sw|libqgtk3|libgtk-3|libgdk-3", re.IGNORECASE)
QT_COVERED = ("pyside6_essentials", "pyside6", "shiboken6")        # Distributions whose licence texts are licenses/Qt (their wheels carry none)
# THE SECOND CONTACT of the written offer (SOURCE-OFFER.txt): a way to reach the maintainer that does not depend on GitHub, for the case that the repository is deleted
# or made private while the offer (three years) is still running. Given by the maintainer, who authorised publishing this address in the packages, the repository and the
# About box. Every build refuses to run if it is ever emptied.
SECOND_CONTACT = "silva.pmm@gmail.com"
ISSUES_URL = "https://github.com/silvapmm/pcb-thermal-lab/issues"
LICENCE_PATTERNS = re.compile(r"^(LICEN[CS]E|COPYING|NOTICE|AUTHORS)", re.IGNORECASE)


def version():
    """!
    @brief The program version, read from pcbthermal/__init__.py (not imported: the build environment may not be the one that has the libraries).
    @return str "X.Y.Z".
    """
    return re.search(r'__version__\s*=\s*"([^"]+)"', (ROOT / "pcbthermal" / "__init__.py").read_text(encoding="utf-8")).group(1)


def platform_tag():
    """!
    @brief The system and the processor as they are written in the file name of the package.
    @return tuple (os, arch, archive extension), for example ("macos", "arm64", ".zip").
    """
    machine = platform.machine().lower()
    arch = {"amd64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(machine, machine)
    if sys.platform == "win32":
        return "windows", arch, ".zip"
    if sys.platform == "darwin":
        return "macos", arch, ".zip"
    return "linux", arch, ".tar.gz"


def package_name():
    """!
    @brief Name of the package folder and of the archive without its extension: PCB-Thermal-Lab-<version>-<os>-<arch>.
    @return str.
    """
    osname, arch, _ = platform_tag()
    return f"{PRODUCT}-{version()}-{osname}-{arch}"


def run(cmd, **kw):
    """!
    @brief Run a command, echoing it, and stop the build when it fails.
    @param cmd List of arguments.
    @param kw Extra arguments of subprocess.run.
    @return subprocess.CompletedProcess.
    """
    print("+", " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def venv_python():
    """!
    @brief The interpreter of the build environment.
    @return Path.
    """
    return VENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def runtime_requirements():
    """!
    @brief The run-time lines of requirements.txt (the tests are left out; PySide6 is substituted, see SUBSTITUTIONS).
    @return list of str, requirement lines.
    """
    out = []
    for raw in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name = re.match(r"[A-Za-z0-9._-]+", line).group(0)
        if name.lower().startswith("pytest"):
            continue
        out.append(SUBSTITUTIONS.get(name.lower(), name) + line[len(name):])
    return out


def make_venv(reuse):
    """!
    @brief Create the build environment and install the libraries (skipped with --reuse-venv when it exists).
    @param reuse True to keep an existing environment as it is.
    """
    if reuse and venv_python().exists():
        return
    if VENV.exists():
        shutil.rmtree(VENV)
    run([sys.executable, "-m", "venv", VENV])
    WORK.mkdir(parents=True, exist_ok=True)
    req = WORK / "requirements-runtime.txt"
    req.write_text("\n".join(runtime_requirements()) + "\n", encoding="utf-8")
    run([venv_python(), "-m", "pip", "install", "--upgrade", "pip"])
    run([venv_python(), "-m", "pip", "install", "-r", req, "-r", PKG / "requirements-build.txt"])


def site_packages():
    """!
    @brief The folder of the packages of the build environment.
    @return Path.
    """
    out = subprocess.run([str(venv_python()), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"], check=True, capture_output=True, text=True)
    return Path(out.stdout.strip())


def normalise(name):
    """!
    @brief Normalised distribution name (lower case, one kind of separator).
    @param name Name as written.
    @return str.
    """
    return re.sub(r"[-_.]+", "_", name).lower()


def bundled_distributions(site):
    """!
    @brief The distributions that go into the program: the run-time requirements and everything they require (without extras), plus the build tools quoted
           (BUILD_TOOLS alone, not their requirements).
    @param site Folder of the packages of the build environment.
    @return dict normalised name -> metadata.Distribution.
    """
    found = {normalise(d.metadata["Name"]): d for d in metadata.distributions(path=[str(site)])}
    todo = [normalise(re.match(r"[A-Za-z0-9._-]+", r).group(0)) for r in runtime_requirements()]
    # The build tools themselves only: their requirements are build-time code, not in the package
    out = {normalise(t): found[normalise(t)] for t in BUILD_TOOLS if normalise(t) in found}
    while todo:
        name = todo.pop()
        if name in out or name not in found:
            continue
        out[name] = found[name]
        for req in found[name].requires or []:
            if "extra ==" in req:
                continue
            todo.append(normalise(re.match(r"[A-Za-z0-9._-]+", req).group(0)))
    return out


def licence_files(dist):
    """!
    @brief The licence files a distribution carries in its dist-info (LICENSE, COPYING, NOTICE, AUTHORS, also under licenses/ or LICENSES/).
    @param dist importlib.metadata.Distribution.
    @return list of (relative path inside the distribution's licence folder, absolute Path).
    """
    out = []
    for f in dist.files or []:
        parts = f.parts
        if ".dist-info" not in parts[0] and ".egg-info" not in parts[0]:
            continue
        if LICENCE_PATTERNS.match(f.name) or any(p.lower() in ("licenses", "license") for p in parts[1:-1]):
            out.append((Path(*parts[1:]), Path(dist.locate_file(f))))
    return out


def collect_licences(staging, dists):
    """!
    @brief Copy the licence files of every bundled distribution to staging/licenses/<name>-<version>/ and write licenses/INDEX.txt.
    @param staging Staging folder.
    @param dists dict from bundled_distributions().
    @return list of str, the lines of INDEX.txt.
    @throws SystemExit If a bundled distribution has no licence file (a licence file must go with every copy). Qt and PySide are covered by licenses/Qt; a
            library whose wheel carries none gets its text from packaging/licenses/_fallback/<name>/.
    """
    root = staging / "licenses"
    index = ["Licences of the software in this package.",
             "Qt (PySide 6, shiboken 6) is under the GNU LGPL v3: see Qt/ and ../SOURCE-OFFER.txt. The other folders are copied from the installed packages.", ""]
    missing = []
    for name, d in sorted(dists.items()):
        label = f"{d.metadata['Name']}-{d.version}"
        files = [(rel, src) for rel, src in licence_files(d) if src.is_file()]
        for rel, src in files:
            dest = root / label / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        note = ""
        if not files and name in QT_COVERED:
            note = " (covered by Qt/)"
        elif not files and (PKG / "licenses" / "_fallback" / d.metadata["Name"] / "LICENSE.txt").is_file():
            (root / label).mkdir(parents=True, exist_ok=True)
            shutil.copy2(PKG / "licenses" / "_fallback" / d.metadata["Name"] / "LICENSE.txt", root / label / "LICENSE.txt")
            note = " (the wheel has no licence file: the text of the project repository, packaging/licenses/_fallback)"
        elif not files:
            missing.append(label)
        licence = d.metadata.get("License-Expression") or d.metadata.get("License") or "; ".join(c for c in d.metadata.get_all("Classifier") or [] if c.startswith("License"))
        licence = " ".join(str(licence).split())[:200]
        index.append(f"{label}: {licence or 'not stated in the metadata'}; {len(files)} licence file(s){note}")
    if missing:
        raise SystemExit("error: no licence file for the bundled " + ", ".join(missing) + ": add its text under packaging/licenses/_fallback/<name>/LICENSE.txt")
    # Python itself (PSF licence): the text sits in the standard library folder of the interpreter that made the environment
    psf = Path(sys.base_prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "LICENSE.txt"
    if sys.platform == "win32":
        psf = Path(sys.base_prefix) / "LICENSE.txt"
    if not psf.is_file():
        raise SystemExit(f"error: the PSF licence text of Python was not found at {psf}")
    (root / "Python").mkdir(parents=True, exist_ok=True)
    shutil.copy2(psf, root / "Python" / "LICENSE.txt")
    # LICENSE.txt holds the PSF licence and the history only; the notices of the code CPython incorporates are in its documentation
    (root / "Python" / "INCORPORATED-SOFTWARE.rst").write_text(python_notices(platform.python_version()), encoding="utf-8")
    index.append(f"Python {platform.python_version()}: PSF licence, Python/LICENSE.txt; the notices of the software CPython incorporates (libmpdec, expat, libffi, zlib, "
                 "OpenSSL, mimalloc, HACL*, ...) in Python/INCORPORATED-SOFTWARE.rst (Doc/license.rst of that CPython release)")
    for name, line in system_notices(root):
        index.append(f"{name}: {line}")
    (root / "INDEX.txt").write_text("\n".join(index) + "\n", encoding="utf-8")
    return index


def python_notices(py_version):
    """!
    @brief The section "Licenses and Acknowledgements for Incorporated Software" (with the PSF terms before it) of Doc/license.rst of one CPython release.
    @param py_version Python version, for example "3.13.5".
    @return str The text of Doc/license.rst of that release.
    @throws SystemExit When it cannot be fetched or does not hold the incorporated-software section (the package must not ship without these notices).
    """
    import urllib.request

    url = PYTHON_NOTICES_URL.format(version=py_version)
    try:
        text = urllib.request.urlopen(url, timeout=60).read().decode("utf-8")
    except OSError as exc:
        raise SystemExit(f"error: the CPython notices could not be fetched from {url}: {exc}")
    if "Licenses and Acknowledgements for Incorporated Software" not in text:
        raise SystemExit(f"error: {url} has no section on the incorporated software")
    return f"Fetched from {url} by packaging/build.py\n\n{text}"


def system_notices(root):
    """!
    @brief Copy the licence of a native library that the Qt wheel of this system bundles and whose source is not in the Qt tarballs (SYSTEM_NOTICES; ICU on Linux).
    @param root The licenses/ folder of the staging area.
    @return list of (name, line of INDEX.txt) for the notices copied.
    @throws SystemExit When the wheel bundles another major version than the text in packaging/licenses/_system/ is for.
    """
    qt_lib = site_packages() / "PySide6" / "Qt" / "lib"
    names = [p.name for p in qt_lib.iterdir()] if qt_lib.is_dir() else []
    out = []
    for name, (pattern, major) in SYSTEM_NOTICES.items():
        majors = {m.group(2) for m in (pattern.match(n) for n in names) if m}
        if not majors:
            continue
        if majors != {major}:
            raise SystemExit(f"error: the Qt wheel bundles {name} {sorted(majors)}, the text in packaging/licenses/_system/{name} is for {major}: replace it")
        shutil.copytree(PKG / "licenses" / "_system" / name, root / name, dirs_exist_ok=True)
        out.append((name, f"{name} {major} (bundled by the Qt wheel of this system), {name}/LICENSE"))
    return out


def qt_versions():
    """!
    @brief The versions of Qt and PySide in the build environment.
    @return tuple (PySide6 version, Qt version).
    """
    out = subprocess.run([str(venv_python()), "-c", "import PySide6; from PySide6.QtCore import qVersion; print(PySide6.__version__, qVersion())"],
                         check=True, capture_output=True, text=True).stdout.split()
    return out[0], out[1]


def source_assets(qt, pyside):
    """!
    @brief The names of the source tarballs that every release carries as assets.
    @param qt Qt version.
    @param pyside PySide6 version.
    @return list of str.
    """
    return [name for name, _ in qt_sources.urls(qt, pyside, wayland=True)]


def pinned_versions():
    """!
    @brief The exact versions pinned in packaging/requirements-build.txt (name == version lines).
    @return dict normalised name -> version string.
    """
    out = {}
    for raw in (PKG / "requirements-build.txt").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*([A-Za-z0-9._-]+)\s*==\s*([A-Za-z0-9.+!-]+)", raw)
        if m:
            out[normalise(m.group(1))] = m.group(2)
    return out


def verify_pins():
    """!
    @brief Check that the libraries installed in the build environment are exactly the pinned ones, and that the Qt version they load is the one whose tarballs the release attaches.
    @return tuple (PySide6 version, Qt version).
    @throws SystemExit When an installed version differs from the pin, or PySide6 and Qt are not the same version (the tarballs are named by the Qt version read from the loaded library).
    """
    site = site_packages()
    found = {normalise(d.metadata["Name"]): d.version for d in metadata.distributions(path=[str(site)])}
    pins = pinned_versions()
    for needed in ("pyside6_essentials", "shiboken6", "pyinstaller"):
        if needed not in pins:
            raise SystemExit(f"error: {needed} is not pinned with == in packaging/requirements-build.txt")
    bad = [f"{n}: installed {found.get(n)}, pinned {v}" for n, v in pins.items() if found.get(n) != v]
    if bad:
        raise SystemExit("error: the build environment does not match packaging/requirements-build.txt:\n  " + "\n  ".join(bad))
    pyside, qt = qt_versions()
    if pyside != pins["pyside6_essentials"] or qt != pyside:
        raise SystemExit(f"error: PySide6 {pyside} loads Qt {qt}; the pin is {pins['pyside6_essentials']} and Qt and PySide must be the same version (the attached source is named by it)")
    return pyside, qt


def write_notice_files(staging, release):
    """!
    @brief Write NOTICE.txt (LGPL 4(a)), SOURCE-OFFER.txt and REPLACING-QT.txt of the package.
    @param staging Staging folder.
    @param release True for the build of a tag, False for a trial build (both carry the same contact; SECOND_CONTACT may never be empty).
    @throws ValueError If SECOND_CONTACT is empty.
    """
    pyside, qt = qt_versions()
    minor = ".".join(qt.split(".")[:2])
    tag = f"v{version()}"
    assets = "\n".join(f"    {n}" for n in source_assets(qt, pyside))
    # Every release carries the exact tarballs (maintainer's decision): there is no mode without them
    where = (f"The complete corresponding source of exactly these versions is attached to the release page of this version of the program:\n"
             f"  https://github.com/silvapmm/pcb-thermal-lab/releases/tag/{tag}\nas these files (their SHA-256 sums are in QT-SOURCE-SHA256.txt in the same place):\n{assets}\n"
             "(qtwayland is needed only for the Linux package.) The Qt Project publishes the same files, and you may use them too:")
    # The written offer needs a second contact that does not depend on GitHub: never write an offer without it
    if not SECOND_CONTACT:
        raise ValueError("SECOND_CONTACT in packaging/build.py is empty: the written offer needs a contact that does not depend on GitHub")
    contact = f"Contact: the Issues page, {ISSUES_URL}, or by e-mail at {SECOND_CONTACT}"
    (staging / "NOTICE.txt").write_text(f"""PCB Thermal Lab {version()}: notice
=====================================
This program uses Qt {qt} and PySide6 {pyside} (Qt for Python), Copyright (c) The Qt Company Ltd. and other contributors, under the GNU Lesser General
Public License version 3. The texts are in licenses/Qt/ (LGPL-3.0.txt and GPL-3.0.txt). Source: see SOURCE-OFFER.txt. You may replace the Qt and PySide
libraries of this package with your own build: see REPLACING-QT.txt. The notices of the third-party code inside Qt are in licenses/Qt/THIRD-PARTY-NOTICES.txt and
the licences of the other libraries in licenses/ (INDEX.txt lists them). The program itself, PCB Thermal Lab, is Copyright (c) 2025-2026 Pedro Silva (PMS Labs)
under the MIT License (LICENSE). Contact: {SECOND_CONTACT}, or the Issues page, {ISSUES_URL}.
""", encoding="utf-8")
    (staging / "SOURCE-OFFER.txt").write_text(f"""Source of Qt and PySide 6 in this package, and the written offer
=================================================================

PCB Thermal Lab {version()} is a Python program (MIT License, see LICENSE) that uses Qt {qt} through PySide 6 (Qt for Python) {pyside}. They are free software
under the GNU Lesser General Public License version 3. NO Qt or PySide file in this package was modified: the libraries are the files of the official PyPI wheels
PySide6_Essentials {pyside} and shiboken6 {pyside} for this system, as published by The Qt Company.

{where}
  https://download.qt.io/official_releases/qt/{minor}/{qt}/submodules/
  https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-{pyside}-src/
Git: https://code.qt.io/cgit/qt/ and https://code.qt.io/cgit/pyside/pyside-setup.git (tag v{pyside}).

Written offer. I, Pedro Silva (PMS Labs), who distribute this package, will give you or any third party, on request and for at least three (3) years from the date
of the release of this package, the complete corresponding source of Qt {qt} and PySide 6 {pyside} as used in this package, for no more than the cost of physically
performing the distribution. Name this package and its version in your request. The offer is valid whether or not the release page is still online.
{contact}
""", encoding="utf-8")
    (staging / "REPLACING-QT.txt").write_text(f"""How to use your own build of Qt or PySide with this package
==========================================================

The Qt and PySide libraries are ordinary files of this package (it is a folder, not a single packed file). LGPL-3.0 gives you the right to replace them
with a modified or newer interface-compatible build and run the program with it. To do so:

1. Build or obtain Qt {minor}.x (and PySide6 {pyside} if you replace the Python bindings) for your system, from the source in SOURCE-OFFER.txt or from the
   official PyPI wheels (for example `pip download PySide6_Essentials=={pyside} --no-deps`, then unzip the wheel).
2. Find the file to replace.
     Windows: the folder `_internal\\PySide6` (Qt6Core.dll, Qt6Gui.dll, Qt6Widgets.dll, the plug-ins) next to the program.
     Linux:   the folder `_internal/PySide6/Qt/lib` (libQt6Core.so.6 and the others) and `_internal/PySide6/Qt/plugins`.
     macOS:   `PCB Thermal Lab.app/Contents/Frameworks/PySide6/Qt/lib` (QtCore.framework, QtGui.framework, QtWidgets.framework).
   The binding modules (QtCore, QtGui and QtWidgets files with PySide6 in the folder name, and shiboken6) are files too and are replaced the same way.
3. Copy your file over it. It must be built from the same Qt version series ({minor}.x), for the same system and processor, and, for the Python bindings, for the
   same Python (CPython 3.13).
4. macOS only: the libraries of this package are signed ad hoc (no developer identity), and Apple silicon refuses a library that is not signed. After the
   copy run, in a terminal:
     codesign --force --sign - "PCB Thermal Lab.app/Contents/Frameworks/PySide6/Qt/lib/QtGui.framework"      (the one you replaced)
     codesign --force --deep --sign - "PCB Thermal Lab.app"
   (A quarantined download also needs the step of the README Download section.)
5. Start the program and open Help - About: the line under the version shows the Qt version that is loaded now. `PCB-Thermal-Lab --selftest` checks the start.

The simplest alternative, and the one this project recommends if you want to change Qt: run the program from source, where Qt is installed by pip and you choose it.
    git clone https://github.com/silvapmm/pcb-thermal-lab ; python3 -m venv .venv ; .venv/bin/pip install -r requirements.txt ; .venv/bin/python -m pcbthermal gui
(any PySide6 or Qt build that pip, or your own, provides). Nothing in this package stops you from doing either.
""", encoding="utf-8")


def write_build_info(staging):
    """!
    @brief Write BUILD-INFO.txt: the exact versions of everything that went into the package, and of the tree.
    @param staging Staging folder.
    """
    freeze = subprocess.run([str(venv_python()), "-m", "pip", "freeze"], check=True, capture_output=True, text=True).stdout
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    py = subprocess.run([str(venv_python()), "-c", "import sys; print(sys.version.replace(chr(10), ' '))"], check=True, capture_output=True, text=True).stdout.strip()
    osname, arch, _ = platform_tag()
    (staging / "BUILD-INFO.txt").write_text(
        f"PCB Thermal Lab {version()}\nBuilt {date.today().isoformat()} on {osname}-{arch} ({platform.platform()})\nSource commit: {commit}\n"
        f"Python: {py}\n\nInstalled packages of the build environment (pip freeze):\n{freeze}", encoding="utf-8")


def make_icns(staging):
    """!
    @brief Make the macOS icon (.icns) from ico/pcb-board.png with sips and iconutil (macOS only).
    @param staging Staging folder.
    """
    if sys.platform != "darwin":
        return
    iconset = staging / "pcb-board.iconset"
    iconset.mkdir(parents=True, exist_ok=True)
    src = ROOT / "ico" / "pcb-board.png"
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            px = size * scale
            if px > 1024:
                continue
            name = f"icon_{size}x{size}{'@2x' if scale == 2 else ''}.png"
            run(["sips", "-z", px, px, src, "--out", iconset / name], stdout=subprocess.DEVNULL)
    run(["iconutil", "-c", "icns", iconset, "-o", staging / "pcb-board.icns"])


def sha256(path):
    """!
    @brief SHA-256 of a file.
    @param path File.
    @return str hexadecimal digest.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def run_pyinstaller(staging):
    """!
    @brief Run PyInstaller on the spec file.
    @param staging Staging folder (given to the spec through PCBT_STAGING).
    @return Path of the folder PyInstaller wrote.
    """
    out = WORK / "pyinstaller-dist"
    if out.exists():
        shutil.rmtree(out)
    env = dict(os.environ, PCBT_STAGING=str(staging))
    run([venv_python(), "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", out, "--workpath", WORK / "pyinstaller-work", PKG / "PCB-Thermal-Lab.spec"],
        env=env, cwd=ROOT)
    return out


def check_forbidden(folder):
    """!
    @brief Fail when the package holds a file of a Qt module or library that must not be shipped (see FORBIDDEN), and report what Python's own libraries added.
    @param folder The folder (or .app) to scan.
    @throws SystemExit With the list of the files found.
    """
    found = sorted(str(p.relative_to(folder)) for p in folder.rglob("*") if FORBIDDEN.search(p.relative_to(folder).as_posix()) and "/licenses/" not in "/" + p.relative_to(folder).as_posix())
    if found:
        raise SystemExit("error: files that must not be in the package:\n  " + "\n  ".join(found[:40]))
    extra = sorted({p.name for p in folder.rglob("*") if re.match(r"(libssl|libcrypto|libssl-|libcrypto-)", p.name)})
    if extra:
        print("note: OpenSSL libraries are bundled (" + ", ".join(extra) + "): their notice must be in licenses/Python")


def assemble(built):
    """!
    @brief Make the package folder from the PyInstaller output and the licence material.
    @param built Folder PyInstaller wrote.
    @return tuple (package folder, relative path of the program inside it).
    """
    folder = DIST / package_name()
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    check_forbidden(built)
    if sys.platform == "darwin":
        shutil.copytree(built / APP_NAME, folder / APP_NAME, symlinks=True)
        exe = f"{APP_NAME}/Contents/MacOS/{PRODUCT}"
    else:
        for item in (built / PRODUCT).iterdir():
            (shutil.copytree(item, folder / item.name, symlinks=True) if item.is_dir() else shutil.copy2(item, folder / item.name))
        exe = PRODUCT + (".exe" if sys.platform == "win32" else "")
    # The same material is at the top of the package, where a person who unpacks it looks first (the program also carries it inside)
    staging = WORK / "staging"
    shutil.copytree(staging / "licenses", folder / "licenses")
    for name in ("NOTICE.txt", "SOURCE-OFFER.txt", "REPLACING-QT.txt", "BUILD-INFO.txt"):
        shutil.copy2(staging / name, folder / name)
    shutil.copy2(ROOT / "LICENSE", folder / "LICENSE")
    return folder, exe


def write_file_list(folder, out):
    """!
    @brief Write the list of the files of the package (path and size) and, first, the native libraries that do not belong to Qt: the file a reviewer reads to
           see what a new build brought in (a library from the build machine needs its notice in licenses/).
    @param folder Package folder.
    @param out File to write.
    @return int Number of files.
    """
    files = sorted(p for p in folder.rglob("*") if p.is_file() and not p.is_symlink())
    native = re.compile(r"\.(so(\.\d+)*|dylib|dll)$", re.IGNORECASE)
    extension = re.compile(r"cpython-|\.abi3\.|\.pyd$", re.IGNORECASE)        # Python extension modules: covered by the licence of their package
    qt = re.compile(r"(^|/)(PySide6|shiboken6)/|Qt6?[A-Z]\w*\.(dll|framework)|/Qt[A-Z]\w*\.framework/", re.IGNORECASE)
    # A copy of the same library in two places of a macOS bundle (Frameworks and Resources) is listed once
    others = sorted({p.name: p.relative_to(folder).as_posix() for p in files if native.search(p.name) and not extension.search(p.name)
                     and not qt.search(p.relative_to(folder).as_posix())}.values())
    lines = [f"Files of {folder.name}: {len(files)} files, {sum(p.stat().st_size for p in files) / 1e6:.1f} MB", "",
             "Native libraries outside PySide6 (each needs a licence in licenses/: a Python package's own, Python/, or packaging/licenses/_system/):"]
    lines += ["  " + r for r in others] + ["", "All files (bytes  path):"]
    lines += [f"{p.stat().st_size:>11}  {p.relative_to(folder).as_posix()}" for p in files]
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(files)


def archive(folder):
    """!
    @brief Archive the package folder (zip with ditto on macOS, which keeps symbolic links and permissions; zip on Windows; tar.gz on Linux).
    @param folder Package folder.
    @return Path of the archive.
    """
    _, _, ext = platform_tag()
    out = DIST / (folder.name + ext)
    if out.exists():
        out.unlink()
    if sys.platform == "darwin":
        run(["ditto", "-c", "-k", "--keepParent", folder, out])
    elif ext == ".zip":
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(folder.rglob("*")):
                z.write(p, p.relative_to(folder.parent).as_posix())
    else:
        with tarfile.open(out, "w:gz") as t:
            t.add(folder, arcname=folder.name)
    return out


def extract(archive_path, target):
    """!
    @brief Unpack an archive into a new folder, as a user would (ditto on macOS).
    @param archive_path Archive.
    @param target Folder to create.
    """
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    if sys.platform == "darwin":
        run(["ditto", "-x", "-k", archive_path, target])
    elif archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path) as z:
            z.extractall(target)
    else:
        with tarfile.open(archive_path) as t:
            t.extractall(target)


def selftest(archive_path, exe):
    """!
    @brief Unpack the archive and run the program's --selftest from the unpacked copy.
    @param archive_path Archive.
    @param exe Path of the program inside the package folder.
    @return int Exit code of the self-test.
    """
    target = WORK / "selftest-extract"
    extract(archive_path, target)
    report = WORK / "selftest-result.txt"
    report.unlink(missing_ok=True)
    t0 = time.time()
    done = subprocess.run([str(target / package_name() / exe), "--selftest", "--selftest-out", str(report)], timeout=300)
    print(f"selftest exit code {done.returncode} in {time.time() - t0:.1f} s; report {report}")
    if report.exists():
        print(report.read_text(encoding="utf-8"))
    return done.returncode


def main(argv=None):
    """!
    @brief Command line.
    @param argv Argument list (default sys.argv[1:]).
    @return Exit code.
    """
    ap = argparse.ArgumentParser(description="Build the downloadable package of PCB Thermal Lab for this system.")
    ap.add_argument("--reuse-venv", action="store_true", help="keep packaging/.venv-build if it exists (default: make it again)")
    ap.add_argument("--selftest", action="store_true", help="unpack the archive and run --selftest of the program from it (exit code 1 when it fails)")
    ap.add_argument("--release", action="store_true", help="the build of a release tag (the contact of the written offer, SECOND_CONTACT, is checked before anything is built)")
    args = ap.parse_args(argv)
    if not SECOND_CONTACT:
        raise SystemExit("error: SECOND_CONTACT in packaging/build.py is empty: a build needs a contact for the written offer that does not depend on GitHub")
    t0 = time.time()
    make_venv(args.reuse_venv)
    verify_pins()
    staging = WORK / "staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    # The Qt texts of the repository are the same for every package; the rest is made from the environment that is about to be bundled
    shutil.copytree(PKG / "licenses", staging / "licenses", ignore=shutil.ignore_patterns("_fallback", "_system"))
    index = collect_licences(staging, bundled_distributions(site_packages()))
    pyside, qt = qt_versions()
    # The exact Qt and PySide source of the release (the assets) and, made from the same tarballs, the notices of the third-party code inside Qt
    sources = qt_sources.fetch(WORK / "qt-source", qt, pyside, wayland=True)
    n = qt_sources.notices(sources, qt, staging / "licenses" / "Qt" / "THIRD-PARTY-NOTICES.txt")
    print(f"Qt third-party notices: {n} components")
    write_notice_files(staging, args.release)
    write_build_info(staging)
    make_icns(staging)
    built = run_pyinstaller(staging)
    folder, exe = assemble(built)
    out = archive(folder)
    DIST.mkdir(exist_ok=True)
    if sys.platform.startswith("linux"):   # The source is one set per release, not per system: the Linux job carries it to the release job
        shutil.rmtree(DIST / "qt-source", ignore_errors=True)
        shutil.copytree(WORK / "qt-source", DIST / "qt-source")
    (DIST / "SHA256SUMS.txt").write_text(f"{sha256(out)}  {out.name}\n", encoding="utf-8")
    print(f"file list: {write_file_list(folder, DIST / 'FILES.txt')} files in {DIST / 'FILES.txt'}")
    osname, arch, _ = platform_tag()
    result = {"version": version(), "os": osname, "arch": arch, "archive": out.name, "folder": folder.name, "executable": exe, "qt": qt, "pyside": pyside, "source_assets": source_assets(qt, pyside), "seconds": round(time.time() - t0),
              "archive_bytes": out.stat().st_size, "licence_index": index}
    (DIST / "BUILD-RESULT.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"built {out} ({out.stat().st_size / 1e6:.1f} MB) in {time.time() - t0:.0f} s")
    return selftest(out, exe) if args.selftest else 0


if __name__ == "__main__":
    sys.exit(main())
