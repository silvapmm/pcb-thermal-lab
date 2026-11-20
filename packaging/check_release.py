#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_release.py
@brief The check of the release job: the three packages carry the same Qt and PySide versions, and the Qt source tarballs attached to the release are those versions.
@details Usage: `python packaging/check_release.py FILES_DIR`. FILES_DIR holds what the build jobs kept: one `BUILD-RESULT-<system>.json` per package (a copy of the
         `BUILD-RESULT.json` of `build.py`), the archives and the folder `qt-source/` made by the Linux job. Exit code 1, with the reasons printed, when a package is
         missing, when `qt` or `pyside` differ between the packages, when a package's own version differs from the others, or when `qt-source/` lacks a tarball named by
         the version (`source_assets` of the results) or its `QT-SOURCE-SHA256.txt`. This is the guard against a release whose packages and attached source disagree.
"""

import json
import sys
from pathlib import Path

SYSTEMS = ("windows-x64", "linux-x64", "macos-arm64")


def check(files):
    """!
    @brief Check the build results of a release.
    @param files Folder with the BUILD-RESULT-<system>.json files, the archives and qt-source/.
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
    if not (files / "qt-source" / "QT-SOURCE-SHA256.txt").is_file():
        problems.append("qt-source/QT-SOURCE-SHA256.txt is missing")
    return problems


def main(argv=None):
    """!
    @brief Command line.
    @param argv Argument list (default sys.argv[1:]).
    @return int Exit code: 0 consistent, 1 problems.
    """
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: check_release.py FILES_DIR", file=sys.stderr)
        return 2
    problems = check(args[0])
    for p in problems:
        print("error:", p, file=sys.stderr)
    if not problems:
        print("the three packages and the attached Qt source agree")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
