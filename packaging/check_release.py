#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_release.py
@brief The check of the release job: the three packages carry the same Qt and PySide versions, and the Qt source tarballs attached to the release are those versions.
@details Usage: `python packaging/check_release.py FILES_DIR`. FILES_DIR holds what the build jobs kept: one `BUILD-RESULT-<system>.json` per package (a copy of the
         `BUILD-RESULT.json` of `build.py`), the archives and the folder `qt-source/` made by the Linux job. Exit code 1, with the reasons printed, when a package is
         missing, when `qt` or `pyside` differ between the packages, when a package's own version differs from the others (or from `--version`, the tag without its v),
         when a source tarball is not named by those Qt and PySide versions, when `qt-source/` lacks one of them or its `QT-SOURCE-SHA256.txt`, or when a sum in that file
         does not match its tarball. This is the guard against a release whose packages and attached source disagree.
         Usage with the tag: `python packaging/check_release.py FILES_DIR --version 2.9.0`.
"""

import hashlib
import json
import sys
from pathlib import Path

SYSTEMS = ("windows-x64", "linux-x64", "macos-arm64")


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


def check(files, version=None):
    """!
    @brief Check the build results of a release.
    @param files Folder with the BUILD-RESULT-<system>.json files, the archives and qt-source/.
    @param version The version of the tag (without the v), or None to skip that comparison.
    @return list of str, the problems found (empty when the release is consistent).
    """
    files = Path(files)
    problems, results = [], {}
    for system in SYSTEMS:
        path = files / f"BUILD-RESULT-{system}.json"
        if not path.is_file():
            problems.append(f"missing {path.name}")
            continue
        results[system] = json.loads(path.read_text(encoding="utf-8"))
        if not (files / results[system]["archive"]).is_file():
            problems.append(f"{system}: the archive {results[system]['archive']} is not in {files}")
    for key in ("qt", "pyside", "version"):
        values = {s: r.get(key) for s, r in results.items()}
        if len(set(values.values())) > 1:
            problems.append(f"{key} differs between the packages: {values}")
    if results:
        any_result = next(iter(results.values()))
        for name in any_result.get("source_assets", []):
            if not (files / "qt-source" / name).is_file():
                problems.append(f"the source tarball {name} is not in qt-source/")
        if any_result.get("qt") not in (any_result.get("pyside"),):
            problems.append(f"Qt {any_result.get('qt')} and PySide6 {any_result.get('pyside')} are not the same version")
        for system, r in results.items():
            if r.get("source_assets") != any_result.get("source_assets"):
                problems.append(f"{system}: the list of source assets differs from the others")
        # The tarballs must be the source of the very versions in the packages: each name carries the Qt version (pyside-setup the PySide version)
        for name in any_result.get("source_assets", []):
            wanted = any_result.get("pyside") if name.startswith("pyside-setup") else any_result.get("qt")
            if f"-src-{wanted}.tar" not in name:
                problems.append(f"the source tarball {name} is not the source of version {wanted} that the packages carry")
        if version is not None and any_result.get("version") != version:
            problems.append(f"the packages are version {any_result.get('version')}, the tag says {version}")
    sums = files / "qt-source" / "QT-SOURCE-SHA256.txt"
    if not sums.is_file():
        problems.append("qt-source/QT-SOURCE-SHA256.txt is missing")
    elif results:
        listed = {}                                   # Lines "digest  file name", as qt_sources.fetch() writes them
        for line in sums.read_text(encoding="utf-8").splitlines():
            fields = line.split(None, 1)
            if len(fields) == 2:
                listed[fields[1].strip().lstrip("*")] = fields[0].lower()
            elif line.strip():
                problems.append(f"QT-SOURCE-SHA256.txt has a line that is not 'digest  name': {line.strip()[:60]}")
        for name in next(iter(results.values())).get("source_assets", []):
            path = files / "qt-source" / name
            if name not in listed:
                problems.append(f"{name} is not in QT-SOURCE-SHA256.txt")
            elif path.is_file() and sha256(path) != listed[name]:
                problems.append(f"{name}: its SHA-256 differs from QT-SOURCE-SHA256.txt")
    return problems


def main(argv=None):
    """!
    @brief Command line.
    @param argv Argument list (default sys.argv[1:]).
    @return int Exit code: 0 consistent, 1 problems.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    version = None
    if "--version" in args:
        i = args.index("--version")
        version = args[i + 1].lstrip("v") if i + 1 < len(args) else ""
        del args[i:i + 2]
    if len(args) != 1 or version == "":
        print("usage: check_release.py FILES_DIR [--version X.Y.Z]", file=sys.stderr)
        return 2
    problems = check(args[0], version)
    for p in problems:
        print("error:", p, file=sys.stderr)
    if not problems:
        print("the three packages and the attached Qt source agree")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
