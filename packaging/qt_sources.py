#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file qt_sources.py
@brief The Qt and PySide source tarballs of a release (the source the LGPL asks us to provide) and the Qt third-party notices made from them.
@details The packages bundle Qt and PySide 6 unmodified. GPL-3.0 section 6 and the Qt Project's own reading ask that the corresponding source be available
         from the place that distributes the object code, not only through a link to the Qt servers. So each release carries the exact tarballs of the version
         in the package: qtbase, qtsvg, qtimageformats, pyside-setup (and qtwayland, which only the Linux package needs).
         `python packaging/qt_sources.py --qt 6.12.0 --pyside 6.12.0 --out DIR` downloads them from download.qt.io, checks each against the `.sha256` file that
         the Qt Project publishes next to it and writes `QT-SOURCE-SHA256.txt`. The files in DIR are the release assets; this script uploads nothing.
         `notices()` reads the `qt_attribution.json` files and the `LICENSES/` folder of those same tarballs and writes THIRD-PARTY-NOTICES.txt, so the notices
         match the exact version that is shipped.
"""

import argparse
import hashlib
import json
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

BASE = "https://download.qt.io/official_releases"
# Qt modules whose libraries or plug-ins are in the package: QtCore, QtGui, QtWidgets (qtbase), QtSvg (the svg icon engine), the image-format plug-ins
MODULES = ("qtbase", "qtsvg", "qtimageformats")
SKIP_PARTS = ("/src/network/", "/src/sql/", "/src/testlib/", "/src/tools/", "/tests/", "/examples/", "/doc/", "/util/")   # Qt code that is not in the package
# Credits that the licences of two bundled components ask for in the documentation of the product
REQUIRED_CREDITS = (
    "Portions of this software are copyright (c) The FreeType Project (www.freetype.org). All rights reserved. (FreeType Project License, the credit it asks for.)",
    "This software is based in part on the work of the Independent JPEG Group. (libjpeg-turbo, the clause of the IJG licence.)",
)


def urls(qt, pyside, wayland=True):
    """!
    @brief The tarballs of one release.
    @param qt Qt version, for example "6.12.0".
    @param pyside PySide6 version, for example "6.12.0".
    @param wayland True to include qtwayland (the Linux package bundles its platform plug-in).
    @return list of (file name, url).
    """
    minor = ".".join(qt.split(".")[:2])
    mods = MODULES + (("qtwayland",) if wayland else ())
    out = [(f"{m}-everywhere-src-{qt}.tar.xz", f"{BASE}/qt/{minor}/{qt}/submodules/{m}-everywhere-src-{qt}.tar.xz") for m in mods]
    name = f"pyside-setup-everywhere-src-{pyside}.tar.xz"
    return out + [(name, f"{BASE}/QtForPython/pyside6/PySide6-{pyside}-src/{name}")]


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


def fetch(dest, qt, pyside, wayland=True):
    """!
    @brief Download the tarballs (kept when already there with the right checksum) and verify each against the checksum file published next to it.
    @param dest Folder for the files.
    @param qt Qt version.
    @param pyside PySide6 version.
    @param wayland True to include qtwayland.
    @return dict file name -> Path.
    @throws RuntimeError If a checksum does not match or a file cannot be downloaded.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    out, lines = {}, []
    for name, url in urls(qt, pyside, wayland):
        expected = urllib.request.urlopen(url + ".sha256", timeout=60).read().decode().split()[0].lower()
        path = dest / name
        if not (path.exists() and sha256(path) == expected):
            print(f"downloading {url}", flush=True)
            urllib.request.urlretrieve(url, path)
        got = sha256(path)
        if got != expected:
            raise RuntimeError(f"{name}: SHA-256 {got} does not match the published {expected}")
        out[name] = path
        lines.append(f"{got}  {name}")
    (dest / "QT-SOURCE-SHA256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _licence_ids(expression):
    """!
    @brief The licence identifiers of an SPDX-like expression.
    @param expression Text such as "BSD-3-Clause AND (MIT OR Zlib)".
    @return list of str.
    """
    return [t for t in re.split(r"\s+|\(|\)", expression or "") if t and t.upper() not in ("AND", "OR", "WITH")]


def notices(tarballs, qt, out_path):
    """!
    @brief Write THIRD-PARTY-NOTICES.txt from the attribution files and licence texts of the Qt tarballs.
    @param tarballs dict from fetch() (the Qt modules are read; pyside-setup is not).
    @param qt Qt version (for the heading).
    @param out_path File to write.
    @return int Number of components listed.
    """
    components, texts = [], {}
    for name, path in tarballs.items():
        if not any(name.startswith(m + "-") for m in MODULES + ("qtwayland",)):
            continue
        with tarfile.open(path, "r:xz") as t:
            for member in t:
                if not member.isfile():
                    continue
                rel = "/" + member.name.split("/", 1)[1] if "/" in member.name else member.name
                if member.name.endswith("/qt_attribution.json") and not any(s in rel for s in SKIP_PARTS):
                    data = json.loads(t.extractfile(member).read().decode("utf-8", "replace"), strict=False)   # Qt files hold raw tabs in strings
                    for entry in data if isinstance(data, list) else [data]:
                        parts = entry.get("QtParts", ["libs"])
                        if "libs" in parts:
                            components.append((rel, entry))
                elif re.search(r"/LICENSES/[^/]+\.txt$", member.name):
                    texts.setdefault(Path(member.name).stem, t.extractfile(member).read().decode("utf-8", "replace"))
    seen, lines = set(), []
    for rel, e in sorted(components, key=lambda c: (c[1].get("Name", ""), c[0])):
        key = (e.get("Name"), e.get("Version"), e.get("LicenseId"))
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"* {e.get('Name', '?')}{' ' + str(e['Version']) if e.get('Version') else ''}\n"
                     f"    licence: {e.get('LicenseId') or e.get('License', '?')}\n"
                     + (f"    homepage: {e['Homepage']}\n" if e.get("Homepage") else "")
                     + (f"    copyright: {' | '.join(e['Copyright']) if isinstance(e.get('Copyright'), list) else e.get('Copyright')}\n" if e.get("Copyright") else "")
                     + f"    in Qt source: {rel.rsplit('/', 1)[0].lstrip('/')}\n")
    ids = sorted({i for _, e in components for i in _licence_ids(e.get("LicenseId", ""))})
    head = (f"Third-party code in Qt {qt}, as bundled with PCB Thermal Lab\n{'=' * 60}\n\n"
            f"Qt itself is used under the GNU LGPL v3 (licenses/Qt/LGPL-3.0.txt, GPL-3.0.txt). The libraries and plug-ins can contain the third-party code below, under "
            f"the licences named. This list and the licence texts at its end were made by packaging/qt_sources.py from the qt_attribution.json files and the LICENSES/ "
            f"folder of the Qt {qt} source (qtbase, qtsvg, qtimageformats, qtwayland), the same tarballs that are attached to the release. It lists the code of those "
            f"modules; not every component is in the library of every system (the Cocoa plug-in is macOS only, Wintab Windows only, the XCB items Linux only).\n\n"
            "Credits that licences of bundled components ask for\n" + "\n".join("  " + c for c in REQUIRED_CREDITS) + "\n\nComponents\n----------\n\n")
    body = "\n".join(lines) + "\n\nLicence texts\n-------------\n"
    for i in ids:
        body += f"\n===== {i} =====\n" + (texts.get(i) or f"(text not found in the Qt source; see https://spdx.org/licenses/{i}.html)\n") + "\n"
    Path(out_path).write_text(head + body, encoding="utf-8")
    return len(seen)


def main(argv=None):
    """!
    @brief Command line: download the source tarballs of a release and (with --notices) write the Qt third-party notices.
    @param argv Argument list (default sys.argv[1:]).
    @return Exit code.
    """
    ap = argparse.ArgumentParser(description="Download the Qt and PySide source tarballs of a release (the release assets) and verify their checksums.")
    ap.add_argument("--qt", required=True, help="Qt version, for example 6.12.0")
    ap.add_argument("--pyside", required=True, help="PySide6 version, for example 6.12.0")
    ap.add_argument("--out", required=True, help="folder for the tarballs and QT-SOURCE-SHA256.txt")
    ap.add_argument("--no-wayland", action="store_true", help="leave qtwayland out (only the Linux package needs it)")
    ap.add_argument("--notices", metavar="FILE", help="also write THIRD-PARTY-NOTICES.txt to FILE")
    args = ap.parse_args(argv)
    files = fetch(args.out, args.qt, args.pyside, not args.no_wayland)
    for name, p in files.items():
        print(f"{p.stat().st_size / 1e6:7.1f} MB  {name}")
    if args.notices:
        print(f"{notices(files, args.qt, args.notices)} components in {args.notices}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
