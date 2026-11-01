#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_freeze_reference.py
@brief Question: which numbers of the final release candidate are frozen as the reference of the next versions? Writes `reference/v<version>.json` from the baseline and the final run.
@details Usage, from the repository root, only after the 2.4.5 release candidate is final and `study_diff.py` shows no alarm:

         .venv/bin/python research/release-regression-245/scripts/study_freeze_reference.py out/v2.4.4.json out/final.json --version 2.4.5

         A record is frozen as `bit` when its numbers are equal in the baseline and in the final run (nothing in the release may change it: later versions are held to exact
         equality), otherwise as `moved` (held to 1e-6 K). The script refuses to freeze while `study_diff.py` still reports an alarm (an unexplained or must-not-move shift),
         unless `--allow-alarms` is given (then the alarm count is written into the file), refuses a run whose program version is not `--version`, and refuses to overwrite an existing
         file without `--force`. The file is committed (it is small: a few hundred numbers per model); the result sets in `out/` are not.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "lib"))

import regress_classify as C                                                # noqa: E402
import regress_frozen as F                                                  # noqa: E402


def main(argv=None):
    """!
    @brief Build and write the frozen file.
    @param argv List of arguments (default: sys.argv[1:]).
    @return int exit code (0, or 2 when the freeze is refused).
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("base", help="result set of the earlier release (out/v2.4.4.json)")
    ap.add_argument("final", help="result set of the final release candidate")
    ap.add_argument("--version", default="2.4.5", help="version the numbers belong to (default 2.4.5)")
    ap.add_argument("--table", default=str(ROOT / "reference" / "expected_shifts.json"))
    ap.add_argument("--out", default=None, help="output file (default reference/v<version>.json)")
    ap.add_argument("--allow-alarms", action="store_true")
    ap.add_argument("--force", action="store_true", help="overwrite an existing file")
    a = ap.parse_args(argv)
    base, final = C.load_set(a.base), C.load_set(a.final)
    out = Path(a.out) if a.out else ROOT / "reference" / f"v{a.version}.json"
    if final["program"]["version"] != a.version:
        print(f"refused: the run is of program version {final['program']['version']}, not {a.version} (bump the version in the tree before freezing)")
        return 2
    if out.exists() and not a.force:
        print(f"refused: {out} exists (use --force to replace it, see INTEGRATION.md 'Updating the file')")
        return 2
    table = json.loads(Path(a.table).read_text(encoding="utf-8"))
    diff = C.diff_sets(base, final, table)
    sor = C.diff_sets(base, final, table, key="sor")
    trans = C.classify_transients(C.transient_diff(base, final), table)
    alarms = diff["summary"]["alarms"] + sor["summary"]["alarms"] + sum(1 for r in trans if r["class"] in C.ALARMS)   # the SOR and the times to 63 % count too (review)
    bad = [c for c in C.internal_checks(final) if not c["ok"]]
    if (alarms or bad) and not a.allow_alarms:
        print(f"refused: {alarms} alarm(s) and {len(bad)} failed check(s) in the comparison with {base['label']}; run study_diff.py and explain them first")
        return 2
    data = F.build(base, final, a.version)
    data["alarms_when_frozen"] = alarms
    data["to_be_explained_when_frozen"] = diff["summary"]["counts"]["to_be_explained"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    n_bit = sum(1 for r in data["records"].values() if r["class"] == "bit")
    print(f"wrote {out}: {len(data['records'])} records ({n_bit} bit, {len(data['records']) - n_bit} moved), {len(data['transients'])} transients, "
          f"{len(data['skipped'])} skipped; alarms when frozen: {alarms}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
