#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file bundle_info.py
@brief What the About box and the Licences window say about the program and its libraries: live versions, the table of the libraries and the licence files.
@details No GUI imports. The table is read at run time from the installed metadata (`importlib.metadata`), starting from the libraries the program imports and
         following what they require, so a library added to `requirements.txt` cannot be forgotten (`tests/test_help.py` fails when a run-time line of
         `requirements.txt` is not in the table or has no recognised licence). In a packaged build the metadata is present because `packaging/PCB-Thermal-Lab.spec`
         copies it, and the licence texts are in the `licenses/` folder of the package (`packaging/build.py`).
"""

import platform
import re
import sys
from importlib import metadata
from pathlib import Path

from . import __version__

ROOTS = ("numpy", "scipy", "pyamg", "matplotlib", "PySide6")        # The run-time libraries of requirements.txt (the closure of their requirements is added)
ALIASES = {"pyside6": ("PySide6", "PySide6_Essentials")}            # A packaged build has the Essentials wheel (the same Qt modules, no add-ons) instead of PySide6
LICENCE_OF = {"pyamg": "MIT"}                                       # Metadata of a library that states nothing usable (checked in its wheel and repository)
CLASSIFIERS = {"BSD License": "BSD", "MIT License": "MIT", "Apache Software License": "Apache-2.0", "Python Software Foundation License": "PSF-based",
               "GNU Lesser General Public License v3 (LGPLv3)": "LGPL-3.0", "ISC License (ISCL)": "ISC", "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0"}
TEXT_FILES = ("LICENSE", "NOTICE.txt", "SOURCE-OFFER.txt", "REPLACING-QT.txt", "BUILD-INFO.txt")   # At the top of a package, in this order


def packaged():
    """!
    @brief Whether this is the packaged build (a PyInstaller executable) and not a run from source.
    @return bool.
    """
    return bool(getattr(sys, "frozen", False))


def root_folder():
    """!
    @brief The folder that holds LICENSE and licenses/: the bundle root when packaged, the repository folder when run from source.
    @return Path.
    """
    if packaged():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


def package_folders():
    """!
    @brief Folders where the licence material of a packaged build may be (inside the bundle, or next to the executable: the top of the unpacked archive).
    @return list of Path, the most likely first.
    """
    exe = Path(sys.executable).resolve()
    return [root_folder(), exe.parent, exe.parent.parent, exe.parents[1] / "Resources", exe.parents[3] if len(exe.parents) > 3 else exe.parent]


def licences_folder():
    """!
    @brief The licenses/ folder shipped with the packaged build.
    @return Path, or None (from source, or a package without it).
    """
    if not packaged():
        return None
    return next((d / "licenses" for d in package_folders() if (d / "licenses" / "Qt").is_dir()), None)


def _first_distribution(names):
    """!
    @brief The first installed distribution among several names.
    @param names Tuple of distribution names.
    @return metadata.Distribution or None.
    """
    for n in names:
        try:
            return metadata.distribution(n)
        except metadata.PackageNotFoundError:
            continue
    return None


def normal(name):
    """!
    @brief Normalised distribution name.
    @param name Name as written.
    @return str lower case, one kind of separator.
    """
    return re.sub(r"[-_.]+", "_", name).lower()


def closure(roots=ROOTS):
    """!
    @brief The distributions behind the libraries: the roots and everything they require (without extras), stopping at what is not installed.
    @param roots Names of the root libraries.
    @return dict normalised name -> metadata.Distribution, sorted by name. PySide6 stands for PySide6-Essentials where only that is installed; its add-on wheels are not followed.
    """
    out, todo = {}, list(roots)
    skip = {"pyside6_addons", "pyside6_webengine", "pyside6_pdf", "tomli"}           # Add-ons of the full PySide6 wheel: the program imports none of their modules
    while todo:
        name = todo.pop()
        dist = _first_distribution(ALIASES.get(name.lower(), (name,)))
        if dist is None or normal(dist.metadata["Name"]) in out or normal(name) in skip:
            continue
        out[normal(dist.metadata["Name"])] = dist
        todo += [re.match(r"[A-Za-z0-9._-]+", r).group(0) for r in dist.requires or [] if "extra ==" not in r]
    return dict(sorted(out.items()))


def licence_of(dist):
    """!
    @brief The licence of a distribution as a short name: the SPDX expression of the metadata, else its short License field, else its OSI classifier, else the table of exceptions.
    @param dist metadata.Distribution.
    @return str, "" when nothing usable is stated.
    """
    md = dist.metadata
    name = normal(md["Name"])
    if name in LICENCE_OF:
        return LICENCE_OF[name]
    for value in (md.get("License-Expression"), md.get("License")):
        value = " ".join((value or "").split())
        if value and len(value) <= 80:                       # A long License field is the whole licence text, not a name
            return value
    found = [CLASSIFIERS.get(c.split(" :: ")[-1], c.split(" :: ")[-1]) for c in md.get_all("Classifier") or [] if c.startswith("License ::")]
    found = [f for f in found if f != "OSI Approved"]
    return found[0] if found else ""


def libraries():
    """!
    @brief The table of the bundled libraries.
    @return list of (name, version, licence) tuples, sorted by name; the licence is "" when it is not stated.
    """
    return [(d.metadata["Name"], d.version, licence_of(d)) for d in closure().values()]


def table_text():
    """!
    @brief The table of the libraries as plain text.
    @return str.
    """
    rows = libraries()
    width = max(len(r[0]) for r in rows)
    return "\n".join(f"{n:<{width}}  {v:<10}  {lic or 'not stated'}" for n, v, lic in rows)


def versions():
    """!
    @brief The versions that are loaded now (a swapped Qt library shows up here).
    @return dict with keys os, arch, python, qt, pyside, build ("packaged build" or "from source").
    """
    from PySide6 import __version__ as pyside_version
    from PySide6.QtCore import qVersion

    system = {"Darwin": "macOS", "Windows": "Windows", "Linux": "Linux"}.get(platform.system(), platform.system())
    return {"os": system, "arch": platform.machine(), "python": platform.python_version(), "qt": qVersion(), "pyside": pyside_version,
            "build": "packaged build" if packaged() else "from source"}


def live_line():
    """!
    @brief The line of the About box: system, Python, Qt, PySide and the kind of build.
    @return str.
    """
    v = versions()
    return f"{v['os']} {v['arch']} · Python {v['python']} · Qt {v['qt']} · PySide6 {v['pyside']} · {v['build']}"


def version_info_text():
    """!
    @brief The text of the Copy version info button (for a bug report).
    @return str.
    """
    return f"PCB Thermal Lab {__version__}\n{live_line()}\n"


def qt_sentence():
    """!
    @brief The sentence of the About box that LGPL 3.0 section 4(c) asks for: the copyright of Qt and the pointer to the licence texts.
    @return str.
    """
    v = versions()
    return (f"This program uses Qt {v['qt']} and PySide6 {v['pyside']} (Qt for Python), Copyright © The Qt Company Ltd. and other contributors, "
            "under the GNU Lesser General Public License version 3. See Licences for the texts, the source and how to replace Qt.")


def _read(path):
    """!
    @brief Text of a file ("" when it cannot be read).
    @param path File.
    @return str.
    """
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def licence_entries():
    """!
    @brief What the Licences window lists: (title, text, tooltip) triples, one entry per library. A packaged build shows the files of its package (the top-level
           notices, the table of the libraries and one entry per folder of licenses/, whose licence files are joined under headings); from source, the LICENSE
           of the program, the table of the libraries and where the Qt texts are.
    @return list of (str title, str text, str tooltip with the full path or a short description).
    """
    entries = []
    folder = licences_folder()
    if folder is not None:
        top = folder.parent
        for name in TEXT_FILES:
            if (top / name).is_file():
                entries.append((name, _read(top / name), str(top / name)))
        entries.append(("Libraries bundled in this build", table_text(), "Name, version and licence of every library in this package."))
        index = folder / "INDEX.txt"
        if index.is_file():
            entries.append(("licenses/INDEX.txt", _read(index), str(index)))
        for sub in sorted((p for p in folder.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
            # The LGPL first: it is the licence Qt is used under here (the GPL text is shipped because the LGPL refers to it)
            files = sorted((p for p in sub.rglob("*") if p.is_file()), key=lambda p: (not p.name.startswith("LGPL"), p.relative_to(sub).as_posix().lower()))
            body = "\n\n".join(f"===== {p.relative_to(sub).as_posix()} =====\n{_read(p)}" for p in files)
            title = "Qt and PySide (LGPL-3.0, GPL-3.0, notices)" if sub.name == "Qt" else sub.name
            entries.append((title, body, f"{sub}  ({len(files)} file(s))"))
        return entries
    entries.append(("LICENSE", _read(root_folder() / "LICENSE"), str(root_folder() / "LICENSE")))
    entries.append(("Libraries (installed in this Python)", table_text(), "Name, version and licence of every library installed in this Python."))
    entries.append(("Qt and PySide (installed by pip)", "Run from source, Qt and PySide are installed by pip from PyPI under their own licence, the GNU LGPL v3 "
                    "(or GPL v2 or v3, or a commercial licence). The texts: https://www.gnu.org/licenses/lgpl-3.0.html and https://www.gnu.org/licenses/gpl-3.0.html. "
                    "The downloadable packages carry the texts, the Qt notices, SOURCE-OFFER.txt and REPLACING-QT.txt (see the Download section of the README).",
                    "Where the Qt licence texts are when the program runs from source."))
    return entries
