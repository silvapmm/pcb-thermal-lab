#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file licence_table.py
@brief Print the table of sample sets with their source and the licence recorded at fetch time (for the README, section 3.1).
@details Reads, per set of data/, the `_SOURCE.txt` written by `fetch_repo.py` (repository, licence reported by the GitHub API) or, for the
         folders copied from the gerbonara test resources, the `README` ("From <url>") and the first line of the `LICENSE` file of the folder.
         Run: .venv/bin/python -I research/gerber-cad-profiles/scripts/licence_table.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")


def first_line(path, n=70):
    """!
    @brief First non-empty line of a text file.
    @param path  File.
    @param n     Maximum length.
    @return str The line, or "" when the file is missing.
    """
    if not os.path.exists(path):
        return ""
    for ln in open(path, encoding="utf-8", errors="replace").read().splitlines():
        ln = ln.strip().lstrip("﻿")
        if ln:
            return ln[:n]
    return ""


def main():
    """!
    @brief Walk the data folder and print the table.
    @return int Exit code.
    """
    print("| set (data/) | source | licence as recorded |")
    print("| :-- | :-- | :-- |")
    for top in sorted(os.listdir(DATA)):
        d = os.path.join(DATA, top)
        if not os.path.isdir(d):
            continue
        subs = [s for s in sorted(os.listdir(d)) if os.path.exists(os.path.join(d, s, "_SOURCE.txt"))]
        if subs:
            for s in subs:
                t = open(os.path.join(d, s, "_SOURCE.txt")).read()
                repo = re.search(r"repo: (\S+)", t).group(1)
                lic = re.search(r"licence \(GitHub API\): (.*)", t).group(1)
                print("| %s/%s | %s | %s (GitHub API) |" % (top, s, repo, lic))
        elif top.startswith("realboards-"):
            print("| %s | see research/gerber-real-boards/README.md section 3 (fetched by that study) | as stated there |" % top)
        else:
            src = first_line(os.path.join(d, "README"))
            lic = first_line(os.path.join(d, "LICENSE"))
            print("| %s | gerbonara tests/resources; %s | %s (LICENSE of the folder) |" % (top, src or "no README", lic or "no LICENSE file"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
