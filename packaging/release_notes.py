#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file release_notes.py
@brief Extract the section of one version from CHANGELOG.md: the text of a release (`gh release create --notes-file`).
@details Usage: `python packaging/release_notes.py 2.8.0 [-o notes.md] [--changelog CHANGELOG.md]`. The section starts at the heading `## [X.Y.Z]` and ends
         before the next `## [` heading; the heading itself is not part of the notes. A pre-release version (2.9.0rc1) without a section of its own takes the `## [Unreleased]` section. With `--build-result` the paragraph about the attached Qt source is appended; with `--sums` (the SHA256SUMS.txt of the release) the "First run" section is appended too (macOS and Windows confirmations, the Linux glibc requirement, the SHA-256 of each package and the pointer to REPLACING-QT.txt). Exit code 1 when the version has no section (never a silent empty
         file), so that a release without its CHANGELOG entry stops the workflow.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRERELEASE = re.compile(r"[0-9](a|b|rc)[0-9]+$")          # A pre-release version such as 2.9.0rc1 (tag v2.9.0rc1)


def extract(text, version):
    """!
    @brief The notes of one version.
    @param text Content of CHANGELOG.md.
    @param version Version without a leading "v", for example "2.8.0".
    @return str The section without its heading, stripped; "" when the version is not in the file.
    """
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if re.match(r"##\s*\[" + re.escape(version) + r"\]", ln)), None)
    if start is None:
        return ""
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## [")), len(lines))
    return "\n".join(lines[start + 1:end]).strip() + "\n"


def source_section(qt, pyside, assets):
    """!
    @brief The paragraph that every release's notes carry about the Qt and PySide source attached to it (LGPL-3.0).
    @param qt Qt version.
    @param pyside PySide6 version.
    @param assets Names of the attached source tarballs.
    @return str Markdown, ending with a newline.
    """
    names = "\n".join(f"- `{a}`" for a in assets)
    return (f"\n## Qt and PySide source\n\nThe packages include Qt {qt} and PySide6 {pyside} under the LGPL-3.0, unmodified. Their exact source is attached to this release:\n\n"
            f"{names}\n- `QT-SOURCE-SHA256.txt` (the SHA-256 sums of the tarballs)\n\nThe licence texts, the notices, `SOURCE-OFFER.txt` and `REPLACING-QT.txt` are inside each package.\n")


def package_sums(sums_text):
    """!
    @brief The SHA-256 lines of the packages in a SHA256SUMS.txt (the Qt tarballs are left out: the source section lists them).
    @param sums_text Content of SHA256SUMS.txt (`<64 hex digits>  <file name>` per line).
    @return list of (str, str): (file name, SHA-256), in file order.
    """
    out = []
    for line in sums_text.splitlines():
        m = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?(PCB-Thermal-Lab-\S+)", line.strip())
        if m:
            out.append((m.group(2), m.group(1).lower()))
    return out


def first_run_section(sums, qt, pyside):
    """!
    @brief The "First run" section of the notes: how to open the unsigned packages, the Linux requirement, the checksums and where the LGPL replacement is explained.
    @param sums List of (file name, SHA-256) as package_sums returns it.
    @param qt Qt version.
    @param pyside PySide6 version.
    @return str Markdown, ending with a newline.
    """
    rows = "\n".join(f"| `{name}` | `{digest}` |" for name, digest in sums)
    return (
        "\n## First run\n\n"
        "The packages are **not signed**, so the first start asks for a confirmation. Unpack the whole archive first; nothing is installed and Python is not needed.\n\n"
        "- **macOS** (macOS 14 or newer, Apple silicon): open the app once and click Done on the warning; then System Settings, Privacy & Security, Security, "
        "**Open Anyway** for PCB Thermal Lab, confirm and authenticate with your password or Touch ID.\n"
        "- **Windows**: SmartScreen says \"Windows protected your PC\": More info, **Run anyway**.\n"
        "- **Linux**: built on Ubuntu 22.04, it needs glibc 2.35 or newer (Ubuntu 22.04 and later, Debian 12 and later, Fedora 36 and later). Older systems "
        "(Ubuntu 20.04, Debian 11, RHEL and Rocky 8 and 9) are not supported by this package: run from source with pip instead.\n\n"
        f"Packages (SHA-256; `sha256sum -c SHA256SUMS.txt` checks them):\n\n| File | SHA-256 |\n| :-- | :-- |\n{rows}\n\n"
        f"Qt {qt} and PySide6 {pyside} are bundled under the LGPL-3.0 as separate, replaceable files. How to replace them with your own build: `REPLACING-QT.txt` "
        "in the package (the Qt source is attached to this release).\n")


def main(argv=None):
    """!
    @brief Command line.
    @param argv Argument list (default sys.argv[1:]).
    @return Exit code: 0 written, 1 version not found.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0].replace("@file release_notes.py", "").strip())
    ap.add_argument("version", help="version without the leading v, for example 2.8.0")
    ap.add_argument("-o", "--output", help="file to write (default: standard output)")
    ap.add_argument("--build-result", help="a BUILD-RESULT*.json of the release: append the paragraph that lists the attached Qt and PySide source tarballs")
    ap.add_argument("--sums", help="the SHA256SUMS.txt of the release (with --build-result): append the 'First run' section with the checksums of the packages")
    ap.add_argument("--changelog", default=str(ROOT / "CHANGELOG.md"), help="CHANGELOG.md to read")
    args = ap.parse_args(argv)
    text = Path(args.changelog).read_text(encoding="utf-8")
    version = args.version.lstrip("v")
    notes = extract(text, version)
    if not notes.strip() and PRERELEASE.search(version):
        # A pre-release (2.9.0rc1) has no section of its own: its notes are the Unreleased section that will become the release's
        notes = extract(text, "Unreleased")
    if not notes.strip():
        print(f"error: no section '## [{args.version}]' in {args.changelog}", file=sys.stderr)
        return 1
    if args.build_result:
        info = json.loads(Path(args.build_result).read_text(encoding="utf-8"))
        notes += source_section(info["qt"], info["pyside"], info["source_assets"])
        if args.sums:
            sums = package_sums(Path(args.sums).read_text(encoding="utf-8"))
            if not sums:
                print(f"error: no package checksum in {args.sums}", file=sys.stderr)
                return 1
            notes += first_run_section(sums, info["qt"], info["pyside"])
    if args.output:
        Path(args.output).write_text(notes, encoding="utf-8")
    else:
        sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
