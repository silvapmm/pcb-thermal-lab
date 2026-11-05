#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file peek.py
@brief Print the first lines of every file of a sample folder (untrusted text, read as bytes).

Question answered: what does a tool write at the top of its files?  Used to read the banners
by hand before the detection rules are written.  Run: .venv/bin/python -I peek.py DIR [N]
"""
import os
import sys


def main(argv):
    """!
    @brief Print N lines of each file under a folder.

    @param argv  [folder, optional number of lines].

    @return int Exit code.
    """
    root = argv[1]
    n = int(argv[2]) if len(argv) > 2 else 6
    for dp, _, fs in sorted(os.walk(root)):
        for f in sorted(fs):
            p = os.path.join(dp, f)
            if os.path.getsize(p) > 5_000_000:
                continue
            raw = open(p, "rb").read(3000)
            txt = raw.decode("latin-1")
            lines = txt.replace("\r", "\n").split("\n")
            lines = [ln for ln in lines if ln.strip()][:n]
            print("--", os.path.relpath(p, root))
            for ln in lines:
                print("   ", ln[:150])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
