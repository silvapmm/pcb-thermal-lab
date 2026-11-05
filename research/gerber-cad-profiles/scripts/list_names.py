#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file list_names.py
@brief Print the file names of sample sets, one line per set (to write the hand labels of the layer functions).
@details Run: .venv/bin/python -I list_names.py SET [SET ...]   (SET relative to research/gerber-cad-profiles/data)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")


def main(argv):
    """!
    @brief Print the names.
    @param argv  Command line.
    @return int Exit code.
    """
    for s in argv[1:]:
        names = []
        for dp, _, fs in os.walk(os.path.join(DATA, s)):
            names += [f for f in fs if f.lower() not in ("license", "readme", "source", "_source.txt")]
        print("## %s: %s" % (s, " | ".join(sorted(names))[:1500]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
