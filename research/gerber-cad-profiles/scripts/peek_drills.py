#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file peek_drills.py
@brief Print the first lines of every drill-like file (Excellon/XNC) of every sample set.

Question answered: how does each tool identify itself in the drill file (comments, header
commands)?  A file counts as a drill file when its first 600 bytes contain M48 or a
`;`-comment header and no `%FS`.  Run: .venv/bin/python -I peek_drills.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")


def main():
    """!
    @brief Walk the data folder and print drill heads, one file per folder and header style.

    @return int Exit code.
    """
    seen = set()
    for dp, _, fs in sorted(os.walk(DATA)):
        for f in sorted(fs):
            p = os.path.join(dp, f)
            if os.path.getsize(p) > 3_000_000:
                continue
            head = open(p, "rb").read(700).decode("latin-1")
            if "%FS" in head or "G04" in head[:300]:
                continue
            if "M48" not in head[:400] and not head.lstrip().startswith(";"):
                continue
            key = (os.path.dirname(p), head[:25])
            if key in seen:
                continue
            seen.add(key)
            print("--", os.path.relpath(p, DATA))
            for ln in [x for x in head.replace("\r", "\n").split("\n") if x.strip()][:7]:
                print("    ", ln[:130])
    return 0


if __name__ == "__main__":
    sys.exit(main())
