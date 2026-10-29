#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_license_header.py
@brief Every Python file of the repository starts with the copyright and licence notice of the project.
@details The two comment lines come first (after a shebang or an encoding line, if there is one) and before the docstring of the module, which stays the
         first statement. A new file without them fails here.
"""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
HEADER = ("#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.",
          "#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.")
FOLDERS = ("pcbthermal", "tests", "examples", "research")


def python_files():
    """!
    @brief The Python files of the repository that the rule covers (the environments and the working copies of the agents are left out).
    @return Sorted list of pathlib.Path.
    """
    out = []
    for folder in FOLDERS:
        for p in (ROOT / folder).rglob("*.py"):
            parts = set(p.relative_to(ROOT).parts)
            if parts & {".venv", ".venv-research", "__pycache__", "out", "data", "pylib", "variant"}:
                continue
            out.append(p)
    return sorted(out)


def test_every_python_file_starts_with_the_copyright_and_licence_notice():
    missing = []
    for p in python_files():
        lines = p.read_text(encoding="utf-8").split("\n")
        start = 0
        while start < len(lines) and (lines[start].startswith("#!") or (start < 2 and lines[start].startswith("#") and "coding" in lines[start])):
            start += 1
        if tuple(lines[start:start + 2]) != HEADER:
            missing.append(str(p.relative_to(ROOT)))
    assert not missing, "files without the copyright and licence header: " + ", ".join(missing[:10])
