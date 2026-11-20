#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file release_notes.py
@brief Extract the section of one version from CHANGELOG.md: the text of a release (`gh release create --notes-file`).
@details Usage: `python packaging/release_notes.py 2.8.0 [-o notes.md] [--changelog CHANGELOG.md]`. The section starts at the heading `## [X.Y.Z]` and ends
         before the next `## [` heading; the heading itself is not part of the notes. Exit code 1 when the version has no section (never a silent empty
         file), so that a release without its CHANGELOG entry stops the workflow.
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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


def main(argv=None):
    """!
    @brief Command line.
    @param argv Argument list (default sys.argv[1:]).
    @return Exit code: 0 written, 1 version not found.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0].replace("@file release_notes.py", "").strip())
    ap.add_argument("version", help="version without the leading v, for example 2.8.0")
    ap.add_argument("-o", "--output", help="file to write (default: standard output)")
    ap.add_argument("--changelog", default=str(ROOT / "CHANGELOG.md"), help="CHANGELOG.md to read")
    args = ap.parse_args(argv)
    notes = extract(Path(args.changelog).read_text(encoding="utf-8"), args.version.lstrip("v"))
    if not notes.strip():
        print(f"error: no section '## [{args.version}]' in {args.changelog}", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).write_text(notes, encoding="utf-8")
    else:
        sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
