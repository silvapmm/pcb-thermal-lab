#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file compare_logs.py
@brief Compare the output of each study script on the tree with its output on the v2.8.0 package.

@details Reads `<scratch>/slog/tree/<key>.log|.rc` and `<scratch>/slog/base/<key>.log|.rc` and prints one TSV line per
script: key, exit code tree, exit code base, class (identical / numeric / text) and a detail. Only the scratch paths,
memory addresses, traceback line numbers and the lines of WALL-CLOCK timing are masked (DECISION.md 4). The first version masked every line
holding the word "time" and every number followed by "s", which hid the simulated times and the transient
temperatures that 2.9.0 moves on purpose; this version keeps them, so a wall-clock line it misses shows up as a
numeric difference that the tester recognises by hand, never the other way round.
"""
import glob
import os
import re
import sys

NUM = re.compile(r"[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?")
# Wall-clock words only: simulated time ("t = 5 s", "time to 63 %", "t_end") must stay compared
WALL = re.compile(r"(?i)^.*\b(elapsed|wall[- ]?clock|took|run ?time|runtime|cpu time|solved in|ran in)\b.*$",
                  re.MULTILINE)


def norm(text, scratch):
    """!
    @brief Mask what legitimately differs between two runs of one script: paths, addresses, wall-clock lines.

    @param text     Output of the script.
    @param scratch  Scratch folder holding the `tree` and `base` copies (its paths are masked).

    @return str The masked text.
    """
    text = text.replace(scratch + "/tree", "ROOT").replace(scratch + "/base", "ROOT")
    text = re.sub(r"0x[0-9a-f]+", "ADDR", text)
    # Line numbers of a traceback move with any edit of the module; the error itself is still compared
    text = re.sub(r'(File "[^"]*", line )\d+', r"\1N", text)
    return WALL.sub("WALLCLOCK", text)


def compare(scratch):
    """!
    @brief Classify every script that has both a tree and a base log.

    @param scratch  Scratch folder with `slog/tree` and `slog/base`.

    @return list Tuples (key, rc tree, rc base, class, detail).
    """
    rows = []
    for rc in sorted(glob.glob(scratch + "/slog/tree/*.rc")):
        key = os.path.basename(rc)[:-3]
        base_rc = f"{scratch}/slog/base/{key}.rc"
        if not os.path.exists(base_rc):
            continue
        rt = open(rc).read().strip()
        rb = open(base_rc).read().strip()
        a = norm(open(f"{scratch}/slog/tree/{key}.log", errors="replace").read(), scratch)
        b = norm(open(f"{scratch}/slog/base/{key}.log", errors="replace").read(), scratch)
        if a == b:
            rows.append((key, rt, rb, "identical", ""))
            continue
        ta, tb = NUM.findall(a), NUM.findall(b)
        # Same words and the same count of numbers: a purely numeric shift, measured by its largest relative size
        if NUM.sub("#", a) == NUM.sub("#", b) and len(ta) == len(tb):
            n, m = 0, 0.0
            for x, y in zip(ta, tb):
                x, y = float(x), float(y)
                if x != y:
                    n += 1
                    m = max(m, abs(x - y) / max(abs(x), abs(y), 1e-12))
            rows.append((key, rt, rb, "numeric", f"{n} numbers differ, max rel {m:.2e}"))
        else:
            rows.append((key, rt, rb, "text", f"{len(a.splitlines())} vs {len(b.splitlines())} lines"))
    return rows


def main():
    """!
    @brief Print the comparison TSV for the scratch folder given as the first argument.

    @return int Exit code 0.
    """
    for row in compare(sys.argv[1]):
        sys.stdout.write("\t".join(row) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
