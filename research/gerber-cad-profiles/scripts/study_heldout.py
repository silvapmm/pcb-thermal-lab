#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_heldout.py
@brief Do the frozen marker rules recognise sets they were not written from?
@details Question answered (README 3.3): the held-out sets of `fetch_manifest.py --heldout` (other repositories, other versions of
         the same programs) are run through `cadprofiles.detect_set` with the rules exactly as committed before they were fetched.
         The truth of a held-out set is the tool whose banner the repository was found by in the code search (so it is a test of
         the rules on other files and versions, not of the search); a set whose files carry no marker is a miss.
         Run from the repository root: .venv/bin/python research/gerber-cad-profiles/scripts/study_heldout.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import cadprofiles as cp  # noqa: E402
import study_markers as sm  # noqa: E402


def main():
    """!
    @brief Detect every held-out set and print the table.
    @return int Exit code.
    """
    table = cp.load_table()
    base = os.path.join(sm.DATA, "heldout")
    print("| held-out set | truth | detected | confidence | version | files | files naming the truth |")
    print("| :-- | :-- | :-- | :-- | :-- | --: | --: |")
    ok = total = 0
    misses = []
    for d in sorted(os.listdir(base)):
        truth = d.split("__")[0]
        files = sm.collect(os.path.join(base, d))
        det = cp.detect_set(files, table)
        own = sum(1 for n, raw in files.items()
                  if any(h.profile == truth and h.weight >= cp.DECISIVE for h in cp.scan_file(table, n, raw)))
        good = det.profile == truth
        ok += good
        total += 1
        if not good:
            misses.append(d)
        print("| %s | %s | %s%s | %s | %s | %d | %d |" % (d, truth, det.profile, "" if good else " (WRONG)", det.confidence,
                                                          det.version or det.declared, len(files), own))
    print("\nrecognised: %d of %d; misses: %s" % (ok, total, ", ".join(misses) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
